---
name: visual-companion
description: >
  WellForge Visual Companion — a browser-based tool the designer agent uses during
  /wellforge:design to show mockups, wireframes, diagrams, and side-by-side layout
  comparisons instead of describing them in text, capturing the user's clicks. Use ONLY
  when the designer was invoked interactively with the visual companion enabled (the
  `--visual` flag on /wellforge:design); NEVER in a headless/orchestrated run and NEVER in
  the spike tier. Covers the just-in-time offer, the per-question show-vs-tell test, theme
  selection from the project's real component library, the write-screen/read-events loop,
  .forge/design/ persistence, and the CSS classes the frame provides. The design.md artifact
  is still the deliverable — the browser only helps resolve visual questions faster.
---

# Visual Companion — mockups in the browser during design

A browser-based companion that lets the **designer agent** show mockups, wireframes,
diagrams, and side-by-side comparisons in a live tab while designing a UI feature, and read
back what the user clicks. It's a **tool, not a mode**: enabling it makes the browser
*available*; the designer still decides, per question, whether to use it.

**The artifact is unchanged.** `design.md` (flows → screens & states → component inventory →
a11y, per the [[spec-driven]] skill) is still the deliverable. The companion only makes the
visual questions that feed it clearer and faster to resolve. Everything shown persists as
**design evidence** under `.forge/design/<feature>/` and is referenced from `design.md`.

## When it is allowed to run — three hard gates

The companion is token-intensive and needs a human at a browser. It runs **only** when all
three hold; otherwise design proceeds text-only exactly as before.

1. **Enabled by flag.** The caller (`/wellforge:design --visual`) explicitly enabled it. If
   the invocation did not say the visual companion is enabled, do **not** start the server.
2. **Interactive session.** There is a user present to look at the browser. In a headless or
   **orchestrated** run (`/wellforge:orchestrate` spawns the designer directly), the
   companion is impossible — never start it. No browser, no offer.
3. **Not the spike tier.** Per [[rigor-tiers]], `spike` skips the designer entirely; the
   companion is for `mvp` (opt-in) and `production`. Never offer it for a spike.

## Offering it — just-in-time, its own message

Do **NOT** offer the companion up front. Design the flows and ask conceptual questions in the
terminal as usual. The **first time** a question would genuinely be clearer *shown than told*
— a real mockup / layout / diagram question, not merely a UI *topic* — offer it then, as a
message containing **only** the offer:

> "This next part might be easier if I show you — I can put together mockups and layout
> comparisons in a browser tab as we go, styled to your app's components. It's token-intensive.
> Want me to? I'll open it for you."

Wait for the answer. On **accept**, start the server with `--open`. On **decline**, continue
text-only and don't offer again unless the user raises it. If no visual question ever arises,
never offer it.

## The per-question test (even after acceptance)

Accepting ≠ every question goes through the browser. For **each** question ask: *would the
user understand this better by seeing it than reading it?*

- **Browser** — content that IS visual: screen mockups, wireframes, layout/navigation
  structure, **side-by-side comparisons** (two layouts, two directions), reuse-vs-NEW
  component decisions shown as real components, architecture/flow diagrams, spacing & hierarchy.
- **Terminal** — content that is text: flow logic, scope/requirements, "what does X mean?",
  A/B/C conceptual choices, tradeoff lists, a11y keyboard paths, API-shaped decisions.

A question *about* a UI topic is not automatically a visual question. "What kind of empty
state do we need?" is conceptual → terminal. "Which of these two empty-state layouts?" is
visual → browser.

## Theme — make mockups look like the real app

The designer already discovers the project's component library (from `AGENTS.md`/`CLAUDE.md`,
`package.json`, and `frontend/src/` imports). Pass the matching `--theme` so mockups adopt
that design system instead of a neutral wireframe:

| Project library | `--theme` |
|---|---|
| Mantine (WellForge `react-ts-vite` greenfield default) | `mantine` |
| Material UI (MUI) | `mui` |
| shadcn/ui | `shadcn` |
| Unknown / structure-only questions | `wireframe` |
| No/unclear library | omit (`default`) |

Use `wireframe` deliberately when the question is about **structure**, not look — the muted,
sketch styling signals "not the final design" and keeps the discussion on layout.

## Starting a session

Start the server **only after** the user accepts. Run it from the skill's `scripts/` dir:

```bash
scripts/start-server.sh \
  --project-dir "$(pwd)" \
  --session-name <NNN-slug> \      # feature slug → .forge/design/<NNN-slug>/, persists across restarts
  --theme <mantine|mui|shadcn|wireframe> \
  --open                           # auto-opens the user's browser on the first screen

# Returns JSON: {"type":"server-started","url":"http://localhost:PORT/?key=…",
#                "screen_dir":".../.forge/design/<NNN-slug>/content",
#                "state_dir":".../.forge/design/<NNN-slug>/state", ...}
```

Save `url`, `screen_dir`, and `state_dir`. Always give the user the **complete** `url`
including `?key=…` — the server 403s any request without the session key (it gates HTTP and
the WebSocket so a stray tab or another machine can't read screens or inject clicks). With
`--open` the browser opens itself; still share the URL as a fallback for headless/remote
setups. If you backgrounded the server and lost stdout, read `state_dir/server-info`.

**Platform note:** in most Claude Code setups the script backgrounds the server itself. If
your environment reaps detached processes (Windows/Git Bash auto-detected; others), pass
`--foreground` and launch the Bash tool call with `run_in_background: true`, then read
`state_dir/server-info` next turn.

## The loop

1. **Confirm the server is alive**, then **write an HTML file** to `screen_dir`:
   - Alive = `state_dir/server-info` exists and `state_dir/server-stopped` does not. If it
     shut down, restart with the **same `--project-dir` and `--session-name`** — it reuses the
     port and the user's open tab reconnects on its own (it shows a "paused" overlay while
     down). Auto-exits after 4h idle (`--idle-timeout-minutes`).
   - **Write content fragments by default** (just the inner HTML) — the server wraps them in
     the themed frame. Only write a full document (starting `<!DOCTYPE`/`<html>`) for total control.
   - Semantic filenames (`checkout-layout.html`), **never reused**; iterate with a suffix
     (`checkout-layout-v2.html`). Use the Write tool — never `cat`/heredoc (dumps noise).
2. **Tell the user and end your turn:** remind them of the URL, one line on what's on screen
   ("Showing 2 checkout layouts — click the one you prefer"), and ask them to respond in the
   terminal.
3. **Next turn:** read `state_dir/events` (JSON-lines of their clicks, cleared when you push a
   new screen) and merge with their terminal reply. Terminal text is primary; events add
   structured signal. No events file = they didn't click; use their text.
4. **Iterate or advance** — refine the current screen (new `-v2` file) until it's settled,
   then move on. When the next question is a terminal one, push a `waiting.html` so the user
   isn't staring at a resolved choice:
   ```html
   <div style="display:flex;align-items:center;justify-content:center;min-height:60vh">
     <p class="subtitle">Continuing in terminal...</p>
   </div>
   ```

## Recording evidence into design.md

Mockups are traceable design evidence, not throwaway:

- They persist in `.forge/design/<NNN-slug>/content/` (survives restarts via `--session-name`).
- For each settled screen, add a reference under its **Screens & states** entry in `design.md`:
  `> mockup: .forge/design/<NNN-slug>/content/checkout-layout-v2.html`
- This gives the quality-engineer and [[observability]] evaluator a concrete visual reference
  for "does the built UI match the approved design?" — cite it as trajectory evidence.
- Ensure `.forge/design/` is git-ignored (WellForge templates ignore it; add it if missing —
  keep `.forge/manifest.json` tracked).

## Cleaning up

```bash
scripts/stop-server.sh <state_dir-without-/state>   # i.e. the session dir
```

Stop the server when design is done. `.forge/design/` (non-`/tmp`) sessions are kept so
mockups stay reviewable; only `/tmp` sessions are deleted on stop.

## CSS classes the frame provides

Write fragments using these — the themed frame supplies all CSS and the click infrastructure.

**Options (A/B/C, clickable):**
```html
<h2>Which layout works better?</h2>
<p class="subtitle">Consider readability and hierarchy</p>
<div class="options"><!-- add data-multiselect to the container for multi-select -->
  <div class="option" data-choice="a" onclick="toggleSelect(this)">
    <div class="letter">A</div>
    <div class="content"><h3>Single column</h3><p>Focused reading</p></div>
  </div>
  <div class="option" data-choice="b" onclick="toggleSelect(this)">
    <div class="letter">B</div>
    <div class="content"><h3>Two column</h3><p>Sidebar + main</p></div>
  </div>
</div>
```

- **Cards** (`.cards` > `.card[data-choice]` > `.card-image` / `.card-body`) — visual designs.
- **Mockup** (`.mockup` > `.mockup-header` + `.mockup-body`) — a framed preview.
- **Split** (`.split` with two `.mockup`s) — side-by-side comparison.
- **Pros/Cons** (`.pros-cons` > `.pros` / `.cons` with `<ul>`).
- **Wireframe primitives** — `.mock-nav`, `.mock-sidebar`, `.mock-content`, `.mock-button`,
  `.mock-input`, `.placeholder`.
- **Typography** — `h2` (title), `h3` (section), `.subtitle`, `.section`, `.label`.

Guidance: 2–4 options per screen; explain the question on the page ("Which feels more
professional?"); scale fidelity to the question (wireframe for layout, polish for polish);
use real content where it matters. Clicks on `[data-choice]` elements post to `state_dir/events`.

## Attribution

The server (`scripts/server.cjs`, `start-server.sh`, `stop-server.sh`, `helper.js`,
`frame-template.html`) is adapted under the MIT License from the **superpowers** project's
`brainstorming` skill by Jesse Vincent (https://github.com/obra/superpowers). WellForge
changes: rebranding, `.forge/design/` layout, per-feature `--session-name`, design-system
`--theme` overlays, and integration with the designer agent + spec-driven workflow.
