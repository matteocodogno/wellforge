# T9 — Measurement: terse-vs-control output reduction

**Task:** T9 (specs/001-terse-mode) — measure the ≥40% output-token reduction on agent-dispatched runs (AC-5.3).
**Date:** 2026-07-25. **Tier:** production.

## Method

A single, fixed, tool-free explanation prompt (WellForge's three rigor tiers + the security
floor) was dispatched to `general-purpose` subagents **6 times, strictly sequentially**, in the
order C1, T1, C2, T2, C3, T3:

- **Control (C1–C3):** the prompt alone.
- **Terse (T1–T3):** the exact terse cue from `skills/terse/SKILL.md` prepended, prompt otherwise identical.
- Every dispatch produced pure prose with **0 tool calls** (verified) so output volume is the answer text itself.
- Sequential + synchronous so each subagent's `.forge/runs/.events.jsonl` line is unambiguously attributable.

Two measures were taken per run: (a) the `output_tokens` recorded by the SubagentStop hook
(the run-trace telemetry T6/T7 rely on), and (b) the **actual answer length** (characters/words)
extracted from each subagent transcript — a faithful, cache-independent proxy for output volume.

## Result — reliable measure (answer length)

| Pair | Control chars | Terse chars | Reduction | (words) |
|---|---|---|---|---|
| C1→T1 | 5629 | 3038 | **46.0%** | 44.9% |
| C2→T2 | 4354 | 3051 | **29.9%** | 33.1% |
| C3→T3 | 5485 | 3280 | **40.2%** | 44.8% |
| | | **median** | **40.2%** | 44.8% |
| | | mean | 38.7% | 40.9% |

**Verdict: AC-5.3 MET (marginally).** Median output reduction = **40.2%** (char) / **44.8%** (word),
both ≥ 40%. Caveats, stated honestly:
- **Marginal.** The mean (38.7% char) is below 40%; one pair (C2→T2) was 29.9%. A slightly
  different sample could dip the median under 40%.
- **Best-case task.** This is a prose-heavy explanation — terse's strongest surface. Mixed
  code/prose tasks will reduce less (the byte-identical invariant preserves all code/commands
  verbatim, so their tokens don't compress).
- **Small N (3 pairs).** Indicative, not a tight confidence interval.

## Finding — the run-trace token telemetry is NOT a usable measurement instrument

The SubagentStop hook's `output_tokens` for the same 6 runs (dispatch order):

| Run | hook output_tokens | actual answer chars |
|---|---|---|
| C1 | 1348 | 5629 |
| T1 | 473 | 3038 |
| C2 | **333** | 4354 |
| T2 | 401 | 3051 |
| C3 | **416** | 5485 |
| T3 | 410 | 3280 |

C2 and C3 are among the **longest** answers yet report the **lowest** token counts — the hook
captured C1/T1 roughly, then under-counted every subsequent run (almost certainly prompt-cache
effects on the repeated identical prompt: the hook sees only a fraction of usage). Pairing on
these numbers gives nonsense (C2→T2 = "+20%", i.e. terse "larger"). This **empirically confirms
Risk R1** and the observability skill's own honest-limits note ("captures only a fraction …
~10–20× under real `/usage` … an audit trail, not a cost meter").

**Consequence:** AC-5.1 / AC-5.3 as written ("the run-trace records the metric" / measured from
run-trace output-token totals) rest on an instrument that is too noisy to trust for the ≥40%
gate. The measurement above therefore uses **actual output length**, not the hook. T6/T7's
run-trace `terse`/`pct_saved` fields remain useful as a **rough indicator**, but must not be the
authoritative gate.

**Recommended spec amendment (drift, for user decision):** make the *authoritative* measure for
AC-5.1/5.3 **output length (chars/words) and/or `/usage`**, and demote the run-trace token delta
to indicative-only. See the review note accompanying this task.

## Reproduction

Prompts, dispatch order, and the extraction (final-assistant-text length per transcript) are
recorded in this run's session; `.events.jsonl` lines 29–34 hold the (unreliable) hook numbers.
