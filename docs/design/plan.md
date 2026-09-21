# Plato "Registrar's ledger" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild Plato's three screens as a warm-paper ruled ledger — no cards, no marketing layer, no fabricated calendar, one amber accent that only ever means "Plato could not read this" — without changing one line of the extraction/flagging model.

**Architecture:** Flask + Jinja2 + vanilla JS, no build step. One shared shell (`base.html`) for all routes; a single new `style.css` built on paper tokens and hairline rules; `app.js` gains a small motion module (one easing family, IntersectionObserver entrances, `matchMedia` reduced-motion gates) and its review handlers move from `.assessment-item` divs to real `<table>` rows. The server contract is unchanged except for two additive response headers on the `.ics` that let the page render a download confirmation in place.

**Tech Stack:** Python 3.12 / Flask 3, Jinja2, vanilla ES2017, CSS custom properties, self-hosted Newsreader + Inter + JetBrains Mono (SIL OFL, latin subset woff2), Lucide from unpkg (already present), pytest, Vercel Python function.

**Spec:** `docs/design/spec.md` (locked 2026-09-21, commit `2928966`). Read it before any task; every task below argues from it.

## Global Constraints

- **Keep from today, exactly:** the extraction/flagging model and its amber "Not found" / "Needs a date" semantics; the completeness figures; the draftmyschedule sentence; "Reading your outline… this takes 10–25 seconds on the free hosting."; "Enter the course by hand" and the whole `/manual` form; the Western sessional-dates helper; the non-affiliation footer; Lucide; `role="alert"` on upload error; every PostHog event; `/api/health`; `/download/<filename>`.
- **`POST /review` must keep returning `mimetype == "text/calendar"`.** Seven tests assert it (`tests/test_flow.py:59,113,217`, `tests/test_app_fixes.py:90,194`, `tests/test_round3.py:256,296`). Never change that.
- **Keep the strings `Add Section` and `Add another assessment`** — `tests/test_flow.py:204` asserts the first, and the direction only asks that they stop being filled pills.
- Tokens are exactly the spec's hexes. One accent (`--flag #9a6a00`). `--link #1f5fbf` for links/focus only.
- One easing family: `--ease cubic-bezier(.22,1,.36,1)`, `--ease-exit cubic-bezier(.4,0,1,1)`. Durations 140 / 200 / 260 / 420 / 700 ms.
- Every animation has a `prefers-reduced-motion: reduce` path that lands on the **complete static final state**.
- `transition: all` is banned. `border-radius` > 2 px is banned. `box-shadow` only the two the spec names.
- No new runtime dependency, no CDN except the Lucide script already there, $0.
- Branch `redesign`. Every commit ends `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Baseline: `.venv/bin/pytest -q` is **1 failed, 158 passed** before any change; the one failure is the pre-existing parser gate `tests/test_corpus.py::test_corpus_scores`. Any other failure is mine.

---

## File Structure

| File | Responsibility |
|---|---|
| `public/static/style.css` | **rewritten.** The whole ledger system: tokens, type, rules, tables, forms, motion, reduced motion, dark scheme, 390 breakpoint. |
| `public/static/fonts/*.woff2` + `OFL.txt` | Self-hosted latin subsets of Newsreader / Inter / JetBrains Mono. |
| `templates/base.html` | Shell: skip link, header lockup + step rail, container lines, flash messages, footer, script tags. |
| `templates/index.html` | Screen 1: drop zone as hero, the review screenshot plate, the three-row constraints list. No marketing. |
| `templates/review.html` | Screen 2: masthead definition grid, summary sentences, parser notes, slots table, assessments table, reminders, actions, modal; plus the screen-3 confirmation block markup (hidden until a download lands). |
| `templates/manual.html` | Same form, ledger styling, fieldset/legend semantics. |
| `templates/error.html` | Ledger-styled error page. |
| `public/static/app.js` | Review interactions retargeted at table rows; motion module; reduced-motion gates; fetch-based download + confirmation with native fallback. |
| `src/app.py` | Two additive `.ics` response headers; `summary_sentences()` folded into `calculate_completeness`; `step` passed to the template. |
| `tests/test_design.py` | **new.** Asserts the slop removals, the copy rewrites, the reduced-motion guard, the table structure, the a11y landmarks and the new headers. |
| `docs/design/DESIGN.md` | The shipped design system, derived from the built result. |
| `docs/images/redesign/*.png` | 1440 + 390 screenshots of all three screens, light + reduced motion. |

---

### Task 1: Server — summary sentences, `.ics` headers, step context

**Files:**
- Modify: `src/app.py` (`calculate_completeness` ~341, `ics_response` ~306, `index()` ~517, `review()` context ~945, `manual()` ~973)
- Test: `tests/test_design.py` (create)

**Interfaces:**
- Produces: `calculate_completeness(data)` gains three keys used by both the template and `app.js`:
  - `summary_assessments: str` — e.g. `"All 9 assessments found. Weights total 101 %."`
  - `summary_slots: str` — e.g. `"1 lecture slot. No lab, no tutorial."`
  - `summary_undated: str` — e.g. `"1 assessment still needs a date."` or `"Every assessment has a date."`
- Produces: `ics_response(filename, ics_bytes)` sets `X-Plato-Events` (int as str) and `X-Plato-Range` (`"Sep 09 – Dec 08, 2026"` or `""`), and exposes both via `Access-Control-Expose-Headers`.
- Produces: every `render_template` call passes `step=1|2|3` for the header rail.

- [ ] **Step 1: Write the failing tests** in `tests/test_design.py`

```python
"""Design-system guarantees for the Registrar's ledger redesign."""
from pathlib import Path

from src.app import app, calculate_completeness, ics_response
from src.models import ExtractedCourseData, CourseTerm, AssessmentTask, SectionOption
from datetime import date, datetime, time

ROOT = Path(__file__).resolve().parent.parent


def _data(**kw):
    d = ExtractedCourseData()
    d.course_code = kw.get("course_code", "BIOL 1001A")
    d.course_name = kw.get("course_name", "Test Course")
    d.term = CourseTerm(term_name="Fall 2026", start_date=date(2026, 9, 9), end_date=date(2026, 12, 8))
    d.assessments = kw.get("assessments", [])
    d.lecture_sections = kw.get("lecture_sections", [])
    d.lab_sections = kw.get("lab_sections", [])
    d.tutorial_sections = kw.get("tutorial_sections", [])
    return d


def test_summary_sentences_replace_the_unparseable_fraction():
    a = [AssessmentTask(title=f"A{i}", type="assignment", weight_percent=10,
                        due_datetime=datetime(2026, 10, i + 1, 23, 59)) for i in range(9)]
    a[0].weight_percent = 11  # total 101
    lec = SectionOption(section_type="Lecture", section_id="001", days_of_week=[0],
                        start_time=time(9, 30), end_time=time(10, 20))
    c = calculate_completeness(_data(assessments=a, lecture_sections=[lec]))
    assert c["summary_assessments"] == "All 9 assessments found. Weights total 101 %."
    assert c["summary_slots"] == "1 lecture slot. No lab, no tutorial."
    assert c["summary_undated"] == "Every assessment has a date."


def test_summary_says_what_is_missing_when_weights_fall_short():
    a = [AssessmentTask(title="Midterm", type="midterm", weight_percent=40,
                        due_datetime=datetime(2026, 10, 20, 23, 59)),
         AssessmentTask(title="Final", type="final", weight_percent=53)]
    c = calculate_completeness(_data(assessments=a))
    assert c["summary_assessments"] == "2 assessments found. Weights total 93 % — 7 % is unaccounted for."
    assert c["summary_slots"] == "No lecture, lab or tutorial slot was found."
    assert c["summary_undated"] == "1 assessment still needs a date."


def test_ics_response_carries_the_event_count_and_range():
    ics = (b"BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nDTSTART;VALUE=DATE:20260909\r\nEND:VEVENT\r\n"
           b"BEGIN:VEVENT\r\nDTSTART:20261208T235900\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
    with app.test_request_context():
        r = ics_response("x.ics", ics)
    assert r.headers["X-Plato-Events"] == "2"
    assert r.headers["X-Plato-Range"] == "Sep 09 – Dec 08, 2026"
    assert "X-Plato-Events" in r.headers["Access-Control-Expose-Headers"]
```

- [ ] **Step 2: Run them and watch them fail**

Run: `.venv/bin/pytest -q tests/test_design.py`
Expected: FAIL — `KeyError: 'summary_assessments'`, `KeyError: 'X-Plato-Events'`.

- [ ] **Step 3: Implement.** In `calculate_completeness`, after `metrics['assessments_undated']` is computed, build the three sentences. Rules, exactly:
  - counted assessments = all rows (bonus included in the count, excluded from the weight, as today).
  - `summary_assessments`: `"All {n} assessments found."` when `total_weight >= 99.5`, else `"{n} assessments found."`; then `" Weights total {t:g} %."` — and when `t < 99.5`, `" Weights total {t:g} % — {100-t:g} % is unaccounted for."` instead; and when `bonus_weight`, append `" Plus {b:g} % bonus, not counted."`. `n == 1` uses "assessment".
  - `summary_slots`: join the non-zero kinds as `"{k} lecture slot(s)"`, then `"{k} lab slot(s)"`, `"{k} tutorial slot(s)"`; the absent ones collapse into one trailing sentence `"No lab, no tutorial."`; if all three are zero the whole string is `"No lecture, lab or tutorial slot was found."`.
  - `summary_undated`: `"Every assessment has a date."` when `assessments_undated == 0`, else `"{u} assessment(s) still needs a date."` (`"still need a date."` when plural).
  In `ics_response`, count `ics_bytes.count(b"BEGIN:VEVENT")`, scan every `DTSTART` for `YYYYMMDD`, and format the min/max as `"%b %d"` – `"%b %d, %Y"`. Set both headers plus `Access-Control-Expose-Headers`.
  Pass `step=1` from `index()`, `step=2` from `review()`'s GET render and `manual()`, `step=3` from nothing (the confirmation is client-side).

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/pytest -q tests/test_design.py && .venv/bin/pytest -q --ignore=tests/test_corpus.py`
Expected: PASS, 158 passed.

- [ ] **Step 5: Commit** `feat: summary sentences, .ics event-count headers, step context`

---

### Task 2: Self-hosted type

**Files:**
- Create: `public/static/fonts/{newsreader-600,newsreader-400,inter-400,inter-500,inter-600,jetbrains-mono-400,jetbrains-mono-500}.woff2`, `public/static/fonts/OFL.txt`

- [ ] **Step 1:** Fetch each family's latin-subset woff2 from `fonts.gstatic.com` (the URLs come from `https://fonts.googleapis.com/css2?family=...` requested with a modern UA). All three are SIL Open Font License 1.1 — free to self-host and redistribute; record the licence text and the three copyright lines in `OFL.txt`.
- [ ] **Step 2:** Verify each file is a real woff2 (`file public/static/fonts/*.woff2` says "Web Open Font Format (Version 2)") and the whole directory is under 400 KB.
- [ ] **Step 3: Commit** `feat: self-host Newsreader, Inter and JetBrains Mono (SIL OFL latin subsets)`

---

### Task 3: The stylesheet

**Files:**
- Rewrite: `public/static/style.css`
- Test: `tests/test_design.py` (extend)

- [ ] **Step 1: Write the failing tests**

```python
CSS = (ROOT / "public/static/style.css").read_text()


def test_the_glow_and_the_dark_saas_palette_are_gone():
    for dead in ("--shadow-glow", "#09090b", "#2563eb", "linear-gradient(135deg, #2563eb",
                 "calendarPulse", "workflowStep1", "arrowParticle1", "rotateProcessing"):
        assert dead not in CSS, f"{dead} survived the redesign"


def test_every_keyframe_is_guarded_by_reduced_motion():
    import re
    assert "@media (prefers-reduced-motion: reduce)" in CSS
    guard = CSS.split("@media (prefers-reduced-motion: reduce)", 1)[1]
    assert "animation-duration: 0.01ms" in guard and "transform: none" in guard
    assert "transition: all" not in CSS


def test_one_easing_family():
    import re
    curves = set(re.findall(r"cubic-bezier\([^)]*\)", CSS))
    assert curves <= {"cubic-bezier(.22, 1, .36, 1)", "cubic-bezier(.4, 0, 1, 1)"}, curves


def test_paper_tokens_are_the_spec_tokens():
    for token, value in (("--paper", "#faf8f4"), ("--sheet", "#ffffff"), ("--ink", "#1c1a17"),
                         ("--rule", "#e0dad0"), ("--flag", "#9a6a00"), ("--flag-bg", "#fff6e0"),
                         ("--link", "#1f5fbf")):
        assert f"{token}: {value}" in CSS
```

- [ ] **Step 2:** Run: `.venv/bin/pytest -q tests/test_design.py -k "glow or keyframe or easing or paper"` — Expected FAIL.
- [ ] **Step 3: Write the stylesheet.** Sections, in order: `@font-face` block (7 faces, `font-display: swap`); `:root` tokens (colour, type, space 4 px scale, motion); `prefers-color-scheme: dark` token remap; reset + `body` on `--paper`; skip link; `:focus-visible` ring; header + step rail + `number-details` ordinals; `container-lines` guides + corner squares; sheet; masthead definition grid; summary sentences; margin-note block; `.ledger` table (hairline rules, `thead` in the 11 px uppercase label, mono tabular numerals, `tfoot` total, row hover, `tr.needs-review` tint, flag pill); inline editor; drop zone + its states; buttons (primary = solid ink, secondary = text + hairline underline); forms; modal; confirmation block; footer; the 13 motion keyframes; the 390 breakpoint (table → ruled blocks via `display: block` on `tbody tr` with `data-label` pseudo-headers); one final `@media (prefers-reduced-motion: reduce)` block that zeroes every duration and forces final states.
- [ ] **Step 4:** Run the four tests — PASS.
- [ ] **Step 5: Commit** `feat: the ledger stylesheet — warm paper, hairline rules, one easing family`

---

### Task 4: The shell (`base.html`)

**Files:** Modify `templates/base.html`; Test: `tests/test_design.py`

**Interfaces:** Produces the DOM contract the other templates and `app.js` rely on: `a.skip-link[href="#content"]`, `header.sheet-head`, `ol.step-rail > li.step[aria-current="step"]`, `main#content.sheet`, `div.container-lines`.

- [ ] **Step 1: Failing test**

```python
def test_every_route_shares_one_shell_with_a_skip_link_and_the_step_rail():
    app.config["TESTING"] = True
    with app.test_client() as c:
        for path, active in (("/", "01"), ("/manual", "02")):
            html = c.get(path).get_data(as_text=True)
            assert 'class="skip-link" href="#content"' in html
            assert 'id="content"' in html
            assert "Course outline to calendar" in html
            assert 'class="step-rail"' in html and ">01<" in html and ">03<" in html
            assert 'aria-current="step"' in html
```

- [ ] **Step 2:** Run it — FAIL (no skip link today).
- [ ] **Step 3:** Rewrite `base.html`: skip link first; `<header class="sheet-head">` with the lockup (Lucide `calendar-check` at 16 px inline, not in a tile) and `<ol class="step-rail">` whose three `<li>` carry `<span class="step-n">01</span> Upload` etc., `aria-current="step"` on the active one from `step`; `<main id="content" class="sheet">`; the container-lines div; footer copy unchanged; `?v=5` on the css/js query strings.
- [ ] **Step 4:** Run — PASS.
- [ ] **Step 5: Commit** `feat: one ledger shell for every route, with a skip link and the step rail`

---

### Task 5: Screen 1 — the drop zone is the hero

**Files:** Modify `templates/index.html`; Test: `tests/test_design.py`

- [ ] **Step 1: Failing test**

```python
def test_the_landing_page_has_no_marketing_layer_and_no_fabricated_calendar():
    with app.test_client() as c:
        html = c.get("/").get_data(as_text=True)
    for dead in ("Automatic Course Calendar Generation", "From Course Outline to Calendar in Seconds",
                 "Get Started", "How It Works", "calendar-background", "workflow-visualization",
                 "arrow-particle", "Lecture 1", "Assignment 1", "feature-icon"):
        assert dead not in html, f"{dead} survived on /"
    assert "Check your outline, then take the calendar." in html
    assert "Drag and drop your course outline here" in html
    assert "PDF only, up to 4 MB." in html
    assert "Enter the course by hand" in html
    assert 'aria-live="polite"' in html
```

- [ ] **Step 2:** Run — FAIL.
- [ ] **Step 3:** Rewrite `index.html`: `h1` (serif) "Check your outline, then take the calendar."; one sub-line; the ruled drop zone with the exact kept strings, the `role="alert"` error `<p>`, the file line, the `Read the outline` primary and the `aria-live="polite"` progress line; beside it (`≥1100px`) `<figure class="plate">` with `static/img/review-ledger.webp` and a caption naming the course it really shows; below, a three-row `<dl class="constraints">`. Keep the "re-read the PDF" checkbox. Keep all upload JS behaviour; delete the calendar-pulse and workflow scripts entirely.
- [ ] **Step 4:** Run — PASS.
- [ ] **Step 5: Commit** `fix: delete the fabricated calendar hero and the dangling connector diagram`

---

### Task 6: Screen 2 — the ledger

**Files:** Modify `templates/review.html`, `public/static/app.js`; Test: `tests/test_design.py`

**Interfaces:** the DOM contract `app.js` binds to, which replaces the old `.assessment-item` div:
- `table.ledger.assessments > tbody > tr.assessment-item[data-assessment-index]`
- cells: `td.c-ordinal`, `td.c-name > .editable-field.assessment-title`, `td.c-weight > .editable-field`, `td.c-date > .editable-field`, `td.c-flag` (holds `.badge-needs-date` and the remove button), and `tr.assessment-note > td[colspan=5] > p.date-reason` — the note is its **own row**, because a `<p>` inside a `<tr>` is invalid HTML and browsers hoist it out of the table.
- slots: `table.ledger.slots > tbody > tr[data-slot="lecture"|"lab"|"tutorial"]`, each with `td.c-section` (the `<select>` or the no-data sentence + `Add Section`) and `td.c-meets`.
- summary: `p[data-summary="assessments"|"slots"|"undated"]`.

- [ ] **Step 1: Failing test**

```python
def test_the_review_screen_is_a_table_not_nine_cards(review_client):
    html = review_client.get("/review").get_data(as_text=True)
    assert "assessment-item" in html and "<table" in html
    assert 'class="ledger assessments"' in html
    assert "of 100% found" not in html          # the unparseable fraction is gone
    assert 'data-summary="assessments"' in html
    assert "Check every date against your outline" in html
    assert "What could not be read from the PDF" in html or "notes" not in html
    assert "Add Section" in html                # kept, restyled
    assert "stat-item" not in html and "summary-stats" not in html
```

(`review_client` is a fixture that uploads the text PDF used by `tests/test_flow.py::test_happy_path`.)

- [ ] **Step 2:** Run — FAIL.
- [ ] **Step 3:** Rewrite `review.html` to the structure above and retarget `app.js`:
  - `applyRowState` writes the badge into `td.c-flag`, toggles `tr.needs-review`, and creates/removes the sibling `tr.assessment-note` instead of appending a `<p>` to the item.
  - `applyCompleteness` writes `summary_assessments` / `summary_slots` / `summary_undated` into the three `p[data-summary]` and drops the four `data-tile` lookups.
  - `addManualSection` finds its row with `document.querySelector('[data-slot="' + sectionType + '"]')` instead of matching `h3` text, and injects the `<select>` into that row's `td.c-section`.
  - `removeAssessment` removes the row **and** its note row.
  - `initEditableFields` keeps `.editable-field` as the hook, and gains `role="button" tabindex="0"` handling for Enter/Space.
- [ ] **Step 4:** Run: `.venv/bin/pytest -q --ignore=tests/test_corpus.py` — 159 passed.
- [ ] **Step 5: Commit** `feat: /review is one ruled ledger — nine rows, not nine cards`

---

### Task 7: Screen 3 — the download confirmation

**Files:** Modify `templates/review.html`, `public/static/app.js`; Test: `tests/test_design.py`

- [ ] **Step 1: Failing test** — asserts `POST /review` still streams `text/calendar` *and* now carries the two headers, and that the confirmation block exists in the markup with `hidden`.

```python
def test_download_still_streams_ics_and_now_names_the_file(review_client):
    r = review_client.post("/review", data={"lecture_section": "0", "lab_section": "none"})
    assert r.mimetype == "text/calendar"
    assert int(r.headers["X-Plato-Events"]) > 0
    assert r.headers["X-Plato-Range"]
```

- [ ] **Step 2:** Run — FAIL if Task 1 regressed; otherwise confirm the markup assertion fails.
- [ ] **Step 3:** Add `<section id="download-done" class="confirm" hidden aria-live="polite">` to `review.html` and, in `app.js`, intercept the review form's submit: `fetch(action, {method:'POST', body:new FormData(form)})`, on a `text/calendar` response save the blob via an object URL, read `X-Plato-Events` / `X-Plato-Range` and the `Content-Disposition` filename, reveal the block (M12), and revoke the URL. Any throw, any non-2xx, or a missing `fetch` falls through to `form.submit()` so the no-JS path is byte-identical to today.
- [ ] **Step 4:** Run the whole suite — PASS.
- [ ] **Step 5: Commit** `feat: name the file, the event count and the range after the download`

---

### Task 8: `/manual` and `/error` on the same paper

**Files:** Modify `templates/manual.html`, `templates/error.html`

- [ ] **Step 1:** No new test — `tests/test_flow.py` already exercises `/manual` end to end; run it first and keep it green.
- [ ] **Step 2:** Wrap each `section.form-section` in `<fieldset><legend>`, keep every input name and every copy string (especially the sessional-dates line), restyle as ruled rows, make `Add another assessment` a text button.
- [ ] **Step 3:** Run: `.venv/bin/pytest -q tests/test_flow.py` — PASS.
- [ ] **Step 4: Commit** `feat: /manual and the error page join the ledger`

---

### Task 9: Motion module + reduced motion

**Files:** Modify `public/static/app.js`, `public/static/style.css`; Test: `tests/test_design.py`

- [ ] **Step 1: Failing test**

```python
JS = (ROOT / "public/static/app.js").read_text()


def test_motion_is_gated_on_reduced_motion_in_js_too():
    assert "prefers-reduced-motion: reduce" in JS
    assert "calendarPulse" not in JS and "animateWorkflow" not in JS
    assert "IntersectionObserver" in JS
```

- [ ] **Step 2:** Run — FAIL.
- [ ] **Step 3:** Add `initMotion()` to `app.js`: one `const REDUCED = matchMedia('(prefers-reduced-motion: reduce)')`; when reduced, add `.is-in` to every `[data-reveal]` immediately and return; otherwise an `IntersectionObserver` (threshold 0.2, rootMargin `0px 0px -10% 0px`, `unobserve` after the first hit) adds `.is-in`, and `splitMaskedReveal()` wraps the masthead's words in `.word-mask > .word` with `--i` for the stagger and sets `aria-label` to the un-split text. Disconnect the observer on `pagehide`.
- [ ] **Step 4:** Run — PASS.
- [ ] **Step 5: Commit** `feat: one motion system, every beat with a reduced-motion final state`

---

### Task 10: Real screenshots, docs, gates

**Files:** `public/static/img/review-ledger.webp`, `docs/images/redesign/*.png`, `docs/design/DESIGN.md`, `README.md`

- [ ] **Step 1:** Run the app locally against a real outline from `~/projects/plato-corpus` (or `course_outlines/`), drive Chrome to `/review`, screenshot at 1440, crop to the ledger, save as WebP ≤ 120 KB. This is the only image on `/` and it must be this build's own screen.
- [ ] **Step 2:** Capture `docs/images/redesign/{index,review,manual}-{1440,390}.png` plus `review-1440-reduced-motion.png`.
- [ ] **Step 3:** Write `docs/design/DESIGN.md` from the shipped CSS (tokens, type roles, the table system, the motion table, reduced motion, the do-not list) and add a "Design" section to `README.md` pointing at the spec, the plan and DESIGN.md.
- [ ] **Step 4:** Gates: `.venv/bin/pytest -q` (expect the one pre-existing corpus failure and nothing else); `npx vercel@latest` preview deploy; claude-in-chrome at 1440 and 390 on the preview with a clean console; Lighthouse ≥ 0.90.
- [ ] **Step 5: Commit** `docs: DESIGN.md, README design section, redesign screenshots`

---

## Self-review

- **Spec coverage.** GOAL/FORMAT → Task 3+4. LAYOUT screen 1 → Task 5; screen 2 → Task 6; screen 3 → Tasks 1+7; mobile → Task 3 step 3. TYPE → Task 2+3. COLOR → Task 3. IMAGERY → Task 10 step 1. COPY kept → Tasks 5/6/8; COPY rewritten → Task 1 (server) + Task 6 (render). CONSTRAINTS/NEGATIVE → Task 3's four tests + Task 5's removal test. Motion table M1–M13 → Tasks 3 and 9. Accessibility → Tasks 4 (skip link, focus), 5 (aria-live), 6 (table semantics, keyboard editable fields), 7 (aria-live confirm). Kept-from-today → the Global Constraints, enforced by the existing suite.
- **Placeholders.** None: every test body and every token value is written out.
- **Type consistency.** `summary_assessments` / `summary_slots` / `summary_undated` are named identically in Task 1 (produced), Task 6 (rendered and re-applied by `applyCompleteness`). `X-Plato-Events` / `X-Plato-Range` identical in Tasks 1 and 7. `.assessment-item`, `.editable-field`, `.badge-needs-date`, `.date-reason` keep their existing names so the unchanged parts of `app.js` keep working; only their host elements change.
