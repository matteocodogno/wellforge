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
   - Architecture: components touched/added and why this shape; reference existing ADRs
     by number.
   - Data model: concrete schema changes + migration approach.
   - API contracts: concrete request/response shapes, error cases included.
   - Test strategy: map every AC in the spec to a test level (unit/integration/e2e).
     An AC with no test mapping is a plan bug.
   - Risks: what could invalidate this plan, each with a mitigation or early check.
   - Security: flag whether the feature is security-sensitive (auth, PII, upload, external
     calls, payments, regulated data) — YES schedules an owasp pass in parallel with QE.

5. **Self-critique — one pass** (`self-critique` skill, plan.md checklist). Re-read the
   draft against the checklist and fix what it catches (an AC with no test row or a row that
   wouldn't prove it, a contract written as prose, a component you never opened a real path
   for, a reflex `Security: NO`, a risk with no early check, a buried ADR candidate) *before*
   the user's review round. One pass, not a loop; it never sets `status:`.

6. **Review with the user.** Present the architecture and the trade-offs you made (what
   you chose AND what you rejected), plus the one-line self-critique result. Iterate.

7. **ADR dispatch — from the plan's own text, not from remembering.** A decision that
   names **an alternative it rejected** is an ADR by definition: it constrains future work
   and its reasoning is exactly what a later reader will lack. Scan the written plan for
   them — the `## ADR candidates` section if you wrote one, and any Architecture or Data
   model paragraph of the shape *"chose X over Y because Z"*.

   For each, by tier (rigor-tiers precedence):
   - **`production`** → spawn `wellforge:adr-writer` automatically, one per decision. Not
     "offer": a decision whose alternatives are recorded only in a chat transcript is a
     decision nobody can revisit, and the transcript is gone by the next session.
   - **`mvp`** → list them and offer. The tier trades ceremony for speed, and this is
     ceremony with a real cost.

   The ADR path is **predictable**: `docs/adr/NNNN-slug.md`, NNNN being the next free
   4-digit number. Reference it back from the plan's Architecture section by that path in
   the same pass, so plan and ADR point at each other rather than the ADR being a file
   nobody finds.

   A decision with **no rejected alternative** is not an ADR — it is a note. Writing one for
   it trains people to skim ADRs, which costs more than the missing record would.

8. **Approval gate.** Ask explicitly whether to mark the plan `approved`. Only on an
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
