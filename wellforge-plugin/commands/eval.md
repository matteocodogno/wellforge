---
description: Score a feature's implementation against the eval rubric (LM-judge — the non-deterministic verification half)
argument-hint: [feature] — NNN-slug / slug / NNN; omit to infer the in-progress/most-recent feature
---

Run the LM-judge evaluation for a feature: score the implementation against the central
rubric and produce a verdict. This is the eval half of verification — tests and CI gates
cover the deterministic part (`/wellforge:implement`'s QE step); this covers spec
fidelity, test quality, code conventions, and trajectory. Conventions: the **spec-driven**
skill (load it).

Feature: $ARGUMENTS

## Step 1 — Resolve the feature

Same resolution as `/wellforge:implement`: leading token matched against `specs/` by
number / slug / full name; if omitted, infer the `in-progress` spec, else the most recent
one whose tasks are all checked. Ambiguous → list and ask. State which feature you
resolved. Read spec.md, plan.md, tasks.md.

## Step 2 — Gate check

- `tasks.md` must exist and the implementation be substantially done (all or nearly all
  tasks checked). Evaluating an unbuilt feature is meaningless — if most tasks are open,
  STOP and point at `/wellforge:implement`.
- Ensure fresh test/coverage output exists; if not, run the project's test+coverage task
  so the evaluator has real evidence (not stale or assumed results).

## Step 3 — Evaluate

Spawn the `wellforge:evaluator` agent with: the spec dir path, the central rubric
(`gates/configs/eval-rubric.yml`), and any `specs/NNN-slug/eval.md` override. It scores
each rubric dimension 1–5 with cited evidence, computes the weighted total, and writes
`specs/NNN-slug/eval-report.md` with a PASS/FAIL verdict (PASS = total ≥ pass_score AND
every dimension ≥ floor).

## Step 4 — Act on the verdict

- **PASS** → report the score table; offer to set spec `status: done` (eval pass is the
  gate into `done`). 
- **FAIL** → relay the failing/weak dimensions with the evaluator's evidence. Route the
  remediation: name the specific ACs/tasks to revisit and suggest
  `/wellforge:implement <feature> <those tasks>`. Do NOT fix anything here — the evaluator
  judges, fixes go through the dev agents. After remediation, re-run `/wellforge:eval`.
- Bounded: the evaluator is a judge, not a loop. One scored verdict per run; you don't
  silently re-evaluate until it passes.

## Step 5 — Record the run (observability)

Write `.forge/runs/<run_id>.json` per the **observability** skill: the `wellforge:evaluator` agent,
its outcome + `score`, and `verdicts.eval`. Short trace, same audit trail as implement/
orchestrate.

## Hard rules

- Read-only on code/specs — this command only produces `eval-report.md` (via the
  evaluator) and, on the user's confirmation, the spec `done` status.
- Never lower a rubric floor or override a FAIL. The rubric is central
  (`gates/configs/eval-rubric.yml`); changing it is a PR to `gates/`.
- An unmet AC fails the eval regardless of the other dimensions (ac_satisfaction floor).
- For a feature with no implementation yet, this is the wrong command — implement first.
