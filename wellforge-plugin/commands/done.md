---
description: Close a feature — verifies the tier-aware done gate (tasks + QE + eval) then sets status: done, or retires it as superseded
argument-hint: [feature] [--superseded-by <NNN-slug>] — NNN-slug / slug / NNN; omit to infer the in-progress feature ready to close
---

Close a feature: verify it has genuinely met its **done gate**, then set `status: done`.
Read-only until the gate passes — this is the human-in-the-loop transition, and **agents
never set status** (the evaluator judges; the calling session records the close). Conventions:
the **spec-driven** and **rigor-tiers** skills (load them).

Feature: $ARGUMENTS

## Step 0 — Who is calling

This procedure is **the only implementation of the `done` transition**, and it is invoked two
ways — both run everything below, unchanged:

- **Directly** by the user (`/wellforge:done [feature]`).
- **As a procedure**, by a command that just finished the work and would otherwise flip the
  status itself: `/wellforge:spike` step 5, `/wellforge:promote`'s final step, and
  `/wellforge:orchestrate`'s close step (both its `mvp` and `production` pipelines). They say
  "run the `/wellforge:done` procedure"; you run it here, in the main loop, with the feature
  already resolved by the caller.

A caller that just ran the gate's inputs still re-verifies them here. That is the point: the
gate is checked against the **artifacts on disk**, never against a caller's recollection of
having passed it. Four copies of this transition is how one of them ends up not checking that
the tasks are all ticked.

## Step 0b — `--superseded-by <NNN-slug>`: the other terminal status

`superseded` is the spec lifecycle's second exit (spec-driven skill): work that stopped
because another spec replaced it, not because it finished. It is NOT `done` — nothing was
delivered — and leaving such a spec `in-progress` forever is what makes
`/wellforge:triage` report rot that no one can clear.

When the flag is present, skip the done gate entirely (there is nothing to verify — the
work was abandoned, not completed) and instead:

1. Resolve BOTH features. The successor must exist and must not be the same feature; if it
   doesn't resolve, STOP — a `superseded_by` pointing nowhere is worse than no pointer.
2. Refuse if the feature is already `done`: a delivered feature is not superseded, it is
   replaced by later work, and rewriting its history hides that it shipped.
3. Set on the superseded spec: `status: superseded`, `superseded_by: <NNN-slug>`,
   `superseded: <today>`. Change nothing else — no tasks, no successor edits.
4. Report both features and say plainly that no work was verified, because none was claimed.

Everything below (the gate, the tiers) applies only WITHOUT this flag.

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
- **`spike`** — a spike closes through its `brief.md`, not tasks/QE/eval: the condition is
  that `## Findings` is filled and the spike's question answered. (Step 3 does the write, on
  the brief rather than a spec.) If it proved out and should become real, suggest
  `/wellforge:promote` alongside the close.

## Step 3 — Close

Only when the gate passes: set the spec (or brief) frontmatter `status: done` and add
`done: <today>` — **both, at every tier**, whoever called. Change nothing else: this
procedure only flips the status. A caller that also owns another field (e.g.
`/wellforge:promote` setting `rigor: production`) writes that itself, before calling you.

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
- **A promoted feature is gated at its NEW tier.** `mvp → production` does not inherit the
  mvp close: the production branch runs in full, so an eval PASS and a fresh QE are required
  even though the feature was already `done` as an mvp.
- No other command may write `status: done` **or `status: superseded`**. If you find one
  that does, that is the bug — this is the single guarded place those transitions live, and
  it is only true while that stays literally true.
- `superseded` is never a way around a failing gate. If the work was finished but can't pass,
  that is a defect to fix, not a spec to retire; the flag is for work another spec replaced.
