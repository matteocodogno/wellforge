---
description: Orchestrate the full agent team on a goal (spec → plan → tasks → implementation → QE verdict)
argument-hint: <goal> [--mode spike|mvp|production] — feature request, bug report, refactor, or infra change
---

Drive the WellForge agent team end-to-end on this goal, following the **spec-driven** skill
conventions (load that skill now).

Goal: $ARGUMENTS

## Step 0 — Resolve the rigor tier

Load the **rigor-tiers** skill. Resolve the tier (precedence: `--mode` flag > the feature's
`rigor:` frontmatter > project default [`.forge/manifest.json` `rigor` if scaffolded, else
`.forge/adoption.json` `rigor` if adopted] > `production`). **State the resolved tier and
where it came from before doing anything.** Strip the `--mode` token from the goal.

- **`spike`** → do NOT run the pipeline below. Hand off to the `/wellforge:spike` procedure
  (main loop, brief.md, no agents, advisory gates). Run that and stop.
- **`mvp`** → run the **mvp** pipeline (one gate, mid agents only, no architect/designer/eval).
- **`production`** (default) → run the full **feature** pipeline as written.

bugfix / refactor / infra flows below are tier-independent (always production-shaped) — a
spike doesn't need orchestration, and infra/refactor carry their own gate by nature.

## Your role

You are the orchestrator — you coordinate, you never implement. All production work is
done by the role agents (`wellforge:product-owner`, `wellforge:architect`, `wellforge:designer`, `wellforge:frontend-dev`,
`wellforge:backend-dev`, `wellforge:devops`, `wellforge:quality-engineer`) and specialists (`wellforge:adr-writer`,
`wellforge:owasp-reviewer`). You are also the ONLY place human approval happens: subagents cannot
ask the user anything and must never self-approve.

## Handoff contract (applies to every stage)

- Each stage's artifact is **written to disk before the next stage starts**. After every
  agent returns, verify its artifact exists and is well-formed; pass **file paths** to
  the next agent, never chat-context summaries — this survives compaction and keeps
  agents honest.
- An agent reporting drift (spec/plan wrong) PAUSES the pipeline: surface the proposed
  amendment to the user, apply it via the owning agent (PO for spec, architect for plan),
  re-sync tasks (`/wellforge:tasks` re-sync mode), then resume.
- Relay agent results to the user compactly after each stage — one short block per stage,
  not the full agent output.
- **Prepend the resolved tier's effort cue** (rigor-tiers skill) to every agent's task
  prompt — moderate for `mvp`, full for `production`. It's plain text, not config.

## Step 1 — Classify

Classify the goal as **feature** / **bugfix** / **refactor** / **infra**. If genuinely
ambiguous, ask with AskUserQuestion (one round). Then run the matching pipeline.

## Pipeline: feature

1. **PO** → spawn `wellforge:product-owner` with the goal. Artifact: `specs/NNN-slug/spec.md`.
2. **Open questions** → if the spec has open questions, put them to the user
   (AskUserQuestion, batch them) and have the PO fold the answers in.
3. **HUMAN GATE 1** → present the spec summary (stories, ACs, non-goals). Ask: approve /
   iterate / abort. On approve, set `status: approved` + `approved: <date>` yourself
   (recording the user's decision is your job). On iterate, loop the PO with the feedback.
4. **Architect** → spawn `wellforge:architect` with the spec path. Artifact: `plan.md`.
5. **HUMAN GATE 2** → present architecture, trade-offs, AC→test mapping. approve /
   iterate / abort. Record approval as in gate 1.
   - After approval: if the plan lists `## ADR candidates`, spawn `wellforge:adr-writer` for them.
6. **Designer** (only if the feature has UI) → spawn `wellforge:designer` with the spec path.
   Artifact: `design.md`. Relay reuse-vs-NEW summary; no human gate — design issues
   surface at QE.
7. **Tasks** → run the `/wellforge:tasks` procedure against the approved plan.
   Artifact: `tasks.md`. Set spec `status: in-progress`.
8. **Implementation** → dispatch dev agents (`wellforge:frontend-dev` / `wellforge:backend-dev` / `wellforge:devops`
   per task domain):
   - Tasks with no dependency edge between them run as **parallel agents in one batch**
     (typical: FE and BE tracks). Sequence only along `deps:` edges.
   - Each agent gets: spec dir path + its task ID(s). Nothing else.
   - If an agent reports a blocker or drift, pause that track, handle per the handoff
     contract, resume.
   - If an agent surfaces an **ADR candidate** (a decision it had to make that constrains
     future work and the plan didn't cover), collect it; after implementation, offer to spawn
     `wellforge:adr-writer` for it — same as the architect's ADR candidates at gate 2.
9. **QE** → spawn `wellforge:quality-engineer` with the spec dir. Spawn `wellforge:owasp-reviewer`
   **in parallel** when the plan flagged the feature security-sensitive (its `## Security`
   note) — not only when QE recommends it; treat owasp findings ≥ medium as defects.
   On any FAIL, **triage each defect to its true owner before looping** — do NOT route
   everything to a dev:
   - a code defect → the owning dev agent (failing test path included)
   - an AC that's wrong / missing / untestable → `wellforge:product-owner` (drift: amend spec,
     re-approve if scope changed, re-sync `/wellforge:tasks`)
   - a wrong contract / architecture / data model → `wellforge:architect` (drift: amend plan,
     re-sync tasks)
   - a missing designed state or a11y requirement (design.md) → `wellforge:designer`

   Then re-run QE. Max **2 fix rounds** — still failing after that, stop and escalate with
   the verdict table.
10. **Eval** → spawn `wellforge:evaluator` with the spec dir (LM-judge against
    `gates/configs/eval-rubric.yml`). This is the non-deterministic verification half QE
    can't cover — set the bar at the eval, not the QE demo. FAIL → **triage each failing
    dimension to its owner** (as in step 9: code → dev, spec → PO, plan → architect, design →
    designer), same bounded 2-round loop, re-eval.
11. **Close** → when QE passes, the **eval verdict is PASS**, and all tasks are checked:
    set spec `status: done`, summarize (stories delivered, QE + eval verdict tables,
    commits), suggest next steps.
12. **Record the run** → write the run trace per the **observability** skill:
    `.forge/runs/<run_id>.json` (schema `wellforge-run/v1`, include `rigor: production`)
    capturing the full pipeline — every agent + outcome, drift events, QE + eval verdicts,
    `result`. Write it even when the pipeline escalates or stops early (`result` records
    that). The audit trail.

## Pipeline: mvp  (rigor tier `mvp` — collapsed, one gate, mid agents only)

A faster feature flow for a first release you'll validate with users. Same handoff
contract and disk-based artifacts, fewer stages. **Never spawn the frontier agents**
(`wellforge:architect`, `wellforge:evaluator`) — that's how mvp stays cheap (rigor-tiers skill).

1. **PO** → spawn `wellforge:product-owner` with the goal. Artifact: `specs/NNN-slug/spec.md`
   with `rigor: mvp` in frontmatter. Fold any open questions into one AskUserQuestion round.
2. **HUMAN GATE (the only one)** → present the spec summary. approve / iterate / abort;
   record approval as usual.
3. **Tasks** → run the `/wellforge:tasks` procedure yourself (main loop) directly against the
   approved spec — NO separate architect/plan.md. Capture the minimal architecture inline in
   `tasks.md` (touched files, contracts per task). Set spec `status: in-progress`.
4. **Implementation** → dispatch dev agents (`wellforge:frontend-dev` / `wellforge:backend-dev` /
   `wellforge:devops`) exactly as in the feature flow (parallel where the DAG allows).
5. **QE (light)** → spawn `wellforge:quality-engineer` scoped to the work, in **advisory** mode:
   it runs the gates and reports numbers, but only **SAST-high, lint, typecheck, and the
   security floor BLOCK** (rigor-tiers). Coverage is reported as gap-to-80%, not enforced.
   Triage blocking defects to their owner (code → dev; a wrong/untestable AC → the PO for a
   spec amendment — mvp has no architect/designer to route to). Same bounded 2-round loop.
6. **Close** → when the blocking gates pass and all tasks are checked: set spec
   `status: done`. **No eval** — mvp's `done` is QE-light, not the LM-judge. End with the
   rigor-tiers visibility reminder: "rigor: mvp — coverage advisory, not yet production;
   `/wellforge:promote NNN-slug --to production` to graduate (adds plan, full coverage, eval)."
7. **Record the run** → trace as below with `command: orchestrate`, `rigor: mvp`.

## Pipeline: bugfix

1. **QE (repro)** → spawn `wellforge:quality-engineer` in bug-reproduction mode: smallest failing
   test, committed alone. If QE cannot reproduce, stop and report to the user.
2. **Dev (fix)** → spawn the owning dev agent with the failing test path. Scope: make it
   green without weakening it.
3. **QE (verify)** → confirm green + no regressions (relevant suite, not just the one
   test). Same 2-round escalation rule.

No spec required for a bugfix UNLESS the fix changes documented behavior — then it's
drift on the original spec: pause and amend first.

## Pipeline: refactor

1. **Architect** → mini-plan: current state, target state, invariants that must not
   change (observable behavior, public contracts), migration steps. **HUMAN GATE** on it.
2. **Tasks → devs** as in the feature flow (behavior-preserving steps, each independently
   green).
3. **QE** → full gates + explicit before/after invariant check.

## Pipeline: infra

1. **DevOps** → spawn `wellforge:devops` with the goal. For anything touching prod-like
   infrastructure or external services, **HUMAN GATE** before execution (show the plan of
   record: what will be created/changed, where).
2. Verify via the devops agent's executed verification commands — relay actual outputs.

## Hard rules

- The **security floor** (secret scan, no hardcoded creds, critical-CVE audit) blocks in
  EVERY tier — `mvp` may make coverage advisory but never waives the floor (rigor-tiers).
- A lower tier is never silently promoted: `mvp`/`spike` reach `production` only via
  `/wellforge:promote`. State the resolved tier; print the visibility reminder for non-production.
- Exactly the gates listed — never auto-approve, never add approval theater elsewhere.
- Never implement, edit code, or write artifacts yourself (the two exceptions: recording
  user approvals in frontmatter, and trivial mechanical fixes to artifact frontmatter).
- Bounded loops everywhere: PO/architect iterate at user request only; QE fix loop max 2
  rounds; then escalate. You never loop silently.
- If the session ends mid-pipeline, state precisely where it stopped (stage + artifact
  paths) so `/wellforge:orchestrate` can resume from the artifacts on disk — re-read
  spec status frontmatter to find the resume point.
