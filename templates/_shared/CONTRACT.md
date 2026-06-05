# Template contract

Every WellForge Copier template MUST satisfy this contract. `/welld-dev:new` and
`/welld-dev:upgrade` depend on it; CI gate wiring and the Phase 6 lifecycle break if a
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
- Common questions (every preset, same names — `/welld-dev:new` fills them):

| Question | Type | Notes |
|---|---|---|
| `project_name` | str | human name, e.g. "Order Service" |
| `project_slug` | str | default derived from project_name (kebab-case); dir + artifact name |
| `description` | str | one line |
| `ci` | choice | `github` (default) / `none` |
| `gates_repo` | str | default `matteocodogno/wellforge` — owner/repo hosting the reusable gate workflows |
| `gates_ref` | str | default `gates-v0` — tag pinned in generated CI |

No "generated date" question/field: hidden (`when: false`) answers are not persisted to
`.copier-answers.yml`, so copy-time injected values diverge from the re-rendered base on
`copier update` and cause spurious conflicts. Generation date lives in git history.

Stack-specific questions (base_package, db, auth, …) are free per template but must have
sensible defaults so `copier copy --defaults` always produces a valid project.

## Required generated files

| File | Requirement |
|---|---|
| `.forge/manifest.json` | `{ "template": "<name>", "version": "<template version>", "answers": { …all answers… } }` — the upgrade contract |
| `.copier-answers.yml` | standard copier answers file (`{{ _copier_answers\|to_nice_yaml }}`) — enables `copier update` |
| `AGENTS.md` | project context (canonical, cross-tool standard): stack + versions, dev commands (mise tasks), architecture pointers, spec-driven workflow note (`specs/` + plugin commands) |
| `CLAUDE.md` | one-line `@AGENTS.md` import for Claude Code — content lives in AGENTS.md only |
| `.claude/settings.json` | pre-wired permissions for the stack's routine commands (mise/pnpm/mvnw test-build-lint) |
| `specs/README.md` | one-paragraph pointer to the spec-driven workflow |
| `mise.toml` (+ per-service) | per the `mise` skill: tools pinned at root, tasks per service, `install/build/test/lint/dev` aggregates at root |
| `.github/workflows/quality.yml` | when `ci == github`: **calls** `{{ gates_repo }}/.github/workflows/quality-<stack>.yml@{{ gates_ref }}` — never inlines gate logic |
| `.gitignore` | stack-appropriate + `.mise.local.toml`, `.claude/settings.local.json` |
| `README.md` | quickstart: `mise install && mise run dev`, layout table, link to CLAUDE.md |

## Versioning & lifecycle

- Releases are **repo-wide git tags `vX.Y.Z`** (copier resolves "latest" from
  PEP440-parseable tags; per-template tags like `name/v1` would be invisible to it).
  Both presets release in lockstep; a release touching one preset is a no-op update
  for the other. `gates-v*` tags are a separate, non-template series.
- Semver discipline: patch = cosmetic, minor = additive, major = needs migration.
- The hidden `template_version` answer mirrors the release version (bump it in the
  release commit); the manifest's `version` field reads it.
- Mechanical migration steps go in root `copier.yml` `_migrations` (run by
  `copier update` at version boundaries); judgment calls belong to
  `/welld-dev:upgrade`'s conflict resolution.

## Rules

- `--defaults` must always generate a working project (CI for templates relies on it).
- Only files needing substitution get the `.jinja` suffix.
- No `_tasks` that require network access; git init and dependency install are
  `/welld-dev:new`'s job, not the template's.
- Conditional files use copier's `{% if %}` filename syntax or empty-content guards —
  a `ci: none` answer must not leave an empty `.github/` directory.
- Pinned versions (Spring Boot, Kotlin, Node, library versions) come from the stack
  skills (`springboot-scaffold`, `react-ts-vite`, `hono-ts-backend`, `mise`) — the skills
  are the source of truth; templates mirror them.
