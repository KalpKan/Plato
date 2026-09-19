"""
Data models for course outline to iCalendar converter.

This module defines all the data structures used throughout the application.
All models use Python dataclasses, which provide a simple way to define
classes that mainly store data. Dataclasses automatically generate common
methods like __init__ and __repr__, making the code cleaner and easier to read.

These models represent:
- Course terms (semesters)
- Section schedules (lectures and labs)
- Assessment tasks (assignments, exams, etc.)
- Study plan items
- User selections
- Cache entries
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import List, Optional, Tuple, Dict


@dataclass
class CourseTerm:
    """Represents the academic term/semester for the course.
    
    This class stores information about when the course takes place.
    It includes the term name (like "Fall 2026"), the start and end dates,
    and the timezone (defaults to America/Toronto for Western University).
    """
    term_name: str              # e.g., "Fall 2026", "Winter 2027"
    start_date: Optional[date]  # First day of classes, or None when the outline does not say
    end_date: Optional[date]    # Last day of classes, or None when the outline does not say
    timezone: str = "America/Toronto"  # Timezone for the course (Western University uses Toronto time)
    exam_periods: List[Tuple[date, date]] = field(default_factory=list)   # Registrar exam windows
    reading_weeks: List[Tuple[date, date]] = field(default_factory=list)
    source: str = "outline"     # outline | sessional | estimated | manual | none (how the dates were found)


@dataclass
class SectionOption:
    """Represents a lecture or lab section with its schedule.
    
    A section is a specific time slot for a course. For example, a course
    might have Lecture Section 001 on Monday/Wednesday/Friday from 10:30-11:30 AM.
    This class stores all that information.
    """
    section_type: str           # "Lecture", "Lab" or "Tutorial"
    section_id: str             # Section number like "001", "002", or "" if not specified
    days_of_week: List[int]     # Days when this section meets: 0=Monday, 1=Tuesday, ..., 6=Sunday
    start_time: Optional[time]  # When the section starts, or None when the outline gives no clock time
    end_time: Optional[time]    # When the section ends, or None when the outline gives no clock time
    location: Optional[str] = None  # Room/building where it meets (e.g., "UC 202"), or None if unknown
    date_range: Optional[Tuple[date, date]] = None  # Custom date range if different from term dates
    note: str = ""              # e.g. "the outline gives no clock time"


@dataclass
class AssessmentTask:
    """Represents an assessment item (assignment, quiz, exam, etc.).
    
    This class stores information about any graded work in the course.
    It can have either an absolute due date (due_datetime) or a relative rule
    (due_rule) that needs to be resolved later. The confidence score indicates
    how certain we are that the extracted information is correct.
    """
    title: str                  # Assessment name/title (e.g., "Assignment 1", "Final Exam")
    type: str                   # Type of assessment: "assignment", "lab_report", "quiz", "midterm", "final", "project", "other"
    weight_percent: Optional[float] = None  # How much this assessment is worth (e.g., 15.0 means 15% of final grade)
    due_datetime: Optional[datetime] = None  # When it's due (absolute date and time), or None if we have a rule instead
    due_rule: Optional[str] = None  # Relative rule text (e.g., "24 hours after lab") - needs to be resolved to a datetime
    rule_anchor: Optional[str] = None  # What the rule is based on: "lab", "tutorial", or "lecture"
    confidence: float = 0.0     # How confident we are in the extraction (0.0 = not confident, 1.0 = very confident)
    source_evidence: Optional[str] = None  # Where we found this info (page number and text snippet for debugging)
    needs_review: bool = False  # True if the information is ambiguous or missing critical data (user should review)
    date_status: str = "exact"  # exact | registrar | tba | range | rule | recurring | missing | manual
    date_note: str = ""         # one line for the review page ("Outline says: scheduled by the Registrar")
    date_window: Optional[Tuple[date, date]] = None  # the window a registrar/range item falls in
    dates: List[date] = field(default_factory=list)  # every occurrence of a recurring item (weekly quizzes)
    end_datetime: Optional[datetime] = None  # when the outline gives an end time (exam 6-8 PM)
    is_bonus: bool = False      # optional / bonus rows are shown but not counted in the total


@dataclass
class StudyPlanItem:
    """Represents a study plan event for an assessment."""
    task_id: str                # Reference to AssessmentTask (title or unique ID)
    start_studying_datetime: datetime  # When to start studying
    due_datetime: datetime      # Assessment due date/time


@dataclass
class ExtractedCourseData:
    """Container for all extracted data from PDF."""
    term: CourseTerm
    lecture_sections: List[SectionOption]
    lab_sections: List[SectionOption]
    assessments: List[AssessmentTask]
    course_code: Optional[str] = None  # e.g., "CS 101"
    course_name: Optional[str] = None  # e.g., "Introduction to Computer Science"
    tutorial_sections: List[SectionOption] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)   # plain-language things the parser could not do
    text_pages: int = 0         # pages with a text layer (0 = scanned / blank PDF)
    image_pages: List[int] = field(default_factory=list)  # pages with no text layer (e.g. a scanned page 1)

    def all_sections(self) -> List[SectionOption]:
        return list(self.lecture_sections) + list(self.lab_sections) + list(self.tutorial_sections)


@dataclass
class UserSelections:
    """Stores user choices for section selection."""
    selected_lecture_section: Optional[SectionOption] = None
    selected_lab_section: Optional[SectionOption] = None
    assessment_overrides: Dict[str, AssessmentTask] = field(default_factory=dict)  # User-corrected assessments


@dataclass
class CacheEntry:
    """Represents a cached result."""
    pdf_hash: str               # SHA-256 hash of PDF
    extracted_data: ExtractedCourseData
    user_selections: UserSelections
    generated_ics: str          # .ics file content as string
    timestamp: datetime         # When cached


# Serialization helpers for JSON conversion

def serialize_date(d: date) -> str:
    """Convert date to ISO format string."""
    return d.isoformat()


def deserialize_date(s: str) -> date:
    """Convert ISO format string to date."""
    return date.fromisoformat(s)


def serialize_datetime(dt: datetime) -> str:
    """Convert datetime to ISO format string."""
    return dt.isoformat()


def deserialize_datetime(s: str) -> datetime:
    """Convert ISO format string to datetime."""
    return datetime.fromisoformat(s)


def serialize_time(t: time) -> str:
    """Convert time to HH:MM:SS string."""
    return t.isoformat()


def deserialize_time(s: str) -> time:
    """Convert HH:MM:SS string to time."""
    return time.fromisoformat(s)




# ---------------------------------------------------------------------------
# One serializer for the caches, the session and the API (was three copies)
# ---------------------------------------------------------------------------

def _opt(fn, v):
    return fn(v) if v is not None else None


def _pairs(pairs):
    return [[serialize_date(a), serialize_date(b)] for a, b in (pairs or []) if a and b]


def _unpairs(pairs):
    return [(deserialize_date(a), deserialize_date(b)) for a, b in (pairs or [])]


def term_to_dict(t: CourseTerm) -> dict:
    return {
        "term_name": t.term_name,
        "start_date": _opt(serialize_date, t.start_date),
        "end_date": _opt(serialize_date, t.end_date),
        "timezone": t.timezone,
        "exam_periods": _pairs(t.exam_periods),
        "reading_weeks": _pairs(t.reading_weeks),
        "source": t.source,
    }


def term_from_dict(d: dict) -> CourseTerm:
    return CourseTerm(
        term_name=d.get("term_name") or "Unknown",
        start_date=_opt(deserialize_date, d.get("start_date")),
        end_date=_opt(deserialize_date, d.get("end_date")),
        timezone=d.get("timezone", "America/Toronto"),
        exam_periods=_unpairs(d.get("exam_periods")),
        reading_weeks=_unpairs(d.get("reading_weeks")),
        source=d.get("source", "outline"),
    )


def section_to_dict(s: SectionOption) -> dict:
    out = {
        "section_type": s.section_type,
        "section_id": s.section_id,
        "days_of_week": list(s.days_of_week),
        "start_time": _opt(serialize_time, s.start_time),
        "end_time": _opt(serialize_time, s.end_time),
        "location": s.location,
        "note": s.note,
    }
    if s.date_range:
        out["date_range"] = [serialize_date(s.date_range[0]), serialize_date(s.date_range[1])]
    return out


def section_from_dict(d: dict) -> SectionOption:
    dr = d.get("date_range")
    return SectionOption(
        section_type=d.get("section_type", ""),
        section_id=d.get("section_id", "") or "",
        days_of_week=list(d.get("days_of_week") or []),
        start_time=_opt(deserialize_time, d.get("start_time")),
        end_time=_opt(deserialize_time, d.get("end_time")),
        location=d.get("location"),
        date_range=(deserialize_date(dr[0]), deserialize_date(dr[1])) if dr else None,
        note=d.get("note", "") or "",
    )


def assessment_to_dict(a: AssessmentTask) -> dict:
    return {
        "title": a.title,
        "type": a.type,
        "weight_percent": a.weight_percent,
        "due_datetime": _opt(serialize_datetime, a.due_datetime),
        "end_datetime": _opt(serialize_datetime, a.end_datetime),
        "due_rule": a.due_rule,
        "rule_anchor": a.rule_anchor,
        "confidence": a.confidence,
        "source_evidence": a.source_evidence,
        "needs_review": a.needs_review,
        "date_status": a.date_status,
        "date_note": a.date_note,
        "date_window": [serialize_date(a.date_window[0]), serialize_date(a.date_window[1])] if a.date_window else None,
        "dates": [serialize_date(x) for x in (a.dates or [])],
        "is_bonus": a.is_bonus,
    }


def assessment_from_dict(d: dict) -> AssessmentTask:
    w = d.get("date_window")
    due = _opt(deserialize_datetime, d.get("due_datetime"))
    status = d.get("date_status")
    if not status:
        # rows saved before date statuses existed
        status = "exact" if due else ("rule" if d.get("due_rule") else "missing")
    return AssessmentTask(
        title=d["title"],
        type=d.get("type", "other"),
        weight_percent=d.get("weight_percent"),
        due_datetime=due,
        due_rule=d.get("due_rule"),
        rule_anchor=d.get("rule_anchor"),
        confidence=d.get("confidence", 0.0) or 0.0,
        source_evidence=d.get("source_evidence"),
        needs_review=bool(d.get("needs_review", False)),
        date_status=status,
        date_note=d.get("date_note", "") or "",
        date_window=(deserialize_date(w[0]), deserialize_date(w[1])) if w else None,
        dates=[deserialize_date(x) for x in (d.get("dates") or [])],
        end_datetime=_opt(deserialize_datetime, d.get("end_datetime")),
        is_bonus=bool(d.get("is_bonus", False)),
    )


def extracted_to_dict(data: ExtractedCourseData) -> dict:
    return {
        "term": term_to_dict(data.term),
        "lecture_sections": [section_to_dict(s) for s in data.lecture_sections],
        "lab_sections": [section_to_dict(s) for s in data.lab_sections],
        "tutorial_sections": [section_to_dict(s) for s in data.tutorial_sections],
        "assessments": [assessment_to_dict(a) for a in data.assessments],
        "course_code": data.course_code,
        "course_name": data.course_name,
        "notes": list(data.notes or []),
        "text_pages": data.text_pages,
        "image_pages": list(data.image_pages or []),
    }


def extracted_from_dict(d: dict) -> ExtractedCourseData:
    return ExtractedCourseData(
        term=term_from_dict(d["term"]),
        lecture_sections=[section_from_dict(s) for s in d.get("lecture_sections", [])],
        lab_sections=[section_from_dict(s) for s in d.get("lab_sections", [])],
        tutorial_sections=[section_from_dict(s) for s in d.get("tutorial_sections", [])],
        assessments=[assessment_from_dict(a) for a in d.get("assessments", [])],
        course_code=d.get("course_code"),
        course_name=d.get("course_name"),
        notes=list(d.get("notes") or []),
        text_pages=int(d.get("text_pages") or 0),
        image_pages=list(d.get("image_pages") or []),
    )
