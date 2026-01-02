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
        assessment information. It supports two formats:
        - Table format: Structured tables with columns (Assessment, Format, Weight, Due Date, Flexibility)
        - Text format: Numbered/bulleted lists in prose (fallback)
        
        Returns:
            List of AssessmentTask objects with extracted information
        """
        assessments = []
        
        # Get full text for fallback extraction
        full_text = "\n".join([text for _, text in self.pages_text])
        
        # First, try table-based extraction (more reliable for structured PDFs)
        table_assessments = self._extract_assessments_from_table_structured()
        if table_assessments and len(table_assessments) > 0:
            # Validate that we got meaningful assessments (not just empty ones)
            valid_assessments = [a for a in table_assessments if a.title and len(a.title.strip()) > 2]
            if len(valid_assessments) > 0:
                assessments.extend(valid_assessments)
                # If we found valid assessments in table, return early (avoid duplicates)
                return assessments
        
        # Fallback to text-based extraction (for PDFs without structured tables)
        text_assessments = self._extract_assessments_from_table(full_text)
        if text_assessments:
            assessments.extend(text_assessments)
        
        # Also search for relative rules
        if assessments:
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
            # Extract core: "quiz 1", "midterm test 1", "final exam"
            # Look for number anywhere after the type (not just immediately after)
            match = re.search(r'^(quiz|midterm|final|assignment|lab\s+report).*?(\d+)', normalized)
            if match:
                type_name = match.group(1)
                number = match.group(2)
                normalized = f"{type_name} {number}"
            else:
                # No number found, just extract the type
                normalized = re.sub(r'^(quiz|midterm|final|assignment|lab\s+report).*', r'\1', normalized).strip()
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
        """Parse day abbreviations from text like "MWF", "TTh", "M/W/F", or "Mon/Wed/Fri".
        
        This function converts day abbreviations (like "MWF" for Monday/Wednesday/Friday)
        into a list of weekday numbers. The numbers follow Python's weekday convention:
        0 = Monday, 1 = Tuesday, 2 = Wednesday, 3 = Thursday, 4 = Friday, 5 = Saturday, 6 = Sunday.
        
        Handles multiple formats:
        - Slash-separated: "M/W/F", "T/Th", "Mon/Wed/Fri"
        - Concatenated: "MWF", "TTh", "MTWThF"
        - Full names: "Monday/Wednesday/Friday"
        
        Args:
            days_str: String containing day abbreviations (e.g., "MWF", "TTh", "Mon/Wed/Fri", "M/W/F")
        
        Returns:
            List of weekday numbers (0=Monday, 6=Sunday), sorted and with duplicates removed.
            Example: "MWF" or "M/W/F" returns [0, 2, 4]
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
        days_str = days_str.strip()
        
        # Step 1: If contains "/", split by "/" and parse each part
        if '/' in days_str:
            parts = [part.strip() for part in days_str.split('/')]
            for part in parts:
                if not part:
                    continue
                # Try to match the part to a day
                part_lower = part.lower()
                # Check full names first (longest match)
                matched = False
                for day_name, day_num in sorted(day_map.items(), key=lambda x: -len(x[0])):
                    if part_lower == day_name.lower() or part_lower.startswith(day_name.lower()):
                        days.append(day_num)
                        matched = True
                        break
                if not matched:
                    # Try single character or abbreviation
                    if len(part) == 1:
                        # Single character: M, T, W, F, S
                        if part.upper() in day_map:
                            days.append(day_map[part.upper()])
                    elif part.upper() in ['TH', 'THU']:
                        days.append(3)  # Thursday
                    elif part.upper() in day_map:
                        days.append(day_map[part.upper()])
        else:
            # Step 2: Handle concatenated format (MWF, TTh, etc.)
            # Need to handle "Th" as a special case (two characters for Thursday)
            days_str_upper = days_str.upper()
            i = 0
            while i < len(days_str_upper):
                # Check for full day names first (longest matches)
                if days_str_upper[i:i+8] == 'THURSDAY':
                    days.append(3)  # Thursday
                    i += 8
                elif days_str_upper[i:i+8] == 'WEDNESDAY':
                    days.append(2)  # Wednesday
                    i += 8
                elif days_str_upper[i:i+7] == 'SATURDAY':
                    days.append(5)  # Saturday
                    i += 7
                elif days_str_upper[i:i+6] == 'TUESDAY':
                    days.append(1)  # Tuesday
                    i += 6
                elif days_str_upper[i:i+6] == 'MONDAY':
                    days.append(0)  # Monday
                    i += 6
                elif days_str_upper[i:i+6] == 'FRIDAY':
                    days.append(4)  # Friday
                    i += 6
                elif days_str_upper[i:i+6] == 'SUNDAY':
                    days.append(6)  # Sunday
                    i += 6
                # Check for Thursday abbreviation (Th, TH, Thu, THU) - must come before single 'T'
                elif i < len(days_str_upper) - 1 and days_str_upper[i:i+2] == 'TH':
                    days.append(3)  # Thursday
                    i += 2
                    # Check if there's 'U' after (THU)
                    if i < len(days_str_upper) and days_str_upper[i] == 'U':
                        i += 1
                else:
                    # Single character match
                    char = days_str_upper[i]
                    if char in day_map:
                        # Special handling: T could be Tuesday or part of Thursday
                        if char == 'T':
                            # Check if next char is 'H' (Thursday)
                            if i + 1 < len(days_str_upper) and days_str_upper[i+1] == 'H':
                                # This is Thursday - handle it here
                                days.append(3)  # Thursday
                                i += 2  # Skip both T and H
                                # Check if there's 'U' after (THU)
                                if i < len(days_str_upper) and days_str_upper[i] == 'U':
                                    i += 1
                            else:
                                # Just Tuesday
                                days.append(1)  # Tuesday
                                i += 1
                        else:
                            days.append(day_map[char])
                            i += 1
                    else:
                        i += 1  # Skip unknown character
        
        # Remove duplicates and sort the list
        # This ensures we return a clean, sorted list like [0, 2, 4] for "MWF" or "M/W/F"
        return sorted(list(set(days)))
    
    def _extract_assessments_from_table_structured(self) -> List[AssessmentTask]:
        """Extract assessments from structured tables using pdfplumber.
        
        This method uses pdfplumber's table extraction to get structured data,
        which is more reliable than text parsing for table-based PDFs.
        
        Returns:
            List of AssessmentTask objects extracted from tables
        """
        assessments = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            # Find pages that might contain assessment tables
            # Usually in the middle-to-end of the document
            for page_num, page in enumerate(pdf.pages, 1):
                tables = page.extract_tables()
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # Check if this is an assessment table
                    if self._is_assessment_table(table):
                        # Extract assessments from this table
                        table_assessments = self._extract_from_table(table)
                        if table_assessments:
                            assessments.extend(table_assessments)
                            # Found assessment table, can stop searching
                            return assessments
        
        return assessments
    
    def _is_assessment_table(self, table: List[List]) -> bool:
        """Check if a table is an assessment/evaluation table.
        
        Args:
            table: List of rows, where each row is a list of cells
            
        Returns:
            True if this appears to be an assessment table
        """
        if not table or len(table) < 2:
            return False
        
        # Check header row
        header_row = table[0]
        header_text = ' '.join([str(cell) for cell in header_row if cell]).lower()
        
        # Must have "assessment" keyword (more specific than "evaluation")
        has_assessment = 'assessment' in header_text
        if not has_assessment:
            return False
        
        # Must have weight/percentage indicator
        has_weight = any(w in header_text for w in ['weight', 'weighting', '%', 'percent'])
        
        # Must have date/due indicator
        has_date = any(d in header_text for d in ['due', 'date', 'deadline'])
        
        # Both weight AND date should be present for a valid assessment table
        # This ensures we don't match other tables that happen to have "assessment" in them
        if not (has_weight and has_date):
            return False
        
        # Additional validation: Check if data rows contain assessment-like content
        # Look at first few data rows for assessment keywords and percentages
        assessment_keywords = ['quiz', 'midterm', 'final', 'assignment', 'exam', 'report', 'lab', 'peerwise']
        keyword_count = 0
        percentage_count = 0
        
        for row in table[1:min(6, len(table))]:  # Check first 5 data rows
            row_text = ' '.join([str(cell) for cell in row if cell]).lower()
            if any(kw in row_text for kw in assessment_keywords):
                keyword_count += 1
            # Check for percentage patterns
            if re.search(r'\d+\.?\d*%', row_text):
                percentage_count += 1
        
        # Must have at least one assessment keyword and one percentage in data rows
        return keyword_count >= 1 and percentage_count >= 1
    
    def _extract_from_table(self, table: List[List]) -> List[AssessmentTask]:
        """Extract assessments from a structured table.
        
        Args:
            table: List of rows, where each row is a list of cells
            
        Returns:
            List of AssessmentTask objects
        """
        if not table or len(table) < 2:
            return []
        
        # Map columns
        column_map = self._map_table_columns(table[0])
        if not column_map:
            return []
        
        assessments = []
        current_assessment = None
        
        # Process data rows (skip header)
        for row_idx, row in enumerate(table[1:], 1):
            # Skip empty rows
            if not row or not any(cell for cell in row if cell):
                continue
            
            # Check if this is a summary row (Total, COURSE TOTAL, etc.)
            if self._is_summary_row(row, column_map):
                continue
            
            # Extract assessment name
            name = self._extract_name_from_row(row, column_map)
            
            # Extract weight and date to check if this row has meaningful data
            row_weight = self._extract_weight_from_row(row, column_map)
            row_due_datetime = self._extract_date_from_row(row, column_map)
            
            # Check if this is a continuation row:
            # 1. Empty name but has date in date column (e.g., "Due Nov 21st")
            # 2. Empty name and empty weight but has date
            # 3. Very short name (< 3 chars) with no weight and no date
            # 4. Short name that looks like a fragment AND previous assessment name suggests continuation
            is_continuation = False
            
            if not name or name.strip() == '':
                # Empty name - check if it has date (likely continuation)
                if row_due_datetime:
                    is_continuation = True
                # Or if it has no weight but previous assessment exists
                elif row_weight is None and current_assessment:
                    is_continuation = True
            elif len(name.strip()) < 3:
                # Very short name with no weight/date - likely continuation
                if row_weight is None and not row_due_datetime:
                    is_continuation = True
            elif current_assessment:
                # Check if this looks like a continuation based on previous assessment
                prev_name = current_assessment.title.lower()
                name_lower = name.lower().strip()
                
                # If name is just a single word and previous name ends with incomplete phrase
                if ' ' not in name_lower or len(name_lower) < 15:
                    # Check if previous name suggests continuation
                    if any(prev_name.endswith(word) for word in ['short', 'intro', 'methods', 'results', 'assignment', 'long', 'rotation 1:', 'rotation 1: short']):
                        # And this name is a common continuation word
                        if name_lower in ['report', 'assignment', 'quiz', 'methods', 'results', 'intro', 'references']:
                            # Also check: if current row has no weight and no date, it's likely continuation
                            if row_weight is None and not row_due_datetime:
                                is_continuation = True
            
            if is_continuation and current_assessment:
                # Merge with previous assessment
                current_assessment = self._merge_continuation_row(current_assessment, row, column_map)
                # Update the last assessment in the list
                if assessments:
                    assessments[-1] = current_assessment
                continue
            
            # Use the extracted weight and date for this row
            weight = row_weight
            due_datetime = row_due_datetime
            
            # Extract format (optional)
            format_type = self._extract_format_from_row(row, column_map)
            
            # Classify assessment type
            assessment_type = self._classify_assessment_type(name)
            
            # Determine confidence
            confidence = 0.8
            if weight is None and due_datetime is None:
                confidence = 0.3
            elif weight is None or due_datetime is None:
                confidence = 0.6
            
            # Skip if name is empty or too short (likely not a real assessment)
            if not name or len(name.strip()) < 2:
                continue
            
            # Create assessment
            assessment = AssessmentTask(
                title=name.strip(),
                type=assessment_type,
                weight_percent=weight,
                due_datetime=due_datetime,
                confidence=confidence,
                source_evidence=self._get_row_text(row, column_map),
                needs_review=(weight is None or due_datetime is None)
            )
            
            assessments.append(assessment)
            current_assessment = assessment
        
        return assessments
    
    def _map_table_columns(self, header_row: List, sample_rows: List[List] = None) -> dict:
        """Map table columns to their purpose.
        
        Handles both dense tables (all columns used) and sparse tables (columns with None/empty cells).
        
        Args:
            header_row: First row of the table (header)
            sample_rows: Optional sample data rows to help infer column positions in sparse tables
            
        Returns:
            Dictionary mapping column purpose to index, e.g. {'name': 0, 'weight': 2, 'date': 3}
        """
        column_map = {}
        
        # First pass: map by header text
        for idx, cell in enumerate(header_row):
            if not cell:
                continue
            
            cell_text = str(cell).lower().strip()
            
            # Assessment name column
            if 'assessment' in cell_text and 'name' not in column_map:
                column_map['name'] = idx
            
            # Weight column
            if ('weight' in cell_text or 'weighting' in cell_text or '%' in cell_text) and 'weight' not in column_map:
                column_map['weight'] = idx
            
            # Date column
            if ('due' in cell_text or 'date' in cell_text or 'deadline' in cell_text) and 'date' not in column_map:
                column_map['date'] = idx
            
            # Format column (optional)
            if 'format' in cell_text and 'format' not in column_map:
                column_map['format'] = idx
        
        # If we have name and at least weight or date, we're good
        if 'name' in column_map and ('weight' in column_map or 'date' in column_map):
            return column_map
        
        # Second pass: for sparse tables, try to infer column positions from data
        # Look at sample rows to find where weight and date actually appear
        if sample_rows and 'name' in column_map:
            # Find weight column by looking for percentages
            if 'weight' not in column_map:
                for row in sample_rows:
                    for idx, cell in enumerate(row):
                        if cell and re.search(r'\d+\.?\d*%', str(cell)):
                            column_map['weight'] = idx
                            break
                    if 'weight' in column_map:
                        break
            
            # Find date column by looking for date patterns
            if 'date' not in column_map:
                for row in sample_rows:
                    for idx, cell in enumerate(row):
                        if cell:
                            cell_text = str(cell).lower()
                            # Look for date indicators
                            if any(indicator in cell_text for indicator in ['oct', 'nov', 'dec', 'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'due', 'at 6:', 'at 11:', 'pm', 'am']):
                                column_map['date'] = idx
                                break
                    if 'date' in column_map:
                        break
        
        # Return mapping if we have name and at least one other column
        if 'name' in column_map and ('weight' in column_map or 'date' in column_map):
            return column_map
        
        return {}
    
    def _extract_name_from_row(self, row: List, column_map: dict) -> str:
        """Extract assessment name from a table row.
        
        Args:
            row: Table row (list of cells)
            column_map: Column mapping dictionary
            
        Returns:
            Assessment name, or empty string if not found
        """
        if 'name' not in column_map:
            return ''
        
        name_idx = column_map['name']
        if name_idx >= len(row) or not row[name_idx]:
            return ''
        
        name_cell = row[name_idx]
        # Handle multi-line cell content (join with spaces)
        if isinstance(name_cell, str):
            name = ' '.join(name_cell.split('\n'))
        else:
            name = str(name_cell)
        
        return name.strip()
    
    def _extract_weight_from_row(self, row: List, column_map: dict) -> Optional[float]:
        """Extract weight percentage from a table row.
        
        Args:
            row: Table row (list of cells)
            column_map: Column mapping dictionary
            
        Returns:
            Weight as float (percentage), or None if not found or completion-based
        """
        if 'weight' not in column_map:
            return None
        
        weight_idx = column_map['weight']
        if weight_idx >= len(row) or not row[weight_idx]:
            return None
        
        weight_cell = row[weight_idx]
        weight_text = str(weight_cell).strip() if weight_cell else ''
        
        # Check for completion-based assessments
        if 'completion' in weight_text.lower() or weight_text.endswith('#'):
            return None  # Mark for review
        
        # Extract percentage
        match = re.search(r'(\d+\.?\d*)%', weight_text)
        if match:
            return float(match.group(1))
        
        return None
    
    def _extract_date_from_row(self, row: List, column_map: dict) -> Optional[datetime]:
        """Extract due date from a table row.
        
        Args:
            row: Table row (list of cells)
            column_map: Column mapping dictionary
            
        Returns:
            Due date as datetime, or None if not found
        """
        if 'date' not in column_map:
            return None
        
        date_idx = column_map['date']
        if date_idx >= len(row) or not row[date_idx]:
            return None
        
        date_cell = row[date_idx]
        date_text = str(date_cell).strip() if date_cell else ''
        
        # Handle multi-line cell content
        date_text = ' '.join(date_text.split('\n'))
        
        # Try to parse date using various patterns
        return self._parse_date_from_text(date_text)
    
    def _extract_format_from_row(self, row: List, column_map: dict) -> Optional[str]:
        """Extract format/type from a table row (optional).
        
        Args:
            row: Table row (list of cells)
            column_map: Column mapping dictionary
            
        Returns:
            Format string, or None if not found
        """
        if 'format' not in column_map:
            return None
        
        format_idx = column_map['format']
        if format_idx >= len(row) or not row[format_idx]:
            return None
        
        format_cell = row[format_idx]
        format_text = str(format_cell).strip() if format_cell else ''
        
        return format_text if format_text else None
    
    def _is_summary_row(self, row: List, column_map: dict) -> bool:
        """Check if a row is a summary row (Total, COURSE TOTAL, etc.).
        
        Args:
            row: Table row (list of cells)
            column_map: Column mapping dictionary
            
        Returns:
            True if this is a summary row
        """
        # Check name column
        if 'name' in column_map:
            name_idx = column_map['name']
            if name_idx < len(row) and row[name_idx]:
                name_text = str(row[name_idx]).lower().strip()
                # Check for summary keywords
                if any(keyword in name_text for keyword in ['total', 'course total', 'sum', 'subtotal']):
                    return True
        
        # Check weight column for sum-like values
        if 'weight' in column_map:
            weight_idx = column_map['weight']
            if weight_idx < len(row) and row[weight_idx]:
                weight_text = str(row[weight_idx]).strip()
                # If weight is a large round number (like 100%, 25.00%), might be a total
                if re.match(r'^\d{2,3}(\.00)?%$', weight_text):
                    # But only if name suggests it's a total
                    if 'name' in column_map:
                        name_idx = column_map['name']
                        if name_idx < len(row) and row[name_idx]:
                            name_text = str(row[name_idx]).lower().strip()
                            if 'rotation' in name_text or 'total' in name_text or 'course' in name_text:
                                return True
        
        return False
    
    def _merge_continuation_row(self, assessment: AssessmentTask, row: List, column_map: dict) -> AssessmentTask:
        """Merge a continuation row into an existing assessment.
        
        Args:
            assessment: Existing assessment to merge into
            row: Continuation row
            column_map: Column mapping dictionary
            
        Returns:
            Updated assessment with merged information
        """
        # Merge name if continuation row has name fragments
        if 'name' in column_map:
            name_idx = column_map['name']
            if name_idx < len(row) and row[name_idx]:
                continuation_name = str(row[name_idx]).strip()
                if continuation_name and continuation_name.lower() not in assessment.title.lower():
                    # Only add if it's not already in the title
                    # Add space if title doesn't end with punctuation
                    if not assessment.title.endswith((':', '-', '&')):
                        assessment.title += " "
                    assessment.title += continuation_name
        
        # Update weight if not already set (continuation rows usually don't have weight)
        if assessment.weight_percent is None and 'weight' in column_map:
            weight_idx = column_map['weight']
            if weight_idx < len(row) and row[weight_idx]:
                weight = self._extract_weight_from_row(row, column_map)
                if weight is not None:
                    assessment.weight_percent = weight
        
        # Update date - continuation rows often have the actual due date
        # Prefer date from continuation row if it exists
        if 'date' in column_map:
            date_idx = column_map['date']
            if date_idx < len(row) and row[date_idx]:
                date_text = str(row[date_idx]).strip()
                parsed_date = self._parse_date_from_text(date_text)
                if parsed_date:
                    # Use continuation row date if current date is None or if continuation date is more specific
                    if not assessment.due_datetime or ('due' in date_text.lower() and 'opens' not in date_text.lower()):
                        assessment.due_datetime = parsed_date
        
        # Update source evidence
        row_text = self._get_row_text(row, column_map)
        if row_text:
            assessment.source_evidence = (assessment.source_evidence or '') + " " + row_text
        
        return assessment
    
    def _get_row_text(self, row: List, column_map: dict) -> str:
        """Get all text from a row for source evidence.
        
        Args:
            row: Table row
            column_map: Column mapping dictionary
            
        Returns:
            Combined text from all cells
        """
        texts = []
        for cell in row:
            if cell:
                cell_text = str(cell).strip()
                if cell_text:
                    texts.append(cell_text)
        return ' '.join(texts)
    
    def _parse_date_from_text(self, date_text: str) -> Optional[datetime]:
        """Parse date from text using various patterns.
        
        Args:
            date_text: Text containing date information
            
        Returns:
            Parsed datetime, or None if not found
        """
        if not date_text or not date_text.strip():
            return None
        
        # Clean up text - handle multi-line and common OCR errors
        date_text = ' '.join(date_text.split('\n'))
        date_text = date_text.replace('S ept', 'Sept').replace('S eptember', 'September')
        
        # Handle "Opens X... Due Y" format - use the Due date
        opens_due_match = re.search(r'Opens\s+[^D]*Due\s+([^\.]+)', date_text, re.IGNORECASE)
        if opens_due_match:
            date_text = opens_due_match.group(1).strip()
        
        # Handle date ranges like "Dec 2nd/3rd" - use the later date
        date_range_match = re.search(r'(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?\s*[/-]\s*(\d{1,2})(?:st|nd|rd|th)?', date_text, re.IGNORECASE)
        if date_range_match:
            month_str = date_range_match.group(1)
            day1 = int(date_range_match.group(2))
            day2 = int(date_range_match.group(3))
            # Use the later day
            day = max(day1, day2)
            month = self._month_name_to_num(month_str)
            if month:
                year = 2025 if month >= 9 else 2026
                return datetime(year, month, day, 23, 59)
        
        # Try dateparser first (handles many formats)
        parsed = dateparser.parse(date_text, settings={'PREFER_DATES_FROM': 'future'})
        if parsed:
            # Extract time if present
            time_match = re.search(r'(\d{1,2})(?:[:–-](\d{2}))?\s*(AM|PM|am|pm)', date_text, re.IGNORECASE)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                if time_match.group(3).upper() == 'PM' and hour != 12:
                    hour += 12
                elif time_match.group(3).upper() == 'AM' and hour == 12:
                    hour = 0
                return datetime.combine(parsed.date(), time(hour, minute))
            else:
                # Default to end of day if no time specified
                return datetime.combine(parsed.date(), time(23, 59))
        
        # Fallback to regex patterns
        patterns = [
            r'(?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday),?\s+(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?',
            r'(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?',
            r'Due\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(\w+)\s+(\d{1,2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_text, re.IGNORECASE)
            if match:
                month_str = match.group(1)
                day = int(match.group(2))
                
                # Determine year (default to 2025, adjust based on month)
                year = 2025
                if any(m in month_str.lower() for m in ['jan', 'feb', 'mar', 'apr']):
                    year = 2026
                
                # Convert month name to number
                month = self._month_name_to_num(month_str)
                if month:
                    # Extract time if present
                    time_match = re.search(r'(\d{1,2})(?:[:–-](\d{2}))?\s*(AM|PM|am|pm)', date_text, re.IGNORECASE)
                    if time_match:
                        hour = int(time_match.group(1))
                        minute = int(time_match.group(2)) if time_match.group(2) else 0
                        if time_match.group(3).upper() == 'PM' and hour != 12:
                            hour += 12
                        elif time_match.group(3).upper() == 'AM' and hour == 12:
                            hour = 0
                        return datetime(year, month, day, hour, minute)
                    else:
                        return datetime(year, month, day, 23, 59)
        
        return None
    
    def _month_name_to_num(self, month_str: str) -> Optional[int]:
        """Convert month name/abbreviation to number.
        
        Args:
            month_str: Month name or abbreviation
            
        Returns:
            Month number (1-12), or None if invalid
        """
        month_map = {
            'jan': 1, 'january': 1,
            'feb': 2, 'february': 2,
            'mar': 3, 'march': 3,
            'apr': 4, 'april': 4,
            'may': 5,
            'jun': 6, 'june': 6,
            'jul': 7, 'july': 7,
            'aug': 8, 'august': 8,
            'sep': 9, 'sept': 9, 'september': 9,
            'oct': 10, 'october': 10,
            'nov': 11, 'november': 11,
            'dec': 12, 'december': 12,
        }
        
        month_lower = month_str.lower().rstrip('.')
        return month_map.get(month_lower)
    
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
        # Initialize match variable to avoid UnboundLocalError
        match = None
        
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
            for assessment_match in assessment_mentions:
                if 'weight' in assessment_match.group(0).lower() or 'due' in assessment_match.group(0).lower():
                    section_text = assessment_match.group(0)
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
            
            # Stop processing if we hit the "Designated Assessment" section - this is informational, not an assessment
            if re.match(r'^Designated\s+Assessment', line, re.IGNORECASE):
                break
            
            # Skip lines that are bullet points (informational sections, not assessments)
            if line.strip().startswith('•') or line.strip().startswith('-'):
                i += 1
                continue
            
            # Check if this line starts an assessment - handle multi-line names
            assessment_name_match = None
            assessment_name = None
            
            # IMPORTANT: Check for Midterm Test FIRST, before other patterns
            # This ensures Midterm Tests are caught even if they appear in unexpected positions
            # Handle both "Midterm Test 1" (with number) and "Midterm Test" (without number)
            if 'Midterm' in line and 'Test' in line:
                match = re.search(r'Midterm\s+(?:Test|TEST)\s+(\d+)', line, re.IGNORECASE)
                if match:
                    midterm_num = match.group(1)
                    assessment_name = f"Midterm Test {midterm_num}"
                    row_lines = [line]
                    j = i + 1
                else:
                    # Try alternative pattern - maybe "Midterm" and number are separated
                    # BUT: Exclude numbers in parentheses like "(2 hrs)" - those are durations, not test numbers
                    # Look for "Midterm Test" followed by a number that's NOT in parentheses
                    alt_match = re.search(r'Midterm\s+(?:Test|TEST)\s+(\d+)', line, re.IGNORECASE)
                    if alt_match:
                        # Check if this number is in parentheses (like "(2 hrs)")
                        num_pos = alt_match.start(1)
                        # Look backwards to see if there's an opening parenthesis before the number
                        before_num = line[:num_pos]
                        if '(' in before_num and ')' not in before_num[:before_num.rfind('(')+1]:
                            # Number is in parentheses - this is a duration, not a test number
                            # Treat as "Midterm Test" without number
                            if re.search(r'Midterm\s+(?:Test|TEST)(?:\s|\(|,|$)', line, re.IGNORECASE):
                                assessment_name = "Midterm Test"
                                row_lines = [line]
                                j = i + 1
                            else:
                                i += 1
                                continue
                        else:
                            midterm_num = alt_match.group(1)
                            assessment_name = f"Midterm Test {midterm_num}"
                            row_lines = [line]
                            j = i + 1
                    else:
                        # No number found - this is just "Midterm Test" (common case)
                        # Check that it's actually "Midterm Test" and not just "Midterm" in another context
                        if re.search(r'Midterm\s+(?:Test|TEST)(?:\s|\(|,|$)', line, re.IGNORECASE):
                            assessment_name = "Midterm Test"
                            row_lines = [line]
                            j = i + 1
                        else:
                            i += 1
                            continue
            
            # First, check if this line starts with "PeerWise" - collect more lines for dates
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
                
                # For PeerWise, collect more lines to capture all date information
                # PeerWise dates are often split across multiple lines
                while j < len(lines) and j < i + 8:  # Collect up to 8 more lines for PeerWise
                    next_line = lines[j]
                    # Stop if we hit another assessment
                    if re.match(r'^(?:Midterm|Final|Assignment\s+\d+|PeerWise|Optional|Designated)', next_line, re.IGNORECASE):
                        break
                    # Stop if we've collected enough date information (both Author and Answer dates)
                    if 'by 11:59 PM' in ' '.join(row_lines).lower() and 'feedback' in ' '.join(row_lines).lower():
                        # Check if we have both dates
                        if re.search(r'Author.*?(\w+\.?\s+\w+\.?\s+\d+)', ' '.join(row_lines), re.IGNORECASE) and \
                           re.search(r'feedback.*?(\w+\.?\s+\w+\.?\s+\d+)', ' '.join(row_lines), re.IGNORECASE):
                            break
                    row_lines.append(next_line)
                    j += 1
            
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
                else:
                    # Try alternative pattern - maybe "Midterm" and number are separated
                    # BUT: Exclude numbers in parentheses like "(2 hrs)" - those are durations, not test numbers
                    # Look for "Midterm Test" followed by a number that's NOT in parentheses
                    alt_match = re.search(r'Midterm\s+(?:Test|TEST)\s+(\d+)', line, re.IGNORECASE)
                    if alt_match:
                        midterm_num = alt_match.group(1)
                        assessment_name = f"Midterm Test {midterm_num}"
                        row_lines = [line]
                        j = i + 1
                    else:
                        # Check if there's a number after "Midterm Test" but not in parentheses
                        # Pattern: "Midterm Test" followed by optional whitespace, then a number NOT preceded by "("
                        alt_match2 = re.search(r'Midterm\s+(?:Test|TEST)(?:\s+)(\d+)(?!\s*hrs?|hours?)', line, re.IGNORECASE)
                        if alt_match2 and not re.search(r'Midterm\s+(?:Test|TEST)\s*\(', line, re.IGNORECASE):
                            midterm_num = alt_match2.group(1)
                            assessment_name = f"Midterm Test {midterm_num}"
                            row_lines = [line]
                            j = i + 1
                        else:
                            # No number found - this is just "Midterm Test" (common case)
                            # Check that it's actually "Midterm Test" and not just "Midterm" in another context
                            if re.search(r'Midterm\s+(?:Test|TEST)(?:\s|\(|,|$)', line, re.IGNORECASE):
                                assessment_name = "Midterm Test"
                                row_lines = [line]
                                j = i + 1
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
                        r'^Midterm\s+(?:Test|TEST)(?:\s+\d+)?',  # Midterm Test 1, Midterm Test 2, or just Midterm Test
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
                # For PeerWise assignments, look for "Author:" and "Answer and provide feedback:" dates
                if 'peerwise' in assessment_name.lower():
                    # Pattern for PeerWise dates: "Author: Mon, Oct. 27th by 11:59 PM" and "feedback: Wed, Oct. 29th by 11:59 PM"
                    # Handle abbreviated day names (Mon, Tue, Wed, Thu, Fri, Sat, Sun) and abbreviated months (Oct., Jan., etc.)
                    peerwise_patterns = [
                        r'Author:?\s*(?:Mon|Monday|Tue|Tuesday|Wed|Wednesday|Thu|Thursday|Fri|Friday|Sat|Saturday|Sun|Sunday),?\s+(Oct|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|September|October|November|December|January|February|March|April|May|June|July|August)\.?\s+(\d{1,2})(?:st|nd|rd|th)?',
                        r'feedback:?\s*(?:Mon|Monday|Tue|Tuesday|Wed|Wednesday|Thu|Thursday|Fri|Friday|Sat|Saturday|Sun|Sunday),?\s+(Oct|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|September|October|November|December|January|February|March|April|May|June|July|August)\.?\s+(\d{1,2})(?:st|nd|rd|th)?',
                    ]
                    
                    for pattern in peerwise_patterns:
                        date_matches = re.finditer(pattern, row_text, re.IGNORECASE)
                        for date_match in date_matches:
                            if len(date_match.groups()) == 2:
                                month = date_match.group(1)
                                day = date_match.group(2)
                                
                                # Determine year based on month
                                year = 2025
                                if any(m in month.lower() for m in ['jan', 'feb', 'mar', 'apr']):
                                    year = 2026
                                elif month.lower() in ['october', 'oct', 'november', 'nov', 'december', 'dec']:
                                    year = 2025
                                
                                date_str = f"{month} {day}, {year}"
                                # Avoid duplicates
                                if date_str not in due_dates:
                                    due_dates.append(date_str)
                
                # General date patterns for other assessments
                if not due_dates:
                    # Pattern for dates: "October 1", "Oct 1", "November 14th", "Sunday, Oct 19", "December exam period"
                    # Handle ordinal suffixes (st, nd, rd, th) by making them optional
                    date_patterns = [
                        r'(?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday),?\s+(Oct|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|September|October|November|December|January|February|March|April|May|June|July|August)\.?\s+(\d{1,2})(?:st|nd|rd|th)?',
                        r'(Oct|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|September|October|November|December|January|February|March|April|May|June|July|August)\.?\s+(\d{1,2})(?:st|nd|rd|th)?',
                    ]
                
                    for date_pattern in date_patterns:
                        date_matches = re.finditer(date_pattern, row_text, re.IGNORECASE)
                        for date_match in date_matches:
                            if len(date_match.groups()) == 2:
                                month = date_match.group(1)
                                day = date_match.group(2)
                                
                                # Determine year
                                year = 2025
                                if '2026' in row_text or any(m in row_text.lower() for m in ['january', 'february', 'march', 'april', 'jan', 'feb', 'mar', 'apr']):
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
                # For PeerWise, times are usually "11:59 PM" and appear after each date
                time_str = None
                if 'peerwise' in assessment_name.lower():
                    # Look for "by 11:59 PM" pattern (common for PeerWise)
                    time_match = re.search(r'by\s+(\d{1,2})(?:[:–-](\d{2}))?\s*(AM|PM)', row_text, re.IGNORECASE)
                    if time_match:
                        time_str = time_match.group(0)
                else:
                    # Look for time patterns: "6-8 PM", "11:59 PM", "in class"
                    time_match = re.search(r'(\d{1,2})(?:[:–-](\d{2}))?\s*(?:[-–]\s*(\d{1,2})(?:[:–-](\d{2}))?)?\s*(AM|PM)', row_text, re.IGNORECASE)
                    if time_match:
                        time_str = time_match.group(0)
                    elif 'in class' in row_text.lower():
                        time_str = 'in class'
                
                # Create assessment(s) - handle multiple due dates (e.g., PeerWise)
                if due_dates:
                    # For PeerWise assignments, use the later date (Answer date) as the primary due date
                    # This represents when the assignment is fully complete
                    if 'peerwise' in assessment_name.lower() and len(due_dates) > 1:
                        # Use the last date (Answer/Feedback date) as the primary due date
                        due_date_str = due_dates[-1]
                        parsed_date = dateparser.parse(due_date_str)
                        if parsed_date:
                            # Extract time for the Answer/Feedback date
                            hour = 23
                            minute = 59
                            feedback_time_match = re.search(r'feedback:?[^.]*?by\s+(\d{1,2})(?:[:–-](\d{2}))?\s*(AM|PM)', row_text, re.IGNORECASE)
                            if feedback_time_match:
                                hour = int(feedback_time_match.group(1))
                                minute = int(feedback_time_match.group(2)) if feedback_time_match.group(2) else 59
                                if feedback_time_match.group(3).upper() == 'PM' and hour != 12:
                                    hour += 12
                                elif feedback_time_match.group(3).upper() == 'AM' and hour == 12:
                                    hour = 0
                            
                            due_datetime = datetime.combine(parsed_date.date(), time(hour, minute))
                            
                            # Create single assessment with the Answer date
                            assessment = AssessmentTask(
                                title=assessment_name,
                                type=assessment_type,
                                weight_percent=weight,
                                due_datetime=due_datetime,
                                confidence=0.8 if weight and due_datetime else 0.5,
                                source_evidence=row_text[:200],
                                needs_review=(due_datetime is None or weight is None)
                            )
                            assessments.append(assessment)
                    else:
                        # For non-PeerWise or single-date assessments, process normally
                        for date_idx, due_date_str in enumerate(due_dates[:2]):  # Limit to 2 dates per assessment
                            parsed_date = dateparser.parse(due_date_str)
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
                                
                                assessment = AssessmentTask(
                                    title=assessment_name,
                                    type=assessment_type,
                                    weight_percent=weight,
                                    due_datetime=due_datetime,
                                    confidence=0.8 if weight and due_datetime else 0.5,
                                    source_evidence=row_text[:200],
                                    needs_review=(due_datetime is None or weight is None)
                                )
                                assessments.append(assessment)
                else:
                    # If no dates found, still create assessment without date
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
                
                # Move to next potential assessment
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

