---
name: spec-driven
description: >
  welld spec-driven development conventions: the spec → plan → tasks workflow, file formats,
  status lifecycle, and drift rule. Use whenever working in a project that has a specs/
  directory, when the user mentions a spec, feature specification, or task list, when
  implementing any task that references a specs/NNN-slug/ path, or when asked about the
  status of a feature. Also the authoritative reference for the /wellforge:spec,
  /wellforge:plan, and /wellforge:tasks commands — they MUST follow this format exactly.
---

# Spec-driven development — welld conventions

One standardized path from idea to reviewed task list. Three artifacts per feature, three
commands, two human approval gates. The spec directory is the **contract** between agents:
the Product Owner writes spec.md, the Architect writes plan.md, developers consume tasks.md.

```
idea ──/wellforge:spec──► spec.md ──[user approves]──/wellforge:plan──► plan.md ──[user approves]──/wellforge:tasks──► tasks.md ──► implementation
```

## Directory layout

```
specs/
├── 001-user-auth/
│   ├── spec.md      # WHAT & WHY — problem, user stories, acceptance criteria
│   ├── plan.md      # HOW — architecture, data model, API contracts, test strategy
│   ├── design.md    # optional, UI features only — flows, screens, component reuse, a11y
│   ├── tasks.md     # ordered, dependency-aware task list
│   ├── eval.md      # optional — per-feature rubric overrides (add dims / raise floors only)
│   └── eval-report.md  # LM-judge scored verdict (written by /wellforge:eval)
└── 002-csv-export/
    └── spec.md
```

- `NNN` is zero-padded and sequential across the project (`ls specs/ | sort | tail -1` to find the next).
- `slug` is short kebab-case; never rename a directory after creation (it's referenced from commits).

## Status lifecycle

Status lives in **spec.md frontmatter only** (plan.md has its own `status` limited to
`draft | approved`). Transitions:

```
draft ──► approved ──► in-progress ──► done
                                └────► superseded (link the successor)
```

- Only the **user** moves a spec from `draft` to `approved` — never set it yourself.
  Record approval as `approved: 2026-06-04` in the frontmatter when the user says so.
- `in-progress` is set when the first task starts; `done` requires THREE things: every
  task in tasks.md checked, quality gates pass (QE — deterministic), AND a passing
  `eval-report.md` (the LM-judge rubric scoring — the non-deterministic half, run by
  `/wellforge:eval`). QE pass alone is not enough to reach `done`: "set the bar at the
  eval, not the demo."

## File formats

### spec.md

```markdown
---
id: 002
slug: csv-export
status: draft
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
```

### tasks.md

```markdown
---
spec: 002
generated: 2026-06-04
---

# Tasks: CSV export for reports

- [ ] T1: <imperative title> — refs: US-1, AC-1.1 — deps: none
  - touch: `backend/src/.../ReportExporter.kt`
  - done when: <objective check, e.g. "integration test X passes">
- [ ] T2: ... — deps: T1
```

Rules: every task references at least one AC; every AC is covered by at least one task;
`deps:` must form a DAG (tasks with no mutual deps may run in parallel).

## Workflow gates

- `/wellforge:plan` MUST refuse to run if spec.md status is not `approved`.
- `/wellforge:tasks` MUST refuse to run if plan.md status is not `approved`.
- Never skip a stage "because it's small" — for trivial changes the spec is 10 lines, not absent.

## Drift rule

The spec is the source of truth. If implementation reveals the spec/plan is wrong:

1. Stop, update spec.md / plan.md first (status stays `in-progress`, note the change).
2. Re-run `/wellforge:tasks` to re-sync tasks.md.
3. Then continue coding.

Enforced mechanically: the Stop hook (`stop-verify.sh`) blocks finishing a session where
`spec.md`/`plan.md` changed but `tasks.md` did not.

## Implementing tasks

- Work tasks in dependency order; set the checkbox immediately on completion.
- Reference task IDs in commit messages: `feat(report): add CSV serializer (T1, specs/002)`.
- When the last task is checked and gates pass, set spec status to `done`.
