---
id: 003
slug: ts-stack-migration
status: draft
rigor: production
created: 2026-09-20
---

# TypeScript stack migration — bring the Node presets to current majors

## Problem

The `hono-react` preset and the `hono-ts-backend` / `react-ts-vite` skills pin a TypeScript
stack that is one to three majors behind, and the skills' code examples use the pinned
versions' idioms throughout. Checked against the npm registry on 2026-09-20:

| Package | Pinned | Current | Gap |
|---|---|---|---|
| `zod` | `^3.24.1` | 4.6.5 | major — `.uuid()` → `z.uuid()`, `error.errors` → `error.issues` |
| `@hono/zod-openapi` | `^0.18.4` | 1.6.3 | major — **requires zod 4** |
| `@biomejs/biome` | `^1.9.4` | 2.5.14 | major — config migration (`biome migrate`) |
| `vitest` | `^2.1.8` | 5.0.1 | three majors |
| `typescript` | `^5.7.2` | 7.0.2 | major |
| `tailwindcss` | `^3.4.16` | 4.x | major — CSS-first, no JS config |
| `effect` | `^3.12.5` | 3.22.2 | minor (the removed `yield* _(x)` adapter is already fixed) |

Every new project scaffolded from the preset starts on these, and every agent that reads the
skills writes code in the old idioms. The cost compounds: the longer the gap, the larger the
single migration, and `@hono/zod-openapi` 1.x already forces zod 4 rather than allowing it.

This was deliberately **not** fixed when the staleness was found (2026-09-20). Raising the
numbers alone would ship a preset whose own examples don't compile, and there is no way to
tell the difference without a build — which is how every other defect found that day
survived. The note at `hono-ts-backend/references/project-setup.md` records that decision;
this spec is the debt it created, so it can be seen rotting instead of remembered.

## User stories

### US-1: A new project scaffolds on a current, coherent stack
As a developer running `/wellforge:new`, I want the generated Node project to use current
major versions, so that I am not starting a new codebase on a migration I will have to do.

**Acceptance criteria:**
- AC-1.1: Given the `hono-react` preset, when `mise run install && mise run build && mise run test`
  runs on a freshly generated project, then all three succeed with the bumped pins.
- AC-1.2: Given the generated backend, when `mise run lint` runs under Biome 2.x, then it
  passes with a migrated config and no deprecated-option warnings.
- AC-1.3: Given the generated project, when `node dist/index.js` runs after `mise run build`,
  then the process reaches runtime (env validation is the only acceptable failure).

### US-2: Skill examples compile against the versions they pin
As an agent writing code from `hono-ts-backend` or `react-ts-vite`, I want every example to
use the idioms of the pinned major, so that code I copy runs.

**Acceptance criteria:**
- AC-2.1: Given the skills' zod examples, when reviewed against zod 4, then no example uses
  `.uuid()` as a string method or reads `error.errors`.
- AC-2.2: Given every TypeScript block in both skills, when extracted and type-checked
  against the bumped versions, then each compiles.
- AC-2.3: Given the version table in `project-setup.md`, when compared against the preset's
  `package.json`, then every shared package matches — one source of truth, no second list.

### US-3: The deferral note stops lying once it's done
As a maintainer, I want the "pins are a major behind" warning removed in the same change
that bumps them, so that the docs never describe a state that no longer exists.

**Acceptance criteria:**
- AC-3.1: Given the migration is complete, when `project-setup.md` is read, then the
  staleness note is gone and the pins shown match the preset.
- AC-3.2: Given this spec, when the work lands, then its status is `done` via
  `/wellforge:done` — or `archived` with a reason, if the decision is reversed.

## Non-goals

- **The JVM preset.** Spring Boot / jOOQ / Modulith versions are a separate matrix with a
  separate blocker — RESOLVED in template `v0.10.0`: `spring-modulith-starter-jooq` was
  never published in any Spring Modulith release (a nonexistent artifact, not a missing
  managed version), and the preset now uses `spring-modulith-starter-jdbc`.
  Mixing them makes both harder to verify.
- **Tailwind 4 as part of the same change.** It is CSS-first with no JS config, which makes
  it a frontend restyle rather than a pin bump. Split it out unless the frontend build
  forces it.
- **Chasing the newest version at merge time.** Pick the majors, verify them, land them. A
  migration that re-targets mid-flight never finishes.
- Changing what the presets *do*. This is a version migration, not a redesign.

## Constraints

- **Blocked on a green baseline.** The verification for every AC here is "the preset builds
  and tests green", so this cannot start until there is a green build to compare against.
  `hono-react` installs green as of 2026-09-20; its `build`/`test` are unverified.
- Templates change, so landing this requires a template `vX.Y.Z` release to reach existing
  projects — and existing projects adopt it through `/wellforge:upgrade`, not automatically.

## Open questions

- [ ] Does `@hono/zod-openapi` 1.x change the route-definition API beyond the zod 4
      requirement, or is it a re-release? — owner: whoever picks this up
- [ ] Is TypeScript 7 safe for the preset's config (`moduleResolution: "bundler"`,
      `isolatedModules`, `verbatimModuleSyntax`), or should it lag one major deliberately?
      — owner: same
- [ ] Vitest 2 → 5 spans three majors; is there a config or API break that affects the
      preset's coverage thresholds feeding the quality gate? — owner: same
