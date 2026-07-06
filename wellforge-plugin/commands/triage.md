---
description: Spec-health heartbeat — surface features that are rotting (stale in-progress, unresolved drift, passed QE but never eval'd). Read-only digest, runnable manually or on a schedule.
argument-hint: [--stale-days N] — staleness threshold for in-progress features (default 14)
---

Surface the features the pull-only flow lets rot. This is the **spec-health heartbeat**
(loop-engineering automations — load the **heartbeat** skill), a read-only triage digest over
`specs/` + `.forge/runs/`. It **never fixes anything** — it surfaces work for a human, exactly
like every other heartbeat. Conventions: the **spec-driven** and **observability** skills (load
them).

Argument: $ARGUMENTS  (`--stale-days N` overrides the in-progress staleness threshold; default 14)

## Gather (read-only)

For every `specs/NNN-slug/` directory:
- `spec.md` / `brief.md` frontmatter: `status`, `rigor` (default `production`), `created:`,
  `approved:`, `done:`.
- `tasks.md` present? checked vs total task lines.
- `eval-report.md` present? its `verdict` (PASS / FAIL) and `score`.
- The file mtimes of `spec.md` / `plan.md` / `tasks.md` (for the staleness clock — most recent
  edit to any of them).

From `.forge/runs/` (if present), via the report script:
```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run-report.py --json
```
Read each run's `feature`, `verdicts` (qe / eval), and `drift_open` (unresolved drift events).

## The three signals — deterministic rules

Evaluate every feature; a feature can appear under more than one signal.

1. **Stale in-progress.** `status: in-progress` AND the most recent edit to `spec.md`/`plan.md`/
   `tasks.md` is older than the stale-days threshold (default 14). → "idle Nd — pick it back up
   or park it". A long-lived in-progress is invisible debt.
2. **Unresolved drift.** Any run trace for the feature has a `drift_events` entry with
   `resolved: false` (surfaced as `drift_open` by the report script). → "drift never reconciled —
   route to the owner (PO for spec, architect for plan), re-sync `/wellforge:tasks`". A spec the
   code silently worked around is the most dangerous rot.
3. **Passed QE, never eval'd (production only).** `rigor: production` AND all tasks checked AND
   the latest QE verdict is PASS AND (`eval-report.md` absent OR its `verdict` is not PASS) AND
   `status != done`. → "QE-green but unjudged — run `/wellforge:eval NNN-slug`". The eval is the
   bar, not the QE demo (rigor-tiers); a feature stuck here looks done but isn't.

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

🧪 Passed QE, never eval'd
  004-billing       production   tasks 8/8, QE PASS, no eval → /wellforge:eval 004-billing

💤 Lower-tier debt
  002-spike-search  spike        spike for 44d → promote or archive

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
