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
import re
import json
import urllib.request
import urllib.error
import hashlib
import uuid
from pathlib import Path
from datetime import date, datetime, time, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import replace
from .outline.term import sessional_dates
from flask import Flask, Response, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

from .models import (
    ExtractedCourseData, UserSelections, CourseTerm, SectionOption, AssessmentTask,
    serialize_date, serialize_datetime, serialize_time,
    deserialize_date, deserialize_datetime, deserialize_time,
    extracted_to_dict, section_to_dict, section_from_dict,
)
from .cache import get_cache_manager, compute_pdf_hash, PARSER_VERSION
from .pdf_extractor import PDFExtractor
from .outline.pipeline import PasswordProtected, NoTextLayer
from .rule_resolver import RuleResolver
from .study_plan import StudyPlanGenerator
from .icalendar_gen import ICalendarGenerator
from . import analytics

# Initialize Flask app
# Templates live in ../templates. Static files live in ../public/static so that
# Vercel's CDN serves them directly; Flask serves the same folder locally.
app = Flask(__name__,
            template_folder='../templates',
            static_folder='../public/static')

# SECRET_KEY signs the session cookie. There is deliberately NO default: a
# missing value must fail the deploy, not silently ship a guessable key.
_secret = os.getenv('SECRET_KEY')
if not _secret:
    raise RuntimeError(
        "SECRET_KEY environment variable is required (no default). "
        "See README 'Where the settings live'."
    )
app.secret_key = _secret

# Configuration
ALLOWED_EXTENSIONS = {'pdf'}
# Vercel's function request body is capped at 4.5 MB, so that is the real limit; the
# browser refuses larger files before uploading (public/static/app.js, same number).
MAX_FILE_SIZE_MB = 4
MAX_FILE_SIZE = int(4.5 * 1024 * 1024)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
app.config['MAX_FILE_SIZE_MB'] = MAX_FILE_SIZE_MB
# Public PostHog project key for the browser snippet (not a secret; empty = analytics off)
app.config['POSTHOG_API_KEY'] = os.getenv('POSTHOG_API_KEY', '')
app.config['POSTHOG_UI_HOST'] = os.getenv('POSTHOG_UI_HOST', 'https://us.posthog.com')


def upload_dir() -> Path:
    """Scratch directory for uploaded PDFs.

    On Vercel the only writable location is /tmp, and it does not survive
    between requests, so everything here is treated as disposable.
    """
    d = Path(os.getenv('PLATO_TMP_DIR', '/tmp')) / 'plato'
    d.mkdir(parents=True, exist_ok=True)
    return d


# Custom Jinja2 filter for 12-hour time format
@app.template_filter('time_12h')
def time_12h_filter(time_obj):
    """Convert time object to 12-hour format with AM/PM."""
    if not time_obj:
        return 'N/A'
    if isinstance(time_obj, time):
        hour = time_obj.hour
        minute = time_obj.minute
        ampm = 'AM' if hour < 12 else 'PM'
        display_hour = hour % 12
        if display_hour == 0:
            display_hour = 12
        return f"{display_hour}:{minute:02d} {ampm}"
    elif isinstance(time_obj, datetime):
        hour = time_obj.hour
        minute = time_obj.minute
        ampm = 'AM' if hour < 12 else 'PM'
        display_hour = hour % 12
        if display_hour == 0:
            display_hour = 12
        return f"{display_hour}:{minute:02d} {ampm}"
    return str(time_obj)

# Cache manager is created on first use (auto-selects SQLite or Postgres) so
# that importing the module never opens a database connection.
_cache = None


def get_cache():
    """Return the process-wide cache manager, creating it on first call."""
    global _cache
    if _cache is None:
        _cache = get_cache_manager()
    return _cache


def visitor_key(pdf_hash: str, session_id: Optional[str]) -> str:
    """Cache key for one visitor's edited copy of one PDF's data.

    The parser's own output stays under the bare pdf_hash and is shared by everyone who
    uploads the same file; every edit (title, weight, date, added row) is written to this
    per-visitor key instead, so one student can never rewrite another's outline.
    """
    return f"{pdf_hash}:{session_id or 'anon'}"


def load_extracted() -> Optional[ExtractedCourseData]:
    """Load the current PDF's data: the visitor's edited copy if there is one, else the
    shared parser output.

    The signed session cookie only carries the PDF hash (plus the filename, a session id
    and the user's choices); the data itself lives in the extraction cache, so any server
    instance can serve any request.
    """
    pdf_hash = session.get('pdf_hash')
    if not pdf_hash:
        return None
    cache = get_cache()
    own = cache.lookup_extraction(visitor_key(pdf_hash, session.get('session_id')))
    if own is not None:
        return own
    return cache.lookup_extraction(pdf_hash)


def save_extracted(extracted_data: ExtractedCourseData) -> None:
    """Persist the visitor's edited copy (never the shared parser output)."""
    pdf_hash = session.get('pdf_hash')
    if pdf_hash:
        get_cache().store_extraction(visitor_key(pdf_hash, session.get('session_id')), extracted_data)


def discard_visitor_copy(pdf_hash: str, session_id: Optional[str]) -> None:
    """Forget a visitor's edits (force refresh)."""
    try:
        get_cache().delete_extraction(visitor_key(pdf_hash, session_id))
    except Exception:
        pass


def _lead_time_generator(custom_lead_time_mapping: Dict[str, Any]) -> StudyPlanGenerator:
    """Build a StudyPlanGenerator honouring the user's custom range -> days mapping."""
    if not custom_lead_time_mapping:
        return StudyPlanGenerator()
    range_to_threshold = {
        "0-5%": 5,
        "6-10%": 10,
        "11-20%": 20,
        "21-30%": 30,
        "31%+": 50,
        "Finals": 50  # Finals use the same as 31%+
    }
    lead_time_mapping_for_gen = StudyPlanGenerator().lead_time_mapping.copy()
    for range_key, days in custom_lead_time_mapping.items():
        threshold = range_to_threshold.get(range_key)
        if threshold:
            lead_time_mapping_for_gen[threshold] = days
    return StudyPlanGenerator(lead_time_mapping=lead_time_mapping_for_gen)


# "Labs (Total = 8)", "(8)", "10 sessions": a count the outline states. The digit in "Term 1 Lab
# Assignments" or "Week 2 lab" is a label, not a count (D23), hence the plural and the lookbehind.
_STATED_TOTAL = re.compile(r"total\s*=\s*(\d{1,2})|\((\d{1,2})\)|(?<!term )(?<!week )(?<!unit )\b(\d{1,2})\s+(?:labs|reports|sessions|tutorials|quizzes)\b", re.I)
_TERM_HALF = re.compile(r"\b(?:term\s*(1|2)|(first|second)\s+term|(fall|winter)\s+term)\b", re.I)


def _term_half(a: AssessmentTask, term: CourseTerm) -> Optional[Tuple[date, date]]:
    """'Term 1 Lab Assignments' in a September-to-April course: the labs of the first half only."""
    if not term.start_date or not term.end_date or term.start_date.month < 8 or term.end_date.month > 6:
        return None
    m = _TERM_HALF.search(f"{a.title} {(a.source_evidence or '').split('|')[0]}")
    if not m:
        return None
    first = (m.group(1) == "1") or (m.group(2) or "").lower() == "first" or (m.group(3) or "").lower() == "fall"
    y1, y2 = term.start_date.year, term.end_date.year
    dec_exams = next((a for a, _ in (term.exam_periods or []) if a.month == 12), None)
    fall = sessional_dates("Fall", y1)
    fall_end = (dec_exams - timedelta(days=1)) if dec_exams else (fall["end"] if fall else date(y1, 12, 10))
    winter = sessional_dates("Winter", y2)
    winter_start = winter["start"] if winter else date(y2, 1, 5)
    if first:
        return term.start_date, min(fall_end, term.end_date)
    return max(winter_start, term.start_date), term.end_date


def rule_hint(a: AssessmentTask, sections: List[SectionOption]) -> Optional[str]:
    """The line the review page prints under a rule-typed row (None when it is not one)."""
    if not a.due_rule or a.due_datetime:
        return None
    anchor = a.rule_anchor
    if not anchor:
        return f"Relative rule: {a.due_rule}. Set the dates by hand (the outline ties them to something the calendar cannot see)."
    have = any((s.section_type or '').lower().startswith(anchor) for s in sections)
    if have:
        return f"Relative rule: {a.due_rule}. One due event per {anchor} is generated from your {anchor} slot."
    return f"Relative rule: {a.due_rule}. Add your {anchor} slot with \"Add Section\" and you get one due event per {anchor}."


def expand_rule_assessments(assessments: List[AssessmentTask], chosen: List[SectionOption], term: CourseTerm,
                            resolver: RuleResolver) -> List[AssessmentTask]:
    """Replace each rule-typed row whose anchor slot was chosen with one dated copy per occurrence
    (capped at a count the outline states, e.g. 'Labs (Total = 8)'); other rows pass through."""
    out: List[AssessmentTask] = []
    for a in assessments:
        if not (a.due_rule and not a.due_datetime and a.rule_anchor):
            out.append(a)
            continue
        anchor = resolver._find_anchor_section(a.rule_anchor, chosen)
        if not anchor or not term.start_date or not term.end_date:
            out.append(a)
            continue
        half = _term_half(a, term)
        if half:
            # clip a "Term 1" / "Term 2" row to its half of a full-year course (D23)
            anchor = replace(anchor, date_range=half)
        base = f"{a.rule_anchor.capitalize()} report" if re.search(r"report", a.due_rule, re.I) \
            else re.sub(r"\s*\(.*?\)", "", a.title).strip().rstrip("s") or a.title
        template = AssessmentTask(title=base, type=a.type, weight_percent=a.weight_percent, due_rule=a.due_rule,
                                  rule_anchor=a.rule_anchor, confidence=a.confidence, source_evidence=a.source_evidence)
        copies = resolver.generate_per_occurrence_assessments(template, anchor, term)
        if not copies or copies[0].due_datetime is None:
            out.append(a)
            continue
        cap = None
        m = _STATED_TOTAL.search(f"{a.title} {a.source_evidence or ''}")
        if m:
            cap = int(next(g for g in m.groups() if g))
        if cap:
            copies = copies[:cap]
        for i, c in enumerate(copies, 1):
            c.title = f"{base} {i}"
            c.date_status = "exact"
            c.needs_review = False
            c.from_rule = True      # no "start studying" event: it is due the day after the lab
            if a.weight_percent:
                c.weight_percent = round(a.weight_percent / len(copies), 2)
        out.extend(copies)
    return out


def build_calendar(extracted_data: ExtractedCourseData,
                   user_selections: UserSelections,
                   lead_time_overrides: Dict[str, Any],
                   custom_lead_time_mapping: Dict[str, Any],
                   pdf_hash: str) -> tuple:
    """Resolve rules, build the study plan and the .ics.

    Returns (filename, ics_bytes, resolved_extracted_data). Nothing is written
    to disk: the caller streams the bytes back in the same HTTP response.
    """
    resolver = RuleResolver()
    chosen = [s for s in (user_selections.selected_lecture_section, user_selections.selected_lab_section,
                          getattr(user_selections, 'selected_tutorial_section', None)) if s]
    # A relative rule ("lab report due 24 h after each lab") becomes one due event per occurrence
    # of the chosen anchor slot, for this calendar only: the stored row keeps its rule so the
    # review page and a later download with another slot start from the outline's words (D16).
    calendar_assessments = expand_rule_assessments(extracted_data.assessments, chosen, extracted_data.term, resolver)

    study_plan = _lead_time_generator(custom_lead_time_mapping).generate_study_plan(
        [a for a in calendar_assessments if not getattr(a, "from_rule", False)],
        user_lead_times=lead_time_overrides if lead_time_overrides else None
    )

    cal_gen = ICalendarGenerator(timezone_str=extracted_data.term.timezone)
    calendar = cal_gen.generate_calendar(
        term=extracted_data.term,
        lecture_section=user_selections.selected_lecture_section,
        lab_section=user_selections.selected_lab_section,
        assessments=calendar_assessments,
        study_plan=study_plan,
        tutorial_section=getattr(user_selections, 'selected_tutorial_section', None),
        course_code=extracted_data.course_code,
    )

    hash_short = (pdf_hash or 'unknown')[:8]
    course_code = (extracted_data.course_code or 'Unknown').replace(' ', '_').replace('/', '_')
    term_name = extracted_data.term.term_name.replace(' ', '').replace('/', '_')
    filename = f"{course_code}_{term_name}_{hash_short}.ics"
    filename = "".join(c for c in filename if c.isalnum() or c in "._-")
    return filename, calendar.to_ical(), extracted_data


def ics_response(filename: str, ics_bytes: bytes):
    """Stream an .ics back as a download in this same request."""
    resp = Response(ics_bytes, mimetype='text/calendar')
    resp.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    resp.headers['Cache-Control'] = 'no-store'
    return resp


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed.
    
    Args:
        filename: Name of the uploaded file
        
    Returns:
        True if file extension is allowed, False otherwise
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def serialize_section(section: Optional[SectionOption]) -> Optional[Dict[str, Any]]:
    """Serialize SectionOption to dict (None stays None)."""
    return section_to_dict(section) if section is not None else None


def deserialize_section(data: Optional[Dict[str, Any]]) -> Optional[SectionOption]:
    """Inverse of serialize_section (used to rebuild choices from the cookie)."""
    return section_from_dict(data) if data else None


def serialize_extracted_data(data: ExtractedCourseData) -> Dict[str, Any]:
    """JSON-serializable dict of the extracted data (one shared serializer in models.py)."""
    return extracted_to_dict(data)


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
    
    # Analyze assessments (bonus / optional rows are shown but not counted)
    metrics['bonus_weight'] = 0.0
    for assessment in data.assessments:
        has_weight = assessment.weight_percent is not None
        has_date = assessment.due_datetime is not None or bool(getattr(assessment, 'dates', None))
        if getattr(assessment, 'is_bonus', False):
            if has_weight:
                metrics['bonus_weight'] += assessment.weight_percent
            continue
        
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
    # This measures the quality of extracted assessments (do they have weight + date?)
    if metrics['num_assessments'] > 0:
        assessment_completeness = (metrics['assessments_complete'] / metrics['num_assessments']) * 100
    else:
        assessment_completeness = 0.0
    
    # Weight coverage: how much of the expected 100% weight have we captured?
    # This helps identify missing assessments
    # If total_weight is 60%, we're missing 40% worth of assessments
    if metrics['total_weight'] > 0:
        # Calculate coverage (capped at 100% for display, but can exceed due to extra credit)
        weight_coverage = min(metrics['total_weight'], 100.0)
        metrics['weight_coverage_percent'] = weight_coverage
        metrics['weight_missing_percent'] = max(0.0, 100.0 - weight_coverage)
    else:
        metrics['weight_coverage_percent'] = 0.0
        metrics['weight_missing_percent'] = 100.0
    
    metrics['overall_completeness'] = (found_items / total_items) * 100 if total_items > 0 else 0.0
    metrics['assessment_completeness'] = assessment_completeness
    metrics['num_tutorial_sections'] = len(getattr(data, 'tutorial_sections', []) or [])
    t = metrics['total_weight']
    metrics['total_class'] = 'over' if t > 102 else 'high' if t >= 95 else 'medium' if t >= 70 else 'low'
    metrics['assessments_undated'] = sum(1 for a in data.assessments
                                         if not a.due_datetime and not getattr(a, 'dates', None) and not getattr(a, 'is_bonus', False))
    
    return metrics


def deserialize_extracted_data(data: Dict[str, Any]) -> ExtractedCourseData:
    """Inverse of serialize_extracted_data."""
    from .models import extracted_from_dict
    return extracted_from_dict(data)


# ---------------------------------------------------------------------------
# PostHog reverse proxy: the browser snippet posts to /ingest/* on this host so
# ad blockers do not drop the events. Static SDK files come from the assets
# host, everything else from the ingest host.
# ---------------------------------------------------------------------------
POSTHOG_INGEST_HOST = os.getenv('POSTHOG_HOST', 'https://us.i.posthog.com').rstrip('/')
POSTHOG_ASSETS_HOST = POSTHOG_INGEST_HOST.replace('.i.posthog.com', '-assets.i.posthog.com')
# Only these request headers are forwarded to PostHog. Everything else, and in
# particular the visitor's signed Flask session cookie and any Authorization
# header, stays inside the app (a whitelist, never a blacklist).
_FORWARDED_REQUEST_HEADERS = ('Content-Type', 'User-Agent', 'Accept', 'Origin', 'Referer')
# Response headers passed back for the static SDK bundles so browsers can cache
# them instead of refetching ~300 KB through this function on every page view.
_STATIC_RESPONSE_HEADERS = ('Cache-Control', 'ETag', 'Last-Modified')


@app.route('/ingest/<path:subpath>', methods=['GET', 'POST', 'OPTIONS'])
def ingest_proxy(subpath: str):
    """Forward a PostHog request and return its response unchanged."""
    if not app.config['POSTHOG_API_KEY']:
        return jsonify(error='analytics disabled'), 404
    base = POSTHOG_ASSETS_HOST if subpath.startswith('static/') else POSTHOG_INGEST_HOST
    url = f"{base}/{subpath}"
    if request.query_string:
        url += '?' + request.query_string.decode('utf-8', 'ignore')
    headers = {name: request.headers[name] for name in _FORWARDED_REQUEST_HEADERS
               if request.headers.get(name)}
    # Keep the visitor's IP for PostHog's geolocation (country/city only)
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
    if client_ip:
        headers['X-Forwarded-For'] = client_ip
    body = request.get_data() if request.method == 'POST' else None
    req = urllib.request.Request(url, data=body, headers=headers, method=request.method)
    try:
        with urllib.request.urlopen(req, timeout=10) as upstream:
            payload = upstream.read()
            resp = Response(payload, status=upstream.status)
            ctype = upstream.headers.get('Content-Type')
            if ctype:
                resp.headers['Content-Type'] = ctype
            if subpath.startswith('static/'):
                for name in _STATIC_RESPONSE_HEADERS:
                    value = upstream.headers.get(name)
                    if value:
                        resp.headers[name] = value
            return resp
    except urllib.error.HTTPError as e:
        return Response(e.read(), status=e.code)
    except Exception as e:  # network trouble must never break the page
        return jsonify(error=str(e)), 502


@app.context_processor
def _inject_limits():
    return {'max_mb': MAX_FILE_SIZE_MB}


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
    # Refuse an oversize body before the form is parsed (Vercel itself answers 413 above
    # 4.5 MB, and the browser checks the size before sending; this is the last line)
    if request.content_length and request.content_length > MAX_FILE_SIZE:
        flash(f'That file is larger than {MAX_FILE_SIZE_MB} MB, which is the most this free hosting can accept. '
              'Print the outline to a smaller PDF (or remove images) and try again.', 'error')
        return redirect(url_for('index'))

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
    
    filepath: Optional[Path] = None
    try:
        # Save the upload under a per-request unique name: two visitors uploading
        # "outline.pdf" at the same moment on one warm instance must not share a
        # path, and the file is removed in the finally block below so /tmp
        # (512 MB on Vercel) never fills up.
        filename = secure_filename(file.filename)
        filepath = upload_dir() / f"{uuid.uuid4().hex}-{filename}"
        file.save(str(filepath))
        
        # Compute PDF hash
        pdf_hash = compute_pdf_hash(filepath)
        
        # Initialize session
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        analytics.capture(session['session_id'], 'pdf_uploaded', {
            'size_bytes': filepath.stat().st_size,
            'force_refresh': force_refresh,
        })
        
        # Check cache (unless force refresh)
        extracted_data = None
        if force_refresh:
            discard_visitor_copy(pdf_hash, session.get('session_id'))
        else:
            extracted_data = get_cache().lookup_extraction(pdf_hash)
            if extracted_data:
                flash('This outline was parsed before; showing the saved result. Use "re-read the PDF" to parse it again.', 'info')
                analytics.capture(session['session_id'], 'pdf_parsed', {
                    'cached': True,
                    'assessments': len(extracted_data.assessments),
                    'course_code': extracted_data.course_code,
                })
        
        # Extract from PDF if not cached or force refresh
        if extracted_data is None:
            started = datetime.utcnow()
            try:
                extractor = PDFExtractor(filepath, original_filename=file.filename)
                extracted_data = extractor.extract_all()
            except PasswordProtected:
                flash('This PDF is password-protected, so its text cannot be read. Remove the password '
                      '(print it to a new PDF) and upload it again, or enter the course by hand in manual mode.', 'error')
                return redirect(url_for('index'))
            except NoTextLayer:
                flash('This PDF has no text layer (a scanned image or an empty file), so nothing can be read from it. '
                      'Download the outline from OWL as a real PDF, or enter the course by hand in manual mode.', 'error')
                return redirect(url_for('index'))
            except Exception as e:
                reason = str(e).strip() or type(e).__name__
                flash(f'This PDF could not be read ({reason}). Try another copy of the outline, '
                      'or enter the course by hand in manual mode.', 'error')
                return redirect(url_for('index'))

            if not extracted_data.assessments and not extracted_data.all_sections() and not extracted_data.course_code:
                flash('No course information was found in this PDF (no course code, no timetable and no '
                      'assessment table). Check that it is a Western course outline, or enter the course by hand in manual mode.', 'error')
                return redirect(url_for('index'))

            # A relative rule ("Day of lab at 11:59pm") is NOT resolved here: the stored row keeps its
            # rule and no date, and the calendar expands it to one event per occurrence of the slot
            # the visitor picks at download time (D16, D23). Resolving it here dated the first lab
            # only, as a placeholder that was then shown and exported as the due date.

            # Cache extraction results (shared, parser output only)
            get_cache().store_extraction(pdf_hash, extracted_data)
            flash('Outline read. Check every date below before you download.', 'success')
            analytics.capture(session['session_id'], 'pdf_parsed', {
                'cached': False,
                'seconds': round((datetime.utcnow() - started).total_seconds(), 1),
                'assessments': len(extracted_data.assessments),
                'undated': sum(1 for a in extracted_data.assessments if not a.due_datetime and not a.dates),
                'lecture_sections': len(extracted_data.lecture_sections),
                'lab_sections': len(extracted_data.lab_sections),
                'tutorial_sections': len(extracted_data.tutorial_sections),
                'term_source': extracted_data.term.source,
                'course_code': extracted_data.course_code,
            })
        
        # Store in session for review page
        session['pdf_hash'] = pdf_hash
        session['pdf_filename'] = filename
        
        # Check for cached user choices
        user_choices = get_cache().lookup_user_choices(pdf_hash, session.get('session_id'))
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
        flash(f'That file is larger than {MAX_FILE_SIZE_MB} MB, which is the most this free hosting can accept. '
              'Print the outline to a smaller PDF (or remove images) and try again.', 'error')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'The file could not be processed ({str(e).strip() or type(e).__name__}). Try again or use manual mode.', 'error')
        return redirect(url_for('index'))
    finally:
        if filepath is not None:
            try:
                filepath.unlink(missing_ok=True)
            except OSError:
                pass


@app.route('/review', methods=['GET', 'POST'])
def review():
    """Review and edit extracted data.
    
    GET: Display review page with extracted data
    POST: Process user selections and generate calendar
    
    Returns:
        Rendered review.html template or redirect to download
    """
    # Check if we have extracted data (the cookie carries only the PDF hash;
    # the data itself is read from the database on every request)
    if 'pdf_hash' not in session:
        flash('No data to review. Please upload a PDF first.', 'error')
        return redirect(url_for('index'))

    pdf_hash = session.get('pdf_hash')
    extracted_data = load_extracted()
    if extracted_data is None:
        flash('Your extracted data has expired. Please upload the PDF again.', 'error')
        return redirect(url_for('index'))
    extracted_data_dict = serialize_extracted_data(extracted_data)

    if request.method == 'POST':
        # Process form submission
        # Handle manual sections first (add them to extracted_data)
        # Note: Manual sections are only used when automatic extraction found no sections
        # The template only shows the "Add Manually" button when lab_sections/lecture_sections is empty
        manual_lecture_sections = request.form.get('manual_lecture_sections')
        manual_lab_sections = request.form.get('manual_lab_sections')
        
        if manual_lecture_sections:
            try:
                from .models import SectionOption
                from datetime import time as dt_time
                
                sections_data = json.loads(manual_lecture_sections)
                for section_data in sections_data:
                    # Parse time strings to time objects
                    start_hour, start_min = map(int, section_data['start_time'].split(':'))
                    end_hour, end_min = map(int, section_data['end_time'].split(':'))
                    
                    section = SectionOption(
                        section_type="Lecture",
                        section_id="",  # Manual sections don't have IDs
                        days_of_week=section_data['days'],
                        start_time=dt_time(start_hour, start_min),
                        end_time=dt_time(end_hour, end_min),
                        location=section_data.get('location') or None
                    )
                    extracted_data.lecture_sections.append(section)
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                flash(f'Error parsing manual lecture sections: {str(e)}', 'warning')
        
        if manual_lab_sections:
            try:
                from .models import SectionOption
                from datetime import time as dt_time
                
                sections_data = json.loads(manual_lab_sections)
                for section_data in sections_data:
                    # Parse time strings to time objects
                    start_hour, start_min = map(int, section_data['start_time'].split(':'))
                    end_hour, end_min = map(int, section_data['end_time'].split(':'))
                    
                    section = SectionOption(
                        section_type="Lab",
                        section_id="",  # Manual sections don't have IDs
                        days_of_week=section_data['days'],
                        start_time=dt_time(start_hour, start_min),
                        end_time=dt_time(end_hour, end_min),
                        location=section_data.get('location') or None
                    )
                    extracted_data.lab_sections.append(section)
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                flash(f'Error parsing manual lab sections: {str(e)}', 'warning')
        
        # Get selected sections
        lecture_idx = request.form.get('lecture_section')
        lab_idx = request.form.get('lab_section')
        tutorial_idx = request.form.get('tutorial_section')
        
        user_selections = UserSelections()
        user_selections.selected_tutorial_section = None
        if tutorial_idx and tutorial_idx != 'none':
            try:
                idx = int(tutorial_idx)
                if 0 <= idx < len(extracted_data.tutorial_sections):
                    user_selections.selected_tutorial_section = extracted_data.tutorial_sections[idx]
            except ValueError:
                pass
        
        # Set selected lecture section. One option and nothing chosen (a browser that ignored
        # `required`): that only option is the course's lecture, never "no lecture" (D22).
        if not lecture_idx and len(extracted_data.lecture_sections) == 1:
            lecture_idx = '0'
        if lecture_idx and lecture_idx != 'none':
            try:
                # Check if it's a manual section (starts with "manual_")
                if lecture_idx.startswith('manual_'):
                    # Extract index from "manual_X"
                    manual_idx = int(lecture_idx.split('_')[1])
                    # Manual sections are added at the end, so we need to find them
                    # Count how many manual sections we added
                    manual_count = len(json.loads(manual_lecture_sections)) if manual_lecture_sections else 0
                    # The manual sections are the last N sections in the list
                    # Find the section at the correct position
                    original_count = len(extracted_data.lecture_sections) - manual_count
                    section_idx = original_count + manual_idx
                    if 0 <= section_idx < len(extracted_data.lecture_sections):
                        user_selections.selected_lecture_section = extracted_data.lecture_sections[section_idx]
                else:
                    idx = int(lecture_idx)
                    if 0 <= idx < len(extracted_data.lecture_sections):
                        user_selections.selected_lecture_section = extracted_data.lecture_sections[idx]
            except (ValueError, IndexError, AttributeError):
                pass
        
        # Set selected lab section
        if lab_idx and lab_idx != 'none':
            try:
                # Check if it's a manual section (starts with "manual_")
                if lab_idx.startswith('manual_'):
                    # Extract index from "manual_X"
                    manual_idx = int(lab_idx.split('_')[1])
                    # Manual sections are added at the end, so we need to find them
                    # Count how many manual sections we added
                    manual_count = len(json.loads(manual_lab_sections)) if manual_lab_sections else 0
                    # The manual sections are the last N sections in the list
                    # Find the section at the correct position
                    original_count = len(extracted_data.lab_sections) - manual_count
                    section_idx = original_count + manual_idx
                    if 0 <= section_idx < len(extracted_data.lab_sections):
                        user_selections.selected_lab_section = extracted_data.lab_sections[section_idx]
                else:
                    idx = int(lab_idx)
                    if 0 <= idx < len(extracted_data.lab_sections):
                        user_selections.selected_lab_section = extracted_data.lab_sections[idx]
            except (ValueError, IndexError, AttributeError):
                pass
        
        # Get lead time overrides from session
        user_choices_dict = session.get('user_choices', {})
        lead_time_overrides = user_choices_dict.get('lead_time_overrides', {})
        custom_lead_time_mapping = user_choices_dict.get('custom_lead_time_mapping', {})
        
        # Store user choices in session (keep both lead-time customisations,
        # /download rebuilds the calendar from exactly this dict)
        session['user_choices'] = {
            'selected_lecture_section': serialize_section(user_selections.selected_lecture_section),
            'selected_lab_section': serialize_section(user_selections.selected_lab_section),
            'selected_tutorial_section': serialize_section(user_selections.selected_tutorial_section),
            'lead_time_overrides': lead_time_overrides,
            'custom_lead_time_mapping': custom_lead_time_mapping,
        }
        
        # Generate calendar and stream it back in this same request
        try:
            filename, ics_bytes, extracted_data = build_calendar(
                extracted_data, user_selections, lead_time_overrides,
                custom_lead_time_mapping, pdf_hash
            )
            # Persist resolved assessments and the user's choices for /download
            save_extracted(extracted_data)
            get_cache().store_user_choices(pdf_hash, user_selections, session.get('session_id'))
            analytics.capture(session.get('session_id'), 'ics_downloaded', {
                'events': ics_bytes.count(b'BEGIN:VEVENT'),
                'assessments': len(extracted_data.assessments),
            })
            return ics_response(filename, ics_bytes)

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error generating calendar: {error_details}")
            flash(f'Error generating calendar: {str(e)}. Please try again or contact support if the issue persists.', 'error')
            # Continue to show review page with error
    
    # Get study plan mapping for display
    study_plan_gen = StudyPlanGenerator()
    default_lead_time_mapping = study_plan_gen.get_default_mapping_display()
    
    # Get user lead time overrides and custom mappings from session
    user_choices_dict = session.get('user_choices', {})
    lead_time_overrides = user_choices_dict.get('lead_time_overrides', {})
    custom_lead_time_mapping = user_choices_dict.get('custom_lead_time_mapping', {})
    
    # Merge custom mappings with default (custom takes precedence)
    lead_time_mapping = default_lead_time_mapping.copy()
    for range_key, days in custom_lead_time_mapping.items():
        if range_key in lead_time_mapping:
            lead_time_mapping[range_key] = days
    
    # Calculate completeness metrics (do this for both GET and POST)
    completeness = calculate_completeness(extracted_data)
    
    # Prepare assessments list for template
    # Calculate current lead time for each assessment
    study_plan_gen = StudyPlanGenerator()
    assessments_list = []
    for a in extracted_data.assessments:
        # Calculate current lead time (using override if available, otherwise default)
        current_lead_time = lead_time_overrides.get(a.title)
        if current_lead_time is None:
            # Use default calculation
            current_lead_time = study_plan_gen._get_lead_time(a, lead_time_overrides)
        
        assessments_list.append({
            'title': a.title,
            'type': a.type,
            'weight_percent': a.weight_percent,
            'due_datetime': a.due_datetime,  # Keep as datetime object for template
            'due_rule': a.due_rule,
            'confidence': a.confidence,
            'source_evidence': a.source_evidence,
            'needs_review': a.needs_review,
            'lead_time_days': current_lead_time,  # Add lead time for display
            'date_status': a.date_status,
            'date_note': rule_hint(a, extracted_data.all_sections()) or a.date_note,
            'dates': a.dates,
            'is_bonus': a.is_bonus,
            'end_datetime': a.end_datetime,
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
            'timezone': extracted_data.term.timezone,
            'exam_periods': extracted_data.term.exam_periods,
        },
        'completeness': completeness,
        'lecture_sections': [
            {
                'section_type': s.section_type,
                'section_id': s.section_id,
                'days_of_week': s.days_of_week,
                'start_time': s.start_time,
                'end_time': s.end_time,
                'location': s.location,
                'note': s.note,
                'label': s.describe(),
                'meetings': s.meetings,
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
                'location': s.location,
                'note': s.note,
                'label': s.describe(),
                'meetings': s.meetings,
            }
            for s in extracted_data.lab_sections
        ],
        'tutorial_sections': [
            {
                'section_type': s.section_type,
                'section_id': s.section_id,
                'days_of_week': s.days_of_week,
                'start_time': s.start_time,
                'end_time': s.end_time,
                'location': s.location,
                'note': s.note,
                'label': s.describe(),
                'meetings': s.meetings,
            }
            for s in extracted_data.tutorial_sections
        ],
        'assessments': assessments_list,
        'lead_time_mapping': lead_time_mapping,
        'user_choices': session.get('user_choices', {}),
        'notes': list(extracted_data.notes or []),
        'term_source': extracted_data.term.source,
        'pdf_filename': session.get('pdf_filename', ''),
        'is_manual': str(pdf_hash).startswith('manual-'),
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
        form = request.form
        term_name = (form.get('term_name') or '').strip() or 'Unknown'
        try:
            start = deserialize_date(form['term_start']) if form.get('term_start') else None
            end = deserialize_date(form['term_end']) if form.get('term_end') else None
        except ValueError:
            flash('Term dates must be real dates (YYYY-MM-DD).', 'error')
            return render_template('manual.html', form=form, max_mb=MAX_FILE_SIZE_MB), 400
        term = CourseTerm(term_name=term_name, start_date=start, end_date=end, source='manual')
        assessments = []
        titles = form.getlist('assessment_title[]')
        types = form.getlist('assessment_type[]')
        dues = form.getlist('assessment_due[]')
        weights = form.getlist('assessment_weight[]')
        for i, title in enumerate(titles):
            title = title.strip()
            if not title:
                continue
            due = None
            raw_due = dues[i] if i < len(dues) else ''
            if raw_due:
                try:
                    due = deserialize_datetime(raw_due.replace('T', ' ') + ('' if ':' in raw_due else ' 23:59'))
                except ValueError:
                    due = None
            weight = None
            raw_w = weights[i] if i < len(weights) else ''
            if raw_w:
                try:
                    weight = float(raw_w)
                except ValueError:
                    weight = None
            assessments.append(AssessmentTask(
                title=title, type=(types[i] if i < len(types) else 'other') or 'other',
                weight_percent=weight, due_datetime=due, confidence=1.0, source_evidence='Entered by hand',
                needs_review=due is None, date_status='exact' if due else 'missing',
                date_note='' if due else 'No date entered yet',
            ))
        from .outline.schedule import parse_days
        slots = {'lecture': [], 'lab': [], 'tutorial': []}
        for kind in slots:
            days = parse_days(form.get(f'{kind}_days') or '')
            st, en = form.get(f'{kind}_start') or '', form.get(f'{kind}_end') or ''
            if days and st and en:
                try:
                    slots[kind].append(SectionOption(
                        section_type=kind.capitalize(), section_id='', days_of_week=days,
                        start_time=deserialize_time(st if st.count(':') == 2 else st + ':00'),
                        end_time=deserialize_time(en if en.count(':') == 2 else en + ':00'),
                        location=(form.get(f'{kind}_location') or '').strip() or None))
                except ValueError:
                    pass
        data = ExtractedCourseData(term=term, lecture_sections=slots['lecture'], lab_sections=slots['lab'],
                                   tutorial_sections=slots['tutorial'], assessments=assessments,
                                   course_code=(form.get('course_code') or '').strip() or None,
                                   course_name=(form.get('course_name') or '').strip() or None,
                                   notes=['Entered by hand: add lecture, lab or tutorial slots with "Add Section" if you want weekly events.'])
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        pdf_hash = f"manual-{uuid.uuid4().hex}"
        session['pdf_hash'] = pdf_hash
        session['pdf_filename'] = 'manual entry'
        session['user_choices'] = {}
        get_cache().store_extraction(visitor_key(pdf_hash, session['session_id']), data)
        analytics.capture(session['session_id'], 'manual_entry', {'assessments': len(assessments)})
        flash('Course entered. Review it below, then download the calendar.', 'success')
        return redirect(url_for('review'))
    
    return render_template('manual.html', form=None, max_mb=MAX_FILE_SIZE_MB)


@app.route('/api/update-field', methods=['POST'])
def update_field():
    """API endpoint to update a field in the extracted data.
    
    This allows users to manually edit missing or incorrect information
    directly from the review page.
    
    Expected JSON payload:
    {
        "field_type": "course_code" | "course_name" | "term_start" | "term_end" | "assessment",
        "field_path": "course_code" or "assessments.0.due_datetime" etc,
        "value": new value,
        "assessment_index": optional, for assessment updates
    }
    
    Returns:
        JSON response with success status
    """
    if 'pdf_hash' not in session:
        return jsonify({'success': False, 'error': 'No data to update'}), 400
    
    try:
        data = request.get_json()
        field_type = data.get('field_type')
        value = data.get('value')
        assessment_index = data.get('assessment_index')
        
        # Get current extracted data
        extracted_data = load_extracted()
        if extracted_data is None:
            return jsonify({'success': False, 'error': 'No data to update'}), 400
        
        # Update based on field type
        if field_type == 'course_code':
            extracted_data.course_code = value if value else None
            
        elif field_type == 'course_name':
            extracted_data.course_name = value if value else None

        elif field_type == 'term_name':
            extracted_data.term.term_name = (value or '').strip() or 'Unknown'
            
        elif field_type == 'term_start':
            if value:
                try:
                    # Parse date from datetime-local format (YYYY-MM-DDTHH:MM) or just YYYY-MM-DD
                    if 'T' in value:
                        date_str = value.split('T')[0]
                    elif ' ' in value:
                        date_str = value.split(' ')[0]
                    else:
                        date_str = value
                    extracted_data.term.start_date = deserialize_date(date_str)
                except (ValueError, AttributeError) as e:
                    return jsonify({'success': False, 'error': f'Invalid date format: {str(e)}. Use YYYY-MM-DD'}), 400
            else:
                extracted_data.term.start_date = None
            
        elif field_type == 'term_end':
            if value:
                try:
                    # Parse date from datetime-local format (YYYY-MM-DDTHH:MM) or just YYYY-MM-DD
                    if 'T' in value:
                        date_str = value.split('T')[0]
                    elif ' ' in value:
                        date_str = value.split(' ')[0]
                    else:
                        date_str = value
                    extracted_data.term.end_date = deserialize_date(date_str)
                except (ValueError, AttributeError) as e:
                    return jsonify({'success': False, 'error': f'Invalid date format: {str(e)}. Use YYYY-MM-DD'}), 400
            else:
                extracted_data.term.end_date = None
            
        elif field_type == 'assessment_due_date':
            if assessment_index is not None:
                try:
                    idx = int(assessment_index)
                    if 0 <= idx < len(extracted_data.assessments):
                        if value:
                            # Parse datetime from datetime-local format (YYYY-MM-DDTHH:MM)
                            try:
                                if 'T' in value:
                                    dt_str = value.replace('T', ' ')
                                else:
                                    dt_str = value
                                # Ensure we have time component
                                if len(dt_str.split(' ')) == 1:
                                    dt_str += ' 23:59:59'
                                extracted_data.assessments[idx].due_datetime = deserialize_datetime(dt_str)
                                # Clear rule if setting absolute date
                                extracted_data.assessments[idx].due_rule = None
                                extracted_data.assessments[idx].date_status = 'exact'
                                extracted_data.assessments[idx].date_note = 'Date entered by you'
                                extracted_data.assessments[idx].dates = []
                                extracted_data.assessments[idx].needs_review = False
                            except (ValueError, AttributeError) as e:
                                return jsonify({'success': False, 'error': f'Invalid datetime format: {str(e)}'}), 400
                        else:
                            extracted_data.assessments[idx].due_datetime = None
                            extracted_data.assessments[idx].dates = []
                            extracted_data.assessments[idx].date_status = 'missing'
                            extracted_data.assessments[idx].date_note = 'Date cleared by you'
                            extracted_data.assessments[idx].needs_review = True
                except (ValueError, IndexError) as e:
                    return jsonify({'success': False, 'error': f'Invalid assessment index: {str(e)}'}), 400
            else:
                return jsonify({'success': False, 'error': 'assessment_index required for assessment updates'}), 400
                
        elif field_type == 'assessment_title':
            if assessment_index is not None:
                try:
                    idx = int(assessment_index)
                    if 0 <= idx < len(extracted_data.assessments):
                        if value and value.strip():
                            extracted_data.assessments[idx].title = value.strip()
                        else:
                            return jsonify({'success': False, 'error': 'Assessment title cannot be empty'}), 400
                except (ValueError, IndexError):
                    return jsonify({'success': False, 'error': 'Invalid assessment index'}), 400
            else:
                return jsonify({'success': False, 'error': 'assessment_index required for assessment updates'}), 400
                
        elif field_type == 'assessment_weight':
            if assessment_index is not None:
                try:
                    idx = int(assessment_index)
                    if 0 <= idx < len(extracted_data.assessments):
                        if value:
                            try:
                                weight = float(value)
                                extracted_data.assessments[idx].weight_percent = weight
                            except ValueError:
                                return jsonify({'success': False, 'error': 'Invalid weight value'}), 400
                        else:
                            extracted_data.assessments[idx].weight_percent = None
                except (ValueError, IndexError):
                    return jsonify({'success': False, 'error': 'Invalid assessment index'}), 400
            else:
                return jsonify({'success': False, 'error': 'assessment_index required for assessment updates'}), 400
                
        elif field_type == 'assessment_lead_time':
            if assessment_index is not None:
                try:
                    idx = int(assessment_index)
                    if 0 <= idx < len(extracted_data.assessments):
                        assessment = extracted_data.assessments[idx]
                        
                        # Get or create lead_time_overrides in user_choices
                        user_choices_dict = session.get('user_choices', {})
                        if 'lead_time_overrides' not in user_choices_dict:
                            user_choices_dict['lead_time_overrides'] = {}
                        
                        if value:
                            try:
                                lead_time = int(value)
                                if lead_time < 0:
                                    return jsonify({'success': False, 'error': 'Lead time must be non-negative'}), 400
                                # Store override
                                user_choices_dict['lead_time_overrides'][assessment.title] = lead_time
                            except ValueError:
                                return jsonify({'success': False, 'error': 'Invalid lead time value (must be an integer)'}), 400
                        else:
                            # Remove override (use default)
                            if assessment.title in user_choices_dict['lead_time_overrides']:
                                del user_choices_dict['lead_time_overrides'][assessment.title]
                        
                        # Update session
                        session['user_choices'] = user_choices_dict
                        
                        # Also update cache
                        pdf_hash = session.get('pdf_hash')
                        if pdf_hash:
                            # Get existing user selections or create new
                            user_selections = get_cache().lookup_user_choices(pdf_hash, session.get('session_id'))
                            if user_selections is None:
                                from .models import UserSelections
                                user_selections = UserSelections()
                            
                            # Update lead time overrides
                            if not hasattr(user_selections, 'lead_time_overrides') or user_selections.lead_time_overrides is None:
                                user_selections.lead_time_overrides = {}
                            else:
                                # Convert from dict if needed
                                if isinstance(user_selections.lead_time_overrides, dict):
                                    pass  # Already a dict
                                else:
                                    user_selections.lead_time_overrides = {}
                            
                            if value:
                                user_selections.lead_time_overrides[assessment.title] = int(value)
                            elif assessment.title in user_selections.lead_time_overrides:
                                del user_selections.lead_time_overrides[assessment.title]
                            
                            get_cache().store_user_choices(pdf_hash, user_selections, session.get('session_id'))
                except (ValueError, IndexError) as e:
                    return jsonify({'success': False, 'error': f'Invalid assessment index: {str(e)}'}), 400
            else:
                return jsonify({'success': False, 'error': 'assessment_index required for assessment updates'}), 400
        
        elif field_type == 'lead_time_mapping':
            # Get weight range from request
            weight_range = request.json.get('weight_range')
            if not weight_range:
                return jsonify({'success': False, 'error': 'weight_range required for lead_time_mapping updates'}), 400
            
            # Get or create custom_lead_time_mapping in user_choices
            user_choices_dict = session.get('user_choices', {})
            if 'custom_lead_time_mapping' not in user_choices_dict:
                user_choices_dict['custom_lead_time_mapping'] = {}
            
            if value:
                try:
                    lead_time = int(value)
                    if lead_time < 0:
                        return jsonify({'success': False, 'error': 'Lead time must be non-negative'}), 400
                    # Store custom mapping
                    user_choices_dict['custom_lead_time_mapping'][weight_range] = lead_time
                except ValueError:
                    return jsonify({'success': False, 'error': 'Invalid lead time value (must be an integer)'}), 400
            else:
                # Remove custom mapping (use default)
                if weight_range in user_choices_dict['custom_lead_time_mapping']:
                    del user_choices_dict['custom_lead_time_mapping'][weight_range]
            
            # Update session
            session['user_choices'] = user_choices_dict
            
            # Also update cache
            pdf_hash = session.get('pdf_hash')
            if pdf_hash:
                # Get existing user selections or create new
                user_selections = get_cache().lookup_user_choices(pdf_hash, session.get('session_id'))
                if user_selections is None:
                    from .models import UserSelections
                    user_selections = UserSelections()
                
                # Update custom lead time mapping
                if not hasattr(user_selections, 'custom_lead_time_mapping') or user_selections.custom_lead_time_mapping is None:
                    user_selections.custom_lead_time_mapping = {}
                else:
                    # Convert from dict if needed
                    if isinstance(user_selections.custom_lead_time_mapping, dict):
                        pass  # Already a dict
                    else:
                        user_selections.custom_lead_time_mapping = {}
                
                if value:
                    user_selections.custom_lead_time_mapping[weight_range] = int(value)
                elif weight_range in user_selections.custom_lead_time_mapping:
                    del user_selections.custom_lead_time_mapping[weight_range]
                
                get_cache().store_user_choices(pdf_hash, user_selections, session.get('session_id'))
        
        else:
            return jsonify({'success': False, 'error': f'Unknown field_type: {field_type}'}), 400
        
        # Persist the modified data (one upsert; save_extracted writes the cache)
        save_extracted(extracted_data)

        # The tiles and the row badges re-render from this without a reload (D19)
        c = calculate_completeness(extracted_data)
        row = None
        if assessment_index is not None and field_type.startswith('assessment_'):
            try:
                a = extracted_data.assessments[int(assessment_index)]
                row = {
                    'has_date': bool(a.due_datetime or a.dates or a.due_rule),
                    'due_display': (a.due_datetime.strftime('%b %d, %Y') + ('' if (a.due_datetime.hour, a.due_datetime.minute) == (23, 59)
                                    else ' ' + a.due_datetime.strftime('%I:%M %p').lstrip('0'))) if a.due_datetime else None,
                    'weight': a.weight_percent,
                    'date_note': a.date_note,
                    'needs_review': bool(a.needs_review),
                    'is_bonus': bool(getattr(a, 'is_bonus', False)),
                }
            except (ValueError, IndexError):
                row = None
        return jsonify({'success': True, 'message': 'Field updated successfully', 'row': row, 'completeness': {
            'num_assessments': c['num_assessments'], 'total_weight': round(c['total_weight']), 'total_class': c['total_class'],
            'bonus_weight': round(c.get('bonus_weight', 0.0), 1), 'num_lecture_sections': c['num_lecture_sections'],
            'num_lab_sections': c['num_lab_sections'], 'num_tutorial_sections': c['num_tutorial_sections'],
            'assessments_undated': c['assessments_undated']}})
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error updating field: {error_details}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/add-assessment', methods=['POST'])
def add_assessment():
    """API endpoint to add a new assessment.
    
    Expected JSON payload:
    {
        "title": "Assessment title",
        "type": "assignment" | "quiz" | "midterm" | "final" | etc,
        "weight_percent": 15.5 (optional),
        "due_datetime": "2025-12-15T23:59" (optional),
        "due_rule": "24 hours after lab" (optional),
        "rule_anchor": "lab" | "tutorial" | "lecture" (optional),
        "confidence": 0.8 (optional, default 0.8),
        "source_evidence": "Manual entry" (optional),
        "needs_review": true/false (optional)
    }
    
    Returns:
        JSON response with success status and updated completeness
    """
    if 'pdf_hash' not in session:
        return jsonify({'success': False, 'error': 'No data to update'}), 400
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'success': False, 'error': 'Title is required'}), 400
        if not data.get('type'):
            return jsonify({'success': False, 'error': 'Type is required'}), 400
        
        # Get current extracted data
        extracted_data = load_extracted()
        if extracted_data is None:
            return jsonify({'success': False, 'error': 'No data to update'}), 400
        
        # Parse due_datetime if provided
        due_datetime = None
        if data.get('due_datetime'):
            try:
                if 'T' in data['due_datetime']:
                    dt_str = data['due_datetime'].replace('T', ' ')
                else:
                    dt_str = data['due_datetime']
                if len(dt_str.split(' ')) == 1:
                    dt_str += ' 23:59:59'
                due_datetime = deserialize_datetime(dt_str)
            except (ValueError, AttributeError) as e:
                return jsonify({'success': False, 'error': f'Invalid datetime format: {str(e)}'}), 400
        
        # Parse weight if provided
        weight_percent = None
        if data.get('weight_percent'):
            try:
                weight_percent = float(data['weight_percent'])
                if weight_percent < 0 or weight_percent > 100:
                    return jsonify({'success': False, 'error': 'Weight must be between 0 and 100'}), 400
            except (ValueError, TypeError):
                return jsonify({'success': False, 'error': 'Invalid weight value'}), 400
        
        # Parse confidence
        confidence = float(data.get('confidence', 0.8))
        if confidence < 0 or confidence > 1:
            confidence = 0.8
        
        # Create new assessment
        new_assessment = AssessmentTask(
            title=data['title'],
            type=data['type'],
            weight_percent=weight_percent,
            due_datetime=due_datetime,
            due_rule=data.get('due_rule'),
            rule_anchor=data.get('rule_anchor'),
            confidence=confidence,
            source_evidence=data.get('source_evidence', 'Manual entry'),
            needs_review=bool(data.get('needs_review', False)) or due_datetime is None,
            date_status='exact' if due_datetime else ('rule' if data.get('due_rule') else 'missing'),
            date_note='Entered by you' if due_datetime else ('Relative rule entered by you' if data.get('due_rule') else 'No date entered yet'),
        )
        
        # Add to assessments list
        extracted_data.assessments.append(new_assessment)
        
        # Store updated data back in session
        save_extracted(extracted_data)
        
        # Recalculate completeness
        completeness = calculate_completeness(extracted_data)
        
        return jsonify({
            'success': True,
            'completeness': completeness,
            'message': 'Assessment added successfully'
        })
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error adding assessment: {error_details}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/remove-assessment', methods=['POST'])
def remove_assessment():
    """API endpoint to remove an assessment.
    
    Expected JSON payload:
    {
        "assessment_index": 0 (index of assessment to remove)
    }
    
    Returns:
        JSON response with success status and updated completeness
    """
    if 'pdf_hash' not in session:
        return jsonify({'success': False, 'error': 'No data to update'}), 400
    
    try:
        data = request.get_json()
        assessment_index = data.get('assessment_index')
        
        if assessment_index is None:
            return jsonify({'success': False, 'error': 'assessment_index is required'}), 400
        
        # Get current extracted data
        extracted_data = load_extracted()
        if extracted_data is None:
            return jsonify({'success': False, 'error': 'No data to update'}), 400
        
        # Validate index
        try:
            idx = int(assessment_index)
            if idx < 0 or idx >= len(extracted_data.assessments):
                return jsonify({'success': False, 'error': 'Invalid assessment index'}), 400
            
            # Remove assessment
            removed_assessment = extracted_data.assessments.pop(idx)
            
        except (ValueError, IndexError) as e:
            return jsonify({'success': False, 'error': f'Invalid assessment index: {str(e)}'}), 400
        
        # Store updated data back in session
        save_extracted(extracted_data)
        
        # Recalculate completeness
        completeness = calculate_completeness(extracted_data)
        
        return jsonify({
            'success': True,
            'completeness': completeness,
            'message': f'Assessment "{removed_assessment.title}" removed successfully'
        })
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error removing assessment: {error_details}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/download/<filename>')
def download(filename: str):
    """Re-generate and stream the .ics for the current PDF.

    Nothing is stored on the server between requests: the calendar is rebuilt
    from the database (extracted data) and the cookie (user choices).
    """
    if 'pdf_hash' not in session:
        flash('Calendar file not found. Please generate a calendar first.', 'error')
        return redirect(url_for('index'))
    extracted_data = load_extracted()
    if extracted_data is None:
        flash('Your extracted data has expired. Please upload the PDF again.', 'error')
        return redirect(url_for('index'))

    user_choices_dict = session.get('user_choices', {})
    lec = user_choices_dict.get('selected_lecture_section')
    lab = user_choices_dict.get('selected_lab_section')
    tut = user_choices_dict.get('selected_tutorial_section')
    if 'selected_lecture_section' not in user_choices_dict:
        flash('Please generate the calendar from the review page first.', 'error')
        return redirect(url_for('review'))
    user_selections = UserSelections()
    user_selections.selected_tutorial_section = deserialize_section(tut) if tut else None
    if lec:
        user_selections.selected_lecture_section = deserialize_section(lec)
    if lab:
        user_selections.selected_lab_section = deserialize_section(lab)
    try:
        built_name, ics_bytes, _ = build_calendar(
            extracted_data, user_selections,
            user_choices_dict.get('lead_time_overrides', {}),
            user_choices_dict.get('custom_lead_time_mapping', {}),
            session.get('pdf_hash')
        )
        return ics_response(secure_filename(filename) or built_name, ics_bytes)
    except Exception as e:
        flash(f'Error generating calendar: {str(e)}. Please try again.', 'error')
        return redirect(url_for('review'))


@app.route('/api/health')
def health():
    """Liveness + database check used by the portfolio hub and UptimeRobot."""
    db = 'ok'
    try:
        if not get_cache().ping():
            db = 'error'
    except Exception:
        db = 'error'
    return jsonify(ok=(db == 'ok'), db=db, service='plato', parser=PARSER_VERSION), (200 if db == 'ok' else 503)


@app.errorhandler(413)
def too_large(error):
    """A body over MAX_CONTENT_LENGTH: say the limit in MB instead of a bare 413."""
    flash(f'That file is larger than {MAX_FILE_SIZE_MB} MB, which is the most this free hosting can accept. '
          'Print the outline to a smaller PDF (or remove images) and try again.', 'error')
    return redirect(url_for('index'))


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

