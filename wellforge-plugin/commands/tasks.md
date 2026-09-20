---
description: Derive the task list from an approved plan — or, at rigor mvp, straight from the approved spec (spec-driven workflow, step 3 of 3)
argument-hint: [NNN-slug] (defaults to the most recent feature ready for tasks)
---

Derive (or re-sync) the ordered task list for a planned feature, following the
**spec-driven** skill conventions (load that skill now — it defines the exact file format;
follow it verbatim).

Target spec: $ARGUMENTS

## Procedure

1. **Resolve target.** If no argument: pick the most recent feature that is *ready for
   tasks* under its own tier (see the gate below) and has no `tasks.md` — or whose upstream
   artifacts are newer than its `tasks.md` (re-sync case). If ambiguous, ask. Read spec.md
   fully, and plan.md too when one exists.

2. **Gate check — resolve the rigor tier FIRST, then gate on it.** Load the **rigor-tiers**
   skill and resolve the feature's tier (precedence: the feature's `rigor:` frontmatter >
   project default in `.forge/manifest.json` / `.forge/adoption.json` > `production`). State
   the resolved tier. The gate differs by tier because the *artifact set* differs — an mvp
   feature has **no plan.md by design** (rigor-tiers: "plan folded into tasks"), so gating it
   on an approved plan would dead-end it permanently:
   - **`production`** → `plan.md` must be `approved`. Otherwise STOP and point at
     `/wellforge:plan`.
   - **`mvp`** → `spec.md` must be `approved`; there is no plan to wait for. Derive directly
     from the spec and capture the minimal architecture inline (step 3). If a `plan.md`
     happens to exist anyway (a feature mid-promotion, or one written by hand), read it and
     use it — never ignore an artifact that is there.
   - **`spike`** → tasks.md is not part of this tier: a spike has `brief.md` and builds in
     the main loop. STOP and point at `/wellforge:spike NNN-slug`, or at
     `/wellforge:promote NNN-slug --to mvp` if the spike is done and should graduate.
   - **Never invent the missing artifact.** A missing plan at `production` is a stage to run,
     not a gap to fill here; a missing plan at `mvp` is the design, not an omission.
   - **Design nudge (UI features, `production` only).** If the feature has a UI surface and
     there's no `design.md` (or it's older than spec/plan), recommend running
     `/wellforge:design NNN-slug` first so frontend tasks derive from a real
     screen/component inventory. A suggestion, not a gate — proceed if the user declines
     (note that frontend tasks will be coarser without it). Skip the nudge at `mvp`: that
     tier deliberately runs no designer, so pointing at one contradicts the tier.

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
   - **At `mvp`, also write the `## Architecture notes` section** (spec-driven skill) at the
     top of tasks.md — this is where the folded-away plan lives, and `/wellforge:orchestrate`'s
     mvp pipeline assumes it exists. Keep it to what a dev agent cannot derive from the spec:
     the components touched, the concrete API contract per task (request/response shape with
     error cases, not prose), the data-model change and its migration, and anything
     deliberately deferred. It is not a plan.md — no trade-off essay, no risk register — but
     a contract written here is as binding on the dev agents as one in a plan.
     At `production` do NOT write this section: plan.md is the contract, and a second copy
     drifts from it.

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

   **Always stamp `synced: <today>` in the frontmatter — including when the re-sync
   changes nothing else.** This is not bookkeeping: the Stop hook's drift check clears
   only when `tasks.md` is part of the branch's change set, so a re-sync that (correctly)
   found nothing to change would otherwise leave the session blocked forever, with the
   hook telling the user to run the command they just ran. The stamp is also the honest
   record — it says the task list was *re-checked against this spec*, which is exactly
   what the drift rule asks for, rather than pretending the list had to change.

6. **Self-critique — one pass** (`self-critique` skill, tasks.md checklist). The overlap
   check above covers the `touch:` *collisions*; this covers the rest: a `done when:` nobody
   could run, a `touch:` list that lies by omission, a missing or invented `deps:` edge, a
   task too large to verify, a task labeled for the wrong domain (the label picks the agent),
   an AC no task serves. Fix what it catches before presenting. One pass, not a loop.

7. **Present** the task table (ID, title, deps, ACs) and the coverage mapping. On user
   confirmation, write the file and set spec status to `in-progress` if work starts now.

## Hard rules

- No task without an objective "done when". "Implement X" with no check is not a task.
- No task without a `touch:` list. An unknown footprint is written as `unknown`, never
  omitted and never guessed — omitting it tells the dispatcher the task touches nothing.
- Don't start implementing — that's for `/wellforge:implement`. Offer it as the natural
  next step: `/wellforge:implement next` (first ready task), `T3,T5` (a subset), or
  `all` — or `/wellforge:orchestrate` to also run QE end-to-end.
