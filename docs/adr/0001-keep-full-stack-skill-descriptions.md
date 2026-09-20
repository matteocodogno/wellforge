# 0001 — Keep Full, Trigger-Phrase-Rich Descriptions on the Five Stack Skills

**Date:** 2026-09-20
**Status:** Accepted
**Deciders:** WellForge plugin maintainers
**Project:** wellforge-plugin

---

## Context

Claude Code injects every skill/command/agent `description` into every session prompt in
every project where the plugin is enabled at user scope — including repos that have nothing
to do with WellForge. Bodies load lazily; descriptions do not. A `terse-compress`
fact-preservation pass already cut the ten largest descriptions, taking total session
injection from 20,351 to 19,540 chars (~5,088 → ~4,885 est. tokens, measured by
`wellforge-plugin/scripts/check-budget.py`). The five stack skills
(`hono-ts-backend`, `kotlin-springboot`, `react-ts-vite`, `pulumi-gcp-ts`, `mise`) remain the
largest un-compressed group: 3,288 chars (~822 tokens, 17% of the total), almost entirely
quoted trigger phrases (react-ts-vite 12, pulumi-gcp-ts 8, hono-ts-backend 7,
kotlin-springboot 5, mise 5) plus load-bearing disambiguation clauses added after real
mis-routing across the JVM/TypeScript boundary (e.g. `hono-ts-backend`: "FIRST confirm the
target stack — for a JVM / Spring Boot / Kotlin service use springboot-scaffold instead; this
skill is TypeScript-only"; `pulumi-gcp-ts`: it is infrastructure, not an application backend).
There is no eval suite in this repo for skill-trigger accuracy, so the token cost of keeping
these descriptions is measurable and certain, while the mis-routing cost of shortening them is
real but currently unmeasurable.

## Decision

We will keep the five stack skills' descriptions at their current length, with their full set
of quoted trigger phrases and disambiguation clauses intact, rather than reducing them to
one-liners that defer routing decisions to the skill body.

## Failure shape

**The failure this avoids:** collapsing a description down to a short label removes exactly
the text a *selection* decision depends on, while leaving the *content* that description was
protecting untouched and seemingly fine. The body of a skill is not read until the skill has
already been chosen — so any trigger information moved out of the description and into the
body stops functioning as a trigger; it just becomes documentation nobody consults before the
decision it needed to inform. The mistake is optimizing a cost that is visible (chars/tokens
injected every session) against a cost that is invisible today (a wrong or missing skill
selection), when nothing in the repo turns the second cost into a number. That asymmetry — one
side measured, ratcheted, and CI-enforced; the other side real but silent — is what makes the
shortening look free when it is not.

This shape recurs anywhere a system carries two representations of the same capability at
different granularities and only one of them is consulted before a branch is taken: a search
index entry vs. the document it points to (truncate the index entry and matching queries stop
finding the document, even though the document is unchanged); a function's docstring summary
vs. its full signature in an IDE's autocomplete-ranking pass; an API gateway's route-matching
prefix vs. the full route definition; a cache key vs. the value it should distinguish. In every
case, ask: *is the short form read at decision time, or only the long form — and if I shrink
the short form, does the decision it feeds get worse in a way nothing here would catch?* If the
answer is "the decision gets worse and nothing measures it," that is this failure, regardless
of what the two representations are called locally.

## Options considered

### Option A — Keep full descriptions (chosen)
Leave the five stack skills as-is: complete trigger-phrase lists and disambiguation clauses in
the description field.

**Pros:**
- Preserves the exact text the JVM/TypeScript disambiguation clauses were added to fix, after
  real mis-routing incidents.
- No change in routing behavior — nothing to re-validate.
- Keeps the (unmeasured but real) mis-routing risk at its current, already-tolerable level.

**Cons:**
- Costs ~822 tokens per session in every project with the plugin installed at user scope, 17%
  of total injection, whether or not that project uses any of these five stacks.

### Option B — One-line descriptions deferring to the body
Shrink each description to a single line ("TypeScript backend framework — see body for
details") and move trigger phrases into the skill body.

**Pros:**
- Would cut ~822 tokens per session, the largest single reduction available.

**Cons:**
- Rejected: the body is not read until the skill is already selected, so moving trigger
  phrases into it deletes exactly the text selection depends on. Optimizes the measurable
  token cost at the expense of the unmeasurable routing cost — the asymmetry this ADR exists
  to name.

### Option C — Keep trigger phrases, cut the "Covers X, Y, Z" tails
Trim only the enumerative tails that don't carry trigger phrases or disambiguation clauses.

**Pros:**
- Real, safe reduction with no routing risk.

**Cons:**
- Already done — this is most of the -11% (20,351 → 19,540 chars) achieved across the ten
  largest descriptions before this ADR. The remaining length in the five stack skills is
  trigger phrases and disambiguation clauses; each further cut removes a real referent, not
  padding.

### Option D — Ship stack skills as a separate optional plugin
Move the five stack skills into an install-on-demand plugin so repos that never use a given
stack pay nothing for it.

**Pros:**
- Genuinely removes the cost for repos that don't need it, without touching trigger-phrase
  content.
- The correct long-term fix if the budget becomes painful.

**Cons:**
- Not chosen now: splits the install and the versioning story (two release cadences, two
  upgrade paths) for a ~822-token saving. Revisit first if the budget becomes a real problem.

### Option E — Gate skills behind a project marker
Load a stack skill only in repos matching some project marker (e.g. a `build.gradle.kts` or
`package.json` signature).

**Pros:**
- Would eliminate the injection cost entirely for non-matching repos.

**Cons:**
- No such conditional-loading mechanism exists in the Claude Code plugin format today. Not a
  currently available option.

## Consequences

**Positive:**
- Trigger-phrase coverage and the JVM/TypeScript disambiguation clauses stay intact; no
  re-introduction of the mis-routing failure they were added to fix.
- The decision is explicit and dated, not an accidental omission from the terse-compress pass.

**Negative / trade-offs:**
- WellForge costs ~4,885 estimated tokens per session everywhere the plugin is installed at
  user scope; ~822 of those tokens (17%) are stack-skill descriptions a given repo may never
  use. This is accepted deliberately, not overlooked.

**Risks:**
- The token budget could grow further if new stack skills are added without an equivalent
  trade-off discussion. Mitigated by a ratchet in `wellforge-plugin/config/budget.yml`
  (`max_chars: 19540`) that fails CI on any growth, so the number can only move by decision.
- The mis-routing risk this ADR protects against remains genuinely unmeasured. Revisit this
  decision if (a) a skill-trigger eval suite is built, turning routing cost from unmeasurable
  into measurable, or (b) the separate-plugin option (Option D) becomes cheap enough to adopt.

## Compliance notes

Not applicable — this decision has no data-protection, residency, or audit-trail impact.

---

*This ADR was generated during a WellForge spec-driven session. Review and amend before committing.*
