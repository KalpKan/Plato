# Comprehensive PDF Extraction Plan

**Based on analysis of:**
- Physiology 3120 Syllabus 2025–2026 (Full year course)
- Physiology 3140A Fall 2025 (Half course)

## 1. Information to Extract

### 1.1 Basic Course Information
- **Course Code**: e.g., "Physiology 3120", "Physiology 3140A"
- **Course Name**: e.g., "Human Physiology", "Cellular Physiology"
- **Term**: e.g., "Fall 2025", "Fall 2025/Winter 2026"
- **Term Dates**:
  - Start date (e.g., September 4, 2025)
  - End date (e.g., December 9, 2025 or April 9, 2026)
  - Reading week dates (e.g., November 3-9, 2025)
  - Exam period dates (e.g., December 11-22, 2025)
- **Timezone**: Always "America/Toronto" for Western University

### 1.2 Schedule Information
- **Lecture Sections**:
  - Days of week (e.g., M/W/F, Monday/Wednesday/Friday)
  - Start time (e.g., 10:30 AM, 9:30 AM)
  - End time (e.g., 11:30 AM, 10:20 AM)
  - Location (if specified)
  - Section ID (if multiple sections exist)
- **Lab Sections** (if applicable):
  - Same fields as lecture sections
- **Tutorial Sections** (if applicable):
  - Same fields as lecture sections

### 1.3 Assessment Information
For each assessment, extract:
- **Title/Name**: e.g., "Midterm Test 1", "Quiz 1", "PeerWise Assignment 1"
- **Type**: quiz, midterm, final, assignment, lab_report, project, other
- **Format**: e.g., "MCQ & Short answer", "Mixed format"
- **Weight**: Percentage (e.g., 25%, 40%, 7%)
- **Due Date(s)**:
  - Primary due date (date and time if specified)
  - Secondary due dates (e.g., PeerWise has "Author" and "Answer" dates)
  - Date ranges (e.g., "December exam period")
  - Relative dates (e.g., "24 hours after lab")
- **Flexibility Information**:
  - Late penalty information
  - Reweighting rules (e.g., "Reweight to midterm")
  - Makeup exam dates
  - Designated assessment status
- **Coverage**: What material is covered (e.g., "lectures 1-16, Modules 1-2")
- **Duration**: For exams/quizzes (e.g., "2 hrs", "25 min")
- **Location**: For in-class assessments (e.g., "in class")

### 1.4 Course Schedule (Detailed)
- **Lecture-by-lecture schedule**:
  - Lecture number
  - Date
  - Day of week
  - Week number
  - Topic/title
  - Instructor name
  - Special notes (e.g., "Thanksgiving OFF", "Reading week")

### 1.5 Additional Information
- **Contact Information**: Course coordinator, instructors, TAs
- **Prerequisites**: Course prerequisites
- **Delivery Mode**: In-person, online, hybrid
- **Important Dates**: Add/drop deadlines, withdrawal deadlines

## 2. How to Consistently Extract Information

### 2.1 Course Code and Name Extraction

**Patterns to look for:**
1. **First page header**: "Department of [Department] [Course Name]-[Course Code]"
   - Pattern: `([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[-–]\s*(Physiology|Physics|Phys)\s+(\d{3,4}[A-Z]?)`
   - Example: "Cellular Physiology-Physiology 3140A"
   - Extract: Course Name = "Cellular Physiology", Course Code = "PHYS 3140A"

2. **Standalone course code**: "Physiology 3120" or "Physiology 3140A"
   - Pattern: `(Physiology|Physics|Phys)\s+(\d{3,4}[A-Z]?)`
   - Map to standard format: "PHYS 3120" or "PHYS 3140A"

3. **Department mapping**:
   - "Physiology" → "PHYS"
   - "Physics" → "PHYS"
   - "Computer Science" → "CS"
   - "Mathematics" → "MATH"
   - etc.

**Extraction Strategy:**
- Search first 2 pages for course code patterns
- Prioritize patterns with course name (more reliable)
- Extract course name from same line or nearby text
- Clean up: Remove "Department of", "Course Outline", etc.

### 2.2 Term Information Extraction

**Patterns:**
1. **Term name**: "Fall 2025", "Fall 2025/Winter 2026", "Winter 2026"
   - Pattern: `(Fall|Winter|Summer)\s+(\d{4})(?:/(Winter|Summer)\s+(\d{4}))?`
   - Handle full-year courses (two terms)

2. **Important dates table**: Look for "Classes Begin", "Reading Week", "Classes End", "Exam Period"
   - Pattern: `Classes Begin\s+Reading Week\s+Classes End\s+Study day\(s\)\s+Exam Period`
   - Extract dates from following line
   - Handle multiple rows (Fall and Winter for full-year courses)

3. **Date parsing**:
   - "September 4" → Parse with year from term
   - "November 3–9" → Date range
   - "December 11-22" → Date range

**Extraction Strategy:**
- Search first 3 pages for term information
- Look for "Important Dates" section
- Parse date table if present
- Fall back to date patterns in text

### 2.3 Lecture/Lab Section Extraction

**Status**: ✅ FIXED - Now correctly parses all day formats (M/W/F, MWF, Mon/Wed/Fri, etc.)

**Previous Issue**: Only extracting first day (Monday) instead of all days (M/W/F)

**Patterns to handle:**
1. **Slash-separated**: "M/W/F", "T/Th", "Mon/Wed/Fri"
   - Pattern: `([M/T/W/Th/F/S]+)\s+(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})`
   - Parse each day separately

2. **Concatenated**: "MWF", "TTh", "MTWThF"
   - Pattern: `([MTWThFS]+)\s+(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})`
   - Handle "Th" as two characters

3. **Full names**: "Monday/Wednesday/Friday"
   - Pattern: `(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)(?:/(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))+`

4. **With section label**: "Lecture M/W/F 9:30-10:20"
   - Pattern: `(?:Lecture|Lab|Tutorial)\s+([M/T/W/Th/F/S]+)\s+(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})`

**Extraction Strategy:**
- Search for "Timetabled Sessions" or "Component Date(s) Time" section
- Look for "Lecture", "Lab", "Tutorial" keywords
- Extract days, start time, end time
- Parse days correctly (handle all formats)
- Convert to list of day numbers [0,2,4] for M/W/F

**Day Parsing Algorithm:**
```
Input: "M/W/F" or "MWF" or "Mon/Wed/Fri"
Output: [0, 2, 4] (Monday=0, Wednesday=2, Friday=4)

1. If contains "/": Split by "/" and parse each part
2. If contains "Th": Handle as special case (Thursday=3)
3. Map single letters: M→0, T→1, W→2, Th→3, F→4, S→5, Su→6
4. Map full names: Monday→0, Tuesday→1, etc.
5. Return sorted list of unique day numbers
```

### 2.4 Assessment Extraction

**Status**: ✅ IMPLEMENTED - Comprehensive extraction for both table-based and text-based formats

**Previous Issue**: Not extracting assessments at all

**Assessment Table Structure:**
Both PDFs have a table with columns:
- Assessment (name)
- Format
- Weight
- Due Date
- Flexibility

**Patterns to extract:**

1. **Assessment name**: Look for common patterns
   - "Quiz 1", "In Class Quiz 1", "Quiz 2"
   - "Midterm Test 1", "Midterm Test 2", "Midterm exam"
   - "Final Exam", "Final Examination"
   - "Assignment 1", "Assignment 2", "Slide redesign"
   - "PeerWise Assignment 1", "PeerWise Assignment 2"
   - "Lab Report 1", "Laboratory Report"

2. **Weight extraction**: Look for percentage patterns
   - Pattern: `(\d+(?:\.\d+)?)\s*%`
   - Extract from same row or nearby

3. **Due date extraction**: Multiple formats
   - **Absolute dates**: "October 1", "Oct 1", "November 14", "Sunday, Oct 19"
   - **Date with time**: "November 14 6-8 PM", "Oct 1 in class"
   - **Date ranges**: "December exam period", "Dec 11-22"
   - **Multiple dates**: "Author: Mon, Oct. 27 by 11:59 PM. Answer: Wed, Oct. 29 by 11:59 PM"
   - **Relative dates**: "24 hours after lab", "within 24 hours"

4. **Format extraction**: "MCQ & Short answer", "Mixed format", "2 hrs", "25 min"

5. **Flexibility extraction**: 
   - "Reweight to midterm"
   - "72 hour no late penalty"
   - "Requires documentation"
   - "Designated assessment"

**Extraction Strategy:**
1. **Find assessment section**: Look for "Assessment and Evaluation" or "8. Assessment"
2. **Identify table structure**: Look for header row with "Assessment", "Format", "Weight", "Due Date", "Flexibility"
3. **Parse table rows**: Extract each assessment row
4. **Handle multi-line entries**: Some assessments span multiple lines
5. **Extract dates**: Use dateparser for flexible date parsing
6. **Extract times**: Look for "AM", "PM", "11:59 PM", "6-8 PM"
7. **Handle special cases**:
   - PeerWise assignments have two due dates
   - Some assessments have date ranges
   - Some have relative deadlines

**Table Parsing Algorithm:**
```
1. Find "Assessment" section (usually page 5-6)
2. Look for table header: "Assessment Format Weight Due Date Flexibility"
3. For each row:
   a. Extract assessment name (first column)
   b. Extract format (if present)
   c. Extract weight percentage
   d. Extract due date(s) - may be multiple
   e. Extract flexibility information
4. Handle multi-row assessments (some span 2-3 lines)
5. Classify assessment type based on name
```

### 2.5 Course Schedule Extraction

**Patterns:**
- Look for "Course Content and Schedule" or "6. Course Content"
- Extract lecture-by-lecture schedule
- Format: "Date Day Wk Topic Instructor"
- Handle special entries: "Thanksgiving OFF", "Reading week", "Final Exam Period"

**Extraction Strategy:**
- Find schedule section
- Parse table rows
- Extract: lecture number, date, day, week, topic, instructor
- Create recurring events for regular lectures
- Create one-time events for special dates

## 3. How to Make Sense of Extracted Information

### 3.1 Data Validation and Normalization

**Term Dates:**
- Validate start date < end date
- Ensure dates are within reasonable academic year
- Handle full-year courses (two terms)

**Schedule:**
- Validate days of week (0-6)
- Validate times (start < end)
- Handle timezone (always America/Toronto)
- Convert 12-hour to 24-hour format

**Assessments:**
- Validate weights sum to 100% (with tolerance for rounding)
- Validate dates are within term dates
- Handle missing weights (mark for review)
- Handle missing dates (mark for review)
- Classify assessment types consistently

### 3.2 Rule Resolution

**Relative Deadlines:**
- "24 hours after lab" → Find lab section, add 24 hours to each occurrence
- "Within 24 hours" → Parse context to find anchor event
- "Reweight to midterm" → Store as metadata, don't create event

**Date Ranges:**
- "December exam period" → Use term's exam period dates
- "Dec 11-22" → Parse as date range, use start date for due date

**Multiple Dates:**
- PeerWise assignments: Create separate events for "Author" and "Answer" deadlines
- Or create one event with description containing both dates

### 3.3 Confidence Scoring

**High Confidence (0.8-1.0):**
- Course code and name from header
- Term dates from structured table
- Lecture schedule from "Timetabled Sessions" section
- Assessments with complete information (name, weight, date, time)

**Medium Confidence (0.5-0.8):**
- Course code from text (not header)
- Term dates from text patterns
- Assessments with missing weight or date
- Relative deadlines

**Low Confidence (0.0-0.5):**
- Assessments with only name
- Ambiguous dates
- Incomplete schedule information

**Mark for Review:**
- Confidence < 0.75 for any field
- Confidence < 0.50 for critical fields (term dates, major assessments)
- Missing required information

## 4. How to Turn Information into Study Plan and Calendar

### 4.1 Calendar Event Generation

**Recurring Events:**
1. **Lecture Events**:
   - Title: "[Course Code] Lecture"
   - Recurrence: Weekly on specified days (M/W/F)
   - Time: Start time to end time
   - Location: If specified
   - Description: Course name, section info

2. **Lab Events** (if applicable):
   - Same structure as lectures
   - Title: "[Course Code] Lab"

**One-Time Events:**
1. **Assessment Due Dates**:
   - Title: Assessment name (e.g., "Midterm Test 1")
   - Date/Time: Due date and time
   - Description: Weight, format, coverage
   - Alarms: 1 day before, 1 hour before

2. **Study Plan Events**:
   - Title: "Start studying: [Assessment Name]"
   - Date: Due date - lead time (based on weight)
   - Description: Assessment details, study tips
   - Alarms: None (study start is the reminder)

3. **Important Dates**:
   - Reading week start/end
   - Add/drop deadline
   - Withdrawal deadline
   - Exam period start/end

### 4.2 Study Plan Generation

**Lead Time Calculation:**
Based on assessment weight:
- 0-5%: 3 days before due
- 6-10%: 7 days before
- 11-20%: 14 days before
- 21-30%: 21 days before
- 31%+: 28 days before
- Finals: 28 days before (minimum)

**Study Plan Events:**
For each assessment:
1. Calculate lead time based on weight
2. Calculate start date: due_date - lead_time
3. Create "Start studying" event
4. Add description with:
   - Assessment details
   - Coverage information
   - Study suggestions

**Special Cases:**
- Quizzes: Shorter lead time (3-7 days)
- Major exams: Longer lead time (21-28 days)
- Assignments: Medium lead time (7-14 days)

### 4.3 Calendar File Generation

**iCalendar Format:**
1. **VTIMEZONE Component**: Always include America/Toronto timezone
2. **Recurring Events**: Use RRULE for lectures/labs
   - FREQ=WEEKLY
   - BYDAY=MO,WE,FR (for M/W/F)
   - UNTIL=term end date
3. **One-Time Events**: Assessment due dates, study plan events
4. **Event Properties**:
   - UID: Unique identifier
   - DTSTART: Start date/time
   - DTEND: End date/time (or DURATION)
   - SUMMARY: Event title
   - DESCRIPTION: Detailed information
   - LOCATION: If specified
   - CATEGORIES: Assessment, Study Plan, Lecture, etc.

**File Naming:**
Format: `<COURSECODE>_<TERM>_Lec<SECTION>_Lab<SECTION>_<HASH8>.ics`
Example: `PHYS3140A_Fall2025_Lec001_LabNone_3fa21c9b.ics`

## 5. Implementation Priorities

### Phase 1: Critical Fixes (Current Issues)
1. ✅ **Fix lecture day extraction**: Parse "M/W/F" correctly to get all days - COMPLETED
2. ✅ **Extract assessments**: Implement table parsing for assessment section - COMPLETED
3. ✅ **Extract assessment weights**: Parse percentage values - COMPLETED
4. ✅ **Extract assessment dates**: Handle multiple date formats - COMPLETED

### Phase 2: Enhanced Extraction
1. **Improve course code extraction**: Handle department name variations
2. **Extract course schedule**: Lecture-by-lecture details
3. **Handle multiple due dates**: PeerWise assignments, etc.
4. **Extract flexibility information**: Late penalties, reweighting rules

### Phase 3: Advanced Features
1. **Relative deadline resolution**: "24 hours after lab"
2. **Date range handling**: Exam periods, reading weeks
3. **Multi-term courses**: Fall/Winter full-year courses
4. **Assessment coverage**: What material is covered

### Phase 4: Study Plan Enhancement
1. **Smart lead times**: Adjust based on assessment type and weight
2. **Study milestones**: Break down large assessments
3. **Review events**: Pre-exam review periods
4. **Progress tracking**: Mark study events as complete

## 6. Testing Strategy

### Test Cases:
1. **Physiology 3140A** (Half course):
   - Course code: PHYS 3140A
   - Term: Fall 2025
   - Lecture: M/W/F 9:30-10:20 AM
   - Assessments: Quiz 1 (7%), Midterm (40%), Quiz 2 (8%), Final (45%)

2. **Physiology 3120** (Full year):
   - Course code: PHYS 3120
   - Term: Fall 2025/Winter 2026
   - Lecture: M/W/F 10:30-11:30 AM
   - Multiple assessments across two terms

### Validation:
- All assessments extracted
- All weights sum to ~100%
- All dates within term dates
- All lecture days correctly parsed
- Study plan events created for all assessments

## 7. Error Handling

**Missing Information:**
- Mark field as "needs review"
- Provide default values where appropriate
- Allow user to edit in review interface

**Conflicting Information:**
- Use highest confidence source
- Mark conflicts for user review
- Log conflicts for pattern improvement

**Invalid Data:**
- Validate dates (within term)
- Validate weights (0-100%)
- Validate times (start < end)
- Provide clear error messages

This plan provides a comprehensive roadmap for extracting, understanding, and converting course outline information into a useful calendar with study plans.