# Plato — status

Night protocol acknowledged 2026-09-21 06:23 UTC.

## Definition of done — "Registrar's ledger" redesign (2026-09-21)

| # | Criterion | Evidence | Done |
|---|---|---|---|
| 1 | `docs/design/spec.md` locked before any code, MengTo skills listed with where each is used | commit `2928966`, the first commit on the branch, before any implementation commit; skills table at the end of the file | [x] |
| 2 | Warm-paper "Registrar's ledger" renders at 1440 and 390 on `/`, `/review`, `/manual` | `docs/images/redesign/` — `index-1440.png`, `review-1440-ledger.png`, `manual-1440.png`, `review-1440-download-confirmed.png`, `index-390.png`, `review-390-ledger.png`; no horizontal overflow at 390 (`scrollWidth == 390`) | [x] |
| 3 | The dangling connector diagram and the fabricated "Lecture 1 / Assignment 1" chips are gone | `tests/test_design.py::test_the_fake_calendar_chips_are_gone_from_the_source` and `::test_the_landing_page_has_no_marketing_layer_and_no_fabricated_calendar`; confirmed absent on the preview deployment | [x] |
| 4 | Upload → `/review` → download works end to end with a real outline | locally against `BIOCHEM 3381A Course Outline Fall 2025.pdf`: 8 rows, 2 flagged, `POST /review` → `text/calendar`, 21–22 `BEGIN:VEVENT`, confirmation block read "Biochem_3381A_Fall2025_b49a3dde.ics / 22 events / Aug 29 – Dec 08, 2025". **Production re-run pending the merge.** | [ ] |
| 5 | Every keyframe respects `prefers-reduced-motion`; one easing family | `tests/test_design.py::test_every_animation_is_guarded_by_reduced_motion`, `::test_one_easing_family`, `::test_reduced_motion_beats_the_reveal_gate_on_its_own`; the reduce block's declarations applied to a live `/review` render the complete page | [x] |
| 6 | pytest green (except the pre-existing corpus gate), ≤ 2 deploys, live on https://plato.kalpkan.com | `pytest -q` → **1 failed, 175 passed**; the failure is `tests/test_corpus.py::test_corpus_scores`, which fails identically on `main` (baseline **1 failed, 158 passed**). Deploy 1 of 2 = preview `plato-jl53gt7la`. **Production pending.** | [ ] |
| 7 | reviewer APPROVE + verifier PASS | pending | [ ] |
| 8 | `docs/design/DESIGN.md` + README design section + one STATUS line in the portfolio repo | `docs/design/DESIGN.md`, README § *Design*; portfolio STATUS line pending | [ ] |

### Baseline recorded before any change

`.venv/bin/pytest -q` on `main` @ `0bbf8d7`: **1 failed, 158 passed**. The single failure is
`tests/test_corpus.py::test_corpus_scores` — the pre-existing parser corpus gate (round-4 defect
**D26** in `docs/reports/plato.md`: `no_fabricated` 67/69). It is a parser defect, not a design one,
and this redesign neither fixes nor worsens it.

### Bugs this redesign found and fixed along the way

1. `X-Plato-Range` carried an en dash; HTTP headers are latin-1, so werkzeug raised
   `UnicodeEncodeError` and the whole `.ics` response died. ASCII in the header, en dash on the page.
2. The download's date range scanned every `DTSTART` including the `VTIMEZONE`'s daylight markers,
   reporting "Jan 01" for a Fall term. Only `VEVENT` blocks count now.
3. `[data-reveal] { opacity: 0 }` hid content until a script succeeded — one typo would have blanked
   the page. The hidden state is now armed by `initMotion()` and disarmed by the first uncaught error.
4. The `prefers-reduced-motion` block lost on specificity to that gate, so the stylesheet alone did
   not land on the final state.

## Needs Kalp

_(nothing — no spending, no credentials, no deletions were required)_
