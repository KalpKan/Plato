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
    assert mod.get_cache().lookup_extraction(HASH).course_name == "New name"


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
