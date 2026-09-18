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

## How to run this (on your own computer)

You need Python 3.12 or newer installed. Then, in a terminal:

```bash
git clone https://github.com/KalpKan/Plato.git
cd Plato
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
SECRET_KEY=anything-random .venv/bin/python -m flask --app src.app run
```

Open http://127.0.0.1:5000 in your browser. Without a `DATABASE_URL` the app keeps
its cache in a small SQLite file under your home folder, so nothing else is needed.
`SECRET_KEY` is mandatory: the app refuses to start without one.

To check everything works: `.venv/bin/pytest` (all tests should pass).

## How to deploy this (the live site)

The live copy runs at **https://plato.kalpkan.com** on Vercel (free Hobby plan) as one
Python function, with its database on Neon (free plan). Every push to the `main`
branch on GitHub deploys automatically; there is nothing to click.

To deploy by hand from this folder (only needed if the automatic deploy is off):

```bash
npx vercel@latest --prod --yes --scope kks-projects-2edcb11a
```

Check that it is healthy: open https://plato.kalpkan.com/api/health and you should
see `{"db":"ok","ok":true,"service":"plato"}`.

If you ever start from a brand-new database, create its tables once with
`DATABASE_URL="<the Neon URL>" python scripts/init_db.py`.

The full operating manual (what to do when it breaks, where every setting is)
lives in the portfolio repo: `skills/portfolio-ops/` in https://github.com/KalpKan/portfolio.

## Where the settings live

All settings are environment variables. Their names are listed in `.env.example`
(with empty values). The real values are stored in **Vercel → project `plato` →
Settings → Environment Variables**, never in this repository.

| Setting | What it is | Required? |
|---|---|---|
| `SECRET_KEY` | A long random string that signs the browser cookie. If it changes, visitors simply start over. | Yes, always |
| `DATABASE_URL` | The Postgres connection string from Neon (project "Plato", database `plato`, pooled). Caches parsed PDFs. | Yes on Vercel; optional locally |
| `POSTHOG_API_KEY` | The public PostHog project key (`phc_...`). Turns on visitor analytics. | No (empty = analytics off) |
| `POSTHOG_HOST` | PostHog ingest host; default `https://us.i.posthog.com` | No |
| `POSTHOG_UI_HOST` | PostHog web app host; default `https://us.posthog.com` | No |
| `PLATO_TMP_DIR` | Scratch folder for uploads; default `/tmp` (the only writable place on Vercel) | No |

Upload limit: the app accepts PDFs up to 16 MB, but Vercel itself rejects any
request body over 4.5 MB, so on the live site a PDF must be under 4.5 MB
(course outlines are usually well under 1 MB).

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
│   ├── cache.py                 # Caching system (SQLite locally, Postgres/Neon live)
│   ├── analytics.py             # PostHog server-side events
│   └── main.py                  # CLI entry point
├── templates/                    # HTML templates
│   ├── base.html               # Base template
│   ├── index.html              # Landing page
│   ├── review.html             # Review/edit page
│   ├── manual.html             # Manual entry page
│   └── error.html              # Error page
├── public/static/               # Static files (served by Vercel's CDN)
│   ├── style.css               # Stylesheet
│   └── app.js                  # Client-side JavaScript
├── tests/                       # pytest suite
├── scripts/init_db.py           # Creates the database tables once
├── course_outlines/             # Test PDFs (not in git)
├── requirements.txt            # Runtime dependencies (requirements-dev.txt adds pytest)
├── pyproject.toml              # Tells Vercel where the app is (src.app:app)
├── vercel.json                 # Vercel function settings (what to leave out of the bundle)
├── .env.example                # Names of the settings, no values
├── legacy/                      # Old Railway/Docker/Supabase files, unused
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

See "How to deploy this" above. The old Railway/Docker files are kept for
reference in `legacy/railway/` and are not used.

## Documentation

- `PROJECT_OVERVIEW.md` - Comprehensive project documentation
- `EXTRACTION_PLAN.md` - Detailed extraction algorithm documentation

## License

This project is provided as-is for educational purposes.

## Support

For issues or questions, please refer to the documentation files or open an issue on GitHub.

## Credits

Made by Kalp Kansara

Note: This tool is not affiliated with Western University. It is an independent tool designed to help students manage their course schedules.
