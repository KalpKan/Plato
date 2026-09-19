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


def _name_near_code(text: str, code: Optional[str]) -> Optional[str]:
    lines = [l.strip() for l in text.split("\n")]
    number = code.split()[-1] if code else None
    for i, line in enumerate(lines[:40]):
        if not number or number.lower() not in line.lower():
            continue
        # "KIN 2000 Physical Activity and Health" / "Classical Studies 1000 — 001: ANCIENT GREECE AND ROME"
        after = re.split(rf"{re.escape(number)}\s*(?:[-–—]\s*\d{{3}})?\s*[:\-–—]?\s*", line, maxsplit=1, flags=re.I)
        if len(after) == 2 and len(after[1].strip()) >= 6 and not _SKIP_NAME.search(after[1]):
            cand = after[1].strip(" :-–—")
            cand = re.sub(r"\s*\(.*?\)\s*$", "", cand)
            if 6 <= len(cand) <= 90 and not re.search(r"\d{3,}", cand):
                return _title(cand)
        # "Biological Macromolecules (Biochem 3381A)"
        m = re.match(r"^(.{6,90}?)\s*\((?:[A-Za-z ]+\s)?" + re.escape(number) + r"\)", line, re.I)
        if m and not _SKIP_NAME.search(m.group(1)):
            return _title(m.group(1))
        # name on the next line ("Computer Science 3340b" / "Analysis of Algorithms I")
        for j in (i + 1, i - 1):
            if 0 <= j < len(lines):
                cand = lines[j]
                if 6 <= len(cand) <= 90 and not _SKIP_NAME.search(cand) and not re.search(r"\d{3,}", cand) \
                        and re.match(r"^[A-Za-z][A-Za-z ,&:'\-]+$", cand):
                    return _title(cand)
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
    name = _name_near_code(first, code) if first_page_num == 1 else None
    if name and code and name.lower().replace(" ", "") == code.lower().replace(" ", ""):
        name = None
    return code, name
