# Quality gates

Centralized, measurable quality thresholds. Templates and projects **reference** these
(reusable workflow call / published config package), never copy them — a threshold bump
here propagates without re-scaffolding.

| Path | What | Status |
|---|---|---|
| `workflows/quality-node.yml` | ESLint, `tsc --noEmit`, Vitest coverage ≥80% lines / ≥70% branches, osv-scanner (high+), semgrep | planned (Phase 5) |
| `workflows/quality-jvm.yml` | ktlint, detekt, JaCoCo coverage ≥80%, dep audit, semgrep | planned (Phase 5) |
| `configs/` | eslint-config-welld, detekt/ktlint rulesets, semgrep ruleset | planned (Phase 5) |

## Rules

- CI is the enforcement point; plugin hooks run the **same configs** locally for fast
  feedback (no local/CI drift).
- Threshold changes happen only via PR to this directory — review is the single
  discretion point.
- Workflows are consumed pinned to a semver tag (`gates/vX.Y.Z`), bumped per project
  via one-line PR.
