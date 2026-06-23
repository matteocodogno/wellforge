# WellForge

Internal platform for **reproducible, standard, fast AI-assisted project setup** at welld.
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

## Repository layout

```
wellforge/
├── CLAUDE.md
├── docs/PLAN.md              # roadmap + per-phase status — read before working here
├── copier.yml                # SINGLE template entry point: preset question + templated
│                             # _subdirectory (required for copier update; repo-wide vX.Y.Z tags)
├── .github/workflows/        # reusable gates: quality-node.yml, quality-jvm.yml
│                             # (must live here — GitHub only resolves workflow_call from this path)
├── wellforge-plugin/         # Claude Code plugin, v1.6.x (local marketplace install)
│   ├── .claude-plugin/plugin.json
│   ├── commands/             # spec, plan, tasks, orchestrate, new, upgrade (→ /wellforge:*)
│   ├── agents/               # product-owner, architect, designer, frontend-dev, backend-dev,
│   │                         # devops, quality-engineer + specialists (owasp-reviewer, adr-writer)
│   ├── skills/               # spec-driven, connections + stack skills (react-ts-vite,
│   │                         # kotlin-springboot-welld, hono-ts-backend, mise, springboot-scaffold)
│   ├── hooks/                # 6 lifecycle hooks
│   └── .mcp.json             # sequential-thinking, playwright, github
├── templates/
│   ├── _shared/CONTRACT.md   # binding contract: questions, required files, versioning
│   ├── spring-kotlin-react/template/   # SB4 Kotlin + jOOQ + Liquibase / React TS Vite
│   └── hono-react/template/            # Hono + Drizzle / React TS Vite
├── gates/                    # configs (semgrep), scripts (check-jacoco.py), policy README
└── scripts/fleet-status.sh   # org-wide table: project template versions vs latest tag
```

## Current state (2026-06)

- **All 6 pillars built** (Phases 0–6 ☑ — per-phase detail and honest deviations in
  `docs/PLAN.md`). Lifecycle E2E-tested: scaffold v0.1.0 → template change → `copier
  update` → zero conflicts.
- Tags: `v0.1.0` (template release series, PEP440 — what copier resolves),
  `gates-v0` (gate workflow pin series — separate, invisible to copier).
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
- All text/docs in English; this is internal welld tooling.
