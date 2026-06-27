---
description: Write the technical plan for an approved spec (spec-driven workflow, step 2 of 3)
argument-hint: [NNN-slug] (defaults to the most recent approved spec without a plan)
---

Create the technical plan for a spec, following the **spec-driven** skill conventions
(load that skill now — it defines the exact file format; follow it verbatim).

Target spec: $ARGUMENTS

## Procedure

1. **Resolve target.** If no argument: pick the most recent spec with `status: approved`
   and no `plan.md`; if ambiguous, ask. Read `specs/NNN-slug/spec.md` fully.

2. **Gate check.** If spec status is not `approved`, STOP and tell the user to finish
   `/wellforge:spec` first. Do not draft "provisionally".

3. **Explore before designing.** Investigate the actual codebase: existing modules this
   feature touches, established patterns (check stack skills and `docs/adr/`), current
   data model, existing API conventions. The plan must fit the codebase as it is, not an
   idealized one. Delegate broad exploration to an Explore agent if the surface is large.

4. **Write `specs/NNN-slug/plan.md`** with `status: draft`:
   - Architecture: components touched/added and why this shape; reference existing ADRs,
     and flag any decision that deserves a NEW ADR (offer to invoke the adr-writer agent).
   - Data model: concrete schema changes + migration approach.
   - API contracts: concrete request/response shapes, error cases included.
   - Test strategy: map every AC in the spec to a test level (unit/integration/e2e).
     An AC with no test mapping is a plan bug.
   - Risks: what could invalidate this plan, each with a mitigation or early check.

5. **Review with the user.** Present the architecture and the trade-offs you made (what
   you chose AND what you rejected). Iterate.

6. **Approval gate.** Ask explicitly whether to mark the plan `approved`. Only on an
   explicit yes, set `status: approved`. Then suggest the next step **by feature type**:
   - **UI feature** → recommend `/wellforge:design NNN-slug` first (flows/screens/component
     reuse so frontend tasks derive from a real inventory), *then* `/wellforge:tasks`.
   - **non-UI feature** → `/wellforge:tasks` directly.

## Hard rules

- Every AC from the spec must appear in the test strategy. Run this check before
  presenting; report the mapping table.
- If during planning you find the spec is wrong or incomplete, stop and propose a spec
  amendment first (drift rule) — don't silently plan around it.
- No implementation. No code beyond contract sketches.
