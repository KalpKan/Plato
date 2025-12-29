# Changelog

All notable changes to the Course Outline to iCalendar Converter project are documented in this file.

## [Unreleased] - 2025-12-29

### Added
- **Web Interface (Flask Application)**
  - Complete Flask web application (`src/app.py`)
  - Upload page with PDF file upload
  - Review page with section selection and assessment display
  - Manual mode page for manual data entry
  - Download functionality for generated .ics files
  - Session management for multi-page workflow
  - Flash messages for user feedback
  - Error handling and validation

- **HTML Templates**
  - `templates/base.html` - Base template with header/footer
  - `templates/index.html` - Upload page
  - `templates/review.html` - Review and section selection page
  - `templates/manual.html` - Manual data entry page
  - `templates/error.html` - Error page

- **Static Files**
  - `static/style.css` - Complete responsive styling
  - `static/app.js` - Client-side JavaScript for form enhancements

- **Supabase Integration**
  - Created `src/supabase_cache.py` for Supabase PostgreSQL cache manager
  - Database tables created in Supabase: `extraction_cache` and `user_choices`
  - Automatic cache manager selection based on `DATABASE_URL` environment variable
  - Support for both SQLite (local) and Supabase (production)

- **Cache System Improvements**
  - Separated extraction cache from user choices
  - New methods: `lookup_extraction()`, `store_extraction()`, `lookup_user_choices()`, `store_user_choices()`
  - Backward compatibility maintained with legacy `lookup()` and `store()` methods
  - Proper schema implementation matching database design

- **Documentation**
  - `PROJECT_STRUCTURE.md` - Complete project layout documentation
  - `CHANGELOG.md` - This file, tracking all changes
  - `MCP_SUPABASE_SETUP.md` - MCP integration guide
  - `CURSOR_MCP_CONFIG.md` - MCP configuration reference
  - `RAILWAY_SUPABASE_SETUP.md` - Deployment setup guide
  - `TESTING_GUIDE.md` - Testing instructions
  - `TEST_RESULTS.md` - Test results summary
  - `DEPLOYMENT_GUIDE.md` - Deployment options comparison

- **Testing Infrastructure**
  - `test_cli.py` - Quick functionality test script
  - `test_extraction.py` - Full pipeline test script
  - `check_supabase_tables.py` - Database connection test
  - `query_supabase_simple.py` - Database query utility

- **Code Improvements**
  - Enhanced code comments for beginners
  - Improved docstrings explaining functionality
  - Better error handling and user feedback

### Changed
- **Application Entry Point**
  - Web interface is now the primary interface
  - CLI (`src/main.py`) remains available for testing
  - Application can be started with `python src/app.py`

- **Cache System Architecture**
  - Migrated from single cache table to separate extraction and user choice tables
  - Updated `src/cache.py` to use new schema
  - Modified `src/main.py` to use new cache methods
  - Added `get_cache_manager()` function for automatic cache manager selection

- **Dependencies**
  - Added `psycopg2-binary>=2.9.0` to `requirements.txt` for Supabase support

- **Documentation**
  - Updated `README.md` to remove emojis
  - Updated `USAGE_GUIDE.md` with comprehensive usage instructions
  - Created `PROJECT_INSTRUCTIONS.md` with development guidelines
  - Updated `.gitignore` to exclude planning files and sensitive data

### Fixed
- **Cache System**
  - Fixed schema mismatch between defined tables and lookup/store methods
  - Corrected table structure to match database design
  - Fixed serialization/deserialization for user choices

- **Code Comments**
  - Improved comments in `src/pdf_extractor.py` explaining extraction logic
  - Enhanced comments in `src/models.py` explaining data structures
  - Added beginner-friendly explanations throughout

### Security
- **Credentials Management**
  - Added `.env` to `.gitignore`
  - Removed hardcoded connection strings from documentation
  - Created `.env.example` template (blocked by gitignore, but documented)

## Development Status

### Completed ✅
- Project setup and data models
- PDF extraction core functionality
- Term and section extraction
- Assessment extraction and rule resolution
- Study plan generation
- iCalendar generation (basic)
- Cache system with Supabase support
- Database tables created
- Comprehensive documentation

### In Progress 🚧
- Cache system testing and validation
- Web interface development (Flask app)
- HTML templates
- Static files (CSS, JS)

### Pending ⏳
- Flask web application (`src/app.py`)
- HTML templates (`templates/`)
- Static files (`static/`)
- Full testing suite
- Railway deployment

## Migration Notes

### From SQLite to Supabase

**For Local Development:**
- No changes needed - automatically uses SQLite when `DATABASE_URL` is not set

**For Production:**
- Set `DATABASE_URL` environment variable
- Cache manager automatically switches to Supabase
- No code changes required

### Breaking Changes
- Cache schema changed (separate tables)
- Legacy `lookup()` and `store()` methods still work but use new schema
- New methods recommended: `lookup_extraction()`, `store_extraction()`, etc.

## Next Release Goals

1. **Web Interface**
   - Flask application with upload, review, and download endpoints
   - HTML templates for user interface
   - Static files for styling and interactivity

2. **Testing**
   - Comprehensive test suite
   - Integration tests
   - End-to-end testing

3. **Deployment**
   - Railway deployment configuration
   - Environment variable setup
   - Production-ready configuration

