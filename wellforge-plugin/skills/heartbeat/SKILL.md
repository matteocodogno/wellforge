---
name: heartbeat
description: >
  WellForge heartbeat / scheduled-automation conventions — the "automations" pillar of loop
  engineering. Scheduled tasks that do discovery + triage on a cadence and SURFACE work for a
  human (never auto-ship). Use whenever adding or reasoning about a heartbeat: the scheduled
  gate heartbeat, the template-drift heartbeat, the fleet heartbeat, or the spec-health
  heartbeat (/wellforge:triage). Authoritative reference for the surface-never-ship rule, the
  one-deduplicated-issue-per-concern rule, the deterministic-vs-agentic split, the off-for-spike
  rule, the cost bound, and where each heartbeat records its trace.
---

# Heartbeat — scheduled automations

A **heartbeat** is a scheduled task that runs on a cadence, discovers work the pull-only flow
would miss, and **surfaces it for a human**. It is the fifth "loop engineering" component
(automations); WellForge already had the other four (skills, verifying subagents, connectors,
external state). Heartbeats exist because some findings appear **without a commit** — a newly
disclosed CVE, a template that moved ahead, a feature left half-done — so nothing triggers a PR.

## The non-negotiable principle — surface, never auto-ship

A heartbeat **opens or updates an issue, posts a digest, or drafts a human-gated PR. It never
merges, deploys, closes a feature, or self-approves.** This is the article's "stay the engineer"
warning and WellForge's gate philosophy in one rule: a heartbeat is discovery + triage, the
human decides. A heartbeat that "fixes" things silently is a bug, not a feature.

## The four heartbeats

| Heartbeat | Kind | Vehicle | Surfaces |
|---|---|---|---|
| **Gate** (14a) | deterministic | GitHub Actions `on: schedule` | CVEs newly disclosed vs merged deps, SAST-rule drift, coverage |
| **Template-drift** (14b) | deterministic | GitHub Actions `on: schedule` | project N `vX.Y.Z` releases behind its template → `/wellforge:upgrade` |
| **Fleet** (14b) | agentic | Claude Code routine (scheduled) | org-wide: which projects drifted / have failing gates → one rolling report |
| **Spec-health** (14b) | agentic | Claude Code routine + manual `/wellforge:triage` | stale `in-progress`, unresolved drift, passed-QE-never-eval'd |

Deterministic heartbeats are **GitHub Actions** — cheap, no tokens, no auth surprises; they
reuse the reusable gate workflows (`gates-v*`) rather than duplicating logic. Agentic heartbeats
need **judgment** (triage, summarize, prioritize) so they run as scheduled Claude Code agents.

## Rules every heartbeat follows

1. **One deduplicated issue per concern.** A heartbeat that opened a fresh issue each run would
   train people to ignore it. Keep exactly one open issue per concern (identified by a label:
   `heartbeat`, `template-drift`, …): open on first finding, **update in place** each run, close
   with a comment when the finding clears. The reusable `heartbeat-report.yml` does this for the
   deterministic heartbeats; agentic ones follow the same update-in-place discipline.
2. **Off for `spike`.** A spike has no enforced gates or lifecycle guarantees to watch
   (rigor-tiers skill). Deterministic heartbeats aren't generated for `rigor: spike`; agentic
   ones skip spike-only projects.
3. **Opt-in, recorded.** Per-project heartbeats are a copier answer (`heartbeat` +
   `heartbeat_cron`) recorded in `.forge/manifest.json` — visible, upgradable, never silent.
4. **Cost-bounded (agentic).** A scheduled agent runs unattended and costs tokens. Bound it:
   cheap model for the triage sweep, escalate to a stronger model only on a real finding; cap
   the work per run; never loop unbounded. State the bound in the routine.
5. **Auth degrades gracefully (agentic).** Interactively-authenticated MCP servers (e.g. the
   github MCP) may be **absent in headless/cron runs**. A scheduled heartbeat must fall back to
   `gh` CLI / REST with a `GITHUB_TOKEN`, never assume an interactive MCP connection.
6. **Recorded like any run.** An agentic heartbeat writes a run trace per the **observability**
   skill (`.forge/runs/…-triage-…json`, or `command: heartbeat`); the deterministic ones leave
   their audit trail in the tracking issue's history.

## Cadence

Default **weekly** (`0 6 * * 1`, Mon 06:00 UTC) — low noise, still catches CVEs within days,
and the single-issue-updated-in-place model keeps it fresh without alert fatigue. Configurable
per project (`heartbeat_cron`) and per routine. Don't go tighter than the finding actually moves.

## See also

- **rigor-tiers** — why spike is excluded and how tiers gate ceremony.
- **observability** — the `.forge/runs/` trace format agentic heartbeats write.
- **connections** — wiring a scheduled routine and its `GITHUB_TOKEN` / secrets.
- `gates/README.md` — the deterministic `heartbeat-report.yml` / `template-drift.yml` workflows.
