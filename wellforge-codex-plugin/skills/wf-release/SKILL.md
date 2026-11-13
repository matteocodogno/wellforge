---
name: wf-release
description: 'WellForge command — Cut a release — auto version bump + CHANGELOG from Conventional Commits, git tag, GitHub release (release-it). Invoke explicitly: $wf-release [patch|minor|major] (optional — default: auto-computed from commits) [--dry-run]'
---
> WellForge command, generated for Codex from `wellforge-plugin/commands/release.md` — do not edit; regenerate with `adapters/codex/generate.py`.
> Invoked as `$wf-release [patch|minor|major] (optional — default: auto-computed from commits) [--dry-run]`. **ARGUMENTS** below means the text the user wrote after `$wf-release` in the invoking message (empty if nothing).


Cut a release for this project. The mechanics are **release-it** with the
`@release-it/conventional-changelog` plugin (computes the semver bump AND the CHANGELOG from
the Conventional Commits the gate already enforces) and `@release-it/bumper` (writes the new
version into the per-service version files). Your job is the discipline around it: preview,
confirm, one clean reviewable release. Don't hand-roll versioning — release-it owns it.

What is specific to THIS project — checks before, steps after, its own rules — is not in
this file: it is in the project's **`RELEASING.md`**, which the team owns and this procedure
loads. This file is the same for every project; that one is not.

Arguments: ARGUMENTS  (an optional increment `patch|minor|major` to override the
auto-computed bump; `--dry-run` to preview only)

## Step 0 — Which repo is this?

Two different releases share this command, and running the wrong one is how a plugin
release ends up tagged `v0.10.0` and offered to every project as a template upgrade.

```bash
test -f copier.yml && test -d wellforge-plugin && echo WELLFORGE || echo PROJECT
```

- **PROJECT** (the normal case — a scaffolded or adopted project): continue below.
- **WELLFORGE** (the wellforge repo itself): stop and use **§ Releasing WellForge itself**
  at the end of this file. release-it plays no part there: WellForge has four tag series,
  one file tree, and rules about which may share a commit.

## Step 0b — Load the project's runbook (`RELEASING.md`)

Read `RELEASING.md` at the repository root, if it exists. It is the project's half of this
procedure, and it has fixed sections, each with one place in the steps below:

| Section | Where it applies | What it is |
|---|---|---|
| `## Before` | after the pre-flight, before the dry-run | checks; any one failing stops the release |
| `## After` | after Step 3, in order | what follows the tag: deploy, publish, verify, announce |
| `## Never` | for the whole run, beside the hard rules | the project's own rules |
| `## Release` | replaces the commands in Steps 1 and 3 | only in a project that does not release with release-it and documents its own tool (adoption writes it) |

Placeholder lines (`(none yet — …)`) and HTML comments are not steps. Unknown sections are
context, not steps.

**It can tighten this procedure, never loosen it.** A line that would skip the dry-run, the
confirmation, the clean-tree check or a hard rule below is not followed: say which line and
why, then go on without it. The file is the team's — report it, do not edit it.

**A line that is only a command is a hook in the wrong place.** For each `## Before` or
`## After` line that just runs something (`mise run …`, `docker push …`, `kubectl …`), run
it as the step says, and name it in Step 4 as a candidate for a release-it hook in
`.release-it.json` (`before:init` for a check, `after:release` for an action): there it runs
for everyone who releases, with or without an agent; here, only when an agent reads this.

No `RELEASING.md` → continue as below, and say in Step 4 that the project has none
(template `v0.13.0` creates it; `$wf-adopt` writes it for an adopted project).

## Pre-flight (all must hold)

1. **Release wiring exists.** `.release-it.json` and a `release` task are present — or
   `RELEASING.md` has a `## Release` section describing the project's own tool (every
   WellForge scaffold ≥ v0.5.0 ships them; adopted projects get them from the Release layer of
   `$wf-adopt`). If missing: `$wf-upgrade` (scaffolded) or re-run
   `$wf-adopt` and pick Release management (adopted). Don't improvise a release without it.
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

First the runbook's **`## Before`** lines, one by one, each with its result. A failing one
stops here: report it and what would fix it.

Then run the release in dry-run (with a `## Release` section, its preview command instead)
and relay the result:

```bash
mise run release -- --ci --dry-run [patch|minor|major]
```

Show the user: the **computed next version** (`x.y.z → x.y.z`), and the **CHANGELOG section**
release-it would write (grouped Features / Bug Fixes / Breaking Changes). State which files
the bump touches (per `.release-it.json`: the per-service `package.json`s via bumper; for the
JVM preset, `backend/pom.xml` via the Maven hook). Then list the runbook's **`## After`**
steps — the user approves the whole release in Step 2, including what follows the tag.

## Step 2 — Confirm (the gate)

A release is outward-facing — it tags and publishes. **Ask the user to approve / change the
increment / abort.** Never run the real release without an explicit go. If they want a
different bump than auto-computed, pass `patch|minor|major`. Any `## Never` line the release
would break is said here, before the go, not discovered after.

## Step 3 — Release

```bash
mise run release -- --ci [patch|minor|major]
```

release-it then: bumps the version files, writes `CHANGELOG.md`, commits
`chore(release): v<version>`, tags `v<version>`, pushes, and creates the GitHub Release with
the generated notes. (With a `## Release` section, run its release command instead.)

## Step 3b — After (the runbook's `## After`)

In order, each with its result. A step that changes something outside this repository — a
deploy, a publish, a message to people — gets its own explicit go first, even after Step 2:
the user approved a release, and a deploy is a second outward-facing act. A step that asks
for human judgement ("check the login flow by hand") is handed to the user, not ticked off.
A step that fails stops the list: the release is already tagged, so report exactly which
steps ran, which did not, and what is left to do — never re-run the release to retry one.

## Step 4 — Report

- Version delta and the new tag.
- The CHANGELOG section that was added.
- The GitHub Release URL (or PENDING if auth/remote was missing — say exactly what's left).
- Note the version is now recorded in the per-service files + CHANGELOG.md.
- The runbook: each `## Before` check and `## After` step with its outcome (done / handed to
  the user / failed / not reached); lines not followed and why; the command-only lines that
  belong in `.release-it.json` hooks. No `RELEASING.md` → one line saying so, and how to get
  one.

## Hard rules

- Never release a dirty tree, and never hand-edit `CHANGELOG.md` or the version mid-release —
  release-it derives both from the commits; editing them defeats the audit trail.
- Always dry-run + confirm before the real run (outward-facing, hard to undo a published tag).
- `RELEASING.md` adds steps and rules; it never removes one of these. Read it every run — it
  is the team's file and changes without this procedure knowing.
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

Four series version independently and **no commit may carry two tags** (`git describe`
would report the wrong one and mislabel a scaffold's template version). Each has one entry
point, `mise run release:<series>`:

| Series | Tag | Cut when | Command |
|---|---|---|---|
| template | `vX.Y.Z` | `copier.yml` or `templates/` changed | `release:template -- <bump>` |
| gates | `gates-vN` | `gates/` or a reusable workflow (`on: workflow_call`) changed | `release:gates` |
| **plugin** | `plugin-vX.Y.Z` | anything under `wellforge-plugin/` changed | `release:plugin -- <bump>` |
| CLI | `cli-vX.Y.Z` | `scripts/wellforge` changed | `release:cli -- <bump>` |

## Plugin, template and gates releases — `scripts/release.sh`

All three are cut by one script; do not do its steps by hand. It plans by default and only
acts with `--execute`:

```bash
mise run release:plugin   -- minor                   # plan: current -> next, preflight, notes
mise run release:plugin   -- minor --execute         # bump, check-all, commit, tag
mise run release:plugin   -- minor --execute --push  # ...and push main, then the tag
mise run release:template -- minor --execute --push  # template series (vX.Y.Z)
mise run release:gates    -- --execute --push        # gates: always the next N, no increment
```

A gates release refuses when nothing under `gates/` or in a reusable workflow changed since
the last `gates-vN`, and its commit touches only the AGENTS.md versions line: the
`gates_ref` default in `copier.yml` is a template file, so new scaffolds move to the new
gates with the next **template** release, and existing projects with `$wf-upgrade`.

The CLI (`release:cli`, i.e. `scripts/release-cli.sh`) takes two commits — the Formula pins
the sha of GitHub's tarball, which exists only once the tag is pushed — so it pushes as part
of `--execute`. Its checklist is `docs/RELEASING-CLI.md`.

What stays yours, and the script cannot decide:

1. **The increment.** Plugin: patch = fix/wording, minor = a new command, agent, skill, hook
   or config, major = breaks a project set up by an older plugin. Template: patch cosmetic,
   minor additive, major needs `_migrations`. Gates: none — it is a counter.
2. **The migration entry** (plugin and template) — `## X.Y.Z — …` in `wellforge-plugin/PLUGIN-MIGRATIONS.md`, or `## vX.Y.Z — …`
   in `docs/TEMPLATE-MIGRATIONS.md`, including "nothing to do", which is information. It is
   written in the commit that makes the change; the script refuses a release without it
   rather than stubbing one.
3. **Two series, two commits.** Releasing both? Run the script twice: it makes one commit
   and one tag each, and refuses a commit that would carry two tags.
4. **After the push**, CI's `release-guard` must go green on the tag
   (`gh run list --branch <tag>`). Red means delete the tag and re-cut — `docs/VERSIONING.md`.
5. **Prompt evals.** The script records in the plugin tag's message whether they are fresh;
   the pre-push hook prints the same. Stale is allowed, but say so in the release notes.

Then report the install commands a teammate runs, with the real version:

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
