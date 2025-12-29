"""
iCalendar generation module.

Generates standards-compliant .ics files for calendar import.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from icalendar import Calendar, Event
from pytz import timezone

from .models import (
    SectionOption, AssessmentTask, StudyPlanItem, CourseTerm
)


class ICalendarGenerator:
    """Generates iCalendar (.ics) files from course data."""
    
    def __init__(self, timezone_str: str = "America/Toronto"):
        """Initialize calendar generator.
        
        Args:
            timezone_str: Timezone string (default: America/Toronto)
        """
        self.tz = timezone(timezone_str)
    
    def generate_calendar(self,
                         term: CourseTerm,
                         lecture_section: Optional[SectionOption],
                         lab_section: Optional[SectionOption],
                         assessments: List[AssessmentTask],
                         study_plan: List[StudyPlanItem]) -> Calendar:
        """Generate complete calendar with all events.
        
        Args:
            term: Course term
            lecture_section: Selected lecture section (if any)
            lab_section: Selected lab section (if any)
            assessments: List of assessments
            study_plan: List of study plan items
            
        Returns:
            Calendar object ready for export
        """
        cal = Calendar()
        cal.add('prodid', '-//Course Outline Converter//EN')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        
        # Add recurring lecture events
        if lecture_section:
            lecture_events = self._create_recurring_section_events(
                lecture_section, term, "Lecture"
            )
            for event in lecture_events:
                cal.add_component(event)
        
        # Add recurring lab events
        if lab_section:
            lab_events = self._create_recurring_section_events(
                lab_section, term, "Lab"
            )
            for event in lab_events:
                cal.add_component(event)
        
        # Add assessment due events
        for assessment in assessments:
            if assessment.due_datetime:
                due_event = self._create_assessment_due_event(assessment)
                cal.add_component(due_event)
        
        # Add study plan start events
        for study_item in study_plan:
            start_event = self._create_study_start_event(study_item)
            cal.add_component(start_event)
        
        return cal
    
    def _create_recurring_section_events(self, section: SectionOption,
                                        term: CourseTerm,
                                        event_type: str) -> List[Event]:
        """Create recurring events for a section.
        
        Args:
            section: Section option
            term: Course term
            event_type: "Lecture" or "Lab"
            
        Returns:
            List of Event objects (one per day of week)
        """
        events = []
        
        # Determine date range
        if section.date_range:
            start_date, end_date = section.date_range
        else:
            start_date, end_date = term.start_date, term.end_date
        
        # Create one event per day of week
        for day_num in section.days_of_week:
            # Find first occurrence of this day
            current_date = start_date
            while current_date.weekday() != day_num and current_date <= end_date:
                current_date += timedelta(days=1)
            
            if current_date > end_date:
                continue
            
            # Create datetime
            dtstart = self.tz.localize(datetime.combine(
                current_date,
                section.start_time
            ))
            dtend = self.tz.localize(datetime.combine(
                current_date,
                section.end_time
            ))
            
            # Create event
            event = Event()
            event.add('uid', f"{uuid.uuid4()}@course-outline")
            event.add('dtstart', dtstart)
            event.add('dtend', dtend)
            event.add('summary', f"{event_type} - {section.section_id or ''}".strip())
            
            if section.location:
                event.add('location', section.location)
            
            # Add RRULE for weekly recurrence
            rrule = {
                'FREQ': 'WEEKLY',
                'BYDAY': self._weekday_to_byday(day_num),
                'UNTIL': end_date
            }
            event.add('rrule', rrule)
            
            event.add('description', f"{event_type} section {section.section_id or 'N/A'}")
            
            events.append(event)
        
        return events
    
    def _create_assessment_due_event(self, assessment: AssessmentTask) -> Event:
        """Create event for assessment due date.
        
        Args:
            assessment: Assessment task
            
        Returns:
            Event object
        """
        event = Event()
        
        # Use due_datetime, default to 11:59 PM if only date
        due_dt = assessment.due_datetime
        if due_dt:
            # Ensure timezone
            if due_dt.tzinfo is None:
                due_dt = self.tz.localize(due_dt)
            
            event.add('uid', f"{uuid.uuid4()}@course-outline")
            event.add('dtstart', due_dt)
            # Due events are typically all-day or short duration
            event.add('dtend', due_dt + timedelta(minutes=1))
            event.add('summary', f"DUE: {assessment.title}")
            
            # Build description
            desc_parts = [f"Assessment: {assessment.title}"]
            desc_parts.append(f"Type: {assessment.type}")
            if assessment.weight_percent:
                desc_parts.append(f"Weight: {assessment.weight_percent}%")
            if assessment.source_evidence:
                desc_parts.append(f"Source: {assessment.source_evidence}")
            desc_parts.append(f"Confidence: {assessment.confidence:.1%}")
            
            event.add('description', "\n".join(desc_parts))
            event.add('priority', 5)  # Medium-high priority for due dates
        
        return event
    
    def _create_study_start_event(self, study_item: StudyPlanItem) -> Event:
        """Create event for study plan start.
        
        Args:
            study_item: Study plan item
            
        Returns:
            Event object
        """
        event = Event()
        
        start_dt = study_item.start_studying_datetime
        if start_dt.tzinfo is None:
            start_dt = self.tz.localize(start_dt)
        
        due_dt = study_item.due_datetime
        if due_dt.tzinfo is None:
            due_dt = self.tz.localize(due_dt)
        
        event.add('uid', f"{uuid.uuid4()}@course-outline")
        event.add('dtstart', start_dt)
        # Study events are typically 1 hour
        event.add('dtend', start_dt + timedelta(hours=1))
        event.add('summary', f"START: {study_item.task_id}")
        
        description = f"Start studying for: {study_item.task_id}\n"
        description += f"Due date: {due_dt.strftime('%Y-%m-%d %H:%M')}"
        event.add('description', description)
        event.add('priority', 3)  # Lower priority than due dates
        
        return event
    
    def _weekday_to_byday(self, weekday: int) -> str:
        """Convert weekday number to iCalendar BYDAY value.
        
        Args:
            weekday: 0=Monday, 6=Sunday
            
        Returns:
            iCalendar BYDAY string (MO, TU, WE, etc.)
        """
        days = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']
        return days[weekday]
    
    def export_to_file(self, calendar: Calendar, filepath: str):
        """Export calendar to .ics file.
        
        Args:
            calendar: Calendar object
            filepath: Path to output file
        """
        with open(filepath, 'wb') as f:
            f.write(calendar.to_ical())


