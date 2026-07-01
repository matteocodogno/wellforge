---
name: rigor-tiers
description: >
  WellForge rigor tiers — match ceremony to stakes. The spike / mvp / production vocabulary
  that governs how much of the pipeline runs (agents, approval gates, models, quality gates,
  eval) for a feature. Use whenever running /wellforge:spike, when /wellforge:orchestrate or
  /wellforge:implement is given a --mode, when reading a feature's `rigor:` frontmatter, or
  when deciding how strict gates should be. Authoritative reference for the three tiers, the
  non-negotiable security floor, advisory-gate behavior, and the rigor precedence rule.
---

# Rigor tiers — velocity vs. assurance

Full WellForge rigor (7 agents, 2 approval gates, frontier models, 80% coverage, LM-judge
eval) is right for production and wasteful for a feasibility spike that may be thrown away.
A **rigor tier** matches ceremony to stakes.

**Principle: don't lower the bar — defer it, explicitly and reversibly.** Lower rigor is a
*declared, recorded, promotable* lifecycle stage, never a silent corner-cut. A lower tier is
a tracked debt (the `rigor:` frontmatter), paid by `/wellforge:promote` when the work becomes
real. The failure mode this design exists to prevent: a spike silently becoming production.

## The three tiers

| Tier | Intent | Throwaway-ok? |
|---|---|---|
| `spike` | Feasibility / business-model experiment | Yes — expected |
| `mvp` | First real release to validate with users | No, but debt is acknowledged |
| `production` | Full rigor (the default everywhere today) | No |

## What each tier tunes

| Lever | `spike` | `mvp` | `production` |
|---|---|---|---|
| Pipeline depth | **main loop** builds from a brief; NO subagents | PO → tasks → dev agents → light QE (no separate architect/designer) | full 7-agent team |
| Human gates | 0 (autonomous; human reviews the result) | 1 (spec approval) | 2 (spec + plan) |
| Spec ceremony | one `brief.md` | `spec.md` + `tasks.md` (plan folded into tasks) | spec + plan + design + tasks |
| Models | inherits the session model (no per-agent routing) | mid agents only — frontier architect/evaluator are NOT spawned | full `model-routing.yml` |
| Quality gates | lint + typecheck + build, **advisory** | + smoke tests + SAST-high **blocking**; coverage advisory | full 80% coverage + SAST + eval |
| Eval (LM-judge) | off | off | on — the gate into `done` |
| Effort cue | minimal (bias to speed) | moderate (pragmatic) | full (deliberate) — see below |

`mvp` gets cheaper not by re-tiering agents (frontmatter `model:` is fixed per agent) but by
**composition** — it simply never spawns the frontier agents (architect, evaluator). See
`config/model-routing.yml`.

## Effort cue — how hard to think, gated by tier

Distinct from *which* model runs (routing) and *which* agents run (composition): the effort
cue is *how hard the chosen model deliberates*. It is **not** a per-agent config field (that
would break tool-neutrality) — it's a plain-text directive the dispatching command adds to
each agent's task prompt, derived from the resolved rigor tier. Tool-portable (just words),
zero new config. Most useful for agents that span tiers (PO, dev agents, QE) and for the
spike main loop; the frontier agents (architect, evaluator) run only at `production`, so
their effort is already "full".

Prepend the tier's cue to each dispatched agent's task (and, for `spike`, the main loop
applies it to itself):

- **`spike`** — "Effort: minimal. Take the shortest path that answers the question. No
  gold-plating, no exhaustive edge-case analysis; leave `// SPIKE:` where you cut a corner.
  Bias hard to speed."
- **`mvp`** — "Effort: moderate. Be pragmatic and correct on the main paths; cover the
  obvious error cases but NOTE deferred edge cases rather than solving them all now."
- **`production`** — "Effort: full. Reason carefully about trade-offs, edge/error/failure
  modes; verification is adversarial. Thoroughness over speed."

This is a nudge, not a hard budget — honest about the seam. Where a tool exposes a real
thinking-budget parameter, a future `model-tiers.yml`-style mapping could bind these levels to
it; until then the directive is the mechanism.

## Security floor — non-negotiable, ALL tiers (incl. spike)

These always run and always **block**, regardless of tier. Fast must never mean "leaks
credentials":

- **Secret scan** (gitleaks / equivalent) — no committed secrets.
- **No hardcoded credentials** in changed code.
- **Dependency audit on CRITICAL CVEs** — critical advisories block even a spike.

A tier may make coverage/lint/SAST-medium advisory; it may NEVER waive the floor.

## Advisory vs. blocking gates

Outside the security floor, lower tiers **run** the gates but report results as **advisory** —
the same mechanism as the brownfield ratchet baseline: measure, show the gap-to-target, do not
block. The numbers are still visible (so the debt is honest); they just don't fail the run.

- `spike`: lint/typecheck/build advisory. Report failures; don't stop on them.
- `mvp`: SAST-high blocks; coverage is advisory (reported with gap-to-80%); lint/typecheck block.
- `production`: everything blocks (today's behavior).

## `rigor:` frontmatter & precedence

A feature records its tier in its `spec.md`/`brief.md` frontmatter: `rigor: spike|mvp|production`.
Absent ⇒ `production` (safe default — full rigor unless explicitly relaxed).

Resolution precedence, highest wins:

1. **Invocation** — `--mode <tier>` on the command.
2. **Feature** — the `rigor:` frontmatter of the feature being worked.
3. **Project default** — `.forge/manifest.json` `rigor` (set at scaffold time; Phase B).

State the resolved tier before acting, and why (which level supplied it).

## Graduation

A lower tier is debt, not a destination. `/wellforge:promote <feature> --to mvp|production`
(or `--project --to …` for the scaffold default) raises the tier and pays the deferred rigor:
brief → spec → retro plan, backfill tests to the coverage floor, flip advisory gates to
blocking, and run the eval. Production rigor is reached ONLY through promote, and only on an
eval PASS — never implicitly. Promotion only RAISES; a tier is never lowered via promote.

## Visibility (the guardrail)

A lower tier must never be mistaken for production-grade. Always:

- Print the resolved tier at the start of a run.
- For `spike`/`mvp`, end with a one-line reminder that gates were advisory and the work is
  unpromoted (e.g. "rigor: spike — gates advisory, not production-ready; `/wellforge:promote`
  to graduate").
