"""The review -> calendar flow must work with no server-side state between requests."""
import importlib
import sys
from datetime import date, datetime, time

from src.models import AssessmentTask, CourseTerm, ExtractedCourseData, SectionOption

HASH = "h" * 64


def _app(monkeypatch, tmp_path):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("PLATO_TMP_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))  # SQLite cache lands under tmp
    monkeypatch.delenv("DATABASE_URL", raising=False)
    sys.modules.pop("src.app", None)
    return importlib.import_module("src.app")


def _data():
    term = CourseTerm(term_name="Fall 2026", start_date=date(2026, 9, 8),
                      end_date=date(2026, 12, 8), timezone="America/Toronto")
    lec = SectionOption(section_type="lecture", section_id="001", days_of_week=["Mon", "Wed"],
                        start_time=time(10, 30), end_time=time(11, 30), location="NCB 101")
    assessments = [
        AssessmentTask(title=f"Quiz {i}", type="quiz", weight_percent=10.0,
                       due_datetime=datetime(2026, 10, i + 1, 23, 59), confidence=0.9)
        for i in range(3)
    ]
    return ExtractedCourseData(term=term, lecture_sections=[lec], lab_sections=[],
                               assessments=assessments, course_code="TEST 1000",
                               course_name="Testing")


def _client_with_pdf(mod):
    mod.get_cache().store_extraction(HASH, _data())
    c = mod.app.test_client()
    with c.session_transaction() as s:
        s["pdf_hash"] = HASH
        s["pdf_filename"] = "x.pdf"
        s["session_id"] = "sid"
        s["user_choices"] = {}
    return c


def test_review_get_renders_from_db(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    c = _client_with_pdf(mod)
    r = c.get("/review")
    assert r.status_code == 200
    assert b"Testing" in r.data and b"Fall 2026" in r.data


def test_review_post_streams_ics_and_download_regenerates(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    c = _client_with_pdf(mod)
    r = c.post("/review", data={"lecture_section": "0", "lab_section": "none"})
    assert r.status_code == 200
    assert r.mimetype == "text/calendar"
    assert r.headers["Content-Disposition"].startswith("attachment;")
    assert r.data.count(b"BEGIN:VEVENT") >= 3
    fname = r.headers["Content-Disposition"].split("filename=")[1].strip('"')
    assert fname.endswith(".ics")
    r2 = c.get(f"/download/{fname}")
    assert r2.status_code == 200
    assert r2.data.count(b"BEGIN:VEVENT") >= 3


def test_session_cookie_stays_small(monkeypatch, tmp_path):
    """Browsers drop cookies over ~4 KB; extracted data must not ride in the cookie."""
    mod = _app(monkeypatch, tmp_path)
    c = _client_with_pdf(mod)
    c.post("/api/update-field", json={"field_type": "course_name", "value": "New name"})
    with c.session_transaction() as s:
        assert "extracted_data" not in s
    # the edit lands in this visitor's copy; the shared parser output is untouched (D6)
    assert mod.get_cache().lookup_extraction(mod.visitor_key(HASH, "sid")).course_name == "New name"
    assert mod.get_cache().lookup_extraction(HASH).course_name == "Testing"


def test_review_get_without_hash_redirects(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    r = mod.app.test_client().get("/review")
    assert r.status_code == 302


def test_health_without_db(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    r = mod.app.test_client().get("/api/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True and body["db"] == "ok"


def test_review_post_keeps_custom_lead_time_mapping(monkeypatch, tmp_path):
    """The weight-range -> days mapping the user set on the review page must survive
    the /review POST (it is used to build the .ics) and still be there for /download."""
    mod = _app(monkeypatch, tmp_path)
    c = _client_with_pdf(mod)
    mapping = {"0-10": 2}
    with c.session_transaction() as s:
        s["user_choices"] = {"custom_lead_time_mapping": mapping, "lead_time_overrides": {"Quiz 0": 5}}
    captured = {}
    real_build = mod.build_calendar

    def spy(extracted, selections, overrides, custom_mapping, pdf_hash):
        captured["mapping"] = custom_mapping
        captured["overrides"] = overrides
        return real_build(extracted, selections, overrides, custom_mapping, pdf_hash)

    monkeypatch.setattr(mod, "build_calendar", spy)
    r = c.post("/review", data={"lecture_section": "0", "lab_section": "none"})
    assert r.status_code == 200 and r.mimetype == "text/calendar"
    assert captured["mapping"] == mapping
    assert captured["overrides"] == {"Quiz 0": 5}
    with c.session_transaction() as s:
        assert s["user_choices"]["custom_lead_time_mapping"] == mapping
        assert s["user_choices"]["lead_time_overrides"] == {"Quiz 0": 5}


def test_download_before_review_redirects_to_review(monkeypatch, tmp_path):
    """Right after upload there is no chosen section yet; /download must not hand out
    a calendar with no lecture events, it must send the user back to /review."""
    mod = _app(monkeypatch, tmp_path)
    c = _client_with_pdf(mod)  # user_choices == {}
    r = c.get("/download/x.ics")
    assert r.status_code == 302
    assert r.headers["Location"].endswith("/review")


def test_upload_uses_unique_tmp_name_and_cleans_up(monkeypatch, tmp_path):
    """Two concurrent uploads named outline.pdf must not share a path, and nothing
    may be left behind in /tmp after the request."""
    import io
    mod = _app(monkeypatch, tmp_path)
    paths = []

    class FakeExtractor:
        def __init__(self, path, original_filename=None):
            paths.append(str(path))
            assert path.exists()
            assert original_filename == "outline.pdf"

        def extract_all(self):
            return _data()

    monkeypatch.setattr(mod, "PDFExtractor", FakeExtractor)
    c = mod.app.test_client()
    for content in (b"%PDF-1.4 fake one", b"%PDF-1.4 fake two"):  # same name, different PDFs
        r = c.post("/upload", data={"pdf_file": (io.BytesIO(content), "outline.pdf")},
                   content_type="multipart/form-data")
        assert r.status_code == 302
    assert len(paths) == 2 and paths[0] != paths[1]
    assert all(p.endswith(".pdf") for p in paths)
    assert list(mod.upload_dir().iterdir()) == []


def test_edit_routes_store_extraction_once(monkeypatch, tmp_path):
    """Each edit must hit the database once, not twice."""
    mod = _app(monkeypatch, tmp_path)
    c = _client_with_pdf(mod)
    cache = mod.get_cache()
    calls = []
    real = cache.store_extraction
    monkeypatch.setattr(cache, "store_extraction", lambda h, d: calls.append(h) or real(h, d))

    r = c.post("/api/update-field", json={"field_type": "course_name", "value": "N"})
    assert r.status_code == 200 and len(calls) == 1
    calls.clear()
    r = c.post("/api/add-assessment", json={"title": "Final", "type": "exam", "weight_percent": 30,
                                            "due_date": "2026-12-01", "due_time": "09:00"})
    assert r.status_code == 200, r.data
    assert len(calls) == 1
    calls.clear()
    r = c.post("/api/remove-assessment", json={"assessment_index": 0})
    assert r.status_code == 200, r.data
    assert len(calls) == 1


def _lab_rule_data():
    term = CourseTerm(term_name="Fall 2026", start_date=date(2026, 9, 8), end_date=date(2026, 12, 8),
                      reading_weeks=[(date(2026, 11, 2), date(2026, 11, 8))], timezone="America/Toronto")
    lec = SectionOption(section_type="lecture", section_id="001", days_of_week=[4],
                        start_time=time(13, 30), end_time=time(14, 30), location="HSB-236")
    labs = AssessmentTask(title="Labs (Total = 8)", type="lab_report", weight_percent=50.0,
                          due_rule="Lab Report due 24hrs after each Lab Session", rule_anchor="lab",
                          date_status="rule", date_note="Relative rule: Lab Report due 24hrs after each Lab Session",
                          confidence=0.9, needs_review=True)
    proj = AssessmentTask(title="PCB Project", type="project", weight_percent=20.0,
                          due_datetime=datetime(2026, 11, 29, 23, 59), confidence=0.9)
    return ExtractedCourseData(term=term, lecture_sections=[lec], lab_sections=[], assessments=[labs, proj],
                               course_code="ECE 2240A", course_name="Electronics Laboratory I")


def test_lab_rule_without_a_lab_slot_tells_the_visitor_to_add_one(monkeypatch, tmp_path):
    """D16: the review page must say the lab slot is needed, and the .ics must not silently drop the row."""
    mod = _app(monkeypatch, tmp_path)
    mod.get_cache().store_extraction(HASH, _lab_rule_data())
    c = mod.app.test_client()
    with c.session_transaction() as s:
        s["pdf_hash"] = HASH; s["pdf_filename"] = "x.pdf"; s["session_id"] = "sid"; s["user_choices"] = {}
    r = c.get("/review")
    assert r.status_code == 200
    assert b"Add Section" in r.data and b"one due event per lab" in r.data.lower().replace(b"\xe2\x80\x99", b"'") or b"per lab" in r.data.lower()


def test_lab_rule_with_a_manual_lab_slot_gives_one_due_event_per_lab(monkeypatch, tmp_path):
    """D16: Monday lab 14:30-17:30 -> lab report due Tuesdays 14:30, capped at the stated 8, none in reading week."""
    mod = _app(monkeypatch, tmp_path)
    mod.get_cache().store_extraction(HASH, _lab_rule_data())
    c = mod.app.test_client()
    with c.session_transaction() as s:
        s["pdf_hash"] = HASH; s["pdf_filename"] = "x.pdf"; s["session_id"] = "sid"; s["user_choices"] = {}
    r = c.post("/review", data={
        "lecture_section": "0", "lab_section": "manual_0", "tutorial_section": "none",
        "manual_lab_sections": '[{"days":[0],"start_time":"14:30","end_time":"17:30","location":"TEB-1"}]'})
    assert r.status_code == 200 and r.mimetype == "text/calendar"
    ics = r.data.decode()
    import re
    due = re.findall(r"SUMMARY:ECE 2240A: (Lab report \d+) due\r?\n", ics)
    assert len(due) == 8, ics
    starts = re.findall(r"SUMMARY:ECE 2240A: Lab report \d+ due\r?\n(?:.*\r?\n)*?DTSTART;TZID=America/Toronto:(\d{8}T\d{6})", ics)
    assert len(starts) == 8
    for s_ in starts:
        d = datetime.strptime(s_, "%Y%m%dT%H%M%S")
        assert d.weekday() == 1 and d.time() == time(14, 30), s_
        assert not (date(2026, 11, 2) <= d.date() <= date(2026, 11, 9)), "lab report in reading week"
    assert "Labs (Total = 8) due" not in ics


def test_update_field_returns_completeness_and_row_state(monkeypatch, tmp_path):
    """D19: the review page re-renders its tiles and badges from the update response."""
    mod = _app(monkeypatch, tmp_path)
    c = _client_with_pdf(mod)
    r = c.post("/api/update-field", json={"field_type": "assessment_weight", "assessment_index": 0, "value": "35"})
    body = r.get_json()
    assert body["success"] and body["completeness"]["total_weight"] == 55 and body["completeness"]["assessments_undated"] == 0
    assert body["row"]["weight"] == 35 and body["row"]["has_date"] is True
    r = c.post("/api/update-field", json={"field_type": "assessment_due_date", "assessment_index": 1, "value": ""})
    body = r.get_json()
    assert body["completeness"]["assessments_undated"] == 1 and body["row"]["has_date"] is False
    r = c.post("/api/update-field", json={"field_type": "assessment_due_date", "assessment_index": 1, "value": "2026-04-20T09:00"})
    body = r.get_json()
    assert body["completeness"]["assessments_undated"] == 0 and body["row"]["due_display"] == "Apr 20, 2026 9:00 AM"
    html = c.get("/review").data.decode()
    assert 'data-tile="undated"' in html and "badge-needs-date" not in html
