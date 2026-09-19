"""Round-3 defects (docs/reports/plato.md, 2026-09-19): D21 invented final-exam dates, D22 a course
that meets on two days offered as two "sections", D23 a printed lab slot + "day of lab" rule, D24
prose-only test dates and a Format column in titles, D25 the Engineering "Fall/Winter" header.

Every fixture is the outline's own wording (pdfplumber text / table cells), trimmed.
"""
import importlib
import re
import sys
from datetime import date, datetime, time

from src.models import AssessmentTask, CourseTerm, ExtractedCourseData, SectionOption
from src.outline import assessments as A
from src.outline.dates import DateResolver, parse_time_span
from src.outline.pipeline import build
from src.outline.schedule import Slot
from src.outline.tables import compress_table
from src.outline.term import TermInfo

HASH = "h" * 64


def winter25():
    return DateResolver(term_start=date(2025, 1, 6), term_end=date(2025, 4, 4),
                        exam_periods=[(date(2025, 4, 7), date(2025, 4, 30))])


def fall25():
    return DateResolver(term_start=date(2025, 9, 4), term_end=date(2025, 12, 9),
                        exam_periods=[(date(2025, 12, 11), date(2025, 12, 22))],
                        reading_weeks=[(date(2025, 11, 3), date(2025, 11, 9))])


# ------------------------------------------------------------------ D21: dates
def test_day_range_inside_exam_period_sentence_is_not_a_date():
    """MOS 2242A: 'Exam 3: to be scheduled during the final exam period, Dec. 11-22, 2025'."""
    r = fall25().resolve("to be scheduled during the final exam period, Dec. 11-22, 2025")
    assert r.status in ("range", "registrar")
    assert r.date is None
    assert r.window == (date(2025, 12, 11), date(2025, 12, 22))


def test_schedule_cell_april_7_30_is_a_window_not_april_7():
    """Biol 3415G schedule row 'April 7-30 | April exam period | Final Exam scheduled by the registrar'."""
    r = winter25().resolve("April 7-30")
    assert r.status == "range" and r.date is None
    assert r.window == (date(2025, 4, 7), date(2025, 4, 30))


def test_duration_after_a_month_name_is_not_a_date():
    """B2382: 'Tutorial Quiz 1 | 7.5% | Written in January 20 mins Online' is not January 20."""
    r = winter25().resolve("Written in January 20 mins Online")
    assert r.status != "exact" and r.date is None
    assert r.status == "range" and r.window == (date(2025, 1, 1), date(2025, 1, 31))


def test_a_real_date_next_to_a_day_range_still_wins():
    r = fall25().resolve("Thursday, Oct. 30, 11:30 - 1:30pm")
    assert r.status == "exact" and r.date == date(2025, 10, 30) and r.time == time(11, 30)


def test_registrar_row_is_not_overwritten_by_the_schedule_table():
    """Biol 3415G: the evaluation table says 'Scheduled by the registrar'; the week-by-week table's
    'April 7-30 | April exam period | Final Exam scheduled by the registrar' must not date it."""
    r = winter25()
    final = A.Assessment(title="Final Exam", weight=40, kind="final", date=r.resolve("Scheduled by the registrar"))
    rows = [(A.DateResult(status="exact", date=date(2025, 4, 7), raw="April 7-30"),
             "April exam period Final Exam scheduled by the registrar")]
    A._enrich_from_schedule([final], rows)
    assert final.date.status == "registrar" and final.date.date is None


def test_schedule_row_that_names_the_registrar_never_dates_anything():
    r = winter25()
    final = A.Assessment(title="Final Exam", weight=40, kind="final", date=A.DateResult(status="missing"))
    rows = [(A.DateResult(status="exact", date=date(2025, 4, 7), raw="April 7"),
             "Final Exam scheduled by the registrar")]
    A._enrich_from_schedule([final], rows)
    assert final.date.status != "exact"


def test_scorer_counts_any_date_on_a_registrar_or_range_item_as_fabricated():
    sys.path.insert(0, "tests/corpus")
    score = importlib.import_module("score")
    gt = {"file": "x.pdf", "course_code": "X 1000", "course_name": "X",
          "term": {"start": "2025-01-06", "end": "2025-04-04", "exam_period": ["2025-04-07", "2025-04-30"]},
          "sections": [],
          "assessments": [
              {"title": "Final Exam", "type": "final", "weight": 40, "due": None, "date_status": "registrar"},
              {"title": "Tutorial Quiz 1", "type": "quiz", "weight": 7.5, "due": None, "date_status": "range",
               "window": ["2025-01-06", "2025-01-31"]},
              {"title": "Quizzes", "type": "quiz", "weight": 10, "due": None, "date_status": "recurring",
               "dates": ["2025-01-20", "2025-02-20"]},
          ]}
    ex = {"ok": True, "course_code": "X 1000", "course_name": "X",
          "term": {"start": "2025-01-06", "end": "2025-04-04"}, "sections": [],
          "assessments": [
              {"title": "Final Exam", "type": "final", "weight": 40, "due": "2025-04-07"},
              {"title": "Tutorial Quiz 1", "type": "quiz", "weight": 7.5, "due": "2025-01-20"},
              {"title": "Quizzes", "type": "quiz", "weight": 10, "due": "2025-01-20"},
          ]}
    r = score.score_one(gt, ex)
    assert r["counts"]["no_fabricated"] == (3, 1), r["date_details"]


# ---------------------------------------------------------------- D24: prose
MSE_TEXT = (
    "Term Test 1 15% KB4\nTerm Test 2 15%\nFinal Examination 50% PA2\n"
    "Term Tests: There will be two term tests. The tests will be closed book. An equation aid and\n"
    "formula sheet will be provided.\n"
    "The tests are tentatively set to be held on October 2nd, 2025 and October 30th, 2025. Both\n"
    "will be held from 1:30 pm to 3:30 pm (corresponding with the tutorial period). The first term\n"
    "test will cover the material from weeks 1-4.\n"
    "F inal Examination: The final examination will take place during the regular examination\n"
    "period and will be 3 hours in duration.\n")
MSE_TABLE = [["Name", "% Worth", "Assigned", "Due Date", "CEAB GAs ASSESSED"],
             ["Tutorial Exercises", "10%", "", "", ""], ["Laboratory", "10%", "", "", "I2, I3"],
             ["Term Test 1", "15%", "", "", "KB4"], ["Term Test 2", "15%", "", "", ""],
             ["Final Examination", "50%", "", "", "PA2"]]


def _fall25_term():
    return TermInfo(name="Fall 2025", start=date(2025, 9, 4), end=date(2025, 12, 9), source="sessional",
                    exam_periods=[(date(2025, 12, 11), date(2025, 12, 22))], year_hints=[2025])


def test_two_tests_dated_by_one_plural_sentence():
    items, _ = A.extract_assessments([(5, MSE_TEXT)], [MSE_TABLE], _fall25_term())
    by = {a.title: a for a in items}
    assert by["Term Test 1"].date.status == "exact" and by["Term Test 1"].date.date == date(2025, 10, 2)
    assert by["Term Test 2"].date.status == "exact" and by["Term Test 2"].date.date == date(2025, 10, 30)
    assert by["Term Test 1"].date.time == time(13, 30) and by["Term Test 2"].date.time == time(13, 30)
    assert by["Final Examination"].date.status in ("range", "registrar")


def test_undated_table_rows_always_carry_a_reason():
    items, _ = A.extract_assessments([(5, MSE_TEXT)], [MSE_TABLE], _fall25_term())
    for a in items:
        if a.date.status == "missing":
            assert a.date.note, a.title


def test_from_to_time_span():
    assert parse_time_span("from 1:30 pm to 3:30 pm") == (time(13, 30), time(15, 30))


MICROIMM_TABLE = [
    ['', 'Assessment', '', '', 'Format', '', '', 'Weighting', '', '', 'Date', '', '', 'Flexibility', ''],
    ['Test 1', None, None, 'mixed', None, None, '20%', None, None, '', None, None, 'None', None, None],
    ['Test 2', None, None, 'mixed', None, None, '20%', None, None, '', None, None, 'None', None, None],
    ['Test 3', None, None, 'mixed', None, None, '20%', None, None, '', None, None, 'None', None, None],
    ['Final Exam', None, None, 'mixed', None, None, '40%', None, None, '', None, None, 'Not applicable', None, None],
]
MICROIMM_TEXT = ("Assessment Format Weighting Date Flexibility\nTest 1 mixed 20% None\nTest 2 mixed 20% None\n"
                 "Test 3 mixed 20% None\nFinal Exam mixed 40% Not applicable\n"
                 "Week 13 Apr 2 Review\nFinal Exam during the final exam period, to be announced\n")


def test_compress_table_realigns_a_shifted_header_even_when_one_column_is_empty():
    rows = compress_table(MICROIMM_TABLE)
    assert rows[0] == ["Assessment", "Format", "Weighting", "Date", "Flexibility"]
    assert rows[1] == ["Test 1", "mixed", "20%", "", "None"]


def test_format_column_does_not_leak_into_titles_and_final_is_in_the_exam_period():
    term = TermInfo(name="Winter 2025", start=date(2025, 1, 6), end=date(2025, 4, 4), source="outline",
                    exam_periods=[(date(2025, 4, 7), date(2025, 4, 30))], year_hints=[2025])
    items, _ = A.extract_assessments([(3, MICROIMM_TEXT)], [MICROIMM_TABLE], term)
    titles = sorted(a.title for a in items)
    assert titles == ["Final Exam", "Test 1", "Test 2", "Test 3"], titles
    final = next(a for a in items if a.title == "Final Exam")
    assert final.date.status in ("range", "tba", "registrar") and final.date.date is None
    assert final.date.window == (date(2025, 4, 7), date(2025, 4, 30))


# ---------------------------------------------------------------- D22: two-day lecture
BIOL_TEXT = ("Biology 3415G Aquatic Ecology Winter 2025\nLectures: Mondays (10:30-11:30 AM) and Wednesdays (9:30-11:30 AM)\n"
             "Key Sessional Dates: Classes begin: January 6, 2025 Classes end: April 4, 2025 Exam period: April 7 - 30, 2025\n")


def test_two_day_lecture_without_section_ids_is_one_section_with_two_meetings():
    data = build([(1, BIOL_TEXT)], [], "B3415G.pdf")
    assert len(data.lecture_sections) == 1
    lec = data.lecture_sections[0]
    meetings = sorted((tuple(m.days_of_week), m.start_time, m.end_time) for m in lec.all_meetings())
    assert meetings == [((0,), time(10, 30), time(11, 30)), ((2,), time(9, 30), time(11, 30))]


def test_same_section_id_on_two_days_is_one_section_and_alternatives_stay_apart():
    """CS 2211A: Section 001 Tue 11:30-12:30 + Thu 10:30-12:30; Section 002 Tue 8:30-9:30 + Fri 8:30-10:30."""
    from src.outline.pipeline import group_slots
    slots = [Slot("lecture", [1], time(11, 30), time(12, 30), section_id="001"),
             Slot("lecture", [3], time(10, 30), time(12, 30), section_id="001"),
             Slot("lecture", [1], time(8, 30), time(9, 30), section_id="002"),
             Slot("lecture", [4], time(8, 30), time(10, 30), section_id="002")]
    groups = group_slots(slots)
    assert [g[0].section_id for g in groups] == ["001", "002"] and all(len(g) == 2 for g in groups)
    # two id-less lectures on the same weekday are alternatives, not one section
    alt = [Slot("lecture", [2], time(9, 30), time(12, 30)), Slot("lecture", [2], time(13, 30), time(16, 30))]
    assert len(group_slots(alt)) == 2
    # id-less labs on different days are alternative lab sections, never merged
    labs = [Slot("lab", [0], time(14, 30), time(17, 30)), Slot("lab", [1], time(14, 30), time(17, 30))]
    assert len(group_slots(labs)) == 2


def test_section_round_trips_its_meetings_through_the_dict_form():
    from src.models import Meeting, section_from_dict, section_to_dict
    s = SectionOption(section_type="Lecture", section_id="", days_of_week=[0], start_time=time(10, 30),
                      end_time=time(11, 30), meetings=[Meeting(days_of_week=[2], start_time=time(9, 30), end_time=time(11, 30))])
    back = section_from_dict(section_to_dict(s))
    assert [(m.days_of_week, m.start_time, m.end_time) for m in back.all_meetings()] == \
        [([0], time(10, 30), time(11, 30)), ([2], time(9, 30), time(11, 30))]


def _app(monkeypatch, tmp_path):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("PLATO_TMP_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    sys.modules.pop("src.app", None)
    return importlib.import_module("src.app")


def _biol_data():
    from src.models import Meeting
    term = CourseTerm(term_name="Winter 2025", start_date=date(2025, 1, 6), end_date=date(2025, 4, 4),
                      exam_periods=[(date(2025, 4, 7), date(2025, 4, 30))])
    lec = SectionOption(section_type="Lecture", section_id="", days_of_week=[0], start_time=time(10, 30),
                        end_time=time(11, 30), meetings=[Meeting(days_of_week=[2], start_time=time(9, 30), end_time=time(11, 30))])
    return ExtractedCourseData(term=term, lecture_sections=[lec], lab_sections=[], assessments=[],
                               course_code="Biol 3415G", course_name="Aquatic Ecology")


def _client(mod, data):
    mod.get_cache().store_extraction(HASH, data)
    c = mod.app.test_client()
    with c.session_transaction() as s:
        s["pdf_hash"] = HASH; s["pdf_filename"] = "x.pdf"; s["session_id"] = "sid"; s["user_choices"] = {}
    return c


def test_review_preselects_the_only_lecture_and_the_empty_option_blocks_submit(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    c = _client(mod, _biol_data())
    html = c.get("/review").data.decode()
    sel = re.search(r'<select name="lecture_section"[^>]*>(.*?)</select>', html, re.S).group(1)
    assert '<option value="">' in sel and 'value="none"' not in sel
    assert re.search(r'<option value="0"\s+selected', sel), sel
    assert "Mon" in sel and "Wed" in sel and "9:30" in sel and "10:30" in sel


def test_download_of_a_two_day_lecture_has_both_weekly_series(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    c = _client(mod, _biol_data())
    r = c.post("/review", data={"lecture_section": "0", "lab_section": "none", "tutorial_section": "none"})
    assert r.status_code == 200 and r.mimetype == "text/calendar"
    ics = r.data.decode()
    assert len(re.findall(r"^RRULE:FREQ=WEEKLY;.*BYDAY=MO", ics, re.M)) == 1
    assert len(re.findall(r"^RRULE:FREQ=WEEKLY;.*BYDAY=WE", ics, re.M)) == 1
    starts = re.findall(r"DTSTART;TZID=America/Toronto:(\d{8}T\d{6})", ics)
    assert "20250106T103000" in starts and "20250108T093000" in starts, starts
    # an empty value with a single option (a browser that ignored `required`) still gets the lecture
    r = c.post("/review", data={"lecture_section": "", "lab_section": "none", "tutorial_section": "none"})
    assert len(re.findall(r"^RRULE:", r.data.decode(), re.M)) == 2


# ---------------------------------------------------------------- D23: printed lab slot + rule
def _anatcell_data():
    term = CourseTerm(term_name="Fall/Winter 2025-2026", start_date=date(2025, 9, 4), end_date=date(2026, 4, 9),
                      reading_weeks=[(date(2025, 11, 3), date(2025, 11, 9)), (date(2026, 2, 14), date(2026, 2, 22))])
    lec = SectionOption(section_type="Lecture", section_id="", days_of_week=[1, 3], start_time=time(11, 30), end_time=time(12, 30))
    lab = SectionOption(section_type="Lab", section_id="002", days_of_week=[0], start_time=time(11, 30), end_time=time(13, 20))
    rows = []
    for n in (1, 2):
        rows.append(AssessmentTask(title=f"Term {n} Lab Assignments", type="lab_report", weight_percent=10.0,
                                   due_rule="Day of lab at 11:59pm", rule_anchor="lab", confidence=0.9, needs_review=True,
                                   date_status="rule",
                                   source_evidence=f"Term {n} Lab Assignments | Online via Gradescope | 10% | Day of lab at 11:59pm | 24-hour no late penalty"))
    return ExtractedCourseData(term=term, lecture_sections=[lec], lab_sections=[lab], assessments=rows,
                               course_code="ANATCELL 3309", course_name="Cell Biology")


def test_stated_total_ignores_the_digit_in_term_1():
    from src.app import _STATED_TOTAL
    assert _STATED_TOTAL.search("Term 1 Lab Assignments | 10% | Day of lab at 11:59pm") is None
    assert _STATED_TOTAL.search("Labs (Total = 8)").group(1) == "8"
    assert _STATED_TOTAL.search("LAB: 3hrs/session (weekly); 10 sessions") is not None


def test_day_of_lab_rule_with_a_printed_lab_slot_gives_one_event_per_lab_at_2359(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    c = _client(mod, _anatcell_data())
    html = c.get("/review").data.decode()
    assert "Sep 08, 2025" not in html and "One due event per lab" in html
    r = c.post("/review", data={"lecture_section": "0", "lab_section": "0", "tutorial_section": "none"})
    assert r.status_code == 200 and r.mimetype == "text/calendar"
    ics = r.data.decode()
    t1 = re.findall(r"SUMMARY:ANATCELL 3309: Term 1 Lab Assignment \d+ due\r?\n(?:.*\r?\n)*?DTSTART;TZID=America/Toronto:(\d{8}T\d{6})", ics)
    t2 = re.findall(r"SUMMARY:ANATCELL 3309: Term 2 Lab Assignment \d+ due\r?\n(?:.*\r?\n)*?DTSTART;TZID=America/Toronto:(\d{8}T\d{6})", ics)
    assert 10 <= len(t1) <= 14 and 10 <= len(t2) <= 14, (len(t1), len(t2))
    for s in t1:
        d = datetime.strptime(s, "%Y%m%dT%H%M%S")
        assert d.weekday() == 0 and d.time() == time(23, 59) and d.date() <= date(2025, 12, 31), s
    for s in t2:
        d = datetime.strptime(s, "%Y%m%dT%H%M%S")
        assert d.weekday() == 0 and d.time() == time(23, 59) and d.date() >= date(2026, 1, 1), s
    assert "Term 1 Lab Assignments due" not in ics


def test_upload_does_not_resolve_a_rule_to_a_placeholder_date(monkeypatch, tmp_path):
    """The stored row keeps its rule; the first lab's start is never shown as the due date."""
    import io
    mod = _app(monkeypatch, tmp_path)

    class FakeExtractor:
        def __init__(self, path, original_filename=None):
            pass

        def extract_all(self):
            return _anatcell_data()

    monkeypatch.setattr(mod, "PDFExtractor", FakeExtractor)
    c = mod.app.test_client()
    r = c.post("/upload", data={"pdf_file": (io.BytesIO(b"%PDF-1.4 fake"), "outline.pdf")}, content_type="multipart/form-data")
    assert r.status_code == 302
    html = c.get("/review").data.decode()
    assert "Sep 08, 2025" not in html
    assert "One due event per lab" in html


# ---------------------------------------------------------------- D25: Fall/Winter header
def test_fall_winter_header_collapses_to_fall_when_every_date_is_in_the_fall():
    text = ("Department of Mechanical and Materials Engineering\nMSE 2214 Materials Science\nCourse Outline Fall/Winter 2025\n" + MSE_TEXT)
    data = build([(1, text)], [MSE_TABLE], "MSE-2214_Fall-2025-Website-Version.pdf")
    assert data.term.term_name == "Fall 2025"
    assert data.term.start_date == date(2025, 9, 4) and data.term.end_date == date(2025, 12, 9)
    assert any("Fall/Winter" in n for n in data.notes)


# ---------------------------------------------------------------- D18 residue: in-class quiz time
def test_in_class_quiz_takes_the_lecture_time():
    text = ("Physiology 3140A Fall 2025\nLectures: MWF 9:30-10:20 am\n"
            "Quiz 1 10% Oct 1 in class\nQuiz 2 10% Nov 12 in class\nFinal Exam 80% Scheduled by the Registrar\n")
    data = build([(1, text)], [], "phys3140a.pdf")
    q = {a.title: a for a in data.assessments}
    assert q["Quiz 1"].due_datetime == datetime(2025, 10, 1, 9, 30), q["Quiz 1"]
