# Gap Analysis — WellForge vs. Google's "The New SDLC With Vibe Coding"

**Source:** *The New SDLC With Vibe Coding — From ad-hoc prompting to Agentic Engineering*,
Addy Osmani, Shubham Saboo, Sokratis Kartakis (Google, May 2026, 51 pp).
**Compared against:** WellForge as of this commit (plugin v2.0.0, templates v0.2.x, gates-v1).
**Date:** 2026-06-23.

This maps WellForge against the paper's frameworks, states where we already embody its
recommendations, and flags the real gaps — separating "should build" from "deliberately
out of scope."

---

## TL;DR verdict

WellForge sits squarely at the paper's **agentic-engineering** end of the spectrum and is,
almost line-for-line, an instance of its **factory model** and **harness engineering**.
That alignment is not accidental — both describe the same shift WellForge was built for.

The material gaps are concentrated in three areas the paper treats as first-class but
WellForge currently lacks:

1. **Evals & trajectory evaluation** (the non-deterministic verification half) — our
   biggest gap. We have tests + CI gates; we have no eval suites, rubrics, or LM-judges.
2. **Observability** — no token/cost metering, run traces, or agent-drift telemetry.
3. **Intelligent model routing** — no deliberate cheap-model-for-cheap-tasks economics.

Per the paper's own test ("without both [tests and evals], the practice is always vibe
coding"), closing gap #1 is what most strengthens WellForge's claim to be agentic
engineering rather than structured-AI-assisted coding.

---

## 1. The spectrum (paper Table 1) — where WellForge lands

| Dimension | Paper's "Agentic Engineering" | WellForge today | Verdict |
|---|---|---|---|
| Intent specification | Formal specs, arch docs, memory files | `specs/NNN/spec.md`+`plan.md`, `AGENTS.md` | ✅ matches |
| Verification | Automated test suites, **CI/CD gates, LM judges** | tests + CI gates ✅, **no LM judges/evals** ❌ | ◐ half |
| Codebase understanding | Comprehensive arch review; AI does impl | architect explores real code; human approval gates | ✅ matches |
| Error handling | Agents self-diagnose in bounds; humans do arch | QE fix loop (max 2), drift→human | ✅ matches |
| Scope | Production systems, team-scale | exactly the target | ✅ matches |
| Risk profile | Low; systematic verification every stage | gates + 2 human gates + QE | ✅ (modulo evals) |

**Finding:** WellForge is agentic-engineering on every axis **except verification**, where
it covers the deterministic half (tests) but not the non-deterministic half (evals).

## 2. Context engineering (paper §"the real skill")

The paper's six context types and the static/dynamic split:

| Paper concept | WellForge | Status |
|---|---|---|
| Instructions (role, boundaries) | agent prompts with explicit "must NOT" lists | ✅ strong |
| Knowledge (docs, arch) | stack skills + references/, plan.md, ADRs | ✅ |
| Memory (session + persistent) | spec files on disk = persistent; **no session memory** | ◐ |
| Examples (few-shot, ref patterns) | skill references show patterns | ✅ |
| Tools (precise defs) | `.mcp.json`, agent tool lists | ✅ |
| Guardrails (hard constraints) | 6 hooks (pre-bash-guard, stop-verify) | ✅ strong |
| **Static context** (always loaded) | `AGENTS.md` + `CLAUDE.md` import | ✅ exemplary |
| **Dynamic context** (on-demand skills) | `SKILL.md` + `references/` progressive disclosure | ✅ exemplary |

**Finding:** This is WellForge's **strongest** alignment. The paper holds up
`AGENTS.md`/skills/progressive-disclosure as the state of the art; WellForge already ships
exactly that (and we adopted `AGENTS.md` as canonical cross-tool context deliberately).
Minor gap: no persistent **session memory** across runs beyond the spec artifacts.

## 3. The factory model (paper §"building the system that builds software")

The paper's factory = specs/context + agents + tests/quality gates + feedback loops +
guardrails. This is a near-exact description of WellForge:

| Factory component | WellForge realization |
|---|---|
| Specifications & context | spec-driven workflow, `AGENTS.md` |
| Agents that translate specs → impl | 9-agent team + orchestrator/implement |
| Tests & quality gates | central reusable CI gates (pillar 5) |
| Feedback loops (failures → agents) | QE verdict → dev fix loop (bounded) |
| Guardrails | hooks + pre-bash-guard + drift enforcement |

**Finding:** WellForge **is** the factory model. "The developer's primary output is the
system that produces code" is literally WellForge's thesis. No gap — this is core strength.

## 4. Harness engineering (paper §"What surrounds the model")

The paper's six harness components, scored:

| Harness component | WellForge | Status |
|---|---|---|
| Instructions & rule files | AGENTS.md, skills, agent prompts | ✅ strong |
| Tools (functions, MCP) | sequential-thinking, playwright, github MCP | ✅ |
| Sandboxes / execution envs | mise toolchain, docker-compose; **no per-agent sandbox isolation** | ◐ |
| Orchestration logic | orchestrate/implement, DAG-parallel dispatch, handoffs | ✅ strong |
| Guardrails / Hooks | 6 lifecycle hooks (the paper's exact "block hard-coded password" example = our pre-bash-guard) | ✅ strong |
| **Observability** | **none** — no traces, cost/latency metering, drift telemetry | ❌ **gap** |

The paper's harness-in-SDLC mapping (configure → run → feedback → observe) lines up with
WellForge phases 1–3 strongly; **phase 4 "Observing the Harness" is where we're thin** —
we run hooks but have no observability layer.

> Paper: *"Most agent failures, examined honestly, are configuration failures."* WellForge's
> entire premise (reproducible harness config) is the antidote — but without observability
> we can't *prove* drift or measure it.

## 5. Conductor vs. Orchestrator (paper §"developer's evolving role")

WellForge is purpose-built for **orchestrator mode** (async, multi-agent delegation:
`/wellforge:orchestrate`, `:implement`, disk handoffs, parallel dispatch). It supplies
little for **conductor mode** (real-time inline pair-programming) — but that's Claude
Code's native surface, not WellForge's job. **By-design, not a gap.**

## 6. The 80% problem & testing (paper §§ 80% problem, Testing/QA)

- **80% problem** (AI does 80%, humans own the risky 20%): WellForge addresses this via 2
  human approval gates + QE verdict + bounded fix loops. ✅ partial — no explicit "this is
  the risky 20%" flagging, but the structure forces human judgment at the right points.
- **Output evaluation** (does it compile/pass): ✅ CI gates + QE.
- **Trajectory evaluation** (did the agent take the right steps/tools): ❌ **none**. The
  paper stresses this as equally necessary; WellForge never inspects *how* an agent worked.
- **Quality flywheel** (benchmark → cluster failures → optimize → regress → monitor prod):
  ◐ partial (QE fix loop + CI), no benchmark suite, no root-cause clustering, no prod monitoring.

## 7. Production-ready agents (paper §"Vibe Coding Production-ready Agents")

The paper's section on building agents *as products* (ADK, Agent Runtime, evalsets, A2A,
persistent memory) describes a **different product category** than WellForge. WellForge
scaffolds **web applications** (Spring Kotlin / Hono), not **AI agents as deliverables**.

**Deliberate scope boundary — not a gap today**, but worth a decision: if welld ever ships
AI-agent products, WellForge has no preset for that stack (no ADK template, no eval
scaffolding, no A2A wiring, no agent-runtime deploy). Flag for the roadmap, not the backlog.

## 8. Economics (paper §"The Economics of AI Development")

| Paper lever | WellForge | Status |
|---|---|---|
| High-CapEx/low-OpEx via upfront structure | the whole platform IS this investment | ✅ thesis-aligned |
| Context engineering as financial lever (dense AGENTS.md, high first-pass) | yes — tight AGENTS.md, skills | ✅ |
| Dynamic context via skills (pay tokens only when needed) | progressive-disclosure skills | ✅ |
| **Intelligent model routing** (cheap models for test-gen/review/CI; frontier for arch) | **none** — agents mostly inherit one model | ❌ **gap** |
| Token/cost metering | none (see Observability) | ❌ |

**Finding:** WellForge nails the *structural* economics but ignores the *runtime* token
economy. Two concrete misses: no model routing, no cost visibility.

---

## Prioritized gaps & recommendations

### P1 — Eval harness ✅ DONE (plugin v2.1.0, gates-v2)
The paper's load-bearing claim: tests verify the deterministic; **evals** verify the
non-deterministic (trajectory, tool choice, quality) via rubrics + LM judges.

Shipped:
- ☑ Central rubric `gates/configs/eval-rubric.yml` (weighted dimensions: AC satisfaction,
  spec fidelity, test quality, code quality, trajectory; per-dimension floors; pass ≥ 80).
  PR-governed like a threshold; per-feature `eval.md` may add dims / raise floors only.
- ☑ `evaluator` LM-judge agent (adversarial, evidence-cited) — distinct from QE
  (deterministic). Writes `specs/NNN/eval-report.md`.
- ☑ `/wellforge:eval <feature>` command; **a passing eval is now the gate into `done`**
  (wired through spec-driven lifecycle, status, implement, orchestrate).
- ☑ Opt-in CI gate: `quality-eval.yml@gates-v2` + `gates/scripts/run-eval.py`
  (Anthropic API; gating logic tested offline: pass / fail-by-total / fail-by-floor).
- ◐ Trajectory dimension is partial pending P2 observability (scores neutral when blind,
  per the rubric note — honest, doesn't fake trajectory evidence).

### P2 — Observability layer
- Capture per-run **traces** of agent dispatch (which agent, which tasks, outcome) — the
  orchestrator already has the data on disk; persist it to `.forge/runs/`.
- **Token/cost & latency metering** per agent run; surface in `/wellforge:status`.
- **Drift telemetry** beyond the binary stop-verify check: record when/where agents
  deviated, for audit.

### P3 — Intelligent model routing
- Annotate agents with a complexity tier; route deterministic work (test-gen, lint-fix,
  CI-monitoring, status) to a cheaper/faster model, frontier models for architect/plan.
- The agent frontmatter already supports a `model:` field (adr-writer uses it) — make it a
  deliberate, documented routing policy, not ad-hoc.

### P4 — Strengthen the quality flywheel
- A small **benchmark/regression eval suite** that compounds across features.
- Wire production signals back (the paper's "monitor prod for new failure modes") — at
  least capture post-deploy issues into the spec/eval loop.

### P5 — Decide on the production-agent category (roadmap, not backlog)
- If welld will build AI-agent products, plan an `agent-*` preset (ADK or equivalent) with
  eval scaffolding, A2A, and agent-runtime deploy. If not, document the boundary.

---

## Where WellForge already exemplifies the paper's "Where to start"

The paper's recommendations that WellForge **already implements** (useful to know we're not
behind on these):

**Individual devs:** ✅ AGENTS.md per project (templates ship it) · ✅ tests-as-contract
(AC→test mapping) · ✅ review-everything posture (human gates, QE, owasp).
**Leaders:** ✅ context engineering as first-class, PR-reviewed, versioned (gates/AGENTS.md
via PR) · ✅ harness as shared team asset (the entire reusable plugin+gates) · ✅
prototype-vs-production distinction (vibe vs the gated workflow).
**Orgs:** ✅ AI dev as engineering investment (the 6 pillars) · ✅ MCP as open standard ·
✅ hybrid human+agent handoff protocols (disk handoffs, approval gates).

Paper recommendations WellForge **does not yet** meet: "set the bar at the eval, not the
demo" (P1), "traces of every agent run" (P2), "intelligent model routing" (P3), A2A
adoption (P5), production-substrate evals-in-CI (P1/P4).

---

## One-line summary

> WellForge is a faithful implementation of the paper's **factory model + harness
> engineering + context engineering**, lagging mainly on the **verification-by-eval,
> observability, and token-economy** dimensions the paper treats as what separates durable
> agentic engineering from sophisticated vibe coding. Closing the eval gap (P1) is the
> highest-leverage next investment.
