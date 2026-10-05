---
name: tdd
description: >
  WellForge test-first discipline — red, green, refactor, one behavior at a time. Use when
  a dev agent implements a task at the mvp or production tier, or makes a QE reproduction
  test pass. Off at the spike tier.
---

# Test-driven development — the test exists before the code that passes it

"Tests are part of the task" was the whole rule, and it said nothing about *when*. A test
written after the code is shaped by the code: it asserts what the implementation does, not
what the AC asks for, and it has never once been seen to fail. That is where the two
defects WellForge already pays reviewers to find come from — the **test that cannot fail**
([`self-critique`](../self-critique/SKILL.md), code checklist) and the AC with no covering test that QE writes
after the fact.

Test-first removes both at the source. **A test you watched fail for the right reason is a
test that can fail.** Everything below is that one sentence, made operational.

## The loop

One behavior per turn of the loop. Never two.

1. **Pick one behavior.** It comes from the task, not from your imagination: an AC the task
   references, a row of plan.md's `## Test strategy`, an error case in the contract, the
   `done when:` check. Say which.
2. **Red.** Write one test for it, through the public interface. Run it. Watch it fail —
   and check *why* (the right-red rule, below).
3. **Green.** Write the least code that makes that test pass. Run it and its neighbours.
4. **Refactor.** Only on green, behavior unchanged, tests untouched. A test that has to
   change during a refactor was testing the implementation — that is a finding about the
   test.
5. Next behavior.

**Work outside-in.** When the task's `done when:` is itself a test ("integration test X
passes"), write it first and leave it red: it is the outer loop, and the inner cycles are
what turn it green. It tells you when the task is finished, which the inner tests cannot.

## The rules

1. **One behavior at a time — never all the tests, then all the code.** Tests written in
   bulk describe a design you have not built yet, so they encode your guess about it, and
   by the time the code disagrees you have ten tests arguing for the guess. One cycle
   teaches the next.
2. **The red must be the right red.** A run that fails is not yet a red. Three outcomes:

   | You ran the new test and… | It means | Do |
   |---|---|---|
   | it fails on the assertion, as you predicted | the behavior is missing and the test sees that | go green |
   | it fails for another reason — import, typo, fixture, wiring, a 404 where you expected a 422 | the test is not yet testing the behavior | fix the **test** (or add the minimal stub so it compiles), re-run until the failure is the assertion |
   | it passes | either the behavior already exists, or the test cannot fail | find out which — break the behavior on purpose. If the test still passes, it is not a test: fix it. If it now fails, keep it, restore the code, and report it as **already-green** |

   In a compiled stack the first failure is usually the compiler. That is not the red —
   stub the symbol and get to an assertion failure before you implement.
3. **Through the public interface.** The endpoint, the exported function, the rendered
   component as a user reaches it. plan.md's contract *is* the interface: the shape and
   the error cases you assert are the ones written there, not the ones you find convenient.
   Mock only what is outside the system (outbound HTTP, the clock, a third-party SDK). The
   database is not outside the system — integration tests run against the project's real
   test database, as the stack skill describes.
4. **Never edit a test to reach green.** If the test is wrong against the AC, fix it and
   say so. If the test is right and the AC or the contract is what cannot be satisfied,
   that is **drift** — stop and report it ([`spec-driven`](../spec-driven/SKILL.md)). Loosening an assertion,
   skipping the case or widening a matcher is the silent corner-cut the self-critique
   checklist exists to catch.
5. **Nothing red is committed.** The cycle lives in your working tree, not in history: the
   task still lands as its one `feat(<scope>): … (T<n>, specs/NNN)` commit, tests and code
   together, green.

## When it runs — tier-gated

| Tier | Test-first |
|---|---|
| `spike` | **off.** The tier's point is the shortest path to an answer, and its gates do not run tests at all. Promotion pays this back ([`rigor-tiers`](../rigor-tiers/SKILL.md)). |
| `mvp` | **on for the behaviors the ACs name** — domain logic, contract shapes, the error cases. Breadth beyond the ACs is not required; coverage is advisory at this tier. |
| `production` | **on, for every row of plan.md's test strategy** and every contract error case. |

The tier changes *how many* behaviors you drive, never the order inside a cycle: a test you
do write is written first.

## What is exempt

Test-first is for behavior. Some of what a task touches has none of its own:

- **Schema migrations** (Liquibase changelogs, Drizzle migrations) and **generated code**
  (jOOQ, OpenAPI clients, route trees) — never hand-edited, never unit-tested directly.
- **Wiring and configuration** — DI setup, route registration, build files, env plumbing.
- **Pure presentation** — theme tokens, spacing, static layout. A component's *states*
  (loading, empty, error, disabled) are behavior and are not exempt.

**Exempt means "not driven by its own test", never "untested".** A migration is proven by
the repository test that needs its column; wiring by the endpoint test that goes through
it. If nothing would fail were the exempt change wrong, a behavior is missing its test.

One more case: **you do not know the shape yet** — an unfamiliar library, an API you have
never called. Probe it, throwaway, to learn the shape. Then delete the probe and drive the
real code from a test. A probe that survives into the diff is untested code with a story.

## An expected red is not "something went red"

[`systematic-debugging`](../systematic-debugging/SKILL.md) fires the moment anything goes red. The red you just wrote
on purpose and predicted is not that moment — do not open a root-cause investigation for
it. Debugging starts when the loop stops behaving:

- the test fails for a reason you **cannot explain** (rule 2, second row, and the cause is
  not obvious), or
- **green will not come.** Each attempt at green on the same test counts toward the
  3-attempt stop. Three misses is not a harder test, it is a wrong design: stop and report
  drift, do not write a fourth implementation.

## Bug fixes — the red is handed to you

In the bugfix pipeline the `quality-engineer` owns reproduction: the smallest failing test,
committed alone. That test **is** your red. Do not write a second one beside it and do not
modify it — make it pass, then run the surrounding suite. If you believe the reproduction
is wrong, that goes back to the caller as a report, not into the test file.

## Reporting

One line in your return, next to the self-critique line:

```
TDD: 5 cycles (AC-1.1, AC-1.2 ×2, AC-2.1, done-when); 2 exempt (changelog 0007, jOOQ
regen); 1 already-green (AC-1.3 — existing behavior, kept as a regression test).
```

Name the behaviors, not just the count. A behavior you implemented **without** a test
first is reported as that — `1 test-after (AC-2.2 — why)` — never folded into the cycles.

## What this is NOT

- **Not evidence.** The line is your account of how you worked; nobody observed the red.
  QE and the evaluator judge the tests that exist — whether they would fail if the behavior
  broke — and never credit the claim that they were written first. This skill is
  prompt-authored with no runtime teeth, by design: a hook cannot tell a real cycle from a
  line describing one.
- **Not a coverage target.** Thresholds belong to the gates ([`quality-gates`](../quality-gates/SKILL.md)). Test-first
  produces tests that mean something; it does not promise a percentage, and a test added
  only to move the number is exactly the test this discipline does not produce.
- **Not a substitute for QE.** The AC sweep, the gates run and the exploratory pass happen
  exactly as before. The expected change is that QE finds fewer ACs with no covering test.
- **Not test-first for everything.** See the exemption list. Pretending a migration was
  "driven by a test" is noise in the report.

Related: [`self-critique`](../self-critique/SKILL.md) (the code checklist this feeds — a test that cannot fail),
[`systematic-debugging`](../systematic-debugging/SKILL.md) (unexpected red, and the attempt counter), [`rigor-tiers`](../rigor-tiers/SKILL.md) (the tier
gating), [`spec-driven`](../spec-driven/SKILL.md) (where the behaviors come from, and the drift rule),
[`quality-gates`](../quality-gates/SKILL.md) (who owns coverage).
