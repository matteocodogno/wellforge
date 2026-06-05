# spring-kotlin-react

Copier template for a welld full-stack monorepo:

- **Backend** — Spring Boot 4 + Kotlin, jOOQ + Liquibase, Spring Modulith, Result/DomainError
  error handling, kotlin-logging, Testcontainers. Mirrors the `springboot-scaffold` skill.
- **Frontend** — React + TypeScript + Vite, Mantine, TanStack Router/Query, Effect TS, ESLint +
  Prettier. Mirrors the `react-ts-vite` skill.
- **Tooling** — `mise` (Java/Node/Maven/pnpm pinned at root, per-service tasks), spec-driven
  workflow scaffolding, optional GitHub CI calling the reusable gate workflows.

## Usage

```bash
uvx copier copy --trust gh:matteocodogno/wellforge my-service \
  --data preset=spring-kotlin-react
```

(Always the repo root — one `copier.yml` serves all presets; see
`templates/_shared/CONTRACT.md`.)

Or via the plugin: `/welld-dev:new` fills the common questions automatically.

## Questions

| Question | Type | Default | Notes |
|---|---|---|---|
| `project_name` | str | `My Service` | human name |
| `project_slug` | str | derived | kebab-case dir + artifact name |
| `description` | str | — | one line |
| `ci` | choice | `github` | `github` / `none` |
| `gates_repo` | str | `matteocodogno/wellforge` | owner/repo hosting gate workflows |
| `gates_ref` | str | `gates-v0` | tag pinned in generated CI |
| `base_package` | str | `ch.welld.<slug>` | root Kotlin/Java package |
| `db` | choice | `postgres` | `postgres` / `none` |

## `db` modes

- **`postgres`** (default) — full data layer: `spring-boot-starter-jooq`,
  `spring-boot-starter-liquibase`, the PostgreSQL driver, jOOQ codegen, the Liquibase changelog
  tree, and `docker-compose.yml`.
- **`none`** — a web-only service. The pom omits all DB starters and the jOOQ codegen plugin; the
  Liquibase changelog tree, `application.yml` jOOQ block, and `docker-compose.yml` are not emitted.

Both modes generate a project that compiles. The pom and `application.yml` are Jinja-templated so
the `db` switch is handled inline rather than with two divergent files.

## Pinned versions

Versions are mirrored from the source skills (the skills are the source of truth):

- Spring Boot **4.0.0**, Kotlin **2.1.20**, Java **21**
- jOOQ **3.19.18** (explicit — BOM property renamed in SB4), Liquibase **4.29.2**
- Spring Modulith BOM **2.0.0**, Testcontainers BOM **1.20.4**
- kotlin-logging-jvm **7.0.3**, MockK **1.13.14**, Kotest **5.9.1**
- mise tools: `java = temurin-21`, `node = 22`, `maven = 3.9.9`, `pnpm = 10`

> SB4 note: `spring-boot-starter-web` was renamed to `spring-boot-starter-webmvc`.

## Known limitations

- No Maven wrapper (`mvnw`) is shipped — generating it needs Maven on PATH (network). The frontend
  has no `pnpm-lock.yaml`. Both are produced by `/welld-dev:new` (or `mise install`) post-generation.
- The reusable gate workflows (`quality-jvm.yml`, `quality-node.yml`) do not exist yet (Phase 5).
  Generated CI wires the calls anyway.
