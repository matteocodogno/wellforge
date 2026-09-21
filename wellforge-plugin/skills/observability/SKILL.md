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

## Semantic run trace — schema `wellforge-run/v3`

```json
{
  "schema": "wellforge-run/v3",
  "plugin_version": "2.39.0",
  "run_id": "<UTC ts, ':'→'-'>-<command>-<feature>",
  "command": "implement | orchestrate | eval | spike | promote | triage",
  "feature": "001-user-auth",
  "rigor": "production | mvp | spike",
  "rigor_recorded": null,
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
  "env_faults": [
    { "agent": "frontend-dev", "class": "secret env", "detail": "VITE_API_BASE_URL empty in worktree, set in main tree", "resolved_by": "carried .mise.local.toml in, re-ran" }
  ],
  "verdicts": { "qe": "PASS", "security": "PASS", "eval": "PASS" },
  "security": { "matched_rules": ["**/auth/**", "token"], "dispatched": true },
  "result": "completed | escalated | partial",
  "tokens": null,
  "cost_usd": null,
  "terse": false,
  "control_run_id": null
}
```

- **Write the trace BEFORE the close it will be judged by.** The done gate reads
  `verdicts.qe` and `verdicts.security` *from the trace* (`forge-state.py` →
  `latest_verdicts`), so a command that closes first and records afterwards is asking the
  gate about a feature that has no trace yet: on a feature whose only run is this one,
  `/wellforge:done` refuses with "QE verdict is absent" for work that has just passed QE.
  `orchestrate` (both pipelines) and `promote` had exactly this order and were corrected.
  The alternative — write the trace incrementally per stage and finalise it after the close
  — is deliberately NOT the rule: it leaves a partially-written trace on disk at the moment
  the gate reads it, which trades a clear failure for an intermittent one.
- Timestamps: `date -u +%FT%TZ`. `run_id` replaces `:` with `-` so it's a safe filename.
- `tokens`/`cost_usd` stay `null` in the trace; `run-report.py` computes them from
  `.events.jsonl` at read time (don't try to fill them inline — you can't read your own
  subagents' token counts reliably mid-run).
- **Event shape** (one line per subagent completion, written by `trace-subagent.sh`):
  `{ts, event, model, agent_type, agent_id, session_id, input_tokens, output_tokens}`.
  Every field except `ts`/`event` is **optional** — the hook records what the harness
  exposes and omits the rest.
- **`plugin_version`** is the plugin that produced the run. Traces outlive the plugin that
  wrote them: the agent roster, the tier rules, the done gate and this very schema all move
  with the plugin, so a trace read a year later needs to say which rules it was produced
  under. It is also the only way to tell "this project ran an old plugin" from "this run
  behaved oddly".
- **`verdicts.security`** is the owasp-reviewer's outcome: `PASS`, `FAIL`, or **absent when
  no review was dispatched**. Absent and PASS must never read alike — at `production` every
  batch is reviewed (`config/security-triggers.yml`), so an absent verdict there means the
  review did not run, which is a failing done-gate condition rather than a silent pass.
  Record the matched rules alongside it so a later reader can see *why* it ran.
- **Every earlier schema stays readable.** v2 added `plugin_version`, v3 added
  `verdicts.security`; no field ever changed meaning. Consumers accept v1, v2 and v3 and
  treat a missing field as unknown — never as an error, never as a reason to skip a run.
  A schema bump that orphans the history it exists to preserve is a bad trade.
- **`rigor_recorded`** is the feature's own `rigor:` when a `--mode` flag ran this pass at a
  DIFFERENT tier; `null` when they agree (the normal case). `rigor` is always what actually
  ran. Keeping both is what makes a downgrade legible later: a run at `mvp` on a feature
  recorded `production` produced less verification than the spec's standard, and an
  evaluator reading trajectory evidence needs to see that rather than infer it from missing
  agents. See [`rigor-tiers`](../rigor-tiers/SKILL.md) — the flag is allowed, unannounced use of it is not.
- **`agent_type` is what makes cost attributable.** Events are matched to runs by time
  window first, then by `agent_type` when several windows overlap. Time alone is not an
  identity: a parallel batch has overlapping windows by construction, so a per-window sum
  counts every run's tokens in every other run's total. An event that matches several runs
  and no single agent is left **unattributed** and reported as such — a visible gap, never
  a number inflated in the direction of looking cheap. On a harness that doesn't send
  `agent_type`, sequential runs still attribute correctly (one window matches); parallel
  ones lose their token data instead of doubling it.
- **Drift is recorded, not just handled.** Every time an agent reports drift and the
  command pauses to amend, append a `drift_events` entry — this is the audit beyond the
  binary stop-verify hook.
- **Parallel isolation is recorded too.** When a batch runs under worktree isolation
  (implement/orchestrate dispatch of ≥2 independent agents), record each isolated agent's
  branch in its `worktree` field. A merge **collision** (two "independent" tasks touched the
  same file → a wrong DAG edge) is appended to `collision_events` with the tasks, files, and
  how it was resolved. Both fields are omitted when the run used the main-tree / sequential
  path (no isolation).
- **`env_faults`** (additive) records failures traced to the environment rather than the code
  — an unresolved variable in a worktree, a shared resource another worktree mutated (see the
  [`worktree-isolation`](../worktree-isolation/SKILL.md) enumeration for the `class` values). Record them even when they cost
  no fix round: an env fault that surfaced as "N tests failing" is exactly the evidence the
  evaluator's trajectory review and the next preflight need, and its absence from the trace is
  how the same one gets rediagnosed next month. When a batch **fell back to sequential**,
  record the preflight class that forced it here too, with `"resolved_by": "sequential"`.
- **`rigor`** records the resolved tier for the run (`production`/`mvp`/`spike`, per the
  rigor-tiers skill). `spike` runs record `"agents": []` (main loop, no subagents).
  `promote` runs additionally record the tier transition: `"from": "<tier>", "to": "<tier>"`.
- **`security`** records WHY the owasp-reviewer ran (or did not): `matched_rules` is the
  list of `config/security-triggers.yml` entries that matched — path globs, substrings, or
  the literal `always_at_tier:<tier>` — and `dispatched` whether the review actually ran.
  This skill, `implement` and `orchestrate` all say to "record the matched rules", and until
  now the schema had nowhere to put them, so the instruction could only be followed by
  inventing a field or ignored. An empty `matched_rules` with `dispatched: false` is a real
  answer: nothing triggered a review. It is not the same as the key being absent, which
  means the command never evaluated the triggers at all.
- **`terse`** and **`control_run_id`** are **additive fields** (schema id stays
  `wellforge-run/v3`; existing readers ignore unknown fields — no migration needed):
  - `terse: boolean` — was this run dispatched with terse mode active (per the **terse**
    skill's activation matrix: `--terse` resolved on for `orchestrate`/`implement`, or the
    spike default unless `--no-terse`). Producers (`orchestrate`, `implement`, `spike`) set
    this from their own resolved terse state when they write the trace; it's `false` for any
    run where terse never applied (including runs from before this field existed — an absent
    `terse` reads as `false`).
  - `control_run_id: string | null` — optional: the `run_id` of the non-terse control run
    this run is compared against for the terse-vs-control token measurement. Left
    `null` by the producers above; pairing a terse run to its control is a later concern
    (`run-report.py`), not something the producer command computes at write time.

## Producers (the commands)

`orchestrate`, `implement`, `eval`: at the START of the run, `date -u +%FT%TZ` →
`started`; dispatch agents as usual; at the END, write
`.forge/runs/<run_id>.json` with every agent's outcome, drift events, and verdicts.
Write it even on escalation/partial (`result` records that). One file per run; never
overwrite a prior run. `orchestrate`, `implement`, and `spike` additionally set `terse`
from their own resolved terse boolean (Step 0 in each command) when they write this file;
`control_run_id` stays `null` at write time (pairing is `run-report.py`'s job, not the
producer's).

## Consumers

- **`--json` envelope**: `{"runs": [...], "unattributed_events": N, "cost_estimated": bool}`.
  It is an object, not a bare list, because the two honesty signals have to travel with the
  data: how many token events could not be attributed to one run, and whether costs were
  priced at all. Consumers read `runs`.
- **`run-report.py`** (`<plugin>/scripts/run-report.py`; resolve `<plugin>` as
  `/wellforge:doctor` does — `${CLAUDE_PLUGIN_ROOT}` is substituted for HOOKS only and is
  NOT exported to the Bash tool) — summarizes
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
- Rates come from `config/model-pricing.yml` — the single table, no embedded copy. If it
  can't be read, the report says cost is unavailable rather than guessing; if a model id
  matches no key, the default rate is used and the run is flagged as inexact. The rates
  themselves are refreshed from the `claude-api` skill's model table, never from memory.

So treat the trace as an **audit trail**, not a cost meter. For real session cost, the
agent CLI's own accounting is authoritative — `/usage` in Claude Code. WellForge does not
try to reproduce it (a losing game against the tool's exact numbers); it reports what ran,
clearly labels tokens as partial, and points to `/usage`.
