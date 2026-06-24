# jOOQ Patterns Reference

All database access goes through jOOQ. Never use JPA, Hibernate, or Spring Data JPA repositories.

---

## DSLContext Injection

Always inject `DSLContext` via constructor (primary constructor, `val`):

```kotlin
@Repository
class UserRepository(private val dsl: DSLContext)
```

---

## Logger Declaration

Declare the logger **above** the class, not inside a companion object:

```kotlin
import io.github.oshai.kotlinlogging.KotlinLogging

private val logger = KotlinLogging.logger {}

@Repository
class UserRepository(private val dsl: DSLContext) { ... }
```

---

## Return Types

- All repository methods return `Result<T>` — never throw, never return raw values.
- Use `Result.catching { }` to wrap jOOQ calls; it catches `DataAccessException` automatically.
- Return `Result<T?>` when a record may not exist (single lookup).
- Return `Result<List<T>>` for collection queries (empty list is success).

---

## CRUD Patterns

### Find by ID (nullable)

```kotlin
fun findById(id: Long): Result<UserRecord?> =
    Result.catching {
        dsl.selectFrom(USERS)
           .where(USERS.ID.eq(id))
           .fetchOne()   // null if not found
    }
```

### Find by ID (domain error if missing)

```kotlin
fun getById(id: Long): Result<UserRecord> =
    findById(id).flatMap { record ->
        record?.let { Result.success(it) }
            ?: Result.failure(DomainError.NotFoundError("User $id not found"))
    }
```

### Find all with filter

```kotlin
fun findAllActive(): Result<List<UserRecord>> =
    Result.catching {
        dsl.selectFrom(USERS)
           .where(USERS.ACTIVE.isTrue)
           .orderBy(USERS.CREATED_AT.desc())
           .fetch()
           .toList()
    }
```

### Insert

```kotlin
fun insert(record: UserRecord): Result<UserRecord> =
    Result.catching {
        dsl.insertInto(USERS)
           .set(record)
           .returning()
           .fetchOne()!!
    }
```

### Update

```kotlin
fun update(record: UserRecord): Result<UserRecord> =
    Result.catching {
        dsl.update(USERS)
           .set(record)
           .where(USERS.ID.eq(record.id))
           .returning()
           .fetchOne()!!
    }
```

### Upsert (Postgres ON CONFLICT)

```kotlin
fun upsert(record: UserRecord): Result<UserRecord> =
    Result.catching {
        dsl.insertInto(USERS)
           .set(record)
           .onConflict(USERS.EMAIL)
           .doUpdate()
           .set(USERS.FULL_NAME, record.fullName)
           .returning()
           .fetchOne()!!
    }
```

### Delete

```kotlin
fun deleteById(id: Long): Result<Int> =
    Result.catching {
        dsl.deleteFrom(USERS)
           .where(USERS.ID.eq(id))
           .execute()
    }
```

---

## Transactions

Use `@Transactional` on service methods, not on repositories.  
jOOQ `DSLContext` participates in Spring transactions automatically.

```kotlin
@Service
class OrderService(
    private val orderRepo: OrderRepository,
    private val lineItemRepo: LineItemRepository,
) {
    @Transactional
    fun createOrder(command: CreateOrderCommand): Result<OrderDto> =
        orderRepo.insert(command.toRecord())
            .flatMap { order ->
                lineItemRepo.insertAll(command.items.map { it.toRecord(order.id!!) })
                    .map { order }
            }
            .map { it.toDto() }
}
```

---

## Mapping to Domain Objects

Never expose `Record` objects outside the module's `dal/` package.  
Map to DTOs or domain value objects before crossing the module boundary.

```kotlin
// dal/mapper/UserMapper.kt
fun UserRecord.toDto() = UserDto(
    id = id!!,
    email = email!!,
    fullName = fullName,
    active = active!!,
)

fun CreateUserCommand.toRecord() = UserRecord().apply {
    email = this@toRecord.email
    fullName = this@toRecord.fullName
    active = true
}
```

---

## Joins

```kotlin
fun findOrdersWithUser(userId: Long): Result<List<OrderWithUserRecord>> =
    Result.catching {
        dsl.select(
                ORDERS.ID,
                ORDERS.TOTAL,
                USERS.EMAIL,
                USERS.FULL_NAME,
            )
           .from(ORDERS)
           .join(USERS).on(ORDERS.USER_ID.eq(USERS.ID))
           .where(ORDERS.USER_ID.eq(userId))
           .fetch { record ->
               OrderWithUserRecord(
                   orderId = record[ORDERS.ID]!!,
                   total = record[ORDERS.TOTAL]!!,
                   userEmail = record[USERS.EMAIL]!!,
                   userName = record[USERS.FULL_NAME],
               )
           }
    }
```

---

## Pagination

```kotlin
fun findPaged(page: Int, size: Int): Result<List<UserRecord>> =
    Result.catching {
        dsl.selectFrom(USERS)
           .orderBy(USERS.CREATED_AT.desc())
           .limit(size)
           .offset(page * size)
           .fetch()
           .toList()
    }
```

---

## Batch Insert

```kotlin
fun insertAll(records: List<OrderLineRecord>): Result<Int> =
    Result.catching {
        dsl.batchInsert(records).execute().sum()
    }
```

---

## Generated Sources Location

jOOQ records are generated to `target/generated-sources/jooq/`.  
Import table references from the generated package:

```kotlin
import com.example.yourservice.dal.jooq.Tables.USERS
import com.example.yourservice.dal.jooq.tables.records.UserRecord
```

Always run `mvn generate-sources` after adding or changing Liquibase migrations  
to refresh the generated records before compiling.
