# Quality gates

Centralized, measurable quality thresholds. Projects **reference** these (reusable
workflow calls pinned to a `gates-v*` tag), never copy them — a threshold bump here
propagates on the next ref bump, no re-scaffold needed.

> The reusable workflows themselves live in `/.github/workflows/` (GitHub only resolves
> `workflow_call` targets from that path). This directory holds their configs, scripts,
> and policy documentation.

## What's enforced

| Check | Node (`quality-node.yml`) | JVM (`quality-jvm.yml`) |
|---|---|---|
| Lint | `pnpm run lint` (zero warnings) | ktlint via `com.github.gantsign.maven:ktlint-maven-plugin:3.2.0:check` |
| Types | `pnpm run typecheck` | Kotlin compiler (via tests) |
| Coverage | Vitest: lines ≥ **80%**, branches ≥ **70%** (CLI-enforced) | JaCoCo: lines ≥ **80%** enforced, branches reported (`scripts/check-jacoco.py`) |
| Dependency audit | `pnpm audit --prod --audit-level high` | `osv-scanner v2.0.0` (fails on any known vuln) |
| SAST | semgrep 1.172.0: `configs/semgrep/wellforge.yml` + `p/typescript` | semgrep 1.172.0: `configs/semgrep/wellforge.yml` + `p/kotlin` |
| Reproducibility | `pnpm-lock.yaml` required, `--frozen-lockfile` | mise-pinned toolchain |

Coverage enforcement skips modules under **50 total lines** (fresh scaffolds must not
fail their own gate); the skip is printed as a CI notice, never silent.

## Layout

| Path | What |
|---|---|
| `/.github/workflows/quality-node.yml` | reusable Node/TS gate (`workflow_call`, input: `working-directory`) |
| `/.github/workflows/quality-jvm.yml` | reusable JVM gate (same interface) |
| `configs/semgrep/wellforge.yml` | org-specific SAST rules (secrets, println, debugger) |
| `configs/gitleaks.toml` | security-floor gitleaks config: default rules + allowlist for 1Password `op://` references (pointers, not secrets). `security-floor.yml` passes it when present; point a local pre-commit gitleaks hook at it too |
| `scripts/check-jacoco.py` | JaCoCo threshold enforcement (tested: pass/fail/floor) |
| `scripts/check-commit-msg.py` | Conventional Commits validator — shared by the local hook and both CI gates |
| `hooks/commit-msg`, `hooks/pre-merge-commit` | local fast-feedback hooks; installed by `/scripts/setup-git-policy.sh` |
| `/.github/workflows/commit-lint.yml` | reusable Conventional Commits gate (`workflow_call`) |
| `/.github/workflows/linear-history.yml` | reusable linear-history gate (`workflow_call`) — no merge commits in the PR range |
| `/.github/workflows/heartbeat-report.yml` | reusable heartbeat reporter (`workflow_call`) — dedup-issue manager (see below) |

## Eval gate (LM-judge — opt-in)

The deterministic gates above (tests, coverage, lint, SAST) can't verify the
non-deterministic half: spec fidelity, test *quality* (not just pass/fail), idiomatic
code, trajectory. The **eval gate** scores a feature against a central rubric using an
LM-judge — "set the bar at the eval, not the demo."

| Path | What |
|---|---|
| `configs/eval-rubric.yml` | the central rubric (dimensions, weights, floors, pass score) — single source of truth |
| `scripts/run-eval.py` | headless LM-judge: scores via the Anthropic API, fails on verdict FAIL (tested: pass / fail-by-total / fail-by-floor) |
| `/.github/workflows/quality-eval.yml` | reusable opt-in workflow (`@gates-v2`) — needs an `ANTHROPIC_API_KEY` secret |

- **Opt-in** because it costs API tokens (the paper's "high CapEx, low OpEx" economics):
  wire it on agent-facing or high-stakes changes, not every PR.
- Pass = weighted total ≥ `pass_score` (80) AND every dimension ≥ its floor — a single
  sub-floor dimension fails, so an unmet AC can't be rescued by a high total.
- Same governance as thresholds: the rubric changes only via PR to `gates/`. Per-feature
  `eval.md` overrides may add dimensions or raise floors, never lower them.
- In-session, `/wellforge:eval` + the `evaluator` agent use the same rubric, writing
  `specs/NNN-slug/eval-report.md`. CI and in-session share `configs/eval-rubric.yml`.

## Conventional Commits gate

Commit messages must follow [Conventional Commits](https://www.conventionalcommits.org)
(`type(scope)!: description`). Two layers, same validator (`scripts/check-commit-msg.py`):

| Layer | What |
|---|---|
| Local `commit-msg` hook | `gates/hooks/commit-msg` — fast feedback. Install: `./scripts/setup-git-policy.sh` (or by hand: `ln -sf ../../gates/hooks/commit-msg .git/hooks/commit-msg`; co-exists with a pre-commit gitleaks hook). Skippable with `--no-verify`. |
| CI gate (`/.github/workflows/commit-lint.yml`) | the enforcement point — lints every commit in a PR, can't be skipped. Consume `@gates-v4`. |

Types: `feat fix docs style refactor perf test build ci chore revert`. Merge/revert/
fixup/squash commits are exempt. The WellForge dev agents already commit in this format;
this gate enforces it for everyone (humans included — it would have caught a stray `harden:`).

## Linear history gate

**Every WellForge repository keeps a strictly linear history — no merge commits.** Branches
are rebased onto `main` and integrated **fast-forward**; a PR merges as squash or rebase,
never "create a merge commit". Rationale: `git log --oneline` *is* the changelog (release-it
derives it from Conventional Commits), `git bisect` stays meaningful, and a revert is one
commit rather than a merge-parent puzzle.

| Layer | What |
|---|---|
| Local config | `merge.ff = only`, `pull.rebase = true`, `rebase.autoStash = true` — `git merge`/`git pull` can then only fast-forward. Per-clone, so it ships as a script, not a file: **`scripts/setup-git-policy.sh`** (run once per clone; also installs the hooks below) |
| Local `pre-merge-commit` hook | `gates/hooks/pre-merge-commit` — git runs it only when a merge *would* create a merge commit; it refuses. Skippable with `--no-verify` |
| CI gate (`/.github/workflows/linear-history.yml`) | the enforcement point — fails on any merge commit in the PR range (this also catches a backmerge of `main` into the branch). Consume `@gates-v8` |
| Branch protection | `required_linear_history: true` + `allow_merge_commit: false` on the repo — set by the `connections` skill (`references/github.md`), verified via the API |

The four layers cover different bypasses: config is the ergonomic default, the hook catches a
`git merge` in a clone that never ran the setup script, CI catches `--no-verify`, and branch
protection catches the GitHub merge button. Parallel worktree integration in
`/wellforge:implement` follows the same rule (rebase each branch, then `merge --ff-only`).

## Scheduled heartbeat (opt-in, Phase 14a)

PR-time gates only run when someone pushes. But two findings change *without* a commit:
CVEs **newly disclosed** against already-merged dependencies (the advisory DB moves on its
own), and updated **SAST** rules. The heartbeat catches those on a cadence.

A scaffold generated with `heartbeat: true` (default; `ci == github`, `rigor != spike`) ships
`.github/workflows/heartbeat.yml`: a `schedule`d (default weekly, `heartbeat_cron`) +
`workflow_dispatch` caller that **re-uses the same `quality-<stack>.yml` gates** — no gate
logic is duplicated — then calls `heartbeat-report.yml`.

| Path | What |
|---|---|
| `/.github/workflows/heartbeat-report.yml` | given a pass/fail (and an optional `body` + `issue-label`), manages **one deduplicated tracking issue**: opens on first failure, **updates it in place** each failing run (never a new issue per cycle), closes it with a comment when it clears. Generic — reused by both the gate and template-drift heartbeats. Needs `issues: write` (the caller declares it) |
| `/.github/workflows/template-drift.yml` | the **template-drift heartbeat** (Phase 14b, Pillar 6): reads `.forge/manifest.json`, resolves the latest `vX.Y.Z` release of the template source, and if the project is behind files a separate deduplicated "N releases behind → `/wellforge:upgrade`" issue (label `template-drift`) via `heartbeat-report.yml`; closes it when the project catches up |

- **Surface, never auto-ship** (loop-engineering principle): a heartbeat only files/updates an
  issue — it never merges, deploys, upgrades, or self-approves. A human triages.
- **Dedup is the point.** A weekly job that opened a fresh issue each run would train people to
  ignore it; one-issue-updated-in-place (per concern label) keeps signal high.
- **Off for `spike`** — a spike has no enforced gates or lifecycle guarantees to watch (rigor-tiers skill).
- Ships in the gate series (`heartbeat-report.yml` v1 landed at `gates-v6`; the `body` input +
  `template-drift.yml` land at **`gates-v7`**); consumers pin `@gates-v*` like every other gate.
- The **agentic** heartbeats (fleet, spec-health) live outside CI — see the `heartbeat` skill,
  `scripts/fleet-triage.sh`, and `/wellforge:triage`.

## Brownfield ratchet (adopted projects)

Legacy codebases can't start at 80% — and a permanently red gate teaches people to
ignore gates. Both workflows accept an optional `coverage-lines-baseline` (node also
`coverage-branches-baseline`): a **measured** per-project minimum set by
`/wellforge:adopt` at adoption time.

- `0` (default) = central thresholds apply — scaffolded projects never set these.
- Non-zero = that project's enforced minimum, with a CI notice showing the gap to the
  central target on every run.
- **Raise-only**: lowering a baseline must be rejected in PR review — it lives in the
  project's `quality.yml`, so the change is always visible. When the baseline reaches
  the central target, drop the input.

## Rules

- CI is the enforcement point; plugin hooks (`post-lint.sh`, `stop-verify.sh`) run the
  same project tasks locally for fast feedback; the QE agent runs the full gate set.
- Threshold changes happen only via PR to this directory — review is the single
  discretion point.
- Consumers pin `@gates-v*` tags; bumping is a one-line PR per project.

## Known deviations / future work

- **ESLint/ktlint/Prettier configs are template-shipped**, not centrally referenced —
  central refs need a package registry (npm + maven). They still propagate via template
  upgrades (Phase 6). Revisit when a registry exists.
- **detekt** not yet wired (not in the template pom) — candidate for template v0.2 +
  gate addition.
- **Audit asymmetry**: node uses pnpm audit (native high+ threshold), JVM uses
  osv-scanner (no severity filter → any vuln fails). Unify on osv-scanner with a
  severity policy when stabilized.
- Branch coverage on JVM is report-only until the pilot calibrates a realistic floor.
