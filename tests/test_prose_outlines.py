"""Round-2 defects D14 / D15 / D16 / D17: outlines that write their timetable and deadlines
as bullet prose instead of tables (CS 2209A, CS 4411, MOS 2181A), a weekly-quiz rule that
must yield to the explicit date list (Biochem 3381A), a per-lab rule that must become one
event per lab once the slot is chosen (ECE 2240A), and the course name.

Every fixture below is the outline's own wording (pdfplumber text), trimmed.
"""
from datetime import date, time

from src.outline.course import extract_course
from src.outline.pipeline import build
from src.outline.schedule import extract_slots


def slot_set(slots):
    return {(s.kind, tuple(s.days), s.start, s.end) for s in slots}


# ------------------------------------------------------------------ D14: slots
def test_cs2209_bulleted_lectures_hours_line():
    text = ("Course Information\n• Course Name: Applied Logic for Computer Science\n• Academic Term: Fall 2025\n"
            "• Instructor: Dr. X\n• Lectures:\n• Hours: Tuesdays 9:30-11:30 am, and Thursdays 9:30-10:30 am\n•\n"
            "List of Prerequisites\n")
    assert slot_set(extract_slots([(1, text)], [])) == {
        ("lecture", (1,), time(9, 30), time(11, 30)), ("lecture", (3,), time(9, 30), time(10, 30))}


def test_cs4411_time_line_without_a_lecture_label():
    text = ("Course Information\n- Course name: Databases II (Advanced Databases)\n- Course number: COMPSCI 4411/9538 A\n"
            "- Academic term: Fall 2025\n-\n- Time: Tuesdays 12:30-2:30 pm and Thursdays 12:30-1:30 pm\nList of Prerequisites\n")
    assert slot_set(extract_slots([(1, text)], [])) == {
        ("lecture", (1,), time(12, 30), time(14, 30)), ("lecture", (3,), time(12, 30), time(13, 30))}


def test_mos_section_lines_under_class_location_and_time():
    text = ("1. Course Information\n1.1 Class Location and Time\nSection 001: Tuesdays, 1:30pm-4:30pm, SSC 2036\n"
            "Section 002: Wednesdays, 9:30am-12:30pm, SSC 2036\nSection 003: Wednesdays, 1:30pm-4:30pm, SEB 2100\n"
            "1.2 Course Description\n")
    slots = extract_slots([(1, text)], [])
    assert slot_set(slots) == {("lecture", (1,), time(13, 30), time(16, 30)),
                               ("lecture", (2,), time(9, 30), time(12, 30)),
                               ("lecture", (2,), time(13, 30), time(16, 30))}
    assert sorted(s.section_id for s in slots) == ["001", "002", "003"]
    assert all(s.location for s in slots)


def test_exam_section_lines_are_not_slots():
    text = ("5. Evaluation\nExam #1 (during class time, 2 hours in length) = 31%\n"
            "Section 001: Tues Oct 7, 2pm-4pm, Elborn College (rooms to be announced)\n"
            "Section 002: Wed Oct 8, 10am-12pm, Elborn College (rooms to be announced)\n")
    assert extract_slots([(4, text)], []) == []


def test_office_hours_line_is_still_not_a_slot():
    text = "Office Hours: Mondays 9am-12pm, via Zoom, by appointment\nTime: Tuesdays 12:30-2:30 pm\n"
    assert slot_set(extract_slots([(1, text)], [])) == {("lecture", (1,), time(12, 30), time(14, 30))}


# ------------------------------------------------------------ D14: assessments
CS2209_PAGES = [
    (1, "Department of Computer Science\nCourse Outline\nApplied Logic for Computer Science1\nCOMPSCI 2209A\n"
        "1. Course Information\nCourse Information\n• Course Name: Applied Logic for Computer Science\n• Academic Term: Fall 2025\n"
        "• Lectures:\n• Hours: Tuesdays 9:30-11:30 am, and Thursdays 9:30-10:30 am\n"),
    (3, "Key Sessional Dates:\n• Classes begin: September 4, 2025\n• Fall Reading Week: November 3 – 9\n"
        "• Classes end: December 9, 2025\n• Exam period: December 11–22, 2025\n"),
    (4, "5. Methods of Evaluation\nThe final course grade will be determined by student performance on the following course components:\n"
        "- Assignments 17% (three assignments: the first one 5%, and the remaining two, 6% each)\n"
        "- Quizzes (online) 8% (four quizzes, 2% each)\n- Midterm Test 30%\n- Final exam 45%\n"
        "To pass the course, students must obtain a weighted average of at least 50% between the Midterm\nTest and the Final Exam.\n"
        "7. Week 7, October 20-October 26\n• The Midterm Test is on October 21, during the lecture time; the location will be\nannounced, and we’ll have class on Thursday.\n"
        "Assignments:\n- Assignment 1: From the content of Weeks 0-3 (available: September 28, deadline: October 8, at 11:55\npm)\n"
        "- Assignment 2: From the content of Weeks 4-7 (available: October 30, deadline: November 10, at 11:55\npm)\n"
        "- Assignment 3: From the content of Weeks 8, 10, 11 and 12 (available: November 29, deadline:\nDecember 9, at 11:55 pm)\n"),
    (5, "Online Quizzes:\n- Quiz 1: From the content of Weeks 0-2 (available: September 18 at 11:55 pm, deadline: September 21\nat 11:55 pm)\n"
        "- Quiz 2: From the content of Weeks 3-5 (available: October 16 at 11:55 pm, deadline: October 19 at\n11:55 pm)\n"
        "- Quiz 3: From the content of Weeks 6-8 (available: November 13 at 11:55 pm, deadline: November 16\nat 11:55 pm)\n"
        "- Quiz 4: From the content of Weeks 10-13 (available: December 5 at 11:55 pm, deadline: December 8 at\n11:55 pm)\n"
        "Midterm Test:\nThe midterm test is on October 21, 9:30 AM-11:30 AM, in class.\nFinal exam:\nThe final exam date and time: TBD.\n"),
]


def _by_title(data):
    return {a.title: a for a in data.assessments}


def test_cs2209_group_rows_become_dated_items():
    data = build(CS2209_PAGES, [], "CS_2209A_FW25.pdf")
    got = _by_title(data)
    assert set(got) == {"Assignment 1", "Assignment 2", "Assignment 3", "Quiz 1", "Quiz 2", "Quiz 3", "Quiz 4",
                        "Midterm Test", "Final exam"}
    assert [got[f"Assignment {i}"].weight_percent for i in (1, 2, 3)] == [5, 6, 6]
    assert all(got[f"Quiz {i}"].weight_percent == 2 for i in (1, 2, 3, 4))
    assert got["Assignment 1"].due_datetime.date() == date(2025, 10, 8)
    assert got["Assignment 1"].due_datetime.time() == time(23, 55)
    assert got["Assignment 3"].due_datetime.date() == date(2025, 12, 9)
    assert got["Quiz 1"].due_datetime.date() == date(2025, 9, 21)
    assert got["Quiz 4"].due_datetime.date() == date(2025, 12, 8)
    assert got["Quiz 4"].due_datetime.time() == time(23, 55)
    assert got["Midterm Test"].due_datetime.date() == date(2025, 10, 21)
    assert got["Final exam"].date_status == "tba"
    assert sum(a.weight_percent for a in data.assessments) == 100


CS4411_PAGES = [
    (1, "Department of Computer Science\nDatabases II (Advanced Databases)\nCOMPSCI 4411/9538\nCourse Outline\n"
        "- Course name: Databases II (Advanced Databases)\n- Course number: COMPSCI 4411/9538 A\n- Academic term: Fall 2025\n"
        "- Time: Tuesdays 12:30-2:30 pm and Thursdays 12:30-1:30 pm\n"),
    (2, "Key Sessional Dates:\nClasses begin: September 4, 2025\nFall Reading Week: November 3 – 9, 2025\n"
        "Classes end: December 9, 2025\nExam period: December 11 – 22, 2025\n"),
    (3, "5. Methods of Evaluation\nGrading Scheme and Assessment Dates\nThe overall course grade will be calculated as listed below:\n"
        "- Assignments 15% (three assignments, 5% each)\n- Midterm test 20%\n- Final exam 30%\n- Project 35%\n"
        "Tentative list of assessments and dates:\n"
        "- Assignment 1: Data storage and indexing (Available: Sep 11, Submission deadline: Sep 25, Peer\nreview: Sep 30 – Oct 7)\n"
        "- Assignment 2: Query answering and optimization (Available: Oct 30, Submission deadline: Nov\n13, Peer review: Nov 18 – Nov 25)\n"
        "- Assignment 3: Transaction management and crash recovery (Available: Nov 13, Submission\ndeadline: Nov 27, Peer review: Dec 2 – Dec 9)\n"
        "- Midterm exam: Weeks 1–6 (Oct 21, 12:30–2:30 pm, in class)\n"
        "- Project: Submission deadline: Dec 6, 11:55 pm (Optional peer review: Dec 9 – Dec 20)\n"
        "- Final exam: Weeks 1–13 (date and time: TBD)\nGeneral information about missed coursework\n"),
]


def test_cs4411_submission_deadlines_and_parenthesised_midterm():
    data = build(CS4411_PAGES, [], "CS_4411A_9538A_FW25.pdf")
    got = _by_title(data)
    assert set(got) == {"Assignment 1", "Assignment 2", "Assignment 3", "Midterm test", "Final exam", "Project"}
    assert [got[f"Assignment {i}"].weight_percent for i in (1, 2, 3)] == [5, 5, 5]
    assert got["Assignment 1"].due_datetime.date() == date(2025, 9, 25)
    assert got["Assignment 2"].due_datetime.date() == date(2025, 11, 13)
    assert got["Assignment 3"].due_datetime.date() == date(2025, 11, 27)
    assert got["Midterm test"].due_datetime.date() == date(2025, 10, 21)
    assert got["Midterm test"].due_datetime.time() == time(12, 30)
    assert got["Project"].due_datetime.date() == date(2025, 12, 6)
    assert got["Project"].due_datetime.time() == time(23, 55)
    assert got["Project"].date_status == "exact"          # not "recurring" from the peer-review range
    assert got["Final exam"].date_status == "tba"


def test_hs2250_final_exam_online_tba_is_tba_not_missing():
    pages = [(1, "Health Sciences 2250A\nFall 2025\n"),
             (2, "Evaluation\nQuiz 1 20% October 3\nFinal Exam [online] 40% TBA\nAssignment 40% November 20\n")]
    got = _by_title(build(pages, [], "x.pdf"))
    assert got["Final Exam [online]"].date_status == "tba" if "Final Exam [online]" in got else \
        next(a for a in got.values() if a.type == "final").date_status == "tba"


# ------------------------------------------------------------------- D15
BIOCHEM_PAGES = [
    (1, "Department of Biochemistry\nBiological Macromolecules (Biochem 3381A)\nCourse Syllabus for Fall 2025\n"),
    (2, "Classes Begin Reading Week Classes End Exam Period\nSeptember 4 November 3–9 December 9 December 11–22\n"),
    (6, "5. Methods of Evaluation\nI. Quizzes (15%) Each Friday of a lecture week (starting Sept 12 and ending\nNovember 14) you will have a quiz "
        "to complete that is worth 2.5% of your final\nmark.\nII. Assignment 1 (5%) Due Monday September 29\nIII. Assignment 2 (20%) Due Wednesday October 13\n"
        "IV. Assignment 3 (20%) Due Monday November 10\nV. Final Written Report: Wed. December 8th. (40% final).\n"
        "Important Details:\n1. Weekly Quizzes: Each Friday starting Sept 12th, we will be having a short quiz.\n"
        "Students will have 30 min to complete the quiz on Bright Space, anytime between 1-\n10 pm. There will be a total of 7 quizzes, the last being Nov\n14.\n"),
    (9, "Quizzes:\nTo be held between 1-10 pm on Bright Space:\n• September 12, 19, 26; October 10, 17, 31; and November 14\n"
        "Assignments:\nAssignment 1 – Deadline: Monday Sept 29 in Bright Space\n"),
]


def test_biochem_explicit_quiz_dates_beat_the_every_friday_rule():
    data = build(BIOCHEM_PAGES, [], "BIOCHEM 3381A.pdf")
    quiz = next(a for a in data.assessments if a.type == "quiz")
    assert quiz.date_status == "recurring"
    assert quiz.dates == [date(2025, 9, 12), date(2025, 9, 19), date(2025, 9, 26), date(2025, 10, 10),
                          date(2025, 10, 17), date(2025, 10, 31), date(2025, 11, 14)]
    assert quiz.due_datetime.time() == time(13, 0)


def test_weekly_rule_with_a_stated_count_that_disagrees_never_invents_dates():
    pages = [(1, "Chem 1000A\nFall 2025\nClasses begin: September 4, 2025\nClasses end: December 9, 2025\n"),
             (2, "Evaluation\nQuizzes 15% Each Friday starting Sept 12 and ending November 14. There will be a total of 7 quizzes.\n"
                 "Final Exam 85% scheduled by the Registrar\n")]
    quiz = next(a for a in build(pages, [], "x.pdf").assessments if a.type == "quiz")
    assert quiz.dates == [] and quiz.due_datetime is None
    assert quiz.date_status in ("range", "tba")
    assert "7" in quiz.date_note


# ------------------------------------------------------------------- D16
def test_lab_report_rule_gets_a_lab_anchor_and_a_helpful_note():
    pages = [(1, "ECE 2240A – Electronics Laboratory I\nCourse Outline Fall 2025\nLECTURE: Friday 1.30 pm-2.30 pm HSB-236 (weekly)\n"
                 "LAB: 3hrs/session (weekly); 10 sessions\nClasses begin: September 4, 2025\nClasses end: December 9, 2025\n"),
             (2, "EVALUATION\nComponent Weight Due\nLabs (Total = 8) 50% Lab Report due 24hrs after each Lab Session\n"
                 "PCB Project 20% November 29\nFinal Examination 30% scheduled by the Registrar\n")]
    tables = [[["Component", "Weight", "Due"], ["Labs (Total = 8)", "50%", "Lab Report due 24hrs after each Lab Session"],
               ["PCB Project", "20%", "November 29"], ["Final Examination", "30%", "scheduled by the Registrar"]]]
    labs = next(a for a in build(pages, tables, "x.pdf").assessments if a.type == "lab_report")
    assert labs.due_rule and labs.rule_anchor == "lab"
    assert labs.date_status == "rule"
    assert "lab" in labs.date_note.lower() and "Add Section" in labs.date_note


# ------------------------------------------------------------------- D17
def test_course_name_label_wins_over_headings():
    code, name = extract_course([(1, "Department of Computer Science\nCourse Outline\nApplied Logic for Computer Science1\nCOMPSCI 2209A\n"
                                     "1. Course Information\nCourse Information\n• Course Name: Applied Logic for Computer Science\n• Academic Term: Fall 2025\n")], "x.pdf")
    assert code == "COMPSCI 2209A"
    assert name == "Applied Logic for Computer Science"


def test_course_name_label_with_trailing_term():
    code, name = extract_course([(1, "Department of Mathematics\nAM 3615B/AM 9576B Course Outline\n1. Course Information\nCourse Information\n"
                                     "Course name: Mathematical Biology. Winter 2026.\nDelivery: In-person lectures.\n")], "x.pdf")
    assert code == "AM 3615B"
    assert name == "Mathematical Biology"


def test_course_name_before_code_line_beats_the_subtitle_after_it():
    _, name = extract_course([(1, "Department of Classical Studies\nCrime and Punishment in Ancient Greece and Rome\n"
                                  "Preliminary Course Outline for CS 2301B 650 (Winter 2026)\nAn online, asynchronous course with in-person examinations\n")], "x.pdf")
    assert name == "Crime and Punishment in Ancient Greece and Rome"


def test_course_name_wrapped_over_two_lines():
    _, name = extract_course([(1, "Health Sciences 2800: Health\nSciences Research Methods\nFall & Winter | 2025-2026\nVersion 1.0\n")], "x.pdf")
    assert name == "Health Sciences Research Methods"


def test_course_name_heading_is_never_a_name():
    _, name = extract_course([(1, "Department of Mathematics\nMath 1228 Course Outline\n1. Course Information\nCourse Information\n"
                                  "This course is Math 1228, section 200. The lecture material is presented online, asynchronously through\nOWL.\n"),
                              (2, "3. Course Syllabus, Schedule, Delivery Mode\nMath 1228 (Methods of Finite Mathematics) covers: techniques of counting.\n")], "x.pdf")
    assert name == "Methods of Finite Mathematics"


def test_course_name_syllabus_tail_is_stripped():
    _, name = extract_course([(1, "Department of Biology\nBio2382b Cell Biology Syllabus – 2025\n1. Course Information\n")], "x.pdf")
    assert name == "Cell Biology"


def test_course_name_with_a_footnote_digit_before_the_code():
    _, name = extract_course([(1, "Department of Computer Science\nCourse Outline\nApplied Logic for Computer Science1\nCOMPSCI 2209A\n1. Course Information\n")], "x.pdf")
    assert name == "Applied Logic for Computer Science"


MOS_PAGES = [
    (1, "Fall 2025 Course Syllabus\nMOS 2181A -- Sections 001, 002, 003\nOrganizational Behaviour\n1. Course Information\n1.1 Class Location and Time\n"
        "Section 001: Tuesdays, 1:30pm-4:30pm, SSC 2036\nSection 002: Wednesdays, 9:30am-12:30pm, SSC 2036\nSection 003: Wednesdays, 1:30pm-4:30pm, SEB 2100\n"),
    (3, "Key Dates\n• Classes begin: September 4, 2025\n• Fall Reading Week: November 3-9, 2025\n• Classes end: December 9, 2025\nExam period: December 11 – 22, 2025\n"),
    (4, "5. Evaluation\nChapter Assignments (one assignment for each of the 15 chapters) = 7%\nExam #1 (during class time, 2 hours in length) = 31%\n"
        "Section 001: Tues Oct 7, 2pm-4pm, Elborn College (rooms to be announced)\nSection 002: Wed Oct 8, 10am-12pm, Elborn College (rooms to be announced)\n"
        "Section 003: Wed Oct 8, 2pm-4pm, Elborn College (rooms to be announced)\nExam #2 (during class time, 2 hours in length) = 31%\n"
        "Section 001: Tues Nov 11, 2pm-4pm, Elborn College (rooms to be announced)\nSection 002: Wed Nov 12, 10am-12pm, Elborn College (rooms to be announced)\n"
        "Section 003: Wed Nov 12, 2pm-4pm, Elborn College (rooms to be announced)\nExam #3 (December exam period, 2 hours in length) = 31%\n"
        "All sections will write together at the same time\nDate, time, location to be scheduled by the Registrar’s Office\nTotal = 100%\n"),
    (5, "• The due dates for the 15 chapter assignments are as follows:\nChapter 1, Chapter 2, Chapter 3 assignments: due Sept 19 @ 11:59pm\no\n"
        "Chapter 4, Chapter 5 assignments: due Sept 26 @ 11:59pm\no\nChapter 6, Chapter 7 assignments: due Oct 17 @ 11:59pm\no\n"
        "Chapter 8, Chapter 9 assignments: due Oct 24 @ 11:59pm\no\nChapter 10 assignment: due Oct 31 @ 11:59pm\no\nChapter 11 assignment: due Nov 21 @ 11:59pm\no\n"
        "Chapter 12, Chapter 13 assignments: due Nov 28 @ 11:59pm\no\nChapter 14, Chapter 15 assignments: due Dec 5 @ 11:59pm\no\n"),
]


def test_mos_section_dependent_exams_and_chapter_assignment_dates():
    data = build(MOS_PAGES, [], "2181A001002003.pdf")
    got = _by_title(data)
    assert sorted(s.section_id for s in data.lecture_sections) == ["001", "002", "003"]
    ch = got["Chapter Assignments"]
    assert ch.date_status == "recurring"
    assert ch.dates == [date(2025, 9, 19), date(2025, 9, 26), date(2025, 10, 17), date(2025, 10, 24), date(2025, 10, 31),
                        date(2025, 11, 21), date(2025, 11, 28), date(2025, 12, 5)]
    assert ch.due_datetime.time() == time(23, 59)
    e1 = got["Exam #1"]
    assert e1.date_status == "range" and e1.due_datetime is None
    assert e1.date_window == (date(2025, 10, 7), date(2025, 10, 8))
    assert "section 001 Oct 7" in e1.date_note and "section 002 Oct 8" in e1.date_note
    assert got["Exam #2"].date_window == (date(2025, 11, 11), date(2025, 11, 12))
    assert got["Exam #3"].date_status in ("registrar", "range") and got["Exam #3"].due_datetime is None


def test_in_class_midterm_takes_the_lecture_slot_time():
    """D18: 'Mid-term Exam4 MCQ, in class, paper 30% Feb 12th' with one Thursday 10:30 lecture -> 10:30, not 23:59."""
    pages = [(1, "KIN 2000 Physical Activity and Health\nWinter 2026\nClasses Begin Reading Week Classes End\nJanuary 8 February 14–22 April 10\n"
                 "Component Day Time Location\nLecture Thursday 10:30-12:20 SSC-2050\n"),
             (3, "Assessment Format Weight Due\nPhysical Activity Tracker 1 Template 10% Jan 16th\nMid-term Exam MCQ, in class, paper 30% Feb 12th\nFinal Exam MCQ 40% Registrar\n")]
    tables = [[["Component", "Day", "Time", "Location"], ["Lecture", "Thursday", "10:30-12:20", "SSC-2050"]],
              [["Assessment", "Format", "Weight", "Due"], ["Physical Activity Tracker 1", "Template", "10%", "Jan 16th"],
               ["Mid-term Exam", "MCQ, in class, paper", "30%", "Feb 12th"], ["Final Exam", "MCQ", "40%", "Registrar"]]]
    data = build(pages, tables, "x.pdf")
    got = _by_title(data)
    assert got["Physical Activity Tracker 1"].due_datetime.time() == time(23, 59)
    assert got["Mid-term Exam"].due_datetime == __import__("datetime").datetime(2026, 2, 12, 10, 30)
