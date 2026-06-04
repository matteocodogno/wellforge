# Validation & Error Handling — Hono + TypeScript

Complete patterns for schema validation with Zod and functional error handling with Effect TS.

---

## Schema-First Validation with Zod

### Basic Schemas

```typescript
import { z } from 'zod'

// Simple object schema
export const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string().min(2).max(100),
  role: z.enum(['user', 'admin']),
  isActive: z.boolean(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
})

// Infer TypeScript type
export type User = z.infer<typeof UserSchema>

// Create/update schemas (subset of full schema)
export const CreateUserSchema = UserSchema.pick({
  email: true,
  name: true,
  role: true,
}).extend({
  password: z.string().min(8),
})

export type CreateUserInput = z.infer<typeof CreateUserSchema>

export const UpdateUserSchema = UserSchema.pick({
  name: true,
  email: true,
}).partial()

export type UpdateUserInput = z.infer<typeof UpdateUserSchema>
```

### Advanced Validation Rules

```typescript
// Email validation with custom error
export const EmailSchema = z
  .string()
  .email('Invalid email format')
  .transform(email => email.toLowerCase())

// Password with complexity requirements
export const PasswordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters')
  .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
  .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
  .regex(/[0-9]/, 'Password must contain at least one number')
  .regex(/[^A-Za-z0-9]/, 'Password must contain at least one special character')

// URL validation
export const UrlSchema = z.string().url().startsWith('https://')

// Date validation
export const DateRangeSchema = z
  .object({
    startDate: z.coerce.date(),
    endDate: z.coerce.date(),
  })
  .refine(data => data.endDate > data.startDate, {
    message: 'End date must be after start date',
    path: ['endDate'],
  })

// Enum with fallback
export const RoleSchema = z.enum(['user', 'admin', 'moderator']).default('user')

// Array with length constraints
export const TagsSchema = z
  .array(z.string().min(1).max(50))
  .min(1, 'At least one tag required')
  .max(10, 'Maximum 10 tags allowed')

// Nested object validation
export const AddressSchema = z.object({
  street: z.string().min(1),
  city: z.string().min(1),
  postalCode: z.string().regex(/^\d{5}(-\d{4})?$/),
  country: z.string().length(2), // ISO 3166-1 alpha-2
})

export const UserWithAddressSchema = UserSchema.extend({
  address: AddressSchema.optional(),
})
```

### Discriminated Unions

```typescript
// Payment method schemas
const CreditCardSchema = z.object({
  type: z.literal('credit_card'),
  cardNumber: z.string().regex(/^\d{16}$/),
  expiryMonth: z.number().int().min(1).max(12),
  expiryYear: z.number().int().min(new Date().getFullYear()),
  cvv: z.string().regex(/^\d{3,4}$/),
})

const PayPalSchema = z.object({
  type: z.literal('paypal'),
  email: z.string().email(),
})

const BankTransferSchema = z.object({
  type: z.literal('bank_transfer'),
  iban: z.string().regex(/^[A-Z]{2}\d{2}[A-Z0-9]+$/),
  swift: z.string().regex(/^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$/),
})

export const PaymentMethodSchema = z.discriminatedUnion('type', [
  CreditCardSchema,
  PayPalSchema,
  BankTransferSchema,
])

export type PaymentMethod = z.infer<typeof PaymentMethodSchema>

// Usage in validation
const validatePayment = (input: unknown): PaymentMethod => {
  return PaymentMethodSchema.parse(input)
}
```

### Conditional Validation

```typescript
export const CreateOrderSchema = z
  .object({
    items: z.array(z.object({
      productId: z.string().uuid(),
      quantity: z.number().int().positive(),
    })).min(1),
    shippingMethod: z.enum(['standard', 'express', 'overnight']),
    shippingAddress: AddressSchema.optional(),
    billingAddress: AddressSchema.optional(),
    sameAsBilling: z.boolean().optional(),
  })
  .refine(
    data => {
      // If sameAsBilling is false, shippingAddress must be provided
      if (data.sameAsBilling === false && !data.shippingAddress) {
        return false
      }
      return true
    },
    {
      message: 'Shipping address is required when different from billing',
      path: ['shippingAddress'],
    }
  )
```

### Transform and Preprocess

```typescript
// Trim and normalize strings
export const TrimmedStringSchema = z.string().transform(s => s.trim())

// Parse JSON string
export const JsonSchema = z.string().transform((str, ctx) => {
  try {
    return JSON.parse(str)
  } catch {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Invalid JSON',
    })
    return z.NEVER
  }
})

// Coerce and validate
export const PositiveIntSchema = z.coerce.number().int().positive()

// Preprocess to handle multiple formats
export const FlexibleDateSchema = z.preprocess(arg => {
  if (typeof arg === 'string' || typeof arg === 'number') {
    return new Date(arg)
  }
  return arg
}, z.date())
```

---

## Error Types with Effect TS

Define typed errors using `Data.TaggedError`:

```typescript
import { Data } from 'effect'

// Base error types
export class NotFoundError extends Data.TaggedError('NotFoundError')<{
  resource: string
  id: string
}> {}

export class ValidationError extends Data.TaggedError('ValidationError')<{
  message: string
  field?: string
  issues?: Array<{ path: string[]; message: string }>
}> {}

export class DuplicateError extends Data.TaggedError('DuplicateError')<{
  resource: string
  field: string
  value: string
}> {}

export class UnauthorizedError extends Data.TaggedError('UnauthorizedError')<{
  message: string
}> {}

export class ForbiddenError extends Data.TaggedError('ForbiddenError')<{
  message: string
  requiredRole?: string
}> {}

export class DatabaseError extends Data.TaggedError('DatabaseError')<{
  message: string
  cause?: unknown
}> {}

export class ExternalServiceError extends Data.TaggedError('ExternalServiceError')<{
  service: string
  message: string
  statusCode?: number
}> {}

export class RateLimitError extends Data.TaggedError('RateLimitError')<{
  retryAfter: number
}> {}
```

---

## Using Effect for Error Handling

### Basic Pattern

```typescript
import { Effect } from 'effect'

// Function that may fail
const findUserById = (id: string): Effect.Effect<User, NotFoundError | DatabaseError> => {
  return Effect.tryPromise({
    try: () => db.query.users.findFirst({ where: eq(users.id, id) }),
    catch: error => new DatabaseError({ message: 'Query failed', cause: error }),
  }).pipe(
    Effect.flatMap(user =>
      user
        ? Effect.succeed(user)
        : Effect.fail(new NotFoundError({ resource: 'User', id }))
    )
  )
}
```

### Composing Effects

```typescript
import { Effect } from 'effect'

const createUser = (
  input: CreateUserInput
): Effect.Effect<User, ValidationError | DuplicateError | DatabaseError> => {
  return Effect.gen(function* (_) {
    // Check if email exists
    const existingUser = yield* _(findUserByEmail(input.email))

    if (existingUser) {
      return yield* _(
        Effect.fail(
          new DuplicateError({
            resource: 'User',
            field: 'email',
            value: input.email,
          })
        )
      )
    }

    // Hash password
    const passwordHash = yield* _(hashPassword(input.password))

    // Create user
    const user = yield* _(
      Effect.tryPromise({
        try: async () => {
          const [newUser] = await db
            .insert(users)
            .values({
              email: input.email,
              name: input.name,
              passwordHash,
              role: input.role,
            })
            .returning()
          return newUser
        },
        catch: error => new DatabaseError({ message: 'Insert failed', cause: error }),
      })
    )

    return user
  })
}
```

### Catching Specific Errors

```typescript
import { Effect } from 'effect'

// Catch specific error tag
const result = await findUserById(id).pipe(
  Effect.catchTag('NotFoundError', () =>
    Effect.succeed(null) // Return null instead of failing
  ),
  Effect.runPromise
)

// Catch multiple error tags
const result = await createUser(input).pipe(
  Effect.catchTags({
    ValidationError: err => Effect.succeed(c.json({ error: err.message }, 400)),
    DuplicateError: err => Effect.succeed(c.json({ error: err.message }, 409)),
  }),
  Effect.runPromise
)

// Catch all errors
const result = await findUserById(id).pipe(
  Effect.catchAll(err =>
    Effect.succeed(c.json({ error: err.message }, 500))
  ),
  Effect.runPromise
)
```

### Transforming Errors

```typescript
import { Effect } from 'effect'

// Map error to different type
const getUserOrFail = (id: string): Effect.Effect<User, ForbiddenError | DatabaseError> => {
  return findUserById(id).pipe(
    Effect.mapError(err => {
      if (err._tag === 'NotFoundError') {
        return new ForbiddenError({ message: 'Access denied' })
      }
      return err
    })
  )
}

// Flatten nested Effects
const getAndValidateUser = (id: string): Effect.Effect<User, NotFoundError | ValidationError> => {
  return findUserById(id).pipe(
    Effect.flatMap(user =>
      user.isActive
        ? Effect.succeed(user)
        : Effect.fail(new ValidationError({ message: 'User is not active' }))
    )
  )
}
```

---

## Converting Errors to HTTP Responses

### Error to Response Mapper

```typescript
import { type Context } from 'hono'
import { Effect } from 'effect'

type AppError =
  | NotFoundError
  | ValidationError
  | DuplicateError
  | UnauthorizedError
  | ForbiddenError
  | DatabaseError
  | ExternalServiceError
  | RateLimitError

export const errorToResponse = (err: AppError, c: Context) => {
  switch (err._tag) {
    case 'NotFoundError':
      return c.json(
        {
          error: `${err.resource} not found`,
          id: err.id,
        },
        404
      )

    case 'ValidationError':
      return c.json(
        {
          error: err.message,
          field: err.field,
          issues: err.issues,
        },
        400
      )

    case 'DuplicateError':
      return c.json(
        {
          error: `${err.resource} with ${err.field} '${err.value}' already exists`,
        },
        409
      )

    case 'UnauthorizedError':
      return c.json({ error: err.message }, 401)

    case 'ForbiddenError':
      return c.json(
        {
          error: err.message,
          requiredRole: err.requiredRole,
        },
        403
      )

    case 'DatabaseError':
      return c.json(
        {
          error: 'Database operation failed',
          details: process.env.NODE_ENV === 'development' ? err.message : undefined,
        },
        500
      )

    case 'ExternalServiceError':
      return c.json(
        {
          error: `External service error: ${err.service}`,
          details: err.message,
        },
        502
      )

    case 'RateLimitError':
      return c.json(
        {
          error: 'Too many requests',
          retryAfter: err.retryAfter,
        },
        429
      )
  }
}
```

### Route Handler with Error Mapping

```typescript
import { Effect } from 'effect'

app.openapi(getUserRoute, async c => {
  const { id } = c.req.valid('param')
  const userService = c.get('userService')

  return await userService
    .findById(id)
    .pipe(
      Effect.map(user => c.json(user, 200)),
      Effect.catchAll(err => Effect.succeed(errorToResponse(err, c))),
      Effect.runPromise
    )
})

// Or with specific error handling
app.openapi(createUserRoute, async c => {
  const input = c.req.valid('json')
  const userService = c.get('userService')

  return await userService
    .create(input)
    .pipe(
      Effect.map(user => c.json(user, 201)),
      Effect.catchTags({
        ValidationError: err => Effect.succeed(c.json({ error: err.message }, 400)),
        DuplicateError: err => Effect.succeed(c.json({ error: err.message }, 409)),
        DatabaseError: err => Effect.succeed(c.json({ error: 'Internal error' }, 500)),
      }),
      Effect.runPromise
    )
})
```

---

## Zod + Effect Integration

### Validate Input with Effect

```typescript
import { Effect } from 'effect'
import { z } from 'zod'

export const validateWithEffect = <T>(
  schema: z.ZodSchema<T>,
  input: unknown
): Effect.Effect<T, ValidationError> => {
  return Effect.try({
    try: () => schema.parse(input),
    catch: error => {
      if (error instanceof z.ZodError) {
        return new ValidationError({
          message: 'Validation failed',
          issues: error.errors.map(err => ({
            path: err.path.map(String),
            message: err.message,
          })),
        })
      }
      return new ValidationError({ message: 'Unknown validation error' })
    },
  })
}

// Usage
const createUserSafe = (input: unknown): Effect.Effect<User, ValidationError | DatabaseError> => {
  return validateWithEffect(CreateUserSchema, input).pipe(
    Effect.flatMap(validInput => createUser(validInput))
  )
}
```

### Safe Parsing in Routes

Hono's `c.req.valid()` already handles Zod validation, but for custom validation:

```typescript
app.post('/users', async c => {
  const body = await c.req.json()

  return await validateWithEffect(CreateUserSchema, body).pipe(
    Effect.flatMap(validInput => userService.create(validInput)),
    Effect.map(user => c.json(user, 201)),
    Effect.catchAll(err => Effect.succeed(errorToResponse(err, c))),
    Effect.runPromise
  )
})
```

---

## Global Error Handler

```typescript
import { type ErrorHandler } from 'hono'
import { ZodError } from 'zod'
import { logger } from '@/config/logger'

export const errorHandler: ErrorHandler = (err, c) => {
  logger.error({
    error: err.message,
    stack: err.stack,
    path: c.req.path,
    method: c.req.method,
  })

  // Zod validation errors
  if (err instanceof ZodError) {
    return c.json(
      {
        error: 'Validation failed',
        issues: err.errors.map(e => ({
          path: e.path.join('.'),
          message: e.message,
        })),
      },
      400
    )
  }

  // Effect errors (if they bubble up)
  if ('_tag' in err) {
    return errorToResponse(err as AppError, c)
  }

  // Default error
  return c.json(
    {
      error: 'Internal server error',
      message: process.env.NODE_ENV === 'development' ? err.message : undefined,
    },
    500
  )
}
```

---

## Validation Utilities

### Reusable Schema Builders

```typescript
import { z } from 'zod'

// Pagination schema
export const PaginationSchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  limit: z.coerce.number().int().positive().max(100).default(20),
})

export type Pagination = z.infer<typeof PaginationSchema>

// Sorting schema
export const SortSchema = <T extends readonly [string, ...string[]]>(fields: T) =>
  z.object({
    sortBy: z.enum(fields).optional(),
    sortOrder: z.enum(['asc', 'desc']).default('asc'),
  })

// Search schema
export const SearchSchema = z.object({
  search: z.string().min(1).optional(),
})

// Combined list query schema
export const createListQuerySchema = <T extends readonly [string, ...string[]]>(sortFields: T) =>
  PaginationSchema.merge(SortSchema(sortFields)).merge(SearchSchema)

// Usage
export const UserListQuerySchema = createListQuerySchema(['name', 'email', 'createdAt'])
```

### Custom Validators

```typescript
import { z } from 'zod'

// UUID validator with custom message
export const uuidSchema = () =>
  z.string().uuid({ message: 'Invalid UUID format' })

// Phone number validator
export const phoneSchema = () =>
  z.string().regex(/^\+?[1-9]\d{1,14}$/, {
    message: 'Invalid phone number format (E.164)',
  })

// Strong password validator
export const strongPasswordSchema = () =>
  z
    .string()
    .min(8)
    .max(128)
    .regex(/[A-Z]/)
    .regex(/[a-z]/)
    .regex(/[0-9]/)
    .regex(/[^A-Za-z0-9]/)

// File size validator (for multipart/form-data)
export const fileSizeSchema = (maxSizeMB: number) =>
  z.custom<File>(
    file => file instanceof File && file.size <= maxSizeMB * 1024 * 1024,
    { message: `File size must not exceed ${maxSizeMB}MB` }
  )
```

---

## Best Practices

1. **Schema-first design** — define Zod schemas before implementing routes
2. **Infer types from schemas** — `z.infer<typeof Schema>`, never manually type
3. **Use Effect for all fallible operations** — never throw, always return `Effect<A, E>`
4. **Tagged errors for pattern matching** — `Data.TaggedError` enables exhaustive matching
5. **Compose Effects with `Effect.gen`** — readable async/error composition
6. **Catch errors at route boundaries** — convert Effect errors to HTTP responses in route handlers
7. **Never expose internal errors to clients** — use generic messages in production
8. **Log all errors** — include context (path, method, user, timestamp)
9. **Use `.pipe(Effect.runPromise)` once per route** — at the outermost level only
10. **Validate early, fail fast** — validate inputs immediately, before business logic
