# Spring Modulith Structure Reference

---

## Package Layout

```
src/main/java/ch/welld/<service>/
├── common/
│   └── package-info.java              ← @ApplicationModule(type = OPEN) — Java, required
└── <module>/
    └── package-info.java              ← @ApplicationModule — Java, required

src/main/kotlin/ch/welld/<service>/
├── Application.kt
├── common/
│   ├── model/
│   │   ├── Result.kt
│   │   └── DomainError.kt
│   ├── config/
│   │   └── CommonConfiguration.kt
│   └── web/
│       └── GlobalExceptionHandler.kt
└── <module>/
    ├── api/                           ← PUBLIC: named interface — other modules import from here
    │   ├── ModuleMetadata.kt          ← @PackageInfo @NamedInterface("api") — required
    │   ├── <Module>Api.kt             ← interface(s) exposed to other modules
    │   └── dto/
    │       ├── <Module>Dto.kt
    │       └── Create<Module>Command.kt
    ├── dal/                           ← PRIVATE: jOOQ repositories
    │   └── <Module>Repository.kt
    ├── services/                      ← PRIVATE: business logic
    │   └── <Module>Service.kt
    ├── presentation/                  ← PRIVATE: REST controllers + request/response models
    │   └── <Module>Controller.kt
    └── <Module>Configuration.kt
```

---

## Layer responsibilities

| Sub-package | Annotation | Contains | Visibility |
|---|---|---|---|
| `api/` | — | **Interfaces only** + their DTOs | **Public** — the only package other modules may import. Concrete classes never go here. |
| `dal/` | `@Repository` | jOOQ `DSLContext` queries | **Private** — never imported outside the module |
| `services/` | `@Service` | Business logic, `Result<T>` operations | **Private** — never imported outside the module |
| `presentation/` | `@RestController` | HTTP handlers, request/response models | **Private** — never imported outside the module |

> **Hard rule:** if a type needs to cross a module boundary, it must be an interface in `api/`. Concrete implementations always stay in `dal/`, `services/`, or `presentation/` and are never exported.

---

## Module Annotations

Kotlin has no package-level annotation support. Spring Modulith requires two different approaches
depending on what you are annotating:

| What | Where | How |
|---|---|---|
| Module root (`@ApplicationModule`) | `src/main/java/.../module/package-info.java` | Java file — only option |
| Named interface (`@NamedInterface`) in `api/` | `src/main/kotlin/.../module/api/ModuleMetadata.kt` | Kotlin class with `@PackageInfo` |

### 1. Module root — package-info.java (Java, one per module)

`@ApplicationModule` must be a Java `package-info.java`. There is no Kotlin equivalent.

```
src/main/java/ch/welld/<service>/common/package-info.java
src/main/java/ch/welld/<service>/session/package-info.java
src/main/java/ch/welld/<service>/game/package-info.java
... one per module
```

```java
// src/main/java/ch/welld/<service>/common/package-info.java
@ApplicationModule(type = ApplicationModule.Type.OPEN)
package ch.welld.<service>.common;

import org.springframework.modulith.ApplicationModule;
```

```java
// src/main/java/ch/welld/<service>/session/package-info.java
@ApplicationModule
package ch.welld.<service>.session;

import org.springframework.modulith.ApplicationModule;
```

### 2. api/ named interface — ModuleMetadata.kt (Kotlin)

Every `api/` sub-package must contain a `ModuleMetadata.kt` file that declares it as a
named interface. This is the Kotlin-idiomatic replacement for annotating `package-info.java`
with `@NamedInterface`. `@PackageInfo` tells Spring Modulith to treat this class as the
logical equivalent of `package-info.java` for the package it lives in.

```kotlin
// src/main/kotlin/ch/welld/<service>/session/api/ModuleMetadata.kt
package ch.welld.<service>.session.api

import org.springframework.modulith.NamedInterface
import org.springframework.modulith.PackageInfo

@PackageInfo
@NamedInterface("api")
class ModuleMetadata
```

This makes `session::api` the named interface that other modules reference in `allowedDependencies`.

### 3. Restricting module dependencies (optional but recommended)

Once named interfaces are declared, you can restrict which modules and named interfaces a module
may depend on:

```java
// src/main/java/ch/welld/<service>/game/package-info.java
@ApplicationModule(allowedDependencies = "session::api")
package ch.welld.<service>.game;

import org.springframework.modulith.ApplicationModule;
```

This makes Spring Modulith fail the `ModularityTest` if `game` ever imports from `session`
outside of `session.api`.

### 4. pom.xml — both src/main/java and src/main/kotlin must be in sourceDirs

```xml
<sourceDirs>
    <sourceDir>${project.basedir}/src/main/kotlin</sourceDir>
    <sourceDir>${project.basedir}/src/main/java</sourceDir>
    <sourceDir>${project.build.directory}/generated-sources/jooq</sourceDir>
</sourceDirs>
```

---

## Full module example — `session`

```
src/main/java/ch/welld/<service>/session/
└── package-info.java                  ← @ApplicationModule (Java)

src/main/kotlin/ch/welld/<service>/session/
├── api/
│   ├── ModuleMetadata.kt              ← @PackageInfo @NamedInterface("api")
│   ├── SessionApi.kt                  ← interface exposed to other modules
│   └── dto/
│       ├── SessionDto.kt
│       └── CreateSessionCommand.kt
├── dal/
│   └── SessionRepository.kt           ← jOOQ queries, owns game_sessions table
├── services/
│   └── SessionService.kt              ← implements SessionApi, returns Result<T>
├── presentation/
│   └── SessionController.kt           ← POST /sessions, POST /sessions/{id}/join
└── SessionConfiguration.kt
```

```kotlin
// session/api/ModuleMetadata.kt
package ch.welld.<service>.session.api

import org.springframework.modulith.NamedInterface
import org.springframework.modulith.PackageInfo

@PackageInfo
@NamedInterface("api")
class ModuleMetadata
```

```kotlin
// session/dal/SessionRepository.kt
private val logger = KotlinLogging.logger {}

@Repository
class SessionRepository(private val dsl: DSLContext) {

    fun findById(gameId: UUID): Result<GameSessionRecord?> =
        Result.catching {
            dsl.selectFrom(GAME_SESSIONS)
               .where(GAME_SESSIONS.GAME_ID.eq(gameId))
               .fetchOne()
        }

    fun save(record: GameSessionRecord): Result<GameSessionRecord> =
        Result.catching {
            dsl.insertInto(GAME_SESSIONS)
               .set(record)
               .returning()
               .fetchOne()!!
        }
}
```

```kotlin
// session/services/SessionService.kt
private val logger = KotlinLogging.logger {}

@Service
class SessionService(private val repo: SessionRepository) : SessionApi {

    override fun createSession(command: CreateSessionCommand): Result<SessionDto> =
        repo.save(command.toRecord())
            .map { it.toDto() }

    override fun getSession(gameId: UUID): Result<SessionDto> =
        repo.findById(gameId)
            .flatMap { record ->
                record?.let { Result.success(it.toDto()) }
                    ?: Result.failure(DomainError.NotFoundError("Session $gameId not found"))
            }
}
```

```kotlin
// session/presentation/SessionController.kt
@RestController
@RequestMapping("/api/sessions")
class SessionController(private val service: SessionService) {

    @PostMapping
    fun create(@RequestBody @Valid body: CreateSessionRequest): ResponseEntity<*> =
        service.createSession(body.toCommand()).fold(
            onSuccess = { ResponseEntity.status(201).body(it) },
            onFailure = { it.toResponse() }
        )

    @GetMapping("/{gameId}")
    fun get(@PathVariable gameId: UUID): ResponseEntity<*> =
        service.getSession(gameId).fold(
            onSuccess = { ResponseEntity.ok(it) },
            onFailure = { it.toResponse() }
        )
}
```

---

## Cross-Module Access Rules

### ✅ Allowed

```kotlin
// game/services/GameService.kt
// Allowed: injecting SessionApi — it lives in session/api/
@Service
class GameService(
    private val repo: InjectionAttemptRepository,   // own dal/ — OK
    private val sessionApi: SessionApi,              // other module's api/ — OK
)
```

```kotlin
// session/api/SessionApi.kt
// This interface lives in api/ — the ONLY reason it can be used by other modules.
// The implementation (SessionService) lives in session/services/ and is never exported.
interface SessionApi {
    fun createSession(command: CreateSessionCommand): Result<SessionDto>
    fun getSession(gameId: UUID): Result<SessionDto>
    fun isActive(gameId: UUID): Result<Boolean>
}
```

### ❌ Forbidden

```kotlin
// WRONG: dal/ is private — never import a repository from another module
@Service
class GameService(
    private val sessionRepo: SessionRepository,  // session/dal/ — NEVER
)

// WRONG: services/ is private — never import a service from another module
@Service
class GameService(
    private val sessionService: SessionService,  // session/services/ — NEVER
)

// WRONG: only session/api/ interfaces may be referenced cross-module
//        if SessionService is not in api/, it stays inside session/
val service: SessionService = ...   // NEVER — must use SessionApi instead

// WRONG: querying another module's table
dsl.selectFrom(GAME_SESSIONS).fetch()  // inside game module — GAME_SESSIONS owned by session
```

---

## Table Ownership

Each module owns its tables. No other module may query those tables with `DSLContext`.

| Module | Owns tables |
|---|---|
| `session` | `game_sessions` |
| `game` | `injection_attempts`, `system_prompt_versions` |
| `summary` | reads across tables via `session` and `game` APIs only |

---

## Module Boundary Test

```kotlin
// src/test/kotlin/ch/welld/<service>/ModularityTest.kt
class ModularityTest {

    private val modules = ApplicationModules.of(<ServiceName>Application::class.java)

    @Test
    fun `modules should not have illegal dependencies`() {
        modules.verify()
    }

    @Test
    fun `should write module documentation`() {
        Documenter(modules).writeDocumentation()
    }
}
```

Run this in CI. It fails fast if any `dal/`, `services/`, or `presentation/` type
is accessed from outside its module.

---

## Configuration per Module

```kotlin
// session/SessionConfiguration.kt
// No @ApplicationModule here — that lives in package-info.java
@Configuration
class SessionConfiguration {

    @Bean
    fun sessionService(repo: SessionRepository): SessionService =
        SessionService(repo)
}
```
