# WellForge — Features

WellForge is an open platform for **reproducible, standard, fast AI-assisted
project setup**: from product idea to a building, CI-gated, spec-driven, AI-ready
repository in minutes — and a fleet that stays upgradeable as standards evolve.

It is built as three layers, because no single mechanism covers everything:

| Layer | Vehicle | Covers |
|---|---|---|
| `wellforge-plugin/` | Claude Code plugin (commands, agents, skills, hooks, MCP) | spec workflow, agent team, orchestration, local enforcement |
| `copier.yml` + `templates/` | [Copier](https://copier.readthedocs.io) monorepo template, semver-tagged | scaffolding, project lifecycle/upgrades |
| `.github/workflows/` + `gates/` | Reusable GitHub Actions + central configs | quality gates (CI enforcement) |

---

## 1. Spec-driven framework

One standardized path from idea to reviewed task list — a command per stage, two human
approval gates, plus an optional **design** stage for UI features:

```
idea ─/wellforge:spec→ spec.md ─[approve]─/wellforge:plan→ plan.md ─[approve]─/wellforge:tasks→ tasks.md ─/wellforge:implement→ code
                                                  └─(UI)─/wellforge:design→ design.md ─┘
```

| Artifact | Content | Author |
|---|---|---|
| `spec.md` | problem, user stories with Given/When/Then acceptance criteria, non-goals, open questions | Product Owner |
| `plan.md` | architecture, data model, API contracts, AC→test mapping, risks | Architect |
| `design.md` (UI features) | flows, screens & states, component reuse map, a11y | Designer (ungated by default; `/wellforge:design --gate` adds an approve/iterate checkpoint) |
| `tasks.md` | DAG-ordered tasks, each with AC refs, deps, touched files, objective "done when" | derived |

Key properties:
- **Status lifecycle** `draft → approved → in-progress → done`; only the human user
  approves — no command or agent can self-approve.
- **Gates are structural**: `/wellforge:plan` refuses a non-approved spec; `/wellforge:tasks`
  refuses a non-approved plan.
- **Bidirectional coverage**: every AC covered by ≥1 task, every task serves ≥1 AC
  (taskless work = scope creep, flagged).
- **Drift rule**, mechanically enforced by a Stop hook: if `spec.md`/`plan.md` change
  without re-syncing `tasks.md`, the session cannot finish cleanly.
- Re-running `/wellforge:tasks` preserves completed tasks (re-sync mode).
- `/wellforge:implement [feature] [tasks]` implements tasks of a feature folder —
  e.g. `001-user-auth T3,T5`, `user-auth next`, or just `all` (feature inferred from the
  in-progress spec). Dep-free tasks dispatch to FE/BE/devops agents in parallel, then a
  scoped QE verdict — the implementation slice of the orchestrator, callable directly.
- `/wellforge:status` recaps every feature's position in the flow (spec/plan/tasks/
  implement/done) with task progress and the exact next command to run — read-only,
  derived from a deterministic state table so the "next step" never drifts.

Why in-house instead of BMAD/Kiro/cc-sdd: we keep the proven spec→plan→tasks *shape*
but own the prompts, so they encode WellForge conventions and don't churn under us.

**Rigor tiers — match ceremony to stakes.** Full rigor is right for production, wasteful for
a feasibility spike that may be thrown away. A feature's `rigor:` (default `production`)
selects how much pipeline runs:

| Tier | Pipeline | Gates | For |
|---|---|---|---|
| `spike` | `/wellforge:spike` — main loop, `brief.md` → code, **no agents, no approval gate** | lint/typecheck/build advisory | PoC / feasibility / business-model experiments |
| `mvp` | `--mode mvp` — PO → 1 gate → tasks → dev agents → light QE (no architect/designer/eval) | SAST-high blocks, coverage advisory | first release to validate with users |
| `production` | the full flow above (unchanged) | full 80% + SAST + eval | long-lived products |

The principle is **defer, don't lower**: a lower tier is a *declared, recorded* debt (the
`rigor:` frontmatter), promoted to full rigor only via `/wellforge:promote` — never silently.
A **non-negotiable security floor** (secret scan, no hardcoded creds, critical-CVE audit)
blocks in *every* tier; "fast" never means "leaks credentials." Canonical reference: the
`rigor-tiers` skill.

## 2. Multi-agent team

Ten agents with crisp role boundaries — each has explicit inputs, one artifact, and a
"must NOT" list that prevents role bleed (seven role agents, the LM-judge evaluator, and
two specialists):

| Agent | Produces | Hard boundary |
|---|---|---|
| `product-owner` | spec.md (draft) | no solutioning; user tech input recorded verbatim as constraints |
| `architect` | plan.md (draft) + ADR candidates | never edits the spec; proposes amendments instead |
| `designer` | design.md | no production code; flags UI no AC asks for |
| `frontend-dev` | code + checked tasks | task `touch:` list = blast radius; contract mismatch → report, never adapt silently |
| `backend-dev` | code + checked tasks | API contract in plan.md is law; migrations only, never edit generated sources |
| `devops` | pipelines, infra, connections | calls central gates, never inlines copies; cannot change thresholds |
| `quality-engineer` | evidence-based verdict table | never fixes production code; single ✗ = FAIL, no "pass with remarks" |
| `evaluator` (LM-judge) | `eval-report.md` scored verdict | judges only, never fixes; distinct from QE — the gate into `done` (§5) |
| `owasp-reviewer` (specialist) | OWASP Top 10 review (jOOQ/Drizzle/React-aware) | scheduled in parallel with QE when the plan flags the feature security-sensitive, or on QE recommendation |
| `adr-writer` (specialist) | MADR-format ADRs | invoked by caller on architect's OR a dev agent's ADR candidates |

Agents run non-interactively: they cannot ask the user anything (questions become
`## Open questions`) and can never set `approved` — approval physically lives in the
calling session.

## 3. AI orchestrator

`/wellforge:orchestrate <goal>` classifies the request and drives the team:

- **feature** — PO → *gate 1* → Architect → *gate 2* (+ adr-writer) → Designer (UI only)
  → tasks → dev agents in parallel where the task DAG allows → QE verdict → done
- **bugfix** — QE writes the smallest failing repro test first → dev fixes → QE verifies
- **refactor** — architect mini-plan with explicit behavior invariants → gate → tasks → QE
- **infra** — devops, with a gate before prod-like changes

Mechanics that make it reliable:
- **Disk-based handoffs**: every stage's artifact is verified on disk before the next
  stage starts; agents receive file paths, not chat summaries — survives context
  compaction and makes pipelines resumable (spec status frontmatter = resume point).
- **Exactly 2 human gates** on the feature flow — never auto-approved, never more
  approval theater than that.
- **Bounded loops**: QE fix loop max 2 rounds, then escalation with the verdict table.
- **Defect triage, not blind dev-routing**: a QE/eval failure is routed to its *true* owner
  — a code bug to the dev, but a wrong/untestable AC to the PO, a wrong contract to the
  architect, a missing designed state to the designer (each a drift amendment + tasks re-sync).
- **Proactive security**: the architect flags security-sensitive features in `plan.md`, so
  the owasp review is *scheduled* in parallel with QE — not discovered late.
- **Drift pauses the pipeline** and routes to the owning agent (PO for spec, architect
  for plan), tasks re-sync, then resume.

## 4. Scaffolder + connection layer

`/wellforge:new` goes from product description to a working repo:

1. **Interview** — product type, scale/lifetime, domain complexity, team constraints.
2. **Stack recommendation** with rationale (and an honest "fits neither → stop"):

| Preset | Sweet spot |
|---|---|
| `spring-kotlin-react` | rich domain logic, transactions, long-lived products, JVM ecosystem (Spring Boot 4, Kotlin, jOOQ, Liquibase, Modulith / React TS Vite) |
| `hono-react` | lightweight APIs, fast iteration, all-TypeScript teams (Hono, Drizzle / React TS Vite) |

3. **Generation** via the root `copier.yml` (one entry point, `--data preset=<name>`).
   Every generated project ships **AI-ready**: project `CLAUDE.md`, pre-allowed
   `.claude/settings.json`, `specs/` directory, mise toolchain (pinned versions, standard
   task names), CI calling the central gates, `.forge/manifest.json` (the upgrade contract).
4. **Build verification** — `mise run install/build/test` is the acceptance bar; failures
   are template bugs to report, not things to patch around.
5. **Connections** — standardized checklists (GitHub repo + branch protection, CI
   secrets, MCP servers, environments/DB). Every checklist opens and closes with an
   executed **verification command**: "connected" is an observed fact. Incompletable
   steps become explicit PENDING items, never silent skips.

Hard rule: max 2 presets until the pilot proves the model — template sprawl is how
platforms like this die.

**Brownfield:** existing projects onboard with `/wellforge:adopt` — AI-readiness files
generated from *observed* conventions, the spec workflow, and optional layers: the central
gates with a **measured coverage baseline** (ratchet: raise-only, gap-to-target reported in
CI) instead of the born-clean 80% bar, and **release management** (a stack-detected
`.release-it.json` — bumper targets its actual version files, git-tag-based, paired with
commit-lint; skipped if the project already has a release tool). Adoption adds files, never
rewrites code. It's **incremental** — re-run `/wellforge:adopt` on an already-adopted project
to add a layer you skipped (it detects `.forge/adoption.json`, offers only the missing layers,
and merges the record); the core is never regenerated. `/wellforge:upgrade` remains
scaffold-only (no template ancestry to re-apply).

## 5. Quality gates

Objective, central, enforceable. CI is the enforcement point; thresholds live in the
reusable workflows' `env` blocks and change **only via PR** to this repo:

| Check | Node (`quality-node.yml`) | JVM (`quality-jvm.yml`) |
|---|---|---|
| Lint | `pnpm run lint`, zero warnings | ktlint |
| Types | `pnpm run typecheck` | Kotlin compiler |
| Coverage | Vitest lines ≥ 80% / branches ≥ 70% (CLI-enforced — project config can't weaken it) | JaCoCo lines ≥ 80% (branches reported) |
| Dependency audit | `pnpm audit --audit-level high` + lockfile required | osv-scanner |
| SAST | semgrep: WellForge rules + p/typescript | semgrep: WellForge rules + p/kotlin |

- **Conventional Commits gate** — generated `quality.yml` also calls `commit-lint.yml`,
  which validates every PR commit against `type(scope)!: description`. CI is the
  enforcement point; a local `commit-msg` hook gives fast feedback. Shared validator
  (`gates/scripts/check-commit-msg.py`); the dev agents already commit in this format.
- **Release management** — that enforced commit history is also the release engine.
  `/wellforge:release` (and `mise run release`) run **release-it** with
  `@release-it/conventional-changelog` (computes the semver bump + writes `CHANGELOG.md` from
  the commits) and `@release-it/bumper` (syncs the per-service version files; the JVM preset
  bumps `pom.xml` via a Maven hook). Every scaffold ships `.release-it.json` pre-wired:
  dry-run preview → confirm → version bump, `CHANGELOG.md`, `chore(release)` commit, `vX.Y.Z`
  tag, and a GitHub Release with generated notes — one reviewable, revertable release.
- Projects call the workflows pinned to a `gates-v*` tag — a threshold bump propagates
  by a one-line ref bump, no re-scaffold.
- Fresh scaffolds don't fail their own gate: modules under 50 lines skip coverage
  enforcement *with a visible CI notice*.
- Locally, plugin hooks run the same project tasks (lint/typecheck/compile) for fast
  feedback; the QE agent runs the full gate set and reports numbers.

**Eval gate (LM-judge).** Tests + the gates above cover the *deterministic* half. The
**eval** covers what only judgment can: spec fidelity, test *quality* (not just pass),
idiomatic code free of "looks-right" failures, trajectory, and — for UI features —
**design fidelity** (a conditional rubric dimension, scored only when `design.md` exists:
are the flows/states/a11y complete and did the build honor them; the total re-normalises
when it doesn't apply). `/wellforge:eval <feature>` spawns the `evaluator` LM-judge, which
scores against the central rubric (`gates/configs/eval-rubric.yml`: weighted dimensions,
per-dimension floors, pass ≥ 80) and writes a verdict to `specs/NNN/eval-report.md`. A **passing eval is the gate into
`done`** — QE alone isn't enough ("set the bar at the eval, not the demo"). An unmet AC
fails regardless of the total (floor rule). Also available as an opt-in CI gate
(`quality-eval.yml@gates-v2`, needs `ANTHROPIC_API_KEY`) — note that pinned tag still carries
the `default-v1` rubric (pre-`design_fidelity`); bump the `gates-ref` to pick up the current
rubric. The in-session evaluator always reads the repo's current rubric (`default-v2`). The rubric is central and
PR-governed like every threshold; per-feature `eval.md` may raise floors, never lower.

**Model routing (economics).** Agents don't all run the frontier model. A central
PR-governed policy (`config/model-routing.yml`) assigns each agent a tier — **frontier**
(opus) for the highest judgment (architect, the LM-judge evaluator), **mid** (sonnet) for
structured writing and implementation (PO, designer, FE/BE dev, devops, QE), reserving the
**cheap** tier for genuinely mechanical surfaces. This drives OpEx down without lowering
quality where it counts — the paper's "intelligent model routing." A drift guard
(`check-routing.py`) keeps each agent's frontmatter in sync with the policy; tiers are
calibrated by the pilot (too cheap causes rework loops — the OpEx trap). Security reviews
escalate to frontier for regulated projects.

**Observability (run traces).** Every multi-agent run (`implement`/`orchestrate`/`eval`)
writes an auditable trace to `.forge/runs/<run_id>.json` — which agents ran, for which
tasks, their outcomes, drift events, and verdicts. A `SubagentStop` hook adds best-effort
token telemetry; `run-report.py` joins them and estimates cost from a central price table.
`/wellforge:status` surfaces recent runs + cost; the `evaluator` reads traces for real
**trajectory** evidence (closing the eval harness's blind spot). The audit trail (who/what/
verdict/drift) is exact; the cost layer is an estimate, honestly labelled.

## 6. Project lifecycle

Generated projects are not snapshots — they follow the template:

- `.forge/manifest.json` + `.copier-answers.yml` record template, version, and answers.
- **`/wellforge:upgrade`**: pre-flight (clean tree, plan-of-record with template
  changelog) → `copier update --skip-answered --conflict inline` → AI conflict
  resolution (default stance: *keep project behavior, adopt template structure*;
  genuinely ambiguous → ask) → gates verify → one revertable commit.
- **Migrations**: mechanical version-boundary steps live in `copier.yml` `_migrations`;
  judgment calls are the upgrade command's job.
- **Releases**: repo-wide `vX.Y.Z` tags (patch cosmetic / minor additive / major needs
  migration). The `gates-v*` series is independent — gate bumps are never bundled into
  template upgrades.
- **Fleet visibility**: `scripts/fleet-status.sh <org>` prints every generated project
  with its template version vs the latest release.

The whole loop is E2E-tested: scaffold at v0.1.0 → template evolves → `copier update`
→ project at v0.1.1 with zero conflicts.

---

## See also

- [Installation](INSTALLATION.md) — set up WellForge on your machine
- [Quick start](QUICKSTART.md) — greenfield project in ~30 minutes
- [PLAN.md](PLAN.md) — build phases, status, honest deviations
- [Template contract](../templates/_shared/CONTRACT.md) · [Gates policy](../gates/README.md)
