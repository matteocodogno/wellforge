---
description: Derive the task list from an approved plan (spec-driven workflow, step 3 of 3)
argument-hint: [NNN-slug] (defaults to the most recent approved plan without tasks)
---

Derive (or re-sync) the ordered task list for a planned feature, following the
**spec-driven** skill conventions (load that skill now — it defines the exact file format;
follow it verbatim).

Target spec: $ARGUMENTS

## Procedure

1. **Resolve target.** If no argument: pick the most recent spec whose `plan.md` is
   `approved` and which has no `tasks.md` — or whose spec/plan is newer than its
   `tasks.md` (re-sync case). If ambiguous, ask. Read both spec.md and plan.md fully.

2. **Gate check.** If plan.md status is not `approved`, STOP and point to
   `/wellforge:plan`.

3. **Derive tasks** into `specs/NNN-slug/tasks.md`:
   - Right-sized: each task is one reviewable unit (roughly one commit / ≤ half a day);
     split anything bigger, merge anything trivial into a sibling.
   - Every task carries: refs to the AC(s) it serves, `deps:` (must form a DAG),
     the files/modules it touches, and an objective "done when" check.
   - Coverage check both directions: every AC covered by ≥1 task, every task serving
     ≥1 AC (a task serving none is scope creep — flag it).
   - Order: dependency-first; mark tasks with no mutual deps as parallelizable
     (FE/BE tracks typically are).
   - Include the closing task: "all gates green, spec status → done".

4. **Re-sync mode.** If tasks.md already exists: preserve checked tasks and their IDs,
   diff the new derivation against them, and present what's added/changed/obsolete
   instead of regenerating blindly. Never un-check a completed task.

5. **Present** the task table (ID, title, deps, ACs) and the coverage mapping. On user
   confirmation, write the file and set spec status to `in-progress` if work starts now.

## Hard rules

- No task without an objective "done when". "Implement X" with no check is not a task.
- Don't start implementing — that's for `/wellforge:implement`. Offer it as the natural
  next step: `/wellforge:implement next` (first ready task), `T3,T5` (a subset), or
  `all` — or `/wellforge:orchestrate` to also run QE end-to-end.
