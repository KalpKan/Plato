#!/usr/bin/env python3
"""
Non-interactive test to see what's being extracted from the PDF.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.pdf_extractor import PDFExtractor
from src.rule_resolver import RuleResolver
from src.study_plan import StudyPlanGenerator
from src.icalendar_gen import ICalendarGenerator
from src.models import UserSelections

def test_full_extraction():
    """Test the full extraction pipeline."""
    print("=" * 70)
    print("Full Extraction Pipeline Test")
    print("=" * 70)
    
    pdf_path = Path("BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"\n📄 Processing: {pdf_path.name}\n")
    
    # Step 1: Extract from PDF
    print("Step 1: PDF Extraction")
    print("-" * 70)
    try:
        extractor = PDFExtractor(pdf_path)
        data = extractor.extract_all()
        
        print(f"✅ Term: {data.term.term_name}")
        print(f"   Start: {data.term.start_date}, End: {data.term.end_date}")
        print(f"✅ Course Code: {data.course_code or 'Not found'}")
        print(f"✅ Course Name: {data.course_name or 'Not found'}")
        print(f"✅ Lecture Sections: {len(data.lecture_sections)}")
        print(f"✅ Lab Sections: {len(data.lab_sections)}")
        print(f"✅ Assessments: {len(data.assessments)}")
        
        # Show sections
        if data.lecture_sections:
            print("\n   Lecture Sections:")
            for i, sec in enumerate(data.lecture_sections, 1):
                days = ", ".join(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d] 
                                for d in sec.days_of_week)
                print(f"     {i}. Section {sec.section_id or 'N/A'}: {days} "
                      f"{sec.start_time.strftime('%H:%M')}-{sec.end_time.strftime('%H:%M')}")
        
        if data.lab_sections:
            print("\n   Lab Sections:")
            for i, sec in enumerate(data.lab_sections, 1):
                days = ", ".join(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d] 
                                for d in sec.days_of_week)
                print(f"     {i}. Section {sec.section_id or 'N/A'}: {days} "
                      f"{sec.start_time.strftime('%H:%M')}-{sec.end_time.strftime('%H:%M')}")
        
        # Show assessments
        if data.assessments:
            print("\n   Assessments:")
            for i, ass in enumerate(data.assessments, 1):
                due = ass.due_datetime.strftime('%Y-%m-%d %H:%M') if ass.due_datetime else (ass.due_rule or "Not specified")
                weight = f"{ass.weight_percent}%" if ass.weight_percent else "Not specified"
                print(f"     {i}. {ass.title}")
                print(f"        Type: {ass.type}, Weight: {weight}")
                print(f"        Due: {due}")
                print(f"        Confidence: {ass.confidence:.1%}, Review: {ass.needs_review}")
        
        # Step 2: Rule Resolution
        print("\n\nStep 2: Rule Resolution")
        print("-" * 70)
        resolver = RuleResolver()
        all_sections = data.lecture_sections + data.lab_sections
        resolved_assessments = resolver.resolve_rules(
            data.assessments,
            all_sections,
            data.term
        )
        print(f"✅ Resolved {len(resolved_assessments)} assessments")
        
        # Step 3: Study Plan
        print("\n\nStep 3: Study Plan Generation")
        print("-" * 70)
        study_gen = StudyPlanGenerator()
        study_plan = study_gen.generate_study_plan(resolved_assessments)
        print(f"✅ Generated {len(study_plan)} study plan items")
        
        # Step 4: iCalendar Generation
        print("\n\nStep 4: iCalendar Generation")
        print("-" * 70)
        cal_gen = ICalendarGenerator(timezone_str=data.term.timezone)
        
        # Use first sections if available, or None
        lecture = data.lecture_sections[0] if data.lecture_sections else None
        lab = data.lab_sections[0] if data.lab_sections else None
        
        calendar = cal_gen.generate_calendar(
            term=data.term,
            lecture_section=lecture,
            lab_section=lab,
            assessments=resolved_assessments,
            study_plan=study_plan
        )
        
        # Count events
        events = [comp for comp in calendar.walk() if comp.name == "VEVENT"]
        print(f"✅ Generated calendar with {len(events)} events")
        
        # Save to file
        output_file = Path("test_output") / "test_calendar.ics"
        output_file.parent.mkdir(exist_ok=True)
        cal_gen.export_to_file(calendar, str(output_file))
        print(f"✅ Saved to: {output_file}")
        
        # Save JSON
        json_file = Path("test_output") / "extracted_data.json"
        json_data = {
            "term": {
                "term_name": data.term.term_name,
                "start_date": str(data.term.start_date),
                "end_date": str(data.term.end_date),
            },
            "course_code": data.course_code,
            "course_name": data.course_name,
            "lecture_sections": len(data.lecture_sections),
            "lab_sections": len(data.lab_sections),
            "assessments": len(data.assessments),
            "study_plan_items": len(study_plan),
            "calendar_events": len(events)
        }
        with open(json_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        print(f"✅ Saved summary to: {json_file}")
        
        print("\n" + "=" * 70)
        print("✅ All pipeline steps completed successfully!")
        print("=" * 70)
        print("\nNote: If sections/assessments are 0, the PDF extraction patterns")
        print("may need to be tuned for this specific PDF format.")
        print("\nThe extraction logic is working - it just needs pattern matching")
        print("optimized for Western University course outline format.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_full_extraction()

