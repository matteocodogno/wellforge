---
description: Upgrade a scaffolded project to a newer template version (copier update + AI conflict resolution)
argument-hint: [target version, e.g. v0.2.0 — defaults to latest]
---

Upgrade this project to a newer WellForge template version. The mechanical re-templating
is copier's job; your job is the judgment: explaining the diff, resolving conflicts
without losing local work, and proving the result with the quality gates.

Target version: $ARGUMENTS

## Pre-flight (all must pass before touching anything)

1. Read `.forge/manifest.json` and `.copier-answers.yml` — they identify the template
   (preset), current version, and recorded answers. Missing/hand-edited files: STOP,
   this project isn't upgradeable (report why; offer to reconstruct the answers file
   only with explicit user agreement).
2. `git status` must be clean — require commit/stash first, no exceptions (the upgrade
   must be one reviewable, revertable commit).
3. Resolve source + target: the template source is the wellforge repo (`_src_path` in
   the answers file; if it's a stale local path, ask for the current checkout/URL).
   Target = `$ARGUMENTS` or the latest `vX.Y.Z` tag. Already there → report and stop.
4. Show the plan of record before running: current → target version, and the template
   changelog between them (`git log <cur>..<target> -- templates/<preset>/ copier.yml`
   in the wellforge repo, when available). Ask the user to confirm.

## Run the update

```bash
uvx copier update --trust --skip-answered \
  --conflict inline \
  --data generated=$(date +%F) \
  [--vcs-ref <target>]
```

- Never change recorded answers during an upgrade (that's re-configuration, a separate
  concern — `--skip-answered` enforces it).
- Copier applies per-version `_migrations` automatically — list any that ran.

## Resolve conflicts (the AI-value step)

For every file with inline conflict markers:
1. Understand BOTH sides: what the template changed (and why — changelog) vs what the
   project customized (and why — `git log -- <file>`).
2. Default stance: **keep the project's behavior, adopt the template's structure**.
   The upgrade must never silently revert local business logic; template boilerplate
   wins only where the project never deliberately diverged.
3. Genuinely ambiguous (template and project changed the same behavior differently):
   don't guess — present both sides to the user with a recommendation.
4. Zero conflict markers may remain; verify with a grep for `<<<<<<<` before moving on.

## Verify

1. `mise run install && mise run build && mise run test` — all green.
2. Lint + typecheck (`mise run lint`, `pnpm run typecheck` where applicable).
3. Failures caused by the upgrade: fix mechanically if obvious; otherwise report
   precisely what the new template version expects and pause for the user.

## Close

1. Confirm `.forge/manifest.json` + `.copier-answers.yml` reflect the new version
   (copier rewrites them — verify, never hand-edit).
2. Single commit: `chore: upgrade template <preset> <old> → <new>` — body lists
   migrations run, conflicts resolved (file + one-line rationale each), and verification
   results.
3. Report: version delta, files changed, conflicts and how each was settled, gate
   results. If the project's CI pins `gates_ref`, note whether a gates bump is also
   available (separate one-line PR — never bundle it into the template upgrade).

## Hard rules

- Dirty tree → no upgrade. No partial upgrades — fully done or fully reverted
  (`git reset --hard` is the rollback; say so in the report if used).
- Never resolve a conflict by deleting a test.
- One version jump at a time when migrations exist between versions; direct jump only
  when the changelog shows no `_migrations` in between.
