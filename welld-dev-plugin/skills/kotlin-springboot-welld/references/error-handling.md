# Error Handling Reference

All fallible operations return `Result<T>`. Never throw from service or repository methods.

---

## Core Classes

Both classes live in `common/model/` and are open to all modules.

### Result\<T\>

```
Result<T>
├── Success(value: T)
└── Failure(error: DomainError)
```

Key operations:
- `map { }` — transform a success value
- `flatMap { }` — chain operations that also return Result
- `mapError { }` — transform the error type
- `fold(onSuccess, onFailure)` — extract a value from either branch
- `onSuccess { }` / `onFailure { }` — side-effects, returns self
- `Result.catching { }` — wraps a block, catches DataAccessException & Exception
- `getOrNull()` — success value or null
- `getOrElse(default)` — success value or default

### DomainError

| Subclass | When to use |
|---|---|
| `DatabaseError` | Low-level DB failure (caught automatically by `Result.catching`) |
| `ValidationError` | Input or business rule violation |
| `NotFoundError` | Entity does not exist |
| `UnexpectedError` | Unclassified failure |
| `StateError` | Operation not valid in current state |

---

## Usage Patterns

### Repository — wrap with `Result.catching`

```kotlin
fun findById(id: Long): Result<UserRecord?> =
    Result.catching {
        dsl.selectFrom(USERS).where(USERS.ID.eq(id)).fetchOne()
    }
// DataAccessException → DomainError.DatabaseError automatically
```

### Service — chain with `flatMap` / `map`

```kotlin
fun createUser(command: CreateUserCommand): Result<UserDto> =
    validateEmail(command.email)                    // Result<String>
        .flatMap { email -> repo.findByEmail(email) }  // Result<UserRecord?>
        .flatMap { existing ->
            if (existing != null)
                Result.failure(DomainError.ValidationError("Email already in use"))
            else
                repo.insert(command.toRecord())    // Result<UserRecord>
        }
        .map { it.toDto() }                        // Result<UserDto>
```

### Service — produce a domain error when not found

```kotlin
fun getUser(id: Long): Result<UserDto> =
    repo.findById(id)
        .flatMap { record ->
            record?.let { Result.success(it.toDto()) }
                ?: Result.failure(DomainError.NotFoundError("User $id not found"))
        }
```

### Validation helper

```kotlin
private fun validateEmail(email: String): Result<String> =
    if (email.contains("@")) Result.success(email)
    else Result.failure(DomainError.ValidationError("Invalid email: $email"))
```

### Combining multiple Results

```kotlin
fun transfer(fromId: Long, toId: Long, amount: BigDecimal): Result<Unit> {
    val from = accountRepo.getById(fromId)
    val to   = accountRepo.getById(toId)

    return from.flatMap { fromAcc ->
        to.flatMap { toAcc ->
            if (fromAcc.balance < amount)
                Result.failure(DomainError.StateError("Insufficient funds"))
            else
                accountRepo.debit(fromAcc, amount)
                    .flatMap { accountRepo.credit(toAcc, amount) }
                    .map { }
        }
    }
}
```

### Logging failures without breaking the chain

```kotlin
fun processOrder(id: Long): Result<OrderDto> =
    orderRepo.getById(id)
        .onFailure { logger.warn { "Order $id not found: ${it.message}" } }
        .flatMap { orderService.process(it) }
        .onSuccess { logger.info { "Order $id processed" } }
```

---

## Controller Layer — fold to HTTP

Use `fold` to convert `Result<T>` into `ResponseEntity`:

```kotlin
@RestController
@RequestMapping("/users")
class UserController(private val service: UserApi) {

    @GetMapping("/{id}")
    fun get(@PathVariable id: Long): ResponseEntity<*> =
        service.getUser(id).fold(
            onSuccess = { ResponseEntity.ok(it) },
            onFailure = { it.toResponse() },
        )

    @PostMapping
    fun create(@RequestBody @Valid body: CreateUserRequest): ResponseEntity<*> =
        service.createUser(body.toCommand()).fold(
            onSuccess = { ResponseEntity.status(201).body(it) },
            onFailure = { it.toResponse() },
        )
}
```

---

## Global Exception Handler

Map `DomainError` → HTTP status in one place (in `common/web/`):

```kotlin
// common/web/GlobalExceptionHandler.kt
@ControllerAdvice
class GlobalExceptionHandler {

    @ExceptionHandler(NotFoundException::class)
    fun handleNotFound(ex: NotFoundException): ResponseEntity<ErrorResponse> =
        ResponseEntity.status(404).body(ErrorResponse(ex.message ?: "Not found"))

    @ExceptionHandler(ValidationException::class)
    fun handleValidation(ex: ValidationException): ResponseEntity<ErrorResponse> =
        ResponseEntity.status(400).body(ErrorResponse(ex.message ?: "Bad request"))

    @ExceptionHandler(DatabaseException::class)
    fun handleDatabase(ex: DatabaseException): ResponseEntity<ErrorResponse> {
        logger.error(ex) { "Database error" }
        return ResponseEntity.status(500).body(ErrorResponse("Internal error"))
    }

    @ExceptionHandler(Exception::class)
    fun handleUnexpected(ex: Exception): ResponseEntity<ErrorResponse> {
        logger.error(ex) { "Unexpected error" }
        return ResponseEntity.status(500).body(ErrorResponse("Internal error"))
    }
}

data class ErrorResponse(val message: String)
```

Extension for converting DomainError in controllers:

```kotlin
// common/web/DomainErrorExtensions.kt
fun DomainError.toResponse(): ResponseEntity<ErrorResponse> =
    when (this) {
        is DomainError.NotFoundError    -> ResponseEntity.status(404).body(ErrorResponse(message))
        is DomainError.ValidationError  -> ResponseEntity.status(400).body(ErrorResponse(message))
        is DomainError.StateError       -> ResponseEntity.status(409).body(ErrorResponse(message))
        is DomainError.DatabaseError    -> ResponseEntity.status(500).body(ErrorResponse("Internal error"))
        is DomainError.UnexpectedError  -> ResponseEntity.status(500).body(ErrorResponse("Internal error"))
    }
```

---

## Anti-Patterns to Avoid

```kotlin
// ❌ Throwing from a service
fun getUser(id: Long): UserDto {
    return repo.findById(id) ?: throw NotFoundException("User $id not found")
}

// ❌ Returning null instead of Result
fun getUser(id: Long): UserDto? = repo.findById(id)?.toDto()

// ❌ Catching inside a flatMap that already is inside Result.catching
Result.catching {
    Result.catching { /* double wrap — redundant */ }
}

// ❌ Using else on sealed classes — defeats exhaustive checking
when (result) {
    is Result.Success -> handle(result.value)
    else -> {}  // wrong — use is Result.Failure
}
```

---

## Result in Tests

```kotlin
@Test
fun `should return NotFoundError for unknown user`() {
    val result = service.getUser(-1L)

    result.isFailure shouldBe true
    val error = (result as Result.Failure).error
    error shouldBe instanceOf<DomainError.NotFoundError>()
    error.message shouldContain "-1"
}

@Test
fun `should return user dto on success`() {
    val result = service.getUser(existingUserId)

    result.isSuccess shouldBe true
    result.getOrNull()?.email shouldBe "test@welld.ch"
}
```
