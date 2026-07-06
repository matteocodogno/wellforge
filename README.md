```
██╗    ██╗███████╗██╗     ██╗     ███████╗ ██████╗ ██████╗  ██████╗ ███████╗
██║    ██║██╔════╝██║     ██║     ██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝
██║ █╗ ██║█████╗  ██║     ██║     █████╗  ██║   ██║██████╔╝██║  ███╗█████╗
██║███╗██║██╔══╝  ██║     ██║     ██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝
╚███╔███╔╝███████╗███████╗███████╗██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗
 ╚══╝╚══╝ ╚══════╝╚══════╝╚══════╝╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝

          idea  →  a building, CI-gated, AI-ready repo  →  in minutes, not hours

       ___________
      |  ◕  ◡  ◕  |    Hi, I'm Forgey — your AI blacksmith.
      |___________|    I forge the boring part (scaffold, gates, CI,
         |     |       the spec workflow, releases) so you get straight
       __|     |__     to building what actually matters.
      |___________|
```

![template](https://img.shields.io/badge/template-v0.5.1-1f6feb)
![plugin](https://img.shields.io/badge/plugin-v2.21.0-8957e5)
![gates](https://img.shields.io/badge/gates-gates--v5-2da44e)
![works with](https://img.shields.io/badge/works%20with-Claude%20Code%20%2B%20OpenCode-111)
![license](https://img.shields.io/badge/license-MIT-green)

> **WellForge turns a week of AI-infra setup into one command.** An open platform for
> **reproducible, standard, fast** AI-assisted project setup — for any team.

## The problem

Every new project starts the same way: wire up the AI agents, the spec workflow, the
scaffold, the quality gates, the CI, the tool connections. Hours of it, every time. Everyone
does it a little differently — and it quietly rots the moment your standards move on.

## What Forgey forges for you

One interview, and you get a **building, CI-gated, spec-driven, AI-ready repository** — with a
team of AI agents already wired in, quality gates that can't be silently weakened, and a
lifecycle that keeps your whole fleet upgradeable.

- 🏗️ **Scaffold** from a versioned template — pick a stack, get a working monorepo.
- 🤝 **A spec-driven agent team** — idea → spec → plan → design → tasks → code → QE → LM-judge eval.
- ✅ **Quality gates as law** — coverage, lint, types, SAST, secret-scan; enforced in CI, not by vibes.
- 🚀 **Rigor tiers** — `spike` a PoC in minutes, or run full `production` rigor. Your call, per feature.
- 📦 **Release & lifecycle** — Conventional-Commit releases (release-it), `copier`-based upgrades, fleet view.
- 🧩 **Brownfield-friendly** — adopt an existing repo incrementally, one layer at a time.

## Is it for you?

WellForge is a plugin on top of an AI coding CLI, and it's opinionated about stack + platform.
It fits best if you have:

- **Claude Code** (or OpenCode) + model access — it's a plugin, not a standalone tool
- **macOS or Linux** with Homebrew (Windows isn't supported yet)
- **GitHub** — the quality gates are GitHub Actions; connections & releases assume `gh`
- **Greenfield**: one of two stacks — **Spring-Kotlin + React** or **Hono + React**
- **Brownfield**: any **Node (pnpm)** or **JVM (Maven)** repo on GitHub, via `/wellforge:adopt`

Outside that (other stacks, other CIs, Windows) the fit drops off — broadening is on
[the roadmap](docs/PLAN.md).

## See it work

```bash
brew tap matteocodogno/wellforge https://github.com/matteocodogno/wellforge
brew install matteocodogno/wellforge/wellforge
wellforge setup            # toolchain + repo + plugin, verified
```

Then, in Claude Code (or OpenCode):

```
/wellforge:new a portal where external contractors manage their work orders
```

Forgey interviews you, recommends a stack, generates the repo, verifies it builds, and walks
you through connecting GitHub / CI / MCP. ~30 minutes to a repo you'd be happy to inherit.
In a hurry? **`/wellforge:spike <idea>`** gets a working prototype in minutes.

## The commands

```
/wellforge:new          idea → interview → stack pick → scaffold → verified build → connections
/wellforge:spike        fast lane — main-loop build from a brief, advisory gates (PoC in minutes)
/wellforge:spec|plan|design|tasks   the spec-driven feature workflow (2 human gates)
/wellforge:orchestrate  the full agent team on a goal   ·   --mode spike|mvp|production
/wellforge:implement    build a feature's tasks — parallel dev agents, QE-verified
/wellforge:eval         LM-judge score against the central rubric (the gate into "done")
/wellforge:done         close a feature — verifies the tier's done gate (tasks + QE + eval)
/wellforge:promote      graduate a feature/project up a rigor tier — pays the deferred debt
/wellforge:release      version + CHANGELOG from Conventional Commits, tag, GitHub release
/wellforge:adopt        onboard an existing (brownfield) repo — incrementally
/wellforge:upgrade      re-template a project to a newer release, AI-resolved conflicts
/wellforge:status       where every feature stands + the exact next command to run
```

## Rigor tiers — as fast or as careful as the work deserves

Match ceremony to stakes. A lower tier is *tracked debt*, raised only via `/wellforge:promote`
— never lowered silently. A **security floor** (secret scan, no hardcoded creds, critical-CVE
audit) blocks in **every** tier: fast never means leaky.

| Tier | Pipeline | Gates | For |
|---|---|---|---|
| `spike` | main loop, no agents, no approval | build + secret-scan floor (advisory) | PoC / feasibility / experiments |
| `mvp` | collapsed team, 1 gate | SAST blocks, coverage advisory | first release to validate with users |
| `production` | full agent team, 2 gates | full 80% + SAST + eval | long-lived products |

## Documentation

| Doc | For |
|---|---|
| **[Features](docs/FEATURES.md)** | what WellForge does — the 6 pillars in detail |
| **[Installation](docs/INSTALLATION.md)** | machine setup — brew fast path or manual |
| **[Quick start](docs/QUICKSTART.md)** | idea → running project in ~30 minutes |
| [PLAN.md](docs/PLAN.md) · [rigor tiers](docs/PLAN-rigor-tiers.md) | build roadmap, per-phase status, honest deviations |

## Under the hood

Three layers, because no single mechanism covers everything:

| Layer | Vehicle | Covers |
|---|---|---|
| [`wellforge-plugin/`](wellforge-plugin/) | Claude Code / OpenCode plugin — commands, agents, skills, hooks, MCP | spec workflow, agent team, orchestration, local enforcement |
| [`copier.yml`](copier.yml) + [`templates/`](templates/) | [Copier](https://copier.readthedocs.io) monorepo template, semver-tagged ([contract](templates/_shared/CONTRACT.md)) | scaffolding, releases, lifecycle upgrades |
| [`.github/workflows/`](.github/workflows/) + [`gates/`](gates/) | reusable GitHub Actions + central thresholds | quality gates (CI enforcement) |

Fleet view across all your generated projects: [`scripts/fleet-status.sh`](scripts/fleet-status.sh).

## Status

All 6 pillars built and E2E-tested, plus rigor tiers and release management. Works with
**Claude Code and OpenCode**. Latest: template `v0.5.1`, gates `gates-v5`, plugin `2.21.0`.
Before `v1.0.0`: the Phase 7 pilot on a real project — see [PLAN.md](docs/PLAN.md).

Built for any team. **[MIT licensed](LICENSE).** Contributions: PRs to `templates/` and gate
thresholds — that review is the single discretion point of the quality system.

```
       ___________
      |  ◕  ◡  ◕  |    "now go build something. I've got the setup."
      |___________|                                          — Forgey
         |     |
       __|     |__
      |___________|
```
