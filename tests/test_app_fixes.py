"""Round-1 audit defects on the Flask layer: D6 per-visitor edits, D7 manual mode, D8 edge files, review page reasons."""
import importlib
import io
import sys
from datetime import date, datetime, time
from pathlib import Path

import pytest

from src.models import AssessmentTask, CourseTerm, ExtractedCourseData, SectionOption

HASH = "h" * 64
EDGE = Path.home() / "projects/plato-corpus/edge"


def _app(monkeypatch, tmp_path):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("PLATO_TMP_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    sys.modules.pop("src.app", None)
    return importlib.import_module("src.app")


def _data():
    term = CourseTerm(term_name="Winter 2026", start_date=date(2026, 1, 5), end_date=date(2026, 4, 9),
                      exam_periods=[(date(2026, 4, 12), date(2026, 4, 30))])
    lec = SectionOption(section_type="Lecture", section_id="", days_of_week=[3], start_time=time(10, 30), end_time=time(12, 20), location="SSC-2050")
    tut = SectionOption(section_type="Tutorial", section_id="", days_of_week=[2], start_time=time(17, 30), end_time=time(18, 20), location="Zoom")
    assessments = [
        AssessmentTask(title="Tracker 1", type="assignment", weight_percent=5.0, due_datetime=datetime(2026, 1, 16, 23, 59), confidence=0.9),
        AssessmentTask(title="Final Exam", type="final", weight_percent=40.0, date_status="registrar",
                       date_note="Outline says: scheduled by the Registrar (exam period Apr 12 – Apr 30, 2026)", needs_review=True),
    ]
    return ExtractedCourseData(term=term, lecture_sections=[lec], lab_sections=[], tutorial_sections=[tut],
                               assessments=assessments, course_code="KIN 2000", course_name="Physical Activity and Health",
                               notes=["Page 1 of the PDF is an image with no text layer, so the course code may be missing."])


def _client(mod, sid):
    c = mod.app.test_client()
    with c.session_transaction() as s:
        s["pdf_hash"] = HASH
        s["pdf_filename"] = "x.pdf"
        s["session_id"] = sid
        s["user_choices"] = {}
    return c


# ---------------------------------------------------------------- D6
def test_edits_are_per_visitor(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    mod.get_cache().store_extraction(HASH, _data())
    a, b = _client(mod, "sid-a"), _client(mod, "sid-b")
    r = a.post("/api/update-field", json={"field_type": "assessment_title", "assessment_index": 0, "value": "EDITED BY VISITOR A"})
    assert r.get_json()["success"]
    assert b"EDITED BY VISITOR A" in a.get("/review").data
    assert b"EDITED BY VISITOR A" not in b.get("/review").data
    # the shared parser output is untouched
    assert mod.get_cache().lookup_extraction(HASH).assessments[0].title == "Tracker 1"


def test_force_refresh_discards_a_visitors_edits(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    mod.get_cache().store_extraction(HASH, _data())
    a = _client(mod, "sid-a")
    a.post("/api/update-field", json={"field_type": "assessment_title", "assessment_index": 0, "value": "EDITED"})
    mod.discard_visitor_copy(HASH, "sid-a")
    assert b"EDITED" not in a.get("/review").data


# ---------------------------------------------------------------- D7
def test_manual_mode_builds_a_review_page(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    c = mod.app.test_client()
    assert c.get("/manual").status_code == 200
    assert b"/manual" in c.get("/").data
    r = c.post("/manual", data={
        "course_code": "TEST 1000", "course_name": "Testing", "term_name": "Fall 2026",
        "term_start": "2026-09-08", "term_end": "2026-12-08",
        "assessment_title[]": ["Quiz 1", "Final"], "assessment_type[]": ["quiz", "final"],
        "assessment_due[]": ["2026-10-01T10:00", ""], "assessment_weight[]": ["10", "50"],
    })
    assert r.status_code == 302 and r.headers["Location"].endswith("/review")
    page = c.get("/review")
    assert page.status_code == 200
    assert b"Quiz 1" in page.data and b"TEST 1000" in page.data
    assert b"not yet fully implemented" not in page.data
    r2 = c.post("/review", data={"lecture_section": "none", "lab_section": "none"})
    assert r2.mimetype == "text/calendar"
    assert r2.data.count(b"SUMMARY:TEST 1000: Quiz 1 due") == 1
    assert b"Final" not in r2.data  # the undated Final gets no event


# ---------------------------------------------------------------- D8
def _pdf_bytes(kind: str) -> bytes:
    import fitz  # PyMuPDF
    doc = fitz.open()
    page = doc.new_page()
    if kind == "text":
        page.insert_text((72, 72), "KIN 2000 Physical Activity and Health\nWinter 2026\nEvaluation\nQuiz 1 10% Jan 16\nFinal Exam 90% Registrar")
    elif kind == "image":
        page.draw_rect(fitz.Rect(50, 50, 300, 300), color=(0, 0, 0), fill=(0.5, 0.5, 0.5))
    if kind == "password":
        page.insert_text((72, 72), "secret text")
        return doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="secret")
    return doc.tobytes()


def _upload(c, data: bytes, name: str):
    r = c.post("/upload", data={"pdf_file": (io.BytesIO(data), name)}, content_type="multipart/form-data")
    return r.status_code, r.headers.get("Location", ""), c.get("/").data.decode()


def test_blank_pdf_gets_a_plain_message(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    code, loc, page = _upload(mod.app.test_client(), _pdf_bytes("blank"), "blank.pdf")
    assert code == 302 and loc.endswith("/")
    assert "no text" in page.lower() and "manual" in page.lower()


def test_image_only_pdf_gets_a_plain_message(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    code, loc, page = _upload(mod.app.test_client(), _pdf_bytes("image"), "scan.pdf")
    assert code == 302 and loc.endswith("/")
    assert "no text" in page.lower() or "scanned" in page.lower()


def test_password_pdf_gets_a_plain_message(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    code, loc, page = _upload(mod.app.test_client(), _pdf_bytes("password"), "locked.pdf")
    assert code == 302 and loc.endswith("/")
    assert "password" in page.lower()


def test_non_pdf_gets_a_plain_message(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    code, loc, page = _upload(mod.app.test_client(), b"hello", "notes.txt")
    assert code == 302 and "PDF" in page


def test_oversize_upload_is_refused_with_the_limit_in_mb(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    big = b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024)
    c = mod.app.test_client()
    r = c.post("/upload", data={"pdf_file": (io.BytesIO(big), "big.pdf")}, content_type="multipart/form-data")
    assert r.status_code in (302, 413)
    page = c.get("/").data.decode()
    assert "4 MB" in page or "4.5 MB" in page


def test_text_pdf_reaches_review(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    code, loc, _ = _upload(mod.app.test_client(), _pdf_bytes("text"), "outline.pdf")
    assert code == 302 and loc.endswith("/review")


@pytest.mark.skipif(not EDGE.exists(), reason="synthetic edge files not on this machine")
def test_real_edge_files(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    for name, expect in [("scanned-no-text-layer.pdf", "no text"), ("password-protected.pdf", "password"),
                         ("blank-one-page.pdf", "no text"), ("not-a-pdf.txt", "PDF")]:
        c = mod.app.test_client()
        code, loc, page = _upload(c, (EDGE / name).read_bytes(), name)
        assert loc.endswith("/"), name
        assert expect.lower() in page.lower(), name


# ------------------------------------------------------- review page copy
def test_review_page_explains_undated_rows_and_notes(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    mod.get_cache().store_extraction(HASH, _data())
    page = _client(mod, "sid").get("/review").data.decode()
    assert "scheduled by the Registrar" in page
    assert "no text layer" in page
    assert 'data-field-type="course_code"' in page
    assert "tutorial_section" in page


def test_review_page_total_flags_over_100(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    d = _data()
    d.assessments.append(AssessmentTask(title="Extra", type="assignment", weight_percent=62.0, due_datetime=datetime(2026, 2, 1)))
    mod.get_cache().store_extraction(HASH, d)
    page = _client(mod, "sid").get("/review").data.decode()
    assert "completeness-over" in page


def test_download_includes_tutorial_and_no_invented_dates(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    mod.get_cache().store_extraction(HASH, _data())
    c = _client(mod, "sid")
    r = c.post("/review", data={"lecture_section": "0", "lab_section": "none", "tutorial_section": "0"})
    assert r.mimetype == "text/calendar"
    body = r.data.decode()
    assert "KIN 2000 Tutorial" in body and "KIN 2000 Lecture" in body
    assert body.count("SUMMARY:KIN 2000: Tracker 1 due") == 1
    assert "Final Exam" not in body  # undated: no event at all, not even a placeholder
    assert body.count("BEGIN:VEVENT") == 4  # lecture, tutorial, Tracker 1 due, Tracker 1 study start
