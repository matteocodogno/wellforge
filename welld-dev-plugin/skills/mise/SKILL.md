---
name: mise
description: >
  mise (dev tools version manager) expert for welld monorepos. Use this skill whenever the user
  asks to set up mise, add tools to mise, create or edit a mise.toml, define mise tasks, manage
  Java/Node/pnpm/Maven versions, or replace npm scripts / Makefile with mise tasks. Also trigger
  for phrases like "pin the node version", "add a task for", "run with mise", "how do I manage
  tool versions", "set up dev environment", or any question about .mise.toml configuration.
  Always use this skill proactively when scaffolding new projects or services — every welld project
  should have a mise.toml.
---

# mise — Dev Tools Version Manager

Authoritative reference for configuring mise in welld Spring Boot Kotlin + React TypeScript
monorepos. See `references/` for deep dives on specific areas.

---

## Pinned tool versions for welld projects

These versions are verified to work together. Use them verbatim unless the user specifies otherwise.

```toml
[tools]
java    = "temurin-21"
node    = "22"
maven   = "3.9.9"        # via mise-plugins/mise-maven
pnpm    = "10"
```

**Why temurin, not openjdk?**  
`temurin` (Eclipse Adoptium) sets `JAVA_HOME` correctly and integrates with IntelliJ auto-detection.
`openjdk` from mise does not set `JAVA_HOME` by default on macOS.

**Maven plugin** — must be installed first:
```bash
mise plugin install maven https://github.com/mise-plugins/mise-maven
```

---

## Monorepo layout — one mise.toml per service, root for shared tools

```
project/
├── mise.toml            ← shared tools (java, node, maven, pnpm) + root tasks
├── backend/
│   └── mise.toml        ← backend-specific tasks (compile, test, run)
└── frontend/
    └── mise.toml        ← frontend-specific tasks (dev, build, lint, e2e)
```

mise walks up the directory tree and merges configurations hierarchically — the root `mise.toml` sets the tool versions used everywhere; service-level files add tasks without re-declaring tools.

---

## Root mise.toml template

```toml
# mise.toml — project root
# Requires: mise plugin install maven https://github.com/mise-plugins/mise-maven

[tools]
java  = "temurin-21"
node  = "22"
maven = "3.9.9"
pnpm  = "10"

[env]
# JAVA_HOME is set automatically by mise when using temurin
# Add project-level env vars here (non-sensitive only — secrets go in .mise.local.toml)
# _.file = ".env"   ← uncomment to load .env automatically

[settings]
experimental = true    # required for monorepo task features

[tasks.install]
description = "Install all dependencies (backend + frontend)"
depends     = ["backend:install", "frontend:install"]

[tasks.build]
description = "Build all services"
depends     = ["backend:build", "frontend:build"]

[tasks.test]
description = "Test all services"
depends     = ["backend:test", "frontend:test"]

[tasks.lint]
description = "Lint all services"
depends     = ["backend:lint", "frontend:lint"]

[tasks.dev]
description = "Start all services in development mode"
depends     = ["backend:dev", "frontend:dev"]
```

---

## backend/mise.toml template

```toml
# backend/mise.toml
# Tools are inherited from root — do not redeclare them here

[tasks.install]
description = "Resolve Maven dependencies"
run         = "./mvnw dependency:resolve -q"
sources     = ["pom.xml"]

[tasks.build]
description = "Compile the backend"
depends     = ["install"]
run         = "./mvnw clean compile -q --no-transfer-progress"
sources     = ["pom.xml", "src/**/*.kt"]
outputs     = ["target/classes/**/*"]

[tasks.test]
description = "Run backend tests"
depends     = ["build"]
run         = "./mvnw test -q --no-transfer-progress"
sources     = ["src/**/*.kt"]

[tasks.run]
description = "Start the Spring Boot service (Docker Compose starts automatically)"
run         = "./mvnw spring-boot:run"

[tasks.lint]
description = "Run ktlint check"
run         = "./mvnw ktlintCheck -q"
sources     = ["src/**/*.kt"]

[tasks."lint:fix"]
description = "Run ktlint format"
run         = "./mvnw ktlintFormat -q"
sources     = ["src/**/*.kt"]

[tasks.generate]
description = "Generate jOOQ sources from Liquibase"
run         = "./mvnw generate-sources -q --no-transfer-progress"
sources     = ["src/main/resources/db/changelog/**/*.sql"]
outputs     = ["target/generated-sources/jooq/**/*"]
```

---

## frontend/mise.toml template

```toml
# frontend/mise.toml
# Tools are inherited from root — do not redeclare them here

[tasks.install]
description = "Install frontend dependencies"
run         = "pnpm install --frozen-lockfile"
sources     = ["package.json", "pnpm-lock.yaml"]
outputs     = ["node_modules/.modules.yaml"]

[tasks.dev]
description = "Start Vite dev server"
depends     = ["install"]
run         = "pnpm dev"

[tasks.build]
description = "Production build"
depends     = ["install", "lint"]
run         = "pnpm build"
sources     = ["src/**/*.{ts,tsx}", "index.html", "vite.config.ts"]
outputs     = ["dist/**/*"]

[tasks.lint]
description = "ESLint check"
run         = "pnpm exec eslint src --max-warnings 0"
sources     = ["src/**/*.{ts,tsx}"]

[tasks."lint:fix"]
description = "ESLint fix"
run         = "pnpm exec eslint src --fix"

[tasks.format]
description = "Prettier format"
run         = "pnpm exec prettier --write src"

[tasks."format:check"]
description = "Prettier check"
run         = "pnpm exec prettier --check src"

[tasks.test]
description = "Run Vitest unit tests"
depends     = ["install"]
run         = "pnpm test --run"

[tasks.e2e]
description = "Run Playwright E2E tests"
depends     = ["build"]
run         = "pnpm e2e"
```

---

## Key CLI commands

```bash
# First-time setup
mise plugin install maven https://github.com/mise-plugins/mise-maven
mise install                    # install all pinned tools
mise trust                      # trust .mise.toml (required once per project)

# Running tasks
mise run dev                    # start everything
mise run backend:build          # single service
mise run test                   # all tests in parallel
mise run build --jobs 2         # limit parallelism

# Version management
mise use java@temurin-21        # pin in current .mise.toml
mise use --global node@22       # pin globally
mise ls                         # show active versions
mise ls --current               # show only currently active

# Environment
mise env                        # show all env vars mise would set
mise exec -- mvn --version      # run command with mise environment (scripts/CI)
```

---

## .gitignore additions

```gitignore
# mise local overrides — never commit
.mise.local.toml
.mise.*.local.toml
```

---

## .mise.local.toml — machine-local secrets and overrides

```toml
# .mise.local.toml — gitignored, never committed
[env]
OPENAI_API_KEY   = "sk-..."
DATABASE_URL     = "postgresql://localhost/mydb_local"
```

Use `_.file = ".env"` in the main `mise.toml` only for non-sensitive defaults.
Secrets always go in `.mise.local.toml` or a gitignored `.env.local`.

---

## Updating the session-start hook

The `session-start.sh` hook in the welld-dev plugin injects context at session start.
When mise is set up in a project, it should also verify tool versions:

```bash
# Add to session-start.sh after the monorepo services block:
echo "## mise tool versions"
if command -v mise &>/dev/null && [ -f "$PROJECT_DIR/mise.toml" ]; then
  mise ls --current 2>/dev/null | awk '{print "- " $1 " " $2}'
else
  echo "(mise not configured)"
fi
```

---

## Common mistakes to avoid

| Mistake | Correct approach |
|---|---|
| Redeclaring `[tools]` in service-level mise.toml | Only declare tools at root — services inherit |
| Using `java = "openjdk-21"` | Use `java = "temurin-21"` for proper `JAVA_HOME` |
| Hardcoding secrets in mise.toml | Use `.mise.local.toml` (gitignored) |
| Running `mvnw` without `mise exec` in CI | Use `mise exec -- ./mvnw ...` in CI pipelines |
| Defining tasks with duplicate tool version pins | Tool version pinning belongs in `[tools]`, not per-task |
| Forgetting `mise trust` after cloning | Always run `mise trust` on first clone |
