"""The .ics never invents a date (D1), is RFC 5545 clean (D9) and titles carry the course code (D4/D9)."""
from datetime import date, datetime, time

from icalendar import Calendar

from src.icalendar_gen import ICalendarGenerator
from src.models import AssessmentTask, CourseTerm, SectionOption


def term():
    return CourseTerm(term_name="Winter 2026", start_date=date(2026, 1, 5), end_date=date(2026, 4, 9),
                      exam_periods=[(date(2026, 4, 12), date(2026, 4, 30))])


def build(assessments, lecture=None, lab=None, tutorial=None, course_code="KIN 2000", t=None):
    gen = ICalendarGenerator()
    cal = gen.generate_calendar(term=t or term(), lecture_section=lecture, lab_section=lab,
                                assessments=assessments, study_plan=[], tutorial_section=tutorial,
                                course_code=course_code)
    return Calendar.from_ical(cal.to_ical())


def events(cal):
    return list(cal.walk("VEVENT"))


def test_undated_assessments_get_no_event():
    a = [AssessmentTask(title="Final Exam", type="final", weight_percent=40, date_status="registrar"),
         AssessmentTask(title="Midterm Test 1", type="midterm", weight_percent=25, date_status="tba"),
         AssessmentTask(title="Essay", type="assignment", weight_percent=25, date_status="missing")]
    assert events(build(a)) == []


def test_unresolved_rule_gets_no_event():
    a = [AssessmentTask(title="Lab reports", type="lab_report", weight_percent=50, due_rule="24 hrs after each lab", date_status="rule")]
    assert events(build(a)) == []


def test_dated_assessment_is_one_due_event_with_course_code_and_dtstamp():
    a = [AssessmentTask(title="Tracker 1", type="assignment", weight_percent=5, due_datetime=datetime(2026, 1, 16, 23, 59))]
    ev = events(build(a))
    assert len(ev) == 1
    assert str(ev[0]["SUMMARY"]) == "KIN 2000: Tracker 1 due"
    assert "DTSTAMP" in ev[0]
    assert ev[0]["DTSTART"].dt.tzinfo is not None


def test_recurring_assessment_makes_one_event_per_date():
    a = [AssessmentTask(title="Weekly Quizzes", type="quiz", weight_percent=15, date_status="recurring",
                        dates=[date(2025, 9, 12), date(2025, 9, 19), date(2025, 9, 26)],
                        due_datetime=datetime(2025, 9, 12, 13, 0))]
    ev = events(build(a))
    assert [e["DTSTART"].dt.date() for e in ev] == [date(2025, 9, 12), date(2025, 9, 19), date(2025, 9, 26)]
    assert all(str(e["SUMMARY"]).endswith("Weekly Quizzes (1 of 3) due") or "of 3" in str(e["SUMMARY"]) for e in ev[:1])


def test_exam_with_end_time_spans_the_exam():
    a = [AssessmentTask(title="Midterm Test 1", type="midterm", weight_percent=25,
                        due_datetime=datetime(2025, 11, 14, 18, 0), end_datetime=datetime(2025, 11, 14, 20, 0))]
    ev = events(build(a))[0]
    assert ev["DTEND"].dt.hour == 20


def test_recurring_lecture_until_last_day_of_classes_in_utc_with_vtimezone_and_location():
    lec = SectionOption(section_type="Lecture", section_id="", days_of_week=[3], start_time=time(10, 30),
                        end_time=time(12, 20), location="SSC-2050")
    cal = build([], lecture=lec)
    assert list(cal.walk("VTIMEZONE")), "VTIMEZONE for America/Toronto is required"
    ev = events(cal)
    assert len(ev) == 1
    assert str(ev[0]["SUMMARY"]) == "KIN 2000 Lecture"
    assert str(ev[0]["LOCATION"]) == "SSC-2050"
    assert ev[0]["DTSTART"].dt == datetime(2026, 1, 8, 10, 30, tzinfo=ev[0]["DTSTART"].dt.tzinfo)
    until = ev[0]["RRULE"]["UNTIL"][0]
    assert isinstance(until, datetime) and until.tzinfo is not None and until.utcoffset().total_seconds() == 0
    assert until.astimezone(ev[0]["DTSTART"].dt.tzinfo).date() == date(2026, 4, 9)


def test_tutorial_is_its_own_event_type():
    tut = SectionOption(section_type="Tutorial", section_id="", days_of_week=[2], start_time=time(17, 30), end_time=time(18, 20), location="Zoom")
    ev = events(build([], tutorial=tut))
    assert str(ev[0]["SUMMARY"]) == "KIN 2000 Tutorial"


def test_section_without_time_or_term_without_dates_makes_no_recurring_event():
    lec = SectionOption(section_type="Lecture", section_id="", days_of_week=[3], start_time=None, end_time=None)
    assert events(build([], lecture=lec)) == []
    lec2 = SectionOption(section_type="Lecture", section_id="", days_of_week=[3], start_time=time(10, 0), end_time=time(11, 0))
    no_dates = CourseTerm(term_name="Unknown", start_date=None, end_date=None)
    assert events(build([], lecture=lec2, t=no_dates)) == []


def test_every_event_has_dtstamp_and_uid():
    lec = SectionOption(section_type="Lecture", section_id="", days_of_week=[0, 2], start_time=time(9, 30), end_time=time(10, 30))
    a = [AssessmentTask(title="A1", type="assignment", weight_percent=5, due_datetime=datetime(2026, 1, 29, 23, 55))]
    for e in events(build(a, lecture=lec)):
        assert "DTSTAMP" in e and "UID" in e
