"""Assessments (title, type, weight, due date or a reason for having none).

Sources, in order of trust:
  1. evaluation tables (a Weight/% column): one candidate per row, continuation rows merged,
     footnote digits stripped from titles, "Assignment | 1 | 8% | Thursday, January 29" rows
     named "<header> <n>";
  2. inline lists in the evaluation section ("Assignment 1 (10%) -- due Oct. 9",
     "First test: 20% (12 November 2025)", "Mid-term test - 20%", "Term Test 1 20% ... Friday Oct. 3");
  3. dates for still-undated rows from the weekly schedule table ("7 | October 16 | MID-TERM TEST (20%)")
     and from prose ("The Midterm exam will be (tentative) on Thursday March 12 at 2:30-4:20PM").
Every candidate carries a DateResult so the review page can print why a row has no date.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from datetime import date, time
from typing import Dict, List, Optional, Sequence, Tuple

from .dates import DateResolver, DateResult, MONTH_RE, parse_time_span
from .tables import compress_table as _compress
from .term import TermInfo

NOUNS = r"exam|examination|midterm|mid-term|test|quiz|quizzes|assignment|assessment|homework|project|lab|labs|laboratory|report|essay|paper|presentation|participation|attendance|portfolio|reflection|evaluation|proposal|practicum|tutorial|case\s+study|journal|discussion|poster|review|critique|exercise|problem\s+set|worksheet|final|term\s+work|inquiry|peer"
_NOUN = re.compile(rf"\b(?:{NOUNS})s?\b", re.I)
_PCT = re.compile(r"(?<![\d.])(\+?\d{1,3}(?:\.\d+)?)\s*%")
_POLICY = re.compile(r"\b(must|at least|minimum|in order to|eligible|passing|pass the|weighted average|reweight|moved to|transferred|penalt|deduct|late|rounded|cap(?:ped)?|threshold|achieve|obtain|required to|will receive|maximum overall|combined mark|combined grade|fail)\b|\bis\s+(?:worth|based)\b|\bmore than\b|\bless than\b|\bper\s+day\b", re.I)
_TOTAL = re.compile(r"^\s*(grand\s+)?total\b|^\s*sum\b|^\s*overall\b|^\s*100\s*%", re.I)
_HEADING_EVAL = re.compile(r"^\s*(?:\d+\.\s*)?(?:methods?\s+of\s+evaluation|evaluation|assessments?\s+and\s+evaluation|assessment|grading|marking\s+scheme|course\s+evaluation|evaluation\s*/\s*grade\s+breakdown|grade\s+breakdown|course\s+requirements|evaluation\s+scheme|marks?\s+distribution|assessments?)\b[^\n]{0,40}$", re.I)
_HEADING_END = re.compile(r"^\s*(?:\d+\.\s*)?(?:course\s+policies|policies|academic|accommodation|communication|office\s+hours|textbook|course\s+materials|required\s+text|schedule|statement|support|contact|learning\s+outcomes|prerequisit|late\s+(?:submission|assignment)|missed|absence|scholastic|plagiarism|use\s+of\s+electronic|notes?\s+to\s+students|about\s+assignments|important\s+details)\b", re.I)
_LEADER = re.compile(r"^\s*(?:[ivx]{1,4}\.|\d{1,2}\.|[•*\-–▪●○]|\(\w\)|[a-z]\))\s*", re.I)
_GROUP_COUNT = re.compile(r"^\s*(\d+)\s+([A-Za-z][A-Za-z\- ]{2,25}?)s\b", re.I)
_DUE_TIME_HEADER = re.compile(r"\bby\s+(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)", re.I)
_SCHEDULE_HEADER = re.compile(r"\b(week|date)", re.I)
_TIME_WORDS = re.compile(r"\b(class(?:es)?|lecture|lab|tutorial|section)\b", re.I)


@dataclass
class Assessment:
    title: str
    weight: Optional[float]
    kind: str = "other"
    date: DateResult = field(default_factory=lambda: DateResult(status="missing"))
    source: str = "table"        # table | inline | manual
    evidence: str = ""
    is_bonus: bool = False
    is_group: bool = False
    confidence: float = 0.6

    def norm(self) -> str:
        return norm_title(self.title)


# ----------------------------------------------------------------- helpers
def norm_title(t: str) -> str:
    t = (t or "").lower()
    t = re.sub(r"\(.*?\)|\(.*$", "", t)
    t = re.sub(r"[^a-z0-9&\s]", " ", t)
    t = re.sub(r"\b(the|a|an|of|to|and|in)\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def clean_title(raw: str) -> str:
    t = (raw or "").replace("\n", " ")
    t = re.sub(r"\s+", " ", t).strip()
    t = _LEADER.sub("", t)
    t = t.lstrip(" :;-–—*").rstrip(" :;-–—")
    t = re.sub(r"\s*\((?:total|each|per\b[^)]*)\)\s*$", "", t, flags=re.I)
    t = re.sub(r"\s*[:\-–—]\s*$", "", t)
    # "Labs (Total = 8)" keeps its parenthesis; a dangling "(" does not
    t = re.sub(r"\s*\($", "", t)
    if t.isupper() and len(t) > 4:
        t = _title_case(t)
    return t.strip()


def _title_case(s: str) -> str:
    small = {"and", "of", "the", "in", "to", "for", "a", "an", "on", "or"}
    return " ".join(w if (w in small and i) else w.capitalize() for i, w in enumerate(s.lower().split()))


def infer_kind(title: str) -> str:
    t = title.lower()
    if re.search(r"\bfinal\b", t) and re.search(r"exam|test|assessment", t):
        return "final"
    if re.search(r"\bfinal\s+exam", t) or t.strip() == "final":
        return "final"
    if re.search(r"mid-?term", t):
        return "midterm"
    if re.search(r"\bquiz", t):
        return "quiz"
    if re.search(r"\btest\b|\bexam\b|examination", t):
        return "test"
    if re.search(r"\blab", t):
        return "lab_report"
    if re.search(r"project", t):
        return "project"
    if re.search(r"presentation", t):
        return "presentation"
    if re.search(r"assignment|homework|essay|paper|report|reflection|portfolio|proposal|evaluation|exercise|problem set|worksheet|journal|review", t):
        return "assignment"
    if re.search(r"participation|attendance", t):
        return "participation"
    return "other"


def parse_weight(cell: str, bare_ok: bool = False) -> Tuple[Optional[float], bool]:
    """'10% (total)' -> (10, False); '+1%' -> (1, True); '25% final' -> (25, False);
    '5x5%=25%' -> (25, False); '2% each for up to 20%' -> (20, False); with bare_ok, '17.5' -> (17.5, False)."""
    if not cell:
        return None, False
    flat = cell.replace("\n", " ")
    m = _PCT.search(flat)
    if not m and bare_ok:
        m2 = re.search(r"(?<![\d.])(\d{1,3}(?:\.\d+)?)(?![\d.%])", flat)
        if not m2:
            return None, False
        v = float(m2.group(1))
        return (v, False) if 0 < v <= 100 else (None, False)
    if not m:
        return None, False
    raw = m.group(1)
    total = re.search(r"(?:=|up\s+to|total\s+of|for\s+a\s+total\s+of|maximum\s+of)\s*(\d{1,3}(?:\.\d+)?)\s*%", flat, re.I)
    if total and (re.search(r"\beach\b|\d\s*[x×]\s*\d|×", flat, re.I)):
        raw = total.group(1)
    bonus = raw.startswith("+") or bool(re.search(r"\bbonus\b|extra\s+credit", cell, re.I))
    try:
        v = float(raw.lstrip("+"))
    except ValueError:
        return None, False
    if v <= 0 or v > 100:
        return None, False
    return v, bonus


def _strip_footnotes(titles: List[str]) -> List[str]:
    """Superscript footnote digits come through glued to the title ('Tracker 11', 'Plan3',
    'Exam4'). They are recognised as a strictly increasing single digit at the end of
    consecutive titles and removed."""
    marks = []
    for t in titles:
        m = re.search(r"(\d)$", t)
        marks.append(int(m.group(1)) if m else None)
    seq = [m for m in marks if m is not None]
    glued = sum(1 for t in titles if re.search(r"[A-Za-z]\d$", t))
    if len(seq) >= 3 and glued >= 2 and all(b > a for a, b in zip(seq, seq[1:])):
        out = []
        for t, m in zip(titles, marks):
            out.append(re.sub(r"\s*(\d)$", "", t).rstrip() if m is not None else t)
        return out
    return titles


def _row_text(cells: Sequence[str]) -> str:
    return " | ".join(c.replace("\n", " ") for c in cells if c)


# --------------------------------------------------------------- tables
def _map_columns(header: List[str], body: List[List[str]]) -> Optional[Dict[str, int]]:
    h = [c.lower().replace("\n", " ") for c in header]
    cols: Dict[str, int] = {}
    for i, c in enumerate(h):
        if "name" not in cols and re.search(r"assessment|component|element|item|task|name|activity|evaluation|deliverable|assignment|method|description of|category", c) and not re.search(r"^\s*(weight|%|value|date|due)", c):
            cols["name"] = i
        if "weight" not in cols and re.search(r"weight|%|worth|value|percent|mark", c) and not re.search(r"due|date", c):
            cols["weight"] = i
        if "due" not in cols and re.search(r"\bdue\b|deadline", c):
            cols["due"] = i
        if "date" not in cols and re.search(r"\bdate", c) and not re.search(r"assigned|release|posted", c):
            cols["date"] = i
        if "assigned" not in cols and re.search(r"assigned|release|posted", c):
            cols["assigned"] = i
    if "weight" not in cols:
        # the column whose cells are mostly percentages
        best, best_n = None, 0
        for i in range(len(h)):
            n = sum(1 for r in body if i < len(r) and _PCT.search(r[i] or ""))
            if n > best_n:
                best, best_n = i, n
        if best is not None and best_n >= max(2, len(body) // 2):
            cols["weight"] = best
    if "weight" not in cols:
        return None
    if "name" not in cols:
        for i in range(len(h)):
            if i != cols["weight"] and any(r[i] for r in body if i < len(r)):
                cols["name"] = i
                break
    if "name" not in cols:
        return None
    if "due" in cols:
        cols["date"] = cols["due"]
    return cols


def _from_tables(tables: Sequence[Sequence[Sequence[Optional[str]]]], resolver: DateResolver) -> Tuple[List[Assessment], List[str]]:
    out: List[Assessment] = []
    notes: List[str] = []
    for raw in tables:
        rows = _compress(raw)
        if len(rows) < 2:
            continue
        # header = first row that looks like one; a table may start with the data if pdfplumber lost it
        header = rows[0]
        htext = " ".join(header).lower()
        if _SCHEDULE_HEADER.search(htext) and not re.search(r"weight|%|worth|value", htext):
            continue
        if re.search(r"penalt|deduct|late\b|reversed|effective\s+change", htext):
            continue  # a late-penalty / policy table, not the evaluation table
        cols = _map_columns(header, rows[1:])
        if not cols:
            continue
        bare_ok = bool(re.search(r"%|worth|weight|marks?\b|method", header[cols["weight"]].lower()))
        default_time = None
        m = _DUE_TIME_HEADER.search(htext)
        if m:
            default_time, _ = parse_time_span(m.group(1))
        name_header = header[cols["name"]].replace("\n", " ").strip()
        cands: List[Assessment] = []
        titles: List[str] = []
        for r in rows[1:]:
            name = r[cols["name"]] if cols["name"] < len(r) else ""
            wcell = r[cols["weight"]] if cols["weight"] < len(r) else ""
            weight, bonus = parse_weight(wcell, bare_ok=bare_ok)
            title = clean_title(name)
            if not title and weight is None:
                continue
            if not title:
                # continuation row: description only
                continue
            if _TOTAL.match(title):
                continue
            if re.fullmatch(r"\d{1,2}", title):
                title = f"{re.sub(r's$', '', name_header.split()[0]) if name_header else 'Item'} {title}"
            if weight is None and not _NOUN.search(title):
                continue
            titles.append(title)
            date_cell = r[cols["date"]] if "date" in cols and cols["date"] < len(r) else ""
            dr = resolver.resolve(date_cell) if date_cell else DateResult(status="missing")
            if dr.status == "missing":
                # no date column, or an empty one: look at the other cells of the row
                others = [c for i, c in enumerate(r) if i not in (cols["name"], cols["weight"], cols.get("assigned", -1)) and c]
                for c in others:
                    alt = resolver.resolve(c)
                    if alt.status != "missing":
                        dr = alt
                        break
            if dr.status == "missing" and not dr.note:
                dr.note = "No due date in the outline"
            if dr.status == "exact" and dr.time is None and default_time:
                dr.time = default_time
            cands.append(Assessment(title=title, weight=weight, kind=infer_kind(title), date=dr, source="table",
                                    evidence=_row_text(r), is_bonus=bonus, confidence=0.9 if weight is not None else 0.6))
        fixed = _strip_footnotes(titles)
        for c, t in zip(cands, fixed):
            c.title = t
            c.kind = infer_kind(t)
        out.extend(cands)
    return out, notes


# --------------------------------------------------------------- inline
_NUMBERED_HEADING = re.compile(r"^\s*\d{1,2}\.\s+[A-Z][A-Za-z ,&/]{2,50}$")
_CAPS_HEADING = re.compile(r"^\s*[A-Z][A-Z ,&/:]{4,45}$")


def _evaluation_region(lines: List[str]) -> List[int]:
    """Indices of lines that sit under an evaluation heading (until the next heading,
    at most 80 lines)."""
    idx: List[int] = []
    inside = False
    count = 0
    for i, line in enumerate(lines):
        if _HEADING_EVAL.match(line) and len(line.strip()) < 60:
            inside = True
            count = 0
            continue
        if inside and len(line.strip()) < 60 and not _PCT.search(line) and (
                _HEADING_END.match(line) or _NUMBERED_HEADING.match(line) or _CAPS_HEADING.match(line)):
            inside = False
        if inside:
            count += 1
            if count > 80:
                inside = False
                continue
            idx.append(i)
    return idx


def _inline_candidate(line: str, next_line: str, resolver: DateResolver, in_region: bool) -> Optional[Assessment]:
    raw = line.rstrip()
    if not raw or len(raw) > 220:
        return None
    m = _PCT.search(raw)
    if not m:
        return None
    before = raw[:m.start()]
    # the title ends at ':' / '(' / ' - ' / ' -- ' or at the weight itself
    cut = re.search(r"\s*(?::|\(|\s-\s|\s–\s|--|\s—\s)", before)
    title_raw = before[:cut.start()] if cut else before
    title = clean_title(title_raw)
    if not title or len(title) < 3 or len(title) > 70 or not re.match(r"^[A-Z\d]", title):
        return None
    if re.search(r"\d{1,2}[:.]\d{2}", title) or _POLICY.search(title):
        return None
    if re.match(rf"^\d{{1,2}}\s+{MONTH_RE}\b", title, re.I) or re.match(rf"^{MONTH_RE}\.?\s+\d{{1,2}}\b", title, re.I):
        return None  # a weekly-schedule row, not a list item
    if _POLICY.search(raw) and not re.search(r"\bdue\b", raw, re.I):
        return None
    if not _NOUN.search(title) and not in_region:
        return None
    if not _NOUN.search(title) and not re.match(r"^[A-Z]", title):
        return None
    # a sentence, not a list item: many lowercase words before the weight
    words = title.split()
    if len(words) > 7 or (sum(1 for w in words if w[:1].islower()) > 2 and not _NOUN.search(title)):
        return None
    weight, bonus = parse_weight(raw)
    if weight is None:
        return None
    if weight >= 100 and not re.search(r"final|exam|project|total", title, re.I):
        return None
    if re.match(r"^(note|n\.b\.|important|tip|hint|warning|reminder)s?$", title, re.I) or re.search(r"\b(over|above|exceed)\s+100\s*%", raw, re.I):
        return None
    rest = raw[len(title_raw):]
    rest = re.sub(r"\(\s*\+?\d{1,3}(?:\.\d+)?\s*%[^)]*\)|\+?\d{1,3}(?:\.\d+)?\s*%", " ", rest, count=1)
    if next_line and not _LEADER.match(next_line) and not re.match(r"^\s*[A-Z][^:\n]{2,40}:\s", next_line) \
            and not re.search(r"[.!?:%]\s*$", raw) and len(next_line) < 140 \
            and (_continues(next_line) or (not _PCT.search(next_line) and (
                re.match(r"^\s*[a-z(]", next_line) or re.search(r"[,(]\s*$|\b(and|or|of|the|to|on|by|from)\s*$", raw)))):
        rest = rest + " " + next_line
    dr = resolver.resolve(rest)
    if dr.status == "rule" and not re.search(r"\bdue\b", rest, re.I):
        dr = DateResult(status="missing")
    conf = 0.8 if in_region else 0.6
    if not _NOUN.search(title):
        conf -= 0.15
    return Assessment(title=title, weight=weight, kind=infer_kind(title), date=dr, source="inline",
                      evidence=raw.strip(), is_bonus=bonus, confidence=conf)


def _continues(next_line: str) -> bool:
    """'November 14) you will have a quiz': a closing bracket before any opening one."""
    head = next_line[:40]
    return ")" in head and ("(" not in head or head.index(")") < head.index("("))


def _from_inline(lines: List[str], resolver: DateResolver) -> List[Assessment]:
    region = set(_evaluation_region(lines))
    out: List[Assessment] = []
    for i, line in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        c = _inline_candidate(line, nxt, resolver, i in region)
        if c:
            out.append(c)
    return out


# ------------------------------------------------------- date enrichment
def _schedule_rows(tables, lines: List[str], resolver: DateResolver) -> List[Tuple[DateResult, str]]:
    """(date, text) pairs from weekly-schedule tables ('7 | October 16 | MID-TERM TEST (20%)')."""
    out: List[Tuple[DateResult, str]] = []
    for raw in tables:
        rows = _compress(raw)
        if len(rows) < 3:
            continue
        htext = " ".join(rows[0]).lower()
        if not _SCHEDULE_HEADER.search(htext) or re.search(r"weight|%|worth", htext):
            continue
        for r in rows[1:]:
            cells = [c.replace("\n", " ") for c in r]
            date_cell = next((c for c in cells if re.search(rf"\b{MONTH_RE}\.?\s*\d{{1,2}}", c, re.I)), None)
            if not date_cell:
                continue
            dr = resolver.resolve(date_cell)
            if dr.status != "exact":
                continue
            text = " ".join(c for c in cells if c is not date_cell)
            out.append((dr, text))
    return out


_NOT_A_SCHEDULE_DATE = re.compile(r"\btb[ad]\b|to be (?:determined|announced|scheduled)|registrar|exam(?:ination)?\s+period", re.I)


def _enrich_from_schedule(items: List[Assessment], rows: List[Tuple[DateResult, str]]) -> None:
    """Date a still-undated row from the weekly schedule. A row the outline already leaves to the
    Registrar, a window or TBA keeps that status: the schedule's 'April 7-30 | Final Exam scheduled by
    the registrar' is not a date (D21)."""
    for a in items:
        if a.date.status in ("exact", "recurring", "rule", "registrar", "range", "tba"):
            continue
        best, best_score = None, 0.0
        for dr, text in rows:
            if _NOT_A_SCHEDULE_DATE.search(text) or _NOT_A_SCHEDULE_DATE.search(dr.raw or ""):
                continue
            score = 0.0
            # weight printed in the schedule cell is a strong tie ("MID-TERM TEST (20%)")
            wm = _PCT.search(text)
            if wm and a.weight is not None and abs(float(wm.group(1).lstrip("+")) - a.weight) < 0.01:
                score += 0.5
            elif wm and a.weight is not None:
                score -= 0.5
            nt = norm_title(text)
            na = a.norm()
            if na and na in nt:
                score += 0.6
            else:
                # each title word present
                words = [w for w in na.split() if len(w) > 2]
                if words:
                    hit = sum(1 for w in words if re.search(rf"\b{re.escape(w)}", nt))
                    score += 0.6 * hit / len(words) if hit == len(words) else 0.0
            if score > best_score:
                best, best_score = dr, score
        if best and best_score >= 0.6:
            a.date = DateResult(status="exact", date=best.date, time=best.time or a.date.time,
                                note="Date taken from the weekly schedule", raw=best.raw)
            if a.date.status == "exact" and a.date.time is None:
                a.date.time = None


def _enrich_from_prose(items: List[Assessment], text: str, resolver: DateResolver) -> None:
    """'The Midterm exam will be (tentative) on Thursday March 12 at 2:30-4:20PM',
    'Midterm covers all content covered in weeks 1-6. Date: Feb 13 (tentative)'."""
    flat = re.sub(r"\s+", " ", text)
    for a in items:
        if a.date.status in ("exact", "recurring", "rule", "registrar", "range"):
            continue
        keys = [re.escape(a.title)]
        first = a.title.split()[0].lower() if a.title.split() else ""
        if first in ("midterm", "mid-term"):
            keys.append(r"mid-?term(?:\s+(?:test|exam(?:ination)?))?")
        elif first == "final" and a.kind == "final":
            keys.append(r"final(?:\s+(?:exam(?:ination)?|test))?(?=\s+(?:will|is|covers|takes|date|:|-))")
        key = "|".join(keys)
        for m in re.finditer(rf"\b(?:the\s+)?(?:{key})\b", flat, re.I):
            seg = flat[m.start():m.start() + 130]
            if _MAKEUP.search(flat[max(0, m.start() - 60):m.start()]):
                continue  # 'The make-up exam for the final exam will likely be held in January': not this item's date
            head = m.group(0)
            body = seg[len(head):]
            # one sentence, except that a following "Date: ..." sentence belongs to it
            sent = re.search(r"[.;](?!\s+(?:date|time|due|when)\b)", body, re.I)
            if sent:
                body = body[:sent.start()]
            # stop at the next item's own sentence ("Final Exam 45% Midterm covers ...")
            other = re.search(r"\b(mid-?term|final|assignment|quiz|quizzes|test|lab|labs|project|essay|report)s?\b", body, re.I)
            if other:
                body = body[:other.start()]
            seg = head + body
            if not re.search(r"\b(on|due|held|take place|takes place|scheduled|written|will be|tb[ad]|registrar|date\s*:|exam(?:ination)? period)", seg, re.I):
                continue
            dr = resolver.resolve(seg)
            if dr.status == "exact" and not re.search(r"\bdate\s*(?:and\s+time)?\s*:?\s*(?:is\s+)?tb[ad]\b", seg, re.I):
                dr.note = "Date taken from the course description text"
                a.date = dr
                break
            if dr.status in ("registrar", "tba", "range"):
                a.date = dr
                break
        if a.date.status in ("missing", "tba"):
            _enrich_from_paragraph(a, text, resolver)


_PLURAL_HELD = re.compile(r"\b(?:the\s+|both\s+|all\s+)?(?:(?:term|mid-?term|in-class|online)\s+)?(?P<stem>tests|exams|examinations|midterms|quizzes|assignments|reports|essays|papers|presentations|labs|projects)\b[^.;]{0,60}?\b(?:held|written|take\s+place|scheduled|due|take\s+place)\b[^.;]{0,40}?\b(?:on|for)\s+(?P<dates>[^.;]{6,160}?)(?=[.;]|\s+(?:both|each|the\s+first|the\s+second)\b)", re.I)
_HELD_FROM = re.compile(r"\b(?:both|each|they|all|the\s+tests?)\b[^.;]{0,30}?\b(?:held|written|run|scheduled|take\s+place)\s+(?:from|at|between)\s+(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?(?:\s*(?:-|–|to|and)\s*\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)?)", re.I)


def _enrich_from_plural_sentence(items: List[Assessment], text: str, resolver: DateResolver) -> None:
    """'The tests are tentatively set to be held on October 2nd, 2025 and October 30th, 2025. Both will be
    held from 1:30 pm to 3:30 pm': one sentence names every date of a numbered family ('Term Test 1',
    'Term Test 2'), in order (MSE 2214, D24). Only fires when the count of dates equals the count of
    still-undated members, so nothing is guessed."""
    flat = re.sub(r"\s+", " ", text)
    families: Dict[str, List[Assessment]] = {}
    for a in items:
        if a.date.status not in ("missing", "tba"):
            continue
        stem = _noun_stem(a.title)
        if stem and _numbering(a.norm()):
            families.setdefault(stem, []).append(a)
    for stem, members in families.items():
        if len(members) < 2:
            continue
        members.sort(key=lambda a: int((_numbering(a.norm()) or ["0"])[0]) if (_numbering(a.norm()) or ["0"])[0].isdigit() else 0)
        for m in _PLURAL_HELD.finditer(flat):
            if _noun_stem(m.group("stem")) != stem:
                continue
            dates = [d for _, d in resolver._find_dates(m.group("dates"))]
            if len(dates) != len(members) or len(set(dates)) != len(dates):
                continue
            tail = flat[m.end():m.end() + 160]
            t = None
            tm = _HELD_FROM.search(tail) or _HELD_FROM.search(m.group(0))
            if tm:
                t, _ = parse_time_span(tm.group(1))
            if t is None:
                t, _ = parse_time_span(m.group("dates"))
            for a, d in zip(members, sorted(dates)):
                a.date = DateResult(status="exact", date=d, time=t, raw=m.group(0),
                                    note="Date taken from the course description text" + (" (tentative)" if re.search(r"tentativ", m.group(0), re.I) else ""))
                a.evidence = f"{a.evidence} | {m.group(0).strip()}"
            break


_MAKEUP = re.compile(r"\bmake-?up\b|\balternative\b|\bdeferred\b|\bspecial\s+exam", re.I)

_SUBMIT_DATE = re.compile(rf"\b(?:submit(?:ted)?|hand(?:ed)?\s+in|due|deadline|upload(?:ed)?)\b[\s\S]{{0,80}}?\b(?:on|by|before)\s+((?:{MONTH_RE})\.?\s*\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s*\d{{4}})?)", re.I)


def _enrich_from_paragraph(a: Assessment, text: str, resolver: DateResolver) -> None:
    """A paragraph headed by the title ('Peer Evaluations: You will be asked ...') that says
    'submit ... on Dec 8th' within its first 700 characters."""
    key = re.escape(a.title.rstrip("s"))
    for m in re.finditer(rf"^\s*{key}s?\s*:", text, re.I | re.M):
        para = text[m.end():m.end() + 700]
        # stop at the next paragraph heading
        nxt = re.search(r"\n[A-Z][A-Za-z &]{3,40}:\s", para)
        if nxt:
            para = para[:nxt.start()]
        sm = _SUBMIT_DATE.search(para)
        if not sm:
            continue
        dr = resolver.resolve(sm.group(1))
        if dr.status == "exact":
            dr.note = "Date taken from the paragraph describing this item"
            a.date = dr
            return


# ------------------------------------------------------------ assembly
def _dedupe(items: List[Assessment]) -> List[Assessment]:
    out: List[Assessment] = []
    for a in items:
        dup = None
        for b in out:
            same_digits = _numbering(a.norm()) == _numbering(b.norm())
            same_title = a.norm() == b.norm() or (same_digits and difflib.SequenceMatcher(None, a.norm(), b.norm()).ratio() >= 0.9)
            if same_title and (a.weight == b.weight or a.weight is None or b.weight is None):
                dup = b
                break
        if dup is None:
            out.append(a)
            continue
        # keep the better-dated / better-sourced copy
        if dup.date.status not in ("exact", "recurring") and a.date.status in ("exact", "recurring", "registrar", "range", "tba"):
            dup.date = a.date
        if dup.weight is None:
            dup.weight = a.weight
    return out


_ORDINALS = {"first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5", "sixth": "6", "seventh": "7", "eighth": "8"}


def _numbering(norm: str) -> List[str]:
    """Digits, ordinal words, trailing roman numerals and single letters that distinguish
    'Reflection I' from 'Reflection II' and 'First test' from 'Second test'."""
    toks = re.findall(r"\d+", norm) + [_ORDINALS[w] for w in norm.split() if w in _ORDINALS]
    m = re.search(r"\b([ivx]{1,4}|[a-h])$", norm)
    if m:
        toks.append(m.group(1))
    return toks


def _drop_groups(items: List[Assessment]) -> List[Assessment]:
    """'3 Assignments 25%' when 'Assignment 1..3' sum to 25; 'Inquiry (40%)' when the
    following items sum to 40."""
    keep = list(items)
    for a in items:
        m = _GROUP_COUNT.match(a.title)
        if m and a.weight is not None:
            n, noun = int(m.group(1)), m.group(2).strip().lower()
            members = [b for b in items if b is not a and re.match(rf"^{re.escape(noun)}\s*\d+$", b.norm())]
            if len(members) == n and abs(sum(b.weight or 0 for b in members) - a.weight) <= 1.0:
                a.is_group = True
        if not a.is_group and a.source == "inline" and a.weight is not None and a.weight >= 20 \
                and a.date.status in ("missing", "tba"):
            # "V. Inquiry (40%)" followed by "* Inquiry Update Reports (3%)" ... summing to 40
            i = items.index(a)
            lead = _leader_style(a.evidence)
            tail = [b for b in items[i + 1:] if not b.is_bonus]
            acc = 0.0
            for k, b in enumerate(tail):
                if b.source != "inline" or _leader_style(b.evidence) == lead:
                    break
                acc += b.weight or 0
                if abs(acc - a.weight) < 0.01 and k >= 1:
                    a.is_group = True
                    break
                if acc > a.weight:
                    break
    return [a for a in keep if not a.is_group]


def _leader_style(evidence: str) -> str:
    m = _LEADER.match(evidence or "")
    if not m:
        return "none"
    lead = m.group(0).strip()
    if re.match(r"^[ivx]+\.$", lead, re.I):
        return "roman"
    if re.match(r"^\d+\.$", lead):
        return "number"
    return "bullet"


_NUM_TABLE_HEADER = re.compile(r"%\s*of\s*(?:total|final|course)|\bweight|\bmethod\s*1|\bmarks?\b|\bvalue\b", re.I)
_NUM_ROW = re.compile(r"^(?P<body>.*?\S)\s+(?P<w>\d{1,3}(?:\.\d+)?)(?:\s+\d{1,3}(?:\.\d+)?)?\s*$")


def _from_numeric_text_table(lines: List[str], resolver: DateResolver) -> List[Assessment]:
    """Evaluation tables printed as text with a bare-number weight column:
    'Component Notes % of total grade' then 'Midterm Test Saturday, March 2, 7:30 – 9:30 PM 32.5 17.5'."""
    out: List[Assessment] = []
    region = _evaluation_region(lines)
    if not region:
        return out
    start = region[0]
    header_at = None
    for i in region[:15]:
        if _NUM_TABLE_HEADER.search(lines[i]) and re.search(r"\bcomponent|\bassessment|\bitem|\belement|\bnotes?\b", lines[i], re.I):
            header_at = i
            break
    if header_at is None:
        return out
    pending_title: Optional[str] = None
    for i in range(header_at + 1, min(header_at + 30, len(lines))):
        line = lines[i].rstrip()
        if not line.strip():
            continue
        if _HEADING_END.match(line) or _NUMBERED_HEADING.match(line) or re.search(r"requirements? for passing|^\s*total\b", line, re.I):
            break
        m = _NUM_ROW.match(line)
        if not m:
            # a title on its own line whose weight comes on a later line ("Final Exam 45" after "TBA by the Registrar")
            if _NOUN.search(line) and len(line) < 40 and re.match(r"^[A-Z]", line.strip()) and not _POLICY.search(line):
                pending_title = clean_title(line)
            continue
        body, w = m.group("body"), float(m.group("w"))
        if w <= 0 or w > 100 or re.search(r"\b(20\d\d|19\d\d)$", body):
            continue
        nm = _NOUN.search(body)
        if not nm:
            if pending_title:
                title, rest = pending_title, body
            else:
                continue
        else:
            # title = leading words up to the first assessment noun, plus following nouns ("Midterm Test") or "of X"
            end = nm.end()
            while True:
                nxt = re.match(r"\s+(?:of\s+)?([A-Z][A-Za-z]+)", body[end:])
                if nxt and (_NOUN.search(nxt.group(1)) or re.match(r"\s+of\s+", body[end:])):
                    end += nxt.end()
                    continue
                break
            title = body[:end]
            rest = body[end:]
            if re.search(r"[a-z]", title[:1]) or len(title) > 45:
                continue
        pending_title = None
        title = clean_title(title)
        # notes that wrapped onto the lines above this row ("Saturday, October 22 7:30-9:30 p.m." / "Test of Knowledge 25")
        look_back = " ".join(l for l in lines[max(header_at + 1, i - 2):i] if not _NUM_ROW.match(l) and not _NOUN.search(l))
        dr = resolver.resolve(rest)
        if dr.status == "missing" and look_back.strip():
            dr = resolver.resolve(look_back)
        out.append(Assessment(title=title, weight=w, kind=infer_kind(title), date=dr, source="inline",
                              evidence=line.strip(), confidence=0.7))
    return out



# ------------------------------------------------- dated bullet items (D14)
_WORD_NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                 "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15}
_BULLET_LEAD = re.compile(r"^\s*(?:[•*\-–—▪●○]|o(?=\s)|\d{1,2}[.)]|[a-z][.)])\s*")
# "- Assignment 1: From the content ...", "- Midterm exam: Weeks 1–6 (Oct 21, ...)", "- Project: Submission deadline: Dec 6"
_ITEM_HEAD = re.compile(r"^([A-Z][A-Za-z#\-]*(?:\s+[A-Za-z#\-]*\d*[A-Za-z]?){0,3}?)\s*:\s*(.+)$")
_DEADLINE_KEY = re.compile(r"\b(?:submission\s+deadline|deadline|due\s+date|due|submit(?:ted)?\s+by|hand(?:ed)?\s+in\s+by)\s*[:\-–]?\s*(?:on\s+|by\s+|at\s+)?", re.I)
_SEGMENT_END = re.compile(r"[;)]|,?\s*\b(?:peer\s+review|optional|available|release[ds]?|posted|open(?:s|ed)?)\b", re.I)
_PAREN = re.compile(r"\(([^()]*)\)")


@dataclass
class DatedItem:
    title: str
    date: DateResult
    line: str


def _join_wrapped(lines: List[str], i: int) -> str:
    """A bullet whose parenthesis (or 'deadline:') runs onto the next line(s)."""
    text = lines[i].rstrip()
    for k in (1, 2):
        if i + k >= len(lines):
            break
        unbalanced = text.count("(") > text.count(")")
        dangling = bool(re.search(r"(?:deadline|due|at|on|by)\s*:?\s*$", text, re.I))
        nxt = lines[i + k].strip()
        if not (unbalanced or dangling) or not nxt or _BULLET_LEAD.match(lines[i + k]) and _ITEM_HEAD.match(_BULLET_LEAD.sub("", lines[i + k])):
            break
        text = text + " " + nxt
    return text


def _from_dated_bullets(lines: List[str], resolver: DateResolver) -> List[DatedItem]:
    out: List[DatedItem] = []
    for i, raw in enumerate(lines):
        stripped = _BULLET_LEAD.sub("", raw)
        m = _ITEM_HEAD.match(stripped)
        if not m:
            continue
        title = clean_title(m.group(1))
        if not title or len(title) > 30 or not _NOUN.search(title) or _PCT.search(title) or _POLICY.search(title):
            continue
        if re.match(r"^(?:week|lecture|class|chapter|unit|module|topic|reading)s?\b", title, re.I):
            continue
        body = _join_wrapped(lines, i)
        body = _BULLET_LEAD.sub("", body)
        body = body[len(m.group(1)):].lstrip(" :")
        dr = _date_in_bullet(body, resolver)
        if dr is None:
            continue
        out.append(DatedItem(title=title, date=dr, line=raw.strip()))
    return out


def _date_in_bullet(body: str, resolver: DateResolver) -> Optional[DateResult]:
    flat = re.sub(r"\s+", " ", body)
    km = _DEADLINE_KEY.search(flat)
    if km:
        seg = flat[km.end():]
        end = _SEGMENT_END.search(seg)
        seg = seg[:end.start()] if end else seg
        dr = resolver.resolve(seg)
        if dr.status == "recurring" and dr.dates:
            dr = DateResult(status="exact", date=dr.dates[0], time=dr.time, raw=seg)
        if dr.status in ("exact", "tba"):
            return dr
    for pm in _PAREN.finditer(flat):
        inner = pm.group(1)
        if re.search(rf"\b{MONTH_RE}\b", inner, re.I) or re.search(r"\btb[ad]\b", inner, re.I):
            dr = resolver.resolve(inner)
            if dr.status in ("exact", "tba", "registrar", "range"):
                return dr
    if re.search(r"\btb[ad]\b", flat, re.I) and not re.search(rf"\b{MONTH_RE}\b", flat, re.I):
        return DateResult(status="tba", raw=flat, note="Outline says the date is TBA")
    return None


def _noun_stem(title: str) -> str:
    m = _NOUN.search(title or "")
    if not m:
        return ""
    w = m.group(0).lower()
    w = re.sub(r"zzes$", "z", w)
    w = re.sub(r"ies$", "y", w)
    return w.rstrip("s")


def _same_item(a: Assessment, d: DatedItem) -> bool:
    if _numbering(a.norm()) != _numbering(norm_title(d.title)):
        return False
    ka, kd = a.kind, infer_kind(d.title)
    if ka == kd and _noun_stem(a.title) == _noun_stem(d.title):
        return True
    if {ka, kd} <= {"midterm", "test"} and re.search(r"mid-?term", a.title + d.title, re.I):
        return True
    return difflib.SequenceMatcher(None, a.norm(), norm_title(d.title)).ratio() >= 0.75


def _group_members(group: Assessment, dated: List[DatedItem]) -> List[DatedItem]:
    stem = _noun_stem(group.title)
    if not stem or not re.search(rf"\b{re.escape(stem)}(?:s|zes|es)?\b", norm_title(group.title)):
        return []
    if not re.search(r"s\b", norm_title(group.title).split()[-1] if norm_title(group.title) else "") and not re.search(r"\d", group.evidence):
        return []
    members = [d for d in dated if _noun_stem(d.title) == stem and re.search(r"\d", d.title) and d.date.status == "exact"]
    seen, uniq = set(), []
    for d in members:
        key = norm_title(d.title)
        if key not in seen:
            seen.add(key); uniq.append(d)
    return uniq


def _stated_count(evidence: str, stem: str) -> Optional[int]:
    m = re.search(rf"\b(\d{{1,2}}|{'|'.join(_WORD_NUMBERS)})\s+(?:[a-z\-]+\s+)?{re.escape(stem)}(?:s|zes|es)?\b", evidence, re.I)
    if not m:
        return None
    w = m.group(1).lower()
    return int(w) if w.isdigit() else _WORD_NUMBERS.get(w)


def _split_weights(group: Assessment, n: int) -> Optional[List[float]]:
    """'(three assignments: the first one 5%, and the remaining two, 6% each)' -> [5, 6, 6];
    '(four quizzes, 2% each)' -> [2, 2, 2, 2]; otherwise an equal split of the group weight."""
    ev = group.evidence.replace("\n", " ")
    total = group.weight or 0
    m = re.search(r"first\s+(?:one|\w+)\s+(\d{1,3}(?:\.\d+)?)\s*%.*?remaining\s+(?:\w+),?\s+(\d{1,3}(?:\.\d+)?)\s*%\s*each", ev, re.I)
    if m:
        ws = [float(m.group(1))] + [float(m.group(2))] * (n - 1)
        if abs(sum(ws) - total) <= 0.5:
            return ws
    m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%\s*each", ev, re.I)
    if m:
        each = float(m.group(1))
        if abs(each * n - total) <= 0.5:
            return [each] * n
    if total and n:
        each = round(total / n, 2)
        ws = [each] * n
        ws[-1] = round(total - each * (n - 1), 2)
        return ws
    return None


def _apply_dated_bullets(items: List[Assessment], dated: List[DatedItem]) -> List[Assessment]:
    """Date existing rows from their bullet ('Project: Submission deadline: Dec 6'), and split a
    group row ('Assignments 17% (three assignments ...)') into its dated members."""
    if not dated:
        return items
    out: List[Assessment] = []
    for a in items:
        if a.date.status in ("exact", "recurring"):
            out.append(a); continue
        hit = next((d for d in dated if _same_item(a, d)), None) if a.date.status in ("missing", "tba") else None
        if hit and (hit.date.status == "exact" or a.date.status == "missing"):
            a.date = DateResult(status=hit.date.status, date=hit.date.date, time=hit.date.time,
                                end_time=hit.date.end_time, window=hit.date.window, raw=hit.line,
                                note="Date taken from the assessment list" if hit.date.status == "exact" else hit.date.note)
            a.evidence = f"{a.evidence} | {hit.line}"
            if hit.date.status == "exact":
                a.confidence = max(a.confidence, 0.8)
        out.append(a)
    items = out
    out = []
    for a in items:
        members = _group_members(a, dated) if a.date.status not in ("exact", "recurring") and a.weight else []
        stated = _stated_count(a.evidence, _noun_stem(a.title)) if members else None
        if len(members) >= 2 and (stated is None or stated == len(members)) \
                and not any(_same_item(b, m) for b in items if b is not a for m in members):
            ws = _split_weights(a, len(members))
            if ws:
                for d, w in zip(members, ws):
                    out.append(Assessment(title=d.title, weight=w, kind=infer_kind(d.title), date=d.date, source="inline",
                                          evidence=f"{a.evidence} | {d.line}", confidence=0.8))
                continue
        out.append(a)
    return out


# ------------------------------------------------ explicit date lists (D15)
_DATE_LIST = re.compile(rf"\b({MONTH_RE})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?(?!\d)((?:\s*(?:,|&|and|,\s*and)\s*(?:and\s+)?\d{{1,2}}(?:st|nd|rd|th)?(?![\d:]))*)", re.I)


def _date_list(segment: str, resolver: DateResolver) -> List[date]:
    """'September 12, 19, 26; October 10, 17, 31; and November 14' -> seven dates."""
    found: List[date] = []
    for m in _DATE_LIST.finditer(segment):
        month = m.group(1)
        days = [int(m.group(2))] + [int(x) for x in re.findall(r"\d{1,2}", m.group(3))]
        for d in days:
            r = resolver.resolve(f"{month} {d}")
            if r.status == "exact" and r.date:
                found.append(r.date)
    return sorted(set(found))


def _explicit_dates_for(a: Assessment, text: str, resolver: DateResolver) -> Optional[Tuple[List[date], Optional[time]]]:
    """A heading 'Quizzes:' followed (within a few lines) by a list of at least three dates."""
    stem = _noun_stem(a.title)
    if not stem:
        return None
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if not re.match(rf"^\s*(?:weekly\s+|online\s+|in-class\s+)?{re.escape(stem)}(?:s|zes|es)?\s*(?:\(.*?\))?\s*:\s*$", line, re.I):
            continue
        block = " ".join(lines[i + 1:i + 5])
        stop = re.search(r"\n\s*[A-Z][A-Za-z ]{2,30}:\s*$", "\n".join(lines[i + 1:i + 5]), re.M)
        if stop:
            block = "\n".join(lines[i + 1:i + 5])[:stop.start()].replace("\n", " ")
        dates = _date_list(block, resolver)
        if len(dates) >= 3:
            t, _ = parse_time_span(block)
            return dates, t
    return None


def _reconcile_recurring(items: List[Assessment], text: str, resolver: DateResolver) -> None:
    """An 'every Friday' expansion yields to the outline's own date list; when the outline states a
    count that the expansion does not match and lists no dates, no dates are invented."""
    for a in items:
        if a.date.status != "recurring" or not a.date.note.startswith("Every "):
            continue
        listed = _explicit_dates_for(a, text, resolver)
        if listed:
            dates, t = listed
            a.date = DateResult(status="recurring", dates=dates, time=t or a.date.time, raw=a.date.raw,
                                note=f"{len(dates)} dates listed in the outline ({dates[0]:%b %-d} – {dates[-1]:%b %-d, %Y})")
            continue
        stem = _noun_stem(a.title)
        n = None
        for m in re.finditer(rf"\b(?:total\s+of|there\s+will\s+be(?:\s+a\s+total\s+of)?)\s+(\d{{1,2}}|{'|'.join(_WORD_NUMBERS)})\s+{re.escape(stem)}(?:s|zes|es)?\b", text, re.I):
            w = m.group(1).lower()
            n = int(w) if w.isdigit() else _WORD_NUMBERS.get(w)
            break
        if n and a.date.dates and n != len(a.date.dates):
            first, last = a.date.dates[0], a.date.dates[-1]
            a.date = DateResult(status="range", window=(first, last), raw=a.date.raw,
                                note=f"Outline says {n} {stem}s between {first:%b %-d} and {last:%b %-d, %Y} but the weekly rule "
                                     f"gives {len(a.date.dates)} dates; it does not list them, so add the {n} dates yourself.")



# ------------------------------------- section-dependent dates and chapter lists (D14, MOS)
_SECTION_DATE_LINE = re.compile(r"^\s*section\s+(\d{3})\s*[:\-–]\s*(.+)$", re.I)
_LIST_DUE_LINE = re.compile(rf"^\s*(?:[•*\-–—▪●○]\s*)?(.{{0,70}}?\b(?:{NOUNS})s?)\s*:\s*due\s+(.+)$", re.I)


def _enrich_section_dependent(items: List[Assessment], lines: List[str], resolver: DateResolver) -> None:
    """'Exam #1 (during class time) = 31%' followed by 'Section 001: Tues Oct 7, 2pm-4pm ...' lines:
    the date depends on the section, so the row gets the window and a note, never one of the dates."""
    for a in items:
        if a.date.status != "missing":
            continue
        head = a.evidence.split(" | ")[0].strip()
        for i, line in enumerate(lines):
            if not head or head not in line:
                continue
            found = []
            for nxt in lines[i + 1:i + 6]:
                sm = _SECTION_DATE_LINE.match(nxt)
                if not sm:
                    break
                dr = resolver.resolve(sm.group(2))
                if dr.status == "exact" and dr.date:
                    found.append((sm.group(1), dr))
            if len(found) >= 2:
                ds = sorted(d.date for _, d in found)
                parts = ", ".join(f"section {sid} {d.date:%b %-d}" + (f" {d.time:%-I:%M %p}" if d.time else "") for sid, d in found)
                a.date = DateResult(status="range", window=(ds[0], ds[-1]), raw=a.evidence,
                                    note=f"Date depends on your section ({parts}); pick the date for your section with the calendar icon.")
                break


def _enrich_chapter_lists(items: List[Assessment], lines: List[str], resolver: DateResolver) -> None:
    """'Chapter 1, Chapter 2, Chapter 3 assignments: due Sept 19 @ 11:59pm' x 8 lines -> the
    'Chapter Assignments' row becomes recurring on those eight dates."""
    per_stem: Dict[str, List[Tuple[date, Optional[time]]]] = {}
    for line in lines:
        m = _LIST_DUE_LINE.match(line)
        if not m:
            continue
        dr = resolver.resolve(m.group(2))
        if dr.status == "exact" and dr.date:
            per_stem.setdefault(_noun_stem(m.group(1)), []).append((dr.date, dr.time))
    for a in items:
        if a.date.status != "missing":
            continue
        hits = per_stem.get(_noun_stem(a.title), [])
        if len(hits) >= 3:
            ds = sorted({d for d, _ in hits})
            t = next((t for _, t in hits if t), None)
            a.date = DateResult(status="recurring", dates=ds, time=t, raw=a.evidence,
                                note=f"{len(ds)} due dates listed in the outline ({ds[0]:%b %-d} – {ds[-1]:%b %-d, %Y})")

def extract_assessments(pages_text: Sequence[Tuple[int, str]],
                        tables: Sequence[Sequence[Sequence[Optional[str]]]],
                        term: TermInfo) -> Tuple[List[Assessment], List[str]]:
    resolver = DateResolver(term.start, term.end, term.exam_periods, term.year_hints, term.reading_weeks)
    text = "\n".join(t for _, t in pages_text)
    lines = text.split("\n")
    notes: List[str] = []

    table_items, tnotes = _from_tables(tables, resolver)
    notes += tnotes
    inline_items = _from_inline(lines, resolver)

    table_total = sum(a.weight or 0 for a in table_items if not a.is_bonus)
    inline_total = sum(a.weight or 0 for a in inline_items if not a.is_bonus)

    inline_items = [a for a in inline_items if not _is_table_echo(a, table_items)]
    if table_items and 85 <= table_total <= 115:
        extra = [a for a in inline_items if _is_new(a, table_items) and a.weight is not None]
        # inline rows outside the table join when they carry a date, or when they fill the gap to 100
        chosen = []
        running = table_total
        for a in extra:
            if a.date.status == "exact" or (a.is_bonus is False and _NOUN.search(a.title)
                                            and abs(100 - (running + a.weight)) < abs(100 - running) - 0.5):
                chosen.append(a)
                running += 0 if a.is_bonus else a.weight
        items = table_items + chosen
    elif table_items and not inline_items:
        items = table_items
    elif inline_items and not table_items:
        items = inline_items
    else:
        items = table_items + inline_items

    if sum(a.weight or 0 for a in items if not a.is_bonus) < 60:
        numeric = _from_numeric_text_table(lines, resolver)
        if sum(a.weight or 0 for a in numeric) > sum(a.weight or 0 for a in items if not a.is_bonus):
            items = numeric + [a for a in items if a.is_bonus]

    items = _dedupe(items)
    items = _apply_dated_bullets(items, _from_dated_bullets(lines, resolver))
    items = _drop_groups(items)

    # a weight far above 100 after grouping: the lowest-confidence duplicates go
    total = sum(a.weight or 0 for a in items if not a.is_bonus)
    if total > 118 and any(a.confidence < 0.7 for a in items):
        items = _trim_to_hundred(items)

    _enrich_from_schedule(items, _schedule_rows(tables, lines, resolver))
    _enrich_from_prose(items, text, resolver)
    _enrich_from_plural_sentence(items, text, resolver)
    _enrich_section_dependent(items, lines, resolver)
    _enrich_chapter_lists(items, lines, resolver)
    _reconcile_recurring(items, text, resolver)

    for a in items:
        if a.date.status == "exact" and a.date.time is None:
            a.date.time = _default_time(text, a)
    return items, notes


def _is_table_echo(a: Assessment, table_items: List[Assessment]) -> bool:
    """pdfplumber's page text repeats each table row as one line ('PeerWise Write 2
    multiple-choice 2% Author: Mon, Oct. 27th'); such a line is not a second assessment."""
    words = [w for w in re.findall(r"[a-z0-9&]+", a.title.lower()) if len(w) > 1]
    if not words:
        return False
    for t in table_items:
        if t.weight != a.weight:
            continue
        ev = t.evidence.lower()
        if all(re.search(rf"\b{re.escape(w)}\b", ev) for w in words):
            return True
    return False


def _is_new(a: Assessment, existing: List[Assessment]) -> bool:
    return all(difflib.SequenceMatcher(None, a.norm(), b.norm()).ratio() < 0.75 for b in existing)


def _trim_to_hundred(items: List[Assessment]) -> List[Assessment]:
    """Drop the least trusted candidates (inline lines without an assessment noun first) until
    the total is back near 100; rows from a table and confident list items are never dropped."""
    core = [a for a in items if not a.is_bonus]
    total = sum(a.weight or 0 for a in core)
    for a in sorted(core, key=lambda a: (a.confidence, a.weight or 0)):
        if total <= 112 or a.confidence >= 0.7:
            break
        core.remove(a)
        total -= a.weight or 0
    return [a for a in items if a in core or a.is_bonus]


_DEFAULT_TIME = re.compile(r"\b(?:all\s+)?(?:assignments?|submissions?|work|deliverables)\s+(?:are|is)\s+due\s+(?:at|by)\s+(\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?)", re.I)


def _default_time(text: str, a: Assessment) -> Optional[time]:
    if a.kind in ("assignment", "project", "lab_report", "presentation", "other", "quiz"):
        m = _DEFAULT_TIME.search(text)
        if m:
            t, _ = parse_time_span(m.group(1))
            return t
    return None
