"""Resolve the date text a course outline prints into a date, a time and a status.

Outlines write dates in many shapes ("Jan 16th", "Thursday, Oct. 30, 11:30 - 1:30pm",
"12 November 2025", "Nov.29th", "Author: Mon, Oct. 27th by 11:59 PM.") and very often
without a year. The year is taken from the term window (Sept-Dec belongs to the start
year, Jan-Aug to the end year), and when the term is unknown, from the weekday the
outline prints (Friday Oct. 3 is 2025, not 2024).

A cell that carries no date is never given one: it gets a status instead
("registrar", "tba", "range", "rule", "recurring", "missing") so the review page can
say why and the .ics can leave it out.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date, time, timedelta
from typing import List, Optional, Sequence, Tuple

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9,
    "september": 9, "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
WEEKDAYS = {
    "mon": 0, "monday": 0, "tue": 1, "tues": 1, "tuesday": 1, "wed": 2, "wednesday": 2,
    "thu": 3, "thur": 3, "thurs": 3, "thursday": 3, "fri": 4, "friday": 4, "sat": 5, "saturday": 5,
    "sun": 6, "sunday": 6,
}
MONTH_RE = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
DAY_RE = r"(\d{1,2})(?:st|nd|rd|th)?"
# full names as well as the short forms: "Wednesdays" used to fall through ("wed" + "day"? no)
WEEKDAY_RE = r"(?:mon(?:day)?|tue(?:sday|s)?|wed(?:nesday)?|thu(?:rsday|rs|r)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?)"

# "January 20 mins", "March 3 hours", "Oct 5 %": a number with a unit after a month name is a duration
_NOT_DAY = r"(?!\s*(?:min(?:ute)?s?|hrs?|hours?|%|marks?|points?|questions?|pages?|words?|weeks?|days?|students?)\b)"
# "Oct. 27th", "October 27", "Sept 16th"
_MD = re.compile(rf"\b({MONTH_RE})\.?\s*{DAY_RE}\b{_NOT_DAY}(?:,?\s*(\d{{4}}))?", re.I)
# "April 7-30", "Dec. 11-22, 2025", "Sept 16 - Oct 3": a window of days, never one date
_DAY_RANGE = re.compile(
    rf"\b({MONTH_RE})\.?\s*(\d{{1,2}})(?:st|nd|rd|th)?\s*[-–—]\s*(?:({MONTH_RE})\.?\s*)?(\d{{1,2}})(?:st|nd|rd|th)?(?![\d:]|\s*[ap]\.?m)(?:,?\s*(\d{{4}}))?", re.I)
# "Written in January", "during February": a month with no day is a month-long window
_MONTH_ONLY = re.compile(rf"\b(?:in|during|throughout|by\s+the\s+end\s+of)\s+({MONTH_RE})\b(?:\s+of\s+|,?\s*)?(20\d{{2}})?", re.I)
# "12 November 2025", "8 Dec"
_DM = re.compile(rf"\b{DAY_RE}\s+({MONTH_RE})\.?(?:,?\s*(\d{{4}}))?\b", re.I)
# "2025-10-27"
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_WEEKDAY = re.compile(rf"\b({WEEKDAY_RE})\b\.?", re.I)
# "11:59 PM", "6 – 8 PM", "7-8:30pm", "11:30 - 1:30pm", "2:30-4:20PM", "1 pm"
_TIME_RANGE = re.compile(
    r"\b(\d{1,2})(?:[:.](\d{2}))?\s*([ap]\.?m\.?)?\s*(?:[-–—]|\bto\b|\buntil\b)\s*(\d{1,2})(?:[:.](\d{2}))?\s*([ap]\.?m\.?)?(?![\d%])", re.I)
_TIME_ONE = re.compile(r"\b(\d{1,2})(?:[:.](\d{2}))\s*([ap]\.?m\.?)?(?!\s*%)|\b(\d{1,2})\s*([ap]\.?m\.?)\b", re.I)

_REGISTRAR = re.compile(r"registrar|final\s+exam(?:ination)?\s+period|exam\s+period\b.*\bfinal|scheduled\s+by\s+the\s+(?:office|university)", re.I)
_TBA = re.compile(r"\btb[ad]\b|to\s+be\s+(?:announced|determined|confirmed)", re.I)
_RULE = re.compile(r"\b(?:\d+\s*(?:hrs?|hours?|days?)\s+(?:after|before|following)|after\s+each|following\s+each|(?:one|two|three)\s+weeks?\s+after|day\s+of\s+(?:the\s+|each\s+|your\s+)?(?:lab|tutorial|lecture|class)|end\s+of\s+(?:each|every)\s+(?:lab|tutorial|class|week))\b", re.I)
_RECURRING = re.compile(rf"\b(?:each|every)\s+({WEEKDAY_RE})\b", re.I)
_EXAM_PERIOD = re.compile(r"\b(december|april|final|fall|winter)?\s*exam(?:ination)?\s+period", re.I)


@dataclass
class DateResult:
    status: str                       # exact | registrar | tba | range | rule | recurring | missing
    date: Optional[date] = None
    time: Optional[time] = None
    end_time: Optional[time] = None
    secondary_date: Optional[date] = None
    window: Optional[Tuple[date, date]] = None
    dates: List[date] = field(default_factory=list)
    rule: Optional[str] = None
    note: str = ""                    # one line for the review page
    raw: str = ""


def _clean(text: str) -> str:
    text = text.replace("–", "-").replace("—", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def _to_time(hour: int, minute: Optional[str], ampm: Optional[str], assume_pm_from: Optional[int] = None) -> Optional[time]:
    minute_i = int(minute) if minute else 0
    if hour > 24 or minute_i > 59:
        return None
    if ampm:
        pm = ampm.lower().startswith("p")
        if pm and hour < 12:
            hour += 12
        if not pm and hour == 12:
            hour = 0
    elif assume_pm_from is not None and hour < assume_pm_from and hour < 12:
        # "7-8:30pm": the start shares the end's meridian
        hour += 12
    if hour == 24:
        hour = 0
    return time(hour, minute_i)


def parse_time_span(text: str) -> Tuple[Optional[time], Optional[time]]:
    """'11:30 - 1:30pm' -> (11:30, 13:30); '6 – 8 PM' -> (18:00, 20:00); 'by 11:59 PM' -> (23:59, None)."""
    t = _clean(text)
    for m in _TIME_RANGE.finditer(t):
        sh, sm, sap, eh, em, eap = m.groups()
        if not (sm or em or sap or eap):
            continue  # "14-22" is a date range, not a time
        if not (sap or eap) and not (sm and em):
            continue  # "7-8:30" without any meridian is too ambiguous to be a time span
        end = _to_time(int(eh), em, eap)
        start_ampm = sap
        if not start_ampm and eap and end:
            # share the meridian unless that would put the start after the end
            cand = _to_time(int(sh), sm, eap)
            if cand and cand <= end:
                start_ampm = eap
        start = _to_time(int(sh), sm, start_ampm)
        if start and end and not (sap or eap):
            # no meridian anywhere: timetable hours run 8:00-22:00, so "2:30-3:30" is afternoon
            if start.hour < 8:
                start = start.replace(hour=start.hour + 12)
            if end.hour < 8 or end < start:
                end = end.replace(hour=end.hour + 12) if end.hour < 12 else end
        if start and end and start <= end:
            return start, end
    for m in _TIME_ONE.finditer(t):
        if m.group(1):
            h, mi, ap = int(m.group(1)), m.group(2), m.group(3)
        else:
            h, mi, ap = int(m.group(4)), None, m.group(5)
        if ap is None and mi is None:
            continue
        if ap is None and h < 8:
            # "1:30" with no meridian is far more likely afternoon in a timetable
            h += 12
        tm = _to_time(h, mi, ap)
        if tm:
            return tm, None
    return None, None


class DateResolver:
    def __init__(self, term_start: Optional[date], term_end: Optional[date],
                 exam_periods: Sequence[Tuple[date, date]] = (), year_hints: Sequence[int] = (),
                 reading_weeks: Sequence[Tuple[date, date]] = ()):
        self.term_start = term_start
        self.term_end = term_end
        self.exam_periods = list(exam_periods)
        self.reading_weeks = list(reading_weeks)
        hints = list(year_hints)
        if term_start:
            hints.append(term_start.year)
        if term_end:
            hints.append(term_end.year)
        self.year_hints = sorted(set(hints))

    # ----------------------------------------------------------------- years
    def _candidate_years(self) -> List[int]:
        if self.year_hints:
            return self.year_hints
        return [date.today().year, date.today().year + 1]

    def _pick_year(self, month: int, day: int, weekday: Optional[int]) -> Optional[int]:
        cands = self._candidate_years()
        if self.term_start and self.term_end:
            lo = self.term_start - timedelta(days=21)
            hi = self.term_end + timedelta(days=60)
            inside = []
            for y in range(self.term_start.year, self.term_end.year + 1):
                try:
                    d = date(y, month, day)
                except ValueError:
                    continue
                if lo <= d <= hi:
                    inside.append(y)
            if inside:
                if weekday is not None:
                    for y in inside:
                        if date(y, month, day).weekday() == weekday:
                            return y
                return inside[0]
            # outside the window: prefer the year whose weekday matches, else the start year for Sep-Dec
            if weekday is not None:
                for y in cands:
                    try:
                        if date(y, month, day).weekday() == weekday:
                            return y
                    except ValueError:
                        pass
            return self.term_start.year if month >= 8 else self.term_end.year
        if weekday is not None:
            for y in cands:
                try:
                    if date(y, month, day).weekday() == weekday:
                        return y
                except ValueError:
                    pass
        return cands[0] if cands else None

    # ---------------------------------------------------------------- dates
    def _find_dates(self, text: str) -> List[Tuple[int, date]]:
        """All (position, date) pairs in the text, earliest position first."""
        found: List[Tuple[int, date]] = []
        for m in _ISO.finditer(text):
            try:
                found.append((m.start(), date(int(m.group(1)), int(m.group(2)), int(m.group(3)))))
            except ValueError:
                pass
        for m in _MD.finditer(text):
            month = MONTHS[m.group(1).lower().rstrip(".")]
            day = int(m.group(2))
            year = int(m.group(3)) if m.group(3) else None
            found.append((m.start(), (month, day, year)))  # type: ignore[arg-type]
        md_month_positions = {m.start(1) for m in _MD.finditer(text)}
        for m in _DM.finditer(text):
            month = MONTHS[m.group(2).lower().rstrip(".")]
            day = int(m.group(1))
            year = int(m.group(3)) if m.group(3) else None
            if any(abs(p - m.start()) < 3 for p, _ in found):
                continue
            if m.start(2) in md_month_positions:
                continue  # "19 February 5": the month is followed by its own day, the 19 is a week number
            found.append((m.start(), (month, day, year)))  # type: ignore[arg-type]
        found.sort(key=lambda x: x[0])
        out: List[Tuple[int, date]] = []
        for pos, val in found:
            if isinstance(val, date):
                out.append((pos, val))
                continue
            month, day, year = val
            if not (1 <= day <= 31):
                continue
            weekday = None
            wm = None
            for w in _WEEKDAY.finditer(text[max(0, pos - 18):pos]):
                wm = w
            if wm:
                weekday = WEEKDAYS.get(wm.group(1).lower())
            if year is None:
                year = self._pick_year(month, day, weekday)
            if year is None:
                continue
            try:
                out.append((pos, date(year, month, day)))
            except ValueError:
                continue
        return out

    def _day_window(self, text: str, month_only: bool = True) -> Optional[Tuple[date, date]]:
        """'April 7-30' -> (Apr 7, Apr 30); 'Sept 16 - Oct 3' -> (Sep 16, Oct 3); 'in January' -> the month
        (unless month_only is False: 'during December exam period' is the exam window, not December)."""
        m = _DAY_RANGE.search(text)
        if m:
            m1 = MONTHS[m.group(1).lower().rstrip(".")]
            m2 = MONTHS[m.group(3).lower().rstrip(".")] if m.group(3) else m1
            d1, d2 = int(m.group(2)), int(m.group(4))
            year = int(m.group(5)) if m.group(5) else self._pick_year(m1, min(d1, 28), None)
            if year is None:
                return None
            try:
                a = date(year, m1, d1)
                b = date(year + (1 if m2 < m1 else 0), m2, d2)
            except ValueError:
                return None
            return (a, b) if a <= b else None
        if not month_only or _MD.search(text) or _DM.search(text) or _ISO.search(text):
            return None
        m = _MONTH_ONLY.search(text)
        if m:
            mon = MONTHS[m.group(1).lower().rstrip(".")]
            year = int(m.group(2)) if m.group(2) else self._pick_year(mon, 1, None)
            if year is None:
                return None
            return date(year, mon, 1), date(year, mon, calendar.monthrange(year, mon)[1])
        return None

    def _exam_window(self, text: str) -> Optional[Tuple[date, date]]:
        m = _EXAM_PERIOD.search(text)
        if not m or not self.exam_periods:
            return self.exam_periods[-1] if self.exam_periods else None
        hint = (m.group(1) or "").lower()
        if hint in ("december", "fall"):
            for w in self.exam_periods:
                if w[0].month == 12:
                    return w
        if hint in ("april", "winter"):
            for w in self.exam_periods:
                if w[0].month == 4:
                    return w
        if hint == "final":
            return self.exam_periods[-1]
        # unqualified "exam period": the one that follows the term end
        return self.exam_periods[-1]

    def resolve(self, text: Optional[str]) -> DateResult:
        raw = text or ""
        t = _clean(raw)
        if not t:
            return DateResult(status="missing", raw=raw, note="No due date in the outline")
        low = t.lower()

        if _RULE.search(low):
            return DateResult(status="rule", rule=t, raw=raw, note=f"Relative rule: {t}")

        if _RECURRING.search(low):
            rec = self._recurring(t)
            if rec:
                return rec

        exam_mention = _EXAM_PERIOD.search(low)
        registrar = bool(_REGISTRAR.search(low))
        tba = bool(_TBA.search(low))
        dates = self._find_dates(t)

        # "April 7-30", "Dec. 11-22, 2025", "Written in January": a window, never the first day of it (D21)
        win = self._day_window(t, month_only=not (registrar or exam_mention))
        if win and all(win[0] <= d <= win[1] for _, d in dates):
            if registrar:
                return DateResult(status="registrar", window=win, raw=raw,
                                  note=f"Outline says: scheduled by the Registrar (exam period {win[0]:%b %-d} – {win[1]:%b %-d, %Y})")
            if exam_mention:
                return DateResult(status="range", window=win, raw=raw,
                                  note=f"Outline says: during the exam period ({win[0]:%b %-d} – {win[1]:%b %-d, %Y})")
            if tba:
                return DateResult(status="tba", window=win, raw=raw,
                                  note=f"Outline says the date is TBA (between {win[0]:%b %-d} and {win[1]:%b %-d, %Y})")
            if _RULE.search(low) is None:
                return DateResult(status="range", window=win, raw=raw,
                                  note=f"Outline gives a window, not a day ({win[0]:%b %-d} – {win[1]:%b %-d, %Y}); pick the day yourself")

        if registrar and not dates:
            win = self._exam_window(low)
            return DateResult(status="registrar", window=win, raw=raw,
                              note="Outline says: scheduled by the Registrar" + (f" (exam period {win[0]:%b %-d} – {win[1]:%b %-d, %Y})" if win else ""))
        if exam_mention and not dates:
            win = self._exam_window(low)
            return DateResult(status="range", window=win, raw=raw,
                              note="Outline says: during the exam period" + (f" ({win[0]:%b %-d} – {win[1]:%b %-d, %Y})" if win else ""))
        if tba and not dates:
            return DateResult(status="tba", raw=raw, note=f"Outline says: {t}" if len(t) <= 40 else "Outline says the date is TBA")
        if not dates:
            return DateResult(status="missing", raw=raw, note="No due date in the outline")

        # a "TBD" next to a date range (HS 2800 "December 8-9 ... (Date TBD)") is still undated
        if tba and re.search(r"\bdate\s+tb[ad]\b", low):
            win = self._exam_window(low) if (registrar or exam_mention) else None
            return DateResult(status="registrar" if registrar else "tba", window=win, raw=raw,
                              note="Outline says the date is TBD")

        first = dates[0][1]
        start_t, end_t = parse_time_span(t)
        if len(dates) >= 3 and not re.search(r"author|answer|draft|final\s+version", low):
            ds = sorted({d for _, d in dates})
            return DateResult(status="recurring", dates=ds, time=start_t, raw=raw,
                              note=f"{len(ds)} dates listed in the outline ({ds[0]:%b %-d} – {ds[-1]:%b %-d, %Y})")
        res = DateResult(status="exact", date=first, time=start_t, end_time=end_t, raw=raw)
        if len(dates) > 1:
            res.secondary_date = dates[1][1]
        return res

    def _recurring(self, t: str) -> Optional[DateResult]:
        m = _RECURRING.search(t)
        if not m:
            return None
        wd = WEEKDAYS.get(m.group(1).lower())
        if wd is None:
            return None
        dates = self._find_dates(t)
        start = end = None
        if len(dates) >= 2:
            start, end = dates[0][1], dates[1][1]
        elif len(dates) == 1:
            start = dates[0][1]
            end = self.term_end
        else:
            start, end = self.term_start, self.term_end
        if not start or not end or end < start:
            return None
        d = start
        while d.weekday() != wd:
            d += timedelta(days=1)
        out = []
        while d <= end:
            if not any(a <= d <= b for a, b in self.reading_weeks):
                out.append(d)
            d += timedelta(days=7)
        start_t, _ = parse_time_span(t)
        return DateResult(status="recurring", dates=out, time=start_t, raw=t,
                          note=f"Every {calendar.day_name[wd]} from {start:%b %-d} to {end:%b %-d, %Y} ({len(out)} dates)")
