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
repo, registers the plugin marketplace, and installs the welld-dev plugin — then prints
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

## 3. Install the welld-dev plugin

The wellforge repo root is itself a plugin marketplace (`.claude-plugin/marketplace.json`,
plugin source declared relative — no paths to edit):

```bash
# 1. Register the marketplace (point it at the repo root)
claude plugin marketplace add ~/.ai/wellforge

# 2. Install
claude plugin install welld-dev@welld --scope user
```

One-shot alternative (testing only): `claude --plugin-dir ~/.ai/wellforge/welld-dev-plugin`

## 4. Verify

Inside a Claude Code session:

| Check | Expect |
|---|---|
| `/plugin` | `welld-dev` listed under Installed (v1.6+) |
| `/mcp` | `sequential-thinking`, `playwright`, `github` connected (github triggers OAuth on first use) |
| `/hooks` | 6 hooks listed |
| type `/welld-dev:` | completions: `spec`, `plan`, `tasks`, `orchestrate`, `new`, `upgrade` |

## 5. Optional

- **Telegram notifications** (DM when Claude needs permission / is waiting) — guided
  wizard, also offered during `wellforge setup`:
  ```bash
  wellforge telegram
  ```
- **Settings to merge** into `~/.claude/settings.json` — see
  `welld-dev-plugin/settings-snippet.jsonc` (companion plugins, attribution).
- **Domain glossary** — create `.claude/context/glossary.md` in any project; the
  session-start hook injects it automatically.

## Updating

There are **two update channels** — they cover different things:

| What | Updates | Command |
|---|---|---|
| The checkout (`~/.ai/wellforge`: plugin, templates, gates) | `wellforge update` | or: `cd ~/.ai/wellforge && git pull` |
| The `wellforge` CLI itself (brew-installed binary) | see below | |

```bash
# CLI binary (the formula is versioned — new releases appear via brew update):
brew update
brew upgrade wellforge
```

> Installed `--HEAD` before the formula became versioned? Switch once with:
> `brew uninstall wellforge && brew install matteocodogno/wellforge/wellforge`

Plugin changes apply on the next Claude Code session (same marketplace path). Template
and gate releases are consumed by projects explicitly — `/welld-dev:upgrade` for
templates, a `gates-v*` ref bump in CI for gates — never implicitly.

## Uninstall

```bash
claude plugin uninstall welld-dev --scope user
claude plugin marketplace remove welld
```

---

Next: [Quick start](QUICKSTART.md) — scaffold your first project.
