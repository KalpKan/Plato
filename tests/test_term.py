"""The term window is read from the outline, never guessed from today (D3)."""
from datetime import date

from src.outline.term import extract_term, sessional_dates


KIN_PAGE1 = """School of Kinesiology
KIN 2000 Physical Activity and Health
Winter 2026
Important Dates
Table 1 Important Dates
Classes Begin Reading Week Classes End Study day(s) Exam Period
January 5 February 14-22 April 9 April 10-11 April 12-30
March 30, 2026: Last day to withdraw from a second-term half course without academic penalty
"""

PHYS_PAGE1 = """Department of Physiology and Pharmacology
Physiology 3120
Course Outline for Fall 2025/Winter 2026
2. Important Dates:
Classes Begin Reading Week Classes End Study day(s) Exam Period
September 4 November 3–9 December 9 December 10 December 11–22
September 30, 2025: National Day for Truth and Reconciliation; non-instructional day
Classes Begin Reading Week Classes End Study day(s) Exam Period
January 5 February 14–22 April 9 April 10, 11 April 12–30
"""

CS3340_PAGE3 = """Key Sessional Dates
Class Begin: Monday, January 5, 2026
Spring Reading Week: February 14-22, 2026
Class End: Thursday, April 9, 2026
Exam Period: April 12–30, 2026
"""


def test_important_dates_table_winter():
    t = extract_term([(1, KIN_PAGE1)], filename="FHS Course Outline 2000.pdf")
    assert (t.start, t.end) == (date(2026, 1, 5), date(2026, 4, 9))
    assert t.name == "Winter 2026"
    assert t.exam_periods == [(date(2026, 4, 12), date(2026, 4, 30))]
    assert t.source == "outline"


def test_two_important_dates_tables_make_a_full_year():
    t = extract_term([(1, PHYS_PAGE1)], filename="Physiology 3120.pdf")
    assert (t.start, t.end) == (date(2025, 9, 4), date(2026, 4, 9))
    assert t.exam_periods == [(date(2025, 12, 11), date(2025, 12, 22)), (date(2026, 4, 12), date(2026, 4, 30))]
    assert "2025" in t.name and "2026" in t.name


def test_class_begin_end_lines():
    t = extract_term([(1, "Computer Science 3340b\nCourse Outline – January 2026"), (3, CS3340_PAGE3)], filename="outline26.pdf")
    assert (t.start, t.end) == (date(2026, 1, 5), date(2026, 4, 9))
    assert t.name == "Winter 2026"


def test_season_year_falls_back_to_western_sessional_dates():
    t = extract_term([(1, "Biological Macromolecules (Biochem 3381A)\nCourse Syllabus for Fall 2025")], filename="x.pdf")
    assert (t.start, t.end) == (date(2025, 9, 4), date(2025, 12, 9))
    assert t.source == "sessional"


def test_full_year_from_year_range():
    t = extract_term([(1, "Classical Studies 1000 — 001: ANCIENT GREECE AND ROME\n2025-2026")], filename="x.pdf")
    assert (t.start, t.end) == (date(2025, 9, 4), date(2026, 4, 9))


def test_fall_winter_2025_with_A_suffix_is_fall():
    t = extract_term([(1, "ECE 2240A – Electronics Laboratory I\nCourse Outline Fall/Winter 2025")], filename="x.pdf")
    assert (t.start, t.end) == (date(2025, 9, 4), date(2025, 12, 9))
    assert t.name == "Fall 2025"


def test_filename_supplies_the_term_when_the_text_has_none():
    t = extract_term([(1, "Math 1228 Course Outline\nTerm Test 1 20% Friday Oct. 3 7-8:30pm")], filename="Math-1228---Fall-2025_red.pdf")
    assert (t.start, t.end) == (date(2025, 9, 4), date(2025, 12, 9))


def test_image_first_page_uses_filename_and_code_suffix():
    t = extract_term([(2, "Assignment 1 (10%) -- due Oct. 9\nMidterm Exam (30%) - Thursday, Oct. 30, 11:30 - 1:30pm")],
                     filename="CS_3342A_FW25.pdf", course_code="CS 3342A")
    assert (t.start, t.end) == (date(2025, 9, 4), date(2025, 12, 9))


def test_weekly_range_table_bounds_the_term():
    text = "Preliminary Course Outline for CS 2301B 650 (Winter 2026)\nWeek 1 (Jan. 05-09) Lecture: Intro\nWeek 2 (Jan. 12-16) Lecture: x\nWeek 3 (Jan. 19-23) Lecture: y\nWeek 4 (Jan. 26-30) Lecture: z\nWeek 12 (Mar. 30-Apr.08) Lecture: y"
    t = extract_term([(1, text)], filename="x.pdf")
    assert (t.start, t.end) == (date(2026, 1, 5), date(2026, 4, 8))


def test_unknown_term_is_unknown_not_today():
    t = extract_term([(1, "Some course\nno dates at all")], filename="scan.pdf")
    assert t.start is None and t.end is None
    assert t.name == "Unknown"


def test_sessional_table_covers_recent_years():
    assert sessional_dates("Fall", 2025)["start"] == date(2025, 9, 4)
    assert sessional_dates("Winter", 2026)["end"] == date(2026, 4, 9)
    assert sessional_dates("Fall", 2024)["start"] == date(2024, 9, 5)
    assert sessional_dates("Winter", 2025)["start"] == date(2025, 1, 6)
