---
description: Adopt WellForge in an existing (brownfield) project — AI-readiness, spec workflow, calibrated quality gates
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

## Stage 5 — Hand off

1. One commit: `chore: adopt WellForge (workflow[, gates][, connections])` — adoption
   must be a single revertable diff.
2. Summary table: layer / added files / status (incl. measured baseline vs central
   target, and any stage stopped with reasons — npm migration, Gradle, …).
3. Suggest the natural next step: `/wellforge:spec <first feature>` — or
   `/wellforge:orchestrate` for a pending bugfix, which doubles as a workflow demo.

## Hard rules

- Adoption ADDS files; it never modifies existing source, build config, or CI beyond
  the new `quality.yml`. Aligning the project to WellForge conventions is refactor work —
  offer `/wellforge:orchestrate` for it, separately, after adoption.
- Never invent conventions for AGENTS.md — document what IS, not what should be.
- Baselines come from measurement, never estimation; round down; prove green locally.
- No `.forge/manifest.json` for adopted projects — that file means "born from the
  template" and would corrupt the upgrade contract.
