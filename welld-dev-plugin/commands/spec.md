---
description: Write a feature specification (spec-driven workflow, step 1 of 3)
argument-hint: <feature description> | <NNN-slug to resume>
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

3. **Write `specs/NNN-slug/spec.md`** with `status: draft`:
   - Problem: 2–5 sentences, no solutioning.
   - User stories with acceptance criteria in Given/When/Then form. Every AC must be
     objectively verifiable — if you can't picture the test, rewrite the AC.
   - Non-goals: anything a reasonable reader might assume is included but isn't.
   - Open questions: what you still don't know, each with an owner.

4. **Review with the user.** Present a compact summary (stories + ACs + non-goals, not the
   whole file). Iterate until they're satisfied.

5. **Approval gate.** Ask explicitly whether to mark the spec `approved`. Only on an
   explicit yes: set `status: approved` and add `approved: <date>` to the frontmatter.
   If open questions remain, approval requires the user to accept them as risk —
   record that in the spec.

## Hard rules

- You write the WHAT and WHY only. No architecture, no technology choices, no file paths —
  that is `/welld-dev:plan`'s job. If the user volunteers technical decisions, capture them
  under a `## Constraints` section verbatim, don't elaborate on them.
- Never set `approved` yourself; never skip the interview for "obvious" features.
- Suggest `/welld-dev:plan` as the next step after approval.
