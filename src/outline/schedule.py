"""Lecture / lab / tutorial slots, from tables and from prose.

Shapes seen in Western outlines:
  table row     Lecture | Thursday | 10:30-12:20 | SSC-2050
  prose         Lectures: MWF 12:30 - 1:20 pm in AHB-1R40.
                Tutorials: W 5:30 - 6:20 pm via zoom (...)
                LECTURE: Friday 1.30 pm-2.30 pm HSB-236 (weekly)
                Class Meetings: Tuesday 2:30-3:30pm, Thursday 2:30-4:30pm  + Location: MC-110
                Lecture M/W/F 10:30 – 11:30 AM
  weekly table  every "Date" is a Thursday -> lecture on Thursday, time unknown
A component that has no day or time (ECE "LAB: 3hrs/session (weekly); 10 sessions")
becomes a note for the review page, never a slot.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, time
from typing import Dict, List, Optional, Sequence, Tuple

from .dates import MONTHS, MONTH_RE, WEEKDAYS, WEEKDAY_RE, parse_time_span
from .tables import compress_table

KINDS = {
    "lecture": r"lectures?|lec\b|class(?:es)?(?:\s+meetings?)?|seminars?",
    "lab": r"labs?|laborator(?:y|ies)",
    "tutorial": r"tutorials?|tut\b",
}
_KIND_RE = re.compile(r"^\s*(?:(lectures?|lec|class(?:es)?(?:\s+meetings?)?|seminars?)|(labs?|laborator(?:y|ies))|(tutorials?|tut))\b[^\n]*?[:\s]", re.I)
_OFFICE = re.compile(r"office\s+hours?", re.I)
_TIME_ANY = re.compile(r"\d{1,2}[:.]\d{2}\s*(?:[ap]\.?m\.?)?\s*[-–]|\d{1,2}\s*[ap]\.?m\.?\s*[-–]", re.I)
_LOCATION = re.compile(r"\b(?:in|at|room|location:?)\s+([A-Z]{2,5}[- ]?\d{1,4}[A-Z]?\d{0,3})\b|\b([A-Z]{2,5}-\d{1,4}[A-Z]?\d{0,3})\b|\b([A-Z]{2,5}\s\d{3,4})\b(?=\s*(?:\(|$|\.|,|;))")
_ZOOM = re.compile(r"\bzoom\b|\bonline\b|\bvirtual\b", re.I)
_DAY_TOKENS = re.compile(
    rf"\b(?:{WEEKDAY_RE})s?\b(?:\s*(?:,|/|&|and)\s*(?:{WEEKDAY_RE})s?\b)*|\b(?:M|T|W|Th|R|F)(?:\s*/\s*(?:M|T|W|Th|R|F))+\b|\b(?:M|T|W|Th|R|F){{2,5}}\b|\bTTh\b|\bMWF\b|\bMW\b|\bWF\b|\bTR\b|\b(?:M|T|W|Th|R|F)\b(?=\s*\d{{1,2}}[:.]\d{{2}})",
    re.I)


@dataclass
class Slot:
    kind: str                     # lecture | lab | tutorial
    days: List[int]               # 0 = Monday
    start: Optional[time]
    end: Optional[time]
    location: Optional[str] = None
    section_id: str = ""
    note: str = ""

    def key(self):
        return (self.kind, tuple(self.days), self.start, self.end)


def parse_days(text: str) -> List[int]:
    """'MWF' -> [0,2,4]; 'M/W/F' -> [0,2,4]; 'Tuesday' -> [1]; 'TTh' -> [1,3]; 'Mon, Wed' -> [0,2]."""
    t = text.strip()
    days: List[int] = []
    for m in re.finditer(rf"\b({WEEKDAY_RE})s?\b", t, re.I):
        d = WEEKDAYS.get(m.group(1).lower())
        if d is not None and d not in days:
            days.append(d)
    if days:
        return sorted(days)
    compact = re.sub(r"[\s/,&]+", "", t)
    if not re.fullmatch(r"(?:M|T|W|Th|R|F|S|Su){1,6}", compact):
        return []
    i = 0
    while i < len(compact):
        two = compact[i:i + 2]
        if two == "Th":
            days.append(3); i += 2; continue
        if two == "Su":
            days.append(6); i += 2; continue
        c = compact[i]
        d = {"M": 0, "T": 1, "W": 2, "R": 3, "F": 4, "S": 5}.get(c)
        if d is not None:
            days.append(d)
        i += 1
    return sorted(set(days))


def _kind_of(label: str) -> Optional[str]:
    low = label.lower()
    for kind, pat in KINDS.items():
        if re.search(rf"\b(?:{pat})", low):
            return kind
    return None


def _location_in(text: str) -> Optional[str]:
    if _ZOOM.search(text) and not re.search(r"[A-Z]{2,5}-\d", text):
        return "Zoom"
    m = _LOCATION.search(text)
    if m:
        return (m.group(1) or m.group(2) or m.group(3)).replace(" ", "-").upper() if m.group(3) else (m.group(1) or m.group(2))
    return None


_SECTION_SPLIT = re.compile(r"(?=\bsection\s+\d{3}\b)", re.I)


def _slots_from_fragment(kind: str, fragment: str, default_location: Optional[str] = None) -> List[Slot]:
    """One label's text ('Tuesday 2:30-3:30pm, Thursday 2:30-4:30pm HSB-236') -> slots.
    'Mondays Section 002 11:30 AM- 1:20 PM MSB-M117 Section 003 1:30-3:20 PM MSB-M117' -> one slot
    per section, later sections inheriting the day."""
    frag = fragment.replace("–", "-").replace("—", "-").replace("\n", " ")
    pieces_by_section = [p for p in _SECTION_SPLIT.split(frag) if p.strip()]
    if len(pieces_by_section) > 1:
        out: List[Slot] = []
        carried_days: List[int] = []
        if not re.match(r"\s*section\s+\d{3}", pieces_by_section[0], re.I):
            head = pieces_by_section[0]
            carried_days = parse_days(" ".join(m.group(0) for m in _DAY_TOKENS.finditer(head)))
            pieces_by_section = pieces_by_section[1:]
        for piece in pieces_by_section:
            sid = re.match(r"\s*section\s+(\d{3})", piece, re.I)
            body = piece[sid.end():] if sid else piece
            own = parse_days(" ".join(m.group(0) for m in _DAY_TOKENS.finditer(body)))
            days = own or carried_days
            if own:
                carried_days = own
            start, end = parse_time_span(body)
            if days and start and end:
                out.append(Slot(kind=kind, days=days, start=start, end=end,
                                location=_location_in(body) or default_location, section_id=sid.group(1) if sid else ""))
        if out:
            return out
    location = _location_in(frag) or default_location
    out = []
    # split into day-group + time pieces: find every day token followed by a time span
    pieces = []
    for dm in _DAY_TOKENS.finditer(frag):
        days = parse_days(dm.group(0))
        if not days:
            continue
        tail = frag[dm.end():]
        nxt = _DAY_TOKENS.search(tail)
        # stop at the next day token that itself has a time after it
        seg = tail[:nxt.start()] if nxt and parse_days(nxt.group(0)) and _TIME_ANY.search(tail[nxt.end():]) else tail
        start, end = parse_time_span(seg)
        pieces.append((days, start, end))
    if not pieces:
        return out
    # "Tuesday 2:30-3:30pm, Thursday 2:30-4:30pm": two pieces with their own times
    # "MWF 12:30 - 1:20 pm": one piece
    # "Monday and Wednesday 10:30-11:30": one token group, one time
    for days, start, end in pieces:
        if start is None:
            continue
        if end is None:
            continue
        out.append(Slot(kind=kind, days=days, start=start, end=end, location=location))
    return out


def _from_tables(tables: Sequence[Sequence[Sequence[Optional[str]]]]) -> List[Slot]:
    out: List[Slot] = []
    for raw in tables:
        table = compress_table(raw)
        if not table or len(table) < 2:
            continue
        header = [str(c or "").strip().lower() for c in table[0]]
        htext = " ".join(header)
        if not (re.search(r"\b(component|day|time|date\(s\)|type|section)\b", htext) and re.search(r"\b(time|day)", htext)):
            continue
        if re.search(r"\b(assessment|weight|due)\b", htext):
            continue
        header_kind = _kind_of(htext) if re.search(r"^(lecture|lab|tutorial)", htext) else None
        cols = {}
        for i, h in enumerate(header):
            if re.search(r"component|type|activity|section", h) and "comp" not in cols:
                cols["comp"] = i
            elif re.search(r"\bday|date", h) and "day" not in cols:
                cols["day"] = i
            elif "time" in h and "time" not in cols:
                cols["time"] = i
            elif re.search(r"location|room|where|place", h) and "loc" not in cols:
                cols["loc"] = i
        if "comp" not in cols:
            cols["comp"] = 0
        for row in table[1:]:
            cells = [str(c or "").replace("\n", " ").strip() for c in row]
            if len(cells) <= cols["comp"]:
                continue
            kind = _kind_of(cells[cols["comp"]]) or header_kind
            if not kind:
                continue
            day_txt = cells[cols["day"]] if "day" in cols and len(cells) > cols["day"] else ""
            time_txt = cells[cols["time"]] if "time" in cols and len(cells) > cols["time"] else ""
            loc = cells[cols["loc"]] if "loc" in cols and len(cells) > cols["loc"] else ""
            frag = f"{day_txt} {time_txt}"
            if not day_txt or not time_txt:
                frag = " ".join(cells[1:])
            slots = _slots_from_fragment(kind, frag, default_location=(loc or None))
            if not slots and day_txt and time_txt:
                days = parse_days(day_txt)
                start, end = parse_time_span(time_txt.replace("–", "-"))
                if days and start and end:
                    slots = [Slot(kind, days, start, end, loc or None)]
            m = re.search(r"\b(\d{3})\b", cells[cols["comp"]])
            for s in slots:
                if m:
                    s.section_id = m.group(1)
            out.extend(slots)
    return out


def _from_text(pages_text: Sequence[Tuple[int, str]]) -> Tuple[List[Slot], List[str]]:
    out: List[Slot] = []
    notes: List[str] = []
    text = "\n".join(t for _, t in pages_text[:6])
    lines = text.split("\n")
    default_loc = None
    for line in lines:
        m = re.match(r"\s*location\s*:\s*([^\n]+)", line, re.I)
        if m:
            default_loc = _location_in(m.group(1)) or m.group(1).strip()
    header_kind: Optional[str] = None
    header_left = 0
    for i, line in enumerate(lines):
        if _OFFICE.search(line):
            continue
        # a text table "Lecture Section | Time and Room | Instructor" followed by "MWF 12:30 – 1:20 Professor X"
        hm = re.match(r"\s*(lectures?|labs?|laboratory|tutorials?)\s+(?:section|time|day)", line, re.I)
        if hm and re.search(r"\b(time|day|room)\b", line, re.I) and not _TIME_ANY.search(line):
            header_kind, header_left = _kind_of(hm.group(1)), 3
            continue
        if header_kind and header_left > 0:
            header_left -= 1
            dm = _DAY_TOKENS.match(line.strip())
            if dm and _TIME_ANY.search(line):
                slots = _slots_from_fragment(header_kind, line, default_location=default_loc)
                if slots:
                    out.extend(slots)
                    header_kind = None
                    continue
        m = re.match(r"\s*((?:lectures?|lec|class\s+meetings?|classes|seminars?|labs?|laborator(?:y|ies)|tutorials?|tut)\b[^:\n]{0,20}):\s*(.*)", line, re.I)
        if not m:
            m = re.match(r"\s*((?:lectures?|labs?|laboratory|tutorials?))\s+((?:%s|M/W/F|MWF|TTh|MW|WF)[^\n]*)" % WEEKDAY_RE, line, re.I)
        if m:
            label, rest = m.group(1), m.group(2)
        elif len(line) < 90 and _TIME_ANY.search(line):
            # "In-person lectures. UCC-65 M/W/F 9:30-10:30 AM": the label sits mid-line
            km = re.search(r"\b(lectures?|labs?|laboratory|tutorials?)\b", line, re.I)
            if not km or not any(parse_days(d.group(0)) for d in _DAY_TOKENS.finditer(line)):
                continue
            label, rest = km.group(1), line
        else:
            continue
        kind = _kind_of(label)
        if not kind:
            continue
        frag = rest
        # a wrapped line continues on the next line when it has no time yet
        if not _TIME_ANY.search(frag) and i + 1 < len(lines) and not _kind_of(lines[i + 1][:12]) \
                and not re.match(r"\s*[A-Z][A-Za-z ]{2,25}:", lines[i + 1]):
            frag = frag + " " + lines[i + 1]
        slots = _slots_from_fragment(kind, frag, default_location=default_loc)
        if slots:
            out.extend(slots)
        elif re.search(r"\b(weekly|session|hrs?/|hours?/|per\s+week)\b", rest, re.I) and not parse_days(rest):
            notes.append(f"The outline lists a {kind} ({rest.strip()[:60]}) but no day or time: "
                         f"check your timetable on draftmyschedule.uwo.ca and add it with \"Add Section\".")
    return out, notes


def _from_weekly_dates(pages_text: Sequence[Tuple[int, str]], term_years: Sequence[int]) -> Optional[Slot]:
    """A weekly schedule whose dated rows all fall on one weekday means the class meets that day."""
    text = "\n".join(t for _, t in pages_text)
    if not re.search(r"\bweek\b", text, re.I):
        return None
    weekdays: List[int] = []
    years = sorted(set(term_years)) or [date.today().year]
    for m in re.finditer(rf"^\s*\d{{1,2}}\s+({MONTH_RE})\.?\s+(\d{{1,2}})(?![\d\-–])", text, re.I | re.M):
        mon = MONTHS[m.group(1).lower().rstrip(".")]
        day = int(m.group(2))
        y = years[0] if (mon >= 8 or len(years) == 1) else years[-1]
        try:
            weekdays.append(date(y, mon, day).weekday())
        except ValueError:
            continue
    if len(weekdays) >= 8 and len(set(weekdays)) == 1:
        return Slot(kind="lecture", days=[weekdays[0]], start=None, end=None,
                    note="Meets weekly on this day according to the course schedule; the outline gives no clock time.")
    return None


def extract_slots_and_notes(pages_text: Sequence[Tuple[int, str]],
                            tables: Sequence[Sequence[Sequence[Optional[str]]]],
                            term_year_hint=None) -> Tuple[List[Slot], List[str]]:
    """term_year_hint: an int (one year) or a sequence of the term's years."""
    if term_year_hint is None:
        years: List[int] = []
    elif isinstance(term_year_hint, int):
        years = [term_year_hint]
    else:
        years = list(term_year_hint)
    slots = _from_tables(tables)
    text_slots, notes = _from_text(pages_text)
    seen = {s.key() for s in slots}
    for s in text_slots:
        if s.key() not in seen:
            seen.add(s.key())
            slots.append(s)
    # a table slot without a location can borrow the one the prose found for the same slot
    for s in slots:
        if not s.location:
            for t in text_slots:
                if t.key() == s.key() and t.location:
                    s.location = t.location
    if not any(s.kind == "lecture" for s in slots):
        wk = _from_weekly_dates(pages_text, years)
        if wk:
            slots.append(wk)
    return slots, notes


def extract_slots(pages_text, tables, term_year_hint: Optional[int] = None) -> List[Slot]:
    return extract_slots_and_notes(pages_text, tables, term_year_hint)[0]
