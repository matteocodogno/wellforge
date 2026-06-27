# WellForge

An open platform for **reproducible, standard, fast AI-assisted project setup**:
product idea → building, CI-gated, spec-driven, AI-ready repository in minutes — with a
fleet that stays upgradeable as standards evolve.

## Documentation

```bash
brew tap matteocodogno/wellforge https://github.com/matteocodogno/wellforge
brew install matteocodogno/wellforge/wellforge
wellforge setup      # toolchain + repo + plugin, verified
```

| Doc | For |
|---|---|
| **[Features](docs/FEATURES.md)** | what WellForge does — the 6 pillars in detail |
| **[Installation](docs/INSTALLATION.md)** | machine setup — brew fast path or manual |
| **[Quick start](docs/QUICKSTART.md)** | scaffold a greenfield project (~30 min) |
| [PLAN.md](docs/PLAN.md) | build roadmap, per-phase status, honest deviations |

## At a glance

```
/wellforge:new          idea → interview → stack pick → scaffold → verified build → connections
/wellforge:spike        fast lane — main-loop build from a brief, advisory gates (PoC/feasibility)
/wellforge:spec|plan|tasks   standardized spec-driven feature workflow (2 human gates)
/wellforge:orchestrate  full agent team on a goal (PO → Architect → Devs ∥ → QE) · --mode spike|mvp|production
/wellforge:promote      graduate a feature/project up a rigor tier — pays the deferred debt
/wellforge:upgrade      re-template a project to a newer release, AI-resolved conflicts
```

**Rigor tiers** match ceremony to stakes: `spike` (minutes, no agents, advisory gates) →
`mvp` (collapsed pipeline) → `production` (full rigor). A lower tier is tracked debt, raised
only via `/wellforge:promote` — never lowered silently. A security floor blocks in every tier.

| Piece | Where |
|---|---|
| Claude Code plugin (commands, 9 agents, skills, hooks, MCP) | [`wellforge-plugin/`](wellforge-plugin/) |
| Project templates — Copier monorepo, root [`copier.yml`](copier.yml) | [`templates/`](templates/) ([contract](templates/_shared/CONTRACT.md)) |
| Quality gates — reusable workflows + central thresholds | [`.github/workflows/`](.github/workflows/) + [`gates/`](gates/) |
| Fleet status script | [`scripts/fleet-status.sh`](scripts/fleet-status.sh) |

**Status**: all 6 pillars built and E2E-tested, plus rigor tiers (spike/mvp/production).
Latest: template `v0.4.0`, gates `gates-v5`, plugin `2.9.0`. Outstanding before `v1.0.0`:
the Phase 7 pilot on a real project — see [PLAN.md](docs/PLAN.md) ·
[rigor tiers plan](docs/PLAN-rigor-tiers.md).

Internal WellForge tooling. Contributions: PRs only for `templates/` and gate thresholds
(that review is the single discretion point of the quality system).
