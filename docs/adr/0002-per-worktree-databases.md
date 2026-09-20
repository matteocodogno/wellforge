# 0002 — Per-Worktree Database Isolation, Derived from Checkout Path

**Date:** 2026-09-20
**Status:** Accepted
**Deciders:** WellForge plugin + template maintainers
**Project:** templates/spring-kotlin-react, templates/hono-react

---

## Context

`CLAUDE.md` and `wellforge-plugin/skills/worktree-isolation/SKILL.md` both state that a git
worktree isolates the **checkout** and nothing else — not databases, ports, containers, or the
migration counter. The skill's shared-state enumeration classes databases as "test: isolate,
dev: forbid" (class 1), but no preset implemented that isolation, so the dispatch-time
preflight had to fall back to sequential execution for most backend batches of ≥2. The
template half of Phase 16 was explicitly deferred to its own `vX.Y.Z` cut. This ADR is that
deferred half, landing in `templates/spring-kotlin-react` and `templates/hono-react`.

Every failure in this class has one shape: **two checkouts, one name, one object.**

## Decision

We will derive a per-worktree database identity, port and compose project name from the
checkout's own absolute path, inject them through `mise`'s `[env]` block, isolate that
identity only for linked worktrees, and back it with a project-shipped guard task that
refuses to run against a mismatched database.

1. **One derived identity, from the checkout's absolute path.** A shipped POSIX-sh script
   (`.wellforge/worktree-id.sh` in each preset) turns `git rev-parse --show-toplevel` into a
   per-checkout identity via `sha256(path) | cut -c1-8`:
   - `suffix`: `""` for the primary tree, `_wt<hash8>` for a linked worktree
   - `id`: `main` | `wt<hash8>`
   - `port`: `$WF_DB_BASE_PORT` (default `5432`) for primary; `base + (hash mod 1000)` for
     linked
   - `linked`: yes|no — detected by `git rev-parse --git-dir != --git-common-dir`

   Derived from the path, never a timestamp or random value, so a re-run in the same worktree
   resolves to the **same** database and port — otherwise cleanup leaks and reruns are not
   reproducible.

2. **The primary tree keeps the plain database name and port 5432.** An existing project
   taking this upgrade must not have its dev database orphaned mid-work. Isolation applies
   where the collision actually happens: linked worktrees.

3. **Injected through mise `[env]`, nothing hard-coded.** Verified on mise 2026.9.11: `[env]`
   values support Tera templating, `{{ exec(command=...) }}` runs the script, and
   `{{ env.VAR }}` / `${VAR}` both reference earlier entries in the same block. Exactly two
   `exec` calls (suffix, port) produce every downstream value by templating: `WF_DB_NAME`,
   `COMPOSE_PROJECT_NAME`, `DATABASE_URL`. Identity resolves identically from any subdirectory
   because it comes from git, not `$PWD`.

4. **Tests use Testcontainers; `mise run dev` uses one named compose project per worktree.**
   - Integration tests get an ephemeral container with a random host port per run — no shared
     container to collide on, and nothing to clean up. This is the preferred answer: it makes
     the test half of class 1 a non-problem rather than a managed one.
   - Both presets keep their default `mise run test` lane Docker-free (JVM: surefire /
     `ModularityTest`; Hono: vitest with the db module mocked) — requiring Docker for unit
     tests would be a real regression. Integration tests are a separate lane
     (`mise run test:integration`): JVM via maven-failsafe (`*IT`), Hono via a separate vitest
     config.
   - `mise run dev` uses the long-lived compose stack, so it takes `COMPOSE_PROJECT_NAME` plus
     the derived published port.

5. **A `mise run db:guard` task, shipped by the template, not the plugin.** It refuses to run
   migrations or destructive test setup against a database whose name is not this checkout's
   expected `WF_DB_NAME`, and is wired into the dev and migration tasks. Per the skill's "Where
   the guard lives" section, this layer — the project's own task definitions — is the only
   place the guard is present for a human running the command by hand, and where no dispatching
   agent can forget it. The plugin cannot enforce it and should not pretend to.

## Failure shape

**What class of mistake does this prevents, stated so it's recognisable somewhere we haven't
been yet:** two independent actors each compute the same name for what they believe is their
own private resource, because that name was derived from something that doesn't vary between
them (a fixed string, a shared working-directory convention, a directory basename) rather than
from something that uniquely identifies each actor. Neither actor sees a conflict at the point
where the name is chosen — the collision only surfaces later, against the resource itself, as
data that doesn't match what either actor just wrote, or as a bind that fails against a port
already claimed. The fix is never "add a check where the collision was noticed"; it is to
derive the identity from something that is unique to the actor in the first place, so the
collision cannot occur upstream of any check.

This shape recurs anywhere two concurrent contexts each construct a name, key, or address from
a convention rather than an identity: two CI jobs writing to the same S3 prefix because both
used the branch name instead of the run ID; two browser tabs of the same app writing to the
same `localStorage` key because the key was hardcoded rather than session-scoped; two consumers
of a queue computing the same idempotency key from a timestamp truncated to the same second;
a cache key built from a request path but not its tenant. The read side and the write side are
both exposed symmetrically here: a worktree that only *reads* the dev database (a report, a
seed-data check) is just as capable of reading another worktree's half-migrated state as a
writer is of corrupting it — the guard in this decision covers both because it gates on
identity mismatch, not on write intent. Recognise it by asking: *does this name depend on
something unique to this run, or only on something both runs share?*

## Options considered

### Option A — Derive identity from the checkout's absolute path hash (chosen)
`sha256(git rev-parse --show-toplevel) | cut -c1-8`, primary tree exempted.

**Pros:**
- Unique per checkout by construction; a basename collision across repos or two worktrees of
  different projects sharing a directory name cannot happen.
- Produces a value that is already a legal identifier fragment (hex), usable directly in a
  database name, a compose project name, and a port offset, with no further sanitization.
- Deterministic and reproducible: the same worktree always resolves to the same identity, so
  cleanup and reruns behave correctly.

**Cons:**
- A hash is opaque — a human cannot read a worktree's database name and know which branch it
  belongs to without running the script.
- Small residual port-collision probability between two worktrees (see failure shapes below).

### Option B — Derive identity from the worktree's directory basename
This is what the `worktree-isolation` skill's own isolation-key example currently shows
(`WF_WORKTREE_ID="$(basename "$(git rev-parse --show-toplevel)")"`), and was the first
candidate considered for the database identity too.

**Pros:**
- Human-readable: the database name matches the folder you're standing in.
- No hashing step.

**Cons:**
- Rejected: a basename is not a legal database identifier (it can contain characters a
  database name can't) and is not a number (can't be used directly as a port offset without an
  extra derivation step). It also collides across repos — two different projects with
  worktrees both named, say, `feature-x`, would derive the same identity despite having
  nothing in common — which the absolute-path hash cannot do.

### Option C — Isolate the primary tree as well as linked worktrees
Give every checkout, primary included, a derived suffix and port.

**Pros:**
- Simpler mental model: no special case for "am I the primary tree."
- Would also isolate the two-clones case (see failure shapes).

**Cons:**
- Rejected: an existing project taking this upgrade has real work sitting in its plain-named
  dev database. Renaming the primary tree's database out from under it on upgrade orphans
  that data. Isolation is only needed where the collision actually happens — between linked
  worktrees — not on the tree that was always there.

## Consequences

**Positive:**
- Backend batches of ≥2 can run in parallel on projects at or above the template version that
  ships this ADR, where they previously fell back to sequential dispatch for class 1. The
  worktree-isolation skill's class-1 row moves from "sequential unless isolated" to "isolated
  by the preset from this template version onward; older projects stay sequential" — the
  dispatch-time preflight reads `.forge/manifest.json`'s recorded template version to decide
  which applies.
- Integration tests no longer share a container to collide on, and leave nothing to clean up
  between runs.
- The guard makes an operator's deliberate override (via `.mise.local.toml`) a conscious act
  instead of an accident, without removing the override itself.

**Negative / trade-offs:**
- Costs two subprocess spawns per `mise` invocation (~20-30ms).
- No new gitignored file and no new required copier answer — the template contract is intact —
  but one new optional knob, `WF_DB_BASE_PORT`, is introduced. It is documented as a
  `.mise.local.toml` override, not a copier question: it is machine-local, and a persisted
  answer would replay one machine's port choice into every future render.

**Risks:**
- **Two worktrees hashing to the same port offset** (~1/1000 per pair, since the offset is
  `hash mod 1000`): both derive the same published port. The second `docker compose up` fails
  to bind — loud and immediate, not silent cross-talk. The database *names* still differ (they
  carry the full 8-hex hash, not the modulo), so no worktree can read or migrate another's data
  even in this case. Escape hatch: set `WF_DB_BASE_PORT` in `.mise.local.toml`.
- **Two separate clones of the same repo** both present as primary trees, so both resolve to
  the plain name and port 5432. This is **not** isolated, by decision point 2 above — a known
  limitation, not an oversight, with the same `WF_DB_BASE_PORT` escape hatch. Worktrees, not
  clones, are what the parallel-dispatch protocol creates, so this is out of scope for the
  case this ADR addresses.
- **Guard false negative:** a hand-written connection string that bypasses `DATABASE_URL` is
  not seen by the guard. The guard checks the target it is given; it is a ratchet on the
  sanctioned path, not a sandbox.
- **`.mise.local.toml` overriding `DATABASE_URL`** wins over the derived value — that is
  mise's precedence and is intended for the escape hatch — so an operator can still point a
  worktree at a shared database deliberately. The guard is what turns that into a conscious
  act: it compares the target against the expected name and refuses unless the names agree.

## Compliance notes

Not applicable — this decision has no data-protection, residency, or audit-trail impact; it
concerns local development and test database naming only.

---

*This ADR was generated during a WellForge spec-driven session. Review and amend before committing.*
