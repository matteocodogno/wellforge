---
description: Spec-health heartbeat — surface features that are rotting (stale in-progress, unresolved drift, passed QE but never eval'd, parked before it started). Read-only digest, runnable manually or on a schedule.
argument-hint: [--stale-days N] — staleness threshold for in-progress features (default 14)
---

Surface the features the pull-only flow lets rot. This is the **spec-health heartbeat**
(loop-engineering automations — load the **heartbeat** skill), a read-only triage digest over
`specs/` + `.forge/runs/`. It **never fixes anything** — it surfaces work for a human, exactly
like every other heartbeat. Conventions: the **spec-driven** and **observability** skills (load
them).

Argument: $ARGUMENTS  (`--stale-days N` overrides the in-progress staleness threshold; default 14)

## Gather — one command

```bash
# Resolve the plugin root ONCE per session, then reuse $WF. ${CLAUDE_PLUGIN_ROOT} is
# substituted for HOOKS only — it is NOT exported to the Bash tool (measured: unset), so
# interpolating it here silently runs `python3 /scripts/...`.
WF=$(python3 -c "import json,os;p=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))['plugins'];print(next(i['installPath'] for k,v in p.items() if k.startswith('wellforge@') for i in v))" 2>/dev/null)
# Running from a checkout (claude --plugin-dir) installs nothing; fall back to the repo.
[ -n "$WF" ] || WF="$(pwd)/wellforge-plugin"
# A FUNCTION, not a variable holding a command: `WFPY="uv run ... python"` then `wfpy x`
# relies on word splitting, which zsh does not do for unquoted parameters — measured, it
# fails with `command not found: uv run --quiet --with pyyaml python`.
# uv first because forge-state needs pyyaml to read frontmatter and the system python3
# usually lacks it; without it every field reads as unknown.
wfpy() {
  if python3 -c "import yaml" 2>/dev/null; then python3 "$@"; else uv run --quiet --with pyyaml python "$@"; fi
}
wfpy "$WF/scripts/forge-state.py" --json
```

One call, everything below. It returns the `forge-state/v1` envelope documented in
`/wellforge:status`: per feature the `status`, `kind`, `rigor`, `tasks {total, checked}`,
`drift {drifted, reason, sources}`, `verdicts {qe, eval}` joined from `.forge/runs/`,
`done_gate`, `last_activity`, and `problems` (frontmatter that violates the schema).

**Do not open a single spec file to compute a signal.** This command runs on a schedule; a
heartbeat that re-reads six files per feature to recount what a script already counted is
paying tokens for a loop. The **heartbeat** skill draws exactly this line — discovery
deterministic, judgment agentic — and here the only judgment is the digest's prose.

For unresolved drift the envelope's `drift` is *artifact staleness*; the **drift events**
recorded by agents during a run are separate and still come from the run traces:

```bash
wfpy "$WF/scripts/run-report.py" --json
```

Read `drift_open` per run from that. (forge-state answers "is tasks.md behind the spec";
run-report answers "did an agent report drift and was it reconciled". Both are real, and
they are not the same question.)

## The signals — deterministic rules

Evaluate every feature; a feature can appear under more than one signal.

Each signal below is a filter over `features[]`. The envelope field is named in brackets so
the rule is checkable, not recalled.

0. **Terminal statuses are skipped entirely** [`terminal == true`]. `done`, `superseded` and `archived` are all
   exits from the lifecycle (spec-driven skill): they will never move again, and reporting
   them as rot trains people to ignore the digest. Skip them in every signal below — with
   one exception: if a superseded spec's `superseded_by:` names a feature that does not
   exist, say so once under a **broken pointer** line. That is a real defect, not staleness.

1. **Stale in-progress** [`status == in-progress` AND `last_activity` older than the
   threshold]. Default 14 days. → "idle Nd — pick it back up,
   park it, or retire it with `/wellforge:done <slug> --superseded-by <other>` if another spec
   took over". A long-lived in-progress is invisible debt.
2. **Unresolved drift.** Any run trace for the feature has a `drift_events` entry with
   `resolved: false` (surfaced as `drift_open` by the report script). → "drift never reconciled —
   route to the owner (PO for spec, architect for plan), re-sync `/wellforge:tasks`". A spec the
   code silently worked around is the most dangerous rot.
3. **Passed QE, never eval'd (production only)** [`rigor == production` AND
   `tasks.checked == tasks.total` AND `verdicts.qe.verdict == PASS` AND
   `verdicts.eval.verdict != PASS` AND `status != done`]. → "QE-green but unjudged — run `/wellforge:eval NNN-slug`". The eval is the
   bar, not the QE demo (rigor-tiers); a feature stuck here looks done but isn't.

4. **Parked before it started** [`status` in (`draft`, `approved`) AND
   (`!artifacts.tasks` OR `tasks.checked == 0`) AND `last_activity` older than the
   threshold]. → "approved Nd ago, never started — start it
   (`/wellforge:tasks`), or retire it (`/wellforge:done <slug> --archive "<why>"`)".

   This is the signal for **deliberately deferred work**, and it is the one that makes
   deferral safe: a decision to not-do-something-yet is only honest if the not-doing stays
   visible. Without it a spec written to record a deferral rots in exactly the way the
   deferral was meant to avoid — signals 1–3 all require work to have started, so an
   approved spec with no tasks is invisible to every one of them. A draft nobody approved
   counts too: the most common form of this is a spec someone wrote, nobody rejected, and
   nobody picked up.

5. **Frontmatter that does not validate** [`problems` non-empty]. A `status: doen` is not a
   status; a `superseded` with no `superseded_by` points nowhere. These used to be invisible
   — the model read them as approximately-right — and now they are a line in the digest with
   the schema violation quoted verbatim. This signal exists *because* discovery became
   deterministic: a script can tell that a value is not in an enum, and a reader skimming
   prose cannot.

6. **QE green, never security-reviewed** [`rigor == "production"`, `verdicts.qe.verdict ==
   "PASS"`, `verdicts.security.verdict == null`, `status` not terminal]. The most
   comfortable-looking failure in the set: every test passes, the dashboard is green, and
   the review that was supposed to be automatic at this tier never ran. `production` is in
   `always_at_tier`, so an absent verdict here is never "nothing matched" — it means no
   trigger check happened at all, which was true of `/wellforge:promote` (it dispatched no
   review and then demanded one) and of `/wellforge:orchestrate`'s mvp pipeline.

   Report it as: `<feature> — QE PASS, no security verdict on record. /wellforge:done will
   refuse. Run /wellforge:implement <feature> (Step 3b dispatches the reviewer).` Do **not**
   report it as a gate failure the author caused; the gap is a command that skipped a step.

   A `FAIL` verdict is a different signal and belongs under the ordinary gate reporting — it
   means the review ran and found something, which is the system working.

7. **Over budget** [`budget.per_feature[].state == "over"`]. The deterministic query:

   ```bash
   wfpy "$WF/scripts/run-report.py" --json --budget
   ```

   → "spent $X of a $Y `<tier>` ceiling (Z%), top consumer `<agent>`". Budgets are
   **advisory** (`config/rigor-budgets.yml`, `advisory_only: true`) — this surfaces, it
   never blocks, per the surface-never-ship rule.

   **`state: "unknown"` is not a finding and must not be reported as one.** It means no
   token events were captured for that feature, which is the normal state when the
   SubagentStop hook never fired. Listing it under "over budget" would turn missing data
   into an accusation. Mention the count once in the footer instead: *"N features have no
   cost data."*

7. **Rework hotspots** [`rework.by_agent[agent] >= hotspot_rounds`]. Same call with
   `--rework`; the threshold and window live in `config/rigor-budgets.yml`
   (`rework.hotspot_rounds`, `rework.window_runs`).

   → "`backend-dev`: 4 rework rounds in the last 20 runs". A rework round is a run whose
   `qe` or `security` verdict FAILED — work that had to be redone.

   Report it as a **question, not a verdict**: rework concentrated on one agent is the
   evidence `config/model-routing.yml` asks for before re-tiering, but the count alone does
   not say whether the agent was too cheap, the spec was wrong, or the feature was hard.
   Naming the candidate is the digest's job; deciding is not.

Also fold in the **lower-tier debt** signal `/wellforge:status` already computes (a `spike`/`mvp`
feature older than ~30 days → promote or archive) — restate it here so the digest is the single
"what needs attention" view. Don't re-derive the per-feature next step (that's `/wellforge:status`).

## Output — the digest

Group by signal; omit a group that's empty. Under each, one line per feature. Example:

```
WellForge · spec-health triage        (stale-days: 14)

⏳ Stale in-progress
  003-audit-log     production   idle 21d   → resume or park
  007-import        mvp          idle 16d   → resume or park

⚠ Unresolved drift
  005-pricing       production   plan drift never reconciled → route to architect, re-sync tasks

💤 Parked before it started
  003-ts-migration  production   draft 31d, no tasks → start it, or archive with a reason

🧪 Passed QE, never eval'd
  004-billing       production   tasks 8/8, QE PASS, no eval → /wellforge:eval 004-billing

💤 Lower-tier debt
  002-spike-search  spike        spike for 44d → /wellforge:promote, or /wellforge:done --archive "<why>"

Summary: 5 features need attention · 2 stale · 1 drift · 1 unevaluated · 1 tier-debt
```

If **nothing** needs attention, say so in one line: "Spec-health clean — nothing rotting." —
that's the good state, and a heartbeat that says "all clear" is doing its job.

## Scheduled use (the heartbeat vehicle)

Run manually any time, OR schedule it as the **spec-health heartbeat** — a Claude Code routine
(the `schedule` skill) invoking `/wellforge:triage` on a cadence (default weekly) and posting the
digest. Per the **heartbeat** skill:
- **Surface, never auto-ship** — post the digest to a tracking issue or Slack; never touch specs,
  check boxes, run eval, or promote. A human reads it and decides.
- **Auth degrades** — in a headless/cron run the github MCP may be absent; post via `gh issue`
  (needs `GITHUB_TOKEN`), not an interactive connection.
- **Dedup + cost bound** — update one rolling "spec-health" issue in place (don't open a new one
  each week); keep the sweep on a cheap model, and it's read-only so there's no escalation.
- **Record it** — write a run trace (`command: triage`) per the observability skill when run as a
  scheduled agent.

## Hard rules

- **Read-only.** Never edit specs, check boxes, change status, run eval, or promote — this
  reports. Every action word in the digest is a suggestion for the human, not something you do.
- The signals come from the rules above, not judgment — same inputs, same digest.
- A folder without `spec.md`/`brief.md` is not a feature; ignore it silently.
- If there are no run traces, signals 1 and 3 still work from the spec files; skip signal 2 and
  note "(no run traces — drift signal unavailable)".
