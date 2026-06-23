---
name: hono-ts-backend
description: >
  Hono + TypeScript best practices for modern backend services. Use this skill whenever building
  or reviewing Hono TypeScript APIs, setting up a new service, defining routes, implementing
  middleware, handling validation, or managing database operations. Covers project setup with
  modern tooling (pnpm, tsx, Biome), Hono routing patterns, Zod validation, functional error
  handling with Effect TS, Drizzle ORM with PostgreSQL, OpenAPI documentation, and Docker
  deployment. Always trigger this skill for any Hono TypeScript task — even partial ones like
  "add a route", "create middleware", or "set up validation".
---

# Hono with TypeScript — Best Practices

Opinionated guide for production-grade Hono / TypeScript backend services.
For deep reference on a specific area, read the matching file in `references/`:

| Topic | File |
|---|---|
| Project setup, tooling & dependencies | `references/project-setup.md` |
| Routing, middleware & context patterns | `references/routing-middleware.md` |
| Validation, error handling & responses | `references/validation-errors.md` |
| Database layer with Drizzle ORM | `references/database-patterns.md` |
| Testing strategies & patterns | `references/testing.md` |

---

## Core Principles

- **pnpm only** — faster, more efficient than npm/yarn.
- **Biome** for linting & formatting — replaces ESLint + Prettier with one fast tool.
- **Strict TypeScript** — `strict: true`, no `any`, inference over explicit types where possible.
- **Hono** as the web framework — fast, lightweight, edge-ready, excellent TypeScript support.
- **Effect TS** for error handling and functional patterns — `Effect<A, E>` for all fallible operations.
- **Zod** for runtime validation — schema-first API design with type inference.
- **Drizzle ORM** for database access — type-safe SQL query builder, PostgreSQL primary.
- **Docker** for deployment — multi-stage builds, non-root user, health checks.
- **OpenAPI** via `@hono/zod-openapi` — generate docs from Zod schemas automatically.
- **Functional composition** — pure functions, immutability, no classes for business logic.
- **Dependency injection via context** — pass services through Hono context variables.

---

## Project Setup (Quick Reference)

**Read `references/project-setup.md`** for complete package.json, tsconfig.json, and tooling setup.

**Key dependencies:**

```json
{
  "dependencies": {
    "hono": "^4.x",
    "@hono/zod-openapi": "^0.x",
    "effect": "^3.x",
    "zod": "^3.x",
    "drizzle-orm": "^0.x",
    "postgres": "^3.x"
  },
  "devDependencies": {
    "@biomejs/biome": "^1.x",
    "tsx": "^4.x",
    "vitest": "^2.x",
    "drizzle-kit": "^0.x"
  }
}
```

**Scripts:**

```json
{
  "scripts": {
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "lint": "biome check .",
    "lint:fix": "biome check --write .",
    "format": "biome format --write .",
    "test": "vitest",
    "db:generate": "drizzle-kit generate",
    "db:migrate": "drizzle-kit migrate",
    "db:studio": "drizzle-kit studio"
  }
}
```

---

## Architecture Overview

```
src/
├── index.ts                 ← Entry point, app initialization
├── app.ts                   ← Hono app instance, global middleware
├── config/
│   ├── env.ts              ← Environment variables with Zod validation
│   └── database.ts         ← Database connection pool
├── routes/
│   ├── index.ts            ← Route registry
│   ├── users.ts            ← User routes (example)
│   └── health.ts           ← Health check endpoint
├── middleware/
│   ├── error-handler.ts    ← Global error handling
│   ├── logger.ts           ← Request logging
│   ├── auth.ts             ← Authentication middleware
│   └── rate-limit.ts       ← Rate limiting
├── services/
│   ├── user.service.ts     ← Business logic (Effect-based)
│   └── auth.service.ts
├── db/
│   ├── schema/
│   │   ├── users.ts        ← Drizzle schema definitions
│   │   └── index.ts
│   ├── migrations/         ← Generated SQL migrations
│   └── repositories/
│       └── user.repository.ts
├── lib/
│   ├── errors.ts           ← Custom error types
│   ├── result.ts           ← Result type helpers
│   └── validation.ts       ← Zod schema utilities
└── types/
    ├── context.ts          ← Hono context type extensions
    └── api.ts              ← Shared API types
```

---

## Routing & Middleware (Quick Reference)

**Read `references/routing-middleware.md`** for detailed patterns.

### Basic Route Pattern

```typescript
import { OpenAPIHono, createRoute, z } from '@hono/zod-openapi'
import type { AppContext } from '@/types/context'

const route = createRoute({
  method: 'get',
  path: '/users/{id}',
  request: {
    params: z.object({
      id: z.string().uuid()
    })
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: UserSchema
        }
      },
      description: 'User found'
    },
    404: {
      description: 'User not found'
    }
  }
})

app.openapi(route, async (c) => {
  const { id } = c.req.valid('param')

  return await userService
    .findById(id)
    .pipe(
      Effect.map(user => c.json(user, 200)),
      Effect.catchAll(err => Effect.succeed(c.json({ error: err.message }, 404))),
      Effect.runPromise
    )
})
```

### Middleware Pattern

```typescript
import { type MiddlewareHandler } from 'hono'
import { Effect } from 'effect'

export const authenticate: MiddlewareHandler<AppContext> = async (c, next) => {
  const token = c.req.header('Authorization')?.replace('Bearer ', '')

  if (!token) {
    return c.json({ error: 'Unauthorized' }, 401)
  }

  return await authService
    .verifyToken(token)
    .pipe(
      Effect.tap(user => Effect.sync(() => c.set('user', user))),
      Effect.flatMap(() => Effect.promise(() => next())),
      Effect.catchAll(err =>
        Effect.succeed(c.json({ error: 'Invalid token' }, 401))
      ),
      Effect.runPromise
    )
}
```

---

## Validation & Error Handling (Quick Reference)

**Read `references/validation-errors.md`** for complete patterns.

### Schema-First Design

```typescript
import { z } from 'zod'

// Define schema
export const CreateUserSchema = z.object({
  email: z.string().email(),
  name: z.string().min(2).max(100),
  role: z.enum(['user', 'admin']).default('user')
})

// Infer TypeScript type
export type CreateUserInput = z.infer<typeof CreateUserSchema>

// Use in route
const route = createRoute({
  method: 'post',
  path: '/users',
  request: {
    body: {
      content: {
        'application/json': {
          schema: CreateUserSchema
        }
      }
    }
  },
  responses: {
    201: {
      content: {
        'application/json': {
          schema: UserSchema
        }
      },
      description: 'User created'
    }
  }
})

app.openapi(route, async (c) => {
  const input = c.req.valid('json')

  return await userService
    .create(input)
    .pipe(
      Effect.map(user => c.json(user, 201)),
      Effect.runPromise
    )
})
```

### Error Types with Effect

```typescript
import { Data } from 'effect'

export class NotFoundError extends Data.TaggedError('NotFoundError')<{
  resource: string
  id: string
}> {}

export class ValidationError extends Data.TaggedError('ValidationError')<{
  message: string
  field?: string
}> {}

export class DatabaseError extends Data.TaggedError('DatabaseError')<{
  message: string
  cause?: unknown
}> {}

// Usage in service
export const findUserById = (id: string): Effect.Effect<User, NotFoundError | DatabaseError> =>
  Effect.tryPromise({
    try: () => db.query.users.findFirst({ where: eq(users.id, id) }),
    catch: (error) => new DatabaseError({ message: 'Query failed', cause: error })
  }).pipe(
    Effect.flatMap(user =>
      user
        ? Effect.succeed(user)
        : Effect.fail(new NotFoundError({ resource: 'User', id }))
    )
  )
```

---

## Database Layer (Quick Reference)

**Read `references/database-patterns.md`** for full Drizzle patterns.

### Schema Definition

```typescript
import { pgTable, uuid, text, timestamp, boolean } from 'drizzle-orm/pg-core'

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: text('email').notNull().unique(),
  name: text('name').notNull(),
  passwordHash: text('password_hash').notNull(),
  isActive: boolean('is_active').notNull().default(true),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow()
})

export type User = typeof users.$inferSelect
export type NewUser = typeof users.$inferInsert
```

### Repository Pattern

```typescript
import { Effect } from 'effect'
import { eq } from 'drizzle-orm'
import type { Database } from '@/config/database'

export const createUserRepository = (db: Database) => ({
  findById: (id: string): Effect.Effect<User | undefined, DatabaseError> =>
    Effect.tryPromise({
      try: () => db.query.users.findFirst({ where: eq(users.id, id) }),
      catch: (error) => new DatabaseError({ message: 'Query failed', cause: error })
    }),

  create: (data: NewUser): Effect.Effect<User, DatabaseError> =>
    Effect.tryPromise({
      try: async () => {
        const [user] = await db.insert(users).values(data).returning()
        return user
      },
      catch: (error) => new DatabaseError({ message: 'Insert failed', cause: error })
    }),

  update: (id: string, data: Partial<NewUser>): Effect.Effect<User, NotFoundError | DatabaseError> =>
    Effect.tryPromise({
      try: async () => {
        const [user] = await db
          .update(users)
          .set({ ...data, updatedAt: new Date() })
          .where(eq(users.id, id))
          .returning()
        return user
      },
      catch: (error) => new DatabaseError({ message: 'Update failed', cause: error })
    }).pipe(
      Effect.flatMap(user =>
        user
          ? Effect.succeed(user)
          : Effect.fail(new NotFoundError({ resource: 'User', id }))
      )
    )
})

export type UserRepository = ReturnType<typeof createUserRepository>
```

---

## Service Layer Pattern

Services contain business logic and return `Effect` types:

```typescript
import { Effect } from 'effect'
import type { UserRepository } from '@/db/repositories/user.repository'

export const createUserService = (repo: UserRepository) => ({
  findById: (id: string): Effect.Effect<User, NotFoundError | DatabaseError> =>
    repo.findById(id).pipe(
      Effect.flatMap(user =>
        user
          ? Effect.succeed(user)
          : Effect.fail(new NotFoundError({ resource: 'User', id }))
      )
    ),

  create: (input: CreateUserInput): Effect.Effect<User, ValidationError | DatabaseError> =>
    Effect.gen(function* (_) {
      // Check if email exists
      const existing = yield* _(repo.findByEmail(input.email))

      if (existing) {
        return yield* _(Effect.fail(
          new ValidationError({ message: 'Email already exists', field: 'email' })
        ))
      }

      // Hash password
      const passwordHash = yield* _(hashPassword(input.password))

      // Create user
      return yield* _(repo.create({
        email: input.email,
        name: input.name,
        passwordHash
      }))
    })
})

export type UserService = ReturnType<typeof createUserService>
```

---

## Dependency Injection via Context

Pass services through Hono context:

```typescript
// types/context.ts
import type { UserService } from '@/services/user.service'
import type { AuthService } from '@/services/auth.service'

export type AppContext = {
  Variables: {
    user?: User
    userService: UserService
    authService: AuthService
  }
}

// app.ts
import { OpenAPIHono } from '@hono/zod-openapi'
import type { AppContext } from '@/types/context'

export const createApp = (
  userService: UserService,
  authService: AuthService
) => {
  const app = new OpenAPIHono<AppContext>()

  // Inject services into context
  app.use('*', async (c, next) => {
    c.set('userService', userService)
    c.set('authService', authService)
    await next()
  })

  return app
}

// routes/users.ts
app.openapi(route, async (c) => {
  const userService = c.get('userService')
  const { id } = c.req.valid('param')

  return await userService
    .findById(id)
    .pipe(
      Effect.map(user => c.json(user, 200)),
      Effect.runPromise
    )
})
```

---

## Testing (Quick Reference)

**Read `references/testing.md`** for complete testing patterns.

- **Vitest** for test runner
- **testcontainers** for integration tests with real PostgreSQL
- Unit test services with mocked repositories
- Integration test routes with test database
- Mock Effect services using `Effect.succeed` / `Effect.fail`

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { Effect } from 'effect'

describe('UserService', () => {
  it('should fail with NotFoundError when user does not exist', async () => {
    const mockRepo = {
      findById: () => Effect.succeed(undefined)
    }
    const service = createUserService(mockRepo)

    const result = await Effect.runPromise(
      service.findById('non-existent').pipe(Effect.flip)
    )

    expect(result).toBeInstanceOf(NotFoundError)
  })
})
```

---

## Style Rules

- **Always use arrow functions** — `const foo = () => ...`, never `function foo()`.
- **Types over interfaces** — use `type Foo = {...}` everywhere.
- **Const over let** — immutability by default; `const` everywhere possible.
- **No classes for business logic** — use factory functions returning objects.
- **Effect for all fallible operations** — never throw errors, return `Effect<A, E>`.
- **Zod for validation** — schema-first, infer types from schemas.
- **Repository pattern** — encapsulate database access, return Effect types.
- **Dependency injection via context** — pass services through Hono context.
- **OpenAPI documentation** — use `@hono/zod-openapi` for auto-generated docs.
- **Comprehensive error types** — use `Data.TaggedError` from Effect for typed errors.
- **No `any` type** — strict TypeScript, let inference work.
- **Prefer `Effect.gen` for complex flows** — makes async composition readable.

---

## Docker Deployment

Multi-stage build with health checks:

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable pnpm && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM node:20-alpine
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001
WORKDIR /app
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/package.json ./
COPY --from=builder --chown=nodejs:nodejs /app/pnpm-lock.yaml ./
RUN corepack enable pnpm && pnpm install --prod --frozen-lockfile
USER nodejs
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1))"
CMD ["node", "dist/index.js"]
```

---

## Environment Configuration

Use Zod to validate environment variables:

```typescript
import { z } from 'zod'

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  PORT: z.coerce.number().default(3000),
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),
  LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info')
})

export const env = envSchema.parse(process.env)
export type Env = z.infer<typeof envSchema>
```

---

## Quick Start Checklist

When starting a new Hono TypeScript project:

- [ ] Initialize with `pnpm init`
- [ ] Install dependencies (Hono, Effect, Zod, Drizzle, Biome, tsx, Vitest)
- [ ] Configure `tsconfig.json` with strict mode and path aliases
- [ ] Set up Biome for linting and formatting
- [ ] Create environment validation with Zod
- [ ] Set up Drizzle with PostgreSQL connection
- [ ] Create base app structure (app.ts, index.ts, routes/, middleware/)
- [ ] Add global error handler middleware
- [ ] Add request logger middleware
- [ ] Set up OpenAPI documentation with `@hono/zod-openapi`
- [ ] Create health check endpoint
- [ ] Write first route with Zod validation
- [ ] Set up Docker and docker-compose for local development
- [ ] Configure Drizzle migrations
- [ ] Write first integration test with Vitest
- [ ] Add pre-commit hooks for linting and type-checking
