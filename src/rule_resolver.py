"""
Rule resolution module for relative deadlines.

Resolves relative deadline rules (e.g., "24 hours after lab") to absolute datetimes.
"""

import re
from datetime import datetime, timedelta
from typing import List, Optional
from .models import AssessmentTask, SectionOption, CourseTerm


class RuleResolver:
    """Resolves relative deadline rules to absolute datetimes."""
    
    def resolve_rules(self, assessments: List[AssessmentTask],
                     sections: List[SectionOption],
                     term: CourseTerm) -> List[AssessmentTask]:
        """Resolve all relative rules in assessments.
        
        Args:
            assessments: List of assessments (some may have due_rule)
            sections: List of section options (for anchor events)
            term: Course term (for date range)
            
        Returns:
            List of assessments with resolved due_datetime
        """
        resolved = []
        
        for assessment in assessments:
            if assessment.due_rule and not assessment.due_datetime:
                # Try to resolve rule
                resolved_assessment = self.resolve_rule(
                    assessment, sections, term
                )
                resolved.append(resolved_assessment)
            else:
                resolved.append(assessment)
        
        return resolved
    
    def resolve_rule(self, assessment: AssessmentTask,
                    sections: List[SectionOption],
                    term: CourseTerm) -> AssessmentTask:
        """Resolve a single relative rule.
        
        Args:
            assessment: Assessment with due_rule
            sections: Available sections for anchor events
            term: Course term
            
        Returns:
            Assessment with resolved due_datetime (or needs_review=True if cannot resolve)
        """
        if not assessment.due_rule or not assessment.rule_anchor:
            assessment.needs_review = True
            return assessment
        
        # Find anchor section
        anchor_section = self._find_anchor_section(
            assessment.rule_anchor, sections
        )
        
        if not anchor_section:
            assessment.needs_review = True
            return assessment
        
        # Parse rule to get offset
        offset = self._parse_rule_offset(assessment.due_rule)
        
        if offset is None:
            assessment.needs_review = True
            return assessment
        
        # Generate occurrences of anchor event
        occurrences = self._generate_occurrences(
            anchor_section, term
        )
        
        if not occurrences:
            assessment.needs_review = True
            return assessment
        
        # Per CLARIFYING_QUESTIONS.md: Create one assessment per occurrence
        # For now, return the assessment with a flag to generate per-occurrence
        # The caller should handle generating multiple assessments
        # Use first occurrence as placeholder, but mark for per-occurrence generation
        first_occurrence = occurrences[0]
        due_datetime = first_occurrence + offset
        
        # Update assessment
        assessment.due_datetime = due_datetime
        assessment.confidence = min(assessment.confidence + 0.2, 1.0)
        # Mark that this should generate per-occurrence assessments
        assessment.needs_review = True  # Will be handled by caller
        
        return assessment
    
    def generate_per_occurrence_assessments(self, assessment_template: AssessmentTask,
                                          anchor_section: SectionOption,
                                          term: CourseTerm) -> List[AssessmentTask]:
        """Generate one assessment per occurrence for recurring rules.
        
        Per CLARIFYING_QUESTIONS.md: Generate one due event per occurrence.
        Name them deterministically: "Lab Report 1", "Lab Report 2", etc.
        Mark as Needs review unless PDF explicitly confirms.
        
        Args:
            assessment_template: Template assessment with rule
            anchor_section: Section to anchor to
            term: Course term
            
        Returns:
            List of assessments, one per occurrence
        """
        if not assessment_template.due_rule:
            return [assessment_template]
        
        # Parse rule offset
        offset = self._parse_rule_offset(assessment_template.due_rule)
        if offset is None:
            return [assessment_template]
        
        # Generate occurrences
        occurrences = self._generate_occurrences(anchor_section, term)
        if not occurrences:
            return [assessment_template]
        
        # "at 11:59pm" / "by 11:59 pm" in the rule sets the clock time of every due event (D23)
        clock = self._parse_rule_time(assessment_template.due_rule)

        # Create one assessment per occurrence
        assessments = []
        for i, occurrence in enumerate(occurrences, start=1):
            due_datetime = occurrence + offset
            if clock is not None:
                due_datetime = due_datetime.replace(hour=clock.hour, minute=clock.minute, second=0)
            
            # Create new assessment with numbered title
            base_title = assessment_template.title
            # Remove "(auto)" or similar if present
            if " (auto)" in base_title:
                base_title = base_title.replace(" (auto)", "")
            
            # Extract base name (e.g., "Lab Report" from "Lab Report (auto)")
            numbered_title = f"{base_title} {i}"
            
            assessment = AssessmentTask(
                title=numbered_title,
                type=assessment_template.type,
                weight_percent=assessment_template.weight_percent,
                due_datetime=due_datetime,
                due_rule=None,  # Resolved
                rule_anchor=None,  # Resolved
                confidence=assessment_template.confidence,
                source_evidence=assessment_template.source_evidence,
                needs_review=True  # Per CLARIFYING_QUESTIONS.md: mark as needs review
            )
            assessments.append(assessment)
        
        return assessments
    
    def _find_anchor_section(self, anchor: str,
                           sections: List[SectionOption]) -> Optional[SectionOption]:
        """Find section that matches anchor type.
        
        Args:
            anchor: "lab", "tutorial", or "lecture"
            sections: Available sections
            
        Returns:
            Matching section or None
        """
        anchor_lower = anchor.lower()
        
        for section in sections:
            section_type_lower = section.section_type.lower()
            if anchor_lower in section_type_lower or section_type_lower in anchor_lower:
                return section
        
        # Also check for "tutorial" as "lab"
        if anchor_lower == "tutorial":
            for section in sections:
                if section.section_type.lower() == "lab":
                    return section
        
        return None
    
    def _parse_rule_time(self, rule_text: str):
        """'Day of lab at 11:59pm' -> 23:59; 'due by 11:59 PM' -> 23:59; None when no clock time is given."""
        m = re.search(r"\b(?:at|by|before)\s+(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)", rule_text or "", re.I)
        if not m:
            return None
        from .outline.dates import parse_time_span
        t, _ = parse_time_span(m.group(1))
        return t

    def _parse_rule_offset(self, rule_text: str) -> Optional[timedelta]:
        """Parse rule text to extract time offset.
        
        Args:
            rule_text: Rule text (e.g., "24 hours after lab")
            
        Returns:
            timedelta or None if cannot parse
        """
        words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7}
        low = rule_text.lower()

        def num(m):
            g = m.group(1)
            return int(g) if g.isdigit() else words.get(g, 0)

        m = re.search(r'(\d+|one|two|three)\s*(?:hours?|hrs?|h)\b', low)
        if m:
            return timedelta(hours=num(m))
        m = re.search(r'(\d+|one|two|three|four|five|six|seven)\s*(?:days?|d)\b', low)
        if m:
            return timedelta(days=num(m))
        m = re.search(r'(\d+|one|two|three)\s*(?:weeks?|wks?)\b', low)
        if m:
            return timedelta(weeks=num(m))
        if re.search(r'\b(?:next|following)\s+(?:lab|tutorial|lecture|class|week)\b', low):
            return timedelta(weeks=1)
        if re.search(r'\b(?:day\s+of|end\s+of|during|in\s+(?:the\s+)?(?:lab|tutorial|class)|beginning\s+of|start\s+of)\b', low):
            return timedelta(0)
        return None

    def _generate_occurrences(self, section: SectionOption,
                             term: CourseTerm) -> List[datetime]:
        """Generate all occurrences of a section within term.
        
        Args:
            section: Section option
            term: Course term
            
        Returns:
            List of datetime occurrences
        """
        occurrences = []

        # Determine date range
        if section.date_range:
            start_date, end_date = section.date_range
        else:
            start_date, end_date = term.start_date, term.end_date
        if not start_date or not end_date:
            return []
        meetings = [(d, m.start_time) for m in section.all_meetings() if m.start_time for d in _day_numbers(m.days_of_week)]
        if not meetings:
            return []
        reading = list(getattr(term, "reading_weeks", None) or [])

        current_date = start_date
        while current_date <= end_date:
            if not any(a <= current_date <= b for a, b in reading):
                for d, start_time in meetings:
                    if current_date.weekday() == d:
                        occurrences.append(datetime.combine(current_date, start_time))
            current_date += timedelta(days=1)
        return occurrences


_DAY_NAMES = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def _day_numbers(days) -> List[int]:
    """Section days come as 0-6 from the parser and the form, or as 'Mon'/'Monday' from older rows."""
    out = []
    for d in days or []:
        if isinstance(d, int):
            out.append(d)
        else:
            n = _DAY_NAMES.get(str(d)[:3].lower())
            if n is not None:
                out.append(n)
    return sorted(set(out))

