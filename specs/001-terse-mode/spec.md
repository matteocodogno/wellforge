---
id: 001
slug: terse-mode
status: in-progress
rigor: production
created: 2026-07-16
approved: 2026-07-16
---

# Terse mode — token-efficient conversational output

## Problem
WellForge agents and the main loop produce verbose prose — explanations, status recaps,
and agent-to-agent handoff narration — that consumes output tokens without adding
substance. This is pure overhead in the fast lane (spike tier) and in long orchestrated
runs, where the connective chatter dwarfs the artifacts that actually matter. WellForge
already controls cost by model tier (`model-routing.yml`), but has no lever on verbosity.
An external tool (caveman) proves ~65% output-token savings are achievable by dropping
filler while keeping substance — but adopting it wholesale conflicts with WellForge's
reproducible, contract-driven design and risks corrupting the format-contracted artifacts
the evaluator scores. We want the savings on the right surfaces, natively owned, without
touching the artifacts.

## Constraints
_Decisions the user fixed during the interview — captured verbatim, not elaborated:_
- Activation: terse mode is **ON by default in the spike tier**; **opt-in via a `--terse`
  flag** on `/wellforge:orchestrate`, `/wellforge:implement`, and the main loop; **OFF in
  mvp/production** unless explicitly flagged.
- Compressible surfaces: conversational output, orchestration/handoff narration, and
  memory + MCP tool-description files. **Not** commit messages or PR/review text.
- Memory/tool-description compression is **one-way** (irreversible — no restore-to-original
  path is in scope).
- Main-loop activation is a **`/wellforge:terse` toggle** command.
- Target output-token reduction: **≥ 40%**.
- The measured token delta compares the terse run against a **measured non-terse control
  run**, recorded in the **run-trace** (`.forge/runs/`, per the observability skill) and
  surfaced to the user.
- The security floor and the artifact format contracts are unaffected by terse mode.

## User stories

### US-1: Terse by default in the spike fast lane
As a developer running a spike, I want terse output without asking for it, so that the
fast lane is also the cheap lane.
**Acceptance criteria:**
- AC-1.1: Given a `/wellforge:spike` run, when the agent produces conversational output,
  then that output is in terse form (fragments, no filler) with no flag required.
- AC-1.2: Given a spike run, when a code block, shell command, file path, or error message
  appears in the output, then it is reproduced byte-for-byte identical to its non-terse
  form (terseness never edits code/commands/paths/errors).

### US-2: Opt into terse for orchestrated and main-loop work
As a developer, I want to enable terse mode explicitly on non-spike work, so that I can
trade prose for tokens when I choose to.
**Acceptance criteria:**
- AC-2.1: Given `/wellforge:orchestrate` or `/wellforge:implement`, when I pass `--terse`,
  then conversational and orchestration-narration output for that run is terse.
- AC-2.2: Given the same commands without `--terse` and a `mvp` or `production` tier, when
  they run, then output is in the normal (verbose) form — terse mode is off by default
  outside spike.
- AC-2.3: Given a main-loop session, when I run the `/wellforge:terse` toggle, then subsequent
  conversational output is terse until I run `/wellforge:terse` again to turn it off.

### US-3: Contracted artifacts are never compressed
As a quality engineer / evaluator, I want spec/plan/tasks/design/ADR/eval artifacts to stay
verbose regardless of terse mode, so that fidelity and human/future-session readability are
preserved.
**Acceptance criteria:**
- AC-3.1: Given terse mode is active (spike or `--terse`), when any of `spec.md`, `plan.md`,
  `tasks.md`, `design.md`, an ADR, `eval.md`, or `eval-report.md` is written, then its
  content follows the full format contract with no terse compression applied.
- AC-3.2: Given terse mode is active, when the evaluator scores a feature, then spec-fidelity
  and code-conventions scores show no regression attributable to terse output (a terse run
  and a baseline run of the same feature score within the rubric's normal variance).

### US-4: Compress memory and tool-description input
As a developer, I want memory files and MCP tool descriptions optionally compressed, so that
recurring input-token cost drops across sessions.
**Acceptance criteria:**
- AC-4.1: Given terse mode with memory/tool-description compression enabled, when a
  **WellForge-owned** file (a memory file or a WellForge-authored skill/command/agent
  `description`) is compressed (a one-way transform), then the compressed form is smaller
  and a reader (human or agent) can still recover every fact present in the original — no
  fact is lost, only phrasing is shortened. _(Refinement, accepted 2026-07-21: third-party
  MCP-server tool descriptions are owned by their servers and out of reach without a runtime
  interceptor — see Non-goals; "tool description" here means the descriptions WellForge
  authors and owns.)_
- AC-4.2: Given a compressed memory or tool-description file, when it is consumed in a later
  session, then behavior that depended on it is unchanged from the uncompressed baseline.

### US-5: Savings are measured and visible
As a developer, I want the token savings recorded and surfaced, so that terse mode's value is
verifiable rather than assumed.
**Acceptance criteria:**
- AC-5.1: Given a terse **agent-dispatched** run (`/wellforge:orchestrate` or
  `/wellforge:implement --terse`), when it completes, then the run-trace records a token
  metric comparing the terse output against a measured non-terse control run of the same
  work. _(Refinement, accepted 2026-07-21: the token telemetry only captures subagent
  output, not the main loop — so spike and `/wellforge:terse` main-loop savings are real but observable
  only via `/usage`, not the run-trace. The mechanical measure is scoped to agent-dispatched
  surfaces.)_
- AC-5.2: Given completed terse runs, when I check status (or the designated stat surface),
  then the recorded token savings are shown.
- AC-5.3: Given a sample of terse **agent-dispatched** runs, when their recorded savings are
  aggregated, then the measured output-token reduction is **≥ 40%** versus the control runs.
  _(Refinement, accepted 2026-07-21: measured on agent-dispatched surfaces per AC-5.1.)_

## Non-goals
- Compressing contracted artifacts (spec/plan/tasks/design/ADR/eval) — always verbose (US-3).
- Terse commit messages or one-line PR/code-review feedback — deliberately excluded this pass
  (not selected in the interview); revisit as a follow-up feature if wanted.
- Vendoring caveman or any external tool, and any global `curl | bash` installer that mutates
  a machine-wide agent config — antithetical to WellForge's pinned, reproducible design.
- Changing model routing or tiers — verbosity is an orthogonal cost lever, out of scope here.
- Multilingual/language-preservation behavior — WellForge tooling is English-only internal.
- Weakening any quality gate, the security floor, or an approval gate to save tokens.
- Compressing third-party MCP-server tool descriptions (owned by their servers; would need a
  fragile runtime interceptor) — a separate, larger feature if ever wanted (Refinement R2).

## Open questions
_All resolved during the interview:_
- [x] Output-token reduction target: **≥ 40%** (AC-5.3).
- [x] Memory/tool-description compression is **one-way** (AC-4.1); the no-fact-loss guarantee
  mechanism is an implementation concern for the plan stage.
- [x] Main-loop activation: **`/wellforge:terse` toggle** (AC-2.3).
- [x] AC-5.1 baseline: a **measured non-terse control run**.
