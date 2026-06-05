# WellForge

welld's internal platform for **reproducible, standard, fast AI-assisted project setup**:
product idea → building, CI-gated, spec-driven, AI-ready repository in minutes — with a
fleet that stays upgradeable as standards evolve.

## Documentation

| Doc | For |
|---|---|
| **[Features](docs/FEATURES.md)** | what WellForge does — the 6 pillars in detail |
| **[Installation](docs/INSTALLATION.md)** | one-time machine setup (~10 min) |
| **[Quick start](docs/QUICKSTART.md)** | scaffold a greenfield project (~30 min) |
| [PLAN.md](docs/PLAN.md) | build roadmap, per-phase status, honest deviations |

## At a glance

```
/welld-dev:new          idea → interview → stack pick → scaffold → verified build → connections
/welld-dev:spec|plan|tasks   standardized spec-driven feature workflow (2 human gates)
/welld-dev:orchestrate  full agent team on a goal (PO → Architect → Devs ∥ → QE verdict)
/welld-dev:upgrade      re-template a project to a newer release, AI-resolved conflicts
```

| Piece | Where |
|---|---|
| Claude Code plugin (commands, 9 agents, skills, hooks, MCP) | [`welld-dev-plugin/`](welld-dev-plugin/) |
| Project templates — Copier monorepo, root [`copier.yml`](copier.yml) | [`templates/`](templates/) ([contract](templates/_shared/CONTRACT.md)) |
| Quality gates — reusable workflows + central thresholds | [`.github/workflows/`](.github/workflows/) + [`gates/`](gates/) |
| Fleet status script | [`scripts/fleet-status.sh`](scripts/fleet-status.sh) |

**Status**: all 6 pillars built and E2E-tested (template release `v0.1.0`, gates
`gates-v0`). Outstanding before `v1.0.0`: the Phase 7 pilot on a real project — see
[PLAN.md](docs/PLAN.md).

Internal welld tooling. Contributions: PRs only for `templates/` and gate thresholds
(that review is the single discretion point of the quality system).
