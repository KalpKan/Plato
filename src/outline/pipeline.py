"""Turn a course-outline PDF into ExtractedCourseData using the outline.* modules."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import pdfplumber

from ..models import AssessmentTask, CourseTerm, ExtractedCourseData, SectionOption
from .assessments import extract_assessments
from .course import extract_course
from .schedule import extract_slots_and_notes
from .term import extract_term

MAX_PAGES = 30


class PasswordProtected(ValueError):
    pass


class NoTextLayer(ValueError):
    pass


def _needs_password(pdf_path: Path) -> bool:
    """PyMuPDF answers this reliably; pdfminer only raises a bare PdfminerException."""
    try:
        import fitz  # PyMuPDF
        with fitz.open(str(pdf_path)) as doc:
            return bool(doc.needs_pass)
    except Exception:
        return False


def load_pages(pdf_path: Path) -> Tuple[List[Tuple[int, str]], List[List[List[Optional[str]]]], int, List[int]]:
    """(pages_text, tables, page_count, image_pages). Raises PasswordProtected / NoTextLayer."""
    pages_text: List[Tuple[int, str]] = []
    tables: List[List[List[Optional[str]]]] = []
    image_pages: List[int] = []
    if _needs_password(pdf_path):
        raise PasswordProtected("This PDF is password-protected")
    try:
        pdf = pdfplumber.open(str(pdf_path))
    except Exception as e:  # pdfminer raises several types for encrypted files
        msg = str(e).lower()
        if "password" in msg or "encrypt" in msg or type(e).__name__ in ("PDFPasswordIncorrect", "PDFEncryptionError"):
            raise PasswordProtected("This PDF is password-protected") from e
        raise
    with pdf:
        if getattr(pdf, "metadata", None) is not None and pdf.doc.is_extractable is False:
            raise PasswordProtected("This PDF does not allow text extraction")
        page_count = len(pdf.pages)
        for page_num, page in enumerate(pdf.pages[:MAX_PAGES], start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text.strip():
                pages_text.append((page_num, text))
            else:
                image_pages.append(page_num)
            try:
                for t in page.extract_tables():
                    if t:
                        tables.append(t)
            except Exception:
                pass
    if not pages_text:
        raise NoTextLayer("This PDF has no text layer")
    return pages_text, tables, page_count, image_pages


def parse_outline(pdf_path: Path, original_filename: Optional[str] = None) -> ExtractedCourseData:
    pages_text, tables, page_count, image_pages = load_pages(Path(pdf_path))
    filename = original_filename or Path(pdf_path).name
    return build(pages_text, tables, filename, page_count, image_pages)


_IN_CLASS = re.compile(r"\bin[- ]class\b|\bduring\s+(?:the\s+)?(?:class|lecture)|\bin\s+lecture\b", re.I)


def _rule_anchor(rule: Optional[str]) -> Optional[str]:
    """'Lab Report due 24hrs after each Lab Session' -> 'lab'; 'end of each tutorial' -> 'tutorial'."""
    low = (rule or "").lower()
    for anchor, pat in (("lab", r"\blab"), ("tutorial", r"\btutorial"), ("lecture", r"\blecture|\bclass\b")):
        if re.search(pat, low):
            return anchor
    return None


def build(pages_text: Sequence[Tuple[int, str]], tables, filename: str, page_count: int = 0,
          image_pages: Sequence[int] = ()) -> ExtractedCourseData:
    notes: List[str] = []
    code, name = extract_course(pages_text, filename)
    term_info = extract_term(pages_text, filename, course_code=code)
    years = [d.year for d in (term_info.start, term_info.end) if d] or list(term_info.year_hints)
    slots, slot_notes = extract_slots_and_notes(pages_text, tables, term_year_hint=years)
    notes += slot_notes
    items, a_notes = extract_assessments(pages_text, tables, term_info)
    notes += a_notes

    term = CourseTerm(term_name=term_info.name, start_date=term_info.start, end_date=term_info.end,
                      exam_periods=list(term_info.exam_periods), reading_weeks=list(term_info.reading_weeks),
                      source=term_info.source)
    if term_info.source == "sessional":
        notes.append(f"The outline names the term ({term_info.name}) but not its dates; Western's sessional "
                     f"dates were used ({term.start_date:%b %-d} – {term.end_date:%b %-d, %Y}). Check them if your course runs on a different schedule.")
    elif term_info.source == "estimated":
        notes.append(f"The term dates for {term_info.name} are estimated from Western's usual pattern; confirm the first and last day of classes.")
    elif term_info.source == "none":
        notes.append("The outline does not say which term this is. Enter the first and last day of classes before downloading, "
                     "otherwise weekly events cannot be generated.")

    lectures: List[SectionOption] = []
    labs: List[SectionOption] = []
    tutorials: List[SectionOption] = []
    for s in slots:
        so = SectionOption(section_type=s.kind.capitalize(), section_id=s.section_id, days_of_week=list(s.days),
                           start_time=s.start, end_time=s.end, location=s.location, note=s.note)
        {"lecture": lectures, "lab": labs, "tutorial": tutorials}[s.kind].append(so)
    if not slots:
        notes.append("No lecture, lab or tutorial times were found in the outline (many Western outlines leave them to "
                     "draftmyschedule.uwo.ca). Add your slots with \"Add Section\" if you want weekly events.")

    assessments: List[AssessmentTask] = []
    for a in items:
        d = a.date
        due = None
        end = None
        anchor = _rule_anchor(d.rule) if d.status == "rule" else None
        note = d.note
        if d.status == "rule":
            if anchor:
                have = any(s.kind == anchor for s in slots)
                note = (f"Relative rule: {d.rule}. " + ("One due event per " + anchor + " is generated from your " + anchor + " slot."
                        if have else f"Add your {anchor} slot with \"Add Section\" and you get one due event per {anchor}."))
            else:
                note = f"Relative rule: {d.rule}. Set the dates by hand (the outline ties them to something the calendar cannot see)."
        if d.status == "exact" and d.date:
            t = d.time
            if t is None and a.kind in ("midterm", "test") and _IN_CLASS.search(f"{a.evidence} {d.raw} {d.note}"):
                # "Mid-term Exam (In-class)": it sits in the lecture slot, not at 23:59 (D18)
                lecture_starts = {s.start for s in slots if s.kind == "lecture" and s.start}
                if len(lecture_starts) == 1:
                    t = lecture_starts.pop()
                    lec = next(s for s in slots if s.kind == "lecture" and s.start == t)
                    if lec.end:
                        end = datetime.combine(d.date, lec.end)
                    note = (note + " " if note else "") + "In class: the time is your lecture slot's."
            due = datetime.combine(d.date, t) if t else datetime.combine(d.date, datetime.min.time().replace(hour=23, minute=59))
            if d.end_time:
                end = datetime.combine(d.date, d.end_time)
        elif d.status == "recurring" and d.dates:
            first = d.dates[0]
            due = datetime.combine(first, d.time) if d.time else datetime.combine(first, datetime.min.time().replace(hour=23, minute=59))
        task = AssessmentTask(
            title=a.title,
            type=a.kind,
            weight_percent=a.weight,
            due_datetime=due,
            due_rule=d.rule if d.status == "rule" else None,
            rule_anchor=anchor,
            confidence=a.confidence,
            source_evidence=a.evidence,
            needs_review=(d.status not in ("exact", "recurring")) or a.weight is None,
            date_status=d.status,
            date_note=note,
            date_window=d.window,
            dates=list(d.dates) if d.status == "recurring" else [],
            end_datetime=end,
            is_bonus=a.is_bonus,
        )
        assessments.append(task)

    if image_pages:
        which = ", ".join(str(p) for p in image_pages[:5])
        notes.append(f"Page {which} of the PDF is an image with no text layer, so anything printed only there "
                     f"(often the course code, term and class times on page 1) could not be read. Check those fields.")
    if not assessments:
        notes.append("No assessment table or list with weights was found. Add each assessment with \"Add Assessment\".")

    return ExtractedCourseData(
        term=term,
        lecture_sections=lectures,
        lab_sections=labs,
        tutorial_sections=tutorials,
        assessments=assessments,
        course_code=code,
        course_name=name,
        notes=notes,
        text_pages=len(pages_text),
        image_pages=list(image_pages),
    )
