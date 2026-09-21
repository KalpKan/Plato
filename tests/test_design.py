"""Design-system guarantees for the "Registrar's ledger" redesign.

These tests hold the spec (docs/design/spec.md) in place: the slop the audit
found must stay deleted, the rewritten copy must stay rewritten, every keyframe
must stay guarded by prefers-reduced-motion, and /review must stay one ruled
table rather than nine cards.
"""
import uuid
from datetime import date, datetime, time
from pathlib import Path

import pytest

from src.app import app, calculate_completeness, ics_response
from src.models import AssessmentTask, CourseTerm, ExtractedCourseData, SectionOption

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "public/static/style.css").read_text()
JS = (ROOT / "public/static/app.js").read_text()
INDEX_HTML = (ROOT / "templates/index.html").read_text()
REVIEW_HTML = (ROOT / "templates/review.html").read_text()


def _data(assessments=None, lecture=None, lab=None, tutorial=None):
    return ExtractedCourseData(
        term=CourseTerm(term_name="Fall 2026", start_date=date(2026, 9, 9), end_date=date(2026, 12, 8)),
        lecture_sections=list(lecture or []),
        lab_sections=list(lab or []),
        assessments=list(assessments or []),
        course_code="BIOL 1001A",
        course_name="Test Course",
        tutorial_sections=list(tutorial or []),
    )


def _section(kind="Lecture"):
    return SectionOption(section_type=kind, section_id="001", days_of_week=[0],
                         start_time=time(9, 30), end_time=time(10, 20))


# --------------------------------------------------------------------------
# Task 1 — the rewritten summary copy and the .ics headers
# --------------------------------------------------------------------------

def test_summary_sentences_replace_the_unparseable_fraction():
    a = [AssessmentTask(title=f"A{i}", type="assignment", weight_percent=10.0,
                        due_datetime=datetime(2026, 10, i + 1, 23, 59)) for i in range(9)]
    a[0].weight_percent = 21.0  # 21 + eight tens = 101
    c = calculate_completeness(_data(assessments=a, lecture=[_section()]))
    assert c["summary_assessments"] == "All 9 assessments found. Weights total 101 %."
    assert c["summary_slots"] == "1 lecture slot. No lab, no tutorial."
    assert c["summary_undated"] == "Every assessment has a date."


def test_summary_says_what_is_missing_when_weights_fall_short():
    a = [AssessmentTask(title="Midterm", type="midterm", weight_percent=40.0,
                        due_datetime=datetime(2026, 10, 20, 23, 59)),
         AssessmentTask(title="Final", type="final", weight_percent=53.0)]
    c = calculate_completeness(_data(assessments=a))
    assert c["summary_assessments"] == "2 assessments found. Weights total 93 % — 7 % is unaccounted for."
    assert c["summary_slots"] == "No lecture, lab or tutorial slot was found."
    assert c["summary_undated"] == "1 assessment still needs a date."


def test_summary_names_bonus_weight_without_counting_it():
    bonus = AssessmentTask(title="Bonus quiz", type="quiz", weight_percent=1.0,
                           due_datetime=datetime(2026, 11, 3, 23, 59))
    bonus.is_bonus = True
    a = [AssessmentTask(title="Exam", type="final", weight_percent=100.0,
                        due_datetime=datetime(2026, 12, 10, 9, 0)), bonus]
    c = calculate_completeness(_data(assessments=a, lecture=[_section()], lab=[_section("Lab")]))
    assert c["summary_assessments"] == "All 2 assessments found. Weights total 100 %. Plus 1 % bonus, not counted."
    assert c["summary_slots"] == "1 lecture slot. 1 lab slot. No tutorial."


def test_ics_range_ignores_the_timezone_blocks_own_dtstart():
    # A VTIMEZONE carries DTSTART:20240101T000000 daylight markers; counting
    # them dragged the range back to "Jan 01" of the wrong year on the live app.
    ics = (b"BEGIN:VCALENDAR\r\nBEGIN:VTIMEZONE\r\nBEGIN:DAYLIGHT\r\n"
           b"DTSTART:20240310T030000\r\nEND:DAYLIGHT\r\nBEGIN:STANDARD\r\n"
           b"DTSTART:20240101T000000\r\nEND:STANDARD\r\nEND:VTIMEZONE\r\n"
           b"BEGIN:VEVENT\r\nDTSTART;TZID=America/Toronto:20250829T130000\r\nEND:VEVENT\r\n"
           b"BEGIN:VEVENT\r\nDTSTART;TZID=America/Toronto:20251208T235500\r\nEND:VEVENT\r\n"
           b"END:VCALENDAR\r\n")
    with app.test_request_context():
        r = ics_response("x.ics", ics)
    assert r.headers["X-Plato-Events"] == "2"
    assert r.headers["X-Plato-Range"] == "Aug 29 - Dec 08, 2025"


def test_ics_event_count_expands_weekly_series():
    """A term of Monday lectures is ONE VEVENT with an RRULE, not one event.

    Counting BEGIN:VEVENT told the visitor "22 events" for a calendar that
    imports about 74, on the screen whose whole job is to be trusted.
    """
    ics = (b"BEGIN:VCALENDAR\r\n"
           b"BEGIN:VEVENT\r\nDTSTART;TZID=America/Toronto:20250908T123000\r\n"
           b"RRULE:FREQ=WEEKLY;UNTIL=20250929T035959Z;BYDAY=MO\r\nEND:VEVENT\r\n"
           b"BEGIN:VEVENT\r\nDTSTART;TZID=America/Toronto:20251020T235900\r\nEND:VEVENT\r\n"
           b"END:VCALENDAR\r\n")
    with app.test_request_context():
        r = ics_response("x.ics", ics)
    # Sep 8, 15, 22, 29 (four Mondays) + the single dated assessment
    assert r.headers["X-Plato-Events"] == "5"
    # and the range runs to the last OCCURRENCE, not the series' first DTSTART
    assert r.headers["X-Plato-Range"] == "Sep 08 - Oct 20, 2025"


def test_the_download_filename_header_is_ascii():
    with app.test_request_context():
        r = ics_response("Économie_1021A.ics", b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n")
    assert r.headers["Content-Disposition"].isascii()


def test_ics_response_carries_the_event_count_and_range():
    ics = (b"BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nDTSTART;VALUE=DATE:20260909\r\nEND:VEVENT\r\n"
           b"BEGIN:VEVENT\r\nDTSTART:20261208T235900\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
    with app.test_request_context():
        r = ics_response("x.ics", ics)
    assert r.headers["X-Plato-Events"] == "2"
    assert r.headers["X-Plato-Range"] == "Sep 09 - Dec 08, 2026"  # ASCII: headers are latin-1
    assert r.headers["X-Plato-Range"].isascii()
    assert "X-Plato-Events" in r.headers["Access-Control-Expose-Headers"]
    assert r.mimetype == "text/calendar"


# --------------------------------------------------------------------------
# Task 3 — the stylesheet
# --------------------------------------------------------------------------

def test_the_glow_and_the_dark_saas_palette_are_gone():
    for dead in ("--shadow-glow", "#09090b", "#2563eb", "calendarPulse", "workflowStep1",
                 "arrowParticle1", "rotateProcessing", "processingPulse"):
        assert dead not in CSS, f"{dead} survived the redesign"


def test_every_animation_is_guarded_by_reduced_motion():
    assert "@media (prefers-reduced-motion: reduce)" in CSS
    guard = CSS.split("@media (prefers-reduced-motion: reduce)", 1)[1]
    assert "animation-duration: 0.01ms" in guard
    assert "transform: none" in guard
    assert "transition: all" not in CSS, "every transition must name its properties"


def test_one_easing_family():
    import re
    curves = set(re.findall(r"cubic-bezier\([^)]*\)", CSS))
    assert curves <= {"cubic-bezier(.22, 1, .36, 1)", "cubic-bezier(.4, 0, 1, 1)"}, curves


def test_paper_tokens_are_the_spec_tokens():
    for token, value in (("--paper", "#faf8f4"), ("--sheet", "#ffffff"), ("--ink", "#1c1a17"),
                         ("--rule", "#e0dad0"), ("--flag", "#8a5f00"), ("--flag-bg", "#fff6e0"),
                         ("--link", "#1f5fbf")):
        assert f"{token}: {value}" in CSS


def test_reduced_motion_beats_the_reveal_gate_on_its_own():
    # `html.motion-ready [data-reveal] { opacity: 0 }` is more specific than a
    # bare `[data-reveal] { opacity: 1 }`, so the reduce block has to name the
    # gated selector (and win) rather than leaning on the JS gate.
    guard = CSS.split("@media (prefers-reduced-motion: reduce)", 1)[1]
    assert "html.motion-ready [data-reveal]" in guard
    assert "opacity: 1 !important" in guard


def test_content_never_depends_on_the_reveal_script_succeeding():
    # [data-reveal] starts at opacity 0 only once initMotion has taken charge.
    assert "html.motion-ready [data-reveal] { opacity: 0; }" in CSS
    assert "\n[data-reveal] { opacity: 0; }" not in CSS  # never ungated
    assert "motion-ready" in JS


def test_the_type_is_self_hosted_and_three_families():
    for family in ("Newsreader", "Inter", "JetBrains Mono"):
        assert f"font-family: '{family}'" in CSS
    assert "fonts/newsreader-latin.woff2" in CSS
    assert "fonts.googleapis.com" not in CSS and "fonts.gstatic.com" not in CSS


# --------------------------------------------------------------------------
# Task 4/5 — the shell and the drop screen
# --------------------------------------------------------------------------

@pytest.fixture()
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_every_route_shares_one_shell_with_a_skip_link_and_the_step_rail(client):
    for path in ("/", "/manual"):
        html = client.get(path).get_data(as_text=True)
        assert 'class="skip-link"' in html and 'href="#content"' in html
        assert 'id="content"' in html
        assert "Course outline to calendar" in html
        assert 'class="step-rail"' in html and ">01<" in html and ">03<" in html
        assert 'aria-current="step"' in html


def test_the_landing_page_has_no_marketing_layer_and_no_fabricated_calendar(client):
    html = client.get("/").get_data(as_text=True)
    for dead in ("Automatic Course Calendar Generation", "From Course Outline to Calendar in Seconds",
                 "Get Started", "How It Works", "calendar-background", "workflow-visualization",
                 "arrow-particle", "Lecture 1", "Assignment 1", "feature-icon", "hero-badge",
                 "hero-glow", "btn-hero"):
        assert dead not in html, f"{dead} survived on /"
    assert "Check your outline, then take the calendar." in html
    assert "Drag and drop your course outline here" in html
    assert "Not a PDF, or a scan?" in html
    assert "Enter the course by hand" in html
    assert 'aria-live="polite"' in html
    assert 'role="alert"' in html


def test_the_fake_calendar_chips_are_gone_from_the_source():
    for dead in ("calendar-event", "calendar-day-number", "Lecture 1", "Assignment 1", "Lab 1",
                 "workflow-arrow", "arrow-line", "arrow-particle", "calendarPulse"):
        assert dead not in INDEX_HTML, f"{dead} survived in templates/index.html"


# --------------------------------------------------------------------------
# Task 6/7 — the ledger and the download confirmation
# --------------------------------------------------------------------------

def test_the_review_screen_is_one_ruled_table_not_nine_cards():
    assert 'class="ledger assessments"' in REVIEW_HTML
    assert "<tbody" in REVIEW_HTML and "<tfoot" in REVIEW_HTML
    assert 'data-summary="assessments"' in REVIEW_HTML
    assert 'data-summary="slots"' in REVIEW_HTML
    assert 'data-slot="lecture"' in REVIEW_HTML and 'data-slot="tutorial"' in REVIEW_HTML
    # the audit's "card apocalypse" and its unparseable fraction
    for dead in ("summary-stats", "stat-item", "stat-value", "of 100% found",
                 "Lecture / lab / tutorial slots"):
        assert dead not in REVIEW_HTML, f"{dead} survived on /review"
    # the copy that must stay verbatim
    assert "Check every date against your outline" in REVIEW_HTML
    assert "What could not be read from the PDF" in REVIEW_HTML
    assert "labs are usually only on draftmyschedule.uwo.ca" in REVIEW_HTML
    assert "Add Section" in REVIEW_HTML  # kept, restyled


def test_the_download_confirmation_block_exists_and_starts_hidden():
    assert 'id="download-done"' in REVIEW_HTML
    assert "X-Plato-Events" in JS and "X-Plato-Range" in JS


# --------------------------------------------------------------------------
# Task 9 — motion in JS
# --------------------------------------------------------------------------

def test_motion_is_gated_on_reduced_motion_in_js_too():
    assert "prefers-reduced-motion: reduce" in JS
    assert "IntersectionObserver" in JS
    assert "calendarPulse" not in JS and "animateWorkflow" not in JS


def test_update_field_returns_the_summary_sentences(monkeypatch, tmp_path):
    """The inline-edit endpoint must say exactly what a reloaded page says.

    It used to hand-pick keys out of calculate_completeness() and drop the three
    summary_* sentences, so after fixing the last undated assessment the reading
    line still asserted "2 assessments still need a date" — in calm black text,
    because the is-flagged class DID get toggled off.
    """
    from src.app import app as flask_app, get_cache
    import src.app as mod

    monkeypatch.setattr(mod, "upload_dir", lambda: tmp_path)
    data = _data(assessments=[
        AssessmentTask(title="Midterm", type="midterm", weight_percent=50.0,
                       due_datetime=datetime(2026, 10, 20, 23, 59)),
        AssessmentTask(title="Final", type="final", weight_percent=50.0),
    ], lecture=[_section()])
    h = "designhash-" + uuid.uuid4().hex  # the edit below mutates the cached entry
    get_cache().store_extraction(h, data)
    c = flask_app.test_client()
    with c.session_transaction() as sess:
        sess["pdf_hash"] = h
        sess["session_id"] = "sid"
        sess["user_choices"] = {}

    before = c.get("/review").get_data(as_text=True)
    assert "1 assessment still needs a date." in before

    r = c.post("/api/update-field", json={"field_type": "assessment_due_date",
                                          "assessment_index": 1,
                                          "value": "2026-12-10T09:00"})
    body = r.get_json()
    assert body["success"] is True
    comp = body["completeness"]
    for key in ("summary_assessments", "summary_slots", "summary_undated"):
        assert key in comp, f"{key} missing from /api/update-field — the reading line goes stale"
    assert comp["summary_undated"] == "Every assessment has a date."
    assert comp["assessments_undated"] == 0


def test_the_accent_is_never_navigation_decoration():
    # The active step ordinal was painted in the flag accent on every page, so
    # the first amber a visitor met on / meant "you are here", not "check this".
    assert ".step.is-active .step-n { color: var(--ink); }" in CSS
    assert "var(--flag)" not in CSS.split(".step.is-active .step-n", 1)[1].split("}", 1)[0]
