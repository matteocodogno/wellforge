---
description: Graduate a feature (or the project) up a rigor tier — pay the deferred debt (retro plan, backfill tests, blocking gates, eval)
argument-hint: <feature> --to mvp|production   |   --project --to mvp|production
---

Raise the rigor tier of a feature (or the whole project) and **pay the rigor it deferred**.
A lower tier was tracked debt (the `rigor:` frontmatter / manifest); promotion settles it.
Load the **rigor-tiers** and **spec-driven** skills now. This mirrors `/wellforge:upgrade`:
clean-tree pre-flight → plan of record → execute → verify → one revertable commit.

Arguments: $ARGUMENTS

## Step 0 — Resolve scope, current tier, target

- **Feature scope** (default): leading token = a `specs/NNN-slug/` feature. Read its
  `brief.md` (spike) or `spec.md` frontmatter `rigor:`. `--project` scope instead promotes
  the project default in `.forge/manifest.json`.
- Target tier = the `--to` value. Tiers are ordered `spike < mvp < production`.
- **Refuse** if target ≤ current (promotion only RAISES — never lower a tier, ever) or if
  already at target. State current → target and the scope before continuing.

## Pre-flight (all must pass)

1. `git status` clean — require commit/stash first. Promotion must be ONE reviewable,
   revertable commit (no exceptions).
2. Compute the **debt** = the gap between current and target (which artifacts/gates/eval
   the lower tier skipped — see the rigor-tiers levers table). One tier at a time: a
   `spike → production` jump runs `spike → mvp` then `mvp → production` in sequence.
3. **Plan of record** — present exactly what will be done for this transition (the steps
   below that apply), and that it ends in one commit. Ask the user to confirm.

## Pay the debt — feature promotion

Run only the steps the transition requires. Each missing artifact is produced by its owning
agent (handoff contract from the **orchestrate** flow); you coordinate, agents do the work.
Prepend the **target tier's** effort cue (rigor-tiers skill) to each agent's task — you're
raising rigor, so agents work at the destination tier's effort, not the source's.

### → mvp  (from spike)
1. **brief.md → spec.md** — spawn `wellforge:product-owner` with the brief + the code already
   built: write a real `spec.md` (problem, user stories, **verifiable ACs**, non-goals),
   frontmatter `rigor: mvp`. The spike's `## Findings` inform the spec; keep the brief.
2. **Tasks** — run the `/wellforge:tasks` procedure against the spec; mark tasks already
   satisfied by the spike code as done (verify each `done when:` actually holds — don't
   check boxes on faith).
3. **QE (light)** — spawn `wellforge:quality-engineer` in advisory mode: SAST-high, lint,
   typecheck and the **security floor** block; coverage reported as gap-to-80%, not enforced.
   Bounded 2-round fix loop for blocking defects only.

### → production  (from mvp)
1. **plan.md** — spawn `wellforge:architect` with the spec + the existing code: write the
   retro `plan.md` capturing the architecture the code already embodies (data model, API
   contracts, test strategy, risks), `status: approved` only on the user's gate. If UI,
   spawn `wellforge:designer` for `design.md`.
2. **Re-sync tasks** to the plan (`/wellforge:tasks` re-sync — preserves checked tasks).
3. **QE (full)** — backfill tests to the **enforced** floors: 80% line coverage, SAST,
   dependency audit, lint, typecheck — all **blocking** now. Route defects to the owning
   dev agent; bounded 2-round loop, then escalate with the verdict table.
4. **Eval** — run the `/wellforge:eval` procedure (LM-judge). **A PASS is the gate into
   `done`** — QE alone is not enough. FAIL → route failing dimensions to the dev agents
   (same bounded loop), re-eval. Only on PASS set `rigor: production` and spec `status: done`.

## Pay the debt — project promotion (`--project`)

The project's `rigor` is a copier answer, so flip it through copier (re-renders the
tier-conditional `quality.yml`, README badge, AGENTS note, manifest) WITHOUT a version bump:

```bash
uvx copier update --trust --skip-answered --conflict inline \
  --vcs-ref <current _commit from .copier-answers.yml> --data rigor=<target>
```

- Pinning `--vcs-ref` to the recorded `_commit` keeps this a pure rigor change, not a
  template upgrade (that's `/wellforge:upgrade`'s job — don't bundle them).
- Resolve any conflict markers (keep project behavior, adopt template structure); zero
  `<<<<<<<` may remain. Verify `.forge/manifest.json` now reads the new `rigor`.
- Promoting the project to `production` raises CI to full gates: run them once and make
  them green before committing (a project promoted to production must pass production CI).

## Verify

- The gates appropriate to the **target** tier, run for real: mvp → advisory coverage +
  blocking SAST/lint/floor; production → full blocking gates + eval PASS.
- `mise run install && mise run build && mise run test` green where the change touches code.

## Close

1. One revertable commit: `chore(rigor): promote <feature|project> <old> → <new>` — body
   lists artifacts created (spec/plan/design), tests backfilled, gate + eval results.
2. Frontmatter/manifest now read the target tier (verify; never hand-edit the manifest).
3. **Record the run** — write `.forge/runs/<run_id>.json` per the **observability** skill:
   `command: promote`, the agents run, QE + eval verdicts, `from`/`to` tiers, `result`.
4. Report: tier delta, debt paid (artifacts, coverage before→after, eval verdict), and what
   (if anything) the user still owns. If a feature reached production, it's now `done`.

## Hard rules

- Promotion only RAISES. A downgrade request is refused — lower rigor is re-declared
  deliberately at creation, never via promote.
- Production is never reached without an eval **PASS** — no auto-approve, no "pass with
  remarks". The eval is the gate, same as the normal flow.
- The security floor was always on; promotion ADDS the deferred gates, never removes a check.
- Bounded loops only (QE/eval fix loop max 2 rounds, then escalate). Dirty tree → no
  promotion; fully done or fully reverted (`git reset --hard`).
- Never weaken a gate or delete a test to make a tier pass — that defeats the promotion.
