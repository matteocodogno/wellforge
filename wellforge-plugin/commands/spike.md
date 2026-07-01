---
description: Spike a goal fast — main-loop build from a one-paragraph brief, advisory gates, no agents, no approval (rigor tier: spike)
argument-hint: <goal — what to prototype / which feasibility question to answer>
---

Build a **spike**: the fastest WellForge path, for feasibility / PoC / business-model
experiments that may be thrown away. Load the **rigor-tiers** skill now — this command IS
the `spike` tier. Resolved tier: **spike** (invocation).

Goal: $ARGUMENTS

## What spike means here

- **Main loop only — you implement directly. Spawn NO subagents.** The whole point is to
  skip orchestration cold-starts. (mvp/production are where the agent team runs.)
- **Effort: minimal** (the spike tier cue, rigor-tiers skill) — apply it to yourself: take
  the shortest path that answers the question, no gold-plating or exhaustive edge-case work,
  leave `// SPIKE:` where you cut a corner. Bias hard to speed.
- **No human approval gate.** You build, then the human reviews the result.
- **Advisory gates** (lint/typecheck/build): run them, report failures, do NOT stop on them.
- **The security floor still blocks** (see rigor-tiers): secret scan, no hardcoded creds,
  critical-CVE dependency audit. Fast never means "leaks credentials."

## Procedure

1. **Resolve the folder.** Next sequential `specs/NNN-slug/` (slug from the goal). Reuse an
   existing folder only if the goal clearly continues it.

2. **Write `specs/NNN-slug/brief.md`** — short, not a spec. Frontmatter then ~5–10 lines:
   ```markdown
   ---
   id: NNN
   slug: <kebab>
   rigor: spike
   status: in-progress
   created: <today>
   ---

   # <goal>

   ## Question            <!-- the feasibility / business question this spike answers -->
   ## Build               <!-- 3–6 bullets: what you'll actually make to answer it -->
   ## Out of scope        <!-- what you're deliberately NOT doing (this is a spike) -->
   ## Findings            <!-- filled in AFTER: did it work? what did you learn? -->
   ```
   No user stories, no ACs, no plan. If the goal is genuinely unclear, ask ONE batched
   AskUserQuestion round — but prefer a sensible assumption recorded under `## Out of scope`.

3. **Build it.** Load the relevant stack skill (`react-ts-vite`, `kotlin-springboot`,
   `hono-ts-backend`, `mise`, …) and write the code directly. Favor the shortest path that
   answers the question; leave honest `// SPIKE:` markers where you cut a corner that
   `/wellforge:promote` would later pay off. Keep changes scoped to the goal.

4. **Sanity check (advisory).** Run the project's lint / typecheck / build (mise tasks if
   present). Report what passed/failed. Do NOT block or loop on failures — note them under
   `## Findings`. THEN run the **security floor** (secret scan + critical-CVE audit): if it
   trips, STOP and fix — the floor is the one thing a spike cannot skip.

5. **Fill `## Findings`** in brief.md: did the spike answer its question? What was learned?
   Set `status: done`.

6. **Record the run (lightweight).** Per the **observability** skill, write
   `.forge/runs/<run_id>.json` (schema `wellforge-run/v1`) with `command: spike`,
   `rigor: spike`, no agents (`agents: []`), the advisory gate outcomes, and `result`. Leave
   `tokens`/`cost` null.

## Report

End with:
- What you built and where (files), and the spike's verdict on its question.
- Advisory gate results (actual numbers) + security-floor result.
- The reminder: **"rigor: spike — gates were advisory, this is not production-ready. Run
  `/wellforge:promote NNN-slug --to mvp` (or `production`) to graduate it."**

## Hard rules

- Never spawn a subagent — if you reach for one, you're in the wrong command (use
  `/wellforge:orchestrate --mode mvp`).
- Never present spike output as production-ready, and never silently raise its rigor —
  graduation is `/wellforge:promote` only.
- The security floor is non-negotiable; everything else is advisory.
