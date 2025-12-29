# Course Outline to iCalendar Converter

A beginner-friendly web application that converts Western University course outline PDFs into iCalendar (.ics) files with recurring schedules and assessment deadlines.

## Features

- **Web-based interface** - Easy to use, no command-line required
- Extracts course information from PDF outlines
- Generates recurring lecture and lab schedules
- Extracts assessments with due dates
- Resolves relative deadlines (e.g., "24 hours after lab") - creates per-occurrence assessments
- Creates study plan events with configurable lead times
- Caches results for identical PDFs (separates extraction from user choices)
- Force refresh option to re-extract cached PDFs
- Exports .ics files compatible with Google Calendar and Apple Calendar
- Manual mode fallback if PDF extraction fails

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. Clone or download this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Starting the Web Application

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

### Output Files

The .ics file will be named:
- `<COURSECODE>_<TERM>_Lec<SECTION>_Lab<SECTION>_<HASH8>.ics`
- Example: `CS3305_Fall2026_Lec001_Lab002_3fa21c9b.ics`
- Falls back to PDF name + hash if course code/term not extracted

### Importing to Calendar

**Google Calendar:**
1. Open Google Calendar
2. Click the "+" button → "Import"
3. Select the generated `.ics` file
4. Choose your calendar and click "Import"

**Apple Calendar:**
1. Open Calendar app
2. File → Import
3. Select the generated `.ics` file
4. Choose your calendar and click "Import"

## Project Structure

```
Plato/
├── src/
│   ├── app.py               # Flask web application
│   ├── models.py            # Data models
│   ├── pdf_extractor.py     # PDF extraction logic
│   ├── rule_resolver.py     # Relative rule resolution
│   ├── study_plan.py        # Study plan generation
│   ├── icalendar_gen.py     # iCalendar generation
│   └── cache.py             # Caching system
├── templates/               # HTML templates
│   ├── index.html          # Upload page
│   ├── review.html         # Review/edit page
│   └── manual.html         # Manual entry page
├── static/                  # Static files (CSS, JS)
│   ├── style.css
│   └── app.js
├── tests/
│   ├── fixtures/            # Test PDFs and expected outputs
│   └── test_*.py            # Test files
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## How It Works

1. **PDF Upload:** User uploads PDF via web form
2. **PDF Extraction:** Extracts text from the PDF and identifies term, sections, and assessments
   - Confidence thresholds: < 0.75 → Needs review, < 0.50 for critical items → Manual confirmation
3. **User Review:** Web UI displays extracted data for review and editing
4. **Section Selection:** User selects lecture/lab sections if multiple exist
5. **Rule Resolution:** Resolves relative deadlines using recurring schedules
   - Matches rules to existing assessments when possible
   - Generates per-occurrence assessments when needed (e.g., "Lab Report 1", "Lab Report 2", etc.)
6. **Lead Time Confirmation:** Shows default lead-time mapping once for user confirmation
7. **Study Plan:** Generates "start studying" events based on confirmed lead times
8. **Calendar Generation:** Creates .ics file with proper timezone (America/Toronto, TZID)
9. **Caching:** Stores extraction results (by PDF hash) and user choices separately

## Limitations

- PDF format only (no DOCX support)
- Requires clear, structured course outlines
- Some ambiguous data may require manual review
- No conflict checking with existing calendar events

## Development

### Running Tests

```bash
pytest tests/
```

### Code Structure

The code is organized into modules:
- `models.py` - Data structures
- `pdf_extractor.py` - PDF parsing and extraction
- `rule_resolver.py` - Relative deadline resolution
- `study_plan.py` - Study plan generation
- `icalendar_gen.py` - Calendar file generation
- `cache.py` - Caching system

## License

This project is provided as-is for educational purposes.

## Support

For issues or questions, please refer to the documentation files:
- `IMPLEMENTATION_PLAN.md` - Development roadmap
- `ARCHITECTURE.md` - System architecture
- `DATA_MODELS.md` - Data structure definitions
- `EXTRACTION_HEURISTICS.md` - Extraction logic details
- `CACHING_APPROACH.md` - Caching implementation
- `TEST_PLAN.md` - Testing strategy

