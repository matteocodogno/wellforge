# WellForge — Features

WellForge is welld's internal platform for **reproducible, standard, fast AI-assisted
project setup**: from product idea to a building, CI-gated, spec-driven, AI-ready
repository in minutes — and a fleet that stays upgradeable as standards evolve.

It is built as three layers, because no single mechanism covers everything:

| Layer | Vehicle | Covers |
|---|---|---|
| `welld-dev-plugin/` | Claude Code plugin (commands, agents, skills, hooks, MCP) | spec workflow, agent team, orchestration, local enforcement |
| `copier.yml` + `templates/` | [Copier](https://copier.readthedocs.io) monorepo template, semver-tagged | scaffolding, project lifecycle/upgrades |
| `.github/workflows/` + `gates/` | Reusable GitHub Actions + central configs | quality gates (CI enforcement) |

---

## 1. Spec-driven framework

One standardized path from idea to reviewed task list. Three artifacts per feature in
`specs/NNN-slug/`, three commands, two human approval gates:

```
idea ─/welld-dev:spec→ spec.md ─[approve]─/welld-dev:plan→ plan.md ─[approve]─/welld-dev:tasks→ tasks.md ─/welld-dev:implement→ code
```

| Artifact | Content | Author |
|---|---|---|
| `spec.md` | problem, user stories with Given/When/Then acceptance criteria, non-goals, open questions | Product Owner |
| `plan.md` | architecture, data model, API contracts, AC→test mapping, risks | Architect |
| `design.md` (UI features) | flows, screens & states, component reuse map, a11y | Designer |
| `tasks.md` | DAG-ordered tasks, each with AC refs, deps, touched files, objective "done when" | derived |

Key properties:
- **Status lifecycle** `draft → approved → in-progress → done`; only the human user
  approves — no command or agent can self-approve.
- **Gates are structural**: `/welld-dev:plan` refuses a non-approved spec; `/welld-dev:tasks`
  refuses a non-approved plan.
- **Bidirectional coverage**: every AC covered by ≥1 task, every task serves ≥1 AC
  (taskless work = scope creep, flagged).
- **Drift rule**, mechanically enforced by a Stop hook: if `spec.md`/`plan.md` change
  without re-syncing `tasks.md`, the session cannot finish cleanly.
- Re-running `/welld-dev:tasks` preserves completed tasks (re-sync mode).
- `/welld-dev:implement [feature] [tasks]` implements tasks of a feature folder —
  e.g. `001-user-auth T3,T5`, `user-auth next`, or just `all` (feature inferred from the
  in-progress spec). Dep-free tasks dispatch to FE/BE/devops agents in parallel, then a
  scoped QE verdict — the implementation slice of the orchestrator, callable directly.

Why in-house instead of BMAD/Kiro/cc-sdd: we keep the proven spec→plan→tasks *shape*
but own the prompts, so they encode welld conventions and don't churn under us.

## 2. Multi-agent team

Nine agents with crisp role boundaries — each has explicit inputs, one artifact, and a
"must NOT" list that prevents role bleed:

| Agent | Produces | Hard boundary |
|---|---|---|
| `product-owner` | spec.md (draft) | no solutioning; user tech input recorded verbatim as constraints |
| `architect` | plan.md (draft) + ADR candidates | never edits the spec; proposes amendments instead |
| `designer` | design.md | no production code; flags UI no AC asks for |
| `frontend-dev` | code + checked tasks | task `touch:` list = blast radius; contract mismatch → report, never adapt silently |
| `backend-dev` | code + checked tasks | API contract in plan.md is law; migrations only, never edit generated sources |
| `devops` | pipelines, infra, connections | calls central gates, never inlines copies; cannot change thresholds |
| `quality-engineer` | evidence-based verdict table | never fixes production code; single ✗ = FAIL, no "pass with remarks" |
| `owasp-reviewer` (specialist) | OWASP Top 10 review | invoked by caller on QE recommendation |
| `adr-writer` (specialist) | MADR-format ADRs | invoked by caller on architect's candidates |

Agents run non-interactively: they cannot ask the user anything (questions become
`## Open questions`) and can never set `approved` — approval physically lives in the
calling session.

## 3. AI orchestrator

`/welld-dev:orchestrate <goal>` classifies the request and drives the team:

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
- **Drift pauses the pipeline** and routes to the owning agent (PO for spec, architect
  for plan), tasks re-sync, then resume.

## 4. Scaffolder + connection layer

`/welld-dev:new` goes from product description to a working repo:

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
internal platforms die.

**Brownfield:** existing projects onboard with `/welld-dev:adopt` — AI-readiness files
generated from *observed* conventions, the spec workflow, and optionally the central
gates with a **measured coverage baseline** (ratchet: raise-only, gap-to-target
reported in CI) instead of the born-clean 80% bar. Adoption adds files, never rewrites
code; `/welld-dev:upgrade` remains scaffold-only (no template ancestry to re-apply).

## 5. Quality gates

Objective, central, enforceable. CI is the enforcement point; thresholds live in the
reusable workflows' `env` blocks and change **only via PR** to this repo:

| Check | Node (`quality-node.yml`) | JVM (`quality-jvm.yml`) |
|---|---|---|
| Lint | `pnpm run lint`, zero warnings | ktlint |
| Types | `pnpm run typecheck` | Kotlin compiler |
| Coverage | Vitest lines ≥ 80% / branches ≥ 70% (CLI-enforced — project config can't weaken it) | JaCoCo lines ≥ 80% (branches reported) |
| Dependency audit | `pnpm audit --audit-level high` + lockfile required | osv-scanner |
| SAST | semgrep: welld rules + p/typescript | semgrep: welld rules + p/kotlin |

- Projects call the workflows pinned to a `gates-v*` tag — a threshold bump propagates
  by a one-line ref bump, no re-scaffold.
- Fresh scaffolds don't fail their own gate: modules under 50 lines skip coverage
  enforcement *with a visible CI notice*.
- Locally, plugin hooks run the same project tasks (lint/typecheck/compile) for fast
  feedback; the QE agent runs the full gate set and reports numbers.

## 6. Project lifecycle

Generated projects are not snapshots — they follow the template:

- `.forge/manifest.json` + `.copier-answers.yml` record template, version, and answers.
- **`/welld-dev:upgrade`**: pre-flight (clean tree, plan-of-record with template
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
