# WellForge

An open platform for **reproducible, standard, fast AI-assisted project setup** for any team.
Every new project currently costs hours of repetitive AI-infrastructure setup; WellForge turns
that into minutes, with a setup that stays upgradeable over time.

## The 6 pillars

1. **Spec-driven framework** — a standardized spec → plan → tasks workflow. Evaluated: BMAD,
   superpowers, Kiro, cc-sdd, Osmani agent-skills. Decision: build a **thin in-house layer**
   (spec-kit-style) packaged in the plugin, so we own it and it doesn't churn under us.
2. **Multi-agent system** — Product Owner, Architect, Designer, Frontend Dev, Backend Dev,
   DevOps, Quality Engineer as Claude Code subagents.
3. **AI orchestrator** — routes work to the right agent(s), enforces the spec workflow,
   coordinates handoffs (PO → Architect → Devs → QE).
4. **Scaffolder + connection layer** — analyzes the product type, recommends a stack, generates
   the scaffold from a versioned template, and guides MCP/CLI connections to ecosystem tools
   (GitHub, CI, cloud, observability) per stack.
5. **Quality gates** — objective, enforceable thresholds shipped with every scaffold: minimum
   coverage, lint/type-check, security scans (SAST), dependency audits. Defined centrally,
   enforced in CI and locally via hooks — never left to individual discretion.
6. **Project lifecycle** — generated projects record which template+version produced them and
   can be **upgraded** when presets evolve (template diff/merge + migration scripts). Without
   this the scaffolder is a snapshot that rots.

## Architecture decision

A Claude Code plugin alone covers pillars 1–3; pillars 4–6 need artifacts that live *outside*
the AI session (versioned templates, CI workflows). WellForge is therefore three layers:

| Layer | Vehicle | Covers |
|---|---|---|
| `wellforge-plugin/` | Claude Code plugin: skills, agents, commands, hooks, MCP | Pillars 1, 2, 3 + local gate enforcement |
| `copier.yml` + `templates/` | [Copier](https://copier.readthedocs.io) monorepo template (chosen for first-class `copier update` re-templating) | Pillars 4, 6 |
| `.github/workflows/` + `gates/` | Reusable GitHub Actions workflows + central thresholds/SAST configs, referenced (not copied) by scaffolds | Pillar 5 |

`/wellforge:new` is the front door: interview → stack recommendation → `copier copy` →
build verification → connection checklists → first spec. `/wellforge:upgrade` re-runs
`copier update` against the recorded template version with AI conflict resolution.
`/wellforge:orchestrate` drives the full agent pipeline on a goal.

**Rigor tiers** (cross-cutting, `rigor-tiers` skill): `spike`/`mvp`/`production` match
ceremony to stakes — `/wellforge:spike` is the main-loop fast lane (no agents, advisory
gates); `--mode` tunes orchestrate/implement; `/wellforge:promote` graduates a feature or
the project up a tier, paying the deferred rigor. Defer-don't-lower: a lower tier is tracked
debt, raised only via promote (production only on an eval PASS), and a security floor blocks
in every tier. Tier is a copier answer (manifest) + spec/brief frontmatter + command flag.

## Repository layout

```
wellforge/
├── CLAUDE.md
├── docs/PLAN.md              # roadmap + per-phase status — read before working here
├── copier.yml                # SINGLE template entry point: preset question + templated
│                             # _subdirectory (required for copier update; repo-wide vX.Y.Z tags)
├── .github/workflows/        # reusable gates: quality-node.yml, quality-jvm.yml
│                             # (must live here — GitHub only resolves workflow_call from this path)
├── wellforge-plugin/         # Claude Code plugin, v2.9.x (local marketplace install)
│   ├── .claude-plugin/plugin.json
│   ├── commands/             # spec, plan, design, tasks, implement, orchestrate, eval, done,
│   │                         # status, new, upgrade, adopt, extract-template, spike, promote,
│   │                         # release (→ /wellforge:*)
│   ├── agents/               # product-owner, architect, designer, frontend-dev, backend-dev,
│   │                         # devops, quality-engineer, evaluator + specialists (owasp-reviewer, adr-writer)
│   ├── skills/               # spec-driven, rigor-tiers, observability, visual-companion,
│   │                         # template-extraction, connections + stack skills (react-ts-vite,
│   │                         # kotlin-springboot, hono-ts-backend, mise, springboot-scaffold,
│   │                         # pulumi-gcp-ts)
│   ├── config/               # model-routing.yml + model-tiers.yml (tool-neutral tiers)
│   ├── hooks/                # lifecycle hooks (incl. SubagentStop run-trace telemetry)
│   └── .mcp.json             # sequential-thinking, playwright, github, context-hub
├── templates/
│   ├── _shared/CONTRACT.md   # binding contract: questions, required files, versioning
│   ├── spring-kotlin-react/template/   # SB4 Kotlin + jOOQ + Liquibase / React TS Vite
│   ├── hono-react/template/            # Hono + Drizzle / React TS Vite
│   └── pulumi-gcp-ts/template/         # Pulumi IaC (TypeScript) on GCP — stacks, ComponentResources,
│                                       # CrossGuard policy, mock tests (reuses quality-node gate)
├── gates/                    # configs (semgrep), scripts (check-jacoco.py), policy README
└── scripts/fleet-status.sh   # org-wide table: project template versions vs latest tag
```

## Current state (2026-06)

- **All 6 pillars built** (Phases 0–6 ☑ — per-phase detail and honest deviations in
  `docs/PLAN.md`). Lifecycle E2E-tested: scaffold v0.1.0 → template change → `copier
  update` → zero conflicts.
- **Rigor tiers shipped** (all 3 phases ☑ — `docs/PLAN-rigor-tiers.md`): spike/mvp/production
  across plugin, gates and templates.
- Latest tags: `v0.7.0` (template series, PEP440 — what copier resolves), `gates-v7` (gate
  workflow pin series — separate, invisible to copier); plugin `2.22.0`. A self-CI workflow
  (`.github/workflows/ci.yml`) lints the repo's own commits + smoke-tests all three presets.
- **Outstanding** (Phase 7 pilot): full `mise run install/build/test` on a generated
  project, CI-green on GitHub (repo has no remote yet), threshold calibration, v1.0.0 cut.

## Conventions

- Plugin agents/commands/skills are Markdown with YAML frontmatter (Claude Code plugin format).
- Generation goes through the ROOT `copier.yml` (`--data preset=<name>`), never
  `templates/<preset>/` directly; scaffolded projects carry `.forge/manifest.json`
  (template, version, answers) — the upgrade contract, never edit either by hand.
- No hidden copy-time-injected answers (e.g. dates) in templates — copier doesn't persist
  `when: false` answers and every future `copier update` would conflict (learned the hard way).
- Template releases: repo-wide `vX.Y.Z` tags, presets in lockstep; semver = patch cosmetic /
  minor additive / major needs `_migrations`. Bump the `template_version` default in the
  release commit.
- Quality thresholds live in the gate workflows' `env` blocks — changed only via PR to
  `gates/`/`.github/workflows/`; templates call them pinned to `gates-v*`.
- Parallel implementation is worktree-isolated: `implement`/`orchestrate` dispatch batches of
  ≥2 dependency-independent dev agents under `isolation: "worktree"` (each commits on its own
  branch, does not touch `tasks.md`), then merge back and reconcile checkboxes centrally — a
  merge conflict means a wrong DAG edge (a "collision"), surfaced like drift. Set
  `worktree.baseRef: "head"`. Solo/sequential batches stay in the main tree.
- All text/docs in English; this is internal WellForge tooling.
