---
description: Recap every feature's position in the spec→plan→tasks→implement flow, with the next command to run
argument-hint: [feature] — omit for all features; or NNN-slug / slug / NNN for one in detail
---

Show where each feature stands in the spec-driven workflow and the exact next command to
run. Read-only — never modifies anything. Conventions: the **spec-driven** skill (load it).

Target: $ARGUMENTS  (a feature token → detail view for that one; empty → all features)

## Gather (read-only)

For every `specs/NNN-slug/` directory (or just the named one):
- `spec.md` frontmatter `status` (draft / approved / in-progress / done) and any
  unchecked `## Open questions`.
- `plan.md` present? its frontmatter `status` (draft / approved).
- `design.md` present? (informational only — not a gate.)
- `tasks.md` present? count `- [x]` vs total `- [ ]`/`- [x]` task lines; note the first
  unchecked task whose `deps:` are all checked ("next ready").
- `eval-report.md` present? its frontmatter `verdict` (PASS / FAIL) and `score`.

## Phase + next step — deterministic table

Evaluate top-down; first matching row wins. `NNN-slug` below is the feature's folder.

| Condition | Phase | Next step |
|---|---|---|
| no `spec.md` | (not a feature) | skip |
| spec `draft` | **spec** | review & approve the spec — refine with `/wellforge:spec NNN-slug` |
| spec `approved`, no `plan.md` | **plan** | `/wellforge:plan NNN-slug` |
| `plan.md` `draft` | **plan** | review & approve the plan |
| plan `approved`, no `tasks.md` | **tasks** | `/wellforge:tasks NNN-slug` |
| `tasks.md`, 0 checked | **implement** | `/wellforge:implement NNN-slug next` |
| `tasks.md`, some unchecked | **implement** | `/wellforge:implement NNN-slug next` |
| all tasks checked, no/ stale `eval-report.md` | **eval** | `/wellforge:eval NNN-slug` (LM-judge scored verdict) |
| `eval-report.md` `verdict: FAIL` | **eval** | fix the failing dimensions, then `/wellforge:eval NNN-slug` |
| `eval-report.md` `verdict: PASS`, spec ≠ `done` | **verify** | set spec `done` |
| spec `done` | **done** | — complete |

If spec is `draft` with open questions, append "(N open questions block approval)".
If `tasks.md` is older than `spec.md`/`plan.md` (drift), flag "⚠ tasks may be stale —
re-run `/wellforge:tasks NNN-slug`" regardless of the row.

## Output

All-features (default) — one line per feature, ordered by NNN:

```
WellForge · feature status

NNN-slug      phase       progress          → next
001-user-auth implement   tasks 3/8         → /wellforge:implement 001-user-auth next
002-csv-export plan        plan draft        → review & approve the plan
003-audit-log  spec        draft (2 open q)  → /wellforge:spec 003-audit-log
004-billing    done        ✓                 → —
```

Progress column: spec/plan phases show the status word; implement shows `tasks X/Y`;
done shows ✓. Keep it a clean aligned table; no narrative per row.

Single-feature (a feature token was given) — the same line, then expand: open questions,
the task checklist with checked/unchecked state and the next ready task highlighted, and
any drift warning. Still read-only.

End with a one-line summary: counts per phase (e.g. "1 done · 1 implementing · 1 planning
· 1 drafting") so the overall project state is visible at a glance.

## Observability (when `.forge/runs/` exists)

If the project has run traces, append a short **Runs** section. You MUST actually run the
report script — do not hand-render the cost from the JSON:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run-report.py --json [--feature <slug>]
```

It returns, per run: `command`, `result`, `agents`, `verdicts`, `input_tokens`,
`output_tokens`, `est_cost_usd`, `drift_open`. Render each run as: the agent trajectory
(`a → b → c`), verdicts, `input/output` tokens, and **the `est_cost_usd` value from the
script** (e.g. `~$0.10`). Label it an estimate, not billed.

- The script ALWAYS returns a cost (it has a built-in pricing fallback). So the cost is
  never unavailable — never write "cost n/a" or "no pricing config"; if `est_cost_usd` is
  present, show it. If you genuinely could not run the script, say "run-report unavailable",
  not "n/a".
- If the captured tokens look implausibly low (e.g. a few hundred input on a multi-agent
  run), note "(partial — token capture is best-effort)" — the trajectory/verdicts are
  exact, the token/cost figure is approximate.
- Omit the whole section if there are no traces.

## Hard rules

- Read-only. Never edit specs, check boxes, or change status — this only reports.
- The "next step" comes from the table above, not judgment — same inputs, same output.
- A folder without `spec.md` is not a feature; ignore it silently.
