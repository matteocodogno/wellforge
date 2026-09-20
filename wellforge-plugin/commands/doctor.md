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
need it (they are marked ⟨plugin⟩ below) rather than reporting them as failures. Note that
a session launched with `claude --plugin-dir <checkout>/wellforge-plugin` is exactly this
case: nothing is installed, and that is normal for a contributor. Say which of the two it
is, instead of reporting a healthy checkout as a broken install.

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
Report the event → script map so the user can see what is meant to be firing — **7 events,
8 scripts** (PostToolUse runs two: `post-lint.sh` and `post-spec-guard.sh`).

Call out `post-spec-guard.sh` specifically if it is missing or not executable: it is the
only mechanical enforcement of the `status: done` gate and the raise-only `rigor:` rule.
Without it both revert to prompt promises, and nothing in a session will say so.

**Guards** ⟨plugin⟩ — run the two drift guards and report their output verbatim:

```bash
uv run --with pyyaml python <plugin>/scripts/check-routing.py --tool claude
uv run --with pyyaml python <plugin>/scripts/check-docs.py
```

**Feature state** — run `forge-state.py` against this project and report two things: that it
runs at all (it is what `/wellforge:status`, `:triage`, `:done` and `:promote` all read, so a
failure here breaks four commands at once), and the count of `problems[]` across features.

```bash
python3 <plugin>/scripts/forge-state.py --json | python3 -c "import json,sys; e=json.load(sys.stdin); print(len(e['features']), 'features,', sum(len(f['problems']) for f in e['features']), 'schema problems')"
```

A non-zero problem count is a **FAIL** with the offending frontmatter quoted: it means a
spec's `status:` or `rigor:` is not a value the lifecycle defines, which every consumer of
that state will then mis-read.

**Project shape** — in the current project: is it a git repo; is there a `specs/`; a
`.forge/manifest.json` (scaffolded — report template + version) or `.forge/adoption.json`
(adopted); what rigor tier is the project default; does `.mise.local.toml` exist where the
project expects secrets. For a scaffolded project also compare the manifest's
`template_version` against the newest `vX.Y.Z` tag of the template source
(`git ls-remote --tags`) and, if behind, point at `/wellforge:upgrade`.

**Install source** ⟨plugin⟩ — where this plugin came from, which decides whether anyone
else can reproduce it. Read the install record and the marketplace it came from:

```bash
python3 - <<'PYEOF'
import json, os
d = json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))['plugins']
for k, v in d.items():
    if k.startswith('wellforge@'):
        i = v[0]
        print(k, i.get('version'), i.get('scope'), i.get('gitCommitSha', '')[:8], i['installPath'])
PYEOF
jq -r '.wellforge.source' ~/.claude/plugins/known_marketplaces.json 2>/dev/null
```

Report one of three, and never guess between them:

| What you find | Report |
|---|---|
| an install record **and** a marketplace source of `github` / `git-subdir` | `installed from the wellforge marketplace, <version> (<sha>)` — reproducible: a teammate runs the two install commands and gets the same plugin |
| an install record but a marketplace source of `directory` | **WARN** — `installed from a local checkout at <path>. That marketplace exists only on this machine, so a teammate cannot install what you are running.` Fix: `claude plugin marketplace add matteocodogno/wellforge` |
| no install record (running via `--plugin-dir`) | `running from a checkout, not an install — edits take effect on relaunch and no version is pinned. Expected for a contributor, unexpected for a user.` |

**Is there a newer plugin release?** The plugin series is tagged `plugin-vX.Y.Z`
(`docs/VERSIONING.md`). Compare the running version against the newest tag on the remote:

```bash
git ls-remote --tags https://github.com/matteocodogno/wellforge.git 'plugin-v*' \
  | sed 's|.*refs/tags/||; s|\^{}||' | sort -V | tail -1
```

Behind → **WARN** with both update commands (`claude plugin marketplace update wellforge`,
then `claude plugin update wellforge@wellforge`) and the note that the marketplace refresh
is what teaches Claude Code about the new tag. Network unreachable → report **unknown**,
never "up to date": those are different answers and only one of them is reassuring.

Do **not** report an update as done on the strength of having printed the commands. What
`claude plugin update` resolves to is undocumented (`docs/VERSIONING.md` says so), so the
version recorded in `installed_plugins.json` afterwards is the only evidence — tell the user
to re-run `/wellforge:doctor` to confirm.

**Plugin version vs. the project** — the project records which plugin set it up
(`plugin.version` in `.forge/manifest.json`, or `.forge/adoption.json` for an adopted
project). Compare it against the running plugin's `.claude-plugin/plugin.json` and report
one of four states:

| Recorded | State | Report |
|---|---|---|
| equal to running | **OK** | `plugin 2.38.0 — project and plugin agree` |
| older than running | **WARN** | `project set up by 2.31.0, running 2.38.0 — run /wellforge:upgrade to apply plugin migrations`, and list the applicable entries from `docs/PLUGIN-MIGRATIONS.md` if the wellforge repo is reachable |
| **newer** than running | **FAIL** | `project is on 2.40.0, this plugin is 2.38.0 — you are running an OLD plugin against a newer project. Update the plugin (/plugin) before running commands that write state; a stale plugin can write a file format the project has already moved past.` |
| **absent** | **WARN** | `no plugin version recorded — this project predates the field (plugin < 2.38). /wellforge:upgrade will stamp it and apply any migrations since.` |

The absent case is the **normal** state of every project scaffolded before 2.38, not an
error: report it as a WARN with that fix and move on. Never crash, and never treat a missing
field as a mismatch — "unknown" and "wrong" are different answers and only one of them needs
alarm.

An adopted project's `plugin` may be a bare version **string** rather than an object (the
shape before 2.38). Accept both; report the string form as recorded-but-old-shape, which
`/wellforge:adopt` or `/wellforge:upgrade` will normalise.

The object's **`marketplace`** field (2.42+) records provenance: `wellforge@wellforge` or
`local`. Compare it with the install source above and call out the mismatch that matters —
a project stamped `local` was set up by someone running a checkout, so its recorded plugin
version names no published release and cannot be reinstalled from it. An absent field means
recorded before 2.42, i.e. unknown, and is reported as unknown.

**Project declares the plugin** — a scaffolded or adopted project's `.claude/settings.json`
should carry `extraKnownMarketplaces.wellforge` and `enabledPlugins["wellforge@wellforge"]`
(`templates/_shared/CONTRACT.md`). Missing → **WARN**: the project works for anyone who
already has the plugin and does nothing at all for anyone who does not, with no error either
way. Fix: `/wellforge:upgrade` (scaffolded) or re-run `/wellforge:adopt` (adopted).

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
<plugin>/hooks/scripts/tests/post-spec-guard.test.sh
uv run --with pyyaml python <plugin>/scripts/tests/run-report.test.py
uv run --with pyyaml python <plugin>/scripts/tests/forge-state.test.py
uv run --with pyyaml python <plugin>/scripts/check-budget.py
```

`check-budget.py` is worth reporting even when it passes: it prints what this plugin costs
every session in this project (~4,900 estimated tokens of descriptions, loaded before the
user types), and that number is invisible otherwise.

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
