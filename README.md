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

- Reads the **term window** from the outline's own "Important Dates" / "Classes begin" text, or falls back to Western's sessional dates for the named term (never today's date)
- Reads every **lecture, lab and tutorial slot** printed in the outline (tables, "Lectures: MWF 12:30 - 1:20 pm in AHB-1R40", "Class Meetings: Tuesday 2:30-3:30pm, Thursday 2:30-4:30pm"), each typed correctly
- Reads every **assessment** with its weight and the due date the outline states (day, month, the right year, the time when given); footnote digits and bullets are stripped from titles
- An assessment the outline does not date (**"scheduled by the Registrar", "Date TBA", "during the exam period"**) is shown with that reason and gets **no calendar event** rather than an invented date
- Weekly quizzes with listed dates become one event per date; bonus / optional rows are shown but not counted
- Review page with inline editing (course code, name, term, dates, titles, weights, due dates, lead times), "Add Section" / "Add Assessment", and a list of everything the parser could not read
- Your edits are private to your browser session: the parser's output for a given PDF is shared, your corrections are not
- Manual mode for scanned or locked PDFs
- Configurable study-reminder lead times
- RFC 5545 `.ics`: `VTIMEZONE`, `DTSTAMP`, weekly series that end on the last day of classes, titles that carry the course code

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

1. **Upload PDF**: drop your course outline PDF (text PDF, up to 4 MB) on the upload page
2. **Review**: the review page shows the course, term, slots and assessments, plus a box "What could not be read from the PDF"
3. **Fix what is wrong**: click any highlighted field to edit it; rows marked "Needs a date" say why (e.g. "Outline says: scheduled by the Registrar") and get no event until you add a date
4. **Add missing data**: "Add Section" / "Add Assessment"
5. **Select sections**: choose your lecture / lab / tutorial slot if the outline lists several
6. **Study reminders**: adjust the lead times if you like
7. **Download Calendar**: the `.ics` streams back immediately; import it into Google, Apple or Outlook

Uploading the same PDF again shows the saved parse (about 2 s); tick "Re-read the PDF" to parse it again (10–25 s on the free hosting).

### Manual Mode

If the PDF is a scan, is password-protected or has no assessment table, the upload page links to **Enter the course by hand** (`/manual`): term dates, optional weekly slots and the assessments, then the same review page and download.

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

### Extraction Pipeline (`src/outline/`)

1. **`pipeline.load_pages`** — page text and tables via pdfplumber; a password-protected file or a file with no text layer raises a specific error that the upload page turns into a plain-language message; pages without text are reported on the review page.
2. **`course.extract_course`** — course code and name from the first text page (spelled-out subjects like "Classical Studies 1000", abbreviations like "KIN 2000", the department line plus a bare number, the file name as a last resort); prerequisite lists and room numbers are ignored. The name comes from an explicit "Course Name:" label first, then the title line beside or above/below the code ("Aquatic Ecology 3415G", "Crime and Punishment … / Preliminary Course Outline for CS 2301B"), then "Math 1228 (Methods of Finite Mathematics)" in the first pages; headings such as "Course Information" and sentences are never taken as the name.
3. **`term.extract_term`** — first the outline's own "Classes Begin / Reading Week / Classes End / Exam Period" table or "Class Begin:" lines, then a weekly table with date ranges, then the season + year (text or file name, "A" = Fall, "B" = Winter) mapped to Western's sessional dates (2022–2027 table). Unknown stays Unknown.
4. **`schedule.extract_slots_and_notes`** — lecture / lab / tutorial slots from timetable tables and prose (day letters, dotted times, per-section rows, bulleted "Lectures: / Hours: Tuesdays 9:30-11:30 am, and Thursdays 9:30-10:30 am", a bare "Time: Tuesdays 12:30-2:30 pm and Thursdays 12:30-1:30 pm", and "Section 001: Tuesdays, 1:30pm-4:30pm, SSC 2036" lines under a "Class Location and Time" heading); a component with no day or time becomes a note, never a slot, and a dated "Section 001: Tues Oct 7, 2pm-4pm" exam line is never a weekly slot.
5. **`assessments.extract_assessments`** — evaluation tables (weight column, continuation rows, footnote digits), inline lists ("Assignment 1 (10%) -- due Oct. 9", "First test: 20% (12 November 2025)"), numeric text tables, then dates for still-undated rows from the weekly schedule, from prose, and from dated bullet lists ("- Assignment 1: … (available: September 28, deadline: October 8, at 11:55 pm)", "- Midterm exam: Weeks 1–6 (Oct 21, 12:30–2:30 pm, in class)", "- Project: Submission deadline: Dec 6, 11:55 pm"). A group row such as "Assignments 17% (three assignments: the first one 5%, and the remaining two, 6% each)" is split into its dated items when the outline lists them; an exam whose date depends on the section ("Section 001: Tues Oct 7 … Section 002: Wed Oct 8") gets the window and a note, never one of the dates; "Chapter 1, Chapter 2 assignments: due Sept 19" lists become one recurring row. An "every Friday from … to …" rule yields to the outline's own date list ("September 12, 19, 26; October 10, 17, 31; and November 14") when there is one, and when the outline states a count that the weekly expansion does not match and lists no dates, the row gets a window and no dates rather than invented ones. An in-class midterm with no printed time takes the lecture slot's time. `dates.DateResolver` turns each date cell into a date + time + status (`exact`, `registrar`, `tba`, `range`, `rule`, `recurring`, `missing`), choosing the year from the term window (Sept–Dec → first year) or the printed weekday.
6. **Rule Resolution** (`rule_resolver.py`, `app.expand_rule_assessments`) — a relative rule such as "Lab Report due 24hrs after each Lab Session" gets an anchor (lab / tutorial / lecture) from its wording; the review page says "Add your lab slot with Add Section and you get one due event per lab", and once that slot is chosen (from the outline or added by hand) the download carries one dated "Lab report N due" event per lab occurrence, the day after each lab, skipping reading week and capped at a count the outline states ("Labs (Total = 8)"). The stored row keeps its rule, so changing the slot later regenerates the events.
7. **Study Plan** (`study_plan.py`) — reminder lead times by weight, user-configurable.
8. **Calendar** (`icalendar_gen.py`) — weekly series (UNTIL = last day of classes, UTC), one event per dated assessment (or per listed date), study-start events; `VTIMEZONE`, `DTSTAMP`, course code in every title; no event for an undated assessment.

The older `document_structure.py` / `assessment_extractor.py` path is kept only as a fallback when the new pipeline finds no assessment at all.

### Caching

- **Extraction cache**: the parser's output keyed by the PDF's SHA-256 **plus the parser version** (`cache.PARSER_VERSION`, a hash of the parser's own source files, shown by `/api/health` as `parser`), shared by everyone who uploads the same file. A deploy that changes the parser therefore never serves a result the previous parser produced; the old rows simply go unread.
- **Per-visitor copy**: every edit is saved under `<pdf_hash>:<session_id>`, so one student's corrections never reach another
- **User choices**: section selections and lead-time overrides keyed by session
- **Re-read the PDF**: the checkbox on the upload page re-parses and drops your edited copy

## Performance

Measured on the labelled corpus (15 real Western outlines with hand-written ground truth, `tests/corpus/`; the PDFs themselves are not committed) after the 2026-09-18 fix round:

| metric | result | bar |
|---|---|---|
| course code | 15/15 | 90 % |
| term window | 15/15 | 90 % |
| slots recall / precision | 15/15 · 15/15 | 90 % |
| assessments recall / precision | 73/74 · 73/73 | 95 % |
| weights | 73/73 | 98 % |
| due dates exact (day, month, year) | 36/36 | 95 % |
| no fabricated dates | 37/37 | 100 % |
| clean titles | 71/73 | 95 % |
| weight totals | 14/15 | 90 % |

All 42 corpus outlines parse without an exception. The baseline before the fix (commit `de32e96`) was 14 % exact due dates, 0/10 term windows, 27 % slot recall.

## Limitations

- PDF with a text layer only (a scanned outline has to be entered by hand)
- Maximum file size 4 MB (Vercel's request limit)
- Lab and tutorial slots that exist only on draftmyschedule are not in the outline; the review page says so and offers "Add Section"
- Registrar-scheduled exams never have a date in the outline; they are listed with the exam period and get no event

## Development

### Running Tests

```bash
.venv/bin/pytest -q tests/                         # unit + flow tests (about 1 s)
.venv/bin/pytest -q tests/test_corpus.py -s        # the corpus gate (needs ~/projects/plato-corpus/pdfs; skips otherwise)
.venv/bin/python tests/corpus/run_extractor.py --out /tmp/out && .venv/bin/python tests/corpus/score.py --output /tmp/out
```

The corpus gate enforces the bar in `tests/test_corpus.py::BAR`; set `PLATO_CORPUS_GATE=0` for report-only mode while experimenting.

### Code Structure

The codebase is organized into focused modules:
- `models.py` - Data structures (dataclasses) and the one JSON (de)serializer
- `outline/` - The parser: `dates.py`, `term.py`, `schedule.py`, `course.py`, `assessments.py`, `tables.py`, `pipeline.py`
- `pdf_extractor.py` - Entry point (`PDFExtractor(path, original_filename).extract_all()`), delegates to `outline.pipeline`
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
