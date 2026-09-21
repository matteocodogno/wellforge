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
| `security-floor.yml` | Secret scan over full git history (gitleaks, pinned + checksum-verified). That is its whole scope — see "What the floor is" below |
| `commit-lint.yml` | Conventional Commits over the PR range ([`git-policy`](../git-policy/SKILL.md)) |
| `linear-history.yml` | No merge commits in the PR range ([`git-policy`](../git-policy/SKILL.md)) |
| `quality-eval.yml` | Opt-in LM-judge against the central rubric; needs `ANTHROPIC_API_KEY` |
| `heartbeat-report.yml` | Deduplicated tracking issue for scheduled runs ([`heartbeat`](../heartbeat/SKILL.md)) |

### When the owasp-reviewer runs — `config/security-triggers.yml`

The security floor blocks at every tier, but the floor is an *automated* check: the secret
scan (which is also the "no hardcoded credentials" check — that is what a secret scanner
does). The **specialist review** — OWASP Top 10 against the
actual diff — used to run only when someone thought to ask for it, which is not a gate.

`wellforge-plugin/config/security-triggers.yml` makes the dispatch a property of the task
graph: path globs (`**/auth/**`, `**/routes/**`, `**/migrations/**`, `**/*Controller*.kt`,
`**/*.sql`, …) plus substrings that imply a sensitive surface (`upload`, `payment`, `token`,
`session`, `password`, `secret`, `credential`), and `always_at_tier: [production]`.

`scripts/security-triggers.py` evaluates it against the **union** of the batch's declared
`touch:` globs and the real `git diff --name-only` — intent and reality, because a file
nobody declared is exactly the one worth reviewing. `/wellforge:implement` (Step 3b) and
`/wellforge:orchestrate` call it after integration and before QE; the outcome is recorded as
`verdicts.security` in the run trace, and at `production` a missing verdict is a failing
done-gate condition (absent ≠ passed).

Changing the trigger list is like changing a threshold: a PR, with the reason. Widening it
costs one mid-tier agent per matched batch; narrowing it removes a review nobody will notice
is missing.

### What the floor is — and the hole it does not cover

`security-floor.yml` runs **one** thing: gitleaks over the full git history, with
`gates/configs/gitleaks.toml`. It is called unconditionally by every generated
`quality.yml`, at every tier.

It used to be described here as "secret scan, hardcoded credentials, CRITICAL-CVE audit".
The first two are the same check. The third it has never run, and it should not:

- The floor is **stack-neutral** — one workflow serves all three presets. `pnpm audit` would
  make it uniform in name and Node-only in fact.
- `osv-scanner` *is* stack-neutral (`quality-jvm.yml` already uses it), but it reports dev
  and production dependencies alike: no `--prod` flag, no dependency group in its JSON
  (measured on 2.6.0). Blocking on that contradicts `quality-node.yml`'s own
  `pnpm audit --prod` policy, and it fails every fresh scaffold today on `vitest@2.1.9` /
  GHSA-5xrq-8626-4rwp (CVSS 9.8) — a **dev** dependency whose fix is a vitest major bump
  deferred to `specs/003-ts-stack-migration`.

So CVE audits live where a stack can judge them, at `mvp` and `production`:

| Where | What | Tiers |
|---|---|---|
| `quality-node.yml` | `pnpm audit --prod --audit-level high` | mvp, production |
| `quality-jvm.yml` | `osv-scanner scan source -r .` | mvp, production |

**A `spike` therefore has no CVE gate in CI.** `/wellforge:spike` checks critical advisories
locally, and local is not a gate. That is the honest shape of the floor: state the hole, do
not paper it over with a line in a table.

A second consequence, worth knowing when reading old runs: the floor resolved its config
from the **caller's** checkout, a path (`gates/configs/gitleaks.toml`) that exists in this
repo and in no generated project — and fell back to defaults silently. Every downstream scan
before `gates-v12` ran without the `op://` allowlist.

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
