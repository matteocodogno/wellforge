---
name: observability
description: >
  WellForge run-trace / observability conventions — the .forge/runs/ trace format that records
  which agents ran for which feature, their outcomes, drift events, verdicts, and (best
  effort) token cost. Use whenever a workflow command (orchestrate, implement, eval) runs
  agents and must record a run, when reading agent run history, when the evaluator needs
  trajectory evidence, or when /wellforge:status surfaces recent runs and cost. Canonical
  reference for the .forge/runs/ schema — producers and consumers MUST follow it.
---

# Observability — run traces

Every multi-agent run leaves an auditable trace. Two layers:

1. **Semantic run trace** (reliable) — written by the command that ran the agents
   (`orchestrate`/`implement`/`eval`). It knows the context: feature, agents, tasks,
   verdicts, drift. One JSON file per run.
2. **Token events** (best-effort) — appended by the `trace-subagent` hook on each
   subagent completion, when the harness exposes usage. Raw, machine, transient.

`run-report.py` (in the plugin) joins them: per-run summary + token/cost estimate.

## Layout (inside the project)

```
.forge/
├── manifest.json          # (scaffolded projects) template provenance — unrelated
└── runs/
    ├── 2026-06-24T10-44-00Z-implement-001-user-auth.json   # semantic run trace (committable audit trail)
    └── .events.jsonl                                        # raw token events (gitignored, transient)
```

`.forge/runs/` is created on first run. The semantic `*.json` files are the audit trail —
keep them committed unless the team chooses otherwise. `.events.jsonl` is gitignored.

## Semantic run trace — schema `wellforge-run/v1`

```json
{
  "schema": "wellforge-run/v1",
  "run_id": "<UTC ts, ':'→'-'>-<command>-<feature>",
  "command": "implement | orchestrate | eval | spike | promote",
  "feature": "001-user-auth",
  "rigor": "production | mvp | spike",
  "started": "2026-06-24T10:44:00Z",
  "finished": "2026-06-24T10:52:13Z",
  "agents": [
    { "agent": "backend-dev", "tasks": ["T2","T3"], "outcome": "completed", "commits": ["abc1234"], "worktree": "forge/be-t2" },
    { "agent": "quality-engineer", "outcome": "PASS" },
    { "agent": "evaluator", "outcome": "PASS", "score": 86 }
  ],
  "drift_events": [
    { "agent": "backend-dev", "artifact": "plan.md", "summary": "<what diverged>", "resolved": true }
  ],
  "collision_events": [
    { "tasks": ["T3","T5"], "files": ["src/app/config.ts"], "resolved_by": "added deps: T5→T3, re-ran T5" }
  ],
  "verdicts": { "qe": "PASS", "eval": "PASS" },
  "result": "completed | escalated | partial",
  "tokens": null,
  "cost_usd": null
}
```

- Timestamps: `date -u +%FT%TZ`. `run_id` replaces `:` with `-` so it's a safe filename.
- `tokens`/`cost_usd` stay `null` in the trace; `run-report.py` computes them from
  `.events.jsonl` at read time (don't try to fill them inline — you can't read your own
  subagents' token counts reliably mid-run).
- **Drift is recorded, not just handled.** Every time an agent reports drift and the
  command pauses to amend, append a `drift_events` entry — this is the audit beyond the
  binary stop-verify hook.
- **Parallel isolation is recorded too.** When a batch runs under worktree isolation
  (implement/orchestrate dispatch of ≥2 independent agents), record each isolated agent's
  branch in its `worktree` field. A merge **collision** (two "independent" tasks touched the
  same file → a wrong DAG edge) is appended to `collision_events` with the tasks, files, and
  how it was resolved. Both fields are omitted when the run used the main-tree / sequential
  path (no isolation).
- **`rigor`** records the resolved tier for the run (`production`/`mvp`/`spike`, per the
  rigor-tiers skill). `spike` runs record `"agents": []` (main loop, no subagents).
  `promote` runs additionally record the tier transition: `"from": "<tier>", "to": "<tier>"`.

## Producers (the commands)

`orchestrate`, `implement`, `eval`: at the START of the run, `date -u +%FT%TZ` →
`started`; dispatch agents as usual; at the END, write
`.forge/runs/<run_id>.json` with every agent's outcome, drift events, and verdicts.
Write it even on escalation/partial (`result` records that). One file per run; never
overwrite a prior run.

## Consumers

- **`run-report.py`** (`${CLAUDE_PLUGIN_ROOT}/scripts/run-report.py`) — summarizes
  `.forge/runs/`: per run the agents/verdicts/drift, and tokens × `config/model-pricing.yml`
  → estimated cost (events joined by the run's `[started, finished]` window).
- **`/wellforge:status`** — an observability line per feature: last run, result, est. cost,
  unresolved drift.
- **The `evaluator`** — reads the feature's run traces for **trajectory** evidence (did
  the right agents run in order, did QE run, was verification skipped) instead of scoring
  trajectory neutral-when-blind.

## Honest limits — tokens/cost are NOT real cost

The semantic trace (who ran, verdicts, drift) is **exact**. The token/cost layer is
**structurally a large under-count** and must never be presented as real cost:

- The `SubagentStop` hook captures only a fraction of subagent usage, and only when the
  harness exposes it (observed ~10–20× under real `/usage` in pilot).
- It **cannot see the main orchestrating loop** — most of the consumption — because only
  subagents trigger the hook.
- It **ignores cache read/write tokens**, which dominate cost on cache-heavy sessions.

So treat the trace as an **audit trail**, not a cost meter. For real session cost, the
agent CLI's own accounting is authoritative — `/usage` in Claude Code. WellForge does not
try to reproduce it (a losing game against the tool's exact numbers); it reports what ran,
clearly labels tokens as partial, and points to `/usage`.
