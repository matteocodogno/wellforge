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
| `plugin/` (welld-dev) | Claude Code plugin: skills, agents, commands, hooks, MCP | Pillars 1, 2, 3 + local gate enforcement |
| `templates/` | [Copier](https://copier.readthedocs.io) templates per stack (chosen for first-class `copier update` re-templating) | Pillars 4, 6 |
| `gates/` | Reusable GitHub Actions workflows + shared lint/coverage/security configs, referenced (not copied) by scaffolds | Pillar 5 |

The plugin's `/forge:new` command is the front door: interview → stack recommendation →
`copier copy` → MCP/CLI connection setup → first spec. `/forge:upgrade` re-runs
`copier update` against the recorded template version.

## Repository layout (target)

```
wellforge/
├── CLAUDE.md
├── docs/PLAN.md              # roadmap — read this before working on the project
├── welld-dev-plugin/         # Claude Code plugin (exists, v1.1 — being extended)
│   ├── .claude-plugin/plugin.json
│   ├── agents/               # PO, architect, designer, fe-dev, be-dev, devops, qe + existing
│   ├── commands/             # /forge:new, /forge:upgrade, /spec, /plan, /tasks, /orchestrate
│   ├── skills/               # stack skills (react-ts-vite, kotlin-springboot-welld, hono-ts-backend)
│   ├── hooks/                # lifecycle hooks (exists)
│   └── .mcp.json             # sequential-thinking, playwright, github
├── templates/                # copier templates, one per stack preset, semver-tagged
│   ├── spring-kotlin-react/
│   ├── hono-react/
│   └── _shared/
└── gates/                    # reusable CI workflows + shared tool configs
    ├── workflows/            # GH Actions: coverage, lint, typecheck, semgrep, osv-scanner
    └── configs/              # eslint-config-welld, ktlint rules, coverage thresholds
```

## Current state (2026-06)

- `welld-dev-plugin/` exists: 3 stack skills, 2 agents (owasp-reviewer, adr-writer), 6 hooks,
  3 MCP servers, 1 shell-script scaffolder (`skills/springboot-scaffold`). Installed via local
  marketplace.
- Everything else in the layout above is **planned, not built** — see `docs/PLAN.md` for
  phases and status.

## Conventions

- Plugin agents/commands/skills are Markdown with YAML frontmatter (Claude Code plugin format).
- Templates are semver-tagged; scaffolded projects carry a `.forge/manifest.json`
  (template name, version, copier answers) — this is the upgrade contract, never edit it by hand.
- Quality thresholds live in `gates/` and are referenced by templates, not duplicated into them.
- All text/docs in English; this is internal welld tooling.
