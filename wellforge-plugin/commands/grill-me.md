---
description: Grill an idea, spec or plan — one question at a time, each with a recommendation, until it is decided
argument-hint: <idea in a sentence or two> | <NNN-slug of an existing feature> [--docs]
---

Interview the user about the target below until its decision tree is resolved, following the
**grilling** skill (load it now — it defines the question rules, the stop conditions and the
ledger format; follow it verbatim). This command only resolves what is being grilled and
what happens to the result.

Target: $ARGUMENTS

## Procedure

1. **Resolve the target.**
   - Matches an existing `specs/NNN-slug/` → grill that feature's **latest artifact**:
     `plan.md` if it exists, otherwise `spec.md` (load the **spec-driven** skill for the
     format and the WHAT/HOW line). Note its `status:` — it decides step 4.
   - Anything else → it is a free-form idea. Nothing is written to `specs/`.
   - Empty → grill whatever plan or idea the conversation so far has been about. If there
     is none, ask what to grill; do not invent a topic.

2. **Read first** (grilling rule 1): neighbouring specs, the ADR index, the glossary, the
   code the target touches. For an existing artifact, read all of it — a question it
   already answers is a finding, not a question.

3. **Map the tree, then grill.** Show the branches and their order, then run the interview
   exactly as the skill defines: one question at a time, parents first, a recommendation
   with every question, branch-closed progress. Stop on any of the skill's three stop
   conditions.

   **Write the ledger file as you go** (grilling skill, *The decision ledger*): create it
   when you show the map and rewrite it each time a decision resolves —
   `.forge/grill/<slug>.md` for a free-form idea, `specs/NNN-slug/ledger.md` for an existing
   feature. The file is the result; the conversation is not.

   **With `--docs`**, also load the **domain-modeling** skill and maintain the docs as you
   go (grilling skill, *Grilling with docs*): challenge a term the moment it is used
   against the glossary, stress-test a new one before writing it, and write
   `.claude/context/glossary.md` as each term resolves — creating it on the first resolved
   term if the project has none. Collect decisions that name a rejected alternative as ADR
   candidates; do not write them.

4. **Close with the ledger, then route it — by what was grilled:**
   - **Free-form idea** → print the ledger, its path, and the exact next command. Either
     works, in this session or a later one, because both read the file:
     - `/wellforge:spec <one-line summary> --ledger .forge/grill/<slug>.md` — write the spec
       yourself and review it;
     - `/wellforge:orchestrate <one-line summary> --ledger .forge/grill/<slug>.md` — hand the
       whole pipeline the ledger; the product-owner writes the spec from it.

     For something the user called throwaway, propose `/wellforge:spike` instead and point
     at the ledger as its brief's starting material.
   - **`status: draft` artifact** → list the edits the ledger implies and ask before
     applying them. On yes, apply them to the draft and nothing else: `status:` stays
     `draft`.
   - **`approved`, `in-progress` or `done` artifact** → edit nothing. The ledger's
     consequences are **proposed amendments**: present them as drift and route them to the
     artifact's own command (`/wellforge:spec NNN-slug` or `/wellforge:plan NNN-slug`).

5. **With `--docs`: ADR dispatch.** If the ledger lists ADR candidates, show them and ask
   once which to record. For each yes, spawn `wellforge:adr-writer` with the decision, the
   rejected alternative and the reason the user gave — it writes `docs/adr/NNNN-slug.md`
   and appends the index line to `AGENTS.md` itself. A decision with no rejected
   alternative is not an ADR; leave it in the ledger. If a term written this session
   contradicts an approved spec or plan, say so here as a proposed amendment.

## Hard rules

- Main loop only. Never dispatch an agent to do the interviewing, and never answer your
  own question to keep the session moving.
- This command never sets `status:`, never approves, and never writes a spec, plan or task
  list — a spec is `/wellforge:spec`'s to create. It writes exactly one file of its own, the
  ledger. With `--docs` it also writes the glossary, and ADRs only through `adr-writer`
  after an explicit yes; nothing else, and nothing without the flag.
- Never allocate a `specs/NNN-slug/` directory for an idea: numbering is `/wellforge:spec`'s,
  and an idea's ledger waits in `.forge/grill/` until a spec exists to move it beside.
- The user saying stop ends it at once: unresolved branches go under **Open**, not into a
  guess.
- A delegated answer ("you pick") is recorded as **Delegated**, never as the user's
  decision.
