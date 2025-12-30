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
        # Handle formats like "M/W/F 9:30 – 10:20" or "MWF 9:30-10:20" or "Lecture M/W/F 9:30-10:20"
        # Look for "Timetabled Sessions" or "Component Date(s) Time" section first
        schedule_patterns = [
            r'Lecture\s+([M/T/W/Th/F/S]+)\s+(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})\s*(?:AM|PM)?',  # "Lecture M/W/F 9:30-10:20 AM"
            r'([M/T/W/Th/F/S]+)\s+(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})\s*(?:AM|PM)?',  # "M/W/F 9:30-10:20 AM" (standalone)
            r'(?:Lecture|LEC|Class|Section)\s*(\d{3})?\s*[:\s]+([M/T/W/Th/F/S]+)\s+(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})',  # "Lecture M/W/F 9:30-10:20"
            r'(?:Lecture|LEC)\s*([MTWThFS]+)\s+(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})',  # "Lecture MWF 9:30-10:20"
        ]
        
        matches = []
        for pattern in schedule_patterns:
            for match in re.finditer(pattern, search_text, re.IGNORECASE):
                matches.append(match)
        
        for match in matches:
            # Handle different pattern groups
            groups = match.groups()
            try:
                if len(groups) == 6:  # First pattern with section ID
                    section_id = groups[0] or ""
                    days_str = groups[1]
                    start_hour = int(groups[2])
                    start_min = int(groups[3])
                    end_hour = int(groups[4])
                    end_min = int(groups[5])
                elif len(groups) == 4:  # Second/third pattern without section ID
                    section_id = ""
                    days_str = groups[0]
                    start_hour = int(groups[1])
                    start_min = int(groups[2])
                    end_hour = int(groups[3])
                    end_min = int(groups[4])
                else:
                    continue
                
                # Parse days of week
                days_of_week = self._parse_days_of_week(days_str)
                if not days_of_week:
                    continue  # Skip if we couldn't parse days
                
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
            except (ValueError, IndexError) as e:
                # Skip matches that don't parse correctly
                continue
        
        return sections
    
    def extract_lab_sections(self) -> List[SectionOption]:
        """Extract lab section schedules.
        
        Returns:
            List of SectionOption objects for labs
        """
        sections = []
        search_text = "\n".join([text for _, text in self.pages_text[:5]])
        
        # Pattern for lab schedules - similar to lecture patterns
        lab_patterns = [
            r'(?:Lab|LAB|Laboratory|Tutorial|TUT)\s*(\d{3})?\s*[:\s]+([M/T/W/Th/F/S]+)\s+(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})',
            r'(?:Lab|LAB|Laboratory|Tutorial|TUT)\s*([MTWThFS]+)\s+(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})',
        ]
        
        matches = []
        for pattern in lab_patterns:
            for match in re.finditer(pattern, search_text, re.IGNORECASE):
                matches.append(match)
        
        for match in matches:
            groups = match.groups()
            try:
                if len(groups) == 5:  # First pattern with section ID
                    section_id = groups[0] or ""
                    days_str = groups[1]
                    start_hour = int(groups[2])
                    start_min = int(groups[3])
                    end_hour = int(groups[4])
                    end_min = int(groups[5])
                elif len(groups) == 4:  # Second pattern without section ID
                    section_id = ""
                    days_str = groups[0]
                    start_hour = int(groups[1])
                    start_min = int(groups[2])
                    end_hour = int(groups[3])
                    end_min = int(groups[4])
                else:
                    continue
                
                days_of_week = self._parse_days_of_week(days_str)
                if not days_of_week:
                    continue  # Skip if we couldn't parse days
                
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
            except (ValueError, IndexError) as e:
                # Skip matches that don't parse correctly
                continue
        
        return sections
    
    def extract_assessments(self) -> List[AssessmentTask]:
        """Extract assessment information from PDF.
        
        This function searches for the "Assessment and Evaluation" section and extracts
        assessment information from the table. It handles various formats including:
        - Table format with columns: Assessment, Format, Weight, Due Date, Flexibility
        - Multiple due dates (e.g., PeerWise assignments)
        - Date ranges (e.g., "December exam period")
        - Relative dates (e.g., "24 hours after lab")
        
        Returns:
            List of AssessmentTask objects with extracted information
        """
        assessments = []
        # Search entire PDF for assessments
        full_text = "\n".join([text for _, text in self.pages_text])
        
        # First, try to extract from assessment table (more reliable)
        table_assessments = self._extract_assessments_from_table(full_text)
        if table_assessments:
            assessments.extend(table_assessments)
            # If we found assessments in table, skip pattern matching (avoid duplicates)
            # But still check for relative rules
            use_pattern_matching = False
        else:
            use_pattern_matching = True
        
        if use_pattern_matching:
            # Fallback to pattern matching if table extraction didn't work
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
                    groups = match.groups()
                # Determine assessment type and title
                if 'Quiz' in match.group(0):
                    assessment_type = 'quiz'
                    # Extract quiz number if available
                    quiz_num = groups[1] if len(groups) > 1 and groups[1].isdigit() else (groups[2] if len(groups) > 2 and groups[2].isdigit() else '')
                    title = f"Quiz {quiz_num}" if quiz_num else "Quiz"
                elif 'Midterm' in match.group(0):
                    assessment_type = 'midterm'
                    title = "Midterm Exam"
                elif 'Final' in match.group(0):
                    assessment_type = 'final'
                    title = "Final Exam"
                elif 'Assignment' in match.group(0) or 'HW' in match.group(0):
                    assessment_type = 'assignment'
                    title = match.group(0)[:50]
                else:
                    assessment_type = 'other'
                    title = match.group(0)[:50]
                
                # Try to extract due date - look for month and day in the match
                due_date_str = None
                # Check last groups for date info
                for i in range(len(groups) - 1, -1, -1):
                    if groups[i] and (groups[i].isdigit() or any(month in groups[i] for month in ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'])):
                        # Try to construct date string
                        if i > 0 and groups[i-1]:
                            # Month name and day
                            due_date_str = f"{groups[i-1]} {groups[i]}, 2025"
                        elif groups[i].isdigit() and i > 0:
                            # Look for month before this group
                            context = match.group(0)[:match.start() + match.end()]
                            month_match = re.search(r'(Oct|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|September|October|November|December|January|February|March|April|May|June|July|August)', context, re.IGNORECASE)
                            if month_match:
                                due_date_str = f"{month_match.group(0)} {groups[i]}, 2025"
                        break
                
                due_datetime = None
                if due_date_str:
                    parsed_date = dateparser.parse(due_date_str)
                    if parsed_date:
                        # Default to 11:59 PM if no time specified
                        due_datetime = datetime.combine(
                            parsed_date.date(),
                            time(23, 59)
                        )
                
                # Try to extract weight from surrounding text
                weight = self._extract_weight(match.group(0))
                
                assessment = AssessmentTask(
                    title=title,
                    type=assessment_type,
                    weight_percent=weight,
                    due_datetime=due_datetime,
                    confidence=0.7 if due_datetime else 0.4,
                    source_evidence=f"Found: {match.group(0)[:100]}",
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
        
        # Deduplicate: Remove assessments with same title but no date/weight if we have a better version
        # Normalize titles for comparison (remove "In Class", case-insensitive, extract core name)
        def normalize_title(title):
            # Remove common prefixes and normalize
            normalized = title.lower().strip()
            normalized = re.sub(r'^in\s+class\s+', '', normalized)
            normalized = re.sub(r'\s+', ' ', normalized)
            # Extract core: "quiz 1", "midterm test", "final exam"
            normalized = re.sub(r'^(quiz|midterm|final|assignment|lab\s+report)\s*(\d+)?.*', r'\1 \2', normalized).strip()
            return normalized
        
        seen_titles = {}
        deduplicated = []
        for assessment in assessments:
            title_normalized = normalize_title(assessment.title)
            # Check if we already have a better version (with date and weight)
            if title_normalized in seen_titles:
                existing = seen_titles[title_normalized]
                # Keep the one with date and weight, or higher confidence
                if (assessment.due_datetime and assessment.weight_percent and 
                    (not existing.due_datetime or not existing.weight_percent)):
                    # Replace existing with better one
                    deduplicated.remove(existing)
                    deduplicated.append(assessment)
                    seen_titles[title_normalized] = assessment
                elif assessment.confidence > existing.confidence:
                    # Replace with higher confidence
                    deduplicated.remove(existing)
                    deduplicated.append(assessment)
                    seen_titles[title_normalized] = assessment
                # Otherwise skip this duplicate
            else:
                seen_titles[title_normalized] = assessment
                deduplicated.append(assessment)
        
        return deduplicated
    
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
        
        # Pattern for course code: Can be "PHYS 3140A" or "Physiology 3140A" or "Phys 3140A"
        # Try multiple patterns to catch different formats - order matters!
        course_code_patterns = [
            r'(Physiology|Physics|Phys)\s+(\d{3,4}[A-Z]?)',  # "Physiology 3140A" - check this first!
            r'([A-Z]{2,4})\s+(\d{3,4}[A-Z]?)',  # "PHYS 3140A" or "CS 101"
        ]
        
        course_code = None
        for pattern in course_code_patterns:
            match = re.search(pattern, first_page, re.IGNORECASE)
            if match:
                dept_raw = match.group(1).upper()
                number = match.group(2)
                
                # Map common department names to abbreviations
                dept_map = {
                    'PHYSIOLOGY': 'PHYS',
                    'PHYSICS': 'PHYS',
                    'PHYS': 'PHYS',
                    'COMPUTER SCIENCE': 'CS',
                    'MATHEMATICS': 'MATH',
                    'MATH': 'MATH',
                    'CHEMISTRY': 'CHEM',
                    'BIOLOGY': 'BIO',
                }
                
                # Try to find abbreviation in map, otherwise use first 4 chars
                dept = dept_map.get(dept_raw, dept_raw[:4])
                course_code = f"{dept} {number}"
                break
        
        # Course name is usually on first page, often on the same line as course code
        # Look for patterns like "Cellular Physiology-Physiology 3140A" or "Introduction to..."
        course_name = None
        
        # Try to find course name - look for text before or after course code
        # Pattern: Look for line with course code, extract descriptive text
        name_patterns = [
            r'([A-Z][^-\n]+?)[-–]\s*(?:Physiology|Physics|Phys)\s+\d+',  # "Cellular Physiology-Physiology 3140A"
            r'(?:Physiology|Physics|Phys)\s+\d+[A-Z]?\s*[-–]\s*([^\n]+)',  # "Physiology 3140A - Course Name"
            r'([A-Z][^.\n]{10,80}?)(?:\s+Physiology|\s+Physics|\s+Phys)\s+\d+',  # Text before "Physiology 3140A"
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, first_page, re.IGNORECASE)
            if match:
                course_name = match.group(1).strip()
                # Clean up common prefixes/suffixes
                course_name = re.sub(r'^(Course|Outline|Department of)\s+', '', course_name, flags=re.IGNORECASE)
                course_name = course_name.strip(' -–')
                if len(course_name) > 5:  # Only use if it's substantial
                    break
        
        # Fallback: if we found course code but not name, look for text on same line
        if not course_name and course_code:
            # Find line containing course code
            for line in first_page.split('\n'):
                if re.search(r'\d{3,4}[A-Z]?', line):  # Line has course number
                    # Extract descriptive text from that line
                    cleaned = re.sub(r'Physiology\s+\d+[A-Z]?.*', '', line, flags=re.IGNORECASE)
                    cleaned = cleaned.strip(' -–')
                    if len(cleaned) > 5:
                        course_name = cleaned[:100]
                        break
        
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
    
    def _extract_assessments_from_table(self, text: str) -> List[AssessmentTask]:
        """Extract assessments from the assessment table in the PDF.
        
        Looks for the "Assessment and Evaluation" section and parses the table
        with columns: Assessment, Format, Weight, Due Date, Flexibility.
        
        Args:
            text: Full text of the PDF
            
        Returns:
            List of AssessmentTask objects extracted from the table
        """
        assessments = []
        
        # Find the assessment section - look for "Assessment and Evaluation" title
        # Try multiple patterns to find the section
        assessment_section_patterns = [
            r'(?:8\.\s*)?Assessment\s+(?:and\s+)?Evaluation[^\n]*(?:\n[^\n]*){0,500}',  # More lines after title
            r'Assessment\s+(?:and\s+)?Evaluation\s+Policy[^\n]*(?:\n[^\n]*){0,500}',
            r'Assessment\s+(?:and\s+)?Evaluation[^\n]*(?:\n[^\n]*){0,1000}',  # Even more lines
        ]
        
        section_text = None
        for pattern in assessment_section_patterns:
            section_match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if section_match:
                section_text = section_match.group(0)
                # Find where the section ends (next major section or end of document)
                # Look for next numbered section or major heading
                next_section_match = re.search(r'\n(?:\d+\.\s+)?(?:Course|Instructor|Textbook|Schedule|Policies|Grading|Contact|Information|General|Appendix)', section_text, re.IGNORECASE)
                if next_section_match:
                    section_text = section_text[:next_section_match.start()]
                break
        
        if not section_text:
            # Fallback: search for any mention of assessment table
            assessment_mentions = re.finditer(r'Assessment[^\n]*(?:\n[^\n]*){0,200}', text, re.IGNORECASE)
            for match in assessment_mentions:
                if 'weight' in match.group(0).lower() or 'due' in match.group(0).lower():
                    section_text = match.group(0)
                    break
        
        if not section_text:
            return assessments
        
        # Look for table header: "Assessment Format Weight Due Date Flexibility"
        header_pattern = r'Assessment\s+(?:Format\s+)?(?:Weight|Weighting)\s+(?:Due\s+)?Date\s*(?:Flexibility)?'
        header_match = re.search(header_pattern, section_text, re.IGNORECASE)
        
        if not header_match:
            # Try alternative header patterns
            header_pattern = r'Assessment\s+Format\s+Weight'
            header_match = re.search(header_pattern, section_text, re.IGNORECASE)
        
        if not header_match:
            return assessments
        
        # Extract text after header (the table rows)
        table_start = header_match.end()
        # Extract more text to capture all assessments (up to 5000 chars)
        table_text = section_text[table_start:table_start+5000]  # Increased limit
        
        # Split table text into lines and process row by row
        # Look for assessment rows - each assessment typically starts with a name
        # Filter out empty/short lines to avoid index issues
        all_lines = table_text.split('\n')
        lines = [l.strip() for l in all_lines if l.strip() and len(l.strip()) >= 3]
        
        i = 0
        while i < len(lines):
            line = lines[i]
            print(f"DEBUG: Processing line {i}: {line[:60]}")
            
            # Check if this line starts an assessment - handle multi-line names
            assessment_name_match = None
            assessment_name = None
            
            # IMPORTANT: Check for Midterm Test FIRST, before other patterns
            # This ensures Midterm Tests are caught even if they appear in unexpected positions
            if 'Midterm' in line and 'Test' in line:
                match = re.search(r'Midterm\s+(?:Test|TEST)\s+(\d+)', line, re.IGNORECASE)
                if match:
                    midterm_num = match.group(1)
                    assessment_name = f"Midterm Test {midterm_num}"
                    row_lines = [line]
                    j = i + 1
                    print(f"DEBUG: Found Midterm Test {midterm_num} at line {i}: {line[:80]}")
                else:
                    # Try alternative pattern - maybe "Midterm" and number are separated
                    alt_match = re.search(r'Midterm[^\d]*(\d+)', line, re.IGNORECASE)
                    if alt_match:
                        midterm_num = alt_match.group(1)
                        assessment_name = f"Midterm Test {midterm_num}"
                        row_lines = [line]
                        j = i + 1
                        print(f"DEBUG: Found Midterm Test {midterm_num} (alt pattern) at line {i}: {line[:80]}")
                    else:
                        i += 1
                        continue
            
            # First, check if this line starts with "PeerWise" - the assignment number is on next line
            elif re.match(r'^PeerWise', line, re.IGNORECASE):
                # Look ahead to next line for "Assignment X"
                if i + 1 < len(lines):
                    next_line = lines[i + 1]  # Already stripped in filtered lines
                    assign_match = re.search(r'Assignment\s+(\d+)', next_line, re.IGNORECASE)
                    if assign_match:
                        assessment_name = f"PeerWise Assignment {assign_match.group(1)}"
                        # Include next line in row_lines
                        row_lines = [line, next_line]
                        i += 1  # Skip next line since we're including it
                        j = i + 1  # Start collecting from line after that
                    else:
                        # Just "PeerWise" without assignment number
                        assessment_name = "PeerWise Assignment"
                        row_lines = [line]
                        j = i + 1
                else:
                    assessment_name = "PeerWise Assignment"
                    row_lines = [line]
                    j = i + 1
            
            # Check for "Assignment X Slide redesign" - might be split
            # BUT: Skip if this is part of a PeerWise description (already handled above)
            elif re.match(r'^Assignment\s+(\d+)', line, re.IGNORECASE) and not any('peerwise' in prev_line.lower() for prev_line in lines[max(0, i-2):i]):
                assign_num_match = re.match(r'^Assignment\s+(\d+)', line, re.IGNORECASE)
                assign_num = assign_num_match.group(1) if assign_num_match else None
                
                # Check if next line has "Slide redesign"
                if i + 1 < len(lines):
                    next_line = lines[i + 1]  # Already stripped
                    if 'slide redesign' in next_line.lower():
                        if 'teach' in next_line.lower():
                            assessment_name = f"Assignment {assign_num} Slide redesign & Teach"
                        else:
                            assessment_name = f"Assignment {assign_num} Slide redesign"
                        row_lines = [line, next_line]
                        i += 1
                        j = i + 1
                    else:
                        # Just "Assignment X" - might be PeerWise (already handled above) or other
                        assessment_name = f"Assignment {assign_num}"
                        row_lines = [line]
                        j = i + 1
                else:
                    assessment_name = f"Assignment {assign_num}"
                    row_lines = [line]
                    j = i + 1
            
            # Check for other patterns - Midterm Test (can appear anywhere in line, not just start)
            # Make this check more robust - check if line contains "Midterm Test" followed by a number
            elif 'Midterm' in line and 'Test' in line:
                match = re.search(r'Midterm\s+(?:Test|TEST)\s+(\d+)', line, re.IGNORECASE)
                if match:
                    midterm_num = match.group(1)
                    assessment_name = f"Midterm Test {midterm_num}"
                    row_lines = [line]
                    j = i + 1
                    print(f"DEBUG: Found Midterm Test {midterm_num} at line {i}: {line[:80]}")
                else:
                    # Try alternative pattern - maybe "Midterm" and number are separated
                    alt_match = re.search(r'Midterm[^\d]*(\d+)', line, re.IGNORECASE)
                    if alt_match:
                        midterm_num = alt_match.group(1)
                        assessment_name = f"Midterm Test {midterm_num}"
                        row_lines = [line]
                        j = i + 1
                        print(f"DEBUG: Found Midterm Test {midterm_num} (alt pattern) at line {i}: {line[:80]}")
                    else:
                        i += 1
                        continue
            
            elif re.match(r'^Final\s+(?:Exam|EXAM)', line, re.IGNORECASE):
                assessment_name = "Final Exam"
                row_lines = [line]
                j = i + 1
            
            elif re.match(r'^(?:Optional\s+)?(?:Bonus|BONUS)', line, re.IGNORECASE):
                assessment_name = "Optional Bonus Assignment"
                row_lines = [line]
                j = i + 1
            
            # Fallback to general pattern
            else:
                general_match = re.search(r'((?:In\s+Class\s+)?(?:Quiz|QUIZ)\s+\d+|(?:Midterm|MIDTERM|Mid-term)\s+(?:Test|Exam)?\s*\d*|(?:Final\s+)?(?:Exam|EXAM|Examination)|(?:Assignment|ASSIGNMENT)\s+\d+|(?:PeerWise|Peerwise)\s+(?:Assignment|ASSIGNMENT)\s+\d+|(?:Lab\s+)?(?:Report|REPORT)|(?:Slide\s+)?(?:redesign|Redesign)(?:\s+&\s+Teach)?|(?:Participation|Participation\s+Grade)|(?:Project|PROJECT)|(?:Presentation|PRESENTATION)|(?:Paper|PAPER)|(?:Essay|ESSAY)|(?:Reflection|REFLECTION)|(?:Optional\s+)?(?:Bonus|BONUS)\s+(?:Assignment|ASSIGNMENT)?)', line, re.IGNORECASE)
                if general_match:
                    assessment_name_match = general_match
                    assessment_name = general_match.group(1)
                    row_lines = [line]
                    j = i + 1
                else:
                    i += 1
                    continue
            
            if assessment_name:
                # Found an assessment - collect continuation lines (if not already done above)
                if 'row_lines' not in locals() or 'j' not in locals():
                    row_lines = [line]
                    j = i + 1
                
                # Collect continuation lines (up to 10 more lines to capture multi-line entries)
                while j < len(lines) and j < i + 11:
                    next_line = lines[j]  # Already stripped in filtered array
                    # Stop if we hit another assessment or section header
                    # Be more specific: only stop if it's clearly a new assessment (not part of description)
                    # Check for assessment names at start of line, or section headers
                    stop_patterns = [
                        r'^(?:In\s+Class\s+)?(?:Quiz|QUIZ)\s+\d+',  # Quiz 1, Quiz 2, etc.
                        r'^Midterm\s+(?:Test|TEST)\s+\d+',  # Midterm Test 1, Midterm Test 2
                        r'^(?:Final\s+)?(?:Exam|EXAM)',  # Final Exam
                        r'^PeerWise',  # New PeerWise assignment
                        r'^Assignment\s+\d+\s+(?:Slide|Augment)',  # Assignment X Slide redesign (new assessment)
                        r'^(?:Optional\s+)?(?:Bonus|BONUS)',  # Optional Bonus
                        r'^Designated',  # Section header
                        r'^Information',  # Section header
                        r'^General',  # Section header
                    ]
                    should_stop = False
                    for pattern in stop_patterns:
                        if re.match(pattern, next_line, re.IGNORECASE):
                            should_stop = True
                            print(f"DEBUG: Stopping collection at line {j} due to pattern match: {next_line[:60]}")
                            break
                    
                    if should_stop:
                        # Don't include this line in row_lines, but j now points to it
                        # This ensures the next iteration will process this line
                        # BUT: Make sure we don't skip the line - the while loop will increment i
                        # Actually, we need to make sure i gets set correctly after processing
                        break
                    
                    if next_line and len(next_line) > 3:
                        row_lines.append(next_line)
                    j += 1
                
                row_text = ' '.join(row_lines)
                
                # Classify type
                assessment_type = self._classify_assessment_type(assessment_name)
                
                # Extract weight
                weight = self._extract_weight(row_text)
                
                # Extract due date(s)
                due_dates = []
                # Pattern for dates: "October 1", "Oct 1", "November 14th", "Sunday, Oct 19", "December exam period"
                # Handle ordinal suffixes (st, nd, rd, th) by making them optional
                date_patterns = [
                    r'(?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday),?\s+(Oct|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|September|October|November|December|January|February|March|April|May|June|July|August)\s+(\d{1,2})(?:st|nd|rd|th)?',
                    r'(Oct|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|September|October|November|December|January|February|March|April|May|June|July|August)\s+(\d{1,2})(?:st|nd|rd|th)?',
                ]
                
                for date_pattern in date_patterns:
                    date_matches = re.finditer(date_pattern, row_text, re.IGNORECASE)
                    for date_match in date_matches:
                        if len(date_match.groups()) == 2:
                            month = date_match.group(1)
                            day = date_match.group(2)
                            
                            # Determine year
                            year = 2025
                            if '2026' in row_text or any(m in row_text for m in ['January', 'February', 'March', 'April']):
                                year = 2026
                            
                            date_str = f"{month} {day}, {year}"
                            # Avoid duplicates
                            if date_str not in due_dates:
                                due_dates.append(date_str)
                
                # Handle "December exam period" or date ranges
                if not due_dates and ('exam period' in row_text.lower() or ('december' in row_text.lower() and 'exam' in row_text.lower())):
                    # For final exam, use a placeholder date that will be resolved later
                    due_dates.append("December 15, 2025")  # Default, will be refined
                
                # Extract time if present
                time_str = None
                # Look for time patterns: "6-8 PM", "11:59 PM", "in class"
                time_match = re.search(r'(\d{1,2})(?:[:–-](\d{2}))?\s*(?:[-–]\s*(\d{1,2})(?:[:–-](\d{2}))?)?\s*(AM|PM)', row_text, re.IGNORECASE)
                if time_match:
                    time_str = time_match.group(0)
                elif 'in class' in row_text.lower():
                    time_str = 'in class'
                
                # Create assessment(s) - handle multiple due dates (e.g., PeerWise)
                print(f"DEBUG: Assessment '{assessment_name}' - found {len(due_dates)} dates: {due_dates}")
                if due_dates:
                    for date_idx, due_date_str in enumerate(due_dates[:2]):  # Limit to 2 dates per assessment
                        parsed_date = dateparser.parse(due_date_str)
                        print(f"DEBUG: Parsing date '{due_date_str}' -> {parsed_date}")
                        if parsed_date:
                            # Handle time
                            hour = 23
                            minute = 59
                            if time_str:
                                if 'in class' in time_str.lower():
                                    hour = 10
                                    minute = 0
                                else:
                                    time_match = re.search(r'(\d{1,2})(?:[:–-](\d{2}))?\s*(AM|PM)', time_str, re.IGNORECASE)
                                    if time_match:
                                        hour = int(time_match.group(1))
                                        minute = int(time_match.group(2)) if time_match.group(2) else 0
                                        if time_match.group(3).upper() == 'PM' and hour != 12:
                                            hour += 12
                                        elif time_match.group(3).upper() == 'AM' and hour == 12:
                                            hour = 0
                            
                            due_datetime = datetime.combine(parsed_date.date(), time(hour, minute))
                            
                            # Create title - add suffix for multiple dates (PeerWise)
                            title = assessment_name
                            if len(due_dates) > 1 and 'peerwise' in row_text.lower():
                                if date_idx == 0:
                                    title = f"{assessment_name} (Author)"
                                elif date_idx == 1:
                                    title = f"{assessment_name} (Answer)"
                            
                            assessment = AssessmentTask(
                                title=title,
                                type=assessment_type,
                                weight_percent=weight,
                                due_datetime=due_datetime,
                                confidence=0.8 if weight and due_datetime else 0.5,
                                source_evidence=row_text[:200],
                                needs_review=(due_datetime is None or weight is None)
                            )
                            assessments.append(assessment)
                            print(f"DEBUG: Added assessment '{title}' to list (total: {len(assessments)})")
                else:
                    # If no dates found, still create assessment without date
                    print(f"DEBUG: No dates found for '{assessment_name}', creating assessment without date")
                    assessment = AssessmentTask(
                        title=assessment_name,
                        type=assessment_type,
                        weight_percent=weight,
                        due_datetime=None,
                        confidence=0.4,
                        source_evidence=row_text[:200],
                        needs_review=True
                    )
                    assessments.append(assessment)
                    print(f"DEBUG: Added assessment '{assessment_name}' to list (total: {len(assessments)})")
                
                # Move to next potential assessment
                print(f"DEBUG: Finished processing '{assessment_name}', moving from line {i} to line {j}")
                i = j
            else:
                i += 1
        
        return assessments
    
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

