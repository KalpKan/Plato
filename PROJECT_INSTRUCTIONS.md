# Project Instructions

This document contains the development guidelines and instructions for the Course Outline to iCalendar Converter project.

## General Guidelines

### 1. Reference PDF Document
- **Always refer to** `BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf` when:
  - Understanding how course outlines are structured
  - Determining where specific fields are located in PDFs
  - Understanding the format of inputs
  - Implementing or updating extraction logic

### 2. Git Workflow

#### Files to Track in Git
- All source code files (`src/*.py`)
- Test files (`tests/*.py`)
- Configuration files (`requirements.txt`, `setup.py`)
- Documentation files (`README.md`, `QUICK_START.md`, `USAGE_GUIDE.md`, `PROJECT_INSTRUCTIONS.md`)
- `.gitignore` file

#### Files to Exclude from Git
- Planning files (excluded via `.gitignore`):
  - `IMPLEMENTATION_PLAN.md`
  - `ARCHITECTURE.md`
  - `DATA_MODELS.md`
  - `EXTRACTION_HEURISTICS.md`
  - `CACHING_APPROACH.md`
  - `TEST_PLAN.md`
  - `CLARIFYING_QUESTIONS.md`
  - `SUMMARY.md`
  - `CHANGES_SUMMARY.md`
  - PDF files (including the reference PDF)

### 3. Documentation Updates

#### After Every Change
- Update `USAGE_GUIDE.md` to reflect:
  - New features or functionality
  - Changes to existing behavior
  - Updated usage instructions
  - New error handling or edge cases

#### Purpose
- `USAGE_GUIDE.md` serves as detailed documentation for git
- Tracks how to use the program
- Documents all changes and updates

### 4. Code Style Guidelines

#### No Emojis
- **Never use emojis in code**
- Do not use emojis in:
  - Source code files
  - Comments
  - Documentation files
  - Error messages
  - Log messages

#### Code Comments
- **All code must be commented** such that any beginner can understand what is going on
- Comments should explain:
  - What each function/class does
  - What parameters mean and their expected types
  - What return values represent
  - Complex logic, algorithms, or business rules
  - Why certain decisions were made (if not obvious)
  - Edge cases and error handling

#### Comment Style
- Use docstrings for functions and classes
- Use inline comments for complex logic
- Explain "why" not just "what" when helpful
- Keep comments up-to-date with code changes

### 5. PDF Extraction Guidelines

#### Field Locations
- Refer to `BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf` for:
  - Where term information appears
  - How lecture/lab schedules are formatted
  - Where assessments are listed
  - How dates and times are formatted
  - Common patterns and structures

#### Extraction Logic
- Update extraction heuristics based on the reference PDF
- Test extraction against the reference PDF
- Document any assumptions about PDF structure

### 6. Testing

#### Test Coverage
- Write tests for all new functionality
- Test edge cases and error conditions
- Test with the reference PDF when possible

#### Test Files
- Test files go in `tests/` directory
- Follow naming convention: `test_*.py`

### 7. Error Handling

#### Principles
- Never fail silently
- Provide clear, actionable error messages
- Use structured failures
- Always provide fallback options (e.g., Manual Mode)

### 8. File Naming

#### Output Files
- Format: `<COURSECODE>_<TERM>_Lec<SECTION>_Lab<SECTION>_<HASH8>.ics`
- Example: `CS3305_Fall2026_Lec001_Lab002_3fa21c9b.ics`
- Fallback: PDF name + hash if course code/term not extracted

### 9. Timezone Handling

#### Default Timezone
- Always use `America/Toronto` timezone
- Use TZID in iCalendar files (no floating time)
- Include VTIMEZONE component for maximum compatibility

### 10. Caching

#### Cache Structure
- Separate extraction cache from user choices:
  - `extraction_cache`: Derived facts from PDF (keyed by PDF hash)
  - `user_choices`: Selected sections, lead-time overrides (keyed by session/user)

#### Cache Management
- Allow force refresh option
- Support multiple users with same PDF but different sections

## Development Workflow

1. **Before Making Changes**
   - Review `PROJECT_INSTRUCTIONS.md` (this file)
   - Check `USAGE_GUIDE.md` for current behavior
   - Refer to reference PDF if working on extraction

2. **While Making Changes**
   - Follow code style guidelines
   - Write clear comments
   - Test changes thoroughly
   - Update code comments as needed

3. **After Making Changes**
   - Update `USAGE_GUIDE.md` with any changes
   - Ensure all code is committed to git
   - Verify planning files are not in git
   - Test the changes

## Code Review Checklist

- [ ] Code follows style guidelines (no emojis, well-commented)
- [ ] Comments explain code clearly for beginners
- [ ] Changes are documented in `USAGE_GUIDE.md`
- [ ] Planning files are not committed to git
- [ ] Tests pass (if applicable)
- [ ] Error handling is appropriate
- [ ] Reference PDF was consulted (if extraction-related)

## Questions or Issues

If you have questions about these instructions or need clarification:
1. Review the reference PDF for extraction-related questions
2. Check `USAGE_GUIDE.md` for usage questions
3. Review existing code for examples of style and patterns

