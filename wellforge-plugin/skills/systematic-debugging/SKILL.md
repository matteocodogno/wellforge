---
name: systematic-debugging
description: >
  WellForge debugging discipline — find the root cause before proposing a fix, and know when
  to stop fixing. Use the moment anything goes red: a failing test, a failing quality gate, a
  build or CI failure, a flaky test, unexpected runtime behavior, or a bug report — in the
  main loop, in a spike, or inside a dev agent whose own task tests fail. Load it BEFORE
  proposing or attempting a fix, not after the first one misses. Authoritative reference for
  the root-cause-first rule, the fix-attempt counter and the architecture stop, the
  never-make-the-symptom-disappear rule, and how a root cause is recorded and routed.
---

# Systematic debugging — root cause first, and a counter that stops you

Two failures are common enough to design against. **Symptom fixing**: the error goes away,
the cause doesn't, and it returns as a harder bug later. **Thrashing**: four plausible fixes
in a row, each one revealing a new problem somewhere else, because the design is wrong and
nobody said so out loud. This skill exists to stop both, cheaply.

**The iron law: no fix without a stated root cause.** State it — "X is the root cause because
Y" — before you edit. If you cannot state it, you are guessing, and a guess that happens to
work is still a guess you will pay for.

## When this applies

The bugfix pipeline in `/wellforge:orchestrate` is not the only place debugging happens; it
is the rarest. This skill applies wherever something goes red:

| Situation | Who is debugging |
|---|---|
| A quality gate goes red locally or in CI | main loop, or the agent that touched the code |
| A dev agent's own `done when:` check or tests fail | that dev agent, mid-task |
| QE hands back a defect (the bounded fix loop) | the owning dev agent |
| `/wellforge:orchestrate --pipeline bugfix` | QE reproduces, a dev agent fixes |
| A spike doesn't behave as expected | the main loop |

The iron law holds in **all** of them, including `spike`. What the rigor tier tunes is how
much you *instrument and document* — never whether you find the cause.

## Phase 1 — investigate before touching code

- **Read the error completely.** The whole stack trace, the whole gate output, the failing
  assertion's actual-vs-expected. Not the first line. Errors frequently contain the answer.
- **Reproduce it.** Exact command, exact conditions, every time. If it isn't reproducible,
  that is your first finding and gathering data is the task — not fixing.
- **Check what changed.** WellForge commits one task per commit
  (`feat(<scope>): <title> (T<n>, specs/NNN)`), so `git log --oneline` and a diff of the last
  green commit usually name the culprit in seconds. Do this before theorising.
- **Instrument the boundaries, once.** Our stacks are multi-component by construction
  (React → API → Drizzle/jOOQ → Postgres; mise task → CI gate → tool). When the failure could
  live in any of several layers, log what enters and what leaves **each** boundary, run once,
  and read the evidence to find *which* layer breaks. Then investigate that layer. One
  evidence run beats three speculative fixes.
- **Trace backwards to the source.** A bad value deep in a call stack is not where the bug
  is. Follow it up until you reach where it was created — fix there.

## Phase 2 — find the thing that works

WellForge codebases are templated, so a working sibling almost always exists: another route,
another repository, another module, another spec's implementation of the same pattern.

- Locate the closest working example and **diff it against the broken one**. List every
  difference, including the ones that "can't matter" — that's where it usually is.
- The stack skills are the reference implementation ([[kotlin-springboot]],
  [[hono-ts-backend]], [[react-ts-vite]], [[pulumi-gcp-ts]]). If the bug is in a pattern they
  cover, read the relevant reference **completely** before adapting it. Partial understanding
  of a pattern is how the bug got there.

## Phase 3 — one hypothesis, one change

- **State a single hypothesis** and put it in writing — the dev agent's return message, or
  your reply in the main loop. A hypothesis nobody can read isn't auditable, and this is the
  line the next person needs when your fix turns out to be wrong.
- **Test it with the smallest possible change.** One variable. Changing three things and
  getting green teaches you nothing about which one mattered.
- **If it's wrong, form a NEW hypothesis.** Do not layer a second fix on top of the first —
  revert it. Stacked speculative fixes are how a one-line bug becomes an afternoon.
- **"I don't understand X" is a valid, useful answer.** Say it and investigate rather than
  producing a confident fix you can't defend.

## Phase 4 — fix the cause, test first

The failing test comes before the fix, always. Don't restate the mechanics here — the
`quality-engineer` agent owns bug reproduction (smallest failing test, committed alone) and
is the right route whenever an agent pipeline is running. In the main loop or a spike you
write that test yourself, to the same standard: smallest reproduction, red before green.

Then: **one change, addressing the cause.** No "while I'm here" refactoring bundled in — it
contaminates the evidence about what actually fixed it. Verify the target test goes green
*and* the surrounding suite didn't break.

## The attempt counter — the part that stops thrashing

**Count your fix attempts on a given symptom, out loud.**

- **Attempt 1–2 fails** → return to Phase 1 with what you just learned. The new evidence is
  the point; don't re-run the same hypothesis harder.
- **3 attempts failed → STOP. Do not attempt a fourth.** Three failures is not bad luck, it's
  a signal: the architecture is wrong, not the hypothesis. The tell is that each fix reveals a
  new problem *somewhere else*, or that the "real" fix would need a large refactor.

What to do at the stop, per context:

- **In a spec'd feature** — this is **drift on `plan.md`**, and it routes exactly like any
  other drift ([[spec-driven]]): stop, report it to the caller, and let the architect amend
  the plan. A fourth patch is a dev agent quietly overruling the architecture.
- **In a spike** — this *is* the deliverable. A spike that discovers the design doesn't hold
  has answered its question; record it under `## Findings` and stop. Don't burn the spike's
  budget proving it three more times.
- **In the main loop** — say it to the user plainly, with the three attempts and what each
  revealed, before proposing anything structural.

**This composes with the bounded QE loop, it doesn't replace it.** `/wellforge:implement`
caps the QE↔dev fix cycle at 2 rounds; this counter caps attempts on a single symptom at 3.
Both apply; whichever trips first, stops the work.

## Never make the symptom disappear

The dev agents already forbid weakening lint/test/coverage config to go green. Debugging is
where that rule gets tested, so it extends:

- Don't raise a timeout to settle a flaky test — **wait on the condition**, not on a
  duration. An arbitrary sleep that passes today is a race that fails in CI.
- Don't add a retry around a failure you haven't explained. Retry is a legitimate design for a
  *known* transient; it is a silencer for everything else.
- Don't catch-and-log an exception to stop it propagating, don't `@Disabled` / `.skip` a red
  test, don't lower a gate threshold, don't add a null guard where the null shouldn't exist.

Every one of these destroys the evidence as well as hiding the bug. If a test itself is
genuinely wrong, that's a spec or plan question — route it, don't delete it.

## Red flags — you have stopped debugging and started guessing

"Quick fix now, investigate later" · "let me just try changing X" · "it's probably X" ·
"I don't fully understand this but it might work" · listing fixes before tracing the data ·
"one more attempt" after two failures · each fix breaking something new · reaching for a
timeout, a retry, or a skip.

Also treat these from the user as a hard stop: *"stop guessing"*, *"is that actually
happening?"*, *"will that even show us anything?"*, *"are we stuck?"* — each one means an
assumption went unverified. Return to Phase 1.

## Recording it

- A dev agent's return message states the **root cause**, not just the fix. "Fixed the failing
  test" is not a report.
- The QE verdict's `Defects:` list already carries repro steps and failing test paths; the
  root cause belongs there too, so the [[observability]] run trace and the evaluator's
  trajectory evidence show *why* it broke, not only that it went green.
- A root cause that turned out to be an architectural problem gets recorded where the
  architecture lives — an amended `plan.md`, or an ADR candidate if it constrains future work.

## When there really is no root cause

Occasionally investigation shows the cause is genuinely external, environmental, or
timing-dependent. Then: document what you ruled out, implement deliberate handling (a scoped
retry, a real timeout, an error message that helps the next person), and add the logging that
would catch it next time. That is a legitimate outcome of the process — but it is a
*conclusion*, not a starting assumption, and most of the time it means the investigation
stopped early.
