# Template contract

Every WellForge Copier template MUST satisfy this contract. `/wellforge:new` and
`/wellforge:upgrade` depend on it; CI gate wiring and the Phase 6 lifecycle break if a
template drifts from it.

## Copier configuration (root `copier.yml` — monorepo pattern)

ONE `copier.yml` at the **wellforge repo root** serves all presets: a `preset` question
selects the stack and `_subdirectory: "templates/{{ preset }}/template"` picks the file
tree. This is not cosmetic — `copier update` (Phase 6 lifecycle) requires the template
source to be the git repo root, versioned by repo-wide `vX.Y.Z` tags. Presets do NOT
have their own copier.yml; preset-specific questions live in the root file guarded with
`when: "{{ preset == '<name>' }}"`.

Generate:
```bash
uvx copier copy --trust <wellforge repo/URL> <dest> --data preset=<preset>
```

- `_min_copier_version: "9.0.0"`.
- Common questions (every preset, same names — `/wellforge:new` fills them):

| Question | Type | Notes |
|---|---|---|
| `project_name` | str | human name, e.g. "Order Service" |
| `project_slug` | str | default derived from project_name (kebab-case); dir + artifact name |
| `description` | str | one line |
| `ci` | choice | `github` (default) / `none` |
| `rigor` | choice | `production` (default) / `mvp` / `spike` — sets CI strictness; recorded in the manifest (wellforge rigor-tiers skill) |
| `gates_repo` | str | default `matteocodogno/wellforge` — owner/repo hosting the reusable gate workflows |
| `gates_ref` | str | default `gates-v11` — tag pinned in generated CI |
| `heartbeat` | bool | default `true` — add the scheduled heartbeat workflow (re-runs the gate on a cadence, files findings to one deduplicated issue). Takes effect only for `ci == github` and `rigor != spike`; recorded in the manifest |
| `heartbeat_cron` | str | default `0 6 * * 1` (weekly, Mon 06:00 UTC) — cron for the heartbeat |

No "generated date" question/field: hidden (`when: false`) answers are not persisted to
`.copier-answers.yml`, so copy-time injected values diverge from the re-rendered base on
`copier update` and cause spurious conflicts. Generation date lives in git history.

Stack-specific questions (base_package, db, auth, …) are free per template but must have
sensible defaults so `copier copy --defaults` always produces a valid project.

## Required generated files

| File | Requirement |
|---|---|
| `.forge/manifest.json` | `{ "template": "<name>", "version": "<template version>", "answers": { …all answers… } }` — the upgrade contract. The **command** adds a `plugin` object after generation; see below |
| `.copier-answers.yml` | standard copier answers file (`{{ _copier_answers\|to_nice_yaml }}`) — enables `copier update` |
| `AGENTS.md` | project context (canonical, cross-tool standard): stack + versions, dev commands (mise tasks), architecture pointers, spec-driven workflow note (`specs/` + plugin commands) |
| `CLAUDE.md` | one-line `@AGENTS.md` import for Claude Code — content lives in AGENTS.md only |
| `.claude/settings.json` | pre-wired permissions for the stack's routine commands (mise/pnpm/mvnw test-build-lint) |
| `specs/README.md` | one-paragraph pointer to the spec-driven workflow |
| `mise.toml` (+ per-service) | per the `mise` skill: tools pinned at root, tasks per service, `install/build/test/lint/dev` aggregates + `release` (release-it) and `git-policy` (linear-history git config, run once per clone) tasks at root. From `v0.10.0`, presets with a database also carry the worktree-isolation `[env]` block and the `db:guard` / `wt:info` / `backend:test:integration` tasks — see below |
| `.github/workflows/quality.yml` | when `ci == github`: **calls** the reusable gates `{{ gates_repo }}/.github/workflows/*.yml@{{ gates_ref }}` (never inlines gate logic). Tier-conditional on `rigor`: `production`/`mvp` call `quality-<stack>.yml` (passing `rigor` so `mvp` coverage is advisory); `spike` calls `security-floor.yml` + a build sanity job only. **`linear-history.yml` is called at every tier** (tier-independent, like the security floor — a merge commit can't be fixed retroactively). When the preset has backing services (`hono-react` with `db == postgres`), the backend job also passes `compose-file` + `env-file` so integration tests get a real database; `pretest-command` ships commented out (a fresh scaffold has no migrations) |
| `.github/workflows/heartbeat.yml` | **conditional** — generated only when `ci == github` AND `heartbeat` AND `rigor != spike`. A `schedule`d (cron `heartbeat_cron`) + `workflow_dispatch` caller that re-uses the same `quality-<stack>.yml@{{ gates_ref }}` gates (→ `heartbeat-report.yml` for one deduplicated findings issue) and calls `template-drift.yml@{{ gates_ref }}` (→ a separate deduplicated "behind template" issue). Needs `issues: write`. Uses the copier `{% if %}` filename idiom so it vanishes when off |
| `.gitignore` | stack-appropriate + `.mise.local.toml`, `.claude/settings.local.json` |
| `.wellforge/worktree-id.sh` | **presets with an application database.** POSIX-sh, executable. Derives this checkout's isolation identity from `sha256(git rev-parse --show-toplevel)`: `id`, `suffix`, `port`, `linked`. Read by the `[env]` block and by `db-guard.sh`; the worktree-isolation skill reads it instead of computing its own key |
| `.wellforge/db-guard.sh` | **presets with an application database.** POSIX-sh, executable. Refuses to act on a database whose name is not this checkout's `WF_DB_NAME`. Wired into `dev`, `test` and every migration task as a `depends` |
| `.release-it.json` | release-it config: `@release-it/conventional-changelog` (semver bump + CHANGELOG from Conventional Commits) + `@release-it/bumper` (per-service version files); `npm.publish:false`; JVM preset bumps `pom.xml` via a Maven `after:bump` hook. Drives `mise run release` / `/wellforge:release` |
| `README.md` | quickstart: `mise install && mise run dev`, layout table, link to CLAUDE.md |

## The `plugin` object — written by the command, never a copier answer

`.forge/manifest.json` records the **template** version, which is what makes `copier update`
possible. It does not record which **plugin** version set the project up — yet the project's
`AGENTS.md` conventions, the spec-driven file formats, the `.forge/runs/` trace schema and
the hooks all change with the plugin. A project scaffolded by plugin 2.20 and driven by 2.38
is a real and currently invisible situation.

Every scaffolded project therefore carries:

```json
{ "template": "hono-react", "version": "0.9.0",
  "answers": { "…": "…" },
  "plugin": { "version": "2.42.0", "set_by": "new", "at": "2026-09-20",
              "marketplace": "wellforge@wellforge" } }
```

`set_by` is `new` | `adopt` | `upgrade`. `marketplace` is where the plugin came from —
`wellforge@wellforge` for a marketplace install, or `local` when it was run from a checkout
with `--plugin-dir`. Absent means "recorded before 2.42, unknown": readers report unknown,
they do not assume. Adopted projects carry the same object in `.forge/adoption.json` (which
previously held `plugin` as a bare version string — readers must accept both and writers
must emit the object).

**It is NOT a copier question, and the templates must not render it.** Two reasons, and the
second is the one that bites:

1. A persisted answer would be *the plugin version at scaffold time, replayed forever*:
   `copier update` re-renders from recorded answers, so the manifest would keep asserting
   2.20 no matter which plugin ran the upgrade. The field would be actively wrong at exactly
   the moment it matters.
2. A hidden (`when: false`) answer is not persisted at all, which is the documented trap this
   repo already hit with a generation date — the re-rendered base diverges from the project
   and every future `copier update` conflicts on the manifest.

So the template emits a manifest **without** the key and the command writes it afterwards.
On `copier update` the re-rendered base still lacks the key while the project has it, so the
template side never touches those lines and the three-way merge should keep them.

**That last sentence is reasoning, not a measurement** — three attempts to exercise a real
`copier update` against a local template source were refused by copier before the merge
(`Updating is only supported in git-tracked templates` / `cannot obtain old template
references`), so the merge itself is unproven here. It is also not load-bearing:
`/wellforge:upgrade` rewrites the `plugin` object as part of every upgrade, so the field is
correct afterwards even if a merge were to drop it. Worth confirming for real the first time
an upgrade runs against a git-hosted template.

The same rule in one line: **anything whose value depends on *when the command ran* rather
than *what the user answered* is written after generation, not asked by copier.**


## Worktree isolation — derived, not asked (template `v0.10.0`+)

Presets with an application database MUST derive their database name, published host port
and compose project from the checkout, so two git worktrees of one repo never resolve to the
same database. The rule and its failure shapes are
`docs/adr/0002-per-worktree-databases.md`; the contract is what a template must emit.

The root `mise.toml` `[env]` block exports, via `.wellforge/worktree-id.sh`:

| Variable | Primary tree | Linked worktree |
|---|---|---|
| `WF_WT_SUFFIX` | `""` | `_wt<hash8>` |
| `WF_DB_NAME` | `<slug>` | `<slug>_wt<hash8>` |
| `WF_DB_PORT` | `5432` | `5432 + (hash mod 1000)` |
| `COMPOSE_PROJECT_NAME` | `<slug>` | `<slug>_wt<hash8>` |

**The primary tree keeps the plain name and port.** That is a contract requirement, not an
implementation detail: an existing project taking this upgrade must not find its dev database
renamed out from under it.

Requirements:

- The compose file reads `${WF_DB_NAME:-<slug>}` and `${WF_DB_PORT:-5432}` — the `:-`
  defaults are what a bare `docker compose up` outside mise gets, i.e. the pre-isolation
  behaviour, so nothing breaks for someone not using the tasks.
- Migration tooling reads the same variables and **hard-codes no database**. Drizzle's
  config throws when `DATABASE_URL` is unset rather than falling back to a literal; the JVM
  preset lets Spring Boot's docker-compose support derive the datasource from the container
  it started, so Liquibase follows with nothing extra configured.
- Integration tests use an **ephemeral Testcontainers database**, never the dev one, and live
  in a lane (`test:integration`) separate from the default `test` task, **which must stay
  runnable without Docker**.
- `db:guard` runs as a `depends` of `dev`, `test` and every migration task, and **passes** for
  a `db == none` project (there is nothing to guard) — a guard that fails there would break
  `mise run test` for every database-less scaffold.

**No new copier question.** The one knob, `WF_DB_BASE_PORT`, is a `.mise.local.toml`
override, documented in the generated README — not an answer. A persisted answer would replay
one machine's port choice into every future render on every machine, which is the same trap as
a copy-time date.

## `.claude/settings.json` — the project declares its plugin

Every scaffold's `.claude/settings.json` carries, alongside its `permissions.allow` list:

```json
{ "extraKnownMarketplaces": {
    "wellforge": { "source": { "source": "github", "repo": "matteocodogno/wellforge" } } },
  "enabledPlugins": { "wellforge@wellforge": true } }
```

This is the project half of the distribution story: the repo itself says which marketplace
and which plugin it expects, so a teammate cloning it does not have to be told out of band.
The key shapes are the observed ones — they are exactly what Claude Code writes into
`~/.claude/plugins/known_marketplaces.json` and `settings.json` for an already-installed
marketplace, not an invention of this contract.

**Two honest limits**, because the difference matters when it does not work:

1. **The version is not pinned here, on purpose.** `enabledPlugins` names a plugin, not a
   version, and pinning one in a *rendered* file would replay the scaffold-time version
   forever — the same trap as the `plugin` object above. The version a project expects lives
   in `.forge/manifest.json`, where `/wellforge:upgrade` can keep it current.
2. **Whether this installs the plugin, prompts for it, or only enables it once installed is
   not documented, and is therefore not claimed.** What it reliably does is *declare* the
   dependency where a human and `/wellforge:doctor` can both read it. If a teammate opens a
   generated project and the commands are missing, the install is two commands
   (`wellforge-plugin/README.md` § Install) and doctor names them.

## Versioning & lifecycle

> Why there are two tag series at all, and how each one reaches a project:
> [`docs/VERSIONING.md`](../../docs/VERSIONING.md). The rules below are the binding ones
> for template authors.

- Releases are **repo-wide git tags `vX.Y.Z`** (copier resolves "latest" from
  PEP440-parseable tags; per-template tags like `name/v1` would be invisible to it).
  Both presets release in lockstep; a release touching one preset is a no-op update
  for the other. `gates-v*` tags are a separate, non-template series.
- **Never tag a `gates-v*` and a `vX.Y.Z` on the same commit.** Copier ignores the
  non-PEP440 `gates-v*` for version resolution, but `git describe` can still record it
  as the scaffold's `_commit`, mislabeling the template version. When a release touches
  both gates and templates, put the `gates-v*` tag on the gates-only commit and the
  `vX.Y.Z` tag on a later (e.g. template-wiring or docs) commit — keep them one apart.
- **A template release does not carry a `gates_ref` bump.** `gates_ref` is a recorded
  answer, and `copier update --skip-answered` keeps recorded answers — verified E2E:
  v0.7.0 → v0.8.0 re-renders every workflow and still pins `@gates-v7`. Bumping the
  template default only affects NEW scaffolds. Existing projects move with
  `copier update --data gates_ref=<latest>`, which `/wellforge:upgrade` now offers as an
  explicit step. Keep the two series' currency separate in your head: `_commit` tracks
  the template, `gates_ref` tracks the gates.
- Semver discipline: patch = cosmetic, minor = additive, major = needs migration.
- The hidden `template_version` answer mirrors the release version (bump it in the
  release commit); the manifest's `version` field reads it.
- Mechanical migration steps go in root `copier.yml` `_migrations` (run by
  `copier update` at version boundaries); judgment calls belong to
  `/wellforge:upgrade`'s conflict resolution.

## Rules

- `--defaults` must always generate a working project (CI for templates relies on it).
- Only files needing substitution get the `.jinja` suffix.
- No `_tasks` that require network access; git init and dependency install are
  `/wellforge:new`'s job, not the template's.
- Conditional files use copier's `{% if %}` filename syntax or empty-content guards —
  a `ci: none` answer must not leave an empty `.github/` directory.
- Pinned versions (Spring Boot, Kotlin, Node, library versions) come from the stack
  skills (`springboot-scaffold`, `react-ts-vite`, `hono-ts-backend`, `mise`, `pulumi-gcp-ts`)
  — the skills are the source of truth; templates mirror them.
