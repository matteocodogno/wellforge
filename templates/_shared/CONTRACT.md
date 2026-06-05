# Template contract

Every WellForge Copier template MUST satisfy this contract. `/welld-dev:new` and
`/welld-dev:upgrade` depend on it; CI gate wiring and the Phase 6 lifecycle break if a
template drifts from it.

## Copier configuration (`copier.yml`)

- `_subdirectory: template` — template files live under `template/`, keeping copier.yml
  and docs out of generated output.
- `_min_copier_version: "9.0.0"`.
- Common questions (every template, same names — `/welld-dev:new` fills them):

| Question | Type | Notes |
|---|---|---|
| `project_name` | str | human name, e.g. "Order Service" |
| `project_slug` | str | default derived from project_name (kebab-case); dir + artifact name |
| `description` | str | one line |
| `ci` | choice | `github` (default) / `none` |
| `gates_repo` | str | default `welld/wellforge` — owner/repo hosting the reusable gate workflows |
| `gates_ref` | str | default `gates-v0` — tag pinned in generated CI |
| `generated` | str | hidden (`when: false`), default `"unknown"` — generation date; `/welld-dev:new` passes `--data generated=$(date +%F)` (copier's Jinja has no now()) |

Stack-specific questions (base_package, db, auth, …) are free per template but must have
sensible defaults so `copier copy --defaults` always produces a valid project.

## Required generated files

| File | Requirement |
|---|---|
| `.forge/manifest.json` | `{ "template": "<name>", "version": "<template version>", "generated": "<date>", "answers": { …all answers… } }` — the upgrade contract |
| `.copier-answers.yml` | standard copier answers file (`{{ _copier_answers\|to_nice_yaml }}`) — enables `copier update` |
| `CLAUDE.md` | project context: stack + versions, dev commands (mise tasks), architecture pointers, spec-driven workflow note (`specs/` + plugin commands) |
| `.claude/settings.json` | pre-wired permissions for the stack's routine commands (mise/pnpm/mvnw test-build-lint) |
| `specs/README.md` | one-paragraph pointer to the spec-driven workflow |
| `mise.toml` (+ per-service) | per the `mise` skill: tools pinned at root, tasks per service, `install/build/test/lint/dev` aggregates at root |
| `.github/workflows/quality.yml` | when `ci == github`: **calls** `{{ gates_repo }}/.github/workflows/quality-<stack>.yml@{{ gates_ref }}` — never inlines gate logic |
| `.gitignore` | stack-appropriate + `.mise.local.toml`, `.claude/settings.local.json` |
| `README.md` | quickstart: `mise install && mise run dev`, layout table, link to CLAUDE.md |

## Versioning

- Template version lives in `copier.yml` as a hidden question with a literal default:
  `template_version: { type: str, default: "0.1.0", when: false }` — bumped on every
  template release and git-tagged `<template-name>/v<version>`.
- The manifest's `version` field reads this answer.

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
