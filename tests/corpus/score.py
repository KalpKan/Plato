#!/usr/bin/env python3
"""Score extractor output against the labelled corpus (recall / precision per event type).

Usage:
  .venv/bin/python tests/corpus/score.py [--output DIR] [--markdown FILE] [--json FILE]

--output defaults to tests/corpus/output (what run_extractor.py writes).
Ground truth lives in tests/corpus/ground_truth/<stem>.json.

Metrics (all per labelled PDF, then pooled across the corpus):
  course_code      extracted code equals the expected code (spaces/case-insensitive)
  course_name      extracted name equals or contains the expected name (letters/digits only); when the
                   outline prints no name beyond the code (GT name == code), None or the code is a hit
  term             start and end dates both equal the expected term dates
  sections         match = same type + same day set + same start time (end/location not scored)
  assessments      match = fuzzy title (>= 0.55 after normalisation) or exact weight+type, greedy best-first
  weights          matched assessment has the expected weight
  dates_exact      GT items with date_status "exact": matched AND extracted due date equals expected
  no_fabricated    GT items with date_status tba/registrar/range: matched item has NO date at all;
                   recurring: no date, or a date in the expected list / window
  clean_titles     matched title equals expected after normalisation (no footnote digits, no '(' tails)
  weight_total     sum of extracted weights is within +/-2 of an acceptable total
  (rows named in ground-truth `excluded_rows`, e.g. bonus marks, are ignored: neither hit nor spurious)

Exit code is always 0; tests/test_corpus.py turns these numbers into a gate.
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GT_DIR = HERE / "ground_truth"

TYPE_ALIASES = {
    "final_exam": "final", "exam": "final", "quiz": "quiz", "test": "test", "midterm": "midterm",
    "assignment": "assignment", "other": "other", "project": "project", "lab_report": "lab_report",
    "lab": "lab_report", "presentation": "presentation", "tutorial": "tutorial", "lecture": "lecture",
}


def norm_title(t: str) -> str:
    t = (t or "").lower()
    t = re.sub(r"^[ivx]+\.\s*|^\*\s*|^\d+\.\s*", "", t)          # "I. ", "* ", "1. "
    t = re.sub(r"\(.*?\)|\(.*$", "", t)                           # parenthetical tails, "Assignment 1 ("
    t = re.sub(r"[^a-z0-9&\s]", " ", t)
    t = re.sub(r"\b(the|a|an|of|to|and|in|term|exam|examination|test)\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


SUBJECT_ALIASES = {
    "computerscience": "cs", "classicalstudies": "cs", "healthsciences": "hs", "kinesiology": "kin",
    "biochemistry": "biochem", "mathematics": "math", "physiology": "physiol", "calculus": "calc",
    "appliedmathematics": "am", "electricalandcomputerengineering": "ece",
}


def norm_code(c: str) -> str:
    """Case/space-insensitive; a spelled-out subject equals its Western abbreviation
    ("Computer Science 3340B" == "CS 3340B"), since outlines print either form."""
    c = (c or "").lower().replace("-", " ")
    c = re.sub(r"\s+", "", c)
    m = re.match(r"^([a-z&]+)(\d.*)$", c)
    if m and m.group(1) in SUBJECT_ALIASES:
        c = SUBJECT_ALIASES[m.group(1)] + m.group(2)
    return c


def norm_name(n) -> str:
    return re.sub(r"[^a-z0-9]", "", (n or "").lower())


def name_hit(gt: dict, ex: dict) -> int:
    want, got = norm_name(gt.get("course_name")), norm_name(ex.get("course_name"))
    if not want or want == norm_name(gt.get("course_code")) or want == norm_code(gt.get("course_code")):
        return int(not got or got == want or got == norm_name(ex.get("course_code")))
    return int(bool(got) and (got == want or want in got))


def title_sim(a: str, b: str) -> float:
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def match_assessments(gt_list, ex_list):
    """Greedy best-first matching; returns list of (gt_idx, ex_idx, sim)."""
    pairs = []
    for i, g in enumerate(gt_list):
        for j, e in enumerate(ex_list):
            sim = title_sim(g["title"], e.get("title", ""))
            same_w = g.get("weight") is not None and e.get("weight") is not None and abs(float(g["weight"]) - float(e["weight"])) < 0.01
            gtype = TYPE_ALIASES.get(g.get("type"), g.get("type"))
            etype = TYPE_ALIASES.get(e.get("type"), e.get("type"))
            score = sim + (0.25 if same_w else 0) + (0.1 if gtype == etype else 0)
            ok = sim >= 0.55 or (same_w and gtype == etype and sim >= 0.2) or (same_w and sim >= 0.4)
            if ok:
                pairs.append((score, i, j))
    pairs.sort(reverse=True)
    used_g, used_e, out = set(), set(), []
    for score, i, j in pairs:
        if i in used_g or j in used_e:
            continue
        used_g.add(i); used_e.add(j); out.append((i, j, score))
    return out


def match_sections(gt_list, ex_list):
    out, used = [], set()
    for i, g in enumerate(gt_list):
        for j, e in enumerate(ex_list):
            if j in used:
                continue
            same_type = (g["type"] or "").lower() == (e.get("type") or "").lower()
            same_days = set(d[:3].title() for d in g.get("days") or []) == set(d[:3].title() for d in e.get("days") or [])
            same_start = (g.get("start") or None) == (e.get("start") or None)
            if same_type and same_days and same_start and (g.get("days") or g.get("start")):
                out.append((i, j)); used.add(j); break
    return out


def score_one(gt: dict, ex: dict) -> dict:
    r = {"file": gt["file"], "ok": ex.get("ok", False)}
    if not ex.get("ok"):
        r.update(error=ex.get("error"), counts={})
        return r
    c = {}
    c["course_code"] = (1, int(norm_code(ex.get("course_code")) == norm_code(gt["course_code"])))
    c["course_name"] = (1, name_hit(gt, ex))
    term_ok = ex.get("term", {}).get("start") == gt["term"]["start"] and ex.get("term", {}).get("end") == gt["term"]["end"]
    c["term"] = (1, int(term_ok))

    gts = [s for s in gt.get("sections", []) if s.get("days") or s.get("start")]
    exs = ex.get("sections", [])
    if gt.get("sections_extractable_without_ocr") is False:
        # the slots live on an image-only page (CS 3342A page 1): no text layer, so the
        # parser is not scored on them (it must say so on the review page instead)
        gts, exs = [], []
    sm = match_sections(gts, exs)
    c["sections_recall"] = (len(gts), len(sm))
    c["sections_precision"] = (len(exs), len(sm))

    gta = gt["assessments"]
    # rows the outline lists but that are not calendar events (bonus weight, optional extras):
    # extracting them is neither rewarded nor punished.
    excluded = [norm_title(re.sub(r"\+?\d+(?:\.\d+)?\s*%", " ", x.split("(")[0])) for x in gt.get("excluded_rows", [])]
    exa = [a for a in ex.get("assessments", [])
           if not any(difflib.SequenceMatcher(None, norm_title(a.get("title", "")), x).ratio() >= 0.8 for x in excluded)]
    am = match_assessments(gta, exa)
    c["assessments_recall"] = (len(gta), len(am))
    c["assessments_precision"] = (len(exa), len(am))
    w_ok = d_ok = d_n = nf_ok = nf_n = t_ok = 0
    details = []
    for i, j, _ in am:
        g, e = gta[i], exa[j]
        w = e.get("weight") is not None and abs(float(e["weight"]) - float(g["weight"])) < 0.01
        w_ok += int(w)
        clean = norm_title(e.get("title", "")) == norm_title(g["title"])
        t_ok += int(clean)
        st = g.get("date_status", "exact")
        if st == "exact":
            d_n += 1
            good = e.get("due") == g["due"]
            d_ok += int(good)
            details.append(f"{g['title']}: due {g['due']} -> {e.get('due')} {'OK' if good else 'WRONG'}")
        else:
            nf_n += 1
            due = e.get("due")
            win = g.get("window") or (gt["term"]["exam_period"] if st == "registrar" else None)
            dates = g.get("dates")
            if due is None:
                good = True
            elif st in ("registrar", "range", "tba"):
                # the outline gives no day: any day the parser attaches is invented, even one inside
                # the window (Biol 3415G 'April 7-30' -> Apr 7 was hidden by the old tolerance, D21)
                good = False
            elif dates and due in dates:
                good = True
            elif win and win[0] <= due <= win[1]:
                good = True
            else:
                good = False
            nf_ok += int(good)
            details.append(f"{g['title']}: {st} -> {due} {'OK' if good else 'FABRICATED'}")
    unmatched_gt = [gta[i]["title"] for i in range(len(gta)) if i not in {i for i, _, _ in am}]
    unmatched_ex = [exa[j].get("title") for j in range(len(exa)) if j not in {j for _, j, _ in am}]
    c["weights"] = (len(am), w_ok)
    c["dates_exact"] = (d_n, d_ok)
    c["no_fabricated"] = (nf_n, nf_ok)
    c["clean_titles"] = (len(am), t_ok)
    total = sum(float(a["weight"]) for a in exa if a.get("weight") is not None)
    acceptable = gt.get("acceptable_weight_totals") or [gt.get("expected_weight_total", 100)]
    c["weight_total"] = (1, int(any(abs(total - t) <= 2 for t in acceptable)))
    r.update(counts=c, extracted_total=total, missed=unmatched_gt, spurious=unmatched_ex, date_details=details)
    return r


def pooled(results):
    keys = ["course_code", "course_name", "term", "sections_recall", "sections_precision", "assessments_recall",
            "assessments_precision", "weights", "dates_exact", "no_fabricated", "clean_titles", "weight_total"]
    out = {}
    for k in keys:
        n = sum(r["counts"].get(k, (0, 0))[0] for r in results if r.get("ok"))
        h = sum(r["counts"].get(k, (0, 0))[1] for r in results if r.get("ok"))
        out[k] = {"n": n, "hit": h, "pct": (100.0 * h / n) if n else None}
    out["files_ok"] = {"n": len(results), "hit": sum(1 for r in results if r.get("ok")),
                       "pct": 100.0 * sum(1 for r in results if r.get("ok")) / max(1, len(results))}
    return out


def fmt_pct(v):
    return "n/a" if v is None else f"{v:.0f}%"


def markdown(results, pool, title):
    lines = [f"# {title}", ""]
    lines.append("| metric | hit / n | % |")
    lines.append("|---|---|---|")
    for k, v in pool.items():
        lines.append(f"| {k} | {v['hit']} / {v['n']} | {fmt_pct(v['pct'])} |")
    lines += ["", "## Per file", "", "| file | code | name | term | sections R/P | assessments R/P | weights | dates exact | no fabricated | clean titles | total |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        if not r.get("ok"):
            lines.append(f"| {r['file']} | ERROR {r.get('error')} | | | | | | | | | |")
            continue
        c = r["counts"]
        def rp(a, b):
            return f"{c[a][1]}/{c[a][0]} · {c[b][1]}/{c[b][0]}"
        lines.append(f"| {r['file']} | {'✓' if c['course_code'][1] else '✗'} | {'✓' if c.get('course_name', (1, 0))[1] else '✗'} | {'✓' if c['term'][1] else '✗'} | {rp('sections_recall','sections_precision')} | {rp('assessments_recall','assessments_precision')} | {c['weights'][1]}/{c['weights'][0]} | {c['dates_exact'][1]}/{c['dates_exact'][0]} | {c['no_fabricated'][1]}/{c['no_fabricated'][0]} | {c['clean_titles'][1]}/{c['clean_titles'][0]} | {r['extracted_total']:.0f} {'✓' if c['weight_total'][1] else '✗'} |")
    lines += ["", "## Details", ""]
    for r in results:
        if not r.get("ok"):
            continue
        lines.append(f"### {r['file']}")
        for d in r["date_details"]:
            lines.append(f"- {d}")
        if r["missed"]:
            lines.append(f"- MISSED: {r['missed']}")
        if r["spurious"]:
            lines.append(f"- SPURIOUS: {r['spurious']}")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(HERE / "output"))
    ap.add_argument("--markdown")
    ap.add_argument("--json")
    ap.add_argument("--title", default="Plato corpus score")
    args = ap.parse_args()
    out_dir = Path(args.output)
    results = []
    for gt_path in sorted(GT_DIR.glob("*.json")):
        gt = json.loads(gt_path.read_text())
        ex_path = out_dir / gt_path.name
        if not ex_path.exists():
            results.append({"file": gt["file"], "ok": False, "error": f"no output at {ex_path}", "counts": {}})
            continue
        results.append(score_one(gt, json.loads(ex_path.read_text())))
    pool = pooled(results)
    md = markdown(results, pool, args.title)
    if args.markdown:
        Path(args.markdown).write_text(md + "\n")
    if args.json:
        Path(args.json).write_text(json.dumps({"pooled": pool, "files": results}, indent=2, ensure_ascii=False) + "\n")
    print(md)


if __name__ == "__main__":
    sys.exit(main())
