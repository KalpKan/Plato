"""Course code and course name from the first text page (and the file name as a last resort).

Western codes are "<Subject> <4 digits><optional letter>" where the subject is either an
abbreviation (KIN, CS, ECE, HS, AM, MSE) or a spelled-out subject that may be two words
("Classical Studies 1000", "Health Sciences 2800", "Computer Science 3340B"). Rooms look
similar ("MC 113", "SSC 2050") so a candidate must be a known subject, or an abbreviation
that appears in a heading-like line, and never a room after "Office" / "Room".
"""
from __future__ import annotations

import re
from typing import List, Optional, Sequence, Tuple

SUBJECTS = [
    "Actuarial Science", "American Studies", "Anatomy and Cell Biology", "Anthropology", "Applied Mathematics", "Applied Math",
    "Microbiology & Immunology", "Physiology & Pharmacology", "Epidemiology & Biostatistics",
    "Arabic", "Art History", "Astronomy", "Biochemistry", "Biology", "Biomedical Engineering", "Biostatistics",
    "Business", "Calculus", "Chemical and Biochemical Engineering", "Chemistry", "Childhood and Youth Studies",
    "Chinese", "Civil and Environmental Engineering", "Classical Studies", "Communication Sciences and Disorders",
    "Computer Science", "Data Science", "Digital Humanities", "Earth Sciences", "Economics", "Electrical and Computer Engineering",
    "Engineering Science", "English", "Environmental Science", "Epidemiology and Biostatistics", "Film Studies",
    "Foods and Nutrition", "French", "Gender, Sexuality, and Women's Studies", "Geography", "German", "Greek",
    "Health Sciences", "Health Studies", "History", "Indigenous Studies", "Integrated Science", "Italian", "Japanese",
    "Kinesiology", "Latin", "Law", "Linguistics", "Management and Organizational Studies", "Mathematics",
    "Mechanical and Materials Engineering", "Medical Biophysics", "Medical Sciences", "Microbiology and Immunology",
    "Music", "Neuroscience", "Nursing", "Pathology", "Pharmacology", "Philosophy", "Physics", "Physiology",
    "Physiology and Pharmacology", "Political Science", "Psychology", "Rehabilitation Sciences", "Scholars Electives",
    "Social Work", "Sociology", "Software Engineering", "Spanish", "Statistical Sciences", "Statistics",
    "Speech and Language Sciences", "Theatre Studies", "Thanatology", "Visual Arts", "Women's Studies", "Writing",
]
ABBREVIATIONS = {
    "ACTURSCI", "AM", "ANATCELL", "BIO", "MICROIMM", "APPLMATH", "MATHS", "ANTHRO", "ASTRO", "BIOCHEM", "BIOL", "BIOSTATS", "BME", "BUS", "CALC", "CBE", "CEE",
    "CHEM", "CHEMBIO", "CS", "CLASSICS", "COMPSCI", "DATASCI", "ECE", "ECON", "ENGSCI", "ENG", "ENGL", "ENVSCI", "EPID",
    "ES", "FRENCH", "GEOG", "HIST", "HS", "HSCI", "INTEGSCI", "KIN", "KINES", "MATH", "MBP", "MEDSCI", "MICROIMM", "MME",
    "MOS", "MSE", "MUS", "NEURO", "PATH", "PHARM", "PHIL", "PHYS", "PHYSIOL", "PHYSPHARM", "PSYCH", "SE", "SOC", "STATS",
    "STAT", "SOCWORK", "SWK", "GSWS", "CSD", "DH", "MIT", "ANAT", "BIOSTAT", "PP",
}
_ROOM_CONTEXT = re.compile(r"\b(office|room|rm\.?|hall|building|location|lecture\s+hall|MC|SSC|NCB|UCC|HSB|AHB|TC|PAB|WSC|SH|MSB|SEB|TEB|SSB|NSC|KB|UC|FNB|LH|BGS|DSB)\b", re.I)
_SPELLED = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in sorted(SUBJECTS, key=len, reverse=True)) + r")\s+(\d{4}[A-Za-z]?(?:/[A-Za-z])?)\b", re.I)
_ABBR = re.compile(r"\b([A-Z]{2,9}|[A-Z][a-z]{1,8})\s?(\d{4}[A-Za-z]?(?:/[A-Za-z])?)\b")
_FILE_CODE = re.compile(r"(?:^|[-_ ])([A-Za-z]{2,9})[-_ ]?(\d{4}[A-Za-z]?)(?=$|[-_ .,])")
_SKIP_NAME = re.compile(r"university|department|school\s+of|faculty|course\s+outline|syllabus|outline\b|www\.|http|@|instructor|professor|"
                        r"\bfall\b|\bwinter\b|\bsummer\b|\bterm\b|\bsession\b|20\d{2}|campus|welcome|version|prerequisite|"
                        r"land\s+acknowledg|london|canada|ontario|preliminary|updated|section\s+\d|^\d", re.I)


def _norm_code(subject: str, number: str) -> str:
    subject = subject.strip()
    if subject.isupper():
        pass
    elif subject.upper() in ABBREVIATIONS and len(subject) <= 3:
        subject = subject.upper()
    else:
        subject = " ".join(w if w.lower() in ("and", "of") else w.capitalize() for w in subject.split())
    number = number.upper()
    return f"{subject} {number}"


def _candidates_from_text(text: str) -> List[Tuple[int, str]]:
    """(score, code) candidates from the first text page; higher score = better."""
    out: List[Tuple[int, str]] = []
    lines = text.split("\n")
    prereq_until = -1
    for li, line in enumerate(lines[:60]):
        if re.search(r"requisite|list of prerequisites|pre-?\s*or\s+co-?requisite", line, re.I):
            prereq_until = li + 4
        in_prereq = li <= prereq_until or bool(re.search(r"\b(minimum (?:mark|grade)|the former)\b", line, re.I))
        for m in _SPELLED.finditer(line):
            score = 100 - li
            if in_prereq or re.search(r"\b(prerequisite|antirequisite|corequisite|requisite|or\b|and\b|the former)", line[:m.start()], re.I):
                score -= 80
            if re.match(r"\s*course\s*name\s*:", line, re.I):
                score += 20
            out.append((score, _norm_code(m.group(1), m.group(2))))
        for m in _ABBR.finditer(line):
            abbr, number = m.group(1), m.group(2)
            before = line[max(0, m.start() - 25):m.start()]
            if abbr.upper() not in ABBREVIATIONS:
                continue
            if _ROOM_CONTEXT.search(before) and abbr in ("MC", "SSC", "UC", "TC", "SH", "PAB", "HSB", "AHB", "NCB", "UCC"):
                continue
            if re.search(r"\b(prerequisite|antirequisite|corequisite|requisite|the former|or|and|,)\s*$", before, re.I) and li > 3:
                continue
            score = 90 - li
            if in_prereq:
                score -= 80
            if re.search(r"^\s*(course\s*name|course\s*code|course)\s*:", line, re.I):
                score += 20
            if len(line.strip()) < 60:
                score += 5
            out.append((score, _norm_code(abbr, number)))
    return out


def _code_from_filename(filename: str) -> Optional[str]:
    stem = re.sub(r"\.pdf$", "", filename or "", flags=re.I)
    for m in _FILE_CODE.finditer(stem):
        abbr, number = m.group(1), m.group(2)
        if abbr.upper() in ABBREVIATIONS or abbr.capitalize() in SUBJECTS:
            return _norm_code(abbr, number)
    return None


_NAME_LABEL = re.compile(r"^\W*course\s*(?:name|title)\s*:\s*(.+)$", re.I)
_HEADING_WORDS = re.compile(
    r"^(?:course\s+(?:information|description|overview|outline|syllabus|materials?|content|format|objectives?|website|delivery|schedule|policies|name|title|number|code)|"
    r"general\s+information|instructor\s+information|learning\s+outcomes|technical\s+requirements|important\s+dates|campus\s+supports?|"
    r"in-?person|online|hybrid|delivery(?:\s+mode)?|welcome.*|table\s+of\s+contents|calendar\s+description|introduction)\W*$", re.I)
_NAME_TAILS = [
    re.compile(r"\s*\((?:[^)]*(?:20\d\d|january|april|september|december|in-?person|online|hybrid|blended|a?synchronous)[^)]*)\)\s*$", re.I),
    re.compile(r"\s*[-–—:|(]?\s*(?:preliminary\s+)?(?:course\s+outline|course\s+syllabus|syllabus|outline|edition)\b.*$", re.I),
    re.compile(r"[.\s,]*\b(?:fall|winter|summer|spring|intersession)?\s*(?:20\d\d(?:\s*[-–/]\s*(?:20)?\d\d)?)\s*(?:term|session)?\W*$", re.I),
    re.compile(r"[.\s,]*\b(?:fall|winter|summer|spring|intersession)\b(?:\s*[/&,-]\s*(?:fall|winter|summer|spring))?\s*(?:term|session)?\W*$", re.I),
    re.compile(r"\s*\([^)]*$"),                      # a parenthesis whose closing half was trimmed away
    re.compile(r"^\W*course\s*(?:name|title)\s*:\s*", re.I),
]
_SUBJECT_TOKEN = re.compile(r"(?:^|[\s,\-–—/])(?:" + "|".join(re.escape(x) for x in sorted(SUBJECTS, key=len, reverse=True))
                            + r"|" + "|".join(sorted(ABBREVIATIONS, key=len, reverse=True)) + r")\s*$", re.I)


def _clean_name(cand: str) -> Optional[str]:
    """Trim a candidate title line to the course name, or None when it is not one."""
    c = (cand or "").strip()
    c = re.sub(r"(?<=[a-z])\d$", "", c)                       # footnote digit glued to the last word
    c = re.sub(r"\s*\(?\b(?:section|sec\.?)\s*\d{3}\b.*$", "", c, flags=re.I)
    for _ in range(4):
        before = c
        for pat in _NAME_TAILS:
            c = pat.sub("", c).strip(" :-–—.,|")
        if c == before:
            break
    c = re.sub(r"\s*\((?:[A-Za-z ]+\s)?\d{4}[A-Za-z]?\)\s*$", "", c)   # "(Biochem 3381A)"
    c = re.sub(r"\s+", " ", c).strip(" :-–—.,|")
    if not (6 <= len(c) <= 90):
        return None
    if _HEADING_WORDS.match(c) or _SKIP_NAME.search(c) or re.search(r"\d{3,}", c):
        return None
    if re.match(r"^(?:an?|the)\s+\w+(?:,\s*\w+)*\s+course\b", c, re.I):
        return None                                            # "An online, asynchronous course with ..."
    words = c.split()
    if sum(1 for w in words if w[:1].islower()) > len(words) // 2 and not c.isupper():
        return None                                            # a sentence, not a title
    if re.search(r"\b(?:is|are|will|covers|provides|examines|introduces)\b", c, re.I):
        return None
    return _title(c)


def _name_from_label(text: str, code: Optional[str]) -> Optional[str]:
    """'• Course Name: Applied Logic for Computer Science' / 'Course name: Mathematical Biology. Winter 2026.'"""
    lines = text.split("\n")
    for i, line in enumerate(lines[:60]):
        m = _NAME_LABEL.match(line.strip())
        if not m:
            continue
        val = m.group(1).strip()
        if _looks_like_code(val, code):
            # "Course Name: Applied Mathematics 3813B:" then "Nonlinear Ordinary Differential Equations and Chaos"
            if val.endswith(":") and i + 1 < len(lines):
                name = _clean_name(lines[i + 1])
                if name:
                    return name
            continue
        name = _clean_name(val)
        if name:
            return name
    return None


def _looks_like_code(val: str, code: Optional[str]) -> bool:
    v = re.sub(r"\s+", "", val).lower().rstrip(":")
    if code and v == re.sub(r"\s+", "", code).lower():
        return True
    return bool(re.fullmatch(r"[A-Za-z&. ]{2,40}\s?\d{4}[A-Za-z]?(?:\s*/\s*(?:[A-Za-z ]+\s)?\d{4}[A-Za-z]?)?\s*[A-Za-z]?\s*:?", val.strip()))


def _title_like(line: str) -> bool:
    return bool(re.match(r"^[A-Za-z][A-Za-z ,&:'’\-()]+\d?$", line.strip()))


def _name_near_code(text: str, code: Optional[str]) -> Optional[str]:
    lines = [l.strip() for l in text.split("\n")]
    number = code.split()[-1] if code else None
    for i, line in enumerate(lines[:40]):
        if not number or number.lower() not in line.lower():
            continue
        # "KIN 2000 Physical Activity and Health" / "Classical Studies 1000 — 001: ANCIENT GREECE AND ROME"
        after = re.split(rf"{re.escape(number)}\s*(?:/\s*[A-Za-z]{{0,4}}\s*\d{{4}}[A-Za-z]?)?\s*(?:[-–—]\s*\d{{3}})?\s*[:\-–—]?\s*", line, maxsplit=1, flags=re.I)
        if len(after) == 2 and after[1].strip():
            cand = after[1].strip(" :-–—")
            cand = re.sub(r"\s*\(.*?\)\s*$", "", cand)
            # "Health Sciences 2800: Health" wraps onto "Sciences Research Methods";
            # "HS 2610G: Introduction to Ethics" wraps onto "and Health"
            if i + 1 < len(lines) and _title_like(lines[i + 1]) and len(lines[i + 1].split()) <= 5 \
                    and not _SKIP_NAME.search(lines[i + 1]) and not _HEADING_WORDS.match(lines[i + 1]) \
                    and (len(cand.split()) <= 2 or lines[i + 1].split()[0].lower() in ("and", "of", "for", "in", "to", "with", "the", "on", "&")):
                cand = cand + " " + lines[i + 1]
            name = _clean_name(cand)
            if name:
                return name
        # "Biological Macromolecules (Biochem 3381A)"
        m = re.match(r"^(.{6,90}?)\s*\((?:[A-Za-z ]+\s)?" + re.escape(number) + r"\)", line, re.I)
        if m:
            name = _clean_name(m.group(1))
            if name:
                return name
        # "Aquatic Ecology 3415G Winter 2025 Course Outline", "Ecology, BIO 2483A, Fall 2025 term.",
        # "Cellular Physiology-Physiology 3140A": the words before the number, minus the subject token
        if len(after) == 2:
            before = line[:line.lower().find(number.lower())]
            before = _SUBJECT_TOKEN.sub("", before).strip(" :-–—,/")
            if before and before.count("(") == before.count(")") and before.lower() not in {x.lower() for x in SUBJECTS} and _title_like(before) \
                    and not re.match(r"^(?:department|school|faculty)\b", before, re.I):
                name = _clean_name(before)
                if name:
                    return name
        # the title line above the code ("Crime and Punishment ..." / "Applied Logic for Computer Science1"),
        # else the line below ("Computer Science 3340b" / "Analysis of Algorithms I")
        for j in (i - 1, i + 1):
            if 0 <= j < len(lines) and _title_like(lines[j]):
                name = _clean_name(lines[j])
                if name:
                    return name
    return None


def _name_in_parentheses(pages_text: Sequence[Tuple[int, str]], code: Optional[str]) -> Optional[str]:
    """'Math 1228 (Methods of Finite Mathematics) covers ...' anywhere in the first three pages."""
    if not code:
        return None
    number = code.split()[-1]
    for _, text in pages_text[:3]:
        for m in re.finditer(rf"\b{re.escape(number)}\s*\(([A-Z][A-Za-z ,&:'’\-]{{5,80}})\)", text):
            name = _clean_name(m.group(1))
            if name:
                return name
    return None


def _department_and_number(text: str) -> Optional[str]:
    """'Department of Biology' + a heading 'Aquatic Ecology 3415G' -> 'Biology 3415G';
    'Microbiology & Immunology' + '3300B' on the next line -> 'Microbiology & Immunology 3300B'."""
    lines = [l.strip() for l in text.split("\n")[:12]]
    dept = None
    for l in lines:
        m = re.match(r"^(?:department|school|faculty|dept\.?)\s+of\s+([A-Z][A-Za-z&, ]{2,50})$", l, re.I)
        if m:
            dept = m.group(1).strip()
            break
        if l in SUBJECTS:
            dept = l
            break
    if not dept:
        return None
    for l in lines:
        m = re.search(r"(?<![A-Za-z\d])(\d{4}[A-Za-z]?)(?:\s*/\s*[A-Za-z])?\b", l)
        if m and not re.search(r"20\d{2}", m.group(1)) and not re.search(r"requisite|minimum|former|@|\d{3}-\d{4}", l, re.I):
            return _norm_code(dept, m.group(1))
    return None


def _title(s: str) -> str:
    s = s.strip()
    if s.isupper():
        small = {"and", "of", "the", "in", "to", "for", "a", "an", "on"}
        words = s.lower().split()
        return " ".join(w if (w in small and i) else w.capitalize() for i, w in enumerate(words))
    return s


def extract_course(pages_text: Sequence[Tuple[int, str]], filename: str = "") -> Tuple[Optional[str], Optional[str]]:
    first = pages_text[0][1] if pages_text else ""
    first_page_num = pages_text[0][0] if pages_text else 1
    cands = _candidates_from_text(first) if first_page_num == 1 else []
    code = None
    if cands:
        cands.sort(key=lambda c: -c[0])
        code = cands[0][1]
    if not code or (cands and cands[0][0] < 20):
        dept = _department_and_number(first)
        if dept:
            code = dept
    if not code:
        code = _code_from_filename(filename)
    if not code and first:
        # an e-mail alias like cs3342@uwo.ca
        m = re.search(r"\b([a-z]{2,9})(\d{4})[a-z]?@uwo\.ca", first, re.I)
        if m and m.group(1).upper() in ABBREVIATIONS:
            code = _norm_code(m.group(1), m.group(2))
    name = None
    if first_page_num == 1:
        name = _name_from_label(first, code) or _name_near_code(first, code)
    if not name:
        name = _name_in_parentheses(pages_text, code)
    if name and code:
        subject = " ".join(code.split()[:-1]).lower()
        if name.lower().replace(" ", "") == code.lower().replace(" ", "") or name.lower() == subject:
            name = None
    return code, name
