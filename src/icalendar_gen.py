"""
iCalendar generation module.

Generates RFC 5545 .ics files for calendar import:
- every VEVENT carries UID and DTSTAMP;
- a VTIMEZONE for the course timezone is embedded so TZID references resolve;
- weekly lecture / lab / tutorial series end (UNTIL, in UTC) on the last day of classes;
- SUMMARY lines carry the course code ("KIN 2000 Lecture", "KIN 2000: Tracker 1 due");
- an assessment without a date produces NO event: the review page explains why instead
  (a placeholder on the term end or on "today" would be a fabricated deadline).
"""

import uuid
from datetime import date, datetime, timedelta, time as dt_time, timezone as dt_timezone
from typing import List, Optional
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event, Timezone, TimezoneStandard, TimezoneDaylight
from pytz import timezone

from .models import (
    SectionOption, AssessmentTask, StudyPlanItem, CourseTerm, _day_ints
)


class ICalendarGenerator:
    """Generates iCalendar (.ics) files from course data."""

    def __init__(self, timezone_str: str = "America/Toronto"):
        self.tz_name = timezone_str
        self.tz = timezone(timezone_str)

    # ------------------------------------------------------------------ public
    def generate_calendar(self,
                          term: CourseTerm,
                          lecture_section: Optional[SectionOption],
                          lab_section: Optional[SectionOption],
                          assessments: List[AssessmentTask],
                          study_plan: List[StudyPlanItem],
                          tutorial_section: Optional[SectionOption] = None,
                          course_code: Optional[str] = None) -> Calendar:
        cal = Calendar()
        cal.add('prodid', '-//Plato course outline converter//kalpkan.com//EN')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        cal.add('x-wr-calname', f"{course_code or 'Course'} {term.term_name}".strip())
        cal.add('x-wr-timezone', self.tz_name)
        cal.add_component(self._vtimezone(term))

        self.course_code = (course_code or "").strip()

        for section, kind in ((lecture_section, "Lecture"), (lab_section, "Lab"), (tutorial_section, "Tutorial")):
            if section:
                for event in self._create_recurring_section_events(section, term, kind):
                    cal.add_component(event)

        for assessment in assessments:
            for event in self._assessment_events(assessment):
                cal.add_component(event)

        for study_item in study_plan:
            cal.add_component(self._create_study_start_event(study_item))

        return cal

    # ---------------------------------------------------------------- helpers
    def _label(self, text: str) -> str:
        return f"{self.course_code} {text}".strip() if self.course_code else text

    def _new_event(self) -> Event:
        event = Event()
        event.add('uid', f"{uuid.uuid4()}@plato.kalpkan.com")
        event.add('dtstamp', datetime.now(dt_timezone.utc))
        return event

    def _localize(self, dt: datetime) -> datetime:
        return dt if dt.tzinfo is not None else self.tz.localize(dt)

    def _vtimezone(self, term: CourseTerm) -> Timezone:
        """A VTIMEZONE covering the term (RFC 5545 §3.6.5) built from the zoneinfo database."""
        years = {d.year for d in (term.start_date, term.end_date) if d} or {date.today().year}
        lo, hi = min(years) - 1, max(years) + 1
        try:
            tzc = Timezone.from_tzinfo(ZoneInfo(self.tz_name), first_date=datetime(lo, 1, 1), last_date=datetime(hi, 12, 31))
            tzc['TZID'] = self.tz_name
            return tzc
        except Exception:
            # Older icalendar without from_tzinfo: a fixed America/Toronto description
            tzc = Timezone()
            tzc.add('tzid', self.tz_name)
            std = TimezoneStandard()
            std.add('dtstart', datetime(1970, 11, 1, 2, 0, 0))
            std.add('rrule', {'freq': 'yearly', 'bymonth': 11, 'byday': '1su'})
            std.add('tzoffsetfrom', timedelta(hours=-4))
            std.add('tzoffsetto', timedelta(hours=-5))
            std.add('tzname', 'EST')
            dst = TimezoneDaylight()
            dst.add('dtstart', datetime(1970, 3, 8, 2, 0, 0))
            dst.add('rrule', {'freq': 'yearly', 'bymonth': 3, 'byday': '2su'})
            dst.add('tzoffsetfrom', timedelta(hours=-5))
            dst.add('tzoffsetto', timedelta(hours=-4))
            dst.add('tzname', 'EDT')
            tzc.add_component(std)
            tzc.add_component(dst)
            return tzc

    # --------------------------------------------------------------- sections
    def _create_recurring_section_events(self, section: SectionOption,
                                         term: CourseTerm,
                                         event_type: str) -> List[Event]:
        """One weekly VEVENT per weekday, from the first occurrence on/after the first day of
        classes until (UNTIL, UTC) the last day of classes. A section without a clock time
        or a term without dates yields nothing."""
        events: List[Event] = []
        if not section.start_time or not section.end_time:
            return events
        if section.date_range:
            start_date, end_date = section.date_range
        else:
            start_date, end_date = term.start_date, term.end_date
        if not start_date or not end_date:
            return events

        summary = self._label(event_type)
        if section.section_id:
            summary += f" ({section.section_id})"

        meetings = [(d, m.start_time, m.end_time, m.location) for m in section.all_meetings()
                    if m.start_time and m.end_time for d in _day_ints(m.days_of_week)]
        for day_num, start_time, end_time, location in meetings:
            current_date = start_date
            while current_date.weekday() != day_num and current_date <= end_date:
                current_date += timedelta(days=1)
            if current_date > end_date:
                continue
            dtstart = self.tz.localize(datetime.combine(current_date, start_time))
            dtend = self.tz.localize(datetime.combine(current_date, end_time))
            if dtend <= dtstart:
                dtend = dtstart + timedelta(hours=1)
            # UNTIL must be a UTC date-time when DTSTART is a local date-time (§3.3.10)
            until_local = self.tz.localize(datetime.combine(end_date, dt_time(23, 59, 59)))
            until_utc = until_local.astimezone(dt_timezone.utc)

            event = self._new_event()
            event.add('dtstart', dtstart)
            event.add('dtend', dtend)
            event.add('summary', summary)
            if location or section.location:
                event.add('location', location or section.location)
            event.add('rrule', {'FREQ': 'WEEKLY', 'BYDAY': self._weekday_to_byday(day_num), 'UNTIL': until_utc})
            desc = f"{event_type}"
            if section.section_id:
                desc += f" section {section.section_id}"
            desc += f", weekly from {start_date:%b %-d} to {end_date:%b %-d, %Y}"
            if section.note:
                desc += f"\n{section.note}"
            event.add('description', desc)
            events.append(event)
        return events

    # ------------------------------------------------------------ assessments
    def _assessment_events(self, assessment: AssessmentTask) -> List[Event]:
        """Events for one assessment: one per listed date for a recurring item, one for a dated
        item, none for an item whose date the outline does not give."""
        status = getattr(assessment, 'date_status', None) or ("exact" if assessment.due_datetime else "missing")
        dates = list(getattr(assessment, 'dates', None) or [])
        if status == "recurring" and dates:
            base_time = assessment.due_datetime.time() if assessment.due_datetime else dt_time(23, 59)
            out = []
            for i, d in enumerate(dates, 1):
                dt = self.tz.localize(datetime.combine(d, base_time))
                out.append(self._create_assessment_due_event_with_date(
                    assessment, dt, suffix=f" ({i} of {len(dates)})"))
            return out
        if assessment.due_datetime:
            return [self._create_assessment_due_event_with_date(assessment, assessment.due_datetime)]
        return []

    def _create_assessment_due_event(self, assessment: AssessmentTask) -> Event:
        if not assessment.due_datetime:
            raise ValueError("Assessment must have due_datetime to create event")
        return self._create_assessment_due_event_with_date(assessment, assessment.due_datetime)

    def _create_assessment_due_event_with_date(self, assessment: AssessmentTask, due_dt: datetime,
                                               suffix: str = "") -> Event:
        due_dt = self._localize(due_dt)
        event = self._new_event()
        event.add('dtstart', due_dt)
        end_dt = getattr(assessment, 'end_datetime', None)
        if end_dt and self._localize(end_dt) > due_dt and not suffix:
            event.add('dtend', self._localize(end_dt))
        else:
            event.add('dtend', due_dt + timedelta(minutes=30 if assessment.type in ("midterm", "final", "test", "quiz") else 1))
        code = f"{self.course_code}: " if self.course_code else ""
        event.add('summary', f"{code}{assessment.title}{suffix} due")

        desc_parts = [f"{assessment.title} ({assessment.type})"]
        if assessment.weight_percent:
            desc_parts.append(f"Weight: {assessment.weight_percent:g}%")
        if getattr(assessment, 'date_note', ''):
            desc_parts.append(assessment.date_note)
        if assessment.source_evidence:
            desc_parts.append(f"Outline says: {assessment.source_evidence[:300]}")
        event.add('description', "\n".join(desc_parts))
        event.add('priority', 5)
        return event

    # ------------------------------------------------------------- study plan
    def _create_study_start_event(self, study_item: StudyPlanItem) -> Event:
        start_dt = self._localize(study_item.start_studying_datetime)
        due_dt = self._localize(study_item.due_datetime)
        event = self._new_event()
        event.add('dtstart', start_dt)
        event.add('dtend', start_dt + timedelta(hours=1))
        event.add('summary', self._label(f"start: {study_item.task_id}") if self.course_code else f"Start: {study_item.task_id}")
        event.add('description', f"Start studying for: {study_item.task_id}\nDue: {due_dt:%Y-%m-%d %H:%M}")
        event.add('priority', 3)
        return event

    def _weekday_to_byday(self, weekday: int) -> str:
        return ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU'][weekday]

    def export_to_file(self, calendar: Calendar, filepath: str):
        with open(filepath, 'wb') as f:
            f.write(calendar.to_ical())
