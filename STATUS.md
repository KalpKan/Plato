# Plato — status

Night protocol acknowledged 2026-09-21 06:23 UTC.

## Definition of done — "Registrar's ledger" redesign (2026-09-21)

Each item is ticked only with evidence (a command's output, a URL check, or a screenshot path).

| # | Criterion | Evidence | Done |
|---|---|---|---|
| 1 | `docs/design/spec.md` locked before any code, MengTo skills listed with where each is used | file exists, committed before the first implementation commit | [ ] |
| 2 | Warm-paper "Registrar's ledger" renders at 1440 and 390 on `/`, `/review`, `/manual` | screenshots in `docs/images/redesign/` | [ ] |
| 3 | The dangling connector diagram and the fabricated "Lecture 1 / Assignment 1" calendar chips are gone from the source and the live page | `grep` returns nothing; live page check | [ ] |
| 4 | Upload → `/review` → download works end to end on production with a real outline | live run on https://plato.kalpkan.com with a real PDF, .ics opened | [ ] |
| 5 | Every keyframe respects `prefers-reduced-motion`; one easing family | `style.css` audit + a reduced-motion screenshot | [ ] |
| 6 | pytest green (except the pre-existing `test_corpus` parser gate), ≤ 2 deploys, live on https://plato.kalpkan.com | raw pytest output; `vercel ls` | [ ] |
| 7 | reviewer APPROVE + verifier PASS | sub-agent verdicts | [ ] |
| 8 | `docs/design/DESIGN.md` + README design section + one STATUS line in the portfolio repo | files committed | [ ] |

### Baseline recorded before any change

- `.venv/bin/pytest -q` on `main` @ `0bbf8d7`: **1 failed, 158 passed**. The single failure is
  `tests/test_corpus.py::test_corpus_scores` — the pre-existing parser corpus gate (portfolio-ops
  records it as round-4 defect D26, "no_fabricated 67/69"). It is a parser/extraction defect, not a
  design one, and this redesign neither fixes nor worsens it.

## Needs Kalp

_(nothing yet)_
