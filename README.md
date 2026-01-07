# Plato - Course Outline to Calendar Converter

A web application that automatically extracts course information from Western University course outline PDFs and generates iCalendar (.ics) files compatible with Google Calendar, Apple Calendar, and Outlook.

## Overview

Plato processes course outline PDFs to extract:
- Course information (code, name, term)
- Lecture and lab schedules (days, times, locations)
- Assessments (assignments, quizzes, exams with due dates and weights)
- Relative date rules (e.g., "24 hours after lab")

The extracted data is then converted into a calendar file with:
- Recurring lecture and lab events
- Assessment due dates
- Study plan events (configurable lead times based on assessment weights)

## Features

- Automatic PDF extraction using multi-layered approach
- Document structure analysis with layout-aware extraction
- Section segmentation for accurate field extraction
- Policy text filtering to reduce false positives
- Constrained selection to ensure assessment weights total ~100%
- Interactive review interface with inline editing
- Manual section and assessment addition
- Configurable study plan lead times
- Session-based caching for performance
- Force refresh option to re-extract cached PDFs
- Dark mode, responsive design
- Clean, minimalist UI

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Local Setup

1. Clone the repository:
```bash
git clone https://github.com/KalpKan/Plato.git
cd Plato
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start the development server:
```bash
python3 src/app.py
```

4. Open your browser and navigate to:
```
http://localhost:5000
```

## Usage

### Basic Workflow

1. **Upload PDF**: Click "Choose File" and select your course outline PDF
2. **Review Extraction**: The system extracts course information and displays it for review
3. **Edit Fields**: Click on any field to edit inline (dates, weights, titles, etc.)
4. **Add Missing Data**: Use "Add Section" or "Add Assessment" buttons if needed
5. **Select Sections**: If multiple lecture/lab sections exist, select yours from dropdowns
6. **Review Assessments**: Review and edit any ambiguous assessments
7. **Configure Lead Times**: Adjust study plan lead times if desired
8. **Generate Calendar**: Click "Generate Calendar" to download the .ics file

### Manual Mode

If PDF extraction fails or you prefer to enter data manually:
1. Click "Manual Mode" button on the upload page
2. Enter term dates, section schedules, and assessments
3. Generate .ics file from manual inputs

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

**Outlook:**
1. Open Outlook
2. File → Open & Export → Import/Export
3. Select "Import an iCalendar (.ics) or vCalendar file"
4. Choose the generated `.ics` file

## Project Structure

```
Plato/
├── src/
│   ├── app.py                    # Flask web application
│   ├── models.py                 # Data models (dataclasses)
│   ├── pdf_extractor.py          # PDF extraction engine
│   ├── document_structure.py    # Document structure analysis
│   ├── assessment_extractor.py   # Assessment extraction pipeline
│   ├── course_extractor.py      # Course info extraction
│   ├── rule_resolver.py         # Relative date rule resolution
│   ├── study_plan.py            # Study plan generation
│   ├── icalendar_gen.py         # iCalendar file generation
│   ├── cache.py                 # Caching system
│   └── main.py                  # CLI entry point
├── templates/                    # HTML templates
│   ├── base.html               # Base template
│   ├── index.html              # Landing page
│   ├── review.html             # Review/edit page
│   ├── manual.html             # Manual entry page
│   └── error.html              # Error page
├── static/                       # Static files
│   ├── style.css               # Stylesheet
│   └── app.js                  # Client-side JavaScript
├── course_outlines/             # Test PDFs (not in git)
├── test_course_outlines/        # Additional test PDFs
├── requirements.txt            # Python dependencies
├── Procfile                    # Railway deployment config
├── Dockerfile                  # Docker configuration
└── README.md                   # This file
```

## How It Works

### Extraction Pipeline

1. **Document Structure Analysis**
   - Extracts text blocks with layout metadata (font sizes, positions)
   - Reconstructs lines from blocks via y-coordinate clustering
   - Detects tables (pdfplumber + reconstructed from aligned lines)
   - Identifies sections (Evaluation, Course Information, etc.)

2. **Section Segmentation**
   - Identifies headings using font size, bold flags, and keywords
   - Creates section ranges (start/end pages and positions)
   - Scopes extraction to relevant sections (e.g., assessments only from Evaluation section)

3. **Assessment Extraction**
   - **Candidate Generation**: From tables, reconstructed tables, and inline patterns
   - **Scoring**: Based on weight validity, assessment nouns, section context
   - **Filtering**: Policy-window filtering to eliminate false positives
   - **Selection**: Constrained selection to ensure weights total ~100%

4. **Course Information Extraction**
   - Layout-based ranking (font size, position, proximity to course code)
   - Filters out generic words (Department, Faculty, etc.)
   - Falls back to PDF metadata if needed

5. **Rule Resolution**
   - Parses relative deadline rules (e.g., "24 hours after lab")
   - Matches rules to existing assessments when possible
   - Generates per-occurrence assessments when needed
   - Resolves to absolute datetimes using recurring schedules

6. **Study Plan Generation**
   - Default lead times based on assessment weight:
     - 0-10%: 3 days
     - 10-20%: 5 days
     - 20-30%: 7 days
     - 30-40%: 10 days
     - 40-50%: 14 days
     - 50%+: 21 days
   - Finals: Always 21 days
   - User-configurable per weight range

7. **Calendar Generation**
   - Creates recurring events (RRULE) for lectures and labs
   - Creates assessment due events
   - Creates study plan start events
   - Uses timezone-aware datetimes (America/Toronto)
   - Includes VTIMEZONE component for compatibility

### Caching

- **Extraction Cache**: Stores extracted data keyed by PDF hash (SHA-256)
- **User Choices Cache**: Stores section selections and lead-time overrides keyed by session
- **Force Refresh**: Option to bypass cache and re-extract

## Performance

Tested on 39 course outline PDFs:
- **Extraction Success**: 100% (39/39)
- **Perfect Weight Accuracy (90-110%)**: 87% (34/39)
- **Good Weight Accuracy (80-120%)**: 92% (36/39)
- **Assessment Extraction**: 97% (38/39 have 2+ assessments)
- **Course Name Extraction**: 100% (39/39)

## Limitations

- PDF format only (no DOCX support)
- Maximum file size: 5MB
- Requires structured course outlines (works best with clear assessment tables)
- Some ambiguous data may require manual review
- Lecture/lab schedules rarely included in PDFs (manual entry available)

## Development

### Running Tests

```bash
# Comprehensive extraction test
python3 test_comprehensive.py

# New extraction pipeline test
python3 test_new_extraction.py
```

### Code Structure

The codebase is organized into focused modules:
- `models.py` - Data structures (dataclasses)
- `pdf_extractor.py` - Main extraction orchestrator
- `document_structure.py` - Layout analysis and section segmentation
- `assessment_extractor.py` - Assessment candidate generation, scoring, selection
- `course_extractor.py` - Course information extraction
- `rule_resolver.py` - Relative date rule resolution
- `study_plan.py` - Study plan generation
- `icalendar_gen.py` - Calendar file generation
- `cache.py` - Caching system

## Deployment

See `DEPLOYMENT.md` for detailed deployment instructions to Railway with Supabase.

## Documentation

- `PROJECT_OVERVIEW.md` - Comprehensive project documentation
- `ARCHITECTURE.md` - System architecture and component responsibilities
- `EXTRACTION_PLAN.md` - Detailed extraction algorithm documentation
- `DEPLOYMENT.md` - Deployment guide

## License

This project is provided as-is for educational purposes.

## Support

For issues or questions, please refer to the documentation files or open an issue on GitHub.

## Credits

Made by Kalp Kansara

Note: This tool is not affiliated with Western University. It is an independent tool designed to help students manage their course schedules.
