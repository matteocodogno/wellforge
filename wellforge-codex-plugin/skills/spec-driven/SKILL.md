---
name: spec-driven
description: >
  WellForge spec-driven development conventions: the spec → plan → tasks workflow, file formats,
  status lifecycle, and drift rule. Use whenever working in a project that has a specs/
  directory, when the user mentions a spec, feature specification, or task list, when
  implementing any task that references a specs/NNN-slug/ path, or when asked about the
  status of a feature. Also the authoritative reference for the $wf-spec,
  $wf-plan, $wf-design, and $wf-tasks commands — they MUST follow this
  format exactly.
---

# Spec-driven development — WellForge conventions

One standardized path from idea to reviewed task list. Three artifacts per feature, three
commands, two human approval gates. The spec directory is the **contract** between agents:
the Product Owner writes spec.md, the Architect writes plan.md, developers consume tasks.md.

```
idea ──$wf-spec──► spec.md ──[user approves]──$wf-plan──► plan.md ──[user approves]──$wf-tasks──► tasks.md ──► implementation
                                                              └─(UI features)─$wf-design──► design.md ──┘
```

For **UI features**, the optional **design** stage (`$wf-design`, the `wf-designer`
agent) runs between plan and tasks — flows, screens/states, component reuse, a11y — so
frontend tasks derive from a real inventory. **Ungated by default** (validated at QE — the
flow's only mandatory gates are spec and plan); opt into a design checkpoint with
`$wf-design --gate`. `$wf-orchestrate` runs it automatically for UI features;
in the manual flow, `$wf-plan` and `$wf-tasks` nudge you to it.

## Directory layout

```
specs/
├── 20261104-user-auth/
│   ├── spec.md      # WHAT & WHY — problem, user stories, acceptance criteria
│   ├── ledger.md    # optional — the decision ledger from $wf-grill-me (who decided what)
│   ├── plan.md      # HOW — architecture, data model, API contracts, test strategy
│   ├── design.md    # optional, UI features only — flows, screens, component reuse, a11y
│   ├── tasks.md     # ordered, dependency-aware task list
│   ├── decisions.md # what the implementing agents decided for you (main loop appends)
│   ├── eval.md      # optional — per-feature rubric overrides (add dims / raise floors only)
│   ├── qe-report.md    # the latest QE verdict table (written by the quality-engineer)
│   └── eval-report.md  # LM-judge scored verdict (written by $wf-eval)
├── 20261109-csv-export/
│   └── spec.md
└── 20261112-pricing-poc/
    └── brief.md     # spike tier ONLY — a brief replaces spec/plan/tasks (see rigor-tiers)
```

The full spec→plan→tasks set is the `production` tier. Lower **rigor tiers** carry less:
`mvp` skips `plan.md`/`design.md`/`eval` (one gate), and `spike` replaces the whole set with
a single `brief.md`. The tier lives in the feature's frontmatter as `rigor:` (default
`production`). See the **rigor-tiers** skill — load it whenever a feature isn't production.

- `NNN` is the feature **id**: the creation date as `YYYYMMDD` (today, local time) — never a
  counter. Several people branch off the same `main` and create features in parallel; a
  sequential counter (`ls specs/ | sort | tail -1` + 1) hands every one of them the same
  number, and the collision only shows up after the merge. A date needs no coordination;
  `id + slug` is the identity, so two features on the same day are distinct by slug. If
  `specs/<today>-<slug>/` already exists, it is the same feature (resume it) or the slug is
  not specific enough (pick a sharper one) — never append a counter.
- Legacy 3-digit ids (`001-user-auth`) stay valid — they sort before every dated id, so a
  half-migrated `ls specs/` is still chronological. A project renames them with
  `scripts/migrate-ids.py` (offered by `$wf-upgrade`), never by hand: the script
  rewrites every reference and records old → new in `.forge/id-migration.json`, which is
  how the old ids in commit messages stay readable. Wherever this plugin writes
  `NNN-slug`, read *id-slug* — either form.
- `slug` is short kebab-case; never rename a directory after creation (it's referenced from commits).

## Status lifecycle

Status lives in **spec.md frontmatter only** (plan.md has its own `status` limited to
`draft | approved`; design.md is `draft` and only reaches `approved` if you opt into the
design checkpoint with `$wf-design --gate` — by default design is ungated and stays
`draft`, validated at QE). Transitions:

```
draft ──► approved ──► in-progress ──► done
                                ├────► superseded (another spec took the work over)
                                └────► archived   (deliberately stopped, no successor)
```

Three terminal statuses, one guarded command. `done` means it shipped and met its gate;
`superseded` means another spec owns the work now; `archived` means it was stopped on
purpose. All three are set only by `$wf-done` (`--superseded-by` / `--archive`), and
the distinction matters downstream: `$wf-triage` skips all three, but only `archived`
carries a recorded reason, and only `superseded` carries a pointer that triage checks.

- Only the **user** moves a spec from `draft` to `approved` — never set it yourself.
  Record approval as `approved: 2026-06-04` in the frontmatter when the user says so.
- **`archived`** is the exit for work deliberately stopped with no successor — the rejected
  approach, the deprioritised feature, the spike that answered its question and ends there.
  Set it with `$wf-done <feature> --archive "<reason>"`; the reason is **required**,
  because an archived spec without one is indistinguishable from an abandoned one. It runs
  no gate and touches nothing but the frontmatter (`status`, `archived:`,
  `archive_reason:`) — the code stays in git. Never an agent's decision: stopping work is a
  human call.
- **`superseded`** is the lifecycle's other exit: another spec took the work over, so this one
  stops without being delivered. Set it with `$wf-done <feature> --superseded-by
  <NNN-slug>` — the same guarded command, since it is the same kind of transition; it records
  `superseded_by:` and `superseded:` and runs no done gate (there is nothing to verify when
  nothing was claimed). Never hand-edit it, never use it to retire work that merely failed its
  gate, and never apply it to a `done` feature. `$wf-status` shows it as retired and
  `$wf-triage` skips it — the reason the status exists is so an abandoned spec stops
  being reported as rot.
- `in-progress` is set when the first task starts. Reaching `done` goes through the guarded
  **`$wf-done`** procedure and nowhere else — never a hand-edit, never an agent, and
  never a second copy of the gate. `$wf-orchestrate` (both pipelines),
  `$wf-promote` and `$wf-spike` all *call* that procedure rather than flipping
  the status themselves; "same gate, re-implemented" is how the copies drift apart. The **done gate is tier-aware**: `production` needs every task
  checked + QE PASS + **a security review PASS** + a fresh passing `eval-report.md` (the
  LM-judge — QE alone isn't enough, "set the bar at the eval, not the demo") + **no drift**;
  `mvp` needs tasks checked + QE-light PASS (no eval, no security verdict); `spike` closes
  via its `brief.md` findings. `$wf-done` refuses to close a feature whose gate isn't
  met.

  This sentence is a summary, not the definition — it omitted security and drift for a
  while and nothing noticed, because nothing reads it. The definition is
  `forge-state.py done_gate()`; print it with `--explain-gate`, and see
  [`$wf-done`](../wf-done/SKILL.md) for the generated table.

## File formats

### spec.md

```markdown
---
id: 002
slug: csv-export
status: draft
rigor: production   # production (default) | mvp | spike — see the rigor-tiers skill
created: 2026-06-04
---

# CSV export for reports

## Problem
<2-5 sentences: who hurts, how, why now. No solutions here.>

## User stories
### US-1: <title>
As a <role>, I want <capability>, so that <benefit>.
**Acceptance criteria:**
- AC-1.1: Given <context>, when <action>, then <observable outcome>.
- AC-1.2: ...

## Non-goals
- <explicitly out of scope, with one-line reason>

## Open questions
- [ ] <question> — owner: <who>
```

Rules: every AC must be objectively verifiable (a QE can turn it into a test without
asking anything). Open questions must be empty or explicitly accepted-as-risk before approval.

### plan.md

```markdown
---
spec: 002
status: draft
---

# Plan: CSV export for reports

## Architecture
<components touched/added, sequence of interactions, why this shape. Reference ADRs.>

## Data model
<new/changed tables, migrations needed>

## API contracts
<endpoints/events with request/response shapes — concrete, not prose>

## Test strategy
<what gets unit / integration / e2e coverage; which ACs map to which test level>

## Risks
<what could invalidate this plan>

## Security
<security-sensitive? YES/NO + why (auth, PII, upload, external calls, payments, regulated
data). YES schedules an owasp-reviewer pass in parallel with QE — see the architect agent.>
```

### tasks.md

```markdown
---
spec: 002
generated: 2026-06-04
synced: 2026-06-11        # last re-sync against the spec (see the drift rule)
---

# Tasks: CSV export for reports

- [ ] T1: <imperative title> — refs: US-1, AC-1.1 — deps: none
  - touch: `backend/src/.../ReportExporter.kt`, `backend/src/db/migrations/*`
  - done when: <objective check, e.g. "integration test X passes">
- [ ] T2: ... — deps: T1
```

At **rigor `mvp`** the file additionally opens with the folded-away plan — the architect
never ran, so the contracts have to live somewhere a dev agent will read:

```markdown
## Architecture notes        <!-- mvp ONLY: no plan.md exists. Omit at production. -->
- Components: <what is touched or added>
- Contracts: <per task — concrete request/response shapes incl. error cases>
- Data model: <schema change + migration>
- Deferred: <what this tier is knowingly not doing>
```

A contract written there binds the dev agents exactly as a plan.md contract does; drift
against it is drift, routed to the PO (mvp has no architect). At `production` the section
must be absent — plan.md is the contract, and a second copy drifts from it.

Rules: every task references at least one AC; every AC is covered by at least one task;
`deps:` must form a DAG (tasks with no mutual deps may run in parallel).

**`touch:` is binding, not commentary.** It is a comma-separated list of repo-relative paths
or globs, and the parallel dispatcher reads it: two tasks whose `touch:` lists overlap get a
scheduling edge **even with no declared `deps:`**, because they were never safe to run
concurrently. So:

- **Effective graph = declared `deps:` ∪ `touch:` overlap.** `deps:` records what must exist
  before what; overlap records what cannot happen *at the same time*. Both are edges, and
  only the union is safe to batch on.
- **Use a glob when the task creates rather than edits** — `db/migrations/*` rather than a
  guessed filename. Two tasks that each add a sequentially-numbered migration collide on the
  *counter*, not on a file: the merge is clean and the ordering is wrong. The glob is what
  makes that visible. Same for any other numbered series.
- An incomplete `touch:` list is the input that makes a parallel batch unsafe. If a task's
  real footprint isn't knowable yet, say so (`touch: unknown — <why>`) and it will be
  scheduled alone rather than guessed at.

See [`worktree-isolation`](../worktree-isolation/SKILL.md) for how the effective graph is computed and enforced at dispatch.

### decisions.md

The ledger records what the **user** decided. This file records what the **agents** decided
on the user's behalf while building: the choices no spec, plan or task dictated, which
otherwise live only in the code, where a reviewer finds them by accident or not at all.
Accepting work without knowing which choices are in it is how delegating turns into
surrendering the judgement.

**Who writes what.** Every `wf-backend-dev`, `wf-frontend-dev` and `wf-devops` report ends with a
`DECISIONS:` block — the `subagent-decisions-guard` hook sends an agent back once if it is
missing. The agents never write this file (parallel worktrees would collide on it): the
**main loop** appends each returned block, verbatim, under a heading for that dispatch.
`$wf-implement` and `$wf-orchestrate` do it after every dev/devops return;
`$wf-done` shows it before closing.

```markdown
# Decisions — CSV export for reports

Choices the agents made that the spec, plan and tasks did not dictate. Disagree with one?
It is drift: amend the spec/plan and re-sync tasks — do not quietly edit the code.

## T3 · backend-dev · 2026-11-10
- default: page size 50 — why: spec silent, matches the list endpoint — where: ExportService.kt
- scope: formula escaping in cells deferred — why: no AC covers it — where: T3
- reinterpretation: "recent" read as last 30 days — why: AC-2 gives no window — where: T3
- assumption: timestamps are UTC in the DB — why: not verified against prod — where: ExportRow.kt

## T4 · frontend-dev · 2026-11-10
none — the task named every value
```

The four kinds, and only these: **default** (picked a value where the text was silent),
**scope** (left something out or deferred it), **reinterpretation** (read a requirement one
way when another reading was possible), **assumption** (took something as true without
checking). An agent with nothing to declare says `DECISIONS: none — <why>`; the main loop
records that line too, so an empty section reads as a statement, not an omission.
A `reinterpretation` of an AC is drift-adjacent: if the other reading is the one the user
meant, it is drift, routed as such. No frontmatter — the file has no lifecycle and is not a
gate input.

## Workflow gates

- `$wf-plan` MUST refuse to run if spec.md status is not `approved`.
- `$wf-tasks` MUST refuse to run if the tier's upstream artifact is not `approved`:
  `plan.md` at `production`, **`spec.md` at `mvp`** (that tier has no plan.md by design —
  see [`rigor-tiers`](../rigor-tiers/SKILL.md)). `$wf-implement` gates the same way. Gating an mvp feature on
  an approved plan dead-ends it permanently: nothing in the flow ever produces one.
- Never skip a stage "because it's small" — for trivial changes the spec is 10 lines, not
  absent. The ONLY sanctioned way to run fewer stages is a **declared lower rigor tier**
  (`rigor: mvp`/`spike` in frontmatter, via `$wf-spike` or `--mode`) — explicit and
  recorded, never an ad-hoc skip. These gates apply in full to the `production` tier.

## Self-critique before the gate

Whoever writes an artifact runs **one** bounded self-critique pass over it before handing it
to the gate that follows (spec → the human gate, plan → the human gate, tasks → dispatch,
code → QE). See [`self-critique`](../self-critique/SKILL.md) for the per-artifact checklists and the one-pass rule. It
changes content only: it never sets `status:`, never checks a box, and never replaces the
gate, QE or the evaluator — those stay independent, which is the whole point of them.

## Drift rule

The spec is the source of truth. If implementation reveals the spec/plan is wrong:

1. Stop, update spec.md / plan.md first (status stays `in-progress`, note the change).
2. Re-run `$wf-tasks` to re-sync tasks.md.
3. Then continue coding.

**Lifecycle frontmatter edits are never drift.** Changing `status`, `done`, `approved`,
`superseded_by`, `archive_reason`, `rigor` or `plugin` is bookkeeping about where the
feature *is*, not a change to what it asks for — so do NOT re-run `$wf-tasks` after
a status change. `forge-state.py` compares the spec's BODY (and any non-lifecycle
frontmatter field) against the committed version, so closing a feature cannot report drift
against its own task list. It once did: `$wf-done` writes `status: done` as its last
action, which made spec.md newer than tasks.md and the gate refused the transition it had
just performed.

Enforced mechanically: the Stop hook (`stop-verify.sh`) blocks finishing a session where
`spec.md`/`plan.md` changed but `tasks.md` did not.

**Know the scope, because the failure mode is surprising.** The check covers every change on
the branch **since its merge base**, not just uncommitted edits — it has to, since dev agents
commit their work and a check that only saw unstaged files saw nothing at all. The
consequence: a one-line typo fix in `spec.md`, committed three commits ago, blocks *every*
Stop for the rest of the branch until `tasks.md` is touched. "I fixed a typo and now Claude
can't stop" is the same rule working, but it does not feel like it.

The escape is `$wf-tasks <slug>` (re-sync mode), which preserves checked tasks and
**always stamps `synced:`** even when nothing else changes — without that stamp the escape
would not clear the block, which is the trap this rule had until 2026-09-20. If you are
certain a spec edit is purely cosmetic, the re-sync is still the right move: it costs one
command and records that the task list was re-checked. Do not reach for `--no-verify` or
edit `tasks.md` by hand to satisfy the hook; that is the drift rule defeated rather than
followed.

## Implementing tasks

- Work tasks in dependency order; set the checkbox immediately on completion.
- Reference task IDs in commit messages: `feat(report): add CSV serializer (T1, specs/002)`.
- When the last task is checked and gates pass, close the feature with `$wf-done`
  (it verifies the tier's done gate before flipping the status).
