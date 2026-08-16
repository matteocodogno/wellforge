---
description: Implement tasks of a feature from its approved tasks.md (dependency-aware, parallel, QE-verified)
argument-hint: [feature] [tasks] [--mode mvp|production] [--terse|--no-terse] — e.g. "001-user-auth", "user-auth T3,T5", "T2-T4", "next", "all"
---

Implement tasks from a feature's `tasks.md`, following the **spec-driven** skill
conventions (load it now). This is the implementation slice of the orchestrator, callable
directly — for when spec/plan/tasks already exist and you just want code written.

Arguments: $ARGUMENTS

## Step 0 — Resolve the rigor tier and terse mode

Load the **rigor-tiers** skill. Resolve the tier (precedence: `--mode` flag > the feature's
`rigor:` frontmatter > project default [`.forge/manifest.json` `rigor` if scaffolded, else
`.forge/adoption.json` `rigor` if adopted] > `production`) and strip the flag from the args.
State it. `spike` is not an implement tier (spikes have no `tasks.md`) — if asked
for `--mode spike`, treat it as `mvp`. The tier changes only **Step 4 (verify)** and the
closing suggestion; dispatch is identical.

Separately, load the **terse** skill and resolve terse mode — an **orthogonal axis from
`--mode`**, not tied to any tier: read a `--terse` / `--no-terse` token from the args, default
**OFF** (terse is off by default in both `mvp` and `production` for this command; only
`/wellforge:spike` defaults it on, and spike has no `tasks.md` to implement). Strip the
matched token from the args before resolving `[feature] [tasks]` from what remains. **State
the resolved terse boolean.**

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
   Otherwise STOP and point at `/wellforge:tasks` (or `/wellforge:plan`) for this feature.
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
- For each task, pick the agent by domain: `wellforge:frontend-dev`, `wellforge:backend-dev`, or `wellforge:devops`
  (infra/CI tasks). Each agent receives ONLY the spec dir path and its task ID(s) —
  it reads the ACs, contracts, and `done when:` itself — plus the resolved tier's **effort
  cue** (rigor-tiers skill: moderate for `mvp`, full for `production`), prepended to its task.
  **When terse is resolved on** (Step 0), also prepend the terse cue (**terse** skill,
  verbatim) to every dispatched agent's task, right beside the effort cue; when terse is
  resolved off (the default), do not prepend it.
- Order and dispatch by the DAG: run dependency-independent tasks **in one batch**;
  sequence only along `deps:` edges. A batch of **one** agent, or a fully sequential chain,
  runs in the **main working tree** — the agent checks its task's box in `tasks.md` on
  completion and commits `feat(<scope>): <title> (T<n>, specs/NNN)`, exactly as before.
- A batch of **two or more** agents runs with **worktree isolation** (below) so their edits
  cannot collide.
- Relay each agent's result compactly (files touched, test/lint output — actual numbers).
- **Drift / blocker** from any agent pauses that track: surface the proposed amendment,
  route it to the owning agent (PO for spec, architect for plan), re-sync via
  `/wellforge:tasks`, then resume. Never let an agent silently work around a wrong spec.

### Parallel isolation (worktrees)

Two agents editing the same working tree at once can clobber each other — and a worktree
isolates only the *checkout*, not the database, ports, containers, credentials or migration
counter the project also reaches. The **worktree-isolation** skill owns this: load it and
follow it verbatim. In order, for any batch of ≥2:

1. **Preflight** the shared-state enumeration against this project and state each class's
   disposition (isolate / forbid / accept). **Unclassified is not a pass** — it means this
   batch runs sequentially instead.
2. **Carry in** the gitignored env files each worktree would otherwise lack, and **verify**
   the env resolves there. A variable that resolves in the main tree and not in the worktree
   is a hard stop, not a warning.
3. **Isolate** (`isolation: "worktree"`), **constrain** each agent (commit on its own branch,
   never edit `tasks.md`, report `WORKTREE-BRANCH` / `COMMITS`, treat anything outside the
   stated allowances as an environment fault to report rather than work around),
   **integrate** by rebase + `--ff-only` (never a merge commit — the repo forbids them),
   **reconcile** every checkbox centrally in one commit, then **prune** the worktrees *and*
   whatever the preflight isolated.
4. **A rebase conflict is a collision** — two tasks the DAG called independent touched the
   same file, so the edge was wrong: surfaced like drift, resolved by a `/wellforge:tasks`
   re-sync, never auto-resolved.

**Environment faults beat code diagnoses.** If an agent in a worktree reports failures it
attributes to "pre-existing breakage", check the fault table in the worktree-isolation skill
before believing it — tests that fail in a worktree and pass on the integrated branch are an
isolation defect, and code must not be "fixed" on that evidence.

**Fallback.** If worktree isolation is unavailable (older Claude Code, or the option is
rejected), or the preflight left a class unclassified, fall back to the main-tree path —
dispatch the batch **sequentially** (not in parallel), each agent committing + checking its
own box. State which mode you used and, if the preflight forced it, which class.

## Step 4 — Verify

- Spawn `wellforge:quality-engineer` scoped to the tasks just implemented: it runs the gates and
  checks the ACs those tasks serve, and returns a verdict table.
- **`production`** — every gate blocks. FAIL → **triage each defect to its true owner** before
  looping (don't route everything to a dev): an **environment fault** → nobody, it is not a
  defect (worktree-isolation skill — fix the isolation or the carry-in and re-run; never spend
  a fix round on it); a code defect → the owning dev agent (failing
  test path included); a wrong/missing/untestable AC → `wellforge:product-owner`; a wrong
  contract/architecture → `wellforge:architect`; a missing designed state/a11y →
  `wellforge:designer` (each a drift amendment + `/wellforge:tasks` re-sync). Re-run QE. **Max
  2 fix rounds**, then stop and escalate. Dev agents debug per the `systematic-debugging`
  skill; its **3-attempts-on-one-symptom** stop composes with this 2-round cap — whichever
  trips first, stop. An agent reporting three failed attempts is an architecture signal:
  route it to the architect, don't spend the second round re-dispatching the same fix.
- **`mvp`** — QE runs in **advisory** mode (rigor-tiers): only SAST-high, lint, typecheck, and
  the security floor block; coverage is reported as gap-to-80%, not enforced. Same 2-round loop
  for blocking defects only.
- The **security floor** (secret scan, no hardcoded creds, critical-CVE audit) blocks in BOTH
  tiers — never waived.
- If QE recommends a security pass, spawn `wellforge:owasp-reviewer`; treat findings ≥ medium as
  defects (same loop).

## Step 5 — Report

- Tasks done (with IDs), tasks skipped (already checked) and deferred (unmet deps not in
  scope), QE verdict, commits. State what remains unchecked in `tasks.md`.
- If every task is now checked and QE passed, suggest the next step **by tier** (never set
  `done` from here — that's `/wellforge:done`'s guarded job):
  - `production` → run **`/wellforge:eval <feature>`** (the LM-judge is the gate, not the QE
    pass alone); on PASS, **`/wellforge:done <feature>`** closes it.
  - `mvp` → no eval; the bar is QE-light. **`/wellforge:done <feature>`** closes it — or
    `/wellforge:promote <feature> --to production` to graduate first.

## Step 6 — Record the run (observability)

Write a run trace per the **observability** skill (load it): capture `started` at the
start of this run and, now, write `.forge/runs/<run_id>.json` (schema `wellforge-run/v1`)
with every dispatched agent + outcome, any drift events (resolved or not), the QE verdict,
and `result` (completed / escalated / partial). Record the isolation mode used, any
collision events, and any environment faults (per the observability skill's `worktree` /
`collision_events` / `env_faults` fields) — including, when a batch fell back to sequential,
the preflight class that forced it.
Set `terse` to the boolean resolved in Step 0 (`true` iff `--terse` resolved on for this
run, `false` otherwise); leave `control_run_id` `null` (pairing to a control run is a later
concern, not this command's). One file per run; leave `tokens`/`cost` null (the
SubagentStop hook + `run-report.py` fill cost). This is the audit trail.

## Hard rules

- Implement ONLY the selected tasks. Discovering adjacent work is a new task (add it via
  `/wellforge:tasks` re-sync), not scope to absorb here.
- Never modify spec.md/plan.md or task definitions — only checkboxes. Drift is reported.
- Bounded loops only: QE fix loop max 2 rounds, then escalate. No silent retrying.
- For a brand-new feature with no spec yet, this is the wrong command — use
  `/wellforge:spec` (or `/wellforge:orchestrate` for the whole pipeline).
