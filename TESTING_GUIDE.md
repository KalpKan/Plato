# Testing Guide: Current Functionality

## Quick Test

You can test the current functionality using the CLI interface that's already implemented.

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt
```

### Basic Test

```bash
# Test with the reference PDF
python -m src.main "BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf"
```

### Test with Options

```bash
# Test with custom output directory
python -m src.main "BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf" --output-dir ./test_output

# Test without cache (force fresh extraction)
python -m src.main "BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf" --no-cache
```

## What Gets Tested

### ✅ Working Features

1. **PDF Extraction**
   - Text extraction from PDF
   - Term detection (Fall/Winter/Summer + year)
   - Course code and name extraction

2. **Section Extraction**
   - Lecture section detection
   - Lab section detection
   - Day/time parsing
   - Location extraction

3. **Assessment Extraction**
   - Assignment detection
   - Quiz/test detection
   - Due date extraction
   - Weight extraction

4. **Rule Resolution**
   - Relative rule parsing ("24 hours after lab")
   - Per-occurrence assessment generation
   - Rule to datetime conversion

5. **Study Plan Generation**
   - Lead time calculation
   - Study start date generation

6. **iCalendar Generation**
   - Recurring events (RRULE)
   - Assessment due dates
   - Study plan events
   - .ics file creation

### ⚠️ Known Issues

1. **Cache System**
   - Schema mismatch (will likely fail)
   - Use `--no-cache` flag to bypass

## Expected Output

### 1. PDF Extraction Phase
```
Extracting data from PDF: BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf
```

### 2. Section Selection (if multiple found)
```
Multiple Lecture sections found:
  1. Section 001: Mon, Wed, Fri 10:30-11:30
  2. Section 002: Tue, Thu 14:00-15:30

Which Lecture section are you enrolled in? (1-2):
```

### 3. Assessment Review (if ambiguous)
```
2 assessment(s) need review:

1. Lab Report 1
   Type: lab_report
   Weight: Not specified
   Due: 24 hours after lab
   Source: Page 3: "Lab reports are due 24 hours after the lab"

Is this information correct? (y/n/skip):
```

### 4. File Generation
```
Generating iCalendar file...
Saved extracted data to: BMSUE_Syllabus_Phys3140A_Fall_2025_Sept3_extracted.json
Saved calendar to: BMSUE_Syllabus_Phys3140A_Fall_2025_Sept3.ics
Results cached for future use.

Done! You can now import the .ics file into your calendar.
```

## Output Files

### 1. JSON Extraction Data
File: `{pdf_name}_extracted.json`

Contains:
- Term information
- All lecture sections found
- All lab sections found
- All assessments extracted
- Confidence scores
- Source evidence

### 2. iCalendar File
File: `{pdf_name}.ics`

Contains:
- Recurring lecture events
- Recurring lab events
- Assessment due dates
- Study plan start dates

### 3. Import to Calendar

**Google Calendar:**
1. Open Google Calendar
2. Click "+" → "Import"
3. Select the `.ics` file
4. Choose calendar and import

**Apple Calendar:**
1. Open Calendar app
2. File → Import
3. Select the `.ics` file
4. Choose calendar and import

## Testing Individual Modules

### Test PDF Extractor

```python
from src.pdf_extractor import PDFExtractor
from pathlib import Path

pdf_path = Path("BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf")
extractor = PDFExtractor(pdf_path)
data = extractor.extract_all()

print(f"Term: {data.term.term_name}")
print(f"Course: {data.course_code} - {data.course_name}")
print(f"Lectures: {len(data.lecture_sections)}")
print(f"Labs: {len(data.lab_sections)}")
print(f"Assessments: {len(data.assessments)}")
```

### Test Rule Resolver

```python
from src.rule_resolver import RuleResolver
from src.models import AssessmentTask, SectionOption, CourseTerm
from datetime import date, time

# Create test assessment with rule
assessment = AssessmentTask(
    title="Lab Report",
    type="lab_report",
    due_rule="24 hours after lab",
    rule_anchor="lab"
)

# Create test section
lab_section = SectionOption(
    section_type="Lab",
    section_id="001",
    days_of_week=[1],  # Tuesday
    start_time=time(14, 0),
    end_time=time(16, 0)
)

# Create test term
term = CourseTerm(
    term_name="Fall 2025",
    start_date=date(2025, 9, 1),
    end_date=date(2025, 12, 15)
)

# Resolve
resolver = RuleResolver()
resolved = resolver.resolve_rule(assessment, [lab_section], term)
print(f"Resolved due date: {resolved.due_datetime}")
```

### Test Study Plan Generator

```python
from src.study_plan import StudyPlanGenerator
from src.models import AssessmentTask
from datetime import datetime, time

# Create test assessment
assessment = AssessmentTask(
    title="Assignment 1",
    type="assignment",
    weight_percent=15.0,
    due_datetime=datetime(2025, 10, 15, 23, 59)
)

# Generate study plan
generator = StudyPlanGenerator()
study_plan = generator.generate_study_plan([assessment])

for item in study_plan:
    print(f"Start studying: {item.start_studying_datetime}")
    print(f"Due date: {item.due_datetime}")
```

### Test iCalendar Generator

```python
from src.icalendar_gen import ICalendarGenerator
from src.models import CourseTerm, SectionOption
from datetime import date, time

# Create test data
term = CourseTerm(
    term_name="Fall 2025",
    start_date=date(2025, 9, 1),
    end_date=date(2025, 12, 15)
)

lecture = SectionOption(
    section_type="Lecture",
    section_id="001",
    days_of_week=[0, 2, 4],  # Mon, Wed, Fri
    start_time=time(10, 30),
    end_time=time(11, 30)
)

# Generate calendar
gen = ICalendarGenerator()
calendar = gen.generate_calendar(
    term=term,
    lecture_section=lecture,
    lab_section=None,
    assessments=[],
    study_plan=[]
)

# Export
gen.export_to_file(calendar, "test.ics")
print("Calendar saved to test.ics")
```

## Troubleshooting

### "Module not found" errors
```bash
# Make sure you're running from project root
cd /Users/kalp/Desktop/Plato

# Install dependencies
pip install -r requirements.txt
```

### "PDF file not found"
```bash
# Use absolute path
python -m src.main "/full/path/to/your/file.pdf"

# Or make sure you're in the right directory
cd /Users/kalp/Desktop/Plato
python -m src.main "BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf"
```

### Cache errors
```bash
# Use --no-cache flag to bypass
python -m src.main "file.pdf" --no-cache
```

## Next Steps After Testing

1. **Fix cache system** (if you want caching to work)
2. **Build web interface** (Flask app)
3. **Set up Supabase** (for production database)
4. **Deploy** (Railway, Render, or Vercel)

