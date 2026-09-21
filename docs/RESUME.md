# Where this left off

Written 2026-09-21 at the end of the "Registrar's ledger" redesign. If you are picking Plato up cold,
read `STATUS.md` first for the done-criteria and their evidence, then this file for what to do next.

**Status: shipped.** `redesign` was merged `--no-ff` into `main` (`03baa48`) and is live on
https://plato.kalpkan.com since 11:00:33 UTC on 2026-09-21. Reversal, if ever needed, is
`git revert -m 1 03baa48 && git push`.

## What was done

The three screens were rebuilt to the PRIMARY direction in the portfolio repo's
`docs/design/app-directions.md` § *3. plato*. The contract is `docs/design/spec.md` (locked before any
code, with an amendments section at the end), the shipped system is `docs/design/DESIGN.md`, and
`tests/test_design.py` fails the build if the deleted slop comes back.

Nothing in the extraction or flagging model was touched. `POST /review` still streams
`text/calendar` byte for byte; the only server changes are three summary sentences added to
`calculate_completeness`, two additive response headers (`X-Plato-Events`, `X-Plato-Range`), and a
`step` value for the header rail.

## Next steps, in order

1. **The parser corpus gate is still red, and it was red before this work.**
   `tests/test_corpus.py::test_corpus_scores` fails on `main` at `0bbf8d7` exactly as it fails now —
   it is round-4 defect **D26** in `docs/reports/plato.md` (`no_fabricated` 67/69: an HS 2610G
   midterm placed on reading week, and Calc 1301B quizzes resolved from "week of Jan 19"). That is
   the single highest-value thing left in this repo and it is a parser problem, not a design one.
   Baseline for comparison: `main` = 1 failed / 158 passed; `redesign` = 1 failed / 175 passed.
2. **Round-4 defects D27 (prose tutorial slots) and D28 (titles)** from the same report.
3. **Google / Apple import screenshots** — still owed from round 3, still not captured.

## The reviews

Two independent reviewers both returned REJECT. Four blocking defects between them, all fixed and
each re-verified in a live browser before the merge; `STATUS.md` has the table with the evidence.
Three are worth remembering because the test suite could not see any of them:

- **Numbers on a reassurance surface must be true.** `X-Plato-Events` counted `BEGIN:VEVENT`, but a
  weekly lecture is ONE VEVENT with an `RRULE`, so the download screen said 22 for a calendar that
  imports 74. If you touch `ics_event_span`, keep expanding recurrences.
- **A partial payload is a lying page.** `/api/update-field` hand-picked keys out of
  `calculate_completeness` and dropped the summary sentences, so the top of `/review` kept asserting
  a stale count after the very interaction the product exists for. Return the dict whole.
- **HTTP headers are latin-1.** Both `X-Plato-Range` and the `Content-Disposition` filename are
  ASCII-guarded. An en dash in the first one crashed the entire download inside werkzeug.

## Things to know before touching the front end

- **One accent.** `--flag` means exactly one thing: "Plato could not read this — you must check it."
  If something new needs colour to look important, it needs better hierarchy instead.
- **One easing family**, and every animation must land on a complete static final state under
  `prefers-reduced-motion: reduce`. `transition: all` is banned and a test enforces it.
- **Content never depends on the script.** `[data-reveal]` only starts hidden once `initMotion()` has
  added `html.motion-ready`; the first uncaught error removes it. Do not reintroduce a bare
  `[data-reveal] { opacity: 0 }`.
- **`app.js` binds to `.assessment-item` `<tr>` rows**, and a row's explanation is its own
  `<tr class="assessment-note">` — a `<p>` inside a `<tr>` is invalid HTML and browsers hoist it out
  of the table. `applyRowState` maintains both.
- **Two tests pin copy that looks incidental but is not**: `tests/test_flow.py` asserts the string
  `Add Section`, and `tests/test_round3.py` reads the lecture meeting description out of the
  `<option>` text as its D22 regression guard. Do not "tidy" either.
- **HTTP headers are latin-1.** `X-Plato-Range` must stay ASCII; an en dash there raised
  `UnicodeEncodeError` inside werkzeug and killed the whole download response.

## Running it

```bash
cd ~/projects/plato
SECRET_KEY=anything-random .venv/bin/python -m flask --app src.app run --port 5055
SECRET_KEY=test .venv/bin/pytest -q            # expect the one corpus failure above
```

To reach `/review` you must upload a real outline; `~/projects/plato-corpus/pdfs/` has the corpus.
The first parse of a given PDF takes 10–25 s, then it is cached by hash.

Browser notes for whoever verifies next: Chrome on this machine runs in **dark** mode at **50% page
zoom**, so you will see the `prefers-color-scheme: dark` variant unless you inject the light `:root`
tokens, and `resize_window` cannot reach a 390 viewport — use a same-origin 390 px iframe, which is
how `docs/images/redesign/*-390.png` were taken.
