---
description: Implement tasks of a feature from its approved tasks.md (dependency-aware, parallel, QE-verified)
argument-hint: [feature] [tasks] [--mode mvp|production] — e.g. "001-user-auth", "user-auth T3,T5", "T2-T4", "next", "all"
---

Implement tasks from a feature's `tasks.md`, following the **spec-driven** skill
conventions (load it now). This is the implementation slice of the orchestrator, callable
directly — for when spec/plan/tasks already exist and you just want code written.

Arguments: $ARGUMENTS

## Step 0 — Resolve the rigor tier

Load the **rigor-tiers** skill. Resolve the tier (precedence: `--mode` flag > the feature's
`rigor:` frontmatter > project default [`.forge/manifest.json` `rigor` if scaffolded, else
`.forge/adoption.json` `rigor` if adopted] > `production`) and strip the flag from the args.
State it. `spike` is not an implement tier (spikes have no `tasks.md`) — if asked
for `--mode spike`, treat it as `mvp`. The tier changes only **Step 4 (verify)** and the
closing suggestion; dispatch is identical.

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

Two agents editing the same working tree at once can clobber each other. When a batch has
**≥2 dependency-independent agents**, isolate each so "one agent's edits literally cannot
touch the other's checkout":

1. **Isolate.** Spawn each agent with git-worktree isolation (Task/Agent tool
   `isolation: "worktree"`) — a fresh worktree + branch off the current HEAD, so it already
   contains the spec, `tasks.md`, and every task integrated earlier in this run. (Set
   `worktree.baseRef: "head"` in settings so worktrees branch from HEAD, not the remote
   default — see the plugin `settings-snippet.jsonc`.)
2. **Constrain the agent.** In each parallel agent's prompt add: *commit your code with the
   standard message but **do NOT edit `tasks.md`*** (its checkbox is reconciled centrally, so
   parallel branches never conflict on adjacent checkbox lines), and *end your report with a
   line `WORKTREE-BRANCH: <git branch --show-current>` and `COMMITS: <n>`*. The dispatch
   result usually also surfaces the agent's worktree branch in its metadata; the self-reported
   line is the portable fallback — use whichever you get.
3. **Integrate.** After the batch returns, merge each branch into the feature branch one at a
   time, in a deterministic order, with **git's default merge message**
   (`git merge --no-ff --no-edit <branch>`). Do NOT pass a custom lowercase `-m "merge …"`:
   a Conventional-Commits `commit-msg` hook (this repo, and generated projects with commitlint)
   rejects it — the default `Merge branch …` and a conventional `chore(...)` message are exempt.
   - **Clean merge** → good. Continue.
   - **Conflict = a collision**, not a routine merge: two tasks the DAG called independent
     touched the same file, so they were never independent. Abort the merge
     (`git merge --abort`), **surface it like drift** — name the two tasks and the colliding
     files — and resolve by adding the missing `deps:` edge (`/wellforge:tasks` re-sync) and
     re-running the later task in the now-integrated tree. Never auto-resolve code conflicts
     silently.
4. **Reconcile the checkboxes centrally.** Once every track is integrated, check the boxes
   for all completed tasks in `tasks.md` in **one** commit on the feature branch.
5. **Prune.** Remove the merged worktrees and their branches (`git worktree remove`,
   `git branch -d`).

**Fallback.** If worktree isolation is unavailable (older Claude Code, or the option is
rejected), fall back to the main-tree path — dispatch the batch **sequentially** (not in
parallel), each agent committing + checking its own box, to avoid collisions. State which
mode you used.

## Step 4 — Verify

- Spawn `wellforge:quality-engineer` scoped to the tasks just implemented: it runs the gates and
  checks the ACs those tasks serve, and returns a verdict table.
- **`production`** — every gate blocks. FAIL → **triage each defect to its true owner** before
  looping (don't route everything to a dev): a code defect → the owning dev agent (failing
  test path included); a wrong/missing/untestable AC → `wellforge:product-owner`; a wrong
  contract/architecture → `wellforge:architect`; a missing designed state/a11y →
  `wellforge:designer` (each a drift amendment + `/wellforge:tasks` re-sync). Re-run QE. **Max
  2 fix rounds**, then stop and escalate.
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
and `result` (completed / escalated / partial). Record the isolation mode used and any
collision events (per the observability skill's `worktree` / `collision_events` fields).
One file per run; leave `tokens`/`cost` null (the SubagentStop hook + `run-report.py` fill
cost). This is the audit trail.

## Hard rules

- Implement ONLY the selected tasks. Discovering adjacent work is a new task (add it via
  `/wellforge:tasks` re-sync), not scope to absorb here.
- Never modify spec.md/plan.md or task definitions — only checkboxes. Drift is reported.
- Bounded loops only: QE fix loop max 2 rounds, then escalate. No silent retrying.
- For a brand-new feature with no spec yet, this is the wrong command — use
  `/wellforge:spec` (or `/wellforge:orchestrate` for the whole pipeline).
