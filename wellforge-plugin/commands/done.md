---
description: Mark a feature done — verifies the tier-aware done gate (tasks + QE + eval), then sets status: done
argument-hint: [feature] — NNN-slug / slug / NNN; omit to infer the in-progress feature ready to close
---

Close a feature: verify it has genuinely met its **done gate**, then set `status: done`.
Read-only until the gate passes — this is the human-in-the-loop transition, and **agents
never set status** (the evaluator judges; the calling session records the close). Conventions:
the **spec-driven** and **rigor-tiers** skills (load them).

Feature: $ARGUMENTS

## Step 1 — Resolve the feature + tier

Resolve the feature from the argument (number / slug / full name), or infer the one ready to
close — an `in-progress` spec with all tasks checked; if ambiguous, list and ask. State which
feature you resolved. Read its `spec.md`/`brief.md`, `tasks.md`, and `eval-report.md`. Resolve
the **rigor tier** (feature `rigor:` frontmatter > project default in `.forge/manifest.json` /
`.forge/adoption.json` > `production`).

## Step 2 — The done gate (tier-aware) — REFUSE if any condition is unmet

Check the conditions for the resolved tier. On any miss: STOP, name the exact missing
condition and the command that fixes it, and do NOT set done.

- **`production`**
  1. every task in `tasks.md` checked (no `- [ ]` remaining)
  2. QE passed (latest verdict PASS — if stale/absent, run `/wellforge:implement` / QE)
  3. `eval-report.md` exists, `verdict: PASS`, and is **not stale** (newer than the last code
     change to the feature) — otherwise point at `/wellforge:eval`
- **`mvp`**
  1. every task checked
  2. QE-light passed (SAST-high / lint / typecheck / security-floor green; coverage is advisory)
  — no eval; mvp's bar is QE, not the LM-judge
- **`spike`** — a spike closes through its `brief.md`, not tasks/QE/eval: its `## Findings`
  are filled and the question answered. Set the brief `status: done`; if it proved out and
  should become real, suggest `/wellforge:promote` instead of just closing.

## Step 3 — Close

Only when the gate passes: set the spec (or brief) frontmatter `status: done` and add
`done: <today>`. Change nothing else — this command only flips the status.

## Step 4 — Report

State: feature, tier, the gate conditions that passed **with evidence** (task count, QE
verdict, eval score/date), and that status is now `done`. If a spike proved out, suggest
`/wellforge:promote`.

## Hard rules

- **Refuse** to close a feature whose gate isn't met — name the missing condition; never set
  done on faith. This is the single guarded place the `done` transition lives.
- Never lower a bar to pass the gate — don't ignore a FAIL eval, a failing QE, or an unchecked
  task. An unmet condition is work to do, not a status to force.
- `done` is the calling session's call to record, never an agent's. You verify and flip it
  here; agents only ever produced the artifacts you're checking.
