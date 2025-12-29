# Web Interface Guide

**Complete guide for using the web interface of the Course Outline to iCalendar Converter.**

## Starting the Web Application

### Prerequisites
- Python 3.8 or higher
- All dependencies installed: `pip install -r requirements.txt`

### Start the Server

```bash
cd /Users/kalp/Desktop/Plato
python3 src/app.py
```

The server will start on `http://localhost:5000`

### Access the Application

Open your web browser and navigate to:
```
http://localhost:5000
```

## Using the Web Interface

### Step 1: Upload PDF

1. **Navigate to Home Page**
   - The home page shows the upload form
   - URL: `http://localhost:5000/`

2. **Select PDF File**
   - Click "Choose File" button
   - Select your course outline PDF
   - Maximum file size: 16MB

3. **Optional: Force Refresh**
   - Check "Force refresh" if you want to re-extract even if PDF is cached
   - Useful if you've updated the PDF or want fresh extraction

4. **Upload**
   - Click "Upload and Extract" button
   - The system will process your PDF

### Step 2: Review Extracted Data

After upload, you'll be redirected to the review page (`/review`).

**What You'll See:**

1. **Course Information**
   - Course code and name
   - Term name and dates
   - Extracted from PDF

2. **Lecture Section Selection**
   - If multiple lecture sections found, select yours from dropdown
   - Shows: Section ID, days, times, location
   - If none found, you can proceed or use manual mode

3. **Lab Section Selection**
   - If multiple lab sections found, select yours from dropdown
   - Shows: Section ID, days, times, location
   - Optional - select "No Lab Section" if you don't have one

4. **Assessments List**
   - All assessments found in PDF
   - Shows: Title, type, weight, due date, confidence
   - Items marked "Needs Review" are highlighted
   - Review each assessment for accuracy

5. **Study Plan Lead Times**
   - Default mapping shown:
     - 0-5%: 3 days before due
     - 6-10%: 7 days
     - 11-20%: 14 days
     - 21-30%: 21 days
     - 31%+: 28 days
     - Finals: 28 days

### Step 3: Generate Calendar

1. **Select Sections**
   - Choose your lecture section (required if multiple exist)
   - Choose your lab section (optional)

2. **Review Assessments**
   - Check that all assessments are correct
   - Note any that need review (highlighted in yellow)

3. **Generate**
   - Click "Generate Calendar" button
   - System will:
     - Generate study plan events
     - Create recurring lecture/lab events
     - Create assessment due dates
     - Generate .ics file

4. **Download**
   - Automatically redirected to download page
   - .ics file downloads automatically
   - File is named: `<COURSECODE>_<TERM>_Lec<SECTION>_Lab<SECTION>_<HASH8>.ics`

### Step 4: Import to Calendar

**Google Calendar:**
1. Open Google Calendar
2. Click "+" → "Import"
3. Select the downloaded .ics file
4. Choose calendar and click "Import"

**Apple Calendar:**
1. Open Calendar app
2. File → Import
3. Select the downloaded .ics file
4. Choose calendar and click "Import"

## Manual Mode

If PDF extraction fails or you prefer manual entry:

1. **Click "Manual Mode"** button on home page
2. **Enter Term Information**
   - Term name (e.g., "Fall 2025")
   - Start date
   - End date

3. **Enter Lecture Section** (if applicable)
   - Check "I have a lecture section"
   - Enter days of week (e.g., "MWF")
   - Enter start and end times
   - Enter location (optional)

4. **Enter Lab Section** (if applicable)
   - Similar to lecture section

5. **Add Assessments**
   - Click "Add Another Assessment" for each one
   - Enter: Title, type, due date, weight (optional)

6. **Generate Calendar**
   - Click "Generate Calendar"
   - Download .ics file

## Features

### Caching
- **Automatic Caching:** Extracted data is cached by PDF hash
- **User Choices Cached:** Your section selections are saved separately
- **Force Refresh:** Re-extract even if cached

### Error Handling
- **Clear Error Messages:** If something goes wrong, you'll see a helpful message
- **Validation:** File type and size are validated before upload
- **Fallback Options:** Manual mode available if extraction fails

### User Experience
- **Responsive Design:** Works on desktop and mobile
- **Clean Interface:** Simple, beginner-friendly design
- **Progress Feedback:** Flash messages show what's happening

## Routes

The web application has the following routes:

- **GET /** - Home page with upload form
- **POST /upload** - Handle PDF upload and extraction
- **GET /review** - Review page with extracted data
- **POST /review** - Process selections and generate calendar
- **GET /manual** - Manual entry form
- **POST /manual** - Process manual input (to be implemented)
- **GET /download/<filename>** - Download generated .ics file

## Session Management

The application uses Flask sessions to:
- Store extracted data between pages
- Remember your PDF hash
- Cache your section selections
- Track your session ID for user choices

Sessions are stored server-side and expire when you close your browser.

## Troubleshooting

### "No file selected"
- Make sure you clicked "Choose File" and selected a PDF
- Check that the file is actually a PDF (not a Word doc, etc.)

### "File too large"
- Maximum file size is 16MB
- Try compressing the PDF or using a smaller file

### "Error extracting PDF"
- The PDF might be corrupted or password-protected
- Try using Manual Mode instead
- Check that it's a valid course outline PDF

### "No data to review"
- Session may have expired
- Go back to home page and upload again

### Page not loading
- Make sure the Flask server is running
- Check that you're accessing `http://localhost:5000`
- Check terminal for error messages

## Development Notes

### File Structure
- **Templates:** `templates/` directory
  - `base.html` - Base template with header/footer
  - `index.html` - Upload page
  - `review.html` - Review page
  - `manual.html` - Manual entry page
  - `error.html` - Error page

- **Static Files:** `static/` directory
  - `style.css` - All styling
  - `app.js` - Client-side JavaScript

- **Uploads:** `uploads/` directory (created automatically, gitignored)
- **Temp Calendars:** `temp_calendars/` directory (created automatically, gitignored)

### Configuration
- **Secret Key:** Set `SECRET_KEY` environment variable for production
- **Database:** Set `DATABASE_URL` for Supabase (optional, uses SQLite by default)
- **Port:** Default is 5000, can be changed in `app.py`

### Running in Production
For production deployment (Railway, etc.):
- Set `FLASK_ENV=production`
- Set proper `SECRET_KEY`
- Use production WSGI server (gunicorn)
- Configure `DATABASE_URL` for Supabase

## Next Steps

The web interface is now functional! You can:
1. Upload PDFs
2. Review extracted data
3. Select sections
4. Generate and download .ics files

**Remaining work:**
- Complete manual mode implementation
- Add assessment editing in review page
- Add lead-time override functionality
- Improve error handling and user feedback

