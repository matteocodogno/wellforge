---
name: springboot-scaffold
description: >
  Scaffold a new WellForge Spring Boot Kotlin service from scratch — the **JVM backend path**. Use
  when the user wants a new **Spring Boot / Kotlin / JVM** service specifically, OR when the project
  is already a JVM/Maven codebase. Trigger phrases: "new Spring Boot service", "new Kotlin/JVM
  microservice", "scaffold a JVM/Spring backend", "new spring boot app". FIRST confirm the target
  stack — for a **TypeScript / Hono** service use the `hono-ts-backend` skill instead; this skill is
  JVM-only and must NOT scaffold Spring into a TypeScript codebase. Asks for artifactId + service
  name, then generates the complete project (Maven, jOOQ, Liquibase, Spring Modulith, Docker Compose,
  Result/DomainError, kotlin-logging) — all pre-wired.
---

# Spring Boot Scaffold Skill

Generates a complete WellForge Spring Boot Kotlin project.  
Only two inputs needed: `artifactId` and `serviceName`.

---

## Stage 0 — confirm the stack (this skill is Spring Boot Kotlin / JVM ONLY)

Before scaffolding, confirm the target is genuinely a **JVM / Spring Boot / Kotlin** service —
don't assume Spring just because someone said "new service":

- **Brownfield (the project already has code):** detect the existing stack from `AGENTS.md`,
  `.forge/adoption.json`, and build files — `pom.xml`/`build.gradle(.kts)` ⇒ JVM;
  `package.json`/`pnpm-lock.yaml` ⇒ TypeScript/Node. A new service should **match the project's
  stack**. If the project is TS/Node, **STOP and use the `hono-ts-backend` skill instead** — never
  scaffold Spring into a TypeScript codebase.
- **Ambiguous / greenfield:** ask which backend the user wants, and offer **both** options
  (Spring-Kotlin *and* Hono-TS) — not Spring alone. Only continue here if they pick JVM/Spring.

Only proceed below when the target is confirmed JVM/Spring.

---

## Pinned dependency versions (do not deviate — verified to compile together)

| Component | Version |
|---|---|
| Spring Boot | **4.0.0** |
| Kotlin | **2.1.20** |
| Spring AI BOM | **1.0.0** |
| Spring Modulith BOM | **2.0.0** |
| jOOQ | **3.19.18** (explicit — do not rely on BOM property) |
| Liquibase | **4.29.2** |
| Testcontainers BOM | **1.20.4** |
| kotlin-logging-jvm | **7.0.3** |
| MockK | **1.13.14** |
| Kotest | **5.9.1** |
| Java | **21** |

## Spring Boot 4 naming changes (critical — these break compilation if wrong)

| Spring Boot 3 name | Spring Boot 4 name |
|---|---|
| `spring-boot-starter-web` | `spring-boot-starter-webmvc` |
| `spring-boot-starter-oauth2-client` | unchanged |
| Spring Modulith BOM | `2.0.0` (not `1.x`) |

**Always use `spring-boot-starter-webmvc` — never `spring-boot-starter-web` in SB4 projects.**

---

## Step 1 — Collect Inputs

Ask the user exactly these two things (nothing more):

1. **`artifactId`** — the Maven artifact ID (e.g. `order-service`, `user-api`). Also used as the directory name.
2. **`serviceName`** — the Kotlin package leaf and Spring app class name (e.g. `order`, `user`). Should be a single lowercase word. Derives:
   - base package: `com.example.<serviceName>`
   - app class: `<ServiceName>Application`
   - jOOQ target package: `com.example.<serviceName>.dal.jooq`

---

## Step 2 — Derive Variables

From the two inputs, compute:

```
artifactId      → e.g. "order-service"
serviceName     → e.g. "order"
ServiceName     → serviceName.replaceFirstChar { it.uppercase() }   → "Order"
basePackage     → "com.example.$serviceName"                        → "com.example.order"
packagePath     → basePackage.replace('.', '/')                      → "com/example/order"
jooqPackage     → "$basePackage.dal.jooq"
```

---

## Step 3 — Run the Scaffold Script

Run `scripts/scaffold.sh` passing the four derived variables:

```bash
bash scripts/scaffold.sh "<artifactId>" "<serviceName>" "<ServiceName>" "<basePackage>"
```

The script creates the full project directory tree at `./<artifactId>/`.

**Prerequisite:** Maven must be available on PATH (`mvn -version`). The script calls
`mvn wrapper:wrapper` at the end to generate `mvnw`. If Maven is not installed,
instruct the user to install it first (`brew install maven` on macOS).

---

## Step 4 — Post-scaffold verification (mandatory — do not skip)

After the script exits, Claude MUST run these commands in order and fix any errors
before declaring the scaffold complete:

```bash
cd <artifactId>

# 1. Verify wrapper was generated
[ -f mvnw ] || { echo "ERROR: mvnw missing"; exit 1; }

# 2. Resolve all dependencies (catches version conflicts)
./mvnw dependency:resolve -q 2>&1 | grep -E "^ERROR|Cannot access|Could not resolve" | head -20

# 3. Compile (catches starter renames, missing dependencies, Kotlin config issues)
./mvnw clean compile -q --no-transfer-progress

# 4. Run tests (catches wiring issues)
./mvnw test -q --no-transfer-progress
```

If **any step fails**, Claude must:
1. Read the full error output
2. Fix the root cause (wrong artifact name, version conflict, missing property)
3. Re-run from the failing step
4. Only report completion after all four steps pass green

**Do not skip verification. Do not report completion if compilation fails.**

---

## Step 5 — Present Output

After all verification steps pass:
- Use `present_files` to deliver the output zip.
- Tell the user:
  1. Run `./mvnw generate-sources` once before opening in the IDE (generates jOOQ records).
  2. Start the service with `./mvnw spring-boot:run` (Docker Compose starts automatically).
  3. Add modules under `src/main/kotlin/<packagePath>/` following the Modulith pattern.
