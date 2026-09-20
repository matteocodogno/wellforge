# WellForge — Installation

One-time setup per developer machine.

## Fast path (Homebrew)

```bash
brew tap matteocodogno/wellforge https://github.com/matteocodogno/wellforge
brew install matteocodogno/wellforge/wellforge
wellforge setup
```

`wellforge setup` asks for the install location (default `~/.ai/wellforge`, Enter
accepts, your choice is remembered), checks/installs the whole toolchain, clones the
repo, registers the plugin marketplace, and installs the wellforge plugin — then prints
a verification table. Day-2: `wellforge doctor` (health check), `wellforge update`
(repo + tools).

The manual path below does the same, step by step.

---

## 1. Prerequisites

| Tool | Why | Install (macOS) |
|---|---|---|
| [Claude Code](https://claude.com/claude-code) | the plugin runs in it | `npm i -g @anthropic-ai/claude-code` or desktop app |
| [mise](https://mise.jdx.dev) | toolchain manager — every generated project pins tools with it | `brew install mise` + shell activation |
| [uv](https://docs.astral.sh/uv/) | runs Copier without a Python setup (`uvx copier`) | `brew install uv` |
| `gh` CLI | repo creation, branch protection, secrets (connections layer) | `brew install gh` && `gh auth login` |
| Docker Desktop | local postgres via docker-compose, Testcontainers | docker.com |
| `jq` | manifest/JSON checks in scripts and hooks | `brew install jq` |

Verify:

```bash
claude --version && mise --version && uvx copier --version && gh auth status && docker info -f '{{.ServerVersion}}' && jq --version
```

## 2. Get the WellForge repo

```bash
git clone https://github.com/matteocodogno/wellforge.git ~/.ai/wellforge
```

(Location is your choice; `~/.ai/wellforge` is the default `wellforge setup` offers.
Private repo: `gh auth setup-git` first, or use the SSH URL.)

## 3. Install the wellforge plugin

The wellforge repo root is itself a plugin marketplace (`.claude-plugin/marketplace.json`,
plugin source declared relative — no paths to edit):

```bash
# 1. Register the marketplace (point it at the repo root)
claude plugin marketplace add ~/.ai/wellforge

# 2. Install
claude plugin install wellforge@wellforge --scope user
```

One-shot alternative (testing only): `claude --plugin-dir ~/.ai/wellforge/wellforge-plugin`

## 4. Verify

Inside a Claude Code session:

| Check | Expect |
|---|---|
| `/plugin` | `wellforge` listed under Installed (v2.0+) |
| `/mcp` | `sequential-thinking`, `playwright`, `github`, `context-hub` connected (github triggers OAuth on first use) |
| `/hooks` | 7 events listed (SessionStart, PreToolUse ×2, PostToolUse, Notification, Stop, SubagentStop, PreCompact) |
| type `/wellforge:` | completions for all 20 commands |
| **`/wellforge:doctor`** | **the real check** — one table of tools, MCP servers, hooks, drift guards and project shape, with a fix command for anything red. Add `--tests` to also run the plugin's own regression matrices. |

Prefer `doctor` to the manual checks above: it verifies the things that fail *silently*
(a missing `jq` makes every hook exit 0 while doing nothing; a hook whose script is missing
never blocks and never says so).

## 5. Optional

- **Telegram notifications** (DM when Claude needs permission / is waiting) — guided
  wizard, also offered during `wellforge setup`:
  ```bash
  wellforge telegram
  ```
- **Settings to merge** into `~/.claude/settings.json` — see
  `wellforge-plugin/settings-snippet.jsonc` (companion plugins, attribution).
- **Domain glossary** — create `.claude/context/glossary.md` in any project; the
  session-start hook injects it automatically.

## Updating

There are **two update channels** — they cover different things:

| What | Updates | Command |
|---|---|---|
| The checkout (`~/.ai/wellforge`: plugin, templates, gates) — where commands/agents/skills land | `wellforge update` | or: `cd ~/.ai/wellforge && git pull` |
| The `wellforge` CLI itself (brew-installed script) — its own `cli-vX.Y.Z` series | `brew upgrade wellforge` | `wellforge version` says which one you are running |

`wellforge doctor` fetches and tells you if the **checkout** is behind (`! checkout N
behind…`) — that's the channel most updates arrive on — and, since the CLI got its own
release series, whether the **CLI** you are running is behind the checkout's copy
(`! cli 1.0.0 is behind the checkout's 1.1.0`). They are two different files.

> The CLI was described here as a "small, stable launcher that changes rarely". That was
> not true, it was just stuck: the Homebrew formula pinned the **template** tag, so a CLI
> fix could only ship with a template release. `scripts/wellforge` drifted 179 insertions
> past the last one with nothing to ride on. It now has its own `cli-vX.Y.Z` series
> ([versioning](VERSIONING.md)), so `brew upgrade wellforge` is a real channel — and
> "already installed" now means what it says.

> **The plugin runs from a version-keyed cache, not the checkout.** Pulling the source
> (`git pull` / `wellforge update`'s first step) and `/reload-plugins` do **not** refresh
> that cache. `wellforge update` refreshes it **only when the cached version differs from
> the source**, with `claude plugin update` — it no longer uninstalls anything, so a failed
> refresh leaves the working plugin in place instead of leaving you with none. `wellforge
> doctor` flags a stale cache (`! plugin cache loaded vX but source is vY`). After
> `wellforge update`, run `/reload-plugins`. Manual refresh:
> `claude plugin update wellforge@wellforge`.
>
> Note that `claude plugin install` on an already-installed plugin is idempotent and does
> **not** pick up a newer source version — it says so and points at `update`. That is why
> `uninstall && install` used to be the only refresh anyone reached for, and why it was the
> wrong one.

```bash
# CLI binary (the formula is versioned — new releases appear via brew update):
brew update
brew upgrade wellforge
```

> Installed `--HEAD` before the formula became versioned? Switch once with:
> `brew uninstall --force wellforge && brew install matteocodogno/wellforge/wellforge`
> (`--force` matters: it removes **all** kegs — a leftover HEAD keg stays linked
> otherwise, shadows every upgrade, and `brew upgrade` reports "already installed".)

Plugin changes apply on the next Claude Code session (same marketplace path). Template
and gate releases are consumed by projects explicitly — `/wellforge:upgrade` for
templates, a `gates-v*` ref bump in CI for gates — never implicitly.

## Uninstall

```bash
claude plugin uninstall wellforge --scope user
claude plugin marketplace remove wellforge
```

---

Next: [Quick start](QUICKSTART.md) — scaffold your first project.
