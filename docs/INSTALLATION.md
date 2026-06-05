# WellForge — Installation

One-time setup per developer machine. ~10 minutes.

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
git clone <wellforge-repo-url> ~/.ai/wellforge     # location is your choice
```

> Until the repo is hosted, a shared checkout path works — but `/welld-dev:upgrade`
> resolves the template source recorded at scaffold time, so prefer the git URL as soon
> as one exists (it makes upgrades work for every team member).

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

- **Telegram notifications** (used by the notify hook) — add to `~/.zshrc`, never commit:
  ```bash
  export TELEGRAM_BOT_TOKEN="..."
  export TELEGRAM_CHAT_ID="..."
  ```
- **Settings to merge** into `~/.claude/settings.json` — see
  `welld-dev-plugin/settings-snippet.jsonc` (companion plugins, attribution).
- **Domain glossary** — create `.claude/context/glossary.md` in any project; the
  session-start hook injects it automatically.

## Updating

```bash
cd ~/.ai/wellforge && git pull
```

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
