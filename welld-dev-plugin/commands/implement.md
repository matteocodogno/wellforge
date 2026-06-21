---
description: Implement tasks of a feature from its approved tasks.md (dependency-aware, parallel, QE-verified)
argument-hint: [feature] [tasks] — e.g. "001-user-auth", "user-auth T3,T5", "T2-T4", "next", "all"
---

Implement tasks from a feature's `tasks.md`, following the **spec-driven** skill
conventions (load it now). This is the implementation slice of the orchestrator, callable
directly — for when spec/plan/tasks already exist and you just want code written.

Arguments: $ARGUMENTS

## Step 1 — Resolve the feature, then the selection

The argument is `[feature] [tasks]` — both optional, feature first.

1. **Feature.** Each feature is a folder `specs/NNN-slug/`. Resolve it from the leading
   token if present — match by number (`001`), slug (`user-auth`), or full name
   (`001-user-auth`) against existing `specs/` dirs.
   - No feature token: infer it — the spec with `status: in-progress`; if none, the most
     recently `approved` spec that has a `tasks.md`. If still ambiguous (several
     in-progress), list them and ask which feature.
   - State which feature you resolved before doing anything. Read its spec.md, plan.md,
     and tasks.md fully.
2. **Gate check.** That feature's `tasks.md` must exist and its plan be `approved`.
   Otherwise STOP and point at `/welld-dev:tasks` (or `/welld-dev:plan`) for this feature.
3. **Selection** — the remaining tokens (everything after the feature) choose tasks
   WITHIN that feature:
   - explicit IDs / comma list / `Tn-Tm` range → those tasks
   - `next` → the first unchecked task whose `deps:` are all checked
   - `all` / omitted → every unchecked task
   - drop already-checked tasks (report them as skipped); if the selection matched
     nothing, stop and show the feature's task table.

## Step 2 — Order and dependency check

- **Refuse to start a task with unchecked deps** that are not themselves in this run.
  If the selection pulls in unmet deps, report them and offer to expand the set to
  include them (user confirms) rather than silently widening scope.
- Topologically order the selected set by `deps:`. Tasks with no edge between them are
  **parallelizable** — typically the FE and BE tracks.

## Step 3 — Dispatch

- Set spec `status: in-progress` if it isn't already.
- For each task, pick the agent by domain: `frontend-dev`, `backend-dev`, or `devops`
  (infra/CI tasks). Each agent receives ONLY the spec dir path and its task ID(s) —
  it reads the ACs, contracts, and `done when:` itself.
- Run dependency-independent tasks as **parallel agents in one batch**; sequence only
  along `deps:` edges.
- Each agent checks its task's box in `tasks.md` on completion and commits
  `feat(<scope>): <title> (T<n>, specs/NNN)`. Relay each agent's result compactly
  (files touched, test/lint output — actual numbers).
- **Drift / blocker** from any agent pauses that track: surface the proposed amendment,
  route it to the owning agent (PO for spec, architect for plan), re-sync via
  `/welld-dev:tasks`, then resume. Never let an agent silently work around a wrong spec.

## Step 4 — Verify

- Spawn `quality-engineer` scoped to the tasks just implemented: it runs the gates and
  checks the ACs those tasks serve, and returns a verdict table.
- FAIL → route each defect back to the owning dev agent (failing test path included),
  re-run QE. **Max 2 fix rounds**, then stop and escalate with the verdict table.
- If QE recommends a security pass, spawn `owasp-reviewer`; treat findings ≥ medium as
  defects (same loop).

## Step 5 — Report

- Tasks done (with IDs), tasks skipped (already checked) and deferred (unmet deps not in
  scope), QE verdict, commits. State what remains unchecked in `tasks.md`.
- If every task is now checked and QE passed, offer to set spec `status: done`.

## Hard rules

- Implement ONLY the selected tasks. Discovering adjacent work is a new task (add it via
  `/welld-dev:tasks` re-sync), not scope to absorb here.
- Never modify spec.md/plan.md or task definitions — only checkboxes. Drift is reported.
- Bounded loops only: QE fix loop max 2 rounds, then escalate. No silent retrying.
- For a brand-new feature with no spec yet, this is the wrong command — use
  `/welld-dev:spec` (or `/welld-dev:orchestrate` for the whole pipeline).
