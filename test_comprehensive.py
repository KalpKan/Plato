#!/usr/bin/env python3
"""
Comprehensive test of the new extraction pipeline on all PDFs.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.pdf_extractor import PDFExtractor


def test_all_pdfs():
    """Test all PDFs in course_outlines and test_course_outlines."""
    
    folders = [
        Path("course_outlines"),
        Path("test_course_outlines"),
    ]
    
    results = []
    
    for folder in folders:
        if not folder.exists():
            continue
            
        for pdf_file in folder.glob("*.pdf"):
            result = test_pdf(pdf_file)
            results.append(result)
    
    # Print summary
    print("\n" + "=" * 70)
    print("COMPREHENSIVE EXTRACTION TEST RESULTS")
    print("=" * 70)
    
    total = len(results)
    successful = sum(1 for r in results if r["status"] == "OK")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    skipped = sum(1 for r in results if r["status"] == "SKIP")
    
    perfect_weight = sum(1 for r in results if r["status"] == "OK" and 90 <= r["weight"] <= 110)
    good_weight = sum(1 for r in results if r["status"] == "OK" and 80 <= r["weight"] <= 120)
    
    with_name = sum(1 for r in results if r["status"] == "OK" and r["has_name"])
    with_term = sum(1 for r in results if r["status"] == "OK" and r["has_term"])
    with_assessments = sum(1 for r in results if r["status"] == "OK" and r["num_assessments"] >= 2)
    
    print(f"\nTotal PDFs: {total}")
    print(f"Successful: {successful} ({100*successful/total:.0f}%)")
    print(f"Errors: {errors}")
    print(f"Skipped: {skipped}")
    
    print(f"\n--- Weight Accuracy ---")
    print(f"Perfect (90-110%): {perfect_weight} ({100*perfect_weight/successful:.0f}% of successful)")
    print(f"Good (80-120%): {good_weight} ({100*good_weight/successful:.0f}% of successful)")
    
    print(f"\n--- Field Extraction ---")
    print(f"Has Course Name: {with_name} ({100*with_name/successful:.0f}%)")
    print(f"Has Term: {with_term} ({100*with_term/successful:.0f}%)")
    print(f"Has 2+ Assessments: {with_assessments} ({100*with_assessments/successful:.0f}%)")
    
    # List problematic PDFs
    print("\n--- Problematic PDFs (weight outside 80-120%) ---")
    for r in results:
        if r["status"] == "OK" and (r["weight"] < 80 or r["weight"] > 120):
            print(f"  {r['name'][:40]}: {r['weight']:.1f}% - {r['num_assessments']} assessments")
    
    print("\n--- Weight Distribution ---")
    weight_ranges = {
        "0-50%": 0,
        "50-80%": 0,
        "80-90%": 0,
        "90-100%": 0,
        "100-110%": 0,
        "110-120%": 0,
        "120%+": 0
    }
    for r in results:
        if r["status"] != "OK":
            continue
        w = r["weight"]
        if w < 50:
            weight_ranges["0-50%"] += 1
        elif w < 80:
            weight_ranges["50-80%"] += 1
        elif w < 90:
            weight_ranges["80-90%"] += 1
        elif w < 100:
            weight_ranges["90-100%"] += 1
        elif w < 110:
            weight_ranges["100-110%"] += 1
        elif w < 120:
            weight_ranges["110-120%"] += 1
        else:
            weight_ranges["120%+"] += 1
    
    for range_name, count in weight_ranges.items():
        bar = "█" * count
        print(f"  {range_name:12} {bar} {count}")


def test_pdf(pdf_path: Path) -> dict:
    """Test a single PDF."""
    result = {
        "name": pdf_path.name,
        "status": "OK",
        "weight": 0,
        "num_assessments": 0,
        "has_name": False,
        "has_term": False,
        "error": None
    }
    
    # Check file size
    size_mb = pdf_path.stat().st_size / (1024 * 1024)
    if size_mb > 5:
        result["status"] = "SKIP"
        result["error"] = f"Too large ({size_mb:.1f}MB)"
        print(f"SKIP: {pdf_path.name} - {result['error']}")
        return result
    
    try:
        extractor = PDFExtractor(pdf_path)
        data = extractor.extract_all()
        
        result["weight"] = sum(a.weight_percent or 0 for a in data.assessments)
        result["num_assessments"] = len(data.assessments)
        result["has_name"] = bool(data.course_name and len(data.course_name) > 3)
        result["has_term"] = bool(data.term and data.term.term_name and data.term.term_name != "Unknown")
        
        status = "✅" if 90 <= result["weight"] <= 110 else "⚠️" if 80 <= result["weight"] <= 120 else "❌"
        print(f"{status} {pdf_path.name[:45]:45} | {result['weight']:6.1f}% | {result['num_assessments']:2} assessments")
        
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)
        print(f"❌ {pdf_path.name[:45]:45} | ERROR: {str(e)[:30]}")
    
    return result


if __name__ == "__main__":
    test_all_pdfs()

