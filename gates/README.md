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
| SAST | semgrep 1.96.0: `configs/semgrep/welld.yml` + `p/typescript` | semgrep 1.96.0: `configs/semgrep/welld.yml` + `p/kotlin` |
| Reproducibility | `pnpm-lock.yaml` required, `--frozen-lockfile` | mise-pinned toolchain |

Coverage enforcement skips modules under **50 total lines** (fresh scaffolds must not
fail their own gate); the skip is printed as a CI notice, never silent.

## Layout

| Path | What |
|---|---|
| `/.github/workflows/quality-node.yml` | reusable Node/TS gate (`workflow_call`, input: `working-directory`) |
| `/.github/workflows/quality-jvm.yml` | reusable JVM gate (same interface) |
| `configs/semgrep/welld.yml` | org-specific SAST rules (secrets, println, debugger) |
| `scripts/check-jacoco.py` | JaCoCo threshold enforcement (tested: pass/fail/floor) |

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
