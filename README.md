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

<!-- LIVE badges, resolved by shields.io at render time — the same sources site/index.html
     uses. The hard-coded versions that were here said template v0.9.0 and plugin v2.32.0,
     sixteen plugin releases behind, because a badge is exactly the kind of number nobody
     remembers to bump. A badge that can go stale should not exist. -->
[![template](https://img.shields.io/github/v/release/matteocodogno/wellforge?label=template&color=1f6feb)](https://github.com/matteocodogno/wellforge/releases)
[![plugin](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fmatteocodogno%2Fwellforge%2Fmain%2Fwellforge-plugin%2F.claude-plugin%2Fplugin.json&query=%24.version&prefix=v&label=plugin&color=8957e5)](wellforge-plugin/)
[![gates](https://img.shields.io/github/v/tag/matteocodogno/wellforge?filter=gates-v*&label=gates&color=2da44e)](docs/VERSIONING.md)
[![cli](https://img.shields.io/github/v/tag/matteocodogno/wellforge?filter=cli-v*&label=cli&color=d29922)](docs/RELEASING-CLI.md)
![works with](https://img.shields.io/badge/works%20with-Claude%20Code%20%2B%20OpenCode%20%2B%20Copilot-111)
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

- **Claude Code**, **OpenCode**, or **GitHub Copilot** (VS Code, via a generated adapter) + model access — it's a plugin/adapter, not a standalone tool
- **macOS or Linux** with Homebrew (Windows isn't supported yet)
- **GitHub** — the quality gates are GitHub Actions; connections & releases assume `gh`
- **Greenfield**: one of three presets — **Spring-Kotlin + React**, **Hono + React**, or
  **Pulumi GCP (TypeScript)** for infrastructure
- **Brownfield**: any **Node (pnpm)** or **JVM (Maven)** repo on GitHub, via `/wellforge:adopt`

Outside that (other stacks, other CIs, Windows) the fit drops off — broadening is on
[the roadmap](docs/plans/PLAN.md).

## See it work

```bash
brew tap matteocodogno/wellforge https://github.com/matteocodogno/wellforge
brew install matteocodogno/wellforge/wellforge
wellforge setup            # toolchain + repo + plugin, verified
```

Keeping it current — two different things, on purpose:

```bash
brew upgrade wellforge     # the CLI itself  (its own `cli-vX.Y.Z` series)
wellforge update           # the checkout + the Claude Code plugin
wellforge version          # which CLI you are actually running
```

`wellforge doctor` reports when the CLI you are running is older than the checkout's copy —
they are two different files, and until the CLI got its own release series it was normal for
the installed one to be months behind with nothing saying so.

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
/wellforge:triage       spec-health digest — what's rotting (stale, drifted, never eval'd)
/wellforge:doctor       health check: tools, MCP, hooks, guards — and the command index
```

`--dry-run` on `upgrade`, `promote`, `adopt` and `release` shows the plan of record —
files, commands, what's irreversible, and what it honestly cannot predict — and changes
nothing. A feature that stops without shipping gets a real exit, not a hand-edit:
`/wellforge:done <feature> --archive "<reason>"`, or `--superseded-by <other>` when another
spec took the work over.

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
| **[Versioning](docs/VERSIONING.md)** | why there are two tag series (`vX.Y.Z` templates, `gates-vN` gates) and how each reaches a project |
| [PLAN.md](docs/plans/PLAN.md) · [rigor tiers](docs/plans/PLAN-rigor-tiers.md) | build roadmap, per-phase status, honest deviations |

## Under the hood

Three layers, because no single mechanism covers everything:

| Layer | Vehicle | Covers |
|---|---|---|
| [`wellforge-plugin/`](wellforge-plugin/) | Claude Code / OpenCode plugin — commands, agents, skills, hooks, MCP | spec workflow, agent team, orchestration, local enforcement |
| [`copier.yml`](copier.yml) + [`templates/`](templates/) | [Copier](https://copier.readthedocs.io) monorepo template, semver-tagged ([contract](templates/_shared/CONTRACT.md)) | scaffolding, releases, lifecycle upgrades |
| [`.github/workflows/`](.github/workflows/) + [`gates/`](gates/) | reusable GitHub Actions + central thresholds | quality gates (CI enforcement) |

Fleet view across all your generated projects: [`scripts/fleet-status.sh`](scripts/fleet-status.sh).

**Other AI tools:** the plugin is the source of truth; [`adapters/`](adapters/) *generates*
tool-native files from it — [OpenCode](adapters/opencode/) (`.opencode/`) and
[GitHub Copilot](adapters/copilot/) for VS Code (`.github/` prompts, chat modes, instructions
+ MCP, invoked as `/wf-*`). Copilot reaches the workflow + agents + skills + MCP; parallel
multi-agent orchestration and local hooks are Claude Code / OpenCode-only (Copilot leans on CI
gates + a generated `lefthook.yml`). See [multi-tool support](docs/plans/MULTI-TOOL-SUPPORT.md).

## Status

All 6 pillars built and E2E-tested, plus rigor tiers and release management. Works with
**Claude Code, OpenCode, and GitHub Copilot** (VS Code, via adapter). Latest: template
four independent series that move
independently, see [versioning](docs/VERSIONING.md).
Before `v1.0.0`: the Phase 7 pilot on a real project — see [PLAN.md](docs/plans/PLAN.md).

Built for any team. **[MIT licensed](LICENSE).**

**Contributing:** start with [CONTRIBUTING.md](CONTRIBUTING.md) — setup, where each kind of
change goes, which of the four tag series it bumps, and what a PR must show. PRs to
`templates/` and gate thresholds are especially welcome: that review is the single discretion
point of the quality system.

**Security:** [SECURITY.md](SECURITY.md) — how to report a vulnerability privately, and the
threat model for the plugin as installed on a developer's machine (what the hooks run, what
the MCP servers are, and what the plugin does and does not do about prompt injection).

```
       ___________
      |  ◕  ◡  ◕  |    "now go build something. I've got the setup."
      |___________|                                          — Forgey
         |     |
       __|     |__
      |___________|
```
