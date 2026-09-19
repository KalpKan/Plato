"""Lecture / lab / tutorial slots from the ways Western outlines print them (D4)."""
from datetime import time

from src.outline.schedule import extract_slots


def slot_set(slots):
    return {(s.kind, tuple(s.days), s.start, s.end, s.location) for s in slots}


def test_kin_table_row():
    text = "Table 4: Date and times of course components\nComponent Day Time Location\nLecture Thursday 10:30-12:20 SSC-2050\n"
    tables = [[["Component", "Day", "Time", "Location"], ["Lecture", "Thursday", "10:30-12:20", "SSC-2050"]]]
    s = extract_slots([(2, text)], tables)
    assert slot_set(s) == {("lecture", (3,), time(10, 30), time(12, 20), "SSC-2050")}


def test_biochem_prose_with_day_letters_and_tutorial():
    text = ("Lectures: MWF 12:30 - 1:20 pm in AHB-1R40. In-person lectures.\n"
            "Tutorials: W 5:30 - 6:20 pm via zoom (https://westernuniversity.zoom.us/j/9). Please\n")
    s = extract_slots([(3, text)], [])
    assert slot_set(s) == {("lecture", (0, 2, 4), time(12, 30), time(13, 20), "AHB-1R40"),
                           ("tutorial", (2,), time(17, 30), time(18, 20), "Zoom")}


def test_ece_dotted_times_and_tutorial_not_lab():
    text = ("LECTURE: Friday 1.30 pm-2.30 pm HSB-236 (weekly)\nSome lectures will be on Zoom/YouTube\n"
            "LAB: 3hrs/session (weekly); 10 sessions\nTUTORIAL: Friday 12.30-1.30 pm (weekly) UCC-56\n")
    s = extract_slots([(1, text)], [])
    assert slot_set(s) == {("lecture", (4,), time(13, 30), time(14, 30), "HSB-236"),
                           ("tutorial", (4,), time(12, 30), time(13, 30), "UCC-56")}
    kinds = [x.kind for x in s]
    assert "lab" not in kinds  # no day/time: reported as a note, not a slot


def test_ece_lab_without_a_time_is_a_note():
    text = "LAB: 3hrs/session (weekly); 10 sessions\n"
    from src.outline.schedule import extract_slots_and_notes
    slots, notes = extract_slots_and_notes([(1, text)], [])
    assert slots == []
    assert any("lab" in n.lower() and "draftmyschedule" in n.lower() or "timetable" in n.lower() for n in notes)


def test_physiology_slash_days():
    text = "Timetabled Sessions\nComponent Date(s) Time\nLecture M/W/F 10:30 – 11:30 AM\n"
    s = extract_slots([(2, text)], [[["Component", "Date(s)", "Time"], ["Lecture", "M/W/F", "10:30 – 11:30 AM"]]])
    assert slot_set(s) == {("lecture", (0, 2, 4), time(10, 30), time(11, 30), None)}


def test_class_meetings_two_days_two_lengths():
    text = "Class Meetings: Tuesday 2:30-3:30pm, Thursday 2:30-4:30pm\nLocation: MC-110\n"
    s = extract_slots([(1, text)], [])
    assert slot_set(s) == {("lecture", (1,), time(14, 30), time(15, 30), "MC-110"),
                           ("lecture", (3,), time(14, 30), time(16, 30), "MC-110")}


def test_weekly_schedule_all_thursdays_gives_a_lecture_day_without_a_time():
    text = ("Week Date(s) Topic\n1 September 4 Intro\n2 September 11 Planning\n3 September 18 x\n4 September 25 y\n"
            "5 October 2 z\n6 October 9 w\n7 October 16 test\n8 October 23 a\n9 October 30 b\n")
    s = extract_slots([(2, text)], [], term_year_hint=2025)
    assert len(s) == 1
    assert (s[0].kind, s[0].days, s[0].start) == ("lecture", [3], None)


def test_office_hours_are_not_slots():
    text = "OFFICE HOURS: W 12:30-1:30 PM\nTIME AND PLACE OF CLASS: See OWL\n"
    assert extract_slots([(1, text)], []) == []


def test_no_duplicate_when_table_and_text_both_match():
    text = "Lecture Thursday 10:30-12:20 SSC-2050\n"
    tables = [[["Component", "Day", "Time", "Location"], ["Lecture", "Thursday", "10:30-12:20", "SSC-2050"]]]
    assert len(extract_slots([(2, text)], tables)) == 1
