---
name: kotlin-springboot-welld
description: >
  Kotlin and Spring Boot development. Trigger this skill for ANY task involving Kotlin, Spring Boot,
  JVM, Maven, jOOQ, Liquibase, database migrations, REST APIs, or backend services. Covers welld-style
  best practices including functional error handling with Result/DomainError, Spring Modulith module
  boundaries, repository patterns, and Spring configuration. Use for writing code, reviewing code,
  setting up new services, defining migrations, configuring dependencies, scaffolding modules, or
  debugging Spring applications. Always trigger for partial tasks like "add a repository", "create
  a migration", "set up a new module", "add an endpoint", or "fix a Spring Boot issue".
---

# Spring Boot with Kotlin — welld Best Practices

Opinionated guide for welld Spring Boot / Kotlin projects.  
For deep reference on a specific area, read the matching file in `references/`:

| Topic | File |
|---|---|
| Maven POM, plugins & dependencies | `references/maven-setup.md` |
| jOOQ patterns & repository style | `references/jooq-patterns.md` |
| Liquibase migrations (dual-DBMS) | `references/liquibase-migrations.md` |
| Spring Modulith module structure | `references/modulith-structure.md` |
| Error handling (Result / DomainError) | `references/error-handling.md` |

---

## Core Principles

- **Maven only** — never Gradle.
- **jOOQ only** — never JPA/Hibernate. Use `spring-boot-starter-jooq`.
- **Liquibase** for all schema changes, SQL dialect, never XML changesets.
- **Postgres** in production; **H2** only for jOOQ code generation at build time.
- **Docker Compose** starter for local dev infrastructure.
- **Spring Modulith** for module boundaries; cross-module access only via API interfaces.
- **Pure functional style** — composition over inheritance, extract operations into named functions that return `Result<T>`, chain with `flatMap`/`map`, never use imperative `try-catch` or `if-else` for control flow.
- **Result\<T\>** for all fallible operations; **DomainError** for typed errors; **Result.catching** to wrap throwables.
- **kotlin-logging** (`KotlinLogging.logger {}`) declared **above** the class, not inside it.

---

## Project Setup (Quick Reference)

**Read `references/maven-setup.md`** for the complete POM skeleton including:
- Parent, properties, dependency management
- `jooq-codegen-maven` plugin wired to Liquibase + H2
- `kotlin-maven-plugin`, `liquibase-maven-plugin`, `spring-boot-maven-plugin`
- Docker Compose starter dependency

**Key versions to align:**

```xml
<properties>
    <kotlin.version>2.1.20</kotlin.version>
    <jooq.version>3.19.18</jooq.version>
    <liquibase.version>4.29.2</liquibase.version>
    <java.version>21</java.version>
</properties>
```

---

## Module Structure (Quick Reference)

**Read `references/modulith-structure.md`** for full package layout and `package-info.java` rules.

Each module is split into three sub-packages by layer:

```
src/main/kotlin/ch/welld/<service>/
├── Application.kt                  ← @SpringBootApplication
├── common/                         ← @ApplicationModule(open = true) via package-info.java
│   ├── model/Result.kt
│   ├── model/DomainError.kt
│   └── config/...
└── <module>/                       ← @ApplicationModule via package-info.java
    ├── api/                        ← PUBLIC: named interface — only package other modules import
    │   ├── ModuleMetadata.kt          ← @PackageInfo @NamedInterface("api") — always required
    │   ├── <Module>Api.kt
    │   └── dto/
    ├── dal/                        ← PRIVATE: jOOQ repositories only
    │   └── <Module>Repository.kt
    ├── services/                   ← PRIVATE: business logic
    │   └── <Module>Service.kt
    ├── presentation/               ← PRIVATE: REST controllers
    │   └── <Module>Controller.kt
    └── <Module>Configuration.kt
```

**Package responsibilities:**

| Sub-package | Contains | Access |
|---|---|---|
| `api/` | Interfaces + DTOs crossing module boundaries | Public — other modules may depend on this |
| `dal/` | jOOQ `@Repository` classes, `DSLContext` usage | Private — never imported outside this module |
| `services/` | `@Service` business logic, `Result<T>` operations | Private — never imported outside this module |
| `presentation/` | `@RestController`, request/response models | Private — never imported outside this module |

**Rules — enforced, no exceptions:**
- **Every interface intended for use by another module MUST live in `api/`.** If it is not in `api/`, it is private to this module and may never be imported elsewhere.
- **Every `api/` package MUST contain `ModuleMetadata.kt`** annotated with `@PackageInfo` and `@NamedInterface("api")`. Without it, Spring Modulith does not recognise `api/` as a named interface and the `ModularityTest` will not enforce its boundary.
- Modules access other modules **only** through their `api/` package — never through `dal/`, `services/`, or `presentation/`.
- `api/` contains **only** interfaces and their DTOs. No concrete classes, no `@Service`, no `@Repository`, no `@RestController`.
- Each module **owns its tables** — no cross-module `DSLContext` table access.
- `common` module is open to all; everything else is encapsulated.

**When creating a new module, always generate these files in this order:**
1. `src/main/java/.../module/package-info.java` — `@ApplicationModule`
2. `src/main/kotlin/.../module/api/ModuleMetadata.kt` — `@PackageInfo @NamedInterface("api")`
3. `src/main/kotlin/.../module/api/<Module>Api.kt` — the interface(s)
4. `src/main/kotlin/.../module/api/dto/` — DTOs used by the interface
5. `src/main/kotlin/.../module/services/<Module>Service.kt` — implementation of the interface
6. `src/main/kotlin/.../module/dal/<Module>Repository.kt` — jOOQ access
7. `src/main/kotlin/.../module/presentation/<Module>Controller.kt` — HTTP endpoints
8. `src/main/kotlin/.../module/<Module>Configuration.kt` — Spring `@Configuration`

---

## Database Layer (Quick Reference)

**Read `references/jooq-patterns.md`** and **`references/liquibase-migrations.md`**.

### Migrations — Dual DBMS Pattern

Some SQL is Postgres-specific (e.g., `TEXT`, `SERIAL`, `jsonb`, `ON CONFLICT`).  
When this happens, create **two** changesets:

```
db/changelog/
├── db.changelog-master.yaml
└── changes/
    ├── 001-create-users-postgres.sql   ← dbms: postgresql
    └── 001-create-users-h2.sql         ← dbms: h2  (jOOQ codegen only)
```

Each changeset header must declare `dbms`:

```sql
--liquibase formatted sql
--changeset author:001-create-users dbms:postgresql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE
);
```

### Repository Pattern (dal/ package)

```kotlin
// <module>/dal/UserRepository.kt
private val logger = KotlinLogging.logger {}

@Repository
class UserRepository(private val dsl: DSLContext) {

    fun findById(id: Long): Result<UserRecord?> =
        Result.catching {
            dsl.selectFrom(USERS)
               .where(USERS.ID.eq(id))
               .fetchOne()
        }

    fun save(record: UserRecord): Result<UserRecord> =
        Result.catching {
            dsl.insertInto(USERS)
               .set(record)
               .returning()
               .fetchOne()!!
        }
}
```

---

## Error Handling (Quick Reference)

**Read `references/error-handling.md`** for full `Result<T>` and `DomainError` usage.

### Pure Functional Style — REQUIRED

**All business logic MUST use monadic composition with `Result<T>`.** Never use imperative `try-catch`, `if-else`, or nullable chains. Extract reusable operations into pure functions that return `Result<T>`.

**Pattern: Extract → Compose → Handle**

```kotlin
// ✅ CORRECT — Pure functional style with Result composition
override fun doFilterInternal(
    request: HttpServletRequest,
    response: HttpServletResponse,
    filterChain: FilterChain,
) {
    extractToken(request)
        .flatMap { token -> authenticateToken(token, request) }
        .onSuccess { auth -> SecurityContextHolder.getContext().authentication = auth }
        .onFailure { error -> logger.debug { "JWT validation failed for ${request.requestURI}: ${error.message}" } }

    filterChain.doFilter(request, response)
}

private fun extractToken(request: HttpServletRequest): Result<String> =
    Result
        .success(Unit)
        .flatMap {
            request.cookies
                ?.firstOrNull { it.name == JWT_COOKIE_NAME }
                ?.value
                .takeIf { SecurityContextHolder.getContext().authentication == null }
                ?.let { token -> Result.success(token) }
                ?: Result.failure(DomainError.ValidationError("No valid token found"))
        }

private fun authenticateToken(
    token: String,
    request: HttpServletRequest,
): Result<UsernamePasswordAuthenticationToken> =
    Result
        .catching { jwtUtils.validateTokenAndGetEmail(token) }
        .flatMap { email -> Result.catching { userDetailsService.loadUserByUsername(email) } }
        .map { userDetails ->
            UsernamePasswordAuthenticationToken(userDetails, null, userDetails.authorities).apply {
                details = WebAuthenticationDetailsSource().buildDetails(request)
            }
        }
```

```kotlin
// ❌ WRONG — Imperative style with try-catch and if-else
override fun doFilterInternal(
    request: HttpServletRequest,
    response: HttpServletResponse,
    filterChain: FilterChain,
) {
    val token = request.cookies?.firstOrNull { it.name == JWT_COOKIE_NAME }?.value

    if (token != null && SecurityContextHolder.getContext().authentication == null) {
        try {
            val email = jwtUtils.validateTokenAndGetEmail(token)
            val userDetails = userDetailsService.loadUserByUsername(email)
            val auth = UsernamePasswordAuthenticationToken(userDetails, null, userDetails.authorities)
            auth.details = WebAuthenticationDetailsSource().buildDetails(request)
            SecurityContextHolder.getContext().authentication = auth
        } catch (ex: Exception) {
            logger.debug { "JWT validation failed: ${ex.message}" }
        }
    }

    filterChain.doFilter(request, response)
}
```

### Service Layer — Always Return Result

```kotlin
// services/ — always return Result
fun createUser(command: CreateUserCommand): Result<UserDto> =
    validate(command)
        .flatMap { repo.findByEmail(it.email) }
        .flatMap { existing ->
            if (existing != null)
                Result.failure(DomainError.ValidationError("Email already in use"))
            else
                repo.save(it.toRecord())
        }
        .map { it.toDto() }

// presentation/ — fold into HTTP response
fun create(@RequestBody @Valid body: CreateUserRequest): ResponseEntity<*> =
    service.createUser(body.toCommand()).fold(
        onSuccess = { ResponseEntity.ok(it) },
        onFailure = { err -> err.toResponse() }
    )
```

**Key principles:**
- **Extract operations into named functions** that return `Result<T>` — never inline complex logic
- **Chain operations with `flatMap`**, `map`, `onSuccess`, `onFailure` — never use `try-catch` or `if-else` for control flow
- **Use `Result.catching { }`** to wrap throwable operations — never bare `try-catch`
- **Always use `takeIf` / `takeUnless`** for conditional logic — never use `if` statements for control flow or validation
  ```kotlin
  // ✅ CORRECT
  user.takeIf { it.isActive }
      ?.let { Result.success(it) }
      ?: Result.failure(DomainError.ValidationError("User is not active"))

  // ❌ WRONG
  if (user.isActive) {
      Result.success(user)
  } else {
      Result.failure(DomainError.ValidationError("User is not active"))
  }
  ```

---

## Logging

Always declare the logger **above** the class declaration (not inside a companion object).

```kotlin
import io.github.oshai.kotlinlogging.KotlinLogging

private val logger = KotlinLogging.logger {}

@Service
class OrderService(...) {

    fun process(id: Long): Result<OrderDto> {
        logger.info { "Processing order $id" }
        // ...
    }
}
```

---

## Testing

- **JUnit 5** + **MockK** + **Kotest assertions**
- **Testcontainers** for integration tests (real Postgres)
- **@SpringModulithTest** to verify module boundaries
- Test slices: `@DataJooqTest` for repository tests in `dal/`
- Never test with H2 in integration tests — use Testcontainers

```kotlin
@SpringBootTest
@Testcontainers
class UserRepositoryTest {

    @Container
    val postgres = PostgreSQLContainer("postgres:16")

    @Test
    fun `should return NotFoundError when user does not exist`() {
        val result = repo.findById(-1L)
        result.isSuccess shouldBe true
        result.getOrNull() shouldBe null
    }
}
```

---

## Docker Compose Starter

Place `compose.yaml` in project root:

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: myservice
      POSTGRES_USER: myservice
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"
```

Spring Boot auto-starts Docker Compose on `./mvnw spring-boot:run` in dev profile.

---

## Code Comments

**CRITICAL: Comments are documentation. Never delete existing comments. Always preserve and update them.**

### Rules — Enforced, No Exceptions

1. **Never delete comments** — when modifying code, update comments to reflect changes; never remove them
2. **Always add comments for:**
   - Public API methods (`fun` in `api/` package) — explain purpose, parameters, return values
   - Complex business logic — explain **why**, not **what**
   - Non-obvious `Result` chains — explain the transformation pipeline
   - Configuration classes — explain each `@Bean` and its role
   - Repository methods with complex jOOQ queries — explain the query intent
3. **KDoc format** for public APIs:
   ```kotlin
   /**
    * Creates a new user account with the provided details.
    *
    * Validates email uniqueness before persisting. Returns ValidationError
    * if email is already registered.
    *
    * @param command User creation details including email and profile
    * @return Result containing UserDto on success, DomainError on failure
    */
   fun createUser(command: CreateUserCommand): Result<UserDto>
   ```
4. **Inline comments** for complex logic:
   ```kotlin
   // Extract token from cookie only if no authentication is already present
   // to avoid re-processing on subsequent filter invocations
   private fun extractToken(request: HttpServletRequest): Result<String> =
       Result.success(Unit)
           .flatMap {
               request.cookies
                   ?.firstOrNull { it.name == JWT_COOKIE_NAME }
                   ?.value
                   .takeIf { SecurityContextHolder.getContext().authentication == null }
                   ?.let { token -> Result.success(token) }
                   ?: Result.failure(DomainError.ValidationError("No valid token found"))
           }
   ```
5. **Update, never delete** — when code changes:
   ```kotlin
   // ✅ CORRECT — Comment updated to reflect new validation
   /**
    * Creates a new user account with the provided details.
    *
    * Validates email uniqueness and password strength before persisting.
    * Returns ValidationError if email is already registered or password
    * does not meet complexity requirements.
    *
    * @param command User creation details including email, password, and profile
    * @return Result containing UserDto on success, DomainError on failure
    */
   fun createUser(command: CreateUserCommand): Result<UserDto>

   // ❌ WRONG — Comment removed entirely
   fun createUser(command: CreateUserCommand): Result<UserDto>
   ```

### When to Comment

- **Always:** Public APIs, complex business rules, non-trivial `Result` chains
- **Often:** Repository queries, configuration beans, validation logic
- **Sometimes:** Simple CRUD operations (if the business context is not obvious)
- **Never:** Trivial getters/setters, obvious variable names, repetitive "this does X" comments

### AI Agent Responsibility

When modifying code:
1. **Read existing comments first** — understand the intent
2. **Update comments** to match code changes — keep them accurate
3. **Add comments** for new complex logic you introduce
4. **Never delete comments** — even if you refactor the code, preserve the knowledge

---

## Style Rules

- Use `val` everywhere possible; `var` only when mutation is unavoidable.
- Use **arrow functions** for single-expression functions.
- Prefer **data classes** for DTOs and value objects.
- No nullability (`?`) on domain model fields unless the absence has explicit business meaning.
- No `lateinit var` — use constructor injection.
- No `companion object` for logger — use top-level `private val`.
- No inheritance hierarchies — prefer interfaces + composition.
- Use `when` exhaustively on sealed classes (never `else` on `Result` or `DomainError`).
- **Always use `takeIf` / `takeUnless` / `let` / `run`** for conditional expressions — `if` statements are forbidden for control flow and validation.
