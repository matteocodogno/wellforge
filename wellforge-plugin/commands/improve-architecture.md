---
description: Find shallow modules — ranked, evidenced refactor candidates, routed to the refactor pipeline
argument-hint: [path or module] (default: the whole repo)
---

Find the places where this codebase makes every change more expensive than it should be,
and turn the best one into a refactor someone can approve. The lens is **module depth**: a
deep module hides a lot behind a small interface; a shallow one makes its callers know
almost everything it knows. Agents amplify whichever the codebase already is — a shallow
seam gets copied, a leaked internal gets depended on — so this is worth doing on purpose.

**This command changes no code.** It produces a ranked report and, for the candidate the
user picks, alternative designs. The refactor itself goes through
`/wellforge:orchestrate`'s refactor pipeline, with its human gate and its invariant check.

Scope: $ARGUMENTS

## Step 1 — Read what already constrains the architecture

Before looking for problems, read what was decided on purpose:

- The ADR index in `AGENTS.md`, and the ADRs that touch the scope. **A shape an ADR chose
  is not a candidate** unless the evidence below shows the ADR's own reasoning no longer
  holds — and then the finding is "revisit ADR NNNN", stated as that.
- The stack skill for this project (module layout, boundary rules — Spring Modulith
  boundaries, the Hono layering). A convention the stack skill prescribes is not friction.
- `.claude/context/glossary.md` if present (`domain-modeling` skill): the domain's concepts
  are the best prior for where module boundaries should be.

## Step 2 — Gather evidence, deterministically first

Discovery is a script's job; judgment is the architect's. Run these and hand the output to
the architect rather than asking a frontier model to rediscover it by reading files.

**Churn and co-change** — files that keep changing together across directories are coupled,
whatever the import graph says:

```bash
SCOPE="<path, or . for the repo>"
git log --since="6 months ago" --name-only --pretty=format:'@@%h' -- "$SCOPE" | python3 -c '
import sys, itertools, collections, os
pairs, churn, files = collections.Counter(), collections.Counter(), []
def flush():
    for f in files: churn[f] += 1
    if 2 <= len(files) <= 15:            # a 40-file commit is a rename or a release, not coupling
        for a, b in itertools.combinations(sorted(set(files)), 2):
            if os.path.dirname(a) != os.path.dirname(b): pairs[(a, b)] += 1
for line in sys.stdin:
    line = line.strip()
    if line.startswith("@@"): flush(); files = []
    elif line: files.append(line)
flush()
print("# files changed most often"); [print(f"{n:4d}  {f}") for f, n in churn.most_common(15)]
print("# pairs in different directories that change together (3+ commits)")
[print(f"{n:4d}  {a}  <->  {b}") for (a, b), n in pairs.most_common(20) if n >= 3]
'
```

Read the output with the project in mind: a lockfile, a changelog, a version file or a
generated source pairing with everything is bookkeeping, not coupling — drop those rows.

**What the pipeline already recorded** — if `.forge/runs/` exists (load the
**observability** skill for the schema), read the trace files for the scope's features:
`collision_events` (two tasks that were supposed to be independent touched the same file)
and `drift_events` on `plan.md` (the architecture did not survive implementation) are
coupling and wrong-seam evidence that cost real rework to produce.

**A young repository has no history to read.** Fewer than ~30 commits in scope → say so,
skip co-change, and let the architect work from the code alone, with lower confidence.

## Step 3 — The scan

Spawn `wellforge:architect` in **architecture review mode** (it defines the mode and the
report format itself) with: the scope, the Step 2 output verbatim, and the ADRs and stack
skill from Step 1. It reads the code and returns **at most five candidates**, ranked, each
with the friction, the evidence, the deepening in one sentence, and the blast radius — and
writes the report to `docs/architecture/review-<YYYY-MM-DD>.md`.

One frontier-agent run. Say so before spawning it on a large scope; at a project whose
default tier is `mvp` this is the one command that reaches for the architect anyway,
because the user asked for it.

## Step 4 — Present, and let the user pick one

Relay the ranked candidates compactly: where, the friction, the evidence, what deepening
it would look like, blast radius, confidence. Then ask which — if any — to take further.
**"None" is a fine answer**; the report stays on disk as the backlog.

Do not start designing all five. One at a time: a refactor that is not finished is worse
than one that was never started.

## Step 5 — Design it twice

For the picked candidate, spawn `wellforge:architect` again (review mode, design step) for
**two or three genuinely different interfaces** for the deepened module, plus "leave it
alone" as a named option with its real cost. For each: the interface a caller sees, what
moves behind it, what gets simpler for callers and for tests, what gets harder, the
migration path in behavior-preserving steps. Then its recommendation, and why not the
others.

Put the options to the user. The choice is theirs.

## Step 6 — Route it

- **Chosen design** → hand it to `/wellforge:orchestrate "<refactor goal>"`. It classifies
  as a **refactor**: the architect's mini-plan (current state, target state, invariants
  that must not change), a human gate, behavior-preserving tasks, and QE's before/after
  invariant check. Give the goal one line and point at the report section — the design
  step's output is that mini-plan's starting point, not a replacement for its gate.
- **The decision itself** names rejected alternatives by construction, so it is an ADR:
  offer `wellforge:adr-writer` once the user has chosen (the same bar `/wellforge:plan`
  uses), including when the choice is "leave it alone" for a stated reason — that is the
  ADR that stops the next scan proposing it again.
- Append the outcome to the report: which candidate, which design, where it went.

## Hard rules

- **No code changes, no spec, no plan, no tasks.** This command writes one file —
  `docs/architecture/review-<date>.md` — and ADRs only through `adr-writer` on a yes.
- **No evidence, no candidate.** "This feels tangled" is not a finding. Every candidate
  cites co-change counts, a trace entry, or specific code (path and what it shows).
- **At most five candidates**, and one taken forward at a time.
- **Never propose a rewrite.** A candidate is one module or one seam with a migration path
  made of steps that are each green on their own. "Replace the persistence layer" is not a
  candidate; it is five of them or none.
- **Never relax a boundary to remove friction.** Merging two modules because their
  boundary is annoying, or exposing an internal because callers want it, is the opposite
  of deepening — if that really is the right call it contradicts the stack skill or an
  ADR, and is presented as that.
- A behavior change discovered along the way is **not** part of the refactor: report it as
  a bug or a feature and keep it out of the candidate.
