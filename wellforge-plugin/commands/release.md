---
description: Cut a release — auto version bump + CHANGELOG from Conventional Commits, git tag, GitHub release (release-it)
argument-hint: [patch|minor|major] (optional — default: auto-computed from commits) [--dry-run]
---

Cut a release for this project. The mechanics are **release-it** with the
`@release-it/conventional-changelog` plugin (computes the semver bump AND the CHANGELOG from
the Conventional Commits the gate already enforces) and `@release-it/bumper` (writes the new
version into the per-service version files). Your job is the discipline around it: preview,
confirm, one clean reviewable release. Don't hand-roll versioning — release-it owns it.

Arguments: $ARGUMENTS  (an optional increment `patch|minor|major` to override the
auto-computed bump; `--dry-run` to preview only)

## Pre-flight (all must hold)

1. **Release wiring exists.** `.release-it.json` and a `release` mise task are present (every
   WellForge scaffold ≥ v0.5.0 ships them). If missing, this project predates release wiring —
   offer `/wellforge:upgrade` (scaffolded) or to add the config by hand (adopted); don't
   improvise a release without it.
2. **Clean working tree** — release-it refuses a dirty tree (the release must be one
   reviewable commit). Require commit/stash first.
3. **On `main`, with an `origin` remote** — release-it derives the repo and pushes the tag
   there. No remote → do the local version+tag only and report the GitHub release as PENDING.
4. **GitHub release needs auth** — `GITHUB_TOKEN` in the environment (or `gh auth`). If
   absent, note that the version+tag will be created but the GitHub Release step will be
   skipped; the user can publish it later.
5. History since the last `vX.Y.Z` tag is Conventional Commits (the commit-lint gate ensures
   this) — that history IS the changelog and the version source.

## Step 1 — Preview (always, before anything mutates)

Run the release in dry-run and relay the result:

```bash
mise run release -- --ci --dry-run [patch|minor|major]
```

Show the user: the **computed next version** (`x.y.z → x.y.z`), and the **CHANGELOG section**
release-it would write (grouped Features / Bug Fixes / Breaking Changes). State which files
the bump touches (per `.release-it.json`: the per-service `package.json`s via bumper; for the
JVM preset, `backend/pom.xml` via the Maven hook).

## Step 2 — Confirm (the gate)

A release is outward-facing — it tags and publishes. **Ask the user to approve / change the
increment / abort.** Never run the real release without an explicit go. If they want a
different bump than auto-computed, pass `patch|minor|major`.

## Step 3 — Release

```bash
mise run release -- --ci [patch|minor|major]
```

release-it then: bumps the version files, writes `CHANGELOG.md`, commits
`chore(release): v<version>`, tags `v<version>`, pushes, and creates the GitHub Release with
the generated notes.

## Step 4 — Report

- Version delta and the new tag.
- The CHANGELOG section that was added.
- The GitHub Release URL (or PENDING if auth/remote was missing — say exactly what's left).
- Note the version is now recorded in the per-service files + CHANGELOG.md.

## Hard rules

- Never release a dirty tree, and never hand-edit `CHANGELOG.md` or the version mid-release —
  release-it derives both from the commits; editing them defeats the audit trail.
- Always dry-run + confirm before the real run (outward-facing, hard to undo a published tag).
- The increment is auto-computed from Conventional Commits; override only deliberately
  (e.g. forcing a `major` for a documented breaking change the commits under-state).
- This releases the project's own version. It is NOT the WellForge template/plugin release
  (those are the wellforge repo's `vX.Y.Z`/`gates-v*`/plugin tags — a different lifecycle).
