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
   - **Design nudge (UI features).** If the feature has a UI surface and there's no
     `design.md` (or it's older than spec/plan), recommend running `/wellforge:design
     NNN-slug` first so frontend tasks derive from a real screen/component inventory. This
     is a suggestion, not a gate — proceed if the user declines (note that frontend tasks
     will be coarser without it).

3. **Derive tasks** into `specs/NNN-slug/tasks.md`:
   - Right-sized: each task is one reviewable unit (roughly one commit / ≤ half a day);
     split anything bigger, merge anything trivial into a sibling.
   - Every task carries: refs to the AC(s) it serves, `deps:` (must form a DAG),
     a `touch:` list, and an objective "done when" check.
   - **`touch:` is binding** (spec-driven skill) — repo-relative paths or globs, written for
     a scheduler, not for a reader. Use a **glob for anything the task creates**
     (`db/migrations/*`), not a guessed filename; write `touch: unknown — <why>` rather than
     guessing, and that task will be scheduled alone.
   - Coverage check both directions: every AC covered by ≥1 task, every task serving
     ≥1 AC (a task serving none is scope creep — flag it).
   - Order: dependency-first; parallelizable means **no edge on the effective graph**
     (`deps:` ∪ `touch:` overlap), not merely no declared dep.
   - Include the closing task: "all gates green, spec status → done".

4. **Overlap check** — before presenting, compute the `touch:` overlaps across the derived
   set (globs included) and resolve each one *now*, while it's cheap:
   - genuinely ordered → add the `deps:` edge explicitly, so the ordering is declared rather
     than inferred at dispatch;
   - inseparable (both halves must land in one numbered series, or in one file, as a unit) →
     **merge them into one task** rather than ordering two;
   - overlap only on a file that all tasks in the feature append to (a barrel/index/route
     registry) → keep them separate, but say so: it's the most common induced edge and it
     will serialize the batch.

   Report the overlaps found and what you did about each — this is the check that stops a
   collision at merge time. See [[worktree-isolation]].

5. **Re-sync mode.** If tasks.md already exists: preserve checked tasks and their IDs,
   diff the new derivation against them, and present what's added/changed/obsolete
   instead of regenerating blindly. Never un-check a completed task.

6. **Present** the task table (ID, title, deps, ACs) and the coverage mapping. On user
   confirmation, write the file and set spec status to `in-progress` if work starts now.

## Hard rules

- No task without an objective "done when". "Implement X" with no check is not a task.
- No task without a `touch:` list. An unknown footprint is written as `unknown`, never
  omitted and never guessed — omitting it tells the dispatcher the task touches nothing.
- Don't start implementing — that's for `/wellforge:implement`. Offer it as the natural
  next step: `/wellforge:implement next` (first ready task), `T3,T5` (a subset), or
  `all` — or `/wellforge:orchestrate` to also run QE end-to-end.
