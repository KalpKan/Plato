# Quick Start Guide

## Installation

```bash
# 1. Install Python dependencies
pip install -r requirements.txt
```

## Starting the Web Application

```bash
# 2. Start the Flask web server
python src/app.py
```

Then open your browser and go to:
```
http://localhost:5000
```

## Using the Web Interface

1. **Upload PDF**: Click "Choose File" and select your course outline PDF
2. **Review Extraction**: The system extracts and displays course information
3. **Select Sections**: Choose your lecture and lab sections (if multiple exist)
4. **Review Assessments**: Review and edit any assessments that need attention
5. **Confirm Lead Times**: Review the lead-time mapping (shown once)
6. **Download Calendar**: Click "Download .ics" to get your calendar file

## What Happens

1. **PDF Processing**: The tool extracts course information from the PDF
2. **Web UI Review**: You'll see extracted data in a user-friendly interface
3. **Section Selection**: Select your lecture/lab sections via dropdown menus
4. **Assessment Review**: Edit any ambiguous assessments or missing data
5. **Lead Time Confirmation**: Confirm the default lead-time mapping (shown once)
6. **File Generation**: Download the `.ics` file with proper naming

## Importing to Calendar

### Google Calendar
1. Open Google Calendar
2. Click the "+" button → "Import"
3. Select the `.ics` file
4. Choose your calendar and click "Import"

### Apple Calendar
1. Open Calendar app
2. File → Import
3. Select the `.ics` file
4. Choose your calendar and click "Import"

## Web Interface Features

- **Force Refresh**: Check "Force Refresh" to re-extract even if PDF is cached
- **Manual Mode**: Click "Manual Mode" if PDF extraction fails
- **Review & Edit**: All extracted data can be reviewed and edited before generating calendar
- **Lead Time Override**: Override lead times for individual assessments during review

## Troubleshooting

### "PDF file not found"
- Check that the file path is correct
- Use absolute path if relative path doesn't work

### "Term information not found"
- The tool will prompt you to enter term information manually
- Enter dates in YYYY-MM-DD format

### "No sections found"
- The tool will prompt you to enter section information manually
- Enter days as abbreviations (e.g., "MWF" for Mon/Wed/Fri)
- Enter times in 24-hour format (e.g., "14:30" for 2:30 PM)

### Calendar import fails
- Check that the .ics file was generated successfully
- Try opening the .ics file in a text editor to verify it's valid
- Ensure your calendar app supports .ics import

## Cache Location

Cached results are stored in:
- **macOS/Linux**: `~/.course_outline_cache/`
- **Windows**: `%USERPROFILE%\.course_outline_cache\`

To clear cache, delete this directory.

## Getting Help

- See `README.md` for detailed documentation
- See `SUMMARY.md` for implementation overview
- See `CLARIFYING_QUESTIONS.md` for future enhancements

