"""Course code and name (D3 course_code)."""
from src.outline.course import extract_course


def test_multiword_department():
    code, name = extract_course([(1, "DEPARTMENT OF CLASSICAL STUDIES\nCOURSE OUTLINE\nClassical Studies 1000 — 001: ANCIENT GREECE AND ROME\n2025-2026")], "x.pdf")
    assert code == "Classical Studies 1000"
    assert name and "Greece" in name


def test_health_sciences_with_colon():
    code, name = extract_course([(1, "Health Sciences 2800: Health\nSciences Research Methods\nFall & Winter | 2025-2026")], "x.pdf")
    assert code == "Health Sciences 2800"


def test_parenthesised_code():
    code, name = extract_course([(1, "Department of Biochemistry\nBiological Macromolecules (Biochem 3381A)\nCourse Syllabus for Fall 2025")], "x.pdf")
    assert code == "Biochem 3381A"
    assert name == "Biological Macromolecules"


def test_room_numbers_are_not_codes():
    code, _ = extract_course([(1, "Department of Mathematics\nMath 1228 Course Outline\nDr. Allen O’Hara aohara@uwo.ca MC 113")], "x.pdf")
    assert code == "Math 1228"


def test_course_name_line_with_section():
    code, name = extract_course([(1, "THE UNIVERSITY OF WESTERN ONTARIO\nDEPARTMENT OF COMPUTER SCIENCE\nLONDON CANADA\nComputer Science 3340b\nAnalysis of Algorithms I\nCourse Outline – January 2026\nCourse Name: Computer Science 3340B\nClass Meetings: Tuesday 2:30-3:30pm")], "x.pdf")
    assert code == "Computer Science 3340B"
    assert name == "Analysis of Algorithms I"


def test_filename_fallback_when_page_one_is_an_image():
    code, _ = extract_course([(2, "Scheme - functional programming\nAll questions are to be sent to cs3342@uwo.ca")], "CS_3342A_FW25.pdf")
    assert code == "CS 3342A"


def test_cs_with_section_number():
    code, name = extract_course([(1, "Department of Classical Studies\nCrime and Punishment in Ancient Greece and Rome\nPreliminary Course Outline for CS 2301B 650 (Winter 2026)")], "x.pdf")
    assert code == "CS 2301B"
    assert name == "Crime and Punishment in Ancient Greece and Rome"


def test_kin():
    code, name = extract_course([(1, "School of Kinesiology\nKIN 2000 Physical Activity and Health\nWinter 2026")], "x.pdf")
    assert code == "KIN 2000"
    assert name == "Physical Activity and Health"
