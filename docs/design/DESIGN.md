# Plato — DESIGN.md

The design system as shipped, read off `public/static/style.css` rather than off intentions.
Codename **Registrar's ledger**. The brief it implements is the PRIMARY direction in the portfolio
repo's `docs/design/app-directions.md` § *3. plato*; the locked spec is `docs/design/spec.md`.

> **Thesis.** A course outline is a legal-ish document, and this is the clerk's ledger you proof it
> against before you sign: warm paper, ruled rows, a serif term header, and a stamp where something
> is missing.

---

## 1. Ground

Light. Warm paper, never white-on-grey, never a dark dashboard. A dark variant exists **only** under
`prefers-color-scheme: dark`; there is no toggle, by design.

| Token | Light | Dark | Job |
|---|---|---|---|
| `--paper` | `#faf8f4` | `#16140f` | the page |
| `--sheet` | `#ffffff` | `#1c1a15` | the drop zone, inputs, the one image plate |
| `--paper-2` | `#f4f1ea` | `#232019` | row hover / focus-within |
| `--ink` | `#1c1a17` | `#f2ede3` | text, the primary button |
| `--ink-2` | `#5c574f` | `#b8b0a2` | secondary text |
| `--ink-3` | `#6f6a61` | `#968f83` | labels, ordinals, captions, footer |
| `--rule` | `#e0dad0` | `#332f27` | hairlines between rows |
| `--rule-2` | `#cdc4b6` | `#46413a` | table heads, sheet edges, corner squares |
| `--flag` | `#8a5f00` | `#e6ad45` | **the only accent** |
| `--flag-bg` | `#fff6e0` | `#2a2415` | the flagged row's tint |
| `--link` | `#1f5fbf` | `#8fb4f0` | links and the focus ring, nothing else |

**The accent has exactly one meaning: "Plato could not read this — you must check it."** It marks a
flagged row's tint, its pill, the parser-notes block, the `Needs a date` badge and the upload error.
It is never decorative, never a gradient, and never used to make something look important.

**Contrast, measured at rendered size** (WCAG 2.1 AA, ≥ 4.5:1 for body text):

| Pair | Light | Dark |
|---|---|---|
| `--ink` on `--paper` | 16.4 | 15.8 |
| `--ink-2` on `--paper` | 6.8 | 8.6 |
| `--ink-3` on `--paper` | 5.1 | 4.9 |
| `--ink-3` on `--paper-2` | 4.8 | 5.1 |
| `--flag` on `--flag-bg` | 5.3 | 7.7 |
| `--flag` on `--paper` | 5.3 | 9.1 |
| `--link` on `--paper` | 5.7 | 8.7 |

Two documented deviations from the direction's literal hexes, both for contrast: the accent is
`#8a5f00` rather than `#9a6a00` (which measured **4.40:1** on its own `#fff6e0` row tint, just under
AA — the shipped value is the same amber at 5.25:1), and `--ink-3` is `#6f6a61` rather than the
`#8a8378` the first draft used (3.54:1).

## 2. Material

Paper. Flat surfaces, hairline rules, 2 px radius on inputs and pills, **0 radius on tables and
rules**. There is no card in the product.

Exactly two shadows exist:

- `--lift-head` `0 1px 2px rgba(28,26,23,.06)` — under the sticky header, only once scrolled.
- `--lift-plate` — `beautiful-shadows` "sm", neutral, on the single screenshot plate on `/`.

No glow, no glass, no blur, no gradient anywhere. `--shadow-glow` was deleted from the codebase.

## 3. Type

Three families, self-hosted from `public/static/fonts/` (SIL OFL latin subsets, 138 KB total,
`font-display: swap`, no font CDN).

| Role | Family | Where |
|---|---|---|
| Serif | **Newsreader** | the page headline, the masthead course name, every section head, the drop-zone line |
| Sans | **Inter** | body, controls, labels, helper text |
| Mono | **JetBrains Mono** | dates, weights, times, ordinals, the file name — `tabular-nums` |

| Role | Spec |
|---|---|
| Page headline (`/`) | serif 600 34/1.12, `-0.015em` |
| Masthead course name | serif 600 30/1.1 (24 at 390) |
| Section head | serif 600 19/1.25 |
| Body / table cell | sans 400 14/1.5 (15 for the assessment name at 390) |
| Numerals | mono 13, tabular |
| Column header / form label | sans 500 11 uppercase, `0.06em` — **only** as a column header or a form label, never as an eyebrow above a heading |
| Helper, margin note, caption | sans 400 12–13/1.55, `--ink-2` / `--ink-3` |

## 4. Structure

- **Measure.** 900 px for the ledger, 1080 px for the drop screen (`body.route-upload`). Gutter 24 px,
  16 px at 390. Top margin 96 px so the sheet reads as a page.
- **`container-lines`.** Two 1 px vertical guides at the sheet's edges with four 6 px corner squares,
  behind content, `pointer-events: none`.
- **One shell for every route** (`templates/base.html`): skip link, the `Plato / Course outline to
  calendar` lockup, and the `01 Upload · 02 Review · 03 Download` rail (`number-details`), collapsing
  to `Step 02 of 03 · Review` below 760 px.
- **Grouping is rules and spacing, never a container.** A definition grid for the masthead, hairline
  rules between rows, one blank line between blocks.
- **Tables are tables.** `<caption>`, `<th scope>`, a `<tfoot>` total. Nine assessments are nine `<tr>`,
  and a row's explanation is its own `<tr class="assessment-note">` — a `<p>` inside a `<tr>` is
  invalid HTML and browsers hoist it out of the table.
- **At 390** the table becomes one ruled block per row (`display: block` on the rows, `thead` visually
  hidden, the ordinal in a 44 px gutter). The row tint survives, so flags still scan.
  **There is never a horizontal scroller.**

## 5. Controls

- **One primary per screen**, and it is ink on paper, not a coloured pill: `Drag and drop your course
  outline here` (the zone itself) on `/`, `Generate calendar` on `/review`.
- **Secondary actions are text with a hairline underline** (`.btn-quiet`) — `Add Section`,
  `Add another assessment`, `Remove file`, `Back to upload`. They stopped being filled pills.
- **Editable fields** carry a dotted underline, tint on hover, `role="button"` + `tabindex="0"`, and
  open an inline editor on click, Enter or Space.
- **Focus** is `2px solid var(--link)` at 2 px offset, on every control, link, editable field and the
  drop zone. One skip link per page.

## 6. Motion

One easing family. Every beat has a reason and a reduced-motion final state. The full table lives in
`docs/design/spec.md` § *Motion system*; the tokens are:

```
--ease       cubic-bezier(.22, 1, .36, 1)   entering / emphasis
--ease-exit  cubic-bezier(.4, 0, 1, 1)      leaving, faster
--d-micro    140ms   hover, press, row tint
--d-state    200ms   toggle, flag appear
--d-small    260ms   inline editor, modal, file accepted
--d-section  420ms   section entrance
--d-hero     700ms   the masked headline
--stagger     60ms   (35ms per word)
```

- **Entrances** (`animation-on-scroll`): fade + 12 px rise, once, IntersectionObserver at
  threshold 0.2 / `-10%`, never replayed.
- **The headline on `/`** rises word-by-word through an overflow mask (`masked-reveal`, implemented in
  CSS — one headline does not justify GSAP on a cold-starting Python function). The un-split text is
  on `aria-label`. The `/review` masthead does **not** use it: its course line is editable and must
  not be split.
- **The payoff beat** is the flag retiring: fix a date and the row's amber tint fades and the pill
  collapses in 320 ms. That is the animation the app exists for.
- **`transition: all` is banned.** Every transition names its properties.
- **Only one repeating animation exists** — the hairline that sweeps under "Reading your outline…" —
  and it runs only while a parse is in flight, in the foreground, as the status indicator itself.
- **`prefers-reduced-motion: reduce`** zeroes every duration **and forces the complete final state**:
  words un-masked, tints applied instantly, the sweep replaced by a static rule. The JS gates on
  `matchMedia` so a reduced-motion visitor never sees a partial state.
- **Content never depends on the script.** `[data-reveal]` only starts hidden once `initMotion()` has
  added `html.motion-ready`, and the first uncaught error removes it again.

## 7. Imagery

Two real screenshots maximum, both of Plato's own review screen, cropped tight, captioned, WebP.
Today there is one: `public/static/img/review-ledger.webp`, a 940×602 crop of this build reading
Biochemistry 3381A's outline. **No illustration, no abstract SVG, no device mockup, and above all no
fabricated calendar** — the old hero's invented "Lecture 1 / Assignment 1" chips were the single
worst thing on the site.

Icons are Lucide at 16 px, 1.5 px stroke, inline with text, never inside a rounded tile. Every icon
that used to sit above a heading is gone.

## 8. The do-not list

No hero pill. No gradient text, buttons or backgrounds. No radial lights, glass or dark panels. No
card around anything. No animated connector diagrams, pulsing calendars or floating particles. No
fabricated data of any kind. No accent stripe welded to a container's side. No WebGL, no Lenis, no
scroll-jacking — this is a tool somebody uses while anxious about a deadline.

## 9. Where the rules are enforced

`tests/test_design.py` fails the build if the glow token, the old dark palette, a third easing curve,
an unguarded `[data-reveal]`, a `transition: all`, the fabricated calendar chips, the workflow
diagram, the stat tiles or the unparseable "of 100% found" fraction come back.
