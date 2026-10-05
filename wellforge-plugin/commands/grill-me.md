---
description: Grill an idea, spec or plan — one question at a time, each with a recommendation, until its decisions are made
argument-hint: <idea in a sentence or two> | <NNN-slug of an existing feature>
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
   with every question, branch-closed progress, the ledger restated every five decisions.
   Stop on any of the skill's three stop conditions.

4. **Close with the ledger, then route it — by what was grilled:**
   - **Free-form idea** → print the ledger and propose
     `/wellforge:spec <one-line summary>`; the ledger above it in the conversation is that
     command's interview, already done. For something the user called throwaway, propose
     `/wellforge:spike` instead.
   - **`status: draft` artifact** → list the edits the ledger implies and ask before
     applying them. On yes, apply them to the draft and nothing else: `status:` stays
     `draft`.
   - **`approved`, `in-progress` or `done` artifact** → edit nothing. The ledger's
     consequences are **proposed amendments**: present them as drift and route them to the
     artifact's own command (`/wellforge:spec NNN-slug` or `/wellforge:plan NNN-slug`).

## Hard rules

- Main loop only. Never dispatch an agent to do the interviewing, and never answer your
  own question to keep the session moving.
- This command never sets `status:`, never approves, and never writes a new artifact — a
  spec is `/wellforge:spec`'s to create.
- The user saying stop ends it at once: unresolved branches go under **Open**, not into a
  guess.
- A delegated answer ("you pick") is recorded as **Delegated**, never as the user's
  decision.
