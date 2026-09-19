#!/usr/bin/env python3
"""Run Plato's extractor over the labelled corpus and dump one JSON per PDF.

Usage:  .venv/bin/python tests/corpus/run_extractor.py [--out DIR] [names...]

PDFs are read from $PLATO_CORPUS_DIR (default ~/projects/plato-corpus/pdfs).
Output JSON has the same shape as tests/corpus/ground_truth/*.json so that
score.py can compare them.
"""
import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.pdf_extractor import PDFExtractor  # noqa: E402

DEFAULT_CORPUS = Path(os.environ.get("PLATO_CORPUS_DIR", Path.home() / "projects/plato-corpus/pdfs"))
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _days(days):
    out = []
    for d in days or []:
        if isinstance(d, int):
            out.append(DAY_NAMES[d] if 0 <= d < 7 else str(d))
        else:
            out.append(str(d)[:3].title())
    return out


def _section(s):
    """One scored slot per weekly meeting (a section that meets Mon and Wed at different times is
    one SectionOption with two meetings since D22; the ground truth lists each meeting)."""
    out = []
    for m in s.all_meetings():
        out.append({
            "type": (s.section_type or "").lower(),
            "id": s.section_id,
            "days": _days(m.days_of_week),
            "start": m.start_time.strftime("%H:%M") if m.start_time else None,
            "end": m.end_time.strftime("%H:%M") if m.end_time else None,
            "location": m.location,
        })
    return out


def _assessment(a):
    return {
        "title": a.title,
        "type": a.type,
        "weight": a.weight_percent,
        "due": a.due_datetime.strftime("%Y-%m-%d") if a.due_datetime else None,
        "due_time": a.due_datetime.strftime("%H:%M") if a.due_datetime else None,
        "confidence": getattr(a, "confidence", None),
        "date_status": getattr(a, "date_status", None),
        "dates": [d.isoformat() for d in (getattr(a, "dates", None) or [])],
        "is_bonus": getattr(a, "is_bonus", False),
    }


def extract_one(pdf: Path) -> dict:
    t0 = time.time()
    try:
        data = PDFExtractor(pdf).extract_all()
        term = data.term
        return {
            "file": pdf.name,
            "ok": True,
            "seconds": round(time.time() - t0, 2),
            "course_code": data.course_code,
            "course_name": data.course_name,
            "term": {
                "name": term.term_name if term else None,
                "start": term.start_date.isoformat() if term and term.start_date else None,
                "end": term.end_date.isoformat() if term and term.end_date else None,
            },
            "sections": [m for s in (data.lecture_sections or []) + (data.lab_sections or []) + (getattr(data, "tutorial_sections", None) or []) for m in _section(s)],
            "assessments": [_assessment(a) for a in data.assessments or []],
            "notes": list(getattr(data, "notes", []) or []),
        }
    except Exception as e:  # noqa: BLE001
        return {"file": pdf.name, "ok": False, "seconds": round(time.time() - t0, 2),
                "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-2000:]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).parent / "output"))
    ap.add_argument("names", nargs="*")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(DEFAULT_CORPUS.glob("*.pdf"))
    if args.names:
        pdfs = [p for p in pdfs if p.stem in args.names or p.name in args.names]
    for pdf in pdfs:
        r = extract_one(pdf)
        (out / (pdf.stem + ".json")).write_text(json.dumps(r, indent=2, default=str))
        flag = "OK " if r["ok"] else "ERR"
        n_a = len(r.get("assessments", [])) if r["ok"] else 0
        n_s = len(r.get("sections", [])) if r["ok"] else 0
        print(f"{flag} {r['seconds']:6.1f}s  a={n_a:2d} s={n_s:2d}  {pdf.name}" + ("" if r["ok"] else f"  {r['error']}"))


if __name__ == "__main__":
    main()
