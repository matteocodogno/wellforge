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
