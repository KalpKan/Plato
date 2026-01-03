#!/usr/bin/env python3
"""
Test script for the new document structure-based extraction.

Tests the improved extraction pipeline on problematic PDFs.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.pdf_extractor import PDFExtractor

# Test PDFs - focus on the problematic ones
TEST_PDFS = [
    # Over-extraction issues
    ("course_outlines/AM2402a_outline_2025_red.pdf", "AM2402a - was 132%"),
    ("course_outlines/Updated-ECE-3349A_Outline_2023.pdf", "ECE-3349A - was 150%"),
    
    # Under-extraction issues
    ("course_outlines/B2382 Course Outline 2025.pdf", "B2382 - was 77.5%"),
    ("course_outlines/B3415G Course Outline 2025.pdf", "B3415G - was 10%"),
    ("course_outlines/B3603A.pdf", "B3603A - was 29%"),
    ("course_outlines/HS-2800-Research-Methods.pdf", "HS-2800 - was 75%"),
    
    # Course name issues
    ("test_course_outlines/CS1000-001 Course Outline 25-26.pdf", "CS1000 - was 'None'"),
    ("course_outlines/2025F---MATH-4121A-9021A---Topology_red.pdf", "MATH-4121A - was 'Course Information'"),
    ("course_outlines/ECE-4429_Fall-2025-Website-Version.pdf", "ECE-4429 - was 'Faculty of Engineering'"),
    
    # Known good PDFs (sanity check)
    ("course_outlines/CS_2211A_FW25.pdf", "CS-2211A - should be ~100%"),
    ("course_outlines/PP3000E Syllabus - Fall–Winter 2025–2026 - FINAL.pdf", "PP3000E - should be ~100%"),
]

def test_pdf(pdf_path: str, description: str) -> dict:
    """Test extraction on a single PDF."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"File: {pdf_path}")
    print('='*60)
    
    full_path = Path(__file__).parent / pdf_path
    if not full_path.exists():
        return {"status": "SKIP", "reason": "File not found"}
    
    try:
        extractor = PDFExtractor(full_path)
        data = extractor.extract_all()
        
        # Calculate weight
        total_weight = sum(a.weight_percent or 0 for a in data.assessments)
        
        result = {
            "status": "OK",
            "course_code": data.course_code,
            "course_name": data.course_name,
            "term": str(data.term.term_name) if data.term else None,
            "num_assessments": len(data.assessments),
            "total_weight": total_weight,
            "assessments": [
                {"title": a.title[:40], "weight": a.weight_percent}
                for a in data.assessments[:8]  # Show first 8
            ]
        }
        
        # Print results
        print(f"\nCourse: {data.course_code} - {data.course_name}")
        print(f"Term: {data.term.term_name if data.term else 'Unknown'}")
        print(f"Assessments: {len(data.assessments)}")
        print(f"Total Weight: {total_weight:.1f}%")
        
        # Color code the weight
        if 90 <= total_weight <= 110:
            weight_status = "✅ PERFECT"
        elif 80 <= total_weight <= 120:
            weight_status = "⚠️ ACCEPTABLE"
        else:
            weight_status = "❌ NEEDS FIX"
        print(f"Weight Status: {weight_status}")
        
        print("\nAssessments:")
        for a in data.assessments[:8]:
            print(f"  - {a.title[:40]}: {a.weight_percent}%")
        
        # Get debug info if available
        if hasattr(extractor, 'get_extraction_debug'):
            debug = extractor.get_extraction_debug()
            if 'assessment_extraction' in debug:
                ae = debug['assessment_extraction']
                if ae.get('rejected_candidates'):
                    print(f"\nRejected {len(ae['rejected_candidates'])} false positives:")
                    for rc in ae['rejected_candidates'][:3]:
                        print(f"  - {rc['title'][:30]}: {rc['reason']}")
        
        return result
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "ERROR", "error": str(e)}


def main():
    print("="*60)
    print("NEW EXTRACTION PIPELINE TEST")
    print("="*60)
    
    results = {}
    stats = {"ok": 0, "error": 0, "skip": 0, "perfect_weight": 0, "acceptable_weight": 0}
    
    for pdf_path, description in TEST_PDFS:
        result = test_pdf(pdf_path, description)
        results[pdf_path] = result
        
        if result["status"] == "OK":
            stats["ok"] += 1
            weight = result.get("total_weight", 0)
            if 90 <= weight <= 110:
                stats["perfect_weight"] += 1
            elif 80 <= weight <= 120:
                stats["acceptable_weight"] += 1
        elif result["status"] == "ERROR":
            stats["error"] += 1
        else:
            stats["skip"] += 1
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total PDFs tested: {len(TEST_PDFS)}")
    print(f"Successful: {stats['ok']}")
    print(f"Errors: {stats['error']}")
    print(f"Skipped: {stats['skip']}")
    print(f"Perfect weight (90-110%): {stats['perfect_weight']}")
    print(f"Acceptable weight (80-120%): {stats['acceptable_weight']}")
    
    # Print weight improvements
    print("\n" + "-"*60)
    print("WEIGHT COMPARISON (Before → After)")
    print("-"*60)
    
    before = {
        "AM2402a": 132,
        "ECE-3349A": 150,
        "B2382": 77.5,
        "B3415G": 10,
        "B3603A": 29,
        "HS-2800": 75,
    }
    
    for pdf_path, result in results.items():
        if result["status"] == "OK":
            name = Path(pdf_path).stem[:15]
            after = result.get("total_weight", 0)
            
            # Find matching before value
            old = None
            for key, val in before.items():
                if key in pdf_path:
                    old = val
                    break
            
            if old:
                direction = "↑" if after > old else "↓" if after < old else "="
                improvement = "✅" if 90 <= after <= 110 else "⚠️"
                print(f"  {name:20} {old:6.1f}% → {after:6.1f}% {direction} {improvement}")


if __name__ == "__main__":
    main()

