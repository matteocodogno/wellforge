---
description: Design the UX for a UI feature — flows, screens/states, component reuse, a11y (spec-driven workflow, optional stage for UI features)
argument-hint: [NNN-slug] [--gate] — --gate adds a human approve/iterate checkpoint before tasks
---

Produce the interaction design for a feature with a user interface, following the
**spec-driven** skill conventions (load it now). This is the optional **design** stage —
it sits between `/wellforge:plan` and `/wellforge:tasks` for UI features, so frontend tasks
derive from a concrete screen/flow inventory instead of being invented ad hoc. The work is
done by the `wellforge:designer` agent; you coordinate and relay.

Target spec: $ARGUMENTS

## Procedure

1. **Resolve target.** If no argument: the most recent spec with `status: approved`, a UI
   surface, and no (or stale) `design.md`. If ambiguous, ask. State which feature you
   resolved. (`--gate` is a flag, not a feature token — strip it before resolving; it
   controls the optional approval in step 6.)

2. **UI check.** If the feature has no user interface (API-only / infra / backend-only),
   this stage does not apply — say so and point at `/wellforge:tasks`. Don't design a UI no
   AC asks for.

3. **Gate check.** The spec must be `approved` (the designer refuses drafts) — if not, STOP
   and point at `/wellforge:spec`. A `plan.md` is recommended first (the designer reads it
   for API contracts), but not required; note if it's missing.

4. **Run the designer.** Spawn `wellforge:designer` with the spec dir path. It reads the
   spec (and plan.md if present), inspects the existing UI in `frontend/src/` (and the
   running app via Playwright if available), and writes `specs/NNN-slug/design.md`:
   flows → screens & states → component inventory (reuse vs NEW) → accessibility.

5. **Relay.** Present the designer's summary: flow count, the reuse/NEW component ratio,
   a11y hotspots, and any gaps it found in the spec or plan.

6. **Approval — opt-in (`--gate`).** By **default there is no gate**: design.md stays
   `status: draft` and design issues surface at QE (the standard model; the feature flow's
   only mandatory gates are spec and plan). If `--gate` was passed, treat design as a
   checkpoint: ask the user explicitly to **approve / iterate / abort**.
   - On **approve** → set design.md `status: approved` (record the user's decision; never
     self-approve).
   - On **iterate** → re-run the designer with the user's feedback (bounded — at the user's
     request, like the spec/plan gates), then re-present.
   - On **abort** → leave design.md `draft`, stop, state where things stand.

7. **Drift.** If the designer reports the spec/plan is wrong or lacks an API a flow needs,
   pause and route the amendment to the owning agent (PO for spec, architect for plan)
   before continuing — never design around a wrong spec.

## Hard rules

- The designer writes `design.md` only — no production code, CSS, or components (that's
  frontend-dev's job at `/wellforge:implement`).
- Default to reuse: every `NEW` component in the inventory needs a one-line justification;
  flag any UI being added that no AC asks for (scope creep).
- Next step after design is `/wellforge:tasks` (frontend tasks now reference the screens
  and component inventory). Suggest it.
