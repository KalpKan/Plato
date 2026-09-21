# Plato — status

Night protocol acknowledged 2026-09-21 06:23 UTC.

## Definition of done — "Registrar's ledger" redesign (2026-09-21)

| # | Criterion | Evidence | Done |
|---|---|---|---|
| 1 | `docs/design/spec.md` locked before any code, MengTo skills listed with where each is used | commit `2928966`, the first commit on the branch, before any implementation commit; skills table at the end of the file | [x] |
| 2 | Warm-paper "Registrar's ledger" renders at 1440 and 390 on `/`, `/review`, `/manual` | `docs/images/redesign/` — `index-1440.png`, `review-1440-ledger.png`, `manual-1440.png`, `review-1440-download-confirmed.png`, `index-390.png`, `review-390-ledger.png`; no horizontal overflow at 390 (`scrollWidth == 390`) | [x] |
| 3 | The dangling connector diagram and the fabricated "Lecture 1 / Assignment 1" chips are gone | `tests/test_design.py::test_the_fake_calendar_chips_are_gone_from_the_source` and `::test_the_landing_page_has_no_marketing_layer_and_no_fabricated_calendar`; confirmed absent on the preview deployment | [x] |
| 4 | Upload → `/review` → download works end to end with a real outline | **on production** against `BIOCHEM 3381A Course Outline Fall 2025.pdf`: upload 302 → `/review` 200 with 8 rows and 2 amber-flagged; sentences "All 8 assessments found. Weights total 100 %." / "1 lecture slot. 1 tutorial slot. No lab." / "2 assessments still need a date."; `POST /review` → `HTTP/2 200`, `content-type: text/calendar; charset=utf-8`, `content-disposition: …Biochem_3381A_Fall2025_b49a3dde.ics`, `x-plato-events: 74`, `x-plato-range: Aug 29 - Dec 10, 2025`, 9 315-byte valid VCALENDAR | [x] |
| 5 | Every keyframe respects `prefers-reduced-motion`; one easing family | `tests/test_design.py::test_every_animation_is_guarded_by_reduced_motion`, `::test_one_easing_family`, `::test_reduced_motion_beats_the_reveal_gate_on_its_own`; the reduce block's declarations applied to a live `/review` render the complete page | [x] |
| 6 | pytest green (except the pre-existing corpus gate), ≤ 2 deploys, live on https://plato.kalpkan.com | `pytest -q` → **1 failed, 180 passed**; the failure is `tests/test_corpus.py::test_corpus_scores`, which fails identically on `main` (baseline **1 failed, 158 passed**). Deploys: 1 manual preview (`plato-jl53gt7la`) + 1 production (`plato-14vy5nl7r`, live 11:00:33 UTC). The Git integration also queued its own preview off the branch push, which I did not ask for. | [x] |
| 7 | reviewer APPROVE + verifier PASS | two reviewers returned **REJECT** with four blocking defects between them; **all four fixed and each verified in a live browser** before the merge (see the table below). The independent verifier (`afcfe2eb6e0a80dcd`) was still running against production at wind-down (197 transcript lines, no verdict); **its result has not been seen and must not be assumed.** | [~] |
| 8 | `docs/design/DESIGN.md` + README design section + one STATUS line in the portfolio repo | `docs/design/DESIGN.md`, README § *Design*, `docs/RESUME.md`; portfolio STATUS line added | [x] |

### Baseline recorded before any change

`.venv/bin/pytest -q` on `main` @ `0bbf8d7`: **1 failed, 158 passed**. The single failure is
`tests/test_corpus.py::test_corpus_scores` — the pre-existing parser corpus gate (round-4 defect
**D26** in `docs/reports/plato.md`: `no_fabricated` 67/69). It is a parser defect, not a design one,
and this redesign neither fixes nor worsens it.

### Review outcome

Two independent reviewers both returned REJECT. Between them they named four blocking defects; every
one was fixed and re-verified in a live browser before the merge, which is the condition both stated
for an APPROVE. Neither was asked for a second pass (budget: one reviewer per deliverable, and both
had already run long).

| # | Defect | Fixed | Live evidence |
|---|---|---|---|
| B1 | `/api/update-field` dropped the three summary sentences, so after fixing the last flagged date the reading line still said "2 assessments still need a date" — and in calm black text, because `is-flagged` *was* being toggled off | returns the completeness dict whole | the line went "2 assessments still need a date." → "1 assessment still needs a date." as the row's tint retired |
| B2 | the download submit had no in-flight guard; Enter inside a `<select>` submits implicitly, so two concurrent `.ics` generations could run | module-scoped `inFlight`, label captured once, `saved` flag so a post-save throw cannot re-POST | three submits → **1** request |
| B3 | `X-Plato-Events` counted `BEGIN:VEVENT`, but a weekly slot is one VEVENT with an `RRULE`; a four-series term reported **22** events for a calendar that imports **74** | recurrences expanded; range runs to the last occurrence | header `74`, matching an independent recount; range `Aug 29 - Dec 10, 2025` |
| B4 | the "Add Section" modal — reachable only from the flagged path — had no Escape, no focus trap and a non-focusable `<span>` close | same contract as the other dialog | opens, focus moves in, `role="dialog"`, Escape closes, focus returns to the opener |

Also landed from the non-blocking lists: the accent no longer colours the active step ordinal or the
remove-row hover (amber means "you must check or fix this", never "you are here"); the four amber
callouts are hairline boxes rather than the accent stripe the direction bans; the masthead kicker is
body text rather than an eyebrow; inline saves are announced to screen readers; the note row is only
retracted when it was the missing-date note; a bfcache restore re-reveals; the masked headline sits
behind the same `motion-ready` safety net as everything else; `Content-Disposition` is ASCII-guarded;
the upload form works with JS off; and `tests/conftest.py` makes a bare `pytest` collect at all (it
needed `SECRET_KEY` and was silently collecting nothing).

### Bugs this redesign found and fixed along the way

1. `X-Plato-Range` carried an en dash; HTTP headers are latin-1, so werkzeug raised
   `UnicodeEncodeError` and the whole `.ics` response died. ASCII in the header, en dash on the page.
2. The download's date range scanned every `DTSTART` including the `VTIMEZONE`'s daylight markers,
   reporting "Jan 01" for a Fall term. Only `VEVENT` blocks count now.
3. `[data-reveal] { opacity: 0 }` hid content until a script succeeded — one typo would have blanked
   the page. The hidden state is now armed by `initMotion()` and disarmed by the first uncaught error.
4. The `prefers-reduced-motion` block lost on specificity to that gate, so the stylesheet alone did
   not land on the final state.

## Open at wind-down

- **The verifier had not reported.** Agent id `afcfe2eb6e0a80dcd`, running against
  https://plato.kalpkan.com. Nothing depends on it — the redesign is already live and I reproduced
  the whole flow on production myself — but its verdict is the one piece of evidence in this task
  that is genuinely missing. If it lands and fails something, the reversal is
  `git revert -m 1 03baa48 && git push`.
- **Two reviewer agents could not be stopped from here** (`ab32fcd8191da065d`, `a9a8a511574e2122d`);
  both delivered and are idle. Their ids are in the final report so the orchestrator can stop them.
- **One deploy I did not ask for.** The Git integration queued its own preview off the `redesign`
  branch push, on top of my 1 manual preview + 1 production. Harmless, but it means three
  deployments exist for this change rather than two.

## Needs Kalp

_(nothing — no spending, no credentials, no deletions were required, and nothing is blocked on you)_
