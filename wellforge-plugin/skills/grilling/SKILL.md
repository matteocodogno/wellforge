---
name: grilling
description: >
  WellForge grilling — the one-question-at-a-time interview that walks an idea, spec or plan
  down its decision tree. Used by /wellforge:grill-me and /wellforge:spec --grill. Main
  loop only, never in a subagent.
---

# Grilling — every load-bearing decision made out loud, by the person who owns it

The default WellForge interview is deliberately cheap: batched questions, two rounds at
most (`/wellforge:spec`, `/wellforge:new`). It closes the gaps the author *noticed*. What it
cannot do is follow an answer — and the expensive defects start exactly there: the second
question that only exists because of how the first was answered, and the gap nobody asked
about that the author then filled with a guess phrased as a fact
([`self-critique`](../self-critique/SKILL.md): *assumption smuggled in*).

Grilling is the other mode. **One question at a time, in dependency order, each with a
recommendation, until no remaining question could change the artifact.** It spends the
human's attention to buy decisions that are actually theirs, so it is opt-in: the user asks
for it (`/wellforge:grill-me`, `/wellforge:spec --grill`), nothing turns it on by itself.

## The rules

1. **Read before you ask.** A question the repository can answer is not a question for the
   user. Neighbouring `specs/`, the ADR index in `AGENTS.md`, `CLAUDE.md`, the glossary, the
   code the idea touches — read them first, and report what you learned as a **finding**
   ("orders already carry a `tenant_id`; I am taking multi-tenancy as given"). The user
   corrects a wrong finding in one word; they should never have to dictate what is on disk.
2. **Map the tree before the first question.** Name the branches — the decisions this idea
   forces — and which depend on which. Show it in a few lines. It tells the user how much
   is coming, and it is what "done" is measured against.
3. **One question at a time.** Never a batch. Each answer prunes or reshapes what follows,
   and a batch asks questions the previous answer would have deleted.
4. **Parents before children.** Ask the decision other decisions hang on first. A leaf
   asked under an unresolved parent gets answered twice, or answered for a branch that is
   about to disappear.
5. **Every question carries your recommendation, and why.** Not a neutral menu: say which
   answer you would pick, the reason, and what gets more expensive if it turns out wrong.
   Use AskUserQuestion with the recommended option first when the answers can be
   enumerated; ask in plain text when they cannot.
6. **Only load-bearing questions.** The test: would the two most likely answers produce a
   different artifact — a different AC, non-goal, contract or task? If not, do not ask.
   Decide, and record it as an assumption the user can strike.
7. **Do not accept a non-answer.** "Fast", "the usual", "whatever is standard" gets one
   follow-up asking for the observable version. An answer that contradicts an earlier one,
   an ADR, or the code is said so at once, with both sides quoted — never smoothed over,
   never silently reconciled in favour of whichever came last.
8. **Stay on the artifact's side of the line.** Grilling a spec is about the WHAT and WHY:
   a technical decision the user volunteers is recorded verbatim as a constraint, not
   explored. Grilling a plan is about the HOW, and a question that reopens the WHAT is
   drift on the spec ([`spec-driven`](../spec-driven/SKILL.md)) — say so, do not relitigate it inside the plan.

Relentless is about substance, not tone. Push on a vague answer; never on the person.

## When it stops

- **The tree is resolved** — every branch on the map is closed, or
- **nothing left is load-bearing** — every remaining question fails rule 6, or
- **the user says stop.** Immediately, and without a parting question. Whatever is
  unresolved is listed as open, never guessed to make the ledger look finished.

There is no question cap, so the cost stays visible instead: each time a branch closes,
say so and say how many remain ("scope closed — 2 branches left: failure handling,
permissions"). Every five closed decisions, restate the ledger so far in full — a long
interview is exactly the session that gets compacted, and decisions that exist only in
scrollback are decisions that will be re-asked.

## The decision ledger

The output of a grilling session, and the only thing a later command should read from it:

```
## Decision ledger — <topic>
Decided (the user chose):
- D1 <decision> — <the reason they gave>
Delegated (the user deferred to the recommendation):
- D4 <decision> — recommended because <reason>
Found (read from the repo, not asked):
- F1 <fact> — <path>
Assumed (not load-bearing; strike any that is wrong):
- A1 <assumption>
Open (unresolved — each needs an owner):
- O1 <question> — owner: <who>
```

With `--docs` ([`domain-modeling`](../domain-modeling/SKILL.md)) the ledger gains two sections, and they are the
only ones that describe something already written or about to be:

```
Terms (written to the glossary during the session):
- T1 **<term>** — <definition> [(delegated)]
ADR candidates (a decision with a rejected alternative — offered, not yet written):
- R1 <decision> — rejected: <alternative>
```

**Decided and Delegated are different, and the difference is the point.** "You pick" is an
honest answer, and it is not the same as the user having an opinion. A delegated decision
is the first place to look when the feature turns out wrong, so it is never recorded as the
user's choice.

Where the ledger goes is the calling command's business: `/wellforge:spec --grill` writes
the spec from it (Open → `## Open questions`, constraints verbatim under `## Constraints`);
`/wellforge:grill-me` prints it and proposes the next command.

## Grilling with docs

Plain grilling reads the glossary and the ADR index and leaves them as it found them. With
`--docs` the session also **maintains** them, per the [`domain-modeling`](../domain-modeling/SKILL.md) skill:

- **Language is challenged as it is used.** The user says a word the glossary defines
  differently, or uses two words for what looks like one concept: that is the next
  question, asked at once, with both usages quoted.
- **A new term is stress-tested before it is written** — the boundary, identity,
  cardinality, time and absence probes. A scenario the definition cannot answer is the
  next question, not a gap you close yourself.
- **The glossary is written as each term resolves**, not at the end, so it survives a
  session that is cut short.
- **Decisions with a rejected alternative are collected as ADR candidates** and offered to
  the `adr-writer` agent when the session closes. Never written inline.

The eight rules and the stop conditions are unchanged; `--docs` adds what is written, not
how questions are asked.

## Where it does not run

- **Never in a subagent.** Agents cannot reach the user, so a "grilling" agent would be
  answering its own questions. The product-owner and architect return their open questions
  to the caller, as before.
- **Never in `/wellforge:orchestrate`**, which batches open questions into one round by
  design — an orchestrated run that stops to interview is no longer orchestrated.
- **Not at the `spike` tier.** A spike prefers a recorded assumption to a question
  ([`rigor-tiers`](../rigor-tiers/SKILL.md)). A user may still run `/wellforge:grill-me` before a spike; nothing
  in the spike itself starts one.

## What this is NOT

- **Not approval.** A fully grilled spec is still `status: draft`. The ledger sets no
  status and checks no box; the human gate that follows runs exactly as before.
- **Not a substitute for self-critique or review.** It removes unasked questions. It does
  not catch an unverifiable AC written from a perfectly good answer.
- **Not design by interrogation.** You bring a recommendation to every question (rule 5).
  An interviewer with no opinion has moved the whole job onto the user.
- **Not a way to edit an approved artifact.** Grilling something already approved produces
  proposed amendments, routed like any other drift.

Related: [`spec-driven`](../spec-driven/SKILL.md) (the artifacts, the WHAT/HOW line and the drift rule),
[`self-critique`](../self-critique/SKILL.md) (the smuggled-assumption failure this prevents upstream), [`rigor-tiers`](../rigor-tiers/SKILL.md)
(why a spike does not interview), [`domain-modeling`](../domain-modeling/SKILL.md) (what `--docs` maintains).
