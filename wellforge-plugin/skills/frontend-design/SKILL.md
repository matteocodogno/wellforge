---
name: frontend-design
description: >
  WellForge visual direction — deciding palette, typography, layout and the one signature
  element deliberately, instead of shipping the look every project in the same stack gets by
  default. Use when the designer is designing a NEW product surface (a greenfield project's
  first UI, a landing/marketing/public page, a standalone prototype or demo), when reshaping
  an existing UI's look on purpose, or when the user asks for something with "personality",
  "a visual identity", or that "doesn't look AI-generated". Do NOT use to add a feature
  inside a project that already has a design system — there the system wins. Authoritative
  reference for the surface-class gate, the two-pass token system, the anti-default
  calibration list, the contrast/motion floor, and how visual direction lands in design.md
  and the theme (never ad-hoc CSS).
---

# Frontend design — visual direction, gated

Everything else in WellForge pushes toward **sameness**, on purpose: reuse the component
library, match the surrounding code, never introduce a second UI library. That is correct for
the internal apps most of the pipeline builds, and wrong exactly when the surface *is* the
product — a landing page, a first impression, a demo someone decides on in eight seconds.

This skill is the narrow escape hatch. It is not a licence to redecorate: it applies to a
specific class of surface, produces a **token system** decided before any code, and hands that
system to frontend-dev to implement as **theme tokens**. Sameness stays the default; this is
the documented exception.

## The surface-class gate — run this first, state the result

| Surface | Verdict | What you do |
|---|---|---|
| A feature inside a project that already has a theme (every **adopted**/brownfield project, every scaffold past its first UI) | **The system wins** | Apply it well. No new palette, no new type pairing, no new radius scale. Reuse components, use existing tokens, add nothing to the token set. Read only the *Quality floor* and *CSS pitfalls* below, then go back to the designer's normal flow. |
| A new **public-facing** area of an existing product (first landing page, marketing site, docs shell, a new product line) | **Extend, don't restart** | Inherit the existing type system and neutral scale. You get **one** new axis — usually an accent plus the signature element. State what you inherited and what you changed. |
| A greenfield project's first UI, a standalone prototype, a demo or artifact whose whole job is impression | **Full direction** | The two-pass process below. |

Ambiguous? **Ask** — same rule as discovering the component library: never resolve ambiguity
by defaulting. And there is no path where distinctiveness beats a stated brief: **where the
user or the spec pins an axis down, that wins**, including when it asks for one of the
defaults listed below.

## Rigor tiers

Per [[rigor-tiers]]: `production`/`mvp` run the designer, so both passes run there. `spike`
never spawns the designer — but the main loop may load this skill when the spike's *whole
point* is a visual prototype. In that case run **pass 1 only**: name the tokens, skip the
critique round and the evidence log, mark it `// SPIKE:` and move.

## Pass 1 — the token system, before any code

Four named things. No prose designs, no "modern and clean" — every entry is a value someone
can implement or argue with.

- **Color** — 4–6 named hex values (`ink`, `paper`, `signal`, …), each with the job it does.
  Not "a palette generated from a hue"; roles first, then values.
- **Type** — the faces for 2+ roles: a characterful **display** face used with restraint, a
  **body** face that complements rather than echoes it, and a **utility** face if there is
  data or captions. Name the scale, weights and tracking. **State the delivery mechanism**
  per face — self-hosted (`@fontsource/*` or a local `woff2`) or a system stack. A CDN
  `<link>` is not a delivery mechanism in a project with a CSP or an offline build; check
  before you choose a face you cannot ship.
- **Layout** — one sentence of prose plus an ASCII wireframe. Compare two before picking one.
- **Signature** — the single element this page is remembered by, and why it belongs to *this*
  subject. One. Everything around it stays quiet.

Ground it in the actual subject. The spec's domain — its materials, artifacts, vocabulary,
the shape of its data — is where non-generic choices come from. If the spec doesn't pin the
subject down enough to design from, name the subject, its audience and the page's single job
yourself, and say that you did.

## Pass 2 — critique the plan, then write code

Review the token system against the brief **before** implementing. The test: *would this plan
come out roughly identical for a different brief in the same stack?* If yes, it is a default
wearing a plan's clothes — revise it and say what you changed and why.

Three looks currently dominate AI-generated design; all are legitimate for some briefs, and
none of them should be where you spend a free axis:

1. Warm cream background (~`#F4F1EA`), high-contrast serif display, terracotta accent.
2. Near-black background, one bright acid-green or vermilion accent.
3. Broadsheet layout: hairline rules, zero border-radius, dense newspaper columns.

WellForge has a **fourth** default, and it is ours: untouched Mantine plus Tailwind's
slate/indigo, `rounded-md`, `shadow-sm`, a stat row with a gradient number. It is the right
answer for an internal admin screen and a non-answer for a product surface. Recognise it when
you produce it.

Also question structural devices that only *look* like information: numbered eyebrows
(01 / 02 / 03) earn their place when the content genuinely is an ordered sequence and the
order matters to the reader — otherwise they are decoration with a monospace font. Same for
motion: one orchestrated moment beats scattered effects, and scattered effects are themselves
a tell.

Match execution to ambition — maximalist directions need elaborate follow-through, minimal
ones need precision in spacing and type. Then remove one accessory before you ship.

## Where it lands

The durable artifact is a section in `design.md`, between **Component inventory** and
**Accessibility** ([[spec-driven]] format):

```markdown
## Visual direction
<surface class + verdict from the gate, in one line>

| Token | Value | Job |
|---|---|---|
| `--color-ink` | `#…` | body text, rules |
| … | | |

Type: <display face + delivery> / <body face + delivery> / <utility>; scale <…>
Layout: <one sentence>
Signature: <the one element>
Risk: <the deliberate choice you would have to defend, and the argument for it>
```

Then, at implementation time:

- **frontend-dev implements this as theme configuration** — Mantine `createTheme` /
  CSS custom properties / the Tailwind theme extension — *never* as hex literals inside
  components. A token used by exactly one component is a smell: promote it or delete it.
- Mockups, and the directions you tried and rejected, go under `.forge/design/<feature>/`
  alongside the [[visual-companion]] evidence. That directory is **gitignored** in the
  templates — it is scratch, not the record. If a rejected direction matters, it belongs in
  the `Risk:` line, not only in the scratch dir.

## Quality floor — checkable, not aspirational

- **Contrast: compute it, don't eyeball it.** Every text/background pair the palette allows
  must clear 4.5:1 (3:1 for ≥24px text and for UI boundaries). A palette that hasn't been
  checked isn't finished. This is the visual half of design.md's **Accessibility** section —
  it does not replace it.
- **Focus is visible.** Replacing the default focus ring is fine; replacing it with something
  *less* visible is a defect. A custom ring must survive both the light and dark palette.
- **Reduced motion is honoured by media query**, not by restraint. `prefers-reduced-motion:
  reduce` kills or shortens every non-essential transition.
- **Responsive to 360px.** The signature element degrades gracefully or is dropped at small
  widths — it never causes horizontal scroll.

## CSS pitfalls in this stack

- Watch selector specificity between section-level classes and element-level ones — the
  classic symptom is section padding that silently cancels out.
- In Mantine + Tailwind the recurring bug is a Tailwind utility losing to Mantine's own
  styles. Fix it through the theme, `styles`/`classNames` props, or `Box` — not with a wall
  of `!important`.

## What this skill does NOT license

- No new UI library, no new CSS-in-JS runtime, no font that the project's CSP or build cannot
  actually deliver ([[react-ts-vite]] conventions still hold).
- No rewriting existing screens because the new direction is nicer — that is a separate
  feature with its own spec (the drift rule).
- The designer still writes no code: this produces the `## Visual direction` section, and
  frontend-dev implements it.
