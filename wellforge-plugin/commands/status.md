---
description: Recap every feature's position in the spec→plan→tasks→implement flow, with the next command to run
argument-hint: [feature] — omit for all features; or NNN-slug / slug / NNN for one in detail
---

Show where each feature stands in the spec-driven workflow and the exact next command to
run. Read-only — never modifies anything. Conventions: the **spec-driven** skill (load it).

Target: $ARGUMENTS  (a feature token → detail view for that one; empty → all features)

## Gather (read-only)

For every `specs/NNN-slug/` directory (or just the named one):
- **Rigor tier** — `rigor:` from `spec.md` or `brief.md` frontmatter (default `production`
  if absent). A `brief.md` with no `spec.md` is a **spike** feature (load the **rigor-tiers**
  skill). Note the feature's `created:`/`status:` for the staleness check below.
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
| `brief.md`, no `spec.md`, status ≠ `done` | **spike** | `/wellforge:spike NNN-slug` (build) |
| `brief.md`, no `spec.md`, status `done` | **spike ✓** | graduate: `/wellforge:promote NNN-slug --to mvp` (or archive) |
| no `spec.md` (and no `brief.md`) | (not a feature) | skip |
| spec `draft` | **spec** | review & approve the spec — refine with `/wellforge:spec NNN-slug` |
| spec `approved`, no `plan.md` (rigor `production`) | **plan** | `/wellforge:plan NNN-slug` |
| spec `approved`, no `tasks.md` (rigor `mvp`) | **tasks** | `/wellforge:tasks NNN-slug` |
| `plan.md` `draft` | **plan** | review & approve the plan |
| plan `approved`, no `tasks.md` | **tasks** | `/wellforge:tasks NNN-slug` |
| `tasks.md`, 0 checked | **implement** | `/wellforge:implement NNN-slug next` |
| `tasks.md`, some unchecked | **implement** | `/wellforge:implement NNN-slug next` |
| all tasks checked, rigor `mvp`, QE passed | **verify** | set spec `done` (mvp — no eval); or `/wellforge:promote NNN-slug --to production` |
| all tasks checked, rigor `production`, no/stale `eval-report.md` | **eval** | `/wellforge:eval NNN-slug` (LM-judge scored verdict) |
| `eval-report.md` `verdict: FAIL` | **eval** | fix the failing dimensions, then `/wellforge:eval NNN-slug` |
| `eval-report.md` `verdict: PASS`, spec ≠ `done` | **verify** | set spec `done` |
| spec `done` | **done** | — complete |

If spec is `draft` with open questions, append "(N open questions block approval)".
If `tasks.md` is older than `spec.md`/`plan.md` (drift), flag "⚠ tasks may be stale —
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

If the project has run traces, append a short **Runs** section from the report script:

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/run-report.py --json [--feature <slug>]
```

Per run it returns `command`, `result`, `agents`, `verdicts`, `input_tokens`,
`output_tokens`, `est_cost_usd`, `drift_open`. Render each run as: the agent trajectory
(`a → b → c`), the verdicts, and any open drift. **These are exact.**

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
