---
description: Upgrade a scaffolded project to a newer template version (copier update + AI conflict resolution)
argument-hint: [target version, e.g. v0.2.0 — defaults to latest] [--dry-run]
---

Upgrade this project to a newer WellForge template version. The mechanical re-templating
is copier's job; your job is the judgment: explaining the diff, resolving conflicts
without losing local work, and proving the result with the quality gates.

Target version: $ARGUMENTS

## `--dry-run` — show the plan, change nothing

With `--dry-run` anywhere in the arguments, run every **read** step below and none of the
writes: produce the plan of record and stop. `/wellforge:release` has had this since it
shipped, for the obvious reason — re-templating touches files a human edited since, and seeing the diff first is the difference between an upgrade and a surprise.

Print, in this order:

1. **What would change** — every file written, created or deleted, one line of reason each.
   Run `copier update --pretend` and relay its output verbatim — it is the authority on the file set, not your reading of the template.
2. **What would run** — the exact commands, copy-pasteable, in order.
3. **What would be irreversible** — anything outward-facing or hard to undo, called out
   separately. If nothing is, say so.
4. **What it cannot predict** — the honest half. `--pretend` does not resolve conflicts, so a clean pretend can still produce merge markers for real. Declared `_migrations` for the crossed versions are listed, not executed.

End with the exact command to run for real (this invocation minus `--dry-run`).

**Hard rule:** a dry run writes **nothing** — not a spec, not a status flip, not a scratch
file, not a git config. If a step cannot be planned without performing it, say so in
section 4 rather than performing it.

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
4. **Read the recorded plugin version too** — `plugin.version` in `.forge/manifest.json`
   (older projects have no `plugin` object at all; treat that as "unknown, pre-2.38" and
   carry on — it is the normal state of every project scaffolded before this field existed,
   not an error). Compare it against the running plugin's
   `.claude-plugin/plugin.json`. **Two upgrades are in play and they are independent:** the
   template (`vX.Y.Z`, what copier re-renders) and the plugin (`2.x`, what changes the
   conventions, spec formats, trace schema and hooks around it). A project can need either,
   both, or neither.
5. Show the plan of record before running: current → target **template** version with its
   changelog (`git log <cur>..<target> -- templates/<preset>/ copier.yml` in the wellforge
   repo, when available), **and** recorded → running **plugin** version with every
   applicable entry from `docs/PLUGIN-MIGRATIONS.md` in between. Ask the user to confirm.

## Run the update

```bash
uvx copier update --trust --skip-answered --conflict inline [--vcs-ref <target>]
```

- Never change recorded answers during an upgrade (that's re-configuration, a separate
  concern — `--skip-answered` enforces it). **One exception: `gates_ref`** — see the next
  section; it is template-owned infrastructure, and freezing it silently ages a project's
  security tooling.
- Copier applies per-version `_migrations` automatically — list any that ran.

## Bump the gate pin (the one deliberate exception to `--skip-answered`)

`gates_ref` is a recorded answer, so `--skip-answered` freezes it — **a template release does
NOT carry a gate bump**. Verified E2E: updating a project v0.7.0 → v0.8.0 re-renders every
workflow but leaves them pinned `@gates-v7`. The template version and the gate series are
independent, and a project can sit on current templates while its SAST/audit tooling rots.

That makes the pin the one answer worth revisiting on every upgrade — it is security-relevant
infrastructure the template owns, not a user preference like `project_name`:

1. Read `gates_ref` from `.copier-answers.yml`; resolve the latest `gates-v*` tag in the
   wellforge repo (`git ls-remote --tags <src> 'gates-v*'`).
2. Behind? Show the delta and what it contains (the gates changelog), then ask.
3. On yes, re-run with the single answer overridden — this rewrites the recorded answer AND
   re-renders every call site, and works even when the template version is already current:

   ```bash
   uvx copier update --trust --data gates_ref=<latest>
   ```

4. **Raise-only.** Never lower a gate pin to make CI green — that is the same discretion the
   ratchet forbids. If the user declines the bump, say so explicitly in the report.

## Apply the plugin migrations

Independent of the template re-render, and skippable only when the recorded plugin version
already equals the running one.

1. Read **`docs/PLUGIN-MIGRATIONS.md`** and take every entry whose minor is greater than the
   recorded `plugin.version`, in order. An unknown recorded version (pre-2.38 project) means
   read them all — they are written to be idempotent, so re-applying one is safe, and
   skipping one because the version is unknown is not.
2. **Automatic** entries: apply them, and say which. **Human** entries: do not guess — surface
   them with the exact change and let the user decide, in the same message as the rest of the
   plan.
3. An entry that says "no project-side action" still gets reported. Silence is ambiguous
   between "nothing to do" and "nobody checked".
4. If `docs/PLUGIN-MIGRATIONS.md` is unreachable (the wellforge repo isn't at hand), say so
   plainly and **do not claim the project is migrated** — record what the gap is so the next
   run can close it.

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

## Stamp the manifest

Before the commit, update `.forge/manifest.json` (or `.forge/adoption.json` for an adopted
project — where `/wellforge:upgrade` does not re-template but the plugin migrations still
apply):

```jsonc
"plugin": { "version": "<the running plugin version>", "set_by": "upgrade", "at": "<today>",
            "marketplace": "<wellforge@wellforge | local>" }
```

Refresh `marketplace` as well as `version`: a project first scaffolded from a local checkout
and later upgraded by a marketplace install has changed provenance, and the field is only
useful if it describes the last plugin that actually touched the project. Resolve it the way
`/wellforge:new` does — the key under `.plugins` in `~/.claude/plugins/installed_plugins.json`
starting `wellforge@`, or `local` when there is none.

Write it even when the template version did not move: the point of the field is to record
which plugin last touched the project, and a plugin-only upgrade is exactly the case that
would otherwise leave a stale value behind. If a migration was surfaced but **not** applied
(a human entry the user deferred), say so in the report and leave the version at the
recorded one — stamping it would claim work that was not done.

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
   results, and the `gates_ref` outcome (bumped old → new, already current, or declined).

## Hard rules

- Dirty tree → no upgrade. No partial upgrades — fully done or fully reverted
  (`git reset --hard` is the rollback; say so in the report if used).
- Never resolve a conflict by deleting a test.
- One version jump at a time when migrations exist between versions; direct jump only
  when the changelog shows no `_migrations` in between.
