---
description: Close a feature — verifies the tier-aware done gate (tasks + QE + eval) then sets status: done, or retires it as superseded
argument-hint: [feature] [--superseded-by <NNN-slug>] [--archive "<reason>"] — NNN-slug / slug / NNN; omit to infer the in-progress feature ready to close
---

Close a feature: verify it has genuinely met its **done gate**, then set `status: done`.
Read-only until the gate passes — this is the human-in-the-loop transition, and **agents
never set status** (the evaluator judges; the calling session records the close). Conventions:
the **spec-driven** and **rigor-tiers** skills (load them).

Feature: $ARGUMENTS

## Step 0 — Who is calling

This procedure is **the only implementation of the `done` transition**, and it is invoked two
ways — both run everything below, unchanged:

- **Directly** by the user (`/wellforge:done [feature]`).
- **As a procedure**, by a command that just finished the work and would otherwise flip the
  status itself: `/wellforge:spike` step 5, `/wellforge:promote`'s final step, and
  `/wellforge:orchestrate`'s close step (both its `mvp` and `production` pipelines). They say
  "run the `/wellforge:done` procedure"; you run it here, in the main loop, with the feature
  already resolved by the caller.

A caller that just ran the gate's inputs still re-verifies them here. That is the point: the
gate is checked against the **artifacts on disk**, never against a caller's recollection of
having passed it. Four copies of this transition is how one of them ends up not checking that
the tasks are all ticked.

## Step 0a — `--archive "<reason>"`: stopping without finishing

`/wellforge:status` and `/wellforge:triage` have always told users to "promote or archive" a
stale spike or mvp. Until now nothing implemented archiving, so the only ways out of that
sentence were to finish the work, lie with `done`, or hand-edit the frontmatter. This is the
missing exit.

**Archived** = deliberately stopped, with no successor: the experiment answered its question
and nobody will build on it, the priority moved, the approach was rejected. Distinct from
**superseded** (another spec took the work over — use `--superseded-by`) and from **done**
(it shipped).

With the flag, skip the done gate entirely and:

1. **Require the reason.** `--archive` with no reason is refused — an archived spec with no
   recorded why is indistinguishable from an abandoned one six months later, which is
   exactly the confusion this status exists to prevent.
2. Refuse if the feature is already `done`: shipped work is not archived, and rewriting its
   status hides that it shipped.
3. Set `status: archived`, `archived: <today>`, `archive_reason: "<reason>"` on the spec or
   brief. Change nothing else — no tasks touched, no code reverted, no branches deleted.
   Archiving is a statement about intent, not a cleanup.
4. Report what was archived, the reason, and that the work is still in git if anyone wants
   it back.

## Step 0b — `--superseded-by <NNN-slug>`: the other terminal status

`superseded` is the spec lifecycle's second exit (spec-driven skill): work that stopped
because another spec replaced it, not because it finished. It is NOT `done` — nothing was
delivered — and leaving such a spec `in-progress` forever is what makes
`/wellforge:triage` report rot that no one can clear.

When the flag is present, skip the done gate entirely (there is nothing to verify — the
work was abandoned, not completed) and instead:

1. Resolve BOTH features. The successor must exist and must not be the same feature; if it
   doesn't resolve, STOP — a `superseded_by` pointing nowhere is worse than no pointer.
2. Refuse if the feature is already `done`: a delivered feature is not superseded, it is
   replaced by later work, and rewriting its history hides that it shipped.
3. Set on the superseded spec: `status: superseded`, `superseded_by: <NNN-slug>`,
   `superseded: <today>`. Change nothing else — no tasks, no successor edits.
4. Report both features and say plainly that no work was verified, because none was claimed.

Everything below (the gate, the tiers) applies only WITHOUT this flag.

## Step 1 — Resolve the feature + tier

```bash
# Resolve the plugin root ONCE per session, then reuse $WF. ${CLAUDE_PLUGIN_ROOT} is
# substituted for HOOKS only — it is NOT exported to the Bash tool (measured: unset), so
# interpolating it here silently runs `python3 /scripts/...`.
WF=$(python3 -c "import json,os;p=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')))['plugins'];print(next(i['installPath'] for k,v in p.items() if k.startswith('wellforge@') for i in v))" 2>/dev/null)
# Running from a checkout (claude --plugin-dir) installs nothing; fall back to the repo.
[ -n "$WF" ] || WF="$(pwd)/wellforge-plugin"
# A FUNCTION, not a variable holding a command: `WFPY="uv run ... python"` then `wfpy x`
# relies on word splitting, which zsh does not do for unquoted parameters — measured, it
# fails with `command not found: uv run --quiet --with pyyaml python`.
# uv first because forge-state needs pyyaml to read frontmatter and the system python3
# usually lacks it; without it every field reads as unknown.
wfpy() {
  if python3 -c "import yaml" 2>/dev/null; then python3 "$@"; else uv run --quiet --with pyyaml python "$@"; fi
}
wfpy "$WF/scripts/forge-state.py" --json [--feature <token>]
```

Resolve the feature from the argument (number / slug / full name) against `features[].slug`,
or infer the one ready to close — `status == in-progress` with `tasks.checked ==
tasks.total`; if ambiguous, list and ask. State which feature you resolved, its `rigor` and
its `rigor_from` (the tier and where it came from, per the rigor-tiers precedence — the
script applies it, you report it).

Do not open the spec directory to work any of this out. The gate below is a field in this
envelope, computed the same way for `/wellforge:status`, `/wellforge:triage` and
`/wellforge:promote` — four commands agreeing because they read one answer, rather than
four implementations that agree until one of them drifts.

## Step 2 — The done gate (tier-aware) — REFUSE if any condition is unmet

**The gate is `done_gate.passes` for this feature.** Do not re-check its parts.

- `passes == true` → proceed to Step 3.
- `passes == false` → **STOP.** Print every entry of `done_gate.failing` **verbatim**, each
  on its own line, then the command that fixes the first one. They are written to be read
  by a human ("3 of 12 tasks unchecked", "QE verdict is FAIL (needs PASS)", "drift: newer
  than tasks.md: spec.md — re-sync with /wellforge:tasks"); paraphrasing them loses the
  numbers, which are the only part that tells someone how far from done they are.
- `passes == null` → the tier is `spike`, whose gate is prose in `brief.md` and not
  machine-checkable. Read `## Findings` yourself and apply the spike rule below.

Also surface any `problems[]` for the feature before closing: a spec whose frontmatter does
not validate should not acquire a `done` on top of a `status: doen`.

The conditions `done_gate` encodes, for reference — this is documentation of what the
script checks, not a second implementation to run:

| Condition                      | Applies at  | Why |
|--------------------------------|-------------|------------------------------------------------------------|
| tasks.md exists                | every tier  | a feature with no task list has nothing to have finished |
| every task checked             | every tier  | unchecked tasks are unfinished work, not optimism |
| tasks.md has >0 tasks          | every tier  | an empty list passes 'all checked' vacuously |
| verdicts.qe == PASS            | every tier  | from the run trace — independent verification, not self-report |
| verdicts.security == PASS      | production  | every production batch is reviewed, so ABSENT means it never ran |
| eval-report.md exists          | production  | the LM-judge half of verification |
| eval-report.md verdict PASS    | production  | a FAIL or absent verdict is not a pass |
| eval is not stale              | production  | an eval that predates the last code change judged a different tree |
| no drift                       | every tier  | spec/plan BODY newer than tasks.md; lifecycle frontmatter edits are not drift |

> **This table is generated.** It is the output of
> `<plugin>/scripts/forge-state.py --explain-gate`, which prints `GATE_CONDITIONS` from the
> function that actually decides. Four documents used to state this gate in their own words
> and no two agreed — this one added a staleness condition nothing computed, the
> `spec-driven` skill omitted security and drift, `rigor-tiers` never mentioned security,
> and `status.md` omitted `verdicts.security` from its envelope, so status printed
> "→ /wellforge:done" for features that `/wellforge:done` then refused. If you change a
> condition, change it in `done_gate()` and paste this table again.

Notes the table cannot carry:

- **A lifecycle frontmatter edit is never drift.** `status`, `done`, `approved`,
  `superseded_by`, `archive_reason`, `rigor` and `plugin` record where the feature *is*,
  not what it asks for. This matters here more than anywhere: THIS command writes
  `status: done` as its last action, which once made spec.md newer than tasks.md and
  refused the transition it had just performed. Do not re-run `/wellforge:tasks` after a
  status change.

- **`mvp`** applies the "every tier" rows only — no security verdict, no eval. mvp's bar is
  QE, not the LM-judge.
- **A missing verdict is not a pass.** `verdicts.security == null` at `production` means the
  review never ran (`config/security-triggers.yml` sets `always_at_tier: [production]`), so
  the gate treats absent exactly like FAIL. Absent → `/wellforge:implement` (its Step 3b
  dispatches the reviewer); FAIL → fix the findings first. A feature can pass every test and
  still ship an unreviewed auth change.
- **Staleness** compares `eval-report.md`'s timestamp against the newest change to code —
  everything outside `specs/` and `.forge/` — using git, or mtime for files with uncommitted
  changes. An eval that predates the last code change judged a different tree.
- **`spike`** — `done_gate.passes` is `null` by design: a spike closes through its
  `brief.md`, not tasks/QE/eval, and no script can read whether a finding answers a
  question. The condition is that `## Findings` is filled and the spike's question answered.
  (Step 3 does the write, on the brief rather than a spec.) If it proved out and should
  become real, suggest `/wellforge:promote` alongside the close.

## Step 3 — Close

Only when the gate passes: set the spec (or brief) frontmatter `status: done` and add
`done: <today>` — **both, at every tier**, whoever called. Change nothing else: this
procedure only flips the status. A caller that also owns another field (e.g.
`/wellforge:promote` setting `rigor: production`) writes that itself, before calling you.

## Step 4 — Report

State: feature, tier, the gate conditions that passed **with evidence** (task count, QE
verdict, eval score/date), and that status is now `done`. If a spike proved out, suggest
`/wellforge:promote`.

## Hard rules

- **Refuse** to close a feature whose gate isn't met — name the missing condition; never set
  done on faith. This is the single guarded place the `done` transition lives.
- Never lower a bar to pass the gate — don't ignore a FAIL eval, a failing QE, or an unchecked
  task. An unmet condition is work to do, not a status to force.
- `done` is the calling session's call to record, never an agent's. You verify and flip it
  here; agents only ever produced the artifacts you're checking.
- **A promoted feature is gated at its NEW tier.** `mvp → production` does not inherit the
  mvp close: the production branch runs in full, so an eval PASS and a fresh QE are required
  even though the feature was already `done` as an mvp.
- **A hook enforces this now, not just this document.** `post-spec-guard.sh` (PostToolUse
  on Write/Edit/MultiEdit) re-checks any edit to a spec's or brief's frontmatter: writing
  `status: done` without `forge-state.py` reporting `done_gate.passes` is refused, and so is
  lowering `rigor:` or reopening a closed feature by edit. It runs *after* the write, so it
  cannot prevent the edit — it blocks the turn and names the revert. **If it fires during
  your run, you did something this command exists to prevent**: revert the frontmatter, run
  the gate properly, and do not re-apply the edit to get past it.
- No other command may write `status: done`, **`status: superseded` or `status: archived`**.
  If you find one that does, that is the bug — this is the single guarded place those transitions live, and
  it is only true while that stays literally true.
- **Neither `superseded` nor `archived` is a way around a failing gate.** If the work is
  finished but cannot pass, that is a defect to fix, not a status to escape into. Use
  `--superseded-by` only when another spec took the work over, and `--archive` only when the
  work is deliberately stopped. An agent must never choose either on its own initiative — a
  human decides to stop work.
