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
(everything on the machine — see [Updating](#updating)).

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

> **Contributing rather than just installing?** [CONTRIBUTING.md](../CONTRIBUTING.md) is the
> guide for people working *on* WellForge: run `mise trust && mise install && mise run
> setup` and `./scripts/setup-git-policy.sh` once per clone, and `mise run check` before
> every push. [SECURITY.md](../SECURITY.md) carries the threat
> model for the plugin you are about to enable on your own machine — worth reading once
> before step 3.

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
claude plugin marketplace add matteocodogno/wellforge

# 2. Install
claude plugin install wellforge@wellforge --scope user
```

One-shot alternative (testing only): `claude --plugin-dir ~/.ai/wellforge/wellforge-plugin`

## 4. Verify

Inside a Claude Code session:

| Check | Expect |
|---|---|
| `/plugin` | `wellforge` listed under Installed (v2.0+) |
| `/mcp` | `playwright`, `context-hub` connected |
| `/hooks` | 7 events listed (SessionStart, PreToolUse ×2, PostToolUse, Notification, Stop, SubagentStop, PreCompact) |
| type `/wellforge:` | completions for all 23 commands |
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
  It writes `~/.config/wellforge/telegram.env` (mode 600, directory 700) and **touches no
  shell rc file**. The notify hook reads that file itself, so the bot token never enters
  your shell environment — and therefore never reaches the processes Claude Code starts,
  where an `env` in a transcript would leak it. Nothing to `source`, no new terminal
  needed. If an older version added a `source` line to your rc, the wizard offers to
  remove it.

  The wizard picks the chat from **private** messages only, and asks if more than one
  person has messaged the bot — a bot that also sits in a group used to save the group,
  and then every permission prompt went there.
- **Settings to merge** into `~/.claude/settings.json` — see
  `wellforge-plugin/settings-snippet.jsonc` (companion plugins, attribution).
- **Domain glossary** — create `.claude/context/glossary.md` in any project; the
  session-start hook injects it automatically. `/wellforge:grill-me --docs` builds it for
  you during an interview (`domain-modeling` skill).

## 6. Other AI tools

The plugin above is for Claude Code. The same workflow, agents and skills reach other tools
generated from it — never edited by hand:

- **Codex — native plugin.** Install once, then set up each project:
  ```bash
  codex plugin marketplace add matteocodogno/wellforge --ref plugin-vX.Y.Z
  ```
  Install WellForge from that marketplace, then in each project run `$wf-setup` (the
  plugin's onboarding skill): it copies the agent team, the scripts the `$wf-*` commands
  run and an `AGENTS.md` block into the project — commit them. Trust the hooks via
  `/hooks`; if `/hooks` does not list them, run `$wf-setup --hooks`. Re-run `$wf-setup`
  after every plugin update (the session start says when a project is behind). Commands
  are `$wf-spec`, `$wf-status`, … — see [`adapters/codex/`](../adapters/codex/README.md).
- **Codex without the plugin, OpenCode, GitHub Copilot (VS Code)** — generate the files
  into the project from a checkout:
  ```bash
  uv run --with pyyaml python adapters/<codex|opencode|copilot>/generate.py --out <project>
  ```
  Each adapter's README ([Codex](../adapters/codex/README.md),
  [OpenCode](../adapters/opencode/README.md), [Copilot](../adapters/copilot/README.md))
  says what is covered and what is not.

## Updating

Two levels, two commands, in this order:

| Level | Command | What it touches | What it never touches |
|---|---|---|---|
| **Machine** — once per machine | `wellforge update`, then `/reload-plugins` (or a new session) | the checkout (`~/.ai/wellforge`: plugin source, templates, gates, migration notes), outdated pinned dev tools (`brew upgrade`), the **loaded** Claude Code plugin (`claude plugin update`, only when the cache is stale), and last the brew-installed `wellforge` CLI itself | any project |
| **Project** — in each project, inside the harness | `/wellforge:upgrade` (`--dry-run` to see the plan first) | re-renders the template (`copier update`), offers the `gates_ref` bump, applies `docs/TEMPLATE-MIGRATIONS.md` **and** `docs/PLUGIN-MIGRATIONS.md` entries (automatic ones applied, human ones offered), resolves conflicts, re-runs the gates, stamps `.forge/manifest.json` — one revertable commit | your machine |

**Order matters.** `/wellforge:upgrade` works with the plugin that is loaded and the migration
notes in the checkout — run it before `wellforge update` and it sees neither the new plugin
nor its migrations. And it is not only for template releases: a **plugin-only** release can
carry project-side migrations too (e.g. 2.62.0's date-based ids), so run it after any
`wellforge update` that moved the plugin. In an adopted project there is no template to
re-render; `/wellforge:upgrade` still applies the plugin migrations.

`wellforge doctor` fetches and tells you what is behind: the **checkout** (`! checkout N
behind…`), the **plugin cache** (`! plugin cache loaded vX but source is vY`), and the
**CLI** you are running versus the checkout's copy (`! cli 1.0.0 is behind the checkout's
1.1.0`). Without brew (CLI run from the checkout) the CLI updates with the checkout pull.

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
# CLI binary by hand — `wellforge update` already does this (the formula is versioned):
brew update
brew upgrade wellforge
```

> Installed `--HEAD` before the formula became versioned? Switch once with:
> `brew uninstall --force wellforge && brew install matteocodogno/wellforge/wellforge`
> (`--force` matters: it removes **all** kegs — a leftover HEAD keg stays linked
> otherwise, shadows every upgrade, and `brew upgrade` reports "already installed".)

Plugin changes reach your **sessions** on the next Claude Code session (same marketplace
path); they reach a **project** only through `/wellforge:upgrade`, which applies the plugin
migrations. Template and gate releases are consumed by projects explicitly too —
`/wellforge:upgrade` re-templates and offers the `gates-v*` bump — never implicitly.

## Uninstall

```bash
claude plugin uninstall wellforge --scope user
claude plugin marketplace remove wellforge
```

---

Next: [Quick start](QUICKSTART.md) — scaffold your first project.
