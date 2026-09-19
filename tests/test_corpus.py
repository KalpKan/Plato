"""Consumer-grade gate for the extractor, measured on the labelled corpus.

Skips when the corpus PDFs are not on this machine (they are never committed).
The consumer-grade bar from docs/reports/plato-spec.md is enforced by default (the
parser met it on 2026-09-18, fix round 1: 15 labelled outlines; fix round 2 on 2026-09-19 raised
the labelled set to 18 and added course_name). Set PLATO_CORPUS_GATE=0 to run in report-only
mode while experimenting with the parser.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORPUS = Path(os.environ.get("PLATO_CORPUS_DIR", Path.home() / "projects/plato-corpus/pdfs"))
GATE = os.environ.get("PLATO_CORPUS_GATE", "1") != "0"

# The bar (see docs/reports/plato-spec.md, section C). Percent of pooled items.
BAR = {
    "files_ok": 100,
    "course_code": 90,
    "course_name": 90,
    "term": 90,
    "sections_recall": 90,
    "sections_precision": 90,
    "assessments_recall": 95,
    "assessments_precision": 95,
    "weights": 98,
    "dates_exact": 95,
    "no_fabricated": 100,
    "clean_titles": 95,
    "weight_total": 90,
}


@pytest.mark.skipif(not CORPUS.exists(), reason=f"labelled corpus not present at {CORPUS}")
def test_corpus_scores(tmp_path):
    out = tmp_path / "out"
    labelled = [json.loads(p.read_text())["file"] for p in (ROOT / "tests/corpus/ground_truth").glob("*.json")]
    subprocess.run([sys.executable, str(ROOT / "tests/corpus/run_extractor.py"), "--out", str(out), *labelled],
                   check=True, cwd=ROOT, timeout=900)
    report = tmp_path / "score.json"
    subprocess.run([sys.executable, str(ROOT / "tests/corpus/score.py"), "--output", str(out),
                    "--json", str(report), "--markdown", str(tmp_path / "score.md")],
                   check=True, cwd=ROOT, timeout=120, stdout=subprocess.DEVNULL)
    pooled = json.loads(report.read_text())["pooled"]
    failures = []
    for key, bar in BAR.items():
        pct = pooled[key]["pct"]
        line = f"{key}: {pooled[key]['hit']}/{pooled[key]['n']} = {pct if pct is None else round(pct)}% (bar {bar}%)"
        print(line)
        if pct is None or pct < bar:
            failures.append(line)
    if GATE:
        assert not failures, "consumer-grade bar not met:\n" + "\n".join(failures)


@pytest.mark.skipif(not CORPUS.exists(), reason=f"labelled corpus not present at {CORPUS}")
def test_default_download_carries_every_labelled_lecture_meeting():
    """D22: a course that meets Mon and Wed is one preselected section with two weekly series; the
    scorer's slot matching cannot see a picker that drops the lecture, so this checks the .ics itself."""
    from src.icalendar_gen import ICalendarGenerator
    from src.outline.pipeline import parse_outline
    problems = []
    for gt_path in sorted((ROOT / "tests/corpus/ground_truth").glob("*.json")):
        gt = json.loads(gt_path.read_text())
        if gt.get("sections_extractable_without_ocr") is False:
            continue
        want = [s for s in gt.get("sections", []) if s["type"] == "lecture" and s.get("start")]
        if not want:
            continue
        data = parse_outline(CORPUS / gt["file"])
        if len(data.lecture_sections) != 1:
            # several printed sections (001/002/...): the student picks one, nothing is preselected
            ids = [s.section_id for s in data.lecture_sections]
            if not all(ids) or len(set(ids)) != len(ids):
                problems.append(f"{gt['file']}: {len(data.lecture_sections)} lecture options without distinct section ids")
            continue
        expected = sum(len(s.get("days") or []) for s in want)
        cal = ICalendarGenerator().generate_calendar(term=data.term, lecture_section=data.lecture_sections[0],
                                                     lab_section=None, assessments=[], study_plan=[],
                                                     course_code=data.course_code)
        ics = cal.to_ical().decode()
        rrules = len([l for l in ics.splitlines() if l.startswith("RRULE:")])
        if rrules != expected:
            problems.append(f"{gt['file']}: {rrules} weekly series in the default download, outline has {expected} lecture meetings")
    assert not problems, "\n".join(problems)
