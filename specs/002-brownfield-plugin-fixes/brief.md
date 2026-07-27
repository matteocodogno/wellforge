---
id: 002
slug: brownfield-plugin-fixes
rigor: spike
status: done
created: 2026-07-27
---

# Fix two brownfield-hostile defects in the WellForge plugin

## Question
Do the plugin's per-edit lint hook and its security floor behave acceptably in a **brownfield**
repo (root `package.json`, no prettier/eslint config, 1Password `op://` refs)? Field report says no.

## Build
- `hooks/scripts/post-lint.sh`: gate prettier/eslint on an ACTUAL config (not just a
  `package.json`), and make the hook **advisory — never `exit 2`** (a missing/erroring formatter
  is an environment fact, not a code error). Applies to the kt/ktlint branch too.
- `gates/configs/gitleaks.toml` (new): `[extend] useDefault=true` + a global allowlist for
  `op://vault/item[/field]` references (runtime pointers, not secrets — the recommended pattern).
- Wire it: `security-floor.yml` passes `--config` when the file exists (graceful); note in `gates/README.md`.

## Out of scope
- Propagating the gitleaks config into scaffolded/adopted templates (promote-time concern; `# SPIKE:` left).
- The user's untracked local `.git/hooks/pre-commit` (repo-local; not ours to ship). CI floor + config are the shipped surface.
- Making post-lint tier-aware or surfacing advisory lint back to the model via hook JSON.

## Findings
Answered: **yes, both were brownfield-hostile; both fixed.**
- `post-lint.sh` rewritten — config-gated (prettier/eslint run only with a real config, not just
  a `package.json`) and fully **advisory (no `exit 2`)**. Verified: brownfield `.ts` (root
  `package.json`, no config) now exits **0** (was `exit 2` → blocked every edit); with a
  `.prettierrc` present it still formats best-effort. kt/ktlint branch made advisory too.
- `gates/configs/gitleaks.toml` (new): default rules + global allowlist for `op://` references;
  `security-floor.yml` passes `--config` when present (graceful for repos without it). Verified:
  config loads, `op://vault/item/field` scans clean. Documented in `gates/README.md`.
- Advisory gates: `bash -n` OK, `security-floor.yml` valid YAML. Security floor: clean.
- **Side finding (out of scope, follow-up):** `pre-bash-guard.sh` also hard-blocks legit temp
  files merely *named* `secrets.env`/`*.key` (hit it during testing) — same brownfield-hostile
  class; worth a similar advisory/scoped pass.
