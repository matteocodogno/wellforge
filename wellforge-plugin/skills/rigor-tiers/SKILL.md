---
name: rigor-tiers
description: >
  WellForge rigor tiers — match ceremony to stakes. The spike / mvp / production vocabulary
  that governs how much of the pipeline runs (agents, approval gates, models, quality gates,
  eval) for a feature. Use whenever running /wellforge:spike, when /wellforge:orchestrate or
  /wellforge:implement is given a --mode, when reading a feature's `rigor:` frontmatter, or
  when deciding how strict gates should be. Authoritative reference for the three tiers, the
  non-negotiable security floor, advisory-gate behavior, and the rigor precedence rule.
---

# Rigor tiers — velocity vs. assurance

Full WellForge rigor (7 agents, 2 approval gates, frontier models, 80% coverage, LM-judge
eval) is right for production and wasteful for a feasibility spike that may be thrown away.
A **rigor tier** matches ceremony to stakes.

**Principle: don't lower the bar — defer it, explicitly and reversibly.** The one place
this is tested in practice is a `--mode` flag below a feature's recorded tier: the flag wins
for that run, so the rule is enforced by *announcement* rather than refusal — see
"Resolving the tier and terse at dispatch" below. A downgrade that is stated, scoped to one
run, and unable to close the feature is deferral; the same downgrade unannounced is the
silent lowering this principle exists to prevent. Lower rigor is a
*declared, recorded, promotable* lifecycle stage, never a silent corner-cut. A lower tier is
a tracked debt (the `rigor:` frontmatter), paid by `/wellforge:promote` when the work becomes
real. The failure mode this design exists to prevent: a spike silently becoming production.

## The three tiers

| Tier | Intent | Throwaway-ok? |
|---|---|---|
| `spike` | Feasibility / business-model experiment | Yes — expected |
| `mvp` | First real release to validate with users | No, but debt is acknowledged |
| `production` | Full rigor (the default everywhere today) | No |

## What each tier tunes

| Lever | `spike` | `mvp` | `production` |
|---|---|---|---|
| Pipeline depth | **main loop** builds from a brief; NO subagents | PO → tasks → dev agents → light QE (no separate architect/designer) | full 7-agent team |
| Human gates | 0 (autonomous; human reviews the result) | 1 (spec approval) | 2 (spec + plan) |
| Spec ceremony | one `brief.md` | `spec.md` + `tasks.md` (plan folded into tasks) | spec + plan + design + tasks |
| Models | inherits the session model (no per-agent routing) | mid agents only — frontier architect/evaluator are NOT spawned | full `model-routing.yml` |
| Quality gates | lint + typecheck + build, **advisory** | + smoke tests + SAST-high **blocking**; coverage advisory | full 80% coverage + SAST + eval |
| Eval (LM-judge) | off | off | on — the gate into `done` |
| Effort cue | minimal (bias to speed) | moderate (pragmatic) | full (deliberate) — see below |
| Self-critique pass | off (`// SPIKE:` markers instead) | on (checklist) | on (full) — see [`self-critique`](../self-critique/SKILL.md) |
| Test-first (dev agents) | off | on for the behaviors the ACs name | on for every test-strategy row — see [`tdd`](../tdd/SKILL.md) |

`mvp` gets cheaper not by re-tiering agents (frontmatter `model:` is fixed per agent) but by
**composition** — it simply never spawns the frontier agents (architect, evaluator). See
`config/model-routing.yml`.

## Effort cue — how hard to think, gated by tier

Distinct from *which* model runs (routing) and *which* agents run (composition): the effort
cue is *how hard the chosen model deliberates*. It is **not** a per-agent config field (that
would break tool-neutrality) — it's a plain-text directive the dispatching command adds to
each agent's task prompt, derived from the resolved rigor tier. Tool-portable (just words),
zero new config. Most useful for agents that span tiers (PO, dev agents, QE) and for the
spike main loop; the frontier agents (architect, evaluator) run only at `production`, so
their effort is already "full".

Prepend the tier's cue to each dispatched agent's task (and, for `spike`, the main loop
applies it to itself):

- **`spike`** — "Effort: minimal. Take the shortest path that answers the question. No
  gold-plating, no exhaustive edge-case analysis; leave `// SPIKE:` where you cut a corner.
  Bias hard to speed."
- **`mvp`** — "Effort: moderate. Be pragmatic and correct on the main paths; cover the
  obvious error cases but NOTE deferred edge cases rather than solving them all now."
- **`production`** — "Effort: full. Reason carefully about trade-offs, edge/error/failure
  modes; verification is adversarial. Thoroughness over speed."

This is a nudge, not a hard budget — honest about the seam. Where a tool exposes a real
thinking-budget parameter, a future `model-tiers.yml`-style mapping could bind these levels to
it; until then the directive is the mechanism.

## Resolving the tier and terse at dispatch — the Step 0 every command runs

`/wellforge:implement`, `/wellforge:orchestrate` and `/wellforge:promote` open with the same
resolution. It is defined **here**; each command cites this section and states only its own
deviation (below).

1. **Tier precedence**, highest first: the `--mode` flag > the feature's `rigor:` frontmatter
   > the project default (`.forge/manifest.json` `rigor` if scaffolded, else
   `.forge/adoption.json` `rigor` if adopted) > `production`.
2. **Strip the matched `--mode` token** from the arguments before parsing the rest.
3. **State the resolved tier and where it came from, before doing anything.** A tier nobody
   announced is a tier nobody can question.
4. **A `--mode` BELOW the feature's recorded `rigor:` is a downgrade — say so, every time.**
   The flag wins (there are legitimate reasons: implementing two tasks quickly before the
   full pipeline, reproducing something cheaply), but it sits against this skill's own
   *defer-don't-lower* principle, so it may never happen quietly. Print, before any work:

   ```
   ⚠ Running at mvp; this feature is recorded as production.
     Skipped this run: architect + designer, the LM-judge eval, blocking coverage.
     NOT changed: the feature's rigor: stays production, and /wellforge:done still gates
     at production — this run cannot close it.
     Raise the tier for real with /wellforge:promote, not with a flag.
   ```

   Name the specific stages the downgrade skips, not just the tier names — "mvp" means
   nothing to someone who has to decide whether that is acceptable right now. Record it in
   the run trace (`rigor_recorded`, [`observability`](../observability/SKILL.md)) so the trajectory shows the run was
   cheaper than the feature's standard; an evaluator reading that trace should see it too.

   A `--mode` **above** the recorded tier needs no warning — more verification is never the
   surprise. State it like any other resolution and move on.

   The **security floor blocks in every tier regardless** (below), so a downgrade reduces
   process, never safety.
5. **Terse is an orthogonal axis**, not a property of a tier: read a `--terse` / `--no-terse`
   token (terse skill), strip it too, and **state the resolved boolean**. Default **OFF**
   everywhere except `/wellforge:spike`, which defaults it **ON**.

Per-command deviations, and nothing else:

| Command | `spike` resolves to |
|---|---|
| `/wellforge:implement` | treated as `mvp` — a spike has no `tasks.md` to implement |
| `/wellforge:orchestrate` | hand off to the `/wellforge:spike` procedure and stop, forwarding any terse token unchanged |
| `/wellforge:promote` | n/a — the tier is the *source*; agents work at the **target** tier's effort cue |

## Run preflight — before the first agent is spent

Defined once here for `orchestrate`, `implement` and `promote` at `mvp` and `production`
(`spike` skips it — no agents, nothing to strand). An agent that discovers the environment
is broken does so by stopping and reporting, which costs a dispatch each time and teaches
the next agent nothing. Every row below is a command and its output, run by the main loop
**before** anything is dispatched; a belief is not a row.

| Row | When | The check | Red means |
|---|---|---|---|
| **baseline** | always | the project's own gate command (`mise run check`, or lint + typecheck + tests) on the commit the feature branch starts from | **stop.** A red baseline is its own piece of work, on its own branch (bugfix pipeline). It is never repaired inside the feature. |
| **commit** | always | `git status` clean; when `commit.gpgsign` is true, a signing probe that touches no ref: `git commit-tree -S 'HEAD^{tree}' -p HEAD -m probe` | stop — the user fixes signing; an agent cannot. |
| **worktree base** | a batch of ≥2 will be dispatched | `worktree.baseRef` is `"head"` in the effective settings ([`worktree-isolation`](../worktree-isolation/SKILL.md)) | set it, or the batch runs sequentially in the main tree. A worktree cut from the default branch has no spec in it. |
| **app starts** | QE will need the running app (any UI feature; an API it must probe live) | start it the way the project documents and hit its health/landing route; every secret the start reads resolved to non-empty | stop — an environment fault now is one line; at QE it is a blocked verdict. |
| **browser** | UI feature | one real call to the browser tool against the running app (navigate + snapshot) | stop, or the user states now that the UI pass will be done by hand (see BLOCKED below). |
| **test identity** | the feature sits behind a login | the credentials QE will use, proven by signing in once — a seeded user, not a registration QE has to be permitted to perform | stop — the user seeds one. |

State the result compactly before the first dispatch, like the worktree preflight:

```
run preflight — 012-export, production, UI: yes
  baseline       green   mise run check @ 4f1c2aa (2m10s)
  commit         green   signed probe ok
  worktree base  green   baseRef: head
  app starts     green   :5173 → 200, 6/6 secrets resolved
  browser        green   navigate + snapshot ok
  test identity  RED     no seeded user; POST /register denied by permissions
```

**A red row is put to the user, once, never routed to an agent** and never worked around.
The two honest answers are *fix it and re-run the preflight* or *stop*. There is no
"proceed anyway" at `production`: every red row here is a check the done gate will need
green, so proceeding only moves the stop to the most expensive point in the run. At `mvp` a
red **app starts / browser / test identity** row may be accepted — QE-light does not need
them — and is recorded in `env_faults`; **baseline** and **commit** are never accepted.

Rows that depend on the spec (is there a UI? a login?) are answered as soon as the spec
says so — at the latest before the first dev agent, when fixing them is still free.

## Routing a QE FAIL — triage before you loop

Also defined once here, because all three commands loop on a QE verdict and a copy of this
table is a copy that drifts. On FAIL, route **each defect to its true owner** — never
everything to a dev:

| Defect | Owner | Why |
|---|---|---|
| **Environment fault** | nobody — it is not a defect | Fix the isolation or the env carry-in and re-run ([`worktree-isolation`](../worktree-isolation/SKILL.md)). Never spend a fix round on it. |
| Code defect | the owning dev agent | Include the failing test path. |
| AC wrong / missing / untestable | `wellforge:product-owner` | Drift: amend the spec, re-approve if scope changed, re-sync `/wellforge:tasks`. |
| Wrong contract / architecture / data model | `wellforge:architect` | Drift: amend the plan, re-sync tasks. (At `mvp` there is no architect — route to the PO.) |
| Missing designed state or a11y requirement | `wellforge:designer` | Only when a `design.md` exists. |

Then re-run QE. **Maximum 2 fix rounds**, then stop and escalate with the verdict table.

### What a round is, and what does not reset it

A **fix round** is one dispatch of the owning agents for a QE verdict's defects, followed by
one QE re-run. The count belongs to **the feature**, for as long as it is `in-progress` —
not to the command invocation, the session, or the last thing the user said. Read it back
from the run traces (`fix_rounds.used`, [`observability`](../observability/SKILL.md)) when a run resumes.

- **A user instruction does not reset the counter.** "Go on" after an escalation grants
  **one** further round, for the defects named in the escalation, and is recorded as an
  extension (`fix_rounds.extensions[]`). The next FAIL escalates again. A cap that an
  ordinary reply clears is not a cap; five rounds reached two at a time is this rule absent.
- **A new defect does not reset it either** — see the next section, because it is the more
  important signal.
- The escalation is one question with real exits, not a status report: **one more round**
  for named defects · **split** — the open defects become a follow-up spec and this feature's
  scope is amended to exclude them, through the PO and gate 1 again (never by editing an AC
  until it passes) · **stop** and leave the feature `in-progress`. Lowering the bar is not on
  the list at any tier.

### A defect the last pass missed is a finding about QE, not about the code

When a re-run reports a defect that **the fix did not introduce** — it was there at the
previous pass and nobody saw it — the loop is not converging on the code, it is discovering
the feature one instance at a time. Another incremental "check the fix" pass will find
exactly one more. Instead:

- The next QE dispatch is a **full sweep by a fresh agent** — every AC, every `design.md`
  state and placement — told to list *everything* before anything is fixed. It costs more
  than a fix check and less than three of them.
- QE files defects **by class, with placements**: "column overflows at 360px — queries
  table ✗, detail card ✗, export dialog ✓", never the first instance it met. The fix brief
  says *fix the class, verify every placement listed*.
- **Hand the dev QE's defect text, verbatim, plus the failing test path. Add no scoping of
  your own.** "Leave the detail card unchanged" in a brief is an instruction the agent will
  follow straight past the same bug.
- A fix to something only visible when rendered is not fixed until it has been rendered.
  A dev agent that could not render it says so (`RENDERED: no`), and QE checks it first.

### BLOCKED — the third verdict

QE returns `PASS`, `FAIL` or **`BLOCKED`**: one or more required checks **could not be
executed** (no browser tool, the app would not start, no test identity) and nothing that
did run failed. It is not a pass with remarks — that verdict does not exist — and it is not
a FAIL: there is no defect and no owning agent.

- BLOCKED **consumes no fix round** and is recorded in `env_faults`; `verdicts.qe` stays
  **absent** in the trace, which the done gate already reads as not-a-pass.
- Its exit is the environment: fix what the blocked rows name, then re-run QE **for those
  rows only**. It is a run-preflight row that was skipped or went red afterwards — add the
  row if the preflight had none.
- **Nothing downstream runs on BLOCKED.** No evaluator: an eval of unverified work fails on
  the missing evidence, which was known before it was dispatched, and spends a frontier
  agent to learn nothing.
- **A check a human performed is evidence; a check nobody performed is not.** When a row
  genuinely cannot be automated here, the user may run it by hand and report the result;
  QE records it in `qe-report.md` as `verified by: <user>, <date>, <what was done>` and the
  row counts. "Waive it" without anyone having looked is not available at `production`.

### Fresh agents, not resumed ones

Every round is a **fresh dispatch** handed file paths: the spec dir, `qe-report.md`, the
defect list. Resume an agent only to ask about the output it has *just* returned. An agent
resumed across rounds carries every earlier round in its context — a QE at 900k tokens is
slower, costlier and measurably less careful than a new one reading a 200-line report — and
it is the handoff contract's own rule: what the next stage needs is on disk, or it is lost.

This cap **composes** with the `systematic-debugging` skill's **3-attempts-on-one-symptom**
stop — whichever trips first, stop. An agent reporting three failed attempts is an
architecture signal: route it to the architect, don't spend the second round re-dispatching
the same fix.

At `mvp`, QE runs in **advisory** mode (quality-engineer agent): only SAST-high, lint,
typecheck and the security floor block; coverage is reported as a gap, never as a ✗. The
triage above applies to the blocking rows only.

## Self-critique — cheap at every tier that runs an agent

One bounded pass over your own artifact before handing it over ([`self-critique`](../self-critique/SKILL.md)). It sits
beside the effort cue and is *not* a gate: it never approves, never blocks, and never counts
as evidence in a QE or eval verdict — it only stops known, checklist-shaped defects from
consuming a reviewer's round. `spike` skips it (no agents, shortest path — the `// SPIKE:`
marker records the cut instead); `mvp` and `production` run it, once.

## Test-first — on wherever a dev agent implements

`frontend-dev` and `backend-dev` write the test before the code it proves ([`tdd`](../tdd/SKILL.md)): one
behavior per cycle, a red seen to fail on the assertion, then green, then refactor. Like the
pass above it is a discipline, *not* a gate — the `TDD:` line in an agent's return is its own
account and never evidence in a QE or eval verdict. `spike` skips it (no agents, and no gate
there runs tests); `mvp` drives the behaviors the ACs name; `production` drives every row of
the plan's test strategy. What a spike skipped, `/wellforge:promote` backfills as ordinary
tests — test-first cannot be applied retroactively, and nobody should claim it was.

## Budgets — advisory tripwires, per tier

`config/rigor-budgets.yml` gives each tier a soft cost ceiling per feature and per run, and
a wall-clock ceiling per implement batch. `/wellforge:triage` surfaces a feature over its
ceiling; `run-report.py --budget` shows spend vs ceiling with the agent that consumed most.

| Tier | per feature | per run | per batch |
|---|---|---|---|
| `spike` | $1.00 | $0.50 | 30 min |
| `mvp` | $4.00 | $1.50 | 60 min |
| `production` | $12.00 | $4.00 | 120 min |

Three things about these numbers, all of which matter more than the numbers:

- **`advisory_only: true`. They never block.** A budget that failed a gate would be the
  surface-never-ship rule broken by the very signal meant to respect it — and it would be
  built on an estimate.
- **The estimate undercounts**, structurally: subagent stops only, no main loop, no cache
  (observability skill). So these are *relative* tripwires — "several times what a feature
  of this tier usually costs" — not dollars. `/usage` is the bill.
- **No token data is not "under budget".** A feature whose trace captured nothing reports
  `unknown`, and triage is told to count it in a footer rather than list it as a finding.
  Missing data reading as reassurance is the failure mode these numbers exist to avoid.

The spike wall-clock ceiling is the one that is not really about money: a spike still
running after half a day has stopped being a spike, and that is a finding about the tier's
premise.

## Security floor — non-negotiable, ALL tiers (incl. spike)

These always run and always **block**, regardless of tier. Fast must never mean "leaks
credentials":

- **Secret scan** (gitleaks, pinned and checksum-verified) over the **full git history** —
  no committed secrets, ever, at any tier. This is also the "no hardcoded credentials"
  check: a secret scanner is what finds a credential pasted into code.

That is the floor — one automated check, and it is the one that cannot be undone after the
fact (a leaked credential is rotated, never unpublished).

**Dependency CVEs are NOT in the floor**, although this section used to claim they were.
`security-floor.yml` is stack-neutral and blocks everywhere, and no CVE tool satisfies both
today: `pnpm audit` is Node-only, and `osv-scanner` cannot separate dev from production
dependencies (measured on 2.6.0 — no flag, no group in its JSON), so blocking on it would
contradict `quality-node.yml`'s own `--prod` policy and red-light every fresh scaffold.
CVE audits therefore run in `quality-node.yml` / `quality-jvm.yml`, at `mvp` and
`production` only — see the `quality-gates` skill. **A `spike` has no CVE gate in CI**;
`/wellforge:spike` checks critical advisories locally, and local is not a gate.

A tier may make coverage/lint/SAST-medium advisory; it may NEVER waive the floor.

**History hygiene is tier-independent too** — for the same reason: it cannot be repaired after
the fact without rewriting published history. Every WellForge repo, at every tier, keeps a
**linear history** (no merge commits — rebase, then `--ff-only`) and **Conventional Commits**.
`linear-history.yml`, `commit-lint.yml` and `security-floor.yml` are therefore called from
generated `quality.yml` **outside the rigor branch entirely** — not duplicated into each
side of it, which is how `security-floor` came to run only at `spike` and `commit-lint` only
at `mvp`/`production`. See `gates/README.md` → "Linear history gate".

## The done gate is defined in one place

Each tier's exit condition is computed by `forge-state.py done_gate()` and printed by
`forge-state.py --explain-gate`. This skill deliberately does not restate the conditions:
it used to, it never mentioned the security verdict, and a tier document that disagrees
with the gate is worse than one that points at it. See
[`/wellforge:done`](../../commands/done.md) for the generated table.

What belongs *here* is the tier shape: `production` adds the security verdict and the eval
(including its staleness check) on top of the every-tier conditions; `mvp` has neither;
`spike` is not machine-checkable at all.

## Advisory vs. blocking gates

Outside the security floor, lower tiers **run** the gates but report results as **advisory** —
the same mechanism as the brownfield ratchet baseline: measure, show the gap-to-target, do not
block. The numbers are still visible (so the debt is honest); they just don't fail the run.

- `spike`: lint/typecheck/build advisory. Report failures; don't stop on them.
- `mvp`: SAST-high blocks; coverage is advisory (reported with gap-to-80%); lint/typecheck block.
- `production`: everything blocks (today's behavior).

## `rigor:` frontmatter & precedence

A feature records its tier in its `spec.md`/`brief.md` frontmatter: `rigor: spike|mvp|production`.
Absent ⇒ `production` (safe default — full rigor unless explicitly relaxed).

Resolution precedence, highest wins:

1. **Invocation** — `--mode <tier>` on the command.
2. **Feature** — the `rigor:` frontmatter of the feature being worked.
3. **Project default** — `.forge/manifest.json` `rigor` (scaffolded projects) or
   `.forge/adoption.json` `rigor` (adopted/brownfield projects, set by `/wellforge:adopt`).

State the resolved tier before acting, and why (which level supplied it).

## Graduation

A lower tier is debt, not a destination. `/wellforge:promote <feature> --to mvp|production`
(or `--project --to …` for the scaffold default) raises the tier and pays the deferred rigor:
brief → spec → retro plan, backfill tests to the coverage floor, flip advisory gates to
blocking, and run the eval. Production rigor is reached ONLY through promote, and only on an
eval PASS — never implicitly. Promotion only RAISES; a tier is never lowered via promote.

## Visibility (the guardrail)

A lower tier must never be mistaken for production-grade. Always:

- Print the resolved tier at the start of a run.
- For `spike`/`mvp`, end with a one-line reminder that gates were advisory and the work is
  unpromoted (e.g. "rigor: spike — gates advisory, not production-ready; `/wellforge:promote`
  to graduate").
