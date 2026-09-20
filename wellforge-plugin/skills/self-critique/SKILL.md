---
name: self-critique
description: >
  WellForge self-critique pass — the ONE bounded review an agent runs on its own artifact
  before handing it to a human gate, to QE, or to the evaluator. Use whenever you are about
  to return a spec.md, plan.md, design.md, tasks.md or an implemented task, whether from an
  agent or from the main loop (/wellforge:spec, :plan, :design, :tasks). Authoritative
  reference for the one-pass rule, the per-artifact failure checklists, the tier gating, and
  the hard line between critiquing your own work and verifying it — self-critique never
  approves, never blocks, and never substitutes for QE or the eval.
---

# Self-critique — the pass before you hand your work over

Every WellForge artifact is checked by someone who did not write it: spec and plan by the
human approval gates, code by QE's deterministic gates, the finished feature by the
evaluator's adversarial rubric. That independence is the design and nothing here weakens it.

But an expensive reviewer's round is a wasteful way to discover that an AC has no observable
outcome, that a contract is prose, or that a test asserts a mock. **Self-critique raises the
floor of what reaches the verifier.** The verifier stays the authority on whether it passes.

## The three rules

1. **One pass, never a loop.** Draft → critique → revise → hand over. You do not critique
   your revision. Unbounded self-refinement burns tokens, drifts toward your own taste, and
   converges on an artifact that *reads* well rather than one that is right. Still uneasy
   after the pass? That is a note for the reviewer, not a third draft.
2. **Against the checklist, not against vibes.** Walk your artifact's list item by item.
   "Looks good" on every item means the pass did not happen — either name what you fixed, or
   name what you deliberately kept and why.
3. **Never self-approve.** The pass changes content. It never sets `status:`, never checks a
   box, never declares anything done or verified. Approval is the human's; PASS is QE's and
   the evaluator's. An artifact is not stronger evidence because its author reviewed it.

## When it runs — tier-gated

| Tier | Self-critique |
|---|---|
| `spike` | **off.** No agents run, and the tier's point is the shortest path. Its substitute already exists: the honest `// SPIKE:` marker — record the corner you cut instead of fixing it. |
| `mvp` | **on**, checklist only, fixes applied inline, one line in the return. |
| `production` | **on**, full checklist. |

Cost is one short pass over an artifact already in context — it buys back the human gate
round, the QE round, or the eval round that the same defect would otherwise cost.

## Checklists

Each item is a failure mode observed to survive an author's own read. Fix it, or record it
(as an open question, a risk, an ADR candidate, or a line in your return) — never both
ignore it and stay silent.

### spec.md — `product-owner`, `/wellforge:spec`

- **Unverifiable AC** — a QE could not turn it into a test without asking you something.
  "fast", "user-friendly", "handles errors gracefully", "appropriate". Rewrite with an
  observable outcome, or move the unknown to `## Open questions`.
- **Hidden AND** — one AC asserting two things. It cannot fail cleanly; split it.
- **Solutioning** — a component, table, endpoint, library or file path has appeared in the
  WHAT. Delete it, or move a caller-supplied constraint verbatim under `## Constraints`.
- **Orphan** — a user story with no AC, or an AC serving no story.
- **Scope boundary missing** — non-goals empty, or restating the problem. The real test:
  what would a reasonable reader assume is included that isn't? That sentence is the entry.
- **Invented vocabulary** — a term that appears nowhere in the repo, the glossary, or
  neighbouring specs, where the project already has a word for it.
- **Assumption smuggled in** — you could not ask, so you guessed, and the guess is now
  phrased as a fact in an AC. It belongs in `## Open questions` with the assumption named.

### plan.md — `architect`, `/wellforge:plan`

- **AC→test gap** — an AC with no row, or a row whose test would pass while the AC is
  violated. An AC you cannot map is a spec or plan bug: say which.
- **Prose contract** — "returns the user's data" instead of a shape, with the error cases
  and nullability spelled out. The consumer is another agent's code, not a reader.
- **Idealized codebase** — the plan targets a module, layer or helper you never opened.
  Every component you claim to touch needs a real path you actually read.
- **Security flag by reflex** — you wrote NO. Re-run the trigger list (auth, PII/personal
  data, file upload, outbound calls, payments, regulated data). In doubt, YES.
- **Risk without a check** — a risk with no mitigation and no early signal is a worry.
- **Unstated rejection** — you chose a shape and did not say what you rejected. A reviewer
  cannot approve a decision whose alternatives are invisible.
- **Buried ADR candidate** — a choice that will constrain future work is sitting in the
  prose instead of `## ADR candidates`.

### design.md — `designer`, `/wellforge:design`

- **Missing state** — any screen without its loading, empty and error states. This is where
  UX dies and where frontend tasks get derived wrong.
- **NEW without justification**, or a NEW component that duplicates an existing one under a
  different name — re-read the inventory before trusting your own table.
- **Flow/AC mismatch** — a flow no AC asks for (scope creep: report it, don't design it), or
  an AC with no UI surface.
- **a11y as a sentence** — accessibility stated once in prose instead of per screen
  (keyboard path, focus management, ARIA, contrast).
- Do **not** re-run visual direction here: `frontend-design` Pass 2 *is* this pass for the
  token system, and running it twice just relitigates taste.

### tasks.md — `/wellforge:tasks`

- **`done when:` not runnable** — it must be a check someone can execute and observe, not
  "the endpoint works".
- **`touch:` that lies** — every file the task will create or modify, globs included for
  generated families (migrations, changelogs). `touch:` is a scheduling edge
  ([[worktree-isolation]]): an incomplete list is a collision you have already scheduled.
- **Wrong edge** — a missing `deps:` where one task consumes another's contract, or a false
  one that serializes work for no reason.
- **Task too large to verify** — one `done when:` covering three outcomes. Split it.
- **Domain mislabeled** — a task tagged frontend whose `touch:` is backend paths. The label
  picks the agent.
- **Coverage** — an AC no task serves, or a task no AC asks for.

### code — `frontend-dev`, `backend-dev`, `devops`

Green tests are the floor, not the critique. Re-read your own diff before you return:

- **Test that cannot fail** — it asserts a mock, restates the implementation, or never
  touches the AC's actual outcome. The check: would this test fail if you broke the
  behavior? If you cannot say yes, it is not a test.
- **Happy path only** — the ACs' error cases and the contract's error shapes are untested.
- **Shape drift** — a field name, nullability or error case differing from plan.md. The
  consumer is another agent's code; this is drift, not a detail.
- **Silent corner-cut** — a default, a guard, a widened type, a swallowed `catch`, a raised
  timeout, a `.skip`/`@Disabled`, a loosened threshold added to make something pass. Either
  it is the root-cause fix ([[systematic-debugging]]) or it is a report. Never a quiet commit.
- **Scope leak** — files touched outside the task's `touch:` list. In a worktree that is also
  an isolation breach.
- **Convention drift** — the neighbouring code handles errors, logs, or names things another
  way, and you did it your way.

## Reporting the pass

One line at the end of your return, so the reviewer sees what was already caught:

```
Self-critique: 2 fixed (AC-1.2 made observable; missing error state on the detail screen),
1 kept (AC-2.1 vague on retry count — raised as an open question instead).
```

Nothing found → `Self-critique: clean`. Expect a verifier to disagree with that sometimes;
that is the system working, not a failure of the pass.

## What this is NOT

- **Not a second opinion.** You are the same model with the same blind spots. This pass
  catches checklist misses — it does not catch the failure you could not see while writing.
  That is why WellForge keeps two independent verifiers (QE deterministic, evaluator
  adversarial) and the human gates.
- **Not a quality gate.** It blocks nothing and gates nothing. A clean self-critique is never
  evidence in a QE verdict or an eval score — an evaluator that credits the author's own
  review is being gamed by the author.
- **Not a reason to skip a stage.** The human gates, the drift rule, QE and the eval run
  exactly as before. Fewer stages come only from a declared rigor tier ([[rigor-tiers]]).

Related: [[spec-driven]] (the artifacts and their formats), [[rigor-tiers]] (the tier gating
and the effort cue this pass sits beside), [[systematic-debugging]] (the rule the code
checklist's corner-cut item enforces), [[frontend-design]] (its Pass 2 is this pass for
visual direction), [[worktree-isolation]] (why `touch:` accuracy is a safety property).
