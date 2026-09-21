---
description: Implement tasks of a feature from its approved tasks.md (dependency-aware, parallel, QE-verified)
argument-hint: [feature] [tasks] [--mode mvp|production] [--terse|--no-terse] — e.g. "001-user-auth", "user-auth T3,T5", "T2-T4", "next", "all"
---

Implement tasks from a feature's `tasks.md`, following the **spec-driven** skill
conventions (load it now). This is the implementation slice of the orchestrator, callable
directly — for when spec/plan/tasks already exist and you just want code written.

Arguments: $ARGUMENTS

## Step 0 — Resolve the rigor tier and terse mode

Load the **rigor-tiers** skill and run its *"Resolving the tier and terse at dispatch"*
section verbatim — precedence, strip the flags, state both. Load the **terse** skill for the
cue itself.

This command's only deviation (also in that table): **`--mode spike` is treated as `mvp`**,
because a spike has no `tasks.md` to implement. The tier changes only **Step 4 (verify)** and
the closing suggestion; dispatch is identical. Resolve `[feature] [tasks]` from the args that
remain after the flags are stripped.

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
2. **Gate check — tier-aware** (Step 0 already resolved the tier). `tasks.md` must exist;
   what must be approved upstream depends on the tier, because an `mvp` feature has **no
   plan.md by design** (rigor-tiers: "plan folded into tasks") and gating it on one would
   dead-end it:
   - **`production`** → `plan.md` must be `approved`.
   - **`mvp`** → `spec.md` must be `approved`; the contracts live in tasks.md's
     `## Architecture notes`. Read that section as the plan and pass it to the dev agents.
   Otherwise STOP and point at `/wellforge:tasks` (or, at `production`, `/wellforge:plan`).
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
- Build the **effective graph**, which is *not* just `deps:` — load the
  **worktree-isolation** skill and compute `deps:` ∪ **overlap of `touch:`**:
  - two tasks whose `touch:` lists share a path get an edge, even with no declared
    dependency — they were never safe to run concurrently;
  - **glob overlap counts** (two tasks touching `**/db/migrations/*` collide on the
    *counter*, not on a file);
  - **report the edges you added** ("T8 and T12 both touch `db/migrations/*` →
    serialized") before dispatching. A silently different graph isn't auditable.
- Topologically order the selected set by that effective graph. Tasks with no edge
  between them are **parallelizable** — typically the FE and BE tracks.

## Step 3 — Dispatch

- Set spec `status: in-progress` if it isn't already.
- For each task, pick the agent by domain: `wellforge:frontend-dev`, `wellforge:backend-dev`, or `wellforge:devops`
  (infra/CI tasks). Each agent receives ONLY the spec dir path and its task ID(s) —
  it reads the ACs, contracts, and `done when:` itself — plus the resolved tier's **effort
  cue** (rigor-tiers skill: moderate for `mvp`, full for `production`), prepended to its task.
  **When terse is resolved on** (Step 0), also prepend the terse cue (**terse** skill,
  verbatim) to every dispatched agent's task, right beside the effort cue; when terse is
  resolved off (the default), do not prepend it.
- Order and dispatch by the **effective graph from Step 2** (`deps:` ∪ `touch:` overlap):
  run tasks with no edge between them **in one batch**; sequence along every edge, declared
  or induced. A batch of **one** agent, or a fully sequential chain,
  runs in the **main working tree** — the agent checks its task's box in `tasks.md` on
  completion and commits `feat(<scope>): <title> (T<n>, specs/NNN)`, exactly as before.
- A batch of **two or more** agents runs with **worktree isolation** (below) so their edits
  cannot collide.
- Relay each agent's result compactly (files touched, test/lint output — actual numbers,
  and its one-line **self-critique** result: every dev agent runs one bounded pass over its
  own diff before returning (`self-critique` skill). An agent that omits the line skipped
  the pass; the line is never a substitute for the QE step below.)
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
4. **A rebase conflict is a collision** — a wrong edge, surfaced like drift, resolved by a
   `/wellforge:tasks` re-sync, never auto-resolved. With Step 2's `touch:` overlap now
   feeding the graph, a collision also means the colliding tasks' `touch:` lists were wrong:
   say so when you surface it.

**Environment faults beat code diagnoses.** If an agent in a worktree reports failures it
attributes to "pre-existing breakage", check the fault table in the worktree-isolation skill
before believing it — tests that fail in a worktree and pass on the integrated branch are an
isolation defect, and code must not be "fixed" on that evidence.

**Fallback.** If worktree isolation is unavailable (older Claude Code, or the option is
rejected), or the preflight left a class unclassified, fall back to the main-tree path —
dispatch the batch **sequentially** (not in parallel), each agent committing + checking its
own box. State which mode you used and, if the preflight forced it, which class.

## Step 3b — Security review, dispatched from the task graph

After integration, **before** QE. The security floor is non-negotiable (rigor-tiers), but
the specialist that reviews the code behind it used to run only when someone thought of it.
This step removes the remembering:

```bash
# Resolve the plugin root ONCE per session, then reuse $WF. ${CLAUDE_PLUGIN_ROOT} is
# substituted for HOOKS only — it is NOT exported to the Bash tool (measured: unset), so
# interpolating it here silently runs `python3 /scripts/...`.
WF=$(python3 -c "import json,os;p=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))['plugins'];print(next(i['installPath'] for k,v in p.items() if k.startswith('wellforge@') for i in v))" 2>/dev/null)
# Running from a checkout (claude --plugin-dir) installs nothing; fall back to the repo.
[ -n "$WF" ] || WF="$(pwd)/wellforge-plugin"
# A FUNCTION, not a variable holding a command: `WFPY="uv run ... python"` then `wfpy x`
# relies on word splitting, which zsh does not do for unquoted parameters — measured, it
# fails with `command not found: uv run --quiet --with pyyaml python`.
# uv first because forge-state needs pyyaml to read frontmatter and the system python3
# usually lacks it; without it every field reads as unknown.
wfpy() {
  if python3 -c "import yaml" 2>/dev/null; then python3 "$@"; else uv run --quiet --with pyyaml python "$@"; fi
}
wfpy "$WF/scripts/security-triggers.py" \
  --tier <resolved tier> --diff-base <the branch base> \
  --touch '<each touch: glob of the tasks in this batch>' --json
```

It reads `config/security-triggers.yml` and matches the **union** of the batch's declared
`touch:` globs and the actual `git diff --name-only` against the base. Both halves matter:
`touch:` catches the intent before the code exists, the diff catches the file nobody
declared. `production` reviews every batch; `mvp` and `spike` review on a match — that tier
difference is deliberate.

- `dispatch: false` → say so in one line and go to QE.
- `dispatch: true` → spawn **`wellforge:owasp-reviewer`** scoped to `scope[]` (the matched
  paths, or the whole changed set when the tier forced it). Give it the paths and nothing
  else; it reads the code itself.
- **Findings ≥ medium are defects** and route exactly like QE failures — the owner table and
  the **2-round cap** in the rigor-tiers skill's *"Routing a QE FAIL"* section, shared so the
  two loops cannot drift apart. A security finding that is really a wrong AC goes to the PO,
  not to a dev.
- Record the outcome as `verdicts.security` in the run trace (PASS / FAIL / null when not
  dispatched), with the matched rules. A review that happened and a review that was never
  needed must not read the same afterwards.

If the script is unavailable, **dispatch anyway and say why**: one extra mid-tier agent is
the cost of being wrong in that direction; an unreviewed auth change is the cost of the other.

## Step 4 — Verify

- Spawn `wellforge:quality-engineer` scoped to the tasks just implemented: it runs the gates and
  checks the ACs those tasks serve, and returns a verdict table.
- **`production`** — every gate blocks. **`mvp`** — QE runs in advisory mode: only SAST-high,
  lint, typecheck and the security floor block, coverage is reported as a gap.
- On FAIL, follow the **rigor-tiers** skill's *"Routing a QE FAIL — triage before you loop"*
  section: the owner-per-defect table (an environment fault owns nobody), the **2-round cap**,
  and how it composes with `systematic-debugging`'s 3-attempt stop. Do not restate it here —
  one copy is the point.
- The **security floor** (secret scan, no hardcoded creds, critical-CVE audit) blocks in BOTH
  tiers — never waived.
- QE may still recommend a security pass beyond what Step 3b matched (it reads the code, the
  triggers read paths) — spawn `wellforge:owasp-reviewer` for it and treat findings ≥ medium
  as defects, same loop. That is now the *exception* path; Step 3b is the rule.

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
start of this run and, now, write `.forge/runs/<run_id>.json` (schema `wellforge-run/v3`)
with every dispatched agent + outcome, any drift events (resolved or not), the QE verdict,
and `result` (completed / escalated / partial). Record the isolation mode used, any
collision events, and any environment faults (per the observability skill's `worktree` /
`collision_events` / `env_faults` fields) — including, when a batch fell back to sequential,
the preflight class that forced it.
Set `plugin_version` to the running plugin's version (from its `.claude-plugin/plugin.json`)
— a trace outlives the plugin that produced it, and the tier rules, agent roster and gate it
records all move with that version. Set `rigor_recorded` when Step 0 resolved a tier different from the feature's own `rigor:`
(a `--mode` downgrade must be legible in the trace, not only in the transcript that
scrolls away). Set `terse` to the boolean resolved in Step 0 (`true` iff `--terse` resolved
on for this run, `false` otherwise); leave `control_run_id` `null` (pairing to a control run is a later
concern, not this command's). One file per run; leave `tokens`/`cost` null (the
SubagentStop hook + `run-report.py` fill cost). This is the audit trail.

## Hard rules

- Implement ONLY the selected tasks. Discovering adjacent work is a new task (add it via
  `/wellforge:tasks` re-sync), not scope to absorb here.
- Never modify spec.md/plan.md or task definitions — only checkboxes. Drift is reported.
- Bounded loops only: QE fix loop max 2 rounds, then escalate. No silent retrying.
- For a brand-new feature with no spec yet, this is the wrong command — use
  `/wellforge:spec` (or `/wellforge:orchestrate` for the whole pipeline).
