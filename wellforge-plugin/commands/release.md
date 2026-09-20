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

## Step 0 — Which repo is this?

Two different releases share this command, and running the wrong one is how a plugin
release ends up tagged `v0.10.0` and offered to every project as a template upgrade.

```bash
test -f copier.yml && test -d wellforge-plugin && echo WELLFORGE || echo PROJECT
```

- **PROJECT** (the normal case — a scaffolded or adopted project): continue below.
- **WELLFORGE** (the wellforge repo itself): stop and use **§ Releasing WellForge itself**
  at the end of this file. release-it plays no part there: WellForge has three tag series,
  one file tree, and rules about which may share a commit.

## Pre-flight (all must hold)

1. **Release wiring exists.** `.release-it.json` and a `release` task are present (every
   WellForge scaffold ≥ v0.5.0 ships them; adopted projects get them from the Release layer of
   `/wellforge:adopt`). If missing: `/wellforge:upgrade` (scaffolded) or re-run
   `/wellforge:adopt` and pick Release management (adopted). Don't improvise a release without it.
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
  (those are the wellforge repo's `vX.Y.Z`/`gates-v*`/`plugin-v*` tags — a different
  lifecycle, in the section below).

---

# Releasing WellForge itself

Only in the wellforge repo (Step 0 said WELLFORGE). Read `docs/VERSIONING.md` at the repo
root first — it is the authority; this is the procedure. (Not a link on purpose: a command
file is installed outside the repo, so a relative path to it resolves nowhere the command
actually runs.)

Three series version independently and **no commit may carry two tags** (`git describe`
would report the wrong one and mislabel a scaffold's template version):

| Series | Tag | Cut when |
|---|---|---|
| template | `vX.Y.Z` | `copier.yml` or `templates/` changed |
| gates | `gates-vN` | `.github/workflows/quality-*.yml` or `gates/` changed |
| **plugin** | `plugin-vX.Y.Z` | anything under `wellforge-plugin/` changed |

## Plugin release

1. **Decide the increment** from what changed: patch = fix/wording, minor = a new command,
   agent, skill, hook or config, major = breaks a project set up by an older plugin.
2. **Bump the version in all three files, one commit.** They must agree or
   `check-docs.py` fails CI — and the failure it prevents is silent, a teammate installing a
   plugin that is not the one this repo describes:
   - `wellforge-plugin/.claude-plugin/plugin.json` → `version`
   - `.claude-plugin/marketplace.json` → `version` **and** `source.ref` (`plugin-vX.Y.Z`)
   - `CLAUDE.md` → the quoted plugin version
3. **Add the `docs/PLUGIN-MIGRATIONS.md` entry** for the minor — including "no project-side
   action", which is information. `/wellforge:upgrade` reads that file; a missing entry is
   indistinguishable from an unexamined one.
4. **Verify before tagging** — all of it, not a sample:

   ```bash
   cd wellforge-plugin && uv run --with pyyaml python scripts/check-docs.py \
     && uv run --with pyyaml python scripts/check-routing.py --tool claude \
     && uv run --with pyyaml python scripts/check-budget.py
   ```

5. **Commit, then tag that commit** — in this order, because the manifest must point at its
   own tag:

   ```bash
   git commit -m "feat(plugin): <what changed>"     # or fix(plugin): for a patch
   git tag plugin-vX.Y.Z
   git push origin main --tags
   ```

6. **Confirm no second tag landed on it**, the one rule that is easy to break and quiet
   when broken:

   ```bash
   git tag --points-at HEAD        # must print exactly one tag
   ```

7. **Report the install commands** a teammate runs, with the real version substituted —
   that is what the release is *for*:

   ```bash
   claude plugin marketplace add matteocodogno/wellforge
   claude plugin install wellforge@wellforge --scope user
   # already installed:
   claude plugin marketplace update wellforge && claude plugin update wellforge@wellforge
   ```

## Hard rules for a WellForge release

- **One series per commit, one tag per commit.** A change spanning layers is split into one
  commit per layer, tagged one apart. Check with `git tag --points-at`.
- **Never tag the plugin series as bare semver** (`2.42.0`). Copier reads PEP440-parseable
  tags as template versions and would offer the plugin as a template upgrade. The
  `plugin-v` prefix is what makes it invisible, exactly as `gates-v` is.
- **Never move a published tag.** A `ref` in the marketplace manifest is a promise that the
  tag's contents are fixed; re-pointing it changes what an already-installed teammate gets
  on their next update, with nothing in either repo recording that it happened. Cut a new
  patch instead.
- The tag is not enough on its own: an unbumped `plugin.json` is cached by version at
  runtime and reaches nobody, including you.
