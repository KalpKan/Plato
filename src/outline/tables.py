"""Normalise pdfplumber tables: drop spacer columns and re-align body cells to the header.

pdfplumber often returns a header whose text sits one column away from the body text
("| Assessment | | Format |" over "Physical Activity | | Complete Template | |"), and a
wrapped row may land one cell in a neighbouring column. Each body cell is assigned to the
nearest header column, so the result has exactly one column per header cell.
"""
from __future__ import annotations

from typing import List, Optional, Sequence


def compress_table(table: Sequence[Sequence[Optional[str]]]) -> List[List[str]]:
    rows = [[(c or "").strip() for c in r] for r in table if r]
    if not rows:
        return []
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    head_pos = [i for i, c in enumerate(rows[0]) if c]
    body_pos = sorted({i for r in rows[1:] for i, c in enumerate(r) if c})
    shifted = bool(body_pos) and any(i not in head_pos for i in body_pos)
    if len(rows) >= 2 and head_pos and len(head_pos) >= 2 and head_pos != body_pos and (
            len(body_pos) >= len(head_pos) or (shifted and len(body_pos) >= len(head_pos) - 1)):
        # header cells shifted relative to the body: assign every body cell to the nearest header column
        out = [[rows[0][i] for i in head_pos]]
        for r in rows[1:]:
            cells = [""] * len(head_pos)
            for i, c in enumerate(r):
                if not c:
                    continue
                j = min(range(len(head_pos)), key=lambda k: (abs(head_pos[k] - i), head_pos[k] < i))
                cells[j] = (cells[j] + " " + c).strip() if cells[j] else c
            out.append(cells)
        return out
    keep = [i for i in range(width) if any(r[i] for r in rows)]
    return [[r[i] for i in keep] for r in rows]
