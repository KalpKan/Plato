"""Read the term window from the outline itself; fall back to Western's sessional dates.

Priority:
  1. an "Important Dates" table (Classes Begin / Reading Week / Classes End / Exam Period),
     one row per term (Physiology 3120 prints two: Fall and Winter);
  2. "Class Begin: Monday, January 5, 2026" / "Class End: ..." lines (CS 3340B);
  3. a weekly schedule whose weeks carry date ranges ("Week 12 (Mar. 30-Apr.08)");
  4. the season + year named in the text or the file name ("Fall 2025", "2025-2026",
     "FW25", course-code suffix A = Fall, B = Winter) mapped to Western's sessional dates.
Never today's date: an unreadable term is reported as Unknown so the review page asks.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Sequence, Tuple

from .dates import MONTHS, MONTH_RE

# Western University undergraduate sessional dates (westerncalendar.uwo.ca, live page
# for 2026-27 and Wayback snapshots of the same page for 2022-2025; Fall 2025 uses the
# dates printed in the 2025-26 outlines themselves, Sept 4 - Dec 9, after the March 2025
# revision). "end" is the last day of classes, not the end of the exam period.
SESSIONAL: Dict[Tuple[str, int], Dict[str, object]] = {
    ("Fall", 2022): {"start": date(2022, 9, 8), "end": date(2022, 12, 8), "reading": (date(2022, 10, 31), date(2022, 11, 6)), "exams": (date(2022, 12, 10), date(2022, 12, 22))},
    ("Winter", 2023): {"start": date(2023, 1, 9), "end": date(2023, 4, 10), "reading": (date(2023, 2, 18), date(2023, 2, 26)), "exams": (date(2023, 4, 13), date(2023, 4, 30))},
    ("Fall", 2023): {"start": date(2023, 9, 7), "end": date(2023, 12, 8), "reading": (date(2023, 10, 30), date(2023, 11, 5)), "exams": (date(2023, 12, 10), date(2023, 12, 22))},
    ("Winter", 2024): {"start": date(2024, 1, 8), "end": date(2024, 4, 8), "reading": (date(2024, 2, 17), date(2024, 2, 25)), "exams": (date(2024, 4, 11), date(2024, 4, 30))},
    ("Fall", 2024): {"start": date(2024, 9, 5), "end": date(2024, 12, 6), "reading": (date(2024, 10, 12), date(2024, 10, 20)), "exams": (date(2024, 12, 9), date(2024, 12, 22))},
    ("Winter", 2025): {"start": date(2025, 1, 6), "end": date(2025, 4, 4), "reading": (date(2025, 2, 15), date(2025, 2, 23)), "exams": (date(2025, 4, 7), date(2025, 4, 30))},
    ("Fall", 2025): {"start": date(2025, 9, 4), "end": date(2025, 12, 9), "reading": (date(2025, 11, 3), date(2025, 11, 9)), "exams": (date(2025, 12, 11), date(2025, 12, 22))},
    ("Winter", 2026): {"start": date(2026, 1, 5), "end": date(2026, 4, 9), "reading": (date(2026, 2, 14), date(2026, 2, 22)), "exams": (date(2026, 4, 12), date(2026, 4, 30))},
    ("Fall", 2026): {"start": date(2026, 9, 9), "end": date(2026, 12, 8), "reading": (date(2026, 10, 10), date(2026, 10, 18)), "exams": (date(2026, 12, 11), date(2026, 12, 22))},
    ("Winter", 2027): {"start": date(2027, 1, 4), "end": date(2027, 4, 9), "reading": (date(2027, 2, 13), date(2027, 2, 21)), "exams": (date(2027, 4, 12), date(2027, 4, 30))},
}


def sessional_dates(season: str, year: int) -> Optional[Dict[str, object]]:
    """Known Western dates for a term, or an estimate (Fall: Thursday after Labour Day
    to the second Tuesday of December; Winter: first Monday on/after Jan 4 to the second
    Thursday of April) flagged with "estimated": True."""
    key = (season.capitalize(), year)
    if key in SESSIONAL:
        return dict(SESSIONAL[key], estimated=False)
    if season.capitalize() == "Fall":
        labour = date(year, 9, 1)
        while labour.weekday() != 0:
            labour = labour.replace(day=labour.day + 1)
        start = labour.replace(day=labour.day + 3)
        end = _nth_weekday(year, 12, 1, 2)
        exams = (_nth_weekday(year, 12, 3, 2), date(year, 12, 22))
        return {"start": start, "end": end, "reading": None, "exams": exams, "estimated": True}
    if season.capitalize() == "Winter":
        start = date(year, 1, 4)
        while start.weekday() != 0:
            start = start.replace(day=start.day + 1)
        end = _nth_weekday(year, 4, 3, 2)
        return {"start": start, "end": end, "reading": None, "exams": (date(year, 4, 12), date(year, 4, 30)), "estimated": True}
    if season.capitalize() == "Summer":
        return {"start": date(year, 5, 4), "end": date(year, 7, 31), "reading": None, "exams": None, "estimated": True}
    return None


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    while d.weekday() != weekday:
        d = d.replace(day=d.day + 1)
    return d.replace(day=d.day + 7 * (n - 1))


@dataclass
class TermInfo:
    name: str = "Unknown"
    start: Optional[date] = None
    end: Optional[date] = None
    exam_periods: List[Tuple[date, date]] = field(default_factory=list)
    reading_weeks: List[Tuple[date, date]] = field(default_factory=list)
    source: str = "none"          # outline | sessional | estimated | none
    year_hints: List[int] = field(default_factory=list)
    note: str = ""


# -------------------------------------------------------------------- helpers
_YEAR = re.compile(r"\b(20\d{2})\b")
_SEASON_YEAR = re.compile(r"\b(Fall|Winter|Summer|Spring|Intersession)\s*(?:/|&|and)?\s*(?:Fall|Winter)?\s*(?:Term|Semester|Session)?\s*[,|\-–]?\s*(20\d{2})(?:\s*[-–/]\s*(20\d{2}|\d{2}))?", re.I)
_YEAR_RANGE = re.compile(r"\b(20\d{2})\s*[-–/]\s*(20\d{2}|\d{2})\b")
_FW_WORD = re.compile(r"\bfall\s*(?:/|&|and|-)\s*winter\b", re.I)
_MONTH_YEAR = re.compile(rf"\b({MONTH_RE})\s+(20\d{{2}})\b", re.I)
_FILE_SEASON = re.compile(r"(fall|winter|summer)[-_ ]*(20\d{2}|\d{2})\b", re.I)
_FILE_FW = re.compile(r"(?:^|[-_ ])(FW|F|W|S)[-_]?(\d{2})(?:$|[-_ .])")
_FILE_RANGE = re.compile(r"(20\d{2})[-_](20\d{2}|\d{2})")
_FILE_YEAR = re.compile(r"(20\d{2})")


def _md(text: str, month_re: str = MONTH_RE) -> List[Tuple[int, int, int]]:
    """(pos, month, day) for every 'Month d' in text."""
    out = []
    for m in re.finditer(rf"\b({month_re})\.?\s*(\d{{1,2}})(?:st|nd|rd|th)?\b", text, re.I):
        out.append((m.start(), MONTHS[m.group(1).lower().rstrip(".")], int(m.group(2))))
    return out


def _md_range(text: str) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """'February 14-22' -> ((2,14),(2,22)); 'Mar. 30-Apr.08' -> ((3,30),(4,8))."""
    m = re.search(rf"\b({MONTH_RE})\.?\s*(\d{{1,2}})\s*[-–]\s*(?:({MONTH_RE})\.?\s*)?(\d{{1,2}})\b", text, re.I)
    if not m:
        return None
    m1 = MONTHS[m.group(1).lower().rstrip(".")]
    m2 = MONTHS[m.group(3).lower().rstrip(".")] if m.group(3) else m1
    return (m1, int(m.group(2))), (m2, int(m.group(4)))


def _year_for(month: int, years: Sequence[int]) -> int:
    """Sept-Dec belongs to the first academic year, Jan-Aug to the second."""
    ys = sorted(set(years))
    if not ys:
        return date.today().year
    if len(ys) == 1:
        return ys[0]
    return ys[0] if month >= 8 else ys[-1]


def _mk(month: int, day: int, years: Sequence[int]) -> Optional[date]:
    try:
        return date(_year_for(month, years), month, day)
    except ValueError:
        return None


# ------------------------------------------------------------- the readers
def _important_dates_rows(text: str, years: Sequence[int]) -> List[Dict[str, object]]:
    """'Classes Begin Reading Week Classes End Study day(s) Exam Period' followed by a
    values line: 'January 5 February 14-22 April 9 April 10-11 April 12-30'."""
    rows = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if not re.search(r"classes\s+begin", line, re.I) or not re.search(r"classes\s+end", line, re.I):
            continue
        for j in range(i + 1, min(i + 4, len(lines))):
            vals = lines[j].replace("–", "-").replace("—", "-")
            parts = _md(vals)
            if len(parts) < 2:
                continue
            # first "Month d" is Classes Begin; the Classes End is the first single date
            # after the reading-week range. Find every month-day token with position.
            tokens = re.findall(rf"({MONTH_RE})\.?\s*(\d{{1,2}})(?:\s*[-–]\s*(?:({MONTH_RE})\.?\s*)?(\d{{1,2}}))?(?:,\s*(\d{{1,2}}))?", vals, re.I)
            if len(tokens) < 2:
                continue
            begin = MONTHS[tokens[0][0].lower().rstrip(".")], int(tokens[0][1])
            reading = None
            end = None
            exams = None
            rest = tokens[1:]
            # classify by header order: reading week (range), classes end (single), study day(s), exam period (range)
            single_after_range = False
            for mon, d1, mon2, d2, _extra in rest:
                m1 = MONTHS[mon.lower().rstrip(".")]
                if d2:  # a range
                    m2 = MONTHS[mon2.lower().rstrip(".")] if mon2 else m1
                    if reading is None and end is None:
                        reading = ((m1, int(d1)), (m2, int(d2)))
                    else:
                        exams = ((m1, int(d1)), (m2, int(d2)))
                else:
                    if end is None:
                        end = (m1, int(d1))
                        single_after_range = True
            if end is None:
                continue
            rows.append({
                "start": _mk(begin[0], begin[1], years),
                "end": _mk(end[0], end[1], years),
                "reading": (_mk(*reading[0], years), _mk(*reading[1], years)) if reading else None,
                "exams": (_mk(*exams[0], years), _mk(*exams[1], years)) if exams else None,
            })
            break
    return rows


def _class_begin_end_lines(text: str, years: Sequence[int]) -> Optional[Dict[str, object]]:
    def grab(label: str) -> Optional[date]:
        m = re.search(rf"\b{label}[^\n:]*:\s*([^\n]+)", text, re.I)
        if not m:
            return None
        line = m.group(1)
        y = _YEAR.search(line)
        mds = _md(line)
        if not mds:
            return None
        _, mon, day = mds[0]
        try:
            return date(int(y.group(1)), mon, day) if y else _mk(mon, day, years)
        except ValueError:
            return None
    start = grab(r"class(?:es)?\s+begins?") or grab(r"first\s+(?:day\s+of\s+)?class(?:es)?") or grab(r"term\s+begins?")
    end = grab(r"class(?:es)?\s+ends?") or grab(r"last\s+(?:day\s+of\s+)?class(?:es)?") or grab(r"term\s+ends?")
    if not (start and end) or end <= start:
        return None
    out: Dict[str, object] = {"start": start, "end": end, "reading": None, "exams": None}
    m = re.search(r"exam(?:ination)?\s+period[^\n:]*:\s*([^\n]+)", text, re.I)
    if m:
        r = _md_range(m.group(1).replace("–", "-"))
        y = _YEAR.search(m.group(1))
        if r:
            yrs = [int(y.group(1))] if y else [end.year]
            out["exams"] = (_mk(*r[0], yrs), _mk(*r[1], yrs))
    m = re.search(r"reading\s+week[^\n:]*:\s*([^\n]+)", text, re.I)
    if m:
        r = _md_range(m.group(1).replace("–", "-"))
        if r:
            out["reading"] = (_mk(*r[0], [start.year, end.year]), _mk(*r[1], [start.year, end.year]))
    return out


def _weekly_ranges(text: str, years: Sequence[int]) -> Optional[Tuple[date, date]]:
    """'Week 1 (Jan. 05-09)' ... 'Week 12 (Mar. 30-Apr.08)' -> (Jan 5, Apr 8)."""
    found = []
    for m in re.finditer(rf"\bweek\s+(\d{{1,2}})\s*[\(:\-–]?\s*({MONTH_RE})\.?\s*(\d{{1,2}})\s*[-–]\s*(?:({MONTH_RE})\.?\s*)?(\d{{1,2}})", text, re.I):
        m1 = MONTHS[m.group(2).lower().rstrip(".")]
        m2 = MONTHS[m.group(4).lower().rstrip(".")] if m.group(4) else m1
        a = _mk(m1, int(m.group(3)), years)
        b = _mk(m2, int(m.group(5)), years)
        if a and b:
            found.append((int(m.group(1)), a, b))
    if len(found) < 4:
        return None
    found.sort()
    return found[0][1], found[-1][2]


def _season_year_from_text(text: str) -> Tuple[Optional[str], List[int], bool]:
    """('Fall', [2025], full_year?)"""
    text = text.replace("\u2212", "-").replace("\u2013", "-").replace("\u2014", "-")
    full = bool(_FW_WORD.search(text))
    years: List[int] = []
    season = None
    for m in _SEASON_YEAR.finditer(text):
        s = m.group(1).capitalize()
        y = int(m.group(2))
        if m.group(3):
            y2 = int(m.group(3)) if len(m.group(3)) == 4 else 2000 + int(m.group(3))
            if s == "Winter" and y2 == y + 1 and not _FW_WORD.search(m.group(0)):
                # "Winter 2023-24" is the Winter term of the 2023-24 session, i.e. Winter 2024
                years.append(y2)
                season = season or "Winter"
                continue
            years.append(y)
            years.append(y2)
            full = True
        else:
            years.append(y)
        if season is None:
            season = "Fall" if s in ("Fall",) else "Winter" if s == "Winter" else "Summer"
        if s.lower() in ("fall",) and re.search(r"fall\s*(?:/|&|and)\s*winter", m.group(0), re.I):
            full = True
    seasons_seen = {(m.group(1).capitalize(), int(m.group(2))) for m in _SEASON_YEAR.finditer(text)}
    if any(("Fall", y) in seasons_seen and ("Winter", y + 1) in seasons_seen for _, y in seasons_seen):
        full = True
    if not years:
        for m in _YEAR_RANGE.finditer(text):
            y1 = int(m.group(1))
            y2 = int(m.group(2)) if len(m.group(2)) == 4 else 2000 + int(m.group(2))
            if y2 == y1 + 1:
                years += [y1, y2]
                full = True
                break
    if not years:
        for m in _MONTH_YEAR.finditer(text):
            years.append(int(m.group(2)))
            mon = MONTHS[m.group(1).lower().rstrip(".")]
            if season is None:
                season = "Fall" if mon >= 8 else "Winter" if mon <= 4 else "Summer"
            break
    return season, years, full


def _season_year_from_filename(filename: str) -> Tuple[Optional[str], List[int], bool]:
    stem = re.sub(r"\.pdf$", "", filename or "", flags=re.I)
    m = _FILE_SEASON.search(stem)
    if m:
        y = int(m.group(2)) if len(m.group(2)) == 4 else 2000 + int(m.group(2))
        return m.group(1).capitalize(), [y], False
    m = _FILE_RANGE.search(stem)
    if m:
        y1 = int(m.group(1))
        y2 = int(m.group(2)) if len(m.group(2)) == 4 else 2000 + int(m.group(2))
        if y2 == y1 + 1:
            return None, [y1, y2], True
    m = _FILE_FW.search(stem)
    if m:
        y = 2000 + int(m.group(2))
        tag = m.group(1).upper()
        if tag == "FW":
            return None, [y, y + 1], True
        return {"F": "Fall", "W": "Winter", "S": "Summer"}[tag], [y], False
    m = _FILE_YEAR.search(stem)
    if m:
        return None, [int(m.group(1))], False
    return None, [], False


def _season_from_code(course_code: Optional[str]) -> Optional[str]:
    """Western suffixes: A = first term, B = second term, A/B or E or none = full year, F/G half-year."""
    if not course_code:
        return None
    m = re.search(r"\d{3,4}\s*([A-Za-z](?:/[A-Za-z])?)\b", course_code)
    if not m:
        return None
    suf = m.group(1).upper()
    if suf in ("A", "F", "Q"):
        return "Fall"
    if suf in ("B", "G", "R"):
        return "Winter"
    if suf in ("E", "A/B", "F/G"):
        return "Full"
    return None


def extract_term(pages_text: Sequence[Tuple[int, str]], filename: str = "",
                 course_code: Optional[str] = None) -> TermInfo:
    first = "\n".join(t for _, t in pages_text[:3])
    whole = "\n".join(t for _, t in pages_text)
    season, years, full = _season_year_from_text(first)
    if not years:
        season2, years, full2 = _season_year_from_filename(filename)
        season = season or season2
        full = full or full2
    if not years:
        season3, years3, full3 = _season_year_from_text(whole)
        season, years, full = season or season3, years3, full or full3
    if not course_code:
        m = re.search(r"\b[A-Z][A-Za-z]{1,4}\s?\d{4}[A-Z]\b", first)
        if m:
            course_code = m.group(0)
    code_season = _season_from_code(course_code)
    if code_season == "Full":
        full = True
    elif code_season:
        # a half course (A = Fall, B = Winter) is one term even when the outline says
        # "Fall/Winter 2025" or the file name says FW25
        season = code_season
        full = False

    year_hints = sorted(set(years))

    # 1. Important Dates table(s)
    rows = _important_dates_rows(first, year_hints or [date.today().year])
    if rows:
        rows = [r for r in rows if r["start"] and r["end"]]
    if rows:
        if len(rows) >= 2:
            rows.sort(key=lambda r: r["start"])  # type: ignore[arg-type]
            start, end = rows[0]["start"], rows[-1]["end"]
        else:
            start, end = rows[0]["start"], rows[0]["end"]
        info = TermInfo(start=start, end=end, source="outline", year_hints=year_hints or [start.year, end.year])  # type: ignore[union-attr]
        info.exam_periods = [r["exams"] for r in rows if r.get("exams") and all(r["exams"])]  # type: ignore[index]
        info.reading_weeks = [r["reading"] for r in rows if r.get("reading") and all(r["reading"])]  # type: ignore[index]
        if full and len(rows) == 1 and start.month >= 8:  # type: ignore[union-attr]
            # a full-year course whose outline prints only the Fall table: the Winter half comes from Western
            w = sessional_dates("Winter", start.year + 1)  # type: ignore[union-attr]
            if w:
                info.end = w["end"]  # type: ignore[assignment]
                info.exam_periods.append(w["exams"])  # type: ignore[arg-type]
                if w.get("reading"):
                    info.reading_weeks.append(w["reading"])  # type: ignore[arg-type]
                info.year_hints = sorted({start.year, start.year + 1})  # type: ignore[union-attr]
        info.name = _name_for(start, end, season)
        _fill_missing_periods(info)
        return info

    # 2. Class Begin / Class End lines
    cbe = _class_begin_end_lines(whole, year_hints or [date.today().year])
    if cbe:
        info = TermInfo(start=cbe["start"], end=cbe["end"], source="outline")  # type: ignore[arg-type]
        info.year_hints = sorted({info.start.year, info.end.year})  # type: ignore[union-attr]
        if cbe.get("exams") and all(cbe["exams"]):  # type: ignore[index]
            info.exam_periods = [cbe["exams"]]  # type: ignore[list-item]
        if cbe.get("reading") and all(cbe["reading"]):  # type: ignore[index]
            info.reading_weeks = [cbe["reading"]]  # type: ignore[list-item]
        info.name = _name_for(info.start, info.end, season)  # type: ignore[arg-type]
        _fill_missing_periods(info)
        return info

    # 3. weekly schedule with date ranges
    if year_hints:
        wr = _weekly_ranges(whole, year_hints)
        if wr:
            info = TermInfo(start=wr[0], end=wr[1], source="outline", year_hints=year_hints)
            info.name = _name_for(wr[0], wr[1], season)
            _fill_missing_periods(info)
            return info

    # 4. sessional dates from season + year
    if year_hints:
        if full or (season is None and len(year_hints) == 2):
            y1 = min(year_hints)
            f = sessional_dates("Fall", y1)
            w = sessional_dates("Winter", y1 + 1)
            if f and w:
                info = TermInfo(name=f"Fall/Winter {y1}-{y1 + 1}", start=f["start"], end=w["end"],  # type: ignore[arg-type]
                                source="estimated" if (f["estimated"] or w["estimated"]) else "sessional",
                                year_hints=[y1, y1 + 1])
                info.exam_periods = [x for x in (f["exams"], w["exams"]) if x]  # type: ignore[misc]
                info.reading_weeks = [x for x in (f["reading"], w["reading"]) if x]  # type: ignore[misc]
                return info
        s = season or "Fall"
        y = min(year_hints) if s == "Fall" else max(year_hints)
        if s == "Winter" and len(year_hints) == 1 and full is False:
            y = year_hints[0]
        d = sessional_dates(s, y)
        if d:
            info = TermInfo(name=f"{s} {y}", start=d["start"], end=d["end"],  # type: ignore[arg-type]
                            source="estimated" if d["estimated"] else "sessional", year_hints=[y])
            if d.get("exams"):
                info.exam_periods = [d["exams"]]  # type: ignore[list-item]
            if d.get("reading"):
                info.reading_weeks = [d["reading"]]  # type: ignore[list-item]
            return info

    return TermInfo(name="Unknown", source="none", year_hints=year_hints,
                    note="The outline does not state its term or dates; enter the first and last day of classes.")


def _name_for(start: date, end: date, season: Optional[str]) -> str:
    if start.year != end.year and start.month >= 8:
        return f"Fall/Winter {start.year}-{end.year}"
    if start.month >= 8:
        return f"Fall {start.year}"
    if start.month <= 4:
        return f"Winter {start.year}"
    return f"{season or 'Summer'} {start.year}"


def _fill_missing_periods(info: TermInfo) -> None:
    """An outline that prints Classes Begin/End but no exam period still gets Western's."""
    if not info.start or not info.end:
        return
    seasons = []
    if info.start.month >= 8:
        seasons.append(("Fall", info.start.year))
    if info.end.month <= 5:
        seasons.append(("Winter", info.end.year))
    if not info.exam_periods:
        for s, y in seasons:
            d = sessional_dates(s, y)
            if d and d.get("exams"):
                info.exam_periods.append(d["exams"])  # type: ignore[arg-type]
    if not info.reading_weeks:
        for s, y in seasons:
            d = sessional_dates(s, y)
            if d and d.get("reading"):
                info.reading_weeks.append(d["reading"])  # type: ignore[arg-type]
