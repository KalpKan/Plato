# Project Structure and Layout

This document describes the organization and layout of the Course Outline to iCalendar Converter project.

## Directory Structure

```
Plato/
├── src/                          # Source code directory
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # CLI entry point (legacy, for testing)
│   ├── models.py                # Data models (dataclasses)
│   ├── pdf_extractor.py         # PDF text extraction and parsing
│   ├── rule_resolver.py         # Relative deadline rule resolution
│   ├── study_plan.py            # Study plan generation
│   ├── icalendar_gen.py         # iCalendar file generation
│   ├── cache.py                 # SQLite cache manager (local dev)
│   └── supabase_cache.py        # Supabase cache manager (production)
│
├── tests/                        # Test files
│   ├── __init__.py
│   ├── test_cache.py
│   └── test_models.py
│
├── templates/                    # HTML templates (to be created)
│   ├── index.html               # Upload page
│   ├── review.html              # Review/edit page
│   └── manual.html              # Manual entry page
│
├── static/                       # Static files (to be created)
│   ├── style.css                # CSS styling
│   └── app.js                   # Client-side JavaScript
│
├── test_output/                  # Test output directory (gitignored)
│
├── .gitignore                   # Git ignore rules
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup configuration
│
├── README.md                    # Main project documentation
├── QUICK_START.md               # Quick start guide
├── USAGE_GUIDE.md               # Detailed usage documentation
├── PROJECT_INSTRUCTIONS.md      # Development guidelines
├── PROJECT_STRUCTURE.md         # This file
├── DEVELOPMENT_STATUS.md        # Current development status
│
├── DEPLOYMENT_GUIDE.md          # Deployment options
├── RAILWAY_SUPABASE_SETUP.md    # Railway + Supabase setup
├── MCP_SUPABASE_SETUP.md        # MCP integration setup
├── CURSOR_MCP_CONFIG.md         # MCP configuration reference
│
└── BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf  # Reference PDF (gitignored)
```

## Source Code Modules

### Core Modules

#### `src/models.py`
**Purpose:** Defines all data structures used throughout the application.

**Key Classes:**
- `CourseTerm` - Academic term information (name, dates, timezone)
- `SectionOption` - Lecture or lab section schedule
- `AssessmentTask` - Assessment item (assignment, exam, etc.)
- `StudyPlanItem` - Study plan event
- `ExtractedCourseData` - Container for all extracted data
- `UserSelections` - User choices (sections, overrides)
- `CacheEntry` - Cached result structure

**Serialization Functions:**
- `serialize_date()`, `deserialize_date()`
- `serialize_datetime()`, `deserialize_datetime()`
- `serialize_time()`, `deserialize_time()`

#### `src/pdf_extractor.py`
**Purpose:** Extracts course information from PDF files.

**Key Methods:**
- `extract_all()` - Main extraction method
- `extract_term()` - Extract term name and dates
- `extract_lecture_sections()` - Extract lecture schedules
- `extract_lab_sections()` - Extract lab schedules
- `extract_assessments()` - Extract assessments and due dates
- `extract_course_info()` - Extract course code and name

**How It Works:**
1. Loads PDF using `pdfplumber`
2. Extracts text page by page
3. Uses regex patterns to find term, sections, assessments
4. Returns `ExtractedCourseData` object

**Reference:** Always refer to `BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf` for PDF structure.

#### `src/rule_resolver.py`
**Purpose:** Resolves relative deadline rules to absolute datetimes.

**Key Methods:**
- `resolve_rules()` - Resolve all relative rules in assessments
- `resolve_rule()` - Resolve a single rule
- `generate_per_occurrence_assessments()` - Create one assessment per occurrence

**How It Works:**
1. Parses relative rules (e.g., "24 hours after lab")
2. Finds anchor section (lab, lecture, tutorial)
3. Generates all occurrences within term
4. Calculates due dates by adding offset to occurrences
5. Creates per-occurrence assessments when needed

#### `src/study_plan.py`
**Purpose:** Generates "start studying" events based on assessment weights.

**Key Methods:**
- `generate_study_plan()` - Generate study plan items
- `get_default_mapping_display()` - Get lead-time mapping for UI

**Lead Time Mapping:**
- 0-5%: 3 days
- 6-10%: 7 days
- 11-20%: 14 days
- 21-30%: 21 days
- 31%+: 28 days
- Finals: 28 days

#### `src/icalendar_gen.py`
**Purpose:** Generates iCalendar (.ics) files.

**Key Methods:**
- `generate_calendar()` - Create complete calendar
- `_create_recurring_section_events()` - Create recurring lecture/lab events
- `_create_assessment_due_event()` - Create assessment due date events
- `_create_study_start_event()` - Create study plan start events
- `export_to_file()` - Save calendar to file

**Features:**
- Uses RRULE for recurring events
- Timezone-aware (America/Toronto)
- Proper iCalendar format

#### `src/cache.py`
**Purpose:** SQLite-based cache manager for local development.

**Key Methods:**
- `lookup_extraction()` - Get cached extraction data
- `store_extraction()` - Store extraction data
- `lookup_user_choices()` - Get cached user choices
- `store_user_choices()` - Store user choices
- `get_cache_manager()` - Auto-select cache manager (SQLite or Supabase)

**Tables:**
- `extraction_cache` - PDF extraction results
- `user_choices` - User selections

#### `src/supabase_cache.py`
**Purpose:** Supabase PostgreSQL cache manager for production.

**Key Methods:**
- Same interface as `cache.py` but uses Supabase
- Automatically used when `DATABASE_URL` environment variable is set

**How It Works:**
1. Connects to Supabase PostgreSQL
2. Uses same table structure as SQLite
3. Stores JSONB data in PostgreSQL
4. Separates extraction cache from user choices

#### `src/main.py`
**Purpose:** CLI entry point for testing and development.

**Usage:**
```bash
python -m src.main "path/to/syllabus.pdf" --no-cache
```

**Note:** This is primarily for testing. The web interface will be the main entry point.

## Data Flow

### 1. PDF Upload
```
User uploads PDF → PDFExtractor.extract_all() → ExtractedCourseData
```

### 2. Cache Check
```
PDF hash → CacheManager.lookup_extraction() → ExtractedCourseData (if cached)
```

### 3. Rule Resolution
```
ExtractedCourseData.assessments → RuleResolver.resolve_rules() → Resolved assessments
```

### 4. Study Plan Generation
```
Resolved assessments → StudyPlanGenerator.generate_study_plan() → StudyPlanItem[]
```

### 5. Calendar Generation
```
ExtractedCourseData + UserSelections + StudyPlan → ICalendarGenerator.generate_calendar() → Calendar
```

### 6. Cache Storage
```
ExtractedCourseData → CacheManager.store_extraction()
UserSelections → CacheManager.store_user_choices
```

## Database Schema

### Supabase Tables

#### `extraction_cache`
- `pdf_hash` (TEXT, PRIMARY KEY) - SHA-256 hash of PDF
- `extracted_json` (JSONB) - Serialized ExtractedCourseData
- `timestamp` (TIMESTAMPTZ) - When cached

#### `user_choices`
- `id` (BIGSERIAL, PRIMARY KEY) - Auto-increment ID
- `pdf_hash` (TEXT) - Links to extraction_cache
- `session_id` (TEXT, nullable) - Optional session identifier
- `selected_lecture_section_json` (JSONB, nullable) - Selected lecture section
- `selected_lab_section_json` (JSONB, nullable) - Selected lab section
- `lead_time_overrides_json` (JSONB, nullable) - Lead time overrides
- `timestamp` (TIMESTAMPTZ) - When stored

## Configuration

### Environment Variables

**Local Development (SQLite):**
- No environment variables needed
- Uses local SQLite database

**Production (Supabase):**
- `DATABASE_URL` - PostgreSQL connection string
- Format: `postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres`

### Cache Manager Selection

The `get_cache_manager()` function automatically selects:
- **Supabase** if `DATABASE_URL` is set
- **SQLite** otherwise (local development)

## Testing

### Test Files
- `tests/test_cache.py` - Cache system tests
- `tests/test_models.py` - Data model tests

### Test Scripts
- `test_cli.py` - Quick functionality test
- `test_extraction.py` - Full pipeline test
- `check_supabase_tables.py` - Database connection test

## Reference Documents

### PDF Structure Reference
- **File:** `BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf`
- **Purpose:** Canonical example of course outline structure
- **Usage:** Refer when implementing/extending extraction patterns

### Documentation Files
- `README.md` - Main project overview
- `USAGE_GUIDE.md` - How to use the program
- `PROJECT_INSTRUCTIONS.md` - Development guidelines
- `DEVELOPMENT_STATUS.md` - Current implementation status

## Next Steps

1. **Web Interface** - Create Flask app (`src/app.py`)
2. **HTML Templates** - Create upload, review, manual pages
3. **Static Files** - Create CSS and JavaScript
4. **Deployment** - Set up Railway deployment

## Code Style

- **Comments:** All code is commented for beginners
- **No Emojis:** Code and documentation don't use emojis
- **Type Hints:** Functions use type hints
- **Docstrings:** All functions have docstrings explaining purpose and parameters

