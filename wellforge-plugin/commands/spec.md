---
description: Write a feature specification (spec-driven workflow, step 1 of 3)
argument-hint: <feature description> | <NNN-slug to resume> [--grill]
---

Create or resume a feature specification following the **spec-driven** skill conventions
(load that skill now — it defines the exact file format; follow it verbatim).

Feature request: $ARGUMENTS

## Procedure

1. **Resolve target.** If the argument matches an existing `specs/NNN-slug/` directory,
   resume that spec. Otherwise determine the next sequential `NNN` and derive a short
   kebab-case slug from the request.

2. **Interview before writing.** Use AskUserQuestion to close the gaps the request leaves
   open — typically: who the users/roles are, what "done" looks like observably, what is
   explicitly OUT of scope, and any hard constraints (deadline, compatibility, compliance).
   Ask only what you cannot infer from the codebase or existing specs; batch questions
   (max 2 rounds). Read neighboring specs first so terminology stays consistent.

   **With `--grill`**, replace the batched rounds with a grilling session (load the
   **grilling** skill and follow it verbatim): one question at a time, parents first, a
   recommendation with every question, until the decision tree is resolved or the user
   stops. Write the spec from its ledger — *Open* becomes `## Open questions`, and a
   *Delegated* decision is marked as such where it lands, never presented as the user's
   choice. If a decision ledger from `/wellforge:grill-me` is already in this conversation
   for this feature, that **is** the interview: do not ask again, with or without the flag.

3. **Write `specs/NNN-slug/spec.md`** with `status: draft`:
   - Problem: 2–5 sentences, no solutioning.
   - User stories with acceptance criteria in Given/When/Then form. Every AC must be
     objectively verifiable — if you can't picture the test, rewrite the AC.
   - Non-goals: anything a reasonable reader might assume is included but isn't.
   - Open questions: what you still don't know, each with an owner.

4. **Self-critique — one pass** (`self-critique` skill, spec.md checklist). Re-read the
   draft against the checklist and fix what it catches (unverifiable ACs, hidden ANDs,
   solutioning that crept into the WHAT, orphan stories, empty non-goals, an assumption
   phrased as a fact) *before* spending the user's review round on it. One pass, not a loop;
   it never sets `status:`. Skip at the `spike` tier.

5. **Review with the user.** Present a compact summary (stories + ACs + non-goals, not the
   whole file) plus the one-line self-critique result. Iterate until they're satisfied.
   If the spec introduces a domain term the glossary lacks, or uses one differently, list
   those as **glossary changes** in the same summary (`domain-modeling` skill — one word
   per concept, run the stress test on anything new) and write them to
   `.claude/context/glossary.md` only on a yes. No new terms → say nothing; never create
   an empty glossary.

6. **Approval gate.** Ask explicitly whether to mark the spec `approved`. Only on an
   explicit yes: set `status: approved` and add `approved: <date>` to the frontmatter.
   If open questions remain, approval requires the user to accept them as risk —
   record that in the spec.

## Hard rules

- You write the WHAT and WHY only. No architecture, no technology choices, no file paths —
  that is `/wellforge:plan`'s job. If the user volunteers technical decisions, capture them
  under a `## Constraints` section verbatim, don't elaborate on them.
- Never set `approved` yourself; never skip the interview for "obvious" features.
- `--grill` changes how the questions are asked, nothing after them: self-critique, the
  review and the approval gate run exactly as without it.
- Suggest `/wellforge:plan` as the next step after approval.
