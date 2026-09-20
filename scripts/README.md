# Scripts — the CLI, its tests, and the org-ops tooling

## `wellforge` — the CLI

`scripts/wellforge` is the setup/diagnostics tool a teammate installs with Homebrew
(`Formula/wellforge.rb` installs exactly this file). It is the one script here that is NOT
fleet tooling, and the one with a regression suite.

### Releasing it

The CLI has its **own** tag series, `cli-vX.Y.Z` — it is not part of the template's
`vX.Y.Z`. It used to be, which meant a CLI fix could only ship with a template release, and
so CLI fixes did not ship: `scripts/wellforge` drifted 179 insertions past `v0.9.0` while
every brew user ran the old one. Full reasoning in [`docs/VERSIONING.md`](../docs/VERSIONING.md).

```bash
scripts/release-cli.sh patch            # plan only — prints every step, changes nothing
scripts/release-cli.sh patch --execute  # bump, commit, tag, push, sha256, formula, push
```

`WELLFORGE_CLI_VERSION` at the top of `scripts/wellforge` is the single source: it is what
`wellforge version` prints, what the Formula's `test` block asserts, and what CI compares
against the newest `cli-v*` tag. Do not bump it by hand — the constant, the tag and the
Formula's `url`/`version`/`sha256` have to agree, and the sha can only come from the pushed
tag (GitHub generates that tarball; a local `git archive` of the same tree hashes
differently — measured, see the script's header).

### Tests

```bash
scripts/tests/wellforge.test.sh          # ~60s; needs bash, git, jq
```

It drives the **real** script against a temp `HOME`, a temp `PATH` of shim executables
(`brew`, `claude`, `gh`, `docker`, `mise`, `curl`, …) and real git fixtures with a real bare
upstream — same contract as `wellforge-plugin/hooks/scripts/tests/*.test.sh`: no re-stating
of the script's logic, so a rule cannot pass its test and fail in practice. Shims record
their calls, which is how "update must not reinstall a plugin that is already current" can
be asserted at all — that behaviour produces no output, only calls.

**`xfail` cases are deliberate.** They describe behaviour a later change introduces; the
suite does not fail on them, but it DOES fail if one starts passing, because then the marker
is lying. Today: `update` reinstalling an up-to-date plugin, an unknown subcommand exiting 0,
`telegram` picking a group chat over a private one, and `telegram` spinning forever on an
exhausted stdin.

**It is CI-only, and deliberately not wired into `/wellforge:doctor --tests`.** That command
runs from the installed plugin, whose root is `wellforge-plugin/` — it has no `scripts/`, and
a *generated project* has neither. Running it would mean shipping the suite inside the plugin
to test a CLI the plugin does not contain. The suite belongs to this repo and runs in this
repo's CI (`cli` job in `.github/workflows/ci.yml`), alongside
`shellcheck -s bash --severity=warning`.

**Known coverage gap:** CI runs the suite on `ubuntu-latest`, while the CLI targets macOS.
Logic regressions are caught; BSD-vs-GNU behaviour differences (`readlink -f`, `sed -i`) are
not. Run it locally on a Mac before a release — it is the same one command.

## Org-ops scripts

Fleet-level tooling — run from a checkout of this repo (they read its `vX.Y.Z` tags to know the
latest template release). Both need an authenticated `gh` CLI and `jq`.

| Script | What |
|---|---|
| `fleet-status.sh <org>` | table of every WellForge-generated repo in an org and its template version vs latest |
| `fleet-triage.sh <org>` | the **fleet heartbeat**'s data step — template drift **and** gate health per repo, grouped by what needs attention, with a one-line summary |

Both accept `--repo-list <file>` (one `owner/repo` per line) to skip the org-wide code search
(which needs a broad search scope) and check an explicit list instead.

```bash
scripts/fleet-triage.sh my-org
scripts/fleet-triage.sh my-org --repo-list fleet.txt
```

## Fleet heartbeat (scheduled)

The **fleet heartbeat** (loop-engineering automations — see the `heartbeat` skill) runs
`fleet-triage.sh` on a cadence and posts the report so a human notices drifted or failing
projects without checking by hand. It is **agentic** (a Claude Code routine) because the triage
report is meant to be read and acted on, not just dumped.

Wire it with the `schedule` skill (a Claude Code routine) — sketch:

- **Cadence:** weekly (matches the per-project heartbeat default). Don't go tighter than the
  fleet actually changes.
- **Job:** run `scripts/fleet-triage.sh <org>`; if the summary shows anything ⬆/✗, post the
  report to **one rolling "fleet health" issue** (or Slack) — update it in place, don't open a
  new issue each week (the dedup rule).
- **Surface, never auto-ship:** the routine reports only. It never runs `/wellforge:upgrade`,
  never merges, never touches a downstream repo. A human reads the report and decides.
- **Auth (headless):** a scheduled/cron run has no interactive github MCP — authenticate `gh`
  with a `GITHUB_TOKEN` that can read the org's repos and their Actions runs, and post via
  `gh issue`. See the `connections` skill for token scope.
- **Cost bound:** the data step is plain `gh`/`jq` (no tokens); keep any agent summarization on a
  cheap model, and it's read-only so there's no escalation. Record the run per the
  `observability` skill (`command: heartbeat`) if run as an agent.

Not shipped as a live cron — scheduling is your org's infrastructure. This provides the runnable
data step and the recipe; enable it once the Phase 7 pilot shows the fleet is worth watching.
