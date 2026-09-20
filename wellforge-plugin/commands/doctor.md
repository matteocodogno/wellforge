---
description: Health check — tools, MCP servers, hooks, guards and self-tests; also the index of what WellForge can do here
argument-hint: [--tests] [--quiet] — --tests also runs the plugin's own regression matrices (slower)
---

Check that WellForge can actually do its job in **this** project, and say precisely what is
broken and how to fix it. Read-only: this command diagnoses, it never installs, writes or
configures. Every check reports **OK / WARN / FAIL** with the command that fixes a FAIL.

Arguments: $ARGUMENTS

## Why this exists

Most WellForge failures are silent — a missing `uv` turns `/wellforge:new` into a confusing
copier error, an unconnected MCP server makes the designer quietly skip its browser audit, a
hook that is not loaded stops blocking without ever saying so. A failure that announces
itself does not need a doctor; these do.

## Step 1 — Locate the plugin

Several checks need the installed plugin's own files. Resolve its root once:

```bash
# CLAUDE_PLUGIN_ROOT is substituted for HOOKS only — it is NOT exported to Bash.
python3 -c "import json,os;p=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))['plugins'];print(next(i['installPath'] for k,v in p.items() if k.startswith('wellforge@') for i in v))"
```

If that fails, the plugin is not installed at user scope — say so and skip the checks that
need it (they are marked ⟨plugin⟩ below) rather than reporting them as failures.

## Step 2 — Checks

Run these and build one table. Do not stop at the first failure; a health report is only
useful complete.

**Toolchain** — `command -v` each, and report the version where it is cheap:

| Tool | Needed for | On FAIL |
|---|---|---|
| `git` | everything | — |
| `jq` | every hook (they exit 0 without it, silently doing nothing) | `brew install jq` |
| `uv` / `uvx` | `/wellforge:new`, `/wellforge:upgrade` (copier) | `brew install uv` or `mise use -g uv` |
| `mise` | generated projects' tasks | `brew install mise` |
| `gh` | connections, releases, the `gh issue` heartbeat path | `brew install gh && gh auth login` |
| `python3` | the gate scripts and run-report | — |
| `node`, `pnpm` | Node/TS presets | via mise |
| `java`, `mvn` | JVM preset | via mise |

`gh` additionally: `gh auth status` — authenticated or not.

**MCP servers** ⟨plugin⟩ — read `.mcp.json` from the plugin root and list what it declares
(`sequential-thinking`, `playwright`, `github`, `context-hub`). You cannot introspect live
connections from here, so report them as **declared**, and tell the user to run `/mcp` for
actual connection state — do not guess or imply you checked.

**Hooks** ⟨plugin⟩ — read `hooks/hooks.json` and confirm each referenced script exists and
is executable. A hook whose script is missing fails open: it never blocks and never says so.
Report the event → script map so the user can see what is meant to be firing.

**Guards** ⟨plugin⟩ — run the two drift guards and report their output verbatim:

```bash
uv run --with pyyaml python <plugin>/scripts/check-routing.py --tool claude
uv run --with pyyaml python <plugin>/scripts/check-docs.py
```

**Project shape** — in the current project: is it a git repo; is there a `specs/`; a
`.forge/manifest.json` (scaffolded — report template + version) or `.forge/adoption.json`
(adopted); what rigor tier is the project default; does `.mise.local.toml` exist where the
project expects secrets. For a scaffolded project also compare the manifest's
`template_version` against the newest `vX.Y.Z` tag of the template source
(`git ls-remote --tags`) and, if behind, point at `/wellforge:upgrade`.

**Git policy** — `git config merge.ff` (want `only`), `pull.rebase` (want `true`), and
whether `gates/hooks/commit-msg` is installed in `.git/hooks/`. On FAIL:
`./scripts/setup-git-policy.sh` (or `mise run git-policy` in a generated project).

## Step 3 — `--tests` (opt-in, slower)

Only with the flag: run the plugin's own regression matrices from the plugin root and report
pass/fail counts per suite.

```bash
<plugin>/hooks/scripts/tests/pre-bash-guard.test.sh
<plugin>/hooks/scripts/tests/pre-file-guard.test.sh
<plugin>/hooks/scripts/tests/stop-verify.test.sh
uv run --with pyyaml python <plugin>/scripts/tests/run-report.test.py
```

These are the same suites CI runs. Running them here answers "is the plugin I have actually
sound", which is otherwise only knowable by pushing. Note in the report that the
stop-verify budget case **skips without coreutils `timeout`** (bare macOS) — a skip is not a
pass.

## Step 4 — Report

One table, `OK` / `WARN` / `FAIL` per check, then:

- **FAILs first**, each with its fix command. No FAILs → say so in one line.
- **WARN** is for "works, but degraded": no `gh` auth (connections will stall), no
  Playwright (designer can't audit the running app), project behind on its template.
- End with the **command index** — what this plugin offers here, grouped: spec flow
  (`spec` → `plan` → `design` → `tasks` → `implement` → `eval` → `done`), orchestration
  (`orchestrate`, `spike`, `promote`), lifecycle (`new`, `upgrade`, `adopt`,
  `extract-template`, `release`), visibility (`status`, `triage`, `doctor`). One line each,
  so `/wellforge:doctor` doubles as the help the plugin otherwise lacks.

## Hard rules

- **Read-only.** Never install a tool, write a config, run `gh auth login`, or fix a git
  setting. Diagnose and hand the user the command; an agent that silently fixes the
  environment hides the fact that it was broken.
- Never report a check you did not run. If something cannot be checked from here — live MCP
  connections are the standing example — say what you can see (declared) and name the
  command that shows the rest (`/mcp`).
- A skipped test is reported as skipped, never folded into a pass count.
