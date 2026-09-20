---
description: Recap every feature's position in the spec→plan→tasks→implement flow, with the next command to run
argument-hint: [feature] — omit for all features; or NNN-slug / slug / NNN for one in detail
---

Show where each feature stands in the spec-driven workflow and the exact next command to
run. Read-only — never modifies anything. Conventions: the **spec-driven** skill (load it).

Target: $ARGUMENTS  (a feature token → detail view for that one; empty → all features)

## Gather — one command, no re-derivation

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/forge-state.py --json [--feature <slug>]
```

That is the whole gather step. `forge-state.py` walks `specs/`, validates every frontmatter
against `config/spec-frontmatter.schema.json`, counts tasks, computes drift from git history,
joins the latest QE and eval verdicts out of `.forge/runs/`, resolves each feature's tier by
the precedence rule, and evaluates the tier's done gate. **Do not re-derive any of it.**
Reading six files per feature and counting checkboxes is work a loop does faster, more
cheaply and — unlike a model — identically every time. It also rejects `status: doen`, which
a model reads as "done-ish".

The envelope (`forge-state/v1`):

```jsonc
{ "version": "forge-state/v1", "generated": "...", "runs_available": true,
  "features": [{
    "slug": "001-x", "kind": "feature|spike", "status": "in-progress",
    "rigor": "production", "rigor_from": "frontmatter|.forge/manifest.json|default",
    "terminal": false,
    "artifacts": { "spec": true, "brief": false, "plan": true, "plan_status": "approved",
                   "design": false, "tasks": true, "eval_report": false },
    "tasks":    { "total": 12, "checked": 9 },
    "drift":    { "drifted": true, "reason": "newer than tasks.md: spec.md", "sources": [...] },
    "verdicts": { "qe":   { "verdict": "PASS", "at": "...", "run_id": "..." },
                  "eval": { "verdict": null, "at": null, "run_id": null, "score": null } },
    "done_gate":{ "tier": "production", "passes": false, "failing": ["3 of 12 tasks unchecked"] },
    "superseded_by": null, "archive_reason": null, "created": "...", "last_activity": "...",
    "problems": [] }] }
```

Two values that are **not** `false`: `verdicts.*.verdict: null` means *no verdict on record*
— never a FAIL — and `done_gate.passes: null` means the gate is not machine-checkable (the
spike tier closes on prose in `brief.md`). Render them as "unknown" and "n/a", not as
failures. When `runs_available` is false, say verdicts are unavailable rather than absent.

Anything the envelope does not carry is still yours: the feature's *next ready task* (the
first unchecked task whose `deps:` are all checked) needs `tasks.md`, so read it only for a
single-feature detail view, and only then.

## Phase + next step — deterministic table

Evaluate top-down; first matching row wins. Every condition below reads a field the
envelope already carries — the column names the field, so this table documents what
`forge-state.py` computed rather than telling you to compute it again. `NNN-slug` is
`feature.slug`.

| Condition (envelope field) | Phase | Next step |
|---|---|---|
| `kind == spike`, `status != done` | **spike** | `/wellforge:spike NNN-slug` (build) |
| `kind == spike`, `status == done` | **spike ✓** | graduate: `/wellforge:promote NNN-slug --to mvp`, or stop here: `/wellforge:done NNN-slug --archive "<why>"` |
| (not in `features[]` at all) | (not a feature) | the script skips these silently |
| `status == draft` | **spec** | review & approve the spec — refine with `/wellforge:spec NNN-slug` |
| `status == approved`, `!artifacts.plan`, `rigor == production` | **plan** | `/wellforge:plan NNN-slug` |
| `status == approved`, `!artifacts.tasks`, `rigor == mvp` | **tasks** | `/wellforge:tasks NNN-slug` |
| `artifacts.plan_status == draft` | **plan** | review & approve the plan |
| `artifacts.plan_status == approved`, `!artifacts.tasks` | **tasks** | `/wellforge:tasks NNN-slug` |
| `tasks.checked == 0 < tasks.total` | **implement** | `/wellforge:implement NNN-slug next` |
| `0 < tasks.checked < tasks.total` | **implement** | `/wellforge:implement NNN-slug next` |
| `tasks.checked == tasks.total`, `rigor == mvp`, `verdicts.qe.verdict == PASS` | **verify** | `/wellforge:done NNN-slug` (mvp — no eval); or `/wellforge:promote NNN-slug --to production` |
| same, `verdicts.qe.verdict == FAIL` | **implement** | fix the defects, then re-run QE: `/wellforge:implement NNN-slug <tasks>` |
| same, `verdicts.qe.verdict == null` | **verify** | no QE verdict on record — run it: `/wellforge:implement NNN-slug` (its QE step), then `/wellforge:done NNN-slug`. Don't assume a missing verdict is a pass. |
| `tasks` complete, `rigor == production`, `!artifacts.eval_report` | **eval** | `/wellforge:eval NNN-slug` (LM-judge scored verdict) |
| `verdicts.eval.verdict == FAIL` | **eval** | fix the failing dimensions, then `/wellforge:eval NNN-slug` |
| `verdicts.eval.verdict == PASS`, `status != done` | **verify** | `/wellforge:done NNN-slug` |
| `status == done` | **done** | — complete |
| `status == superseded` | **retired** | — replaced by `superseded_by:`; nothing to do (flag it only if that feature doesn't exist) |
| `status == archived` | **retired** | — stopped on purpose (`archive_reason:`); nothing to do |

Open questions are not in the envelope (they are prose) — read them from `spec.md` only for
a single-feature detail view, and append "(N open questions block approval)".
If `drift.drifted`, flag "⚠ tasks may be stale —
re-run `/wellforge:tasks NNN-slug`" regardless of the row.

**Staleness nag (lower tiers are debt).** For a feature at `rigor: spike` or `mvp` whose
`created:` is more than ~30 days ago, append "⏳ <tier> for Nd — promote (`/wellforge:promote`)
or archive". A long-lived spike/mvp is unpaid debt; surface it, don't judge it.

## Output

All-features (default) — one line per feature, ordered by NNN:

```
WellForge · feature status

NNN-slug       tier        phase       progress          → next
001-user-auth  production  implement   tasks 3/8         → /wellforge:implement 001-user-auth next
002-csv-export production  plan        plan draft        → review & approve the plan
003-audit-log  production  spec        draft (2 open q)  → /wellforge:spec 003-audit-log
004-billing    production  done        ✓                 → —
005-pricing    spike       spike ✓     built             → /wellforge:promote 005-pricing --to mvp
006-search     mvp         done        tasks 6/6         → set done (mvp); or promote --to production
```

Tier column: the feature's `rigor` (omit/blank it for the common `production` case if you
prefer a tighter table, but always show non-`production` tiers). Progress column: spec/plan
phases show the status word; implement shows `tasks X/Y`; spike shows built/in-progress;
done shows ✓. Keep it a clean aligned table; no narrative per row.

Single-feature (a feature token was given) — the same line, then expand: open questions,
the task checklist with checked/unchecked state and the next ready task highlighted, and
any drift warning. Still read-only.

End with a one-line summary: counts per phase (e.g. "1 done · 1 implementing · 1 planning
· 1 drafting") so the overall project state is visible at a glance.

## Observability (when `.forge/runs/` exists)

Two scripts, two questions — keep them apart. `forge-state.py` answers *what state is each
feature in* (the section above); `run-report.py` answers *what happened in each run*:
trajectory, tokens, cost, agent-reported drift. Neither subsumes the other, and merging them
would put per-run cost into a per-feature envelope.

If the project has run traces, append a short **Runs** section from the report script:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run-report.py --json [--feature <slug>]
```

It returns `{"runs": [...], "unattributed_events": N, "cost_estimated": bool}`; each entry
in `runs` has `command`, `result`, `agents`, `verdicts`, `input_tokens`, `output_tokens`,
`est_cost_usd`, `drift_open`, `terse`. When `cost_estimated` is false the pricing table
could not be read — show tokens without a cost rather than a zero. Render each run as: the agent
trajectory (`a → b → c`), the verdicts, and any open drift. **These are exact.**

**Terse savings.** When a run's JSON has `terse: true` AND it also
carries `output_tokens_saved` / `pct_saved` / `control_run_id` (run-report.py only adds these
three when it found a comparable non-terse control run — see its `find_control` pairing
heuristic), append one line for that run:

```
terse saved ~<output_tokens_saved> output tok (~<pct_saved>%) vs control <control_run_id>
```

**Omit the line entirely** when a terse run's entry lacks those fields (no control paired
yet) — same omit-when-empty convention as the rest of this section; never print a
placeholder or a "no control found" line. This is **subagent output only** (Risk R1 in the
terse-mode plan) — never state or imply it measures the main loop's savings.

**Cost/tokens — do NOT present them as real cost.** WellForge captures only a fraction of
subagent tokens; it cannot see the main orchestrating loop or cache tokens, which dominate.
The figure is structurally a small under-count (often by 10×+). So:

- Show captured tokens only as `tok (partial)`, and the dollar figure only as a faint
  lower bound if at all — never as "the cost".
- End the section with: **"For real session cost run `/usage` (Claude Code) — WellForge's
  numbers are partial subagent tokens only."**
- The value of this section is the **audit trail** (who ran, verdicts, drift), not cost.
- Omit the whole section if there are no traces.

## Hard rules

- Read-only. Never edit specs, check boxes, or change status — this only reports.
- The "next step" comes from the table above, not judgment — same inputs, same output.
- A folder without `spec.md` is not a feature; ignore it silently.
