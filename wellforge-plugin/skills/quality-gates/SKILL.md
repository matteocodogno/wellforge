---
name: quality-gates
description: >
  WellForge quality gates — what CI enforces, where the thresholds live, and how to change
  one. Use when wiring CI into a project, when a gate is red and you need to know whether it
  blocks at this rigor tier, when someone proposes lowering a threshold, when pinning or
  bumping a gates-v* ref, or when the devops agent needs the standard wiring. Authoritative
  reference for the gate catalogue, the central-threshold rule (change by PR to gates/, never
  locally), the security floor that blocks at every tier, and the reusable-workflow calling
  convention.
---

# Quality gates — objective, central, and not yours to lower

Gates are the deterministic half of verification (the LM-judge eval is the other half —
[`rigor-tiers`](../rigor-tiers/SKILL.md)). Their defining property is that **no individual decides whether their own
code passes**: thresholds live centrally, in the gate workflows' `env` blocks under
`gates/`, and change only by PR to that directory.

## The catalogue

| Gate | What it runs |
|---|---|
| `quality-node.yml` | Node/TS: install, lint, typecheck, test + coverage, SAST, dependency audit |
| `quality-jvm.yml` | JVM: compile, ktlint, test, JaCoCo coverage, SAST, dependency audit |
| `security-floor.yml` | Secret scan (gitleaks), hardcoded credentials, CRITICAL-CVE audit |
| `commit-lint.yml` | Conventional Commits over the PR range ([`git-policy`](../git-policy/SKILL.md)) |
| `linear-history.yml` | No merge commits in the PR range ([`git-policy`](../git-policy/SKILL.md)) |
| `quality-eval.yml` | Opt-in LM-judge against the central rubric; needs `ANTHROPIC_API_KEY` |
| `heartbeat-report.yml` | Deduplicated tracking issue for scheduled runs ([`heartbeat`](../heartbeat/SKILL.md)) |

Supporting configs: `gates/configs/semgrep/wellforge.yml` (SAST rules),
`gates/configs/gitleaks.toml`, `gates/configs/eval-rubric.yml` (the rubric — mirrored into
the plugin so an in-session eval can resolve it), `gates/scripts/check-jacoco.py`,
`check-commit-msg.py`, `run-eval.py`.

## Referenced, never copied

Generated projects **call** the gates as reusable workflows; they never vendor a copy:

```yaml
jobs:
  quality:
    uses: <gates-repo>/.github/workflows/quality-node.yml@gates-v11
    with:
      gates-repo: <owner/repo>
      gates-ref: gates-v11
      working-directory: backend
```

Always pass `gates-repo` **and** `gates-ref` explicitly, and pin to a `gates-v*` tag. A call
that omits them falls back to the gate's own default — which is how a pilot project once ran
2026-06 configs against a current checkout and failed with an unexplained semgrep exit 7.
The pin a project is on must be readable in the project's own workflow file.

The `gates-v*` series is **separate from the template `vX.Y.Z` series** and moves
independently: a template release does not carry a gates bump to existing projects (the ref
is a recorded copier answer). `/wellforge:upgrade` raises it as an explicit, raise-only step.

## Tier behaviour — what blocks, and what only reports

From [`rigor-tiers`](../rigor-tiers/SKILL.md); repeated here because this is where people look when a gate is red:

| Tier | Blocking | Advisory |
|---|---|---|
| `spike` | security floor, plus history hygiene | lint, typecheck, build |
| `mvp` | security floor, SAST-high, lint, typecheck, history hygiene | coverage (reported as a gap) |
| `production` | everything, incl. 80% line coverage and the eval | — |

**The security floor blocks at every tier, including spike.** Fast never means "leaks
credentials". History hygiene is tier-independent for a different reason: it cannot be
repaired after the fact without rewriting published history.

## Changing a threshold

1. Open a PR to `gates/` (or `.github/workflows/`) with the new value **and the evidence** —
   what the number is today, why the new one is right, what it would have caught or missed.
2. Never change it locally, per project, or "temporarily". A threshold one project can lower
   is not a gate, and a gate everyone overrides is worse than no gate at all: it costs the
   same and proves nothing.
3. Ratchets go **up**. The adoption path deliberately starts a brownfield project at its
   *measured* baseline rather than at 80%, then raises it — a gate set above reality on day
   one gets disabled by week two.

A red gate is never fixed by editing the gate. The two legitimate responses are: fix the
code, or bring evidence that the threshold is wrong. QE reports a lowered threshold as a
FAIL, not as a pass.
