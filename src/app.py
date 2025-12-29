"""
Flask web application for Course Outline to iCalendar Converter.

This is the main web interface for the application. It provides:
- PDF upload functionality
- Data review and editing interface
- Section selection
- Assessment review
- Manual mode for manual data entry
- Calendar file download
"""

import os
import json
import hashlib
import uuid
from pathlib import Path
from datetime import date, datetime, time
from typing import Optional, Dict, Any
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash, jsonify
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

from .models import (
    ExtractedCourseData, UserSelections, CourseTerm, SectionOption, AssessmentTask,
    serialize_date, serialize_datetime, serialize_time,
    deserialize_date, deserialize_datetime, deserialize_time
)
from .cache import get_cache_manager, compute_pdf_hash
from .pdf_extractor import PDFExtractor
from .rule_resolver import RuleResolver
from .study_plan import StudyPlanGenerator
from .icalendar_gen import ICalendarGenerator

# Initialize Flask app
# Set template and static folders to be in project root
app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
UPLOAD_FOLDER = Path('uploads')
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Initialize cache manager (auto-selects SQLite or Supabase)
cache_manager = get_cache_manager()


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed.
    
    Args:
        filename: Name of the uploaded file
        
    Returns:
        True if file extension is allowed, False otherwise
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def serialize_section(section: Optional[SectionOption]) -> Optional[Dict[str, Any]]:
    """Serialize SectionOption to dict.
    
    Args:
        section: SectionOption object to serialize, or None
        
    Returns:
        Dictionary representation of section, or None
    """
    if section is None:
        return None
    return {
        "section_type": section.section_type,
        "section_id": section.section_id,
        "days_of_week": section.days_of_week,
        "start_time": serialize_time(section.start_time),
        "end_time": serialize_time(section.end_time),
        "location": section.location
    }


def serialize_extracted_data(data: ExtractedCourseData) -> Dict[str, Any]:
    """Serialize ExtractedCourseData to JSON-serializable dict.
    
    This function converts the ExtractedCourseData object into a dictionary
    that can be easily converted to JSON for storage in session or database.
    
    Args:
        data: ExtractedCourseData object to serialize
        
    Returns:
        Dictionary representation of the data
    """
    return {
        "term": {
            "term_name": data.term.term_name,
            "start_date": serialize_date(data.term.start_date),
            "end_date": serialize_date(data.term.end_date),
            "timezone": data.term.timezone
        },
        "lecture_sections": [
            {
                "section_type": s.section_type,
                "section_id": s.section_id,
                "days_of_week": s.days_of_week,
                "start_time": serialize_time(s.start_time),
                "end_time": serialize_time(s.end_time),
                "location": s.location
            }
            for s in data.lecture_sections
        ],
        "lab_sections": [
            {
                "section_type": s.section_type,
                "section_id": s.section_id,
                "days_of_week": s.days_of_week,
                "start_time": serialize_time(s.start_time),
                "end_time": serialize_time(s.end_time),
                "location": s.location
            }
            for s in data.lab_sections
        ],
        "assessments": [
            {
                "title": a.title,
                "type": a.type,
                "weight_percent": a.weight_percent,
                "due_datetime": serialize_datetime(a.due_datetime) if a.due_datetime else None,
                "due_rule": a.due_rule,
                "rule_anchor": a.rule_anchor,
                "confidence": a.confidence,
                "source_evidence": a.source_evidence,
                "needs_review": a.needs_review
            }
            for a in data.assessments
        ],
        "course_code": data.course_code,
        "course_name": data.course_name
    }


def calculate_completeness(data: ExtractedCourseData) -> Dict[str, Any]:
    """Calculate extraction completeness metrics.
    
    This function analyzes the extracted course data to determine:
    - How much of the course material is successfully extracted
    - What information is missing
    - Total assessment weight (handling extra credit >100%)
    
    Args:
        data: ExtractedCourseData object
        
    Returns:
        Dictionary with completeness metrics
    """
    metrics = {
        'course_code_found': data.course_code is not None,
        'course_name_found': data.course_name is not None,
        'term_found': data.term is not None and data.term.term_name != "Unknown",
        'lecture_sections_found': len(data.lecture_sections) > 0,
        'lab_sections_found': len(data.lab_sections) > 0,
        'num_lecture_sections': len(data.lecture_sections),
        'num_lab_sections': len(data.lab_sections),
        'num_assessments': len(data.assessments),
        'assessments_with_weight': 0,
        'assessments_with_date': 0,
        'assessments_complete': 0,  # Has both weight and date
        'total_weight': 0.0,
        'total_weight_with_dates': 0.0,
        'total_weight_without_dates': 0.0,
        'has_extra_credit': False,
    }
    
    # Analyze assessments
    for assessment in data.assessments:
        has_weight = assessment.weight_percent is not None
        has_date = assessment.due_datetime is not None
        
        if has_weight:
            metrics['assessments_with_weight'] += 1
            metrics['total_weight'] += assessment.weight_percent
            
            if has_date:
                metrics['assessments_complete'] += 1
                metrics['total_weight_with_dates'] += assessment.weight_percent
            else:
                metrics['total_weight_without_dates'] += assessment.weight_percent
        
        if has_date:
            metrics['assessments_with_date'] += 1
    
    # Check for extra credit (total > 100%)
    if metrics['total_weight'] > 100.0:
        metrics['has_extra_credit'] = True
    
    # Calculate completeness percentages
    total_items = 0
    found_items = 0
    
    # Course info
    total_items += 2  # course_code, course_name
    if metrics['course_code_found']:
        found_items += 1
    if metrics['course_name_found']:
        found_items += 1
    
    # Term
    total_items += 1
    if metrics['term_found']:
        found_items += 1
    
    # Sections
    total_items += 2  # lecture sections, lab sections
    if metrics['lecture_sections_found']:
        found_items += 1
    if metrics['lab_sections_found']:
        found_items += 1
    
    # Assessments completeness
    if metrics['num_assessments'] > 0:
        assessment_completeness = (metrics['assessments_complete'] / metrics['num_assessments']) * 100
    else:
        assessment_completeness = 0.0
    
    metrics['overall_completeness'] = (found_items / total_items) * 100 if total_items > 0 else 0.0
    metrics['assessment_completeness'] = assessment_completeness
    
    return metrics


def deserialize_extracted_data(data: Dict[str, Any]) -> ExtractedCourseData:
    """Deserialize dict to ExtractedCourseData.
    
    This function converts a dictionary (from JSON) back into an
    ExtractedCourseData object. Used when loading data from cache or session.
    
    Args:
        data: Dictionary representation of ExtractedCourseData
        
    Returns:
        ExtractedCourseData object
    """
    from .models import CourseTerm, SectionOption, AssessmentTask
    
    term_dict = data["term"]
    term = CourseTerm(
        term_name=term_dict["term_name"],
        start_date=deserialize_date(term_dict["start_date"]),
        end_date=deserialize_date(term_dict["end_date"]),
        timezone=term_dict.get("timezone", "America/Toronto")
    )
    
    lecture_sections = [
        SectionOption(
            section_type=s["section_type"],
            section_id=s["section_id"],
            days_of_week=s["days_of_week"],
            start_time=deserialize_time(s["start_time"]),
            end_time=deserialize_time(s["end_time"]),
            location=s.get("location")
        )
        for s in data.get("lecture_sections", [])
    ]
    
    lab_sections = [
        SectionOption(
            section_type=s["section_type"],
            section_id=s["section_id"],
            days_of_week=s["days_of_week"],
            start_time=deserialize_time(s["start_time"]),
            end_time=deserialize_time(s["end_time"]),
            location=s.get("location")
        )
        for s in data.get("lab_sections", [])
    ]
    
    assessments = [
        AssessmentTask(
            title=a["title"],
            type=a["type"],
            weight_percent=a.get("weight_percent"),
            due_datetime=deserialize_datetime(a["due_datetime"]) if a.get("due_datetime") else None,
            due_rule=a.get("due_rule"),
            rule_anchor=a.get("rule_anchor"),
            confidence=a.get("confidence", 0.0),
            source_evidence=a.get("source_evidence"),
            needs_review=a.get("needs_review", False)
        )
        for a in data.get("assessments", [])
    ]
    
    return ExtractedCourseData(
        term=term,
        lecture_sections=lecture_sections,
        lab_sections=lab_sections,
        assessments=assessments,
        course_code=data.get("course_code"),
        course_name=data.get("course_name")
    )


@app.route('/')
def index():
    """Home page with PDF upload form.
    
    This is the main entry point of the web application. Users can upload
    a course outline PDF here to begin the conversion process.
    
    Returns:
        Rendered index.html template
    """
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle PDF file upload.
    
    This route processes the uploaded PDF file:
    1. Validates the file
    2. Saves it temporarily
    3. Computes PDF hash
    4. Checks cache for existing extraction
    5. Extracts data if not cached
    6. Redirects to review page
    
    Returns:
        Redirect to review page or error page
    """
    # Check if file was uploaded
    if 'pdf_file' not in request.files:
        flash('No file selected. Please choose a PDF file.', 'error')
        return redirect(url_for('index'))
    
    file = request.files['pdf_file']
    force_refresh = request.form.get('force_refresh') == 'on'
    
    # Check if file is selected
    if file.filename == '':
        flash('No file selected. Please choose a PDF file.', 'error')
        return redirect(url_for('index'))
    
    # Check file extension
    if not allowed_file(file.filename):
        flash('Invalid file type. Please upload a PDF file.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = Path(app.config['UPLOAD_FOLDER']) / filename
        file.save(str(filepath))
        
        # Compute PDF hash
        pdf_hash = compute_pdf_hash(filepath)
        
        # Initialize session
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        # Check cache (unless force refresh)
        extracted_data = None
        if not force_refresh:
            extracted_data = cache_manager.lookup_extraction(pdf_hash)
            if extracted_data:
                flash('Found cached extraction data for this PDF.', 'info')
        
        # Extract from PDF if not cached or force refresh
        if extracted_data is None:
            try:
                extractor = PDFExtractor(filepath)
                extracted_data = extractor.extract_all()
                
                # Resolve relative rules
                resolver = RuleResolver()
                all_sections = extracted_data.lecture_sections + extracted_data.lab_sections
                extracted_data.assessments = resolver.resolve_rules(
                    extracted_data.assessments,
                    all_sections,
                    extracted_data.term
                )
                
                # Cache extraction results
                cache_manager.store_extraction(pdf_hash, extracted_data)
                flash('PDF extracted successfully.', 'success')
                
            except Exception as e:
                flash(f'Error extracting PDF: {str(e)}', 'error')
                return redirect(url_for('index'))
        
        # Store in session for review page
        session['pdf_hash'] = pdf_hash
        session['pdf_filename'] = filename
        session['extracted_data'] = serialize_extracted_data(extracted_data)
        
        # Check for cached user choices
        user_choices = cache_manager.lookup_user_choices(pdf_hash, session.get('session_id'))
        if user_choices:
            session['user_choices'] = {
                'selected_lecture_section': serialize_section(user_choices.selected_lecture_section) if user_choices and user_choices.selected_lecture_section else None,
                'selected_lab_section': serialize_section(user_choices.selected_lab_section) if user_choices and user_choices.selected_lab_section else None,
            }
        else:
            session['user_choices'] = {}
        
        # Redirect to review page
        return redirect(url_for('review'))
        
    except RequestEntityTooLarge:
        flash('File too large. Maximum size is 16MB.', 'error')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/review', methods=['GET', 'POST'])
def review():
    """Review and edit extracted data.
    
    GET: Display review page with extracted data
    POST: Process user selections and generate calendar
    
    Returns:
        Rendered review.html template or redirect to download
    """
    # Check if we have extracted data
    if 'extracted_data' not in session:
        flash('No data to review. Please upload a PDF first.', 'error')
        return redirect(url_for('index'))
    
    extracted_data_dict = session['extracted_data']
    extracted_data = deserialize_extracted_data(extracted_data_dict)
    
    # ALWAYS check cache first - session data can be stale
    # This ensures we always have the latest extracted data
    pdf_hash = session.get('pdf_hash')
    if pdf_hash:
        cached_data = cache_manager.lookup_extraction(pdf_hash)
        if cached_data:
            # Use cached data (it's more reliable than session)
            extracted_data = cached_data
            # Update session with fresh data
            session['extracted_data'] = serialize_extracted_data(extracted_data)
    
    # Check if assessments are missing (likely stale session data)
    # This happens when session has old data from before extraction was fixed
    if len(extracted_data.assessments) == 0:
        print(f"DEBUG: No assessments found in session data. PDF hash: {session.get('pdf_hash')}")
        # Try to re-extract from cache or suggest force refresh
        pdf_hash = session.get('pdf_hash')
        if pdf_hash:
            cached_data = cache_manager.lookup_extraction(pdf_hash)
            if cached_data and len(cached_data.assessments) > 0:
                # Use cached data instead
                extracted_data = cached_data
                session['extracted_data'] = serialize_extracted_data(extracted_data)
                flash('Loaded updated assessment data from cache.', 'info')
            else:
                # Cache also empty - try re-extracting from PDF
                pdf_filename = session.get('pdf_filename')
                if pdf_filename:
                    filepath = Path(app.config['UPLOAD_FOLDER']) / pdf_filename
                    if filepath.exists():
                        try:
                            from .pdf_extractor import PDFExtractor
                            from .rule_resolver import RuleResolver
                            
                            extractor = PDFExtractor(filepath)
                            extracted_data = extractor.extract_all()
                            
                            # Resolve relative rules
                            resolver = RuleResolver()
                            all_sections = extracted_data.lecture_sections + extracted_data.lab_sections
                            extracted_data.assessments = resolver.resolve_rules(
                                extracted_data.assessments,
                                all_sections,
                                extracted_data.term
                            )
                            
                            # Update session and cache
                            session['extracted_data'] = serialize_extracted_data(extracted_data)
                            cache_manager.store_extraction(pdf_hash, extracted_data)
                            flash('Re-extracted assessments from PDF.', 'info')
                        except Exception as e:
                            flash(f'Could not re-extract: {str(e)}', 'warning')
    
    if request.method == 'POST':
        # Process form submission
        # Get selected sections
        lecture_idx = request.form.get('lecture_section')
        lab_idx = request.form.get('lab_section')
        
        user_selections = UserSelections()
        
        # Set selected lecture section
        if lecture_idx and lecture_idx != 'none':
            try:
                idx = int(lecture_idx)
                if 0 <= idx < len(extracted_data.lecture_sections):
                    user_selections.selected_lecture_section = extracted_data.lecture_sections[idx]
            except (ValueError, IndexError):
                pass
        
        # Set selected lab section
        if lab_idx and lab_idx != 'none':
            try:
                idx = int(lab_idx)
                if 0 <= idx < len(extracted_data.lab_sections):
                    user_selections.selected_lab_section = extracted_data.lab_sections[idx]
            except (ValueError, IndexError):
                pass
        
        # Store user choices in session
        session['user_choices'] = {
            'selected_lecture_section': serialize_section(user_selections.selected_lecture_section),
            'selected_lab_section': serialize_section(user_selections.selected_lab_section),
        }
        
        # Generate calendar
        try:
            # Generate study plan
            study_plan_gen = StudyPlanGenerator()
            study_plan = study_plan_gen.generate_study_plan(extracted_data.assessments)
            
            # Generate calendar
            cal_gen = ICalendarGenerator(timezone_str=extracted_data.term.timezone)
            calendar = cal_gen.generate_calendar(
                term=extracted_data.term,
                lecture_section=user_selections.selected_lecture_section,
                lab_section=user_selections.selected_lab_section,
                assessments=extracted_data.assessments,
                study_plan=study_plan
            )
            
            # Generate filename
            pdf_hash = session.get('pdf_hash', 'unknown')
            hash_short = pdf_hash[:8] if len(pdf_hash) >= 8 else pdf_hash
            course_code = extracted_data.course_code or 'Unknown'
            term_name = extracted_data.term.term_name.replace(' ', '')
            lec_id = user_selections.selected_lecture_section.section_id if user_selections.selected_lecture_section and user_selections.selected_lecture_section.section_id else 'None'
            lab_id = user_selections.selected_lab_section.section_id if user_selections.selected_lab_section and user_selections.selected_lab_section.section_id else 'None'
            
            # Sanitize filename components
            course_code_safe = (course_code or 'Unknown').replace(' ', '_').replace('/', '_')
            term_name_safe = term_name.replace(' ', '').replace('/', '_')
            lec_id_safe = lec_id if lec_id else 'None'
            lab_id_safe = lab_id if lab_id else 'None'
            hash_short_safe = hash_short[:8] if len(hash_short) >= 8 else hash_short
            
            filename = f"{course_code_safe}_{term_name_safe}_Lec{lec_id_safe}_Lab{lab_id_safe}_{hash_short_safe}.ics"
            # Final sanitization - remove any problematic characters
            filename = "".join(c for c in filename if c.isalnum() or c in "._-")
            
            # Save calendar to temporary file (use absolute path to avoid path issues)
            # Get project root (parent of src directory)
            project_root = Path(__file__).parent.parent
            temp_dir = project_root / 'temp_calendars'
            temp_dir.mkdir(exist_ok=True)
            temp_path = temp_dir / filename
            
            # Ensure the file is written successfully
            cal_gen.export_to_file(calendar, str(temp_path))
            
            if not temp_path.exists():
                raise FileNotFoundError(f"Calendar file was not created at {temp_path}")
            
            # Store in session (use absolute path)
            session['calendar_filename'] = filename
            session['calendar_path'] = str(temp_path.absolute())
            
            # Cache user choices
            pdf_hash = session.get('pdf_hash')
            if pdf_hash:
                cache_manager.store_user_choices(
                    pdf_hash,
                    user_selections,
                    session.get('session_id')
                )
            
            # Redirect to download
            return redirect(url_for('download', filename=filename))
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error generating calendar: {error_details}")
            flash(f'Error generating calendar: {str(e)}. Please try again or contact support if the issue persists.', 'error')
            # Continue to show review page with error
    
    # Get study plan mapping for display
    study_plan_gen = StudyPlanGenerator()
    lead_time_mapping = study_plan_gen.get_default_mapping_display()
    
    # Calculate completeness metrics (do this for both GET and POST)
    completeness = calculate_completeness(extracted_data)
    
    # Prepare assessments list for template
    assessments_list = []
    for a in extracted_data.assessments:
        assessments_list.append({
            'title': a.title,
            'type': a.type,
            'weight_percent': a.weight_percent,
            'due_datetime': a.due_datetime,  # Keep as datetime object for template
            'due_rule': a.due_rule,
            'confidence': a.confidence,
            'source_evidence': a.source_evidence,
            'needs_review': a.needs_review
        })
    
    # Prepare data for template (convert to dict for easier template handling)
    context = {
        'extracted_data': extracted_data_dict,
        'course_code': extracted_data.course_code or 'Not found',
        'course_name': extracted_data.course_name or 'Not found',
        'term': {
            'term_name': extracted_data.term.term_name,
            'start_date': extracted_data.term.start_date,
            'end_date': extracted_data.term.end_date,
            'timezone': extracted_data.term.timezone
        },
        'completeness': completeness,
        'lecture_sections': [
            {
                'section_type': s.section_type,
                'section_id': s.section_id,
                'days_of_week': s.days_of_week,
                'start_time': s.start_time,
                'end_time': s.end_time,
                'location': s.location
            }
            for s in extracted_data.lecture_sections
        ],
        'lab_sections': [
            {
                'section_type': s.section_type,
                'section_id': s.section_id,
                'days_of_week': s.days_of_week,
                'start_time': s.start_time,
                'end_time': s.end_time,
                'location': s.location
            }
            for s in extracted_data.lab_sections
        ],
        'assessments': assessments_list,
        'lead_time_mapping': lead_time_mapping,
        'user_choices': session.get('user_choices', {})
    }
    
    return render_template('review.html', **context)


@app.route('/manual', methods=['GET', 'POST'])
def manual():
    """Manual data entry mode.
    
    GET: Display manual entry form
    POST: Process manual input and generate calendar
    
    Returns:
        Rendered manual.html template or redirect to download
    """
    if request.method == 'POST':
        # Process manual form data
        # This will be implemented to handle manual input
        flash('Manual mode is not yet fully implemented.', 'info')
        return redirect(url_for('index'))
    
    return render_template('manual.html')


@app.route('/download/<filename>')
def download(filename: str):
    """Download generated .ics file.
    
    Args:
        filename: Name of the calendar file to download
        
    Returns:
        File download response or redirect with error message
    """
    # Check if file exists in session
    if 'calendar_path' not in session or session.get('calendar_filename') != filename:
        flash('Calendar file not found. Please generate a calendar first.', 'error')
        return redirect(url_for('review'))
    
    filepath = Path(session['calendar_path'])
    
    # Handle both absolute and relative paths
    if not filepath.is_absolute():
        project_root = Path(__file__).parent.parent
        filepath = project_root / filepath
    
    if not filepath.exists():
        flash('Calendar file not found. Please try generating the calendar again.', 'error')
        return redirect(url_for('review'))
    
    try:
        return send_file(
            str(filepath),
            as_attachment=True,
            download_name=filename,
            mimetype='text/calendar'
        )
    except Exception as e:
        flash(f'Error downloading calendar: {str(e)}. Please try generating the calendar again.', 'error')
        return redirect(url_for('review'))


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return render_template('error.html', error='Internal server error'), 500


if __name__ == '__main__':
    # Run development server
    app.run(debug=True, host='0.0.0.0', port=5000)

