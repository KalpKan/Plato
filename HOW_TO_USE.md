# How to Use: Course Outline to iCalendar Converter

**Complete guide for using the program and understanding its layout.**

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Test Current Functionality

```bash
# Quick test
python3 test_cli.py

# Full pipeline test
python3 test_extraction.py

# CLI interface (interactive)
python3 -m src.main "BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf" --no-cache
```

### 3. Configure Database (Optional)

**For Local Development:**
- No configuration needed - uses SQLite automatically

**For Production (Supabase):**
```bash
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres"
```

## How the Program Works

### Architecture Overview

```
PDF Upload
    ↓
PDF Extraction (pdf_extractor.py)
    ↓
ExtractedCourseData (term, sections, assessments)
    ↓
Cache Check (cache.py / supabase_cache.py)
    ↓
Rule Resolution (rule_resolver.py) - if relative deadlines exist
    ↓
Study Plan Generation (study_plan.py)
    ↓
iCalendar Generation (icalendar_gen.py)
    ↓
.ics File Export
```

### Step-by-Step Process

#### 1. PDF Extraction
- **Module:** `src/pdf_extractor.py`
- **What it does:** Extracts text from PDF and identifies:
  - Term name and dates (Fall 2025, Sept 1 - Dec 15)
  - Course code and name (e.g., "PHYS 3140A")
  - Lecture sections (days, times, locations)
  - Lab sections (days, times, locations)
  - Assessments (assignments, exams, due dates, weights)
- **Reference:** Uses `BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf` as structure reference

#### 2. Cache System
- **Modules:** `src/cache.py` (SQLite) or `src/supabase_cache.py` (Supabase)
- **What it does:**
  - Stores extracted data separately from user choices
  - Allows multiple users to use same PDF with different sections
  - Caches by PDF hash (SHA-256)
- **Tables:**
  - `extraction_cache` - PDF extraction results
  - `user_choices` - User section selections and overrides

#### 3. Rule Resolution
- **Module:** `src/rule_resolver.py`
- **What it does:**
  - Resolves relative deadlines (e.g., "24 hours after lab")
  - Generates per-occurrence assessments when needed
  - Creates "Lab Report 1", "Lab Report 2", etc. automatically

#### 4. Study Plan Generation
- **Module:** `src/study_plan.py`
- **What it does:**
  - Calculates "start studying" dates based on assessment weights
  - Uses default lead-time mapping:
    - 0-5%: 3 days before due
    - 6-10%: 7 days
    - 11-20%: 14 days
    - 21-30%: 21 days
    - 31%+: 28 days
    - Finals: 28 days

#### 5. iCalendar Generation
- **Module:** `src/icalendar_gen.py`
- **What it does:**
  - Creates recurring events for lectures (RRULE)
  - Creates recurring events for labs (RRULE)
  - Creates assessment due date events
  - Creates study plan start events
  - Exports to .ics file format

## Program Layout

### Data Models (`src/models.py`)

**Core Data Structures:**
- `CourseTerm` - Term information (name, dates, timezone)
- `SectionOption` - Section schedule (days, times, location)
- `AssessmentTask` - Assessment item (title, type, due date, weight)
- `StudyPlanItem` - Study plan event
- `ExtractedCourseData` - Container for all extracted data
- `UserSelections` - User choices (sections, overrides)

### Processing Modules

**Extraction (`src/pdf_extractor.py`):**
- Reads PDF text
- Uses regex patterns to find information
- Returns structured data

**Resolution (`src/rule_resolver.py`):**
- Parses relative rules
- Matches to anchor events
- Generates absolute dates

**Planning (`src/study_plan.py`):**
- Calculates lead times
- Generates study start dates

**Generation (`src/icalendar_gen.py`):**
- Creates calendar events
- Formats as iCalendar
- Exports to file

### Cache System

**Local (SQLite):**
- File: `~/.course_outline_cache/cache.db`
- Automatic - no configuration needed
- Used when `DATABASE_URL` not set

**Production (Supabase):**
- PostgreSQL database
- Tables: `extraction_cache`, `user_choices`
- Used when `DATABASE_URL` is set
- Automatic selection via `get_cache_manager()`

## Usage Examples

### Example 1: Basic CLI Usage

```bash
# Extract and generate calendar
python3 -m src.main "syllabus.pdf"

# Force fresh extraction (ignore cache)
python3 -m src.main "syllabus.pdf" --no-cache

# Specify output directory
python3 -m src.main "syllabus.pdf" --output-dir ./output
```

### Example 2: Testing Extraction

```python
from src.pdf_extractor import PDFExtractor
from pathlib import Path

pdf_path = Path("syllabus.pdf")
extractor = PDFExtractor(pdf_path)
data = extractor.extract_all()

print(f"Term: {data.term.term_name}")
print(f"Lectures: {len(data.lecture_sections)}")
print(f"Assessments: {len(data.assessments)}")
```

### Example 3: Using Cache System

```python
from src.cache import get_cache_manager, compute_pdf_hash
from pathlib import Path

# Get cache manager (auto-selects SQLite or Supabase)
cache = get_cache_manager()

# Compute PDF hash
pdf_path = Path("syllabus.pdf")
pdf_hash = compute_pdf_hash(pdf_path)

# Look up cached extraction
extracted_data = cache.lookup_extraction(pdf_hash)

# Look up cached user choices
user_choices = cache.lookup_user_choices(pdf_hash)
```

## Configuration

### Environment Variables

**For Supabase (Production):**

```bash
export DATABASE_URL="postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres"
```

**For Local Development:**
- No environment variables needed
- Uses SQLite automatically

### Cache Manager Selection

The system automatically selects the cache manager:

```python
# In cache.py
def get_cache_manager():
    if os.getenv("DATABASE_URL"):
        return SupabaseCacheManager()  # Production
    else:
        return CacheManager()  # Local (SQLite)
```

## Output Files

### Generated Files

1. **JSON Extraction Data** (`{pdf_name}_extracted.json`)
   - Contains all extracted information
   - Useful for debugging
   - Human-readable format

2. **iCalendar File** (`{pdf_name}.ics`)
   - Calendar file for import
   - Contains all events
   - Compatible with Google Calendar, Apple Calendar, etc.

### File Naming

**Format:** `<COURSECODE>_<TERM>_Lec<SECTION>_Lab<SECTION>_<HASH8>.ics`

**Example:** `PHYS3140A_Fall2025_Lec001_Lab002_3fa21c9b.ics`

**Fallback:** If course code/term not extracted, uses PDF name + hash

## Troubleshooting

### PDF Extraction Returns 0 Sections/Assessments

**Cause:** Extraction patterns don't match PDF format

**Solution:**
1. Check reference PDF structure
2. Update regex patterns in `pdf_extractor.py`
3. Test with reference PDF

### Cache Not Working

**For SQLite:**
- Check `~/.course_outline_cache/cache.db` exists
- Verify write permissions

**For Supabase:**
- Check `DATABASE_URL` is set correctly
- Verify Supabase project is active (not paused)
- Test connection: `python3 query_supabase_simple.py`

### Database Connection Errors

**Symptoms:** "Connection refused" or "timeout"

**Solutions:**
1. Check Supabase project status (may be paused)
2. Verify connection string format
3. Check firewall/network settings
4. Try connection pooler (port 6543)

## Development Workflow

### Making Changes

1. **Update Code**
   - Make changes to source files
   - Follow code style guidelines (see `PROJECT_INSTRUCTIONS.md`)

2. **Test Changes**
   ```bash
   python3 test_cli.py
   python3 test_extraction.py
   ```

3. **Update Documentation**
   - Update `USAGE_GUIDE.md` if usage changes
   - Update `CHANGELOG.md` with changes
   - Update `DEVELOPMENT_STATUS.md` if status changes

4. **Commit to Git**
   ```bash
   git add .
   git commit -m "Description of changes"
   git push
   ```

### Adding New Features

1. **Plan:** Review `IMPLEMENTATION_PLAN.md`
2. **Implement:** Follow existing code patterns
3. **Test:** Add tests in `tests/`
4. **Document:** Update relevant documentation
5. **Commit:** Track in `CHANGELOG.md`

## Reference Documentation

- **`README.md`** - Project overview
- **`USAGE_GUIDE.md`** - Detailed usage instructions
- **`PROJECT_STRUCTURE.md`** - Complete project layout
- **`PROJECT_INSTRUCTIONS.md`** - Development guidelines
- **`DEVELOPMENT_STATUS.md`** - Current implementation status
- **`CHANGELOG.md`** - All changes and updates
- **`TESTING_GUIDE.md`** - Testing instructions

## Next Steps

1. **Web Interface** - Build Flask app and HTML templates
2. **Testing** - Comprehensive test suite
3. **Deployment** - Railway deployment setup
4. **PDF Pattern Tuning** - Optimize extraction for Western University format

## Support

For issues or questions:
1. Check documentation files
2. Review `TROUBLESHOOTING.md` (if exists)
3. Check `DEVELOPMENT_STATUS.md` for known issues
4. Review code comments (all code is well-commented)

