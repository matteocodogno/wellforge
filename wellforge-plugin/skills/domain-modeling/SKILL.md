---
name: domain-modeling
description: >
  WellForge domain modeling — the project glossary (.claude/context/glossary.md): one term
  per concept, stress-tested against edge cases. Use when a spec, plan or grilling session
  introduces, renames or contradicts a domain term, and for /wellforge:grill-me --docs.
---

# Domain modeling — one word per concept, and a definition that survives its edge cases

Every WellForge artifact is written in the project's domain language, by a different
author each time: the product-owner names a concept in an AC, the architect names its
table, a dev agent names its type, QE names its test. Nothing made those four names the
same. When they differ, nobody is wrong and the cost is invisible — until a reader has to
work out whether a *client*, a *customer* and an *account* are one thing or three.

The glossary is where that is decided, once. **One word per concept, one concept per word,
and a definition precise enough to answer the awkward cases.** This skill is the authority
for the file, the rules for a term, and the stress test that sharpens one.

## The file

`.claude/context/glossary.md`, at the project root. It is **injected into every session**
by the session-start hook, which is why it works and why it must stay small.

```markdown
# Domain glossary

## Terms
- **Order**: a customer's confirmed request to buy; exists from checkout confirmation
  onward. _Avoid:_ purchase, basket.
- **Basket**: the unconfirmed selection that precedes an Order. _Avoid:_ cart.

## Relationships
- A **Basket** becomes at most one **Order**; an **Order** has one or more **Order lines**.

## Open ambiguities
- "account" is used for both **Customer** and **Billing account** — owner: PO.
```

- A flat list of `- **term**: definition` lines with no sections is a valid glossary (it
  is the format projects already have). Add `## Relationships` and `## Open ambiguities`
  the first time you need them; never restructure a working file for its own sake.
- **Create it lazily** — the first time a term is actually resolved. An empty glossary
  scaffolded "for later" is a file people learn to ignore.
- One or two lines per term. It is paid for in every session: a glossary that has outgrown
  a screen or two is carrying things that are not domain terms.

## The rules for a term

1. **One word per concept.** Pick the canonical term and list the others under `_Avoid:_`.
   A synonym left unlisted will be back in the next spec.
2. **One concept per word.** A word doing two jobs is two terms that need two names
   (**Customer** / **Billing account**). Until that is decided, it lives under
   `## Open ambiguities` with an owner — not in `## Terms` with a definition that hedges.
3. **Say what it is, and where it begins and ends.** A definition is a sentence that
   distinguishes the thing from its neighbours and states its lifecycle boundary ("exists
   from checkout confirmation onward"). Not what it is used for, not how it is stored.
4. **Domain terms only.** Words the business would recognise. `repository`, `DTO`,
   `handler`, a table name, a library — those are implementation and belong in the plan,
   the stack skill or an ADR.
5. **The code is evidence, and it can lose.** Before proposing a term, look for what the
   code already calls the concept. If it agrees, that is a finding. If the code says
   `Client` and everyone says *customer*, that is a **conflict to put to the user**: either
   the glossary follows the code, or the rename is real work — a task, never a quiet edit
   and never a glossary that describes a codebase that does not exist.
6. **Project language beats textbook language.** If the team's word is unusual but
   consistent, it wins. The glossary records how this project speaks.

## The stress test

A definition is cheap to write and is usually wrong at the edges. Before a new or changed
term is written down, run it against concrete scenarios — real ones, with made-up names and
numbers, not abstractions. Five probes; use the ones that bite:

| Probe | The scenario to invent | It exposes |
|---|---|---|
| **Boundary** | the moment just before it becomes an X, and just after it stops being one | a missing lifecycle ("is a cancelled Order still an Order?") |
| **Identity** | two things that look the same — are they one X or two? | what actually identifies it ("same items, re-submitted: same Order?") |
| **Cardinality** | zero of them, and two where you assumed one | a hidden one-to-many ("can a Basket become two Orders?") |
| **Time** | it changes after something else already depended on it | history and versioning ("the price changes after the Order is placed") |
| **Absence** | it exists without the thing you assumed it always has | optional relationships ("an Order with no Customer — guest checkout?") |

A scenario the definition answers leaves it alone. A scenario it **cannot** answer is the
valuable result, and it is never settled by the author: in a [`grilling`](../grilling/SKILL.md) session it is the
next question (with your recommendation); anywhere else it goes to `## Open ambiguities`
or the artifact's `## Open questions`. The answer usually changes the definition — and
often an AC or the data model with it, which is the point of running the test before
those exist.

## Who writes the glossary

It is one shared file, read by every session, so the write path is narrow:

| Who | What they do |
|---|---|
| **Main loop** — `/wellforge:grill-me --docs`, `/wellforge:spec` | writes it. In a grilling session a term is written the moment the user resolves it, not saved up for the end; in `/wellforge:spec` proposed terms are shown at the review and written on a yes. |
| **`product-owner`, `architect`** | read it and use its terms. A concept it lacks, or a term it gets wrong, goes in their return as a **glossary candidate** — they never edit the file. |
| **`frontend-dev`, `backend-dev`** | name types, tables, endpoints and tests with its terms. A concept with no term is reported, not named ad hoc. They never edit the file — in a worktree that is also a guaranteed conflict. |

Nothing is written from a guess. A term whose meaning the user **delegated** is written
and marked `(delegated)`; a term nobody was asked about is a candidate, not an entry.

**A term that changes under an approved artifact is drift.** If a sharper definition
contradicts an AC or a contract already approved, update the glossary and report the
contradiction as a proposed amendment ([`spec-driven`](../spec-driven/SKILL.md)) — do not edit the approved artifact
to match, and do not soften the definition to avoid the conflict.

## Decisions that are not vocabulary

A grilling session about the domain keeps turning up decisions that are not terms: an
invariant, a rule with an alternative that was rejected. Those are **ADR candidates**, and
the bar is the plan's own: a decision that names **an alternative it rejected** and will
constrain future work. Collect them, and let the caller offer them to the `adr-writer`
agent — do not write ADRs inline, and do not file a note as an ADR. A decision with no
rejected alternative is a sentence in the spec.

## What this is NOT

- **Not a data model.** No fields, no types, no tables — that is plan.md. The glossary says
  what an Order *is*; the plan says what columns it has.
- **Not documentation of the codebase.** It does not list classes or modules.
- **Not approval of anything.** A term in the glossary does not approve the spec that
  uses it.
- **Not required.** A project with no glossary works exactly as before; the agents'
  instructions all say "if present".

Related: [`grilling`](../grilling/SKILL.md) (the interview that resolves a term), [`spec-driven`](../spec-driven/SKILL.md) (artifacts and
the drift rule), [`self-critique`](../self-critique/SKILL.md) (the *invented vocabulary* item this gives teeth to).
