#!/usr/bin/env python3
"""
Simple test script to verify current functionality.

Usage:
    python test_cli.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.pdf_extractor import PDFExtractor
from src.models import CourseTerm
from datetime import date

def test_pdf_extraction():
    """Test PDF extraction with the reference PDF."""
    print("=" * 60)
    print("Testing PDF Extraction")
    print("=" * 60)
    
    pdf_path = Path("BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        print("   Make sure the PDF file is in the project root directory.")
        return False
    
    try:
        print(f"📄 Extracting from: {pdf_path.name}")
        extractor = PDFExtractor(pdf_path)
        data = extractor.extract_all()
        
        print(f"\n✅ Extraction successful!")
        print(f"   Term: {data.term.term_name}")
        print(f"   Course: {data.course_code or 'Not found'} - {data.course_name or 'Not found'}")
        print(f"   Lecture sections: {len(data.lecture_sections)}")
        print(f"   Lab sections: {len(data.lab_sections)}")
        print(f"   Assessments: {len(data.assessments)}")
        
        if data.lecture_sections:
            print(f"\n   Lecture sections found:")
            for i, section in enumerate(data.lecture_sections, 1):
                days = ", ".join(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d] 
                                for d in section.days_of_week)
                print(f"     {i}. Section {section.section_id or 'N/A'}: {days} "
                      f"{section.start_time.strftime('%H:%M')}-{section.end_time.strftime('%H:%M')}")
        
        if data.lab_sections:
            print(f"\n   Lab sections found:")
            for i, section in enumerate(data.lab_sections, 1):
                days = ", ".join(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d] 
                                for d in section.days_of_week)
                print(f"     {i}. Section {section.section_id or 'N/A'}: {days} "
                      f"{section.start_time.strftime('%H:%M')}-{section.end_time.strftime('%H:%M')}")
        
        if data.assessments:
            print(f"\n   Assessments found:")
            for i, assessment in enumerate(data.assessments[:5], 1):  # Show first 5
                due_info = assessment.due_datetime.strftime('%Y-%m-%d %H:%M') if assessment.due_datetime else assessment.due_rule or "Not specified"
                weight = f"{assessment.weight_percent}%" if assessment.weight_percent else "Not specified"
                print(f"     {i}. {assessment.title}")
                print(f"        Type: {assessment.type}, Weight: {weight}, Due: {due_info}")
                print(f"        Confidence: {assessment.confidence:.1%}, Needs review: {assessment.needs_review}")
            if len(data.assessments) > 5:
                print(f"     ... and {len(data.assessments) - 5} more")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_modules():
    """Test that all modules can be imported."""
    print("\n" + "=" * 60)
    print("Testing Module Imports")
    print("=" * 60)
    
    modules = [
        "src.models",
        "src.pdf_extractor",
        "src.rule_resolver",
        "src.study_plan",
        "src.icalendar_gen",
        "src.cache",
    ]
    
    all_ok = True
    for module_name in modules:
        try:
            __import__(module_name)
            print(f"✅ {module_name}")
        except ImportError as e:
            print(f"❌ {module_name}: {e}")
            all_ok = False
    
    return all_ok

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Plato - Functionality Test")
    print("=" * 60)
    print("\nThis script tests the current functionality of the project.")
    print("Note: The web interface is not yet implemented.\n")
    
    # Test imports
    imports_ok = test_modules()
    
    if not imports_ok:
        print("\n❌ Some modules failed to import. Please install dependencies:")
        print("   pip install -r requirements.txt")
        return
    
    # Test PDF extraction
    extraction_ok = test_pdf_extraction()
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    if imports_ok and extraction_ok:
        print("✅ All tests passed!")
        print("\nYou can now test the full CLI with:")
        print('   python -m src.main "BMSUE Syllabus Phys3140A Fall 2025 Sept3.pdf" --no-cache')
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    print("\nFor more testing options, see TESTING_GUIDE.md")

if __name__ == "__main__":
    main()

