# Templates

[Copier](https://copier.readthedocs.io) templates, one per stack preset. Semver-tagged via
git tags in this repo (`templates/<name>/vX.Y.Z`).

| Preset | Stack | Status |
|---|---|---|
| `spring-kotlin-react/` | Spring Boot 4 + Kotlin + jOOQ + Liquibase / React + TS + Vite | v0.1.0 |
| `hono-react/` | Hono + TS + Drizzle / React + TS + Vite | v0.1.0 |
| `_shared/CONTRACT.md` | the binding contract every template must satisfy (questions, required files, versioning) | active |

Generate from the **repo root** (one copier.yml serves all presets — required for
`copier update` to work):

```bash
uvx copier copy --trust <wellforge repo/URL> <dest> --data preset=<preset>
```

— or use `/welld-dev:new`, which interviews, recommends, generates, and verifies.
Upgrades: `/welld-dev:upgrade` in a generated project (releases = repo-wide `vX.Y.Z` tags).

## Contract

Every template MUST emit:

- `.forge/manifest.json` — `{ template, version, answers }`, the upgrade contract
- `.copier-answers.yml` — Copier's own update record
- a project-local `CLAUDE.md` + `.claude/settings.json` pre-wired for the welld-dev plugin
- CI workflows that **call** `gates/workflows/` (pinned tag), never copy them

Hard rule: max 2 presets until Phase 7 (pilot) proves the model.
