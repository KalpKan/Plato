"""
PDF extraction module for course outlines.

Extracts term information, lecture/lab sections, and assessments from PDF files.
"""

import re
import pdfplumber
from pathlib import Path
from datetime import date, datetime, time
from typing import List, Optional, Tuple
import dateparser

from .models import (
    CourseTerm, SectionOption, AssessmentTask, ExtractedCourseData
)


class PDFExtractor:
    """Extracts course information from PDF course outlines."""
    
    def __init__(self, pdf_path: Path):
        """Initialize extractor with PDF path.
        
        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = pdf_path
        self.pages_text = []
        self._load_pdf()
    
    def _load_pdf(self):
        """Load PDF and extract text page by page."""
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    self.pages_text.append((page_num, text))
    
    def extract_all(self) -> ExtractedCourseData:
        """Extract all course information from PDF.
        
        Returns:
            ExtractedCourseData with term, sections, and assessments
        """
        term = self.extract_term()
        lecture_sections = self.extract_lecture_sections()
        lab_sections = self.extract_lab_sections()
        assessments = self.extract_assessments()
        
        # Try to extract course code and name
        course_code, course_name = self.extract_course_info()
        
        return ExtractedCourseData(
            term=term,
            lecture_sections=lecture_sections,
            lab_sections=lab_sections,
            assessments=assessments,
            course_code=course_code,
            course_name=course_name
        )
    
    def extract_term(self) -> CourseTerm:
        """Extract term information from PDF.
        
        This function searches the first 3 pages of the PDF for term information.
        It looks for patterns like "Fall 2026" or "Winter Term 2027" and date ranges.
        If information is missing, it returns placeholder values that will be
        filled in by user input later.
        
        Returns:
            CourseTerm object with term name and date range. If information is
            missing, returns placeholder values (term_name="Unknown" or default dates).
        """
        # Search first 3 pages for term information
        # Most course outlines have term info on the first page or two
        search_text = "\n".join([text for _, text in self.pages_text[:3]])
        
        # Pattern for term name - look for "Fall 2026", "Winter Term 2027", etc.
        # These patterns match common ways term names are written in course outlines
        term_patterns = [
            r'(Fall|Winter|Summer)\s+(\d{4})',  # "Fall 2026"
            r'(Fall|Winter|Summer)\s+Term\s+(\d{4})',  # "Fall Term 2026"
            r'(Fall|Winter|Summer)\s+Semester\s+(\d{4})',  # "Fall Semester 2026"
        ]
        
        term_name = None
        # Try each pattern until we find a match
        for pattern in term_patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                # Combine the season and year (e.g., "Fall 2026")
                term_name = f"{match.group(1)} {match.group(2)}"
                break
        
        # Pattern for date ranges - look for "September 1 - December 15, 2026"
        # or "2026-09-01 - 2026-12-15" format
        date_range_patterns = [
            r'(September|October|November|December|January|February|March|April|May|June|July|August)\s+(\d{1,2})\s*[-–]\s*(September|October|November|December|January|February|March|April|May|June|July|August)\s+(\d{1,2}),?\s+(\d{4})',
            r'(\d{4})-(\d{2})-(\d{2})\s*[-–]\s*(\d{4})-(\d{2})-(\d{2})',
        ]
        
        start_date = None
        end_date = None
        
        # Try to find date ranges in the text
        for pattern in date_range_patterns:
            match = re.search(pattern, search_text, re.IGNORECASE)
            if match:
                # Try to parse dates using dateparser library
                # This handles various date formats automatically
                date_str = match.group(0)
                dates = dateparser.parse(date_str, fuzzy=True)
                if dates:
                    # This is a simplified approach - may need refinement
                    # For now, we'll infer dates from term name if this doesn't work
                    pass
        
        # If term name found but dates missing, try to infer from term name
        # For example, "Fall 2026" typically means September to December
        if term_name and not start_date:
            year_match = re.search(r'\d{4}', term_name)
            if year_match:
                year = int(year_match.group(0))
                # Set default dates based on term type
                if "Fall" in term_name:
                    start_date = date(year, 9, 1)  # September 1
                    end_date = date(year, 12, 15)  # December 15
                elif "Winter" in term_name:
                    start_date = date(year, 1, 8)  # January 8
                    end_date = date(year, 4, 30)  # April 30
                elif "Summer" in term_name:
                    start_date = date(year, 5, 1)  # May 1
                    end_date = date(year, 8, 31)  # August 31
        
        # If still missing, return with placeholder values
        # The caller (main.py or app.py) will prompt the user to fill these in
        if not term_name or not start_date or not end_date:
            # Return placeholder - will be filled by user input
            return CourseTerm(
                term_name=term_name or "Unknown",
                start_date=start_date or date.today(),
                end_date=end_date or date.today()
            )
        
        # Return the extracted term information
        return CourseTerm(
            term_name=term_name,
            start_date=start_date,
            end_date=end_date,
            timezone="America/Toronto"  # Western University is in Toronto timezone
        )
    
    def extract_lecture_sections(self) -> List[SectionOption]:
        """Extract lecture section schedules.
        
        Returns:
            List of SectionOption objects for lectures
        """
        sections = []
        # Search for schedule section (usually in first few pages)
        search_text = "\n".join([text for _, text in self.pages_text[:5]])
        
        # Pattern for schedule tables/lists
        # This is a simplified pattern - may need refinement based on actual PDFs
        schedule_pattern = r'(Lecture|LEC|Class|Section)\s*(\d{3})?\s*[:\s]+([MTWThFS]+)\s+(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})'
        
        matches = re.finditer(schedule_pattern, search_text, re.IGNORECASE)
        
        for match in matches:
            section_id = match.group(2) or ""
            days_str = match.group(3)
            start_hour = int(match.group(4))
            start_min = int(match.group(5))
            end_hour = int(match.group(6))
            end_min = int(match.group(7))
            
            # Parse days of week
            days_of_week = self._parse_days_of_week(days_str)
            
            # Determine AM/PM (simplified - may need refinement)
            start_time = time(start_hour % 24, start_min)
            end_time = time(end_hour % 24, end_min)
            
            section = SectionOption(
                section_type="Lecture",
                section_id=section_id,
                days_of_week=days_of_week,
                start_time=start_time,
                end_time=end_time,
                location=None  # Extract location if pattern found
            )
            sections.append(section)
        
        return sections
    
    def extract_lab_sections(self) -> List[SectionOption]:
        """Extract lab section schedules.
        
        Returns:
            List of SectionOption objects for labs
        """
        sections = []
        search_text = "\n".join([text for _, text in self.pages_text[:5]])
        
        # Pattern for lab schedules
        lab_pattern = r'(Lab|LAB|Laboratory|Tutorial|TUT)\s*(\d{3})?\s*[:\s]+([MTWThFS]+)\s+(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})'
        
        matches = re.finditer(lab_pattern, search_text, re.IGNORECASE)
        
        for match in matches:
            section_id = match.group(2) or ""
            days_str = match.group(3)
            start_hour = int(match.group(4))
            start_min = int(match.group(5))
            end_hour = int(match.group(6))
            end_min = int(match.group(7))
            
            days_of_week = self._parse_days_of_week(days_str)
            start_time = time(start_hour % 24, start_min)
            end_time = time(end_hour % 24, end_min)
            
            section = SectionOption(
                section_type="Lab",
                section_id=section_id,
                days_of_week=days_of_week,
                start_time=start_time,
                end_time=end_time,
                location=None
            )
            sections.append(section)
        
        return sections
    
    def extract_assessments(self) -> List[AssessmentTask]:
        """Extract assessment information.
        
        Returns:
            List of AssessmentTask objects
        """
        assessments = []
        # Search entire PDF for assessments
        full_text = "\n".join([text for _, text in self.pages_text])
        
        # Pattern for assessments with due dates
        assessment_patterns = [
            r'(Assignment|ASSIGNMENT|HW|Homework)\s+(\d+)[^\n]*(?:due|Due|DUE)[^\n]*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})',
            r'(Quiz|QUIZ|Test)\s+(\d+)[^\n]*(?:due|Due|DUE|on|On)[^\n]*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})',
            r'(Lab\s+Report|Laboratory\s+Report|Lab\s+Assignment)\s+(\d+)[^\n]*(?:due|Due|DUE)[^\n]*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})',
            r'(Final\s+Exam|FINAL|Final\s+Examination)[^\n]*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})',
            r'(Midterm|MIDTERM|Mid-term)[^\n]*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})',
        ]
        
        for pattern in assessment_patterns:
            matches = re.finditer(pattern, full_text, re.IGNORECASE)
            for match in matches:
                assessment_type = self._classify_assessment_type(match.group(1))
                title = match.group(0)[:50]  # Truncate for title
                
                # Try to extract due date
                due_date_str = match.group(-1) if len(match.groups()) > 1 else None
                due_datetime = None
                if due_date_str:
                    parsed_date = dateparser.parse(due_date_str)
                    if parsed_date:
                        # Default to 11:59 PM if no time specified
                        due_datetime = datetime.combine(
                            parsed_date.date(),
                            time(23, 59)
                        )
                
                # Try to extract weight
                weight = self._extract_weight(match.group(0))
                
                assessment = AssessmentTask(
                    title=title,
                    type=assessment_type,
                    weight_percent=weight,
                    due_datetime=due_datetime,
                    confidence=0.7 if due_datetime else 0.4,
                    source_evidence=f"Page {match.start() // 1000}: {match.group(0)[:100]}",
                    needs_review=(due_datetime is None or weight is None)
                )
                assessments.append(assessment)
        
        # Also search for relative rules
        relative_rules = self._extract_relative_rules(full_text)
        for rule_text, anchor in relative_rules:
            # Create assessment with rule
            assessment = AssessmentTask(
                title=f"Assessment (rule: {rule_text[:30]})",
                type="other",
                due_rule=rule_text,
                rule_anchor=anchor,
                confidence=0.5,
                source_evidence=f"Relative rule: {rule_text}",
                needs_review=True
            )
            assessments.append(assessment)
        
        return assessments
    
    def extract_course_info(self) -> Tuple[Optional[str], Optional[str]]:
        """Extract course code and name from the PDF.
        
        This function searches the first page of the PDF for the course code
        (like "CS 101" or "MATH 120") and the course name. Course codes typically
        follow the pattern of 2-4 uppercase letters followed by 3-4 digits.
        
        Returns:
            Tuple of (course_code, course_name). Both can be None if not found.
            Example: ("CS 101", "Introduction to Computer Science")
        """
        # Search first page for course code (e.g., "CS 101", "MATH 120")
        # Course codes are almost always on the first page
        first_page = self.pages_text[0][1] if self.pages_text else ""
        
        # Pattern for course code: 2-4 uppercase letters, space, 3-4 digits
        # Examples: "CS 101", "MATH 120", "PHYS 3140"
        course_code_pattern = r'([A-Z]{2,4})\s+(\d{3,4})'
        match = re.search(course_code_pattern, first_page)
        course_code = match.group(0) if match else None
        
        # Course name is usually on first page, right after the course code
        course_name = None
        if course_code:
            # Try to find course name near course code
            # Look for the position of the course code in the text
            idx = first_page.find(course_code)
            if idx != -1:
                # Look for text after course code (usually the course name)
                # Check up to 200 characters after the course code
                remaining = first_page[idx + len(course_code):idx + 200]
                # Extract first line or sentence (course name is usually on the same line)
                lines = remaining.split('\n')
                if lines:
                    # Take the first line and limit to 100 characters
                    course_name = lines[0].strip()[:100]
        
        return course_code, course_name
    
    def _parse_days_of_week(self, days_str: str) -> List[int]:
        """Parse day abbreviations from text like "MWF" or "TTh".
        
        This function converts day abbreviations (like "MWF" for Monday/Wednesday/Friday)
        into a list of weekday numbers. The numbers follow Python's weekday convention:
        0 = Monday, 1 = Tuesday, 2 = Wednesday, 3 = Thursday, 4 = Friday, 5 = Saturday, 6 = Sunday.
        
        Args:
            days_str: String containing day abbreviations (e.g., "MWF", "TTh", "Mon/Wed/Fri")
        
        Returns:
            List of weekday numbers (0=Monday, 6=Sunday), sorted and with duplicates removed.
            Example: "MWF" returns [0, 2, 4]
        """
        # Map of day abbreviations to weekday numbers
        # Python uses 0=Monday, 1=Tuesday, etc.
        day_map = {
            'M': 0, 'Mon': 0, 'Monday': 0,
            'T': 1, 'Tue': 1, 'Tuesday': 1,
            'W': 2, 'Wed': 2, 'Wednesday': 2,
            'Th': 3, 'Thu': 3, 'Thursday': 3,
            'F': 4, 'Fri': 4, 'Friday': 4,
            'S': 5, 'Sat': 5, 'Saturday': 5,
            'Su': 6, 'Sun': 6, 'Sunday': 6,
        }
        
        days = []
        days_str_upper = days_str.upper()  # Convert to uppercase for case-insensitive matching
        
        # Handle common patterns found in course outlines
        # Check for Monday (M) - but make sure it's not part of "MT" or "MW"
        if 'M' in days_str_upper and days_str_upper.index('M') < len(days_str_upper) - 1:
            # Make sure the next character isn't 'T' (which would be part of "MT" or "MW")
            if days_str_upper[days_str_upper.index('M') + 1] != 'T':
                days.append(0)  # Monday
        
        # Check for Tuesday (T) or Thursday (TH)
        if 'T' in days_str_upper:
            idx = days_str_upper.index('T')
            # If next character is 'H', it's Thursday
            if idx + 1 < len(days_str_upper) and days_str_upper[idx + 1] == 'H':
                days.append(3)  # Thursday
            else:
                days.append(1)  # Tuesday
        
        # Check for Wednesday (W)
        if 'W' in days_str_upper:
            days.append(2)  # Wednesday
        
        # Check for Thursday (TH or THU) - in case it wasn't caught above
        if 'TH' in days_str_upper or 'THU' in days_str_upper:
            days.append(3)  # Thursday
        
        # Check for Friday (F)
        if 'F' in days_str_upper:
            days.append(4)  # Friday
        
        # Remove duplicates and sort the list
        # This ensures we return a clean, sorted list like [0, 2, 4] for "MWF"
        return sorted(list(set(days)))
    
    def _classify_assessment_type(self, text: str) -> str:
        """Classify assessment type from text."""
        text_lower = text.lower()
        if "assignment" in text_lower or "hw" in text_lower or "homework" in text_lower:
            return "assignment"
        elif "lab report" in text_lower or "laboratory report" in text_lower:
            return "lab_report"
        elif "quiz" in text_lower:
            return "quiz"
        elif "midterm" in text_lower or "mid-term" in text_lower:
            return "midterm"
        elif "final" in text_lower:
            return "final"
        elif "project" in text_lower:
            return "project"
        else:
            return "other"
    
    def _extract_weight(self, text: str) -> Optional[float]:
        """Extract weight percentage from text."""
        weight_pattern = r'(\d+(?:\.\d+)?)\s*%'
        match = re.search(weight_pattern, text)
        if match:
            return float(match.group(1))
        return None
    
    def _extract_relative_rules(self, text: str) -> List[Tuple[str, str]]:
        """Extract relative deadline rules.
        
        Returns:
            List of (rule_text, anchor) tuples
        """
        rules = []
        
        # Pattern for relative rules
        rule_patterns = [
            (r'due\s+(\d+)\s+hours?\s+after\s+(the\s+)?(lab|tutorial|lecture)', 'hours'),
            (r'due\s+(\d+)\s+days?\s+after\s+(the\s+)?(lab|tutorial|lecture)', 'days'),
            (r'due\s+(\d+)\s+weeks?\s+after\s+(the\s+)?(lab|tutorial|lecture)', 'weeks'),
        ]
        
        for pattern, unit in rule_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                anchor = match.group(-1)  # lab, tutorial, or lecture
                rule_text = match.group(0)
                rules.append((rule_text, anchor))
        
        return rules

