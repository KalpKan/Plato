# Usage Guide: Course Outline to iCalendar Converter

This document tracks how to use the program and serves as detailed documentation for git.

## Overview

The Course Outline to iCalendar Converter is a web-based application that converts Western University course outline PDFs into iCalendar (.ics) files. The application extracts course information, generates recurring schedules, and creates assessment deadlines with study plan reminders.

## Reference Document

**Important:** When working with PDF extraction or understanding field locations, always refer to the reference PDF file:
- `BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf`

This file serves as the canonical example of how course outlines are structured and where specific fields are located.

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup Steps

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Starting the Web Server

```bash
python src/app.py
```

Then open your browser and navigate to:
```
http://localhost:5000
```

### Using the Web Interface

1. **Upload PDF**: Click "Choose File" and select your course outline PDF
2. **Review Extraction**: The system will extract course information and display it for review
3. **Select Sections**: If multiple lecture/lab sections exist, select yours
4. **Review Assessments**: Review and edit any ambiguous assessments
5. **Confirm Lead Times**: Review the lead-time mapping (shown once per import)
6. **Download Calendar**: Click "Download .ics" to get your calendar file

### Manual Mode

If PDF extraction fails or you prefer to enter data manually:
1. Click "Manual Mode" button
2. Enter term dates, section schedules, and assessments
3. Generate .ics file from manual inputs

## Output Files

The .ics file will be named:
- Format: `<COURSECODE>_<TERM>_Lec<SECTION>_Lab<SECTION>_<HASH8>.ics`
- Example: `CS3305_Fall2026_Lec001_Lab002_3fa21c9b.ics`
- Falls back to PDF name + hash if course code/term not extracted

## Importing to Calendar

### Google Calendar
1. Open Google Calendar
2. Click the "+" button → "Import"
3. Select the generated `.ics` file
4. Choose your calendar and click "Import"

### Apple Calendar
1. Open Calendar app
2. File → Import
3. Select the generated `.ics` file
4. Choose your calendar and click "Import"

## How It Works

### 1. PDF Upload
User uploads PDF via web form

### 2. PDF Extraction
Extracts text from the PDF and identifies:
- Term information (name, start date, end date)
- Lecture sections (days, times, locations)
- Lab sections (days, times, locations)
- Assessments (title, type, due date, weight)
- Course code and name

**Confidence Thresholds:**
- < 0.75: Marked as "Needs review"
- < 0.50 for critical items (term dates, schedule, final exam): Requires manual confirmation

### 3. User Review
Web UI displays extracted data for review and editing. Users can:
- Correct term dates
- Select lecture/lab sections
- Edit assessment details
- Confirm or override lead times

### 4. Section Selection
User selects lecture/lab sections if multiple exist

### 5. Rule Resolution
Resolves relative deadlines using recurring schedules:
- Matches rules to existing assessments when possible
- Generates per-occurrence assessments when needed (e.g., "Lab Report 1", "Lab Report 2", etc.)

### 6. Lead Time Confirmation
Shows default lead-time mapping once for user confirmation:
- 0-5%: 3 days
- 6-10%: 7 days
- 11-20%: 14 days
- 21-30%: 21 days
- 31%+: 28 days
- Finals: 28 days

### 7. Study Plan
Generates "start studying" events based on confirmed lead times

### 8. Calendar Generation
Creates .ics file with:
- Proper timezone (America/Toronto, TZID)
- Recurring lecture events
- Recurring lab events
- Assessment due dates
- Study plan start dates

### 9. Caching
Stores extraction results (by PDF hash) and user choices separately:
- `extraction_cache`: Derived facts from PDF (keyed by PDF hash)
- `user_choices`: Selected sections, lead-time overrides (keyed by session/user)

## Error Handling

The application never fails silently:
- Clear error messages displayed to user
- Fallback manual mode available
- Structured failures with actionable guidance

## Troubleshooting

### PDF Extraction Fails
- Use Manual Mode to enter data manually
- Check that PDF is a valid course outline
- Ensure PDF is not password-protected

### Missing Information
- Review extracted data carefully
- Use review interface to correct missing fields
- Manual mode available as fallback

### Calendar Import Issues
- Ensure .ics file is valid
- Check timezone settings in calendar application
- Verify dates are within valid range

## Code Structure

The codebase is organized into modules:
- `models.py` - Data structures (CourseTerm, SectionOption, AssessmentTask, etc.)
- `pdf_extractor.py` - PDF parsing and extraction
- `rule_resolver.py` - Relative deadline resolution
- `study_plan.py` - Study plan generation
- `icalendar_gen.py` - Calendar file generation
- `cache.py` - Caching system
- `main.py` - CLI entry point (legacy)
- `app.py` - Flask web application (primary interface)

## Development Guidelines

### Code Comments
All code is commented such that any beginner can understand what is going on. Comments explain:
- What each function does
- What parameters mean
- What return values represent
- Complex logic and algorithms
- Why certain decisions were made

### No Emojis
Code and documentation do not use emojis. This applies to:
- Source code files
- Comments
- Documentation files
- Error messages
- Log messages

### Git Workflow
- Planning files are excluded from git (see `.gitignore`)
- All code changes are tracked in git
- Usage documentation (`USAGE_GUIDE.md`) is updated after every change
- Reference PDF is excluded from git but kept locally for development

### Reference PDF
- Always refer to `BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf` when:
  - Understanding PDF structure
  - Determining field locations
  - Implementing extraction logic
  - Testing extraction functionality

## Limitations

- PDF format only (no DOCX support)
- Requires clear, structured course outlines
- Some ambiguous data may require manual review
- No conflict checking with existing calendar events

## Support

For issues or questions, please refer to:
- `README.md` - Main documentation
- `QUICK_START.md` - Quick start guide
- `USAGE_GUIDE.md` - This file (detailed usage)

