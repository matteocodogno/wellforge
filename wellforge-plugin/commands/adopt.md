---
description: Adopt WellForge in an existing (brownfield) project — AI-readiness, spec workflow, calibrated quality gates, release management
argument-hint: (run from the project root; no arguments)
---

Onboard this existing project onto WellForge: AI-readiness files, the spec-driven
workflow, optionally the central quality gates (with a measured baseline) and tool
connections. Adoption **adds** — it never rewrites existing code or conventions.

## Stage 0 — Survey (read-only)

1. Preconditions: a git repo with a reasonably clean tree (uncommitted adoption files
   must be reviewable as one diff). Refuse to run in a project that already has
   `.forge/` (scaffolded or already adopted — point to `/wellforge:upgrade` or report).
2. Detect the stack: build files (package.json/pnpm-lock/pom.xml/build.gradle),
   languages, test runners, lint setup, CI provider, monorepo layout. Read the README
   and any existing AI-context files (CLAUDE.md, AGENTS.md, .cursorrules, …).
3. Report what you found and what adoption will add BEFORE touching anything.

## Stage 1 — Scope interview

AskUserQuestion (batch): which layers to adopt —
- **Workflow + AI-readiness** (always; the core)
- **Quality gates in CI** (needs GitHub Actions + interface prerequisites, see stage 3)
- **Release management** (release-it: version + CHANGELOG from Conventional Commits — stage 5;
  offer only if the project has no release tool already, and pair it with commit-lint)
- **Connections** (GitHub settings, MCP, environments — the `connections` skill)
- **mise toolchain** (offer only if the project doesn't already pin tools another way;
  never fight an existing working setup)

## Stage 2 — AI-readiness + spec workflow

1. `AGENTS.md` (canonical context file, cross-tool standard): generate from the survey —
   actual stack + versions, dev commands (the project's real ones, not WellForge defaults),
   layout, conventions you OBSERVED (naming, error handling, test style), and the
   spec-driven workflow note (`specs/` + `/wellforge:*` commands).
   - **For projects with a frontend, record the UI library & styling system explicitly**
     (e.g. MUI / Chakra / Ant / shadcn / Mantine / Tailwind-only) — the designer and
     frontend-dev read this to map component reuse against the *project's* library, not the
     WellForge greenfield default. Note the component directory and any theme/design-token file.
   - Existing `CLAUDE.md` with content? Migrate its content into AGENTS.md (preserving
     every rule), then replace CLAUDE.md with the one-line `@AGENTS.md` import.
   - Existing `AGENTS.md`? Extend, never overwrite — append missing sections only.
2. `specs/README.md` — pointer to the spec-driven workflow (same as scaffolds get).
3. `.claude/settings.json` — pre-allow the project's routine commands (its actual
   build/test/lint invocations). Merge into an existing file, never clobber.
4. `.forge/adoption.json` — `{ "adopted": "<date>", "plugin": "<version>", "layers": [...] }`.
   Records that this is an ADOPTED project: `/wellforge:upgrade` stays unavailable
   (no template ancestry) and fleet tooling can distinguish adopted from scaffolded.

## Stage 3 — Quality gates (if chosen)

1. **Interface check** — the reusable workflows have prerequisites; verify, don't assume:
   - Node: pnpm with committed `pnpm-lock.yaml`, scripts `lint`, `typecheck`, vitest
     for coverage. npm/yarn projects: STOP this stage and report what a migration
     would involve — wiring a gate that can't pass is worse than no gate.
   - JVM: Maven (`mvnw` or mise-provided), kotlin sources. ktlint/JaCoCo run via full
     plugin coordinates — no pom changes needed. Gradle projects: not supported yet;
     report it as a gates/ feature request.
2. **Measure the baseline** — run the project's coverage ONCE, locally. Record actual
   line (and branch, node) percentages, rounded DOWN to the nearest integer.
3. **Wire** `.github/workflows/quality.yml` calling the reusable workflow(s) pinned to
   the current `gates-v*` tag, passing `coverage-lines-baseline` (and branches for
   node) from the measurement. Include the header comment:
   ```yaml
   # Ratchet rule: baselines may only be RAISED, never lowered (PR review enforces
   # this). Central target: 80/70 — close the gap over time, then drop the inputs.
   ```
4. **Prove it locally**: lint + typecheck + coverage-at-baseline must pass before you
   commit the workflow. A gate that is born red is a calibration failure — remeasure.

## Stage 4 — Connections (if chosen)

Load the `connections` skill and walk its checklists (each opens and closes with a
verification command; PENDING for anything needing rights you don't have).

## Stage 5 — Release management (if chosen)

Wire release-it so the project gets a version bump + `CHANGELOG.md` from its Conventional
Commits (the `release` task / `/wellforge:release`). Additive; never destructive.

1. **Never run two release tools — detect an existing one FIRST.** Look for
   `.releaserc*`/`release.config.*` (semantic-release), `.changeset/` (Changesets),
   `.versionrc*`/`standard-version`, a release GitHub Action, or a maintained `CHANGELOG.md`
   with real history. If ANY exists: **STOP this stage**, report it, and do NOT add release-it
   (offer to document their existing process in AGENTS.md instead). Never fight a working setup.
2. **Version source — git tags (default).** release-it reads the latest `vX.Y.Z` tag as the
   base and computes the bump from the commits. If there are NO release tags yet but a
   manifest carries a version (`package.json`/`pom.xml`/…), use that as the starting version;
   note future versions come from tags. Match the project's existing tag style (`v` prefix or
   not) if it already tags.
3. **Detect the version files to keep in sync** — document what IS, include only files that
   actually carry a version:
   - `package.json` (root and/or each package in a monorepo) → `@release-it/bumper` `out`.
   - `pom.xml` → `hooks.after:bump`: `mvn versions:set -DnewVersion=${version} -DgenerateBackupPoms=false` (mvnw or mise-provided mvn).
   - `build.gradle(.kts)` → a hook or a bumper regex on the `version` line.
   - `pyproject.toml` → bumper (`project.version` or `tool.poetry.version`).
   - `Cargo.toml` → bumper (`package.version`).
   - None carry a version → git tags alone are fine (no bumper `out`).
4. **Write `.release-it.json`**: `npm.publish:false` (adoption never publishes a package
   unless the user explicitly asks), `github.release:true`, the `@release-it/conventional-changelog`
   plugin (`preset: conventionalcommits`, `infile: CHANGELOG.md`), and the bumper `out`/hooks
   from step 3. Mirror the project's commit/tag conventions.
5. **How to run it** — if the repo uses mise, add a `release` task like the scaffold's
   (`pnpm --package=release-it@^17 --package=@release-it/conventional-changelog@^8 --package=@release-it/bumper@^6 dlx release-it`);
   otherwise document `npx release-it` in AGENTS.md. Needs Node available.
6. **Conventional Commits from here on** — the changelog only works if commits are
   conventional going forward (historical commits stay as-is; the first notes start clean at
   the current tag). **Strongly recommend the commit-lint gate** (Quality-gates layer) so it's
   enforced — say so explicitly. Do NOT run a release during adoption; that's `/wellforge:release`.

## Stage 6 — Hand off

1. One commit: `chore: adopt WellForge (workflow[, gates][, release][, connections])` —
   adoption must be a single revertable diff.
2. Summary table: layer / added files / status (incl. measured baseline vs central
   target, the release version source + files synced, and any stage stopped with reasons —
   npm migration, Gradle, existing release tool, …).
3. Suggest the natural next step: `/wellforge:spec <first feature>` — or
   `/wellforge:orchestrate` for a pending bugfix, which doubles as a workflow demo.

## Hard rules

- Adoption ADDS files (AI-readiness, `quality.yml`, `.release-it.json`); it never modifies
  existing source or build config, and never a version file except at an explicit
  `/wellforge:release` later. Aligning the project to WellForge conventions is refactor work —
  offer `/wellforge:orchestrate` for it, separately, after adoption.
- Never wire release-it over an existing release tool (semantic-release, Changesets, …) —
  detect and defer. Two release tools on one repo is a footgun.
- Never invent conventions for AGENTS.md — document what IS, not what should be.
- Baselines come from measurement, never estimation; round down; prove green locally.
- No `.forge/manifest.json` for adopted projects — that file means "born from the
  template" and would corrupt the upgrade contract.
