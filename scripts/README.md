# Org-ops scripts

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
