# Template migrations — project-side notes, per template version

`.forge/manifest.json` records the **template** version a project was generated from or last
upgraded to. `copier update` re-renders the files; this file records what a human has to know
or do **around** that re-render — the part copier cannot perform and a diff does not explain.

**Read by `/wellforge:upgrade`**, which compares the recorded template version against the
target and surfaces every entry in between. The sibling file for the plugin series is
[`PLUGIN-MIGRATIONS.md`](PLUGIN-MIGRATIONS.md); the two series are independent
([`VERSIONING.md`](VERSIONING.md)).

## What belongs here

Only what a **project** must absorb: a new file it needs to run, a task that changed meaning,
a pinned dependency whose bump it must reconcile, a one-off command to run after the update.
A cosmetic re-render does not belong here — copier already shows it in the diff.

The test: *after a clean `copier update`, would something still be wrong, surprising, or
need a human?* If no, it is not a migration.

An entry with no project-side action still gets a line saying so — silence is ambiguous
between "nothing to do" and "nobody wrote it down".

---

## v0.10.2 — spring-kotlin-react passes its own gates, and the compose promise is real

**Action: one command, and only if your `project_slug` contains a hyphen** — see the end.

`generated-gates` (added in v0.10.1) covered hono-react and pulumi-gcp-ts. Turning it on for
spring-kotlin-react found that a fresh scaffold failed its own gates too, and that two things
the preset documents were never wired.

**The docker-compose promise**

`AGENTS.md` and the `backend:run` task description both say Docker Compose starts
automatically. It did not. Spring Boot's compose support resolves the file against the
**process working directory** — `backend/`, because Maven runs there — while
`docker-compose.yml` lives at the monorepo root. It found nothing and said nothing.
`spring.docker.compose.file: ../docker-compose.yml` makes the documented behaviour the actual
behaviour: verified live in a linked worktree, `Using Docker Compose file …/docker-compose.yml`
then the container started and went healthy.

**The event publication registry**

With compose finally starting, the app got far enough to fail on something else:
`BadSqlGrammarException` on a missing `EVENT_PUBLICATION` table. `spring-modulith-starter-jdbc`
stores the registry there and nothing created it. `spring.modulith.events.jdbc.
schema-initialization.enabled: true` applies Modulith's own DDL on startup. This was latent
before: the POM used to name `spring-modulith-starter-jooq`, an artifact that has never been
published in any Modulith release, so the POM did not parse and the app never started at all.

**Gates that could not pass**

- The frontend had no test at all, and `mise run frontend:test` therefore failed on an empty
  run. It now ships `src/features/home/HomePage.test.tsx` with a jsdom `vitest.config.ts` and
  a `matchMedia` stub (Mantine needs it), plus the three dev dependencies they require.
- `eslint.config.ts` was not covered by any `tsconfig` include and could not be linted or
  type-checked; it is now `eslint.config.js`, which is what flat config expects anyway.
- `backend:run` and `backend:generate` are named in `AGENTS.md` but had no delegation tasks,
  so both failed with `task not found` — the exact failure the comment above that section
  warns about.
- `.claude/settings.json` pre-allowed `Bash(./mvnw:*)`. No wrapper is shipped; the tasks call
  `mvn` from mise. Now `Bash(mvn:*)`.
- The generated application class was `OrderserviceApplication`: `capitalize` was applied to
  the package's last segment, which is already lowercased with the word boundaries stripped.
  It now derives from `project_name`, which still has them.
- `db = none` did not compile — `Result.kt` imported `org.springframework.dao` unconditionally
  while the dependency is Postgres-only. Both the import and its `catch` are now guarded.

**Version tables that had drifted**

`AGENTS.md` claimed jOOQ 3.19.18 and Testcontainers 1.20.4 while the POM pinned 3.19.38 and
1.21.4 — and 3.19.18 was never published as a BOM, so a reader who trusted the table got a 404.
The table now points at `backend/pom.xml` instead of copying it. The `kotlin-springboot` skill
carried the same two wrong numbers and the phantom `-jooq` starter; both are corrected there.

**The one action.** `WF_DB_NAME` now replaces hyphens with underscores, matching hono-react
(Postgres accepts a hyphenated name only when quoted). If your `project_slug` has a hyphen,
your local dev database is about to be addressed under a new name, and the old one's data will
look like it vanished. It has not — it is still in the old database. Either re-run your
migrations against the fresh one (`mise run db:up`), or rename in place:

```sh
psql -h localhost -p "$WF_DB_PORT" -U postgres \
  -c 'ALTER DATABASE "my-service" RENAME TO my_service;'
```

CI, tests and throwaway environments need nothing: they create the database from scratch.

---

## v0.10.1 — the presets pass their own gates

**Action: none, beyond `copier update`** — with one thing to check, at the end. Every change
is inside files the template owns.

Until now a freshly scaffolded hono-react or pulumi-gcp-ts project failed its OWN
`mise run lint / typecheck / test / build` before anyone had written a line of code. CI
never caught it: the scaffold job asserted the contract files existed and never ran what the
preset ships. The new `generated-gates` job does.

**pulumi-gcp-ts**

- The root `mise run install / build / test / lint / dev` never worked at all. They declare
  `depends = ["infra:install"]` and so on, but no `infra:*` delegation tasks existed, so
  each failed with `task not found`. The other two presets carry that delegation block for
  backend/frontend; this preset shipped without it.
- `tsconfig.json` and `policy/tsconfig.json` paired `module: commonjs` with
  `moduleResolution: node16`, which tsc rejects outright (TS5110) — so typecheck and build
  failed before reading a single file. Now `node10`, keeping the CommonJS that Pulumi's
  Node runtime requires. The `pulumi-gcp-ts` skill's reference carried the same broken pair
  and is fixed with it.

**hono-react**

- `backend/vitest.config.ts` had no `test.exclude`, so the default `vitest` run picked up
  `src/db/*.integration.test.ts` and tried to reach a real database: `mise run test` failed
  with ECONNREFUSED on any machine without Postgres. Integration tests now have exactly one
  entry point, `mise run backend:test:integration`.
- The frontend's `test` block moved out of `vite.config.ts` into its own
  `vitest.config.ts`. It could not type-check where it was: the preset pins vite ^6 and
  vitest ^2, and vitest 2 bundles vite 5, so each of the two possible `defineConfig`
  imports produces a different TS2769. Splitting the files removes the conflict without
  moving the pins (that is specs/003-ts-stack-migration).
- `"typecheck": "tsc --noEmit"` ran against a solution-style `tsconfig.json` (`"files": []`)
  and therefore checked **nothing**, passing whatever the app contained. It is now
  `tsc -b --noEmit`.
- `@types/node` was missing although `vite.config.ts` uses `node:path` and `__dirname`;
  `vite-env.d.ts` needed a real `eslint-disable` for the declaration-merging exception its
  own comment already described; and the template's sources had never been run through the
  preset's own formatter.
- **`.gitignore` no longer ignores `frontend/.env`.** The bare `.env` rule excluded the very
  file the template ships, so `git add -A` silently dropped it and the frontend lost its
  non-secret `VITE_` defaults. The rules now match the spring preset: `.env` committed,
  `.env.local` and `.env.*.local` ignored.

  **This is the one thing to check after updating.** If your project has a
  `frontend/.env`, it was never tracked — git will now offer it as a new file. Look at it
  before committing: anything secret in there has been living untracked and should move to
  `.mise.local.toml`, which stays ignored.

**spring-kotlin-react is not covered by this release.** Its frontend lint/build (an
outdated `jiti`), its frontend test lane ("No test files found") and its backend ktlint
are still red on a fresh scaffold; the `generated-gates` job reports them on every push.
Nothing here regresses that preset — it is simply untouched.

**For the repo, not for projects:** `scripts/format-templates.sh` renders each preset, runs
the preset's own formatter over the output, and copies the result back into the template —
so the next edit is judged by the formatter the generated project will use. It never
rewrites a `.jinja` source automatically (its render has the answers baked in); those are
reported with a diff and applied by hand.

## v0.10.0 — per-worktree databases

**Action: one command, plus two reconciliations if you pinned things yourself.**

Both application presets now derive the database name, published host port and compose
project from the checkout's own path, so two git worktrees of one repo can no longer resolve
to the same database ([ADR 0002](adr/0002-per-worktree-databases.md)).

1. **Run `mise trust` after the update.** This is the one required step. The update adds an
   `[env]` block that computes those values by executing `.wellforge/worktree-id.sh`, and
   mise refuses to run a config it has not been told to trust. The failure mode if you skip
   it is the quiet one: the variables resolve to nothing and every checkout falls back to the
   same database — exactly the situation the change removes. `mise run wt:info` prints what
   this checkout actually resolved; run it once and look.

2. **Your existing dev database is untouched.** The primary tree keeps the plain name and
   port 5432 on purpose; only linked worktrees are suffixed. Nothing to migrate, no data to
   move.

3. **Check the new scripts are executable** — `.wellforge/worktree-id.sh` and
   `.wellforge/db-guard.sh`. Copier preserves the mode on a clean create, but a three-way
   merge on an existing file can drop it:

   ```bash
   chmod +x .wellforge/*.sh
   ```

4. **`mise run test` and `mise run dev` now depend on `db:guard`.** It refuses when the
   configured database is not this checkout's. If it refuses on your primary tree, something
   in `.mise.local.toml` is pointing the project at a different database — that is a real
   finding, not a false positive. Setting `WF_DB_NAME` makes the guard agree with you; do it
   deliberately or not at all.

5. **New lane: `mise run backend:test:integration`** (Testcontainers, needs Docker). The
   default `mise run test` stays Docker-free. If your CI ran integration tests through
   `mise run test`, point it at the new task.

6. **JVM preset only — two pins moved**, and if you overrode either in your own `pom.xml`
   you must reconcile:
   - `spring-modulith-starter-jooq` → **`spring-modulith-starter-jdbc`**. The jOOQ starter
     has never existed in any published Spring Modulith release, so this dependency made the
     POM unparseable and the backend could not build at all. Your data access stays jOOQ;
     only the event-registry storage is JDBC.
   - Testcontainers `1.20.4` → **`1.21.4`**. 1.20.4 cannot find a Docker environment under
     OrbStack (its Docker-Desktop strategy throws before any other strategy is tried), so
     integration tests failed on machines where `docker ps` works fine. Do not jump to 2.x
     without a migration: it restructured the BOM and
     `org.testcontainers:postgresql`/`junit-jupiter` stop resolving.

**Optional knob, not a copier answer:** `WF_DB_BASE_PORT` in `.mise.local.toml`, if 5432 is
already taken on your machine. It is machine-local, which is why it is not a question — a
persisted answer would replay one machine's port choice into every future render.
