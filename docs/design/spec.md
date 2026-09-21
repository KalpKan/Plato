# Plato — design spec: "Registrar's ledger"

**Locked 2026-09-21, before any implementation commit.** Written with MengTo's
`design-first-ui-prompting` skeleton, filled from the PRIMARY direction in the portfolio repo's
`docs/design/app-directions.md` § *3. plato*. `no-ai-design-slop` runs as a passive gate over every
section added below. Nothing in this file may be softened during the build; if reality contradicts it,
amend this file first and say why.

Source of truth for the direction: `/Users/kalp/projects/portfolio/docs/design/app-directions.md`,
section "## 3. plato" → "### Primary direction — Registrar's ledger".

---

## GOAL

- Turn a Western course-outline PDF into a checked `.ics`. Three screens: **drop the PDF**, **proof the
  extraction**, **take the file**.
- For: a Western undergrad at the start of term, doing this once per course, four times in an evening,
  on a laptop, in a hurry, and slightly anxious about missing a deadline.
- Success: the user can scan nine assessment rows and spot the one with no date in under three seconds,
  and trusts the `.ics` enough to import it without re-checking the PDF.
- Visual thesis (one, for the whole product): **a course outline is a legal-ish document, and this is
  the clerk's ledger you proof it against before you sign.** Warm paper, ruled rows, a serif term
  header, and a stamp where something is missing.

## FORMAT

- Responsive web, designed at **1440** and **390**. Flask + Jinja2 + vanilla JS; no framework, no build
  step, one Python function on Vercel.
- Ledger sheet measure: **900 px**. Drop screen measure: **1080 px**. Gutter 24 px at 1440, 16 px at 390.
- Top margin **96 px** at 1440 (56 px at 390) so the sheet reads as a page, not a viewport.

## LAYOUT

**One shell on all three routes** (`base.html`), which is the fix for audit item P2 "two unrelated
visual languages":

- Skip link (`Skip to content`) as the first focusable element on every page.
- Masthead rule: the `Plato / Course outline to calendar` lockup left; the step rail right —
  `01 Upload · 02 Review · 03 Download`, active step in ink, the others at 45 %, with a hairline
  under the active one. (`number-details`.)
- A single hairline under the header; `0 1px 2px` lift only once the page is scrolled.
- `container-lines`: two 1 px vertical guides at the sheet's left and right edges, with 6 px corner
  squares at the sheet's four corners. Behind content, `pointer-events: none`.

**Screen 1 — `/`.** No marketing layer at all.

- The drop zone **is** the hero: a full-measure ruled rectangle at the top of the page, serif line
  inside it, the constraints underneath.
- Beside it at ≥ 1100 px: **one real, cropped, captioned screenshot of the review ledger** (taken from
  this build, not a mockup), so the first-time visitor sees the good screen instead of a sales pitch.
- Under both: the three honest constraints as a ruled definition list (`What Plato reads` /
  `What it cannot` / `What you get`) — three rows of a list, **not** three icon-tile cards.
- DELETED: the eyebrow pill, the sentence headline, the gradient CTA, the faux-calendar background with
  its fabricated `Lecture 1 / Assignment 1 / Midterm` chips, the "How It Works" section, the animated
  connector diagram with its dangling second line, the three interchangeable feature cards.

**Screen 2 — `/review`.** The ledger.

- **Masthead block**: course code + course name in the serif, then a definition grid with hairline rules
  — Term / First day / Last day / Exam period. Two columns at 1440, one at 390.
- **Reading line**: the completeness statement, rewritten as sentences (see COPY).
- **"What could not be read from the PDF"**: kept exactly, as a ruled margin-note block, not a card.
- **Slots**: ONE three-row table — `Kind / Section / Meets` — covering lecture, lab and tutorial. Not
  three separate sections, not three cards. The `no lab time was found…` sentence sits in the table's
  `Meets` cell for that row, with the `Add a slot` control as a text button beside it.
- **Assessments**: ONE table, ruled between every row:
  `# / Assessment / Weight / Date / Flag`. Ordinals mono in the first column (`number-details`),
  right-aligned mono numerals for weight and date, the total weight in a `<tfoot>` row.
  A flagged row gets a **row tint** plus the pill — never an accent stripe welded to a card side.
- **Study reminders** stays a `<details>`, its table ruled the same way.
- **No section is a card. Ever.** Grouping is rules and spacing.

**Screen 3 — the download.** A confirmation block naming the file, the event count and the date range.
Implemented without changing the server contract: `POST /review` still streams `text/calendar`
(seven tests depend on it). The page intercepts its own submit with `fetch`, saves the blob, reads the
two new response headers `X-Plato-Events` and `X-Plato-Range`, and renders the confirmation in place.
Any failure falls back to the native form POST, so the no-JS path is byte-identical to today.

**Mobile (390).** The assessment table becomes one ruled block per assessment: name on line 1 at 15 px,
weight and date on line 2 in mono, the flag as a trailing pill; the block keeps the row tint so flags
still scan. The masthead grid becomes a two-column label/value list. The step rail collapses to
`Step 02 of 03 · Review`. The drop zone stays full width with a 44 pt tap target.
**Never a horizontal scroller.**

## TYPE SYSTEM

Three families, self-hosted (SIL OFL, `$0`, latin subset only, `font-display: swap`):

| Role | Family | Use |
|---|---|---|
| Serif | **Newsreader** | course name, sheet masthead, section heads, the drop-zone line. This is the type move; it is what makes it a ledger and not a dashboard. |
| Sans | **Inter** | controls, labels, helper text, body |
| Mono | **JetBrains Mono** | dates, weights, times, ordinals, the file name — `font-variant-numeric: tabular-nums` |

Scale (rendered px):

- Masthead course name — serif 600 30/1.1 (24 at 390)
- Section head — serif 600 19/1.25
- Body / table cell — sans 400 14/1.5 (15 at 390 for the assessment name)
- Numerals — mono 13, tabular
- Field label / column header — sans 500 11 uppercase, tracking 0.06em. Used **only** as column headers
  and form labels — never as an eyebrow above a heading.
- Helper / margin note — sans 400 13/1.55, ink-2

## COLOR + MATERIAL

Light is the ground. Tokens (`:root`):

```
--paper    #faf8f4   page
--sheet    #ffffff   the ledger surface
--paper-2  #f4f1ea   row hover / thead fill
--ink      #1c1a17   text
--ink-2    #5c574f   secondary text
--rule     #e0dad0   hairlines
--rule-2   #cdc4b6   stronger rules (table head, sheet edge)
--flag     #9a6a00   THE accent — "Plato could not read this; you must check it"
--flag-bg  #fff6e0   flagged row tint
--link     #1f5fbf   links and focus only
```

- **One accent, and it is the flag colour.** Amber appears nowhere decorative.
- Blue is links + focus ring only. The old `#2563eb` gradient CTA becomes a flat solid ink button.
  Gradients leave the product entirely.
- Material: paper. **No shadows** except `0 1px 2px rgba(28,26,23,.06)` under the sticky header once
  scrolled, and the same single `Beautiful sm`-weight lift on the one screenshot plate
  (`beautiful-shadows`, one strength per component, never stacked, never tinted).
- `--shadow-glow: 0 0 24px rgba(59,130,246,0.15)` is **deleted** from the codebase.
- Radii: 2 px on inputs and pills, 0 on rules and tables. No 14–18 px card radius anywhere.
- **Dark variant via `prefers-color-scheme: dark` only, never a toggle** (per the direction). It is the
  same ledger with warm ink inverted: `--paper #16140f`, `--sheet #1c1a15`, `--ink #f2ede3`,
  `--rule #332f27`, `--flag #e6ad45` on `--flag-bg #2a2415`, `--link #8fb4f0`. Contrast re-checked at
  rendered size; nothing else changes.

## IMAGERY / UI STYLE

- **Two real screenshots, maximum**, both of Plato's own review screen, cropped tight, captioned, one
  aspect ratio, WebP. Produced by running this build locally against a real Western outline. No
  illustration, no fake calendar, no abstract SVG, no device mockup, no invented course names.
- Icons: keep **Lucide**, at 16 px, 1.5 px stroke, inline with text, never in a rounded tile. Every
  icon that sits above a heading is deleted.

## COPY (render EXACTLY where quoted — these are live and good)

Kept verbatim:

- "Plato" / "Course outline to calendar"
- "Drag and drop your course outline here" / "PDF only, up to 4 MB. Not a PDF, or a scan? Enter the
  course by hand."
- "Review & Confirm" / "Check every date against your outline; click any highlighted field to correct
  it. Your edits are saved for you only."
- "What could not be read from the PDF"
- "Reading your outline… this takes 10–25 seconds on the free hosting."
- "No lab time was found in the outline (labs are usually only on draftmyschedule.uwo.ca). Add one if
  you have a lab."
- "This tool is not affiliated with Western University" / "Developed by Kalp Kansara"
- Western's sessional-dates helper line, the whole `/manual` form, "Enter the course by hand".

Rewritten (audit P2, "confusing summary copy"):

- `100% OF 100% FOUND (+1.0 BONUS)` → **"All 9 assessments found. Weights total 101 %."**
  (pluralised and adapted honestly: the bonus clause only appears when there is bonus weight, and the
  sentence says "Weights total 93 % — 7 % is unaccounted for." when the total is under 100.)
- `1 / 0 / 0 LECTURE / LAB / TUTORIAL SLOTS` → **"1 lecture slot. No lab, no tutorial."**
- New h1 on `/`: **"Check your outline, then take the calendar."**

Deleted: the pill "Automatic Course Calendar Generation"; the h1 "From Course Outline to Calendar in
Seconds"; the three feature-card descriptions; "Get Started".

## CONSTRAINTS

```
FONT   Newsreader + Inter + JetBrains Mono
STYLE  ruled ledger on warm paper
MODE   light (dark only via prefers-color-scheme, never a toggle)
```

## NEGATIVE PROMPT

- No hero pill, no gradient text, no gradient buttons, no radial lights, no dark glass.
- No card around anything. Nine assessments are nine table rows.
- No animated connector diagrams, no pulsing calendar, no floating particles.
- No fabricated calendar chips, no invented course names in decoration, no "trusted by N students".
- No accent stripe welded to the side of a container.
- No WebGL, no Three.js, no Lenis, no scroll-jacking, no scroll-scrubbed sequences. This is a deadline
  tool.

---

## Motion system

One easing family, from `animation-systems`. Every animation below names the goal it serves
(1 hierarchy, 2 feedback, 3 attention, 4 continuity, 5 polish); anything that served none was deleted.

```
--ease        cubic-bezier(.22, 1, .36, 1)   /* entering / emphasis — expo.out */
--ease-exit   cubic-bezier(.4, 0, 1, 1)      /* leaving — faster, ease-in     */
--d-micro     140ms   hover, press, row tint
--d-state     200ms   toggle, flag appear/disappear
--d-small     260ms   inline editor, modal, confirmation
--d-section   420ms   section entrance
--d-hero      700ms   masthead masked reveal
--stagger      60ms   (35ms per word in the masthead; 40ms on 390)
```

| # | Moving component | What it does | Why (goal) | Skill |
|---|---|---|---|---|
| M1 | Masthead reveal (`/review`) | the serif course line rises word-by-word through an overflow mask, 700 ms, 35 ms stagger, once | 1 — names the document before the rows | `masked-reveal` (CSS implementation, see note) |
| M2 | Sheet entrance | masthead → slots → assessments fade + rise 12 px, 420 ms, 60 ms stagger, once | 1, 3 — establishes reading order top-down | `animation-systems` A, `animation-on-scroll` |
| M3 | Below-fold sections | same primitive, fired by IntersectionObserver at 20 % / `-10%` rootMargin, once | 3 | `animation-on-scroll` |
| M4 | Drop zone dragover | rule hairline → 2 px ink, inner paper-2 tint, 140 ms | 2 — the target is armed | `animation-systems` (micro) |
| M5 | File accepted | the zone's prompt cross-fades to the file line, 260 ms, scale .98 → 1 | 2, 4 | `animation-systems` B |
| M6 | Parse progress | a hairline sweeps left→right under "Reading your outline…" **only while parsing**, with `aria-live="polite"` on the text | 2 — a 25 s operation must look alive | `animation-systems` |
| M7 | Inline edit open/close | field → input, 260 ms fade + scale .98 → 1; close uses `--ease-exit` at 200 ms | 2, 4 | `animation-systems` B/C |
| M8 | **Flag retires** | when a fix lands, the row's amber tint fades out and the pill collapses (width + opacity), 320 ms | 2, 3 — the payoff animation of the whole app: you fixed it, the stamp leaves | `animation-systems` |
| M9 | Flag appears | tint in + pill in, 200 ms | 3 | `animation-systems` |
| M10 | Row hover / focus | `--paper-2` fill, 140 ms | 2 — keeps the eye on one row while scanning a column | `animation-systems` |
| M11 | Modal (add assessment / add slot) | backdrop 160 ms fade, panel 260 ms fade + 8 px rise; exit 200 ms `--ease-exit`; focus trapped, Esc closes | 4 | `animation-systems` C |
| M12 | Download confirmation | the block reveals fade + rise 12 px, 420 ms, after the file is saved | 2 | `animation-systems` A |
| M13 | Step rail underline | the hairline under the active step scales X 0 → 1, 420 ms, on load | 1 | `number-details` + `animation-systems` |

**No perpetual motion behind content.** M6 is the only repeating animation and it exists only while a
parse is in flight, in the foreground, as the status indicator itself.

**`masked-reveal` note.** The skill's recipe uses GSAP ScrollTrigger. Loading GSAP from a CDN for one
headline on a page whose whole thesis is restraint (and whose hosting budget is a single cold-starting
Python function) fails the skill's own taste test, so M1 implements the identical motion — per-word
`overflow:hidden` mask, `translateY(110%) → 0`, `power3.out` ≈ `--ease`, 0.8 s, 0.035 s stagger, once —
in CSS with a 12-line splitter. `aria-label` carries the un-split text, exactly as the skill requires.

**Reduced motion.** `@media (prefers-reduced-motion: reduce)` sets every animation and transition to
`0.01ms` **and forces the complete final state**: `opacity:1; transform:none; visibility:visible`,
words un-masked, tints applied instantly, the progress sweep replaced by a static rule. The JS gates
(`matchMedia`) skip word-splitting and mark reveal targets visible immediately, so a reduced-motion
visitor never sees a partial state. This is audit item P2 "unguarded motion" — today `style.css` has
`modalSlideIn`, `calendarPulse`, `workflowStep1/2/3`, `rotateProcessing`, `processingPulse`,
`arrowLine1/2`, `arrowParticle1/2` (10 keyframes) plus ~30 `transition: all` rules and **no** media
query at all. Most of those keyframes belong to elements this redesign deletes; the survivors are
listed above and every one is guarded. `transition: all` is banned — every transition names its
properties.

---

## Accessibility (audit P3)

- One skip link per page, first in tab order, visible on focus.
- `:focus-visible` ring token: `2px solid var(--link)` with a 2 px offset, on every control, link,
  editable field, table row action and the drop zone.
- `aria-live="polite"` on the upload progress line and on the inline-save notice; the existing
  `role="alert"` on the upload error is kept.
- The assessment ledger is a real `<table>` with `<caption>`, `<th scope>`; the editable cells are
  `<button>`-semantics (`role="button"`, `tabindex="0"`, Enter/Space) so the whole proofing task is
  keyboard-reachable.
- Contrast verified at rendered size in both colour schemes; the amber flag text is `--flag` on
  `--flag-bg`, checked ≥ 4.5:1.
- Modals: focus trapped, Esc closes, focus returns to the opener.

## Kept from today (non-negotiable)

The entire extraction/flagging model and its amber "Not found" / "Needs a date" semantics; the
completeness figures; the draftmyschedule explanation; the honest free-hosting timing note; the
"Enter the course by hand" escape hatch and the whole `/manual` form; the Western sessional-dates
helper; the non-affiliation footer; every copy string quoted above; Lucide as the icon source; the
`role="alert"` on upload error; every PostHog event; `/api/health`; the `/download/<filename>` route;
the `text/calendar` contract of `POST /review`.

## Primary action

- `/` → **the drop zone itself** ("Drag and drop your course outline here"), not a button.
- `/review` → **Generate calendar**. One primary per screen; "Add another assessment" and "Add a slot"
  are secondary and stop being filled pills — they become text buttons with a hairline underline.

## MengTo skills used, and exactly where

| Skill | Where it lands in this build |
|---|---|
| `design-first-ui-prompting` | this document — the GOAL → NEGATIVE PROMPT skeleton is its structure, filled once and locked before code |
| `no-ai-design-slop` | passive gate on every section: the removal test was run on the pill, the gradient CTA, the faux calendar, the workflow diagram, the nine cards, the four stat tiles and the icon tiles — all deleted; the ruled table replaced them |
| `light-mode-paper-technical` | the whole system: warm paper surfaces, precise hairline geometry, one restrained accent that punctuates rather than dominates |
| `book-serif-index` | the `/review` masthead and assessments table — serif-led page, mono index column, margin notes for the "could not be read" explanations |
| `container-lines` | the 900 px sheet's two vertical guides + 6 px corner squares |
| `number-details` | `01 02 03` on the step rail, and the assessment ordinals in the ledger's first column |
| `animation-systems` | the motion tokens, the one easing family, every duration above, the reduced-motion policy |
| `animation-on-scroll` | M2/M3, the IntersectionObserver entrance, once-only, threshold 0.2 |
| `masked-reveal` | M1, the masthead word reveal (CSS implementation of the skill's motion, see note) |
| `beautiful-shadows` | the single `Beautiful sm`-weight lift on the screenshot plate and the scrolled header — one strength, neutral, never stacked |
| `build-awwwards-quality-sites` | the quality bar: one thesis per screen, real content, no filler section, verified at both viewports |

**Deliberately not used** (the direction's do-not list): `gsap-scrolltrigger-storytelling`,
`cinematic-scroll-storytelling`, `cinematic-gsap-lenis-motion-system`, `mesh-gradient-dark-blue-clean`,
`atmosphere-background`, `dark-blue-contrasting-clean`, `funky-purple-container-tech`,
`beam-glow-states`, `scroll-scrubbed-word-reveal`, and every WebGL / particle skill.
