# Testing — Hono + TypeScript

Complete testing patterns for Hono TypeScript APIs with Vitest, Testcontainers, and Effect TS.

---

## Test Stack

- **Vitest** — fast test runner with native TypeScript support
- **Testcontainers** — Docker containers for integration tests (real PostgreSQL)
- **@hono/testing** — utilities for testing Hono apps
- **Effect** — functional error handling in tests

---

## Test Organization

```
src/
├── services/
│   ├── user.service.ts
│   └── user.service.test.ts
├── db/
│   └── repositories/
│       ├── user.repository.ts
│       └── user.repository.test.ts
├── routes/
│   ├── users.ts
│   └── users.test.ts
└── test/
    ├── setup.ts
    └── helpers/
        ├── test-db.ts
        ├── test-app.ts
        └── fixtures.ts
```

---

## Unit Testing Services

### Service Test with Mocked Repository

```typescript
import { describe, it, expect, vi } from 'vitest'
import { Effect } from 'effect'
import { createUserService } from './user.service'
import { NotFoundError, ValidationError, DuplicateError } from '@/lib/errors'
import type { UserRepository } from '@/db/repositories/user.repository'

describe('UserService', () => {
  describe('findById', () => {
    it('should return user when found', async () => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        name: 'Test User',
        role: 'user' as const,
        isActive: true,
        createdAt: new Date(),
        updatedAt: new Date(),
      }

      const mockRepo: UserRepository = {
        findById: () => Effect.succeed(mockUser),
        findByEmail: vi.fn(),
        list: vi.fn(),
        create: vi.fn(),
        update: vi.fn(),
        delete: vi.fn(),
      }

      const service = createUserService(mockRepo)

      const result = await Effect.runPromise(service.findById('123'))

      expect(result).toEqual(mockUser)
    })

    it('should fail with NotFoundError when user does not exist', async () => {
      const mockRepo: UserRepository = {
        findById: () => Effect.succeed(undefined),
        findByEmail: vi.fn(),
        list: vi.fn(),
        create: vi.fn(),
        update: vi.fn(),
        delete: vi.fn(),
      }

      const service = createUserService(mockRepo)

      const result = await Effect.runPromise(
        service.findById('non-existent').pipe(Effect.flip)
      )

      expect(result).toBeInstanceOf(NotFoundError)
      expect(result.id).toBe('non-existent')
    })
  })

  describe('create', () => {
    it('should create user when email is unique', async () => {
      const input = {
        email: 'new@example.com',
        name: 'New User',
        password: 'Password123!',
        role: 'user' as const,
      }

      const createdUser = {
        id: '456',
        email: input.email,
        name: input.name,
        passwordHash: 'hashed',
        role: input.role,
        isActive: true,
        createdAt: new Date(),
        updatedAt: new Date(),
      }

      const mockRepo: UserRepository = {
        findById: vi.fn(),
        findByEmail: () => Effect.succeed(undefined),
        list: vi.fn(),
        create: () => Effect.succeed(createdUser),
        update: vi.fn(),
        delete: vi.fn(),
      }

      const service = createUserService(mockRepo)

      const result = await Effect.runPromise(service.create(input))

      expect(result.email).toBe(input.email)
      expect(result.name).toBe(input.name)
    })

    it('should fail with DuplicateError when email already exists', async () => {
      const input = {
        email: 'existing@example.com',
        name: 'Test User',
        password: 'Password123!',
        role: 'user' as const,
      }

      const existingUser = {
        id: '789',
        email: input.email,
        name: 'Existing User',
        passwordHash: 'hash',
        role: 'user' as const,
        isActive: true,
        createdAt: new Date(),
        updatedAt: new Date(),
      }

      const mockRepo: UserRepository = {
        findById: vi.fn(),
        findByEmail: () => Effect.succeed(existingUser),
        list: vi.fn(),
        create: vi.fn(),
        update: vi.fn(),
        delete: vi.fn(),
      }

      const service = createUserService(mockRepo)

      const result = await Effect.runPromise(service.create(input).pipe(Effect.flip))

      expect(result).toBeInstanceOf(DuplicateError)
    })
  })
})
```

---

## Integration Testing Repositories

### Setup Testcontainers

**src/test/helpers/test-db.ts:**

```typescript
import { PostgreSqlContainer, StartedPostgreSqlContainer } from '@testcontainers/postgresql'
import { drizzle } from 'drizzle-orm/postgres-js'
import { migrate } from 'drizzle-orm/postgres-js/migrator'
import postgres from 'postgres'
import * as schema from '@/db/schema'
import type { Database } from '@/config/database'

let container: StartedPostgreSqlContainer | null = null
let db: Database | null = null
let client: ReturnType<typeof postgres> | null = null

export const setupTestDatabase = async (): Promise<Database> => {
  if (db) return db

  // Start PostgreSQL container
  container = await new PostgreSqlContainer('postgres:16-alpine')
    .withExposedPorts(5432)
    .withDatabase('test')
    .withUsername('test')
    .withPassword('test')
    .start()

  const connectionString = container.getConnectionUri()

  // Create client
  client = postgres(connectionString, { max: 1 })

  // Create Drizzle instance
  db = drizzle(client, { schema })

  // Run migrations
  await migrate(db, { migrationsFolder: './src/db/migrations' })

  return db
}

export const getTestDatabase = (): Database => {
  if (!db) throw new Error('Test database not initialized')
  return db
}

export const teardownTestDatabase = async () => {
  if (client) await client.end()
  if (container) await container.stop()
  db = null
  client = null
  container = null
}

export const cleanDatabase = async () => {
  if (!db) return

  // Truncate all tables
  await db.execute('TRUNCATE TABLE users, posts, comments CASCADE')
}
```

**src/test/setup.ts:**

```typescript
import { beforeAll, afterAll, afterEach } from 'vitest'
import { setupTestDatabase, teardownTestDatabase, cleanDatabase } from './helpers/test-db'

beforeAll(async () => {
  await setupTestDatabase()
}, 60000) // 60s timeout for container start

afterEach(async () => {
  await cleanDatabase()
})

afterAll(async () => {
  await teardownTestDatabase()
})
```

### Repository Integration Test

```typescript
import { describe, it, expect, beforeEach } from 'vitest'
import { Effect } from 'effect'
import { getTestDatabase } from '@/test/helpers/test-db'
import { createUserRepository } from './user.repository'
import { NotFoundError } from '@/lib/errors'

describe('UserRepository (Integration)', () => {
  const db = getTestDatabase()
  const repo = createUserRepository(db)

  describe('findById', () => {
    it('should return user when exists', async () => {
      const newUser = {
        email: 'test@example.com',
        name: 'Test User',
        passwordHash: 'hash',
        role: 'user' as const,
      }

      const created = await Effect.runPromise(repo.create(newUser))
      const found = await Effect.runPromise(repo.findById(created.id))

      expect(found).toBeDefined()
      expect(found?.email).toBe(newUser.email)
    })

    it('should return undefined when user does not exist', async () => {
      const found = await Effect.runPromise(
        repo.findById('00000000-0000-0000-0000-000000000000')
      )

      expect(found).toBeUndefined()
    })
  })

  describe('create', () => {
    it('should create user with generated ID', async () => {
      const newUser = {
        email: 'new@example.com',
        name: 'New User',
        passwordHash: 'hash',
        role: 'user' as const,
      }

      const created = await Effect.runPromise(repo.create(newUser))

      expect(created.id).toBeDefined()
      expect(created.email).toBe(newUser.email)
      expect(created.createdAt).toBeInstanceOf(Date)
    })
  })

  describe('update', () => {
    it('should update user fields', async () => {
      const newUser = {
        email: 'original@example.com',
        name: 'Original Name',
        passwordHash: 'hash',
        role: 'user' as const,
      }

      const created = await Effect.runPromise(repo.create(newUser))

      const updated = await Effect.runPromise(
        repo.update(created.id, { name: 'Updated Name' })
      )

      expect(updated.name).toBe('Updated Name')
      expect(updated.email).toBe(newUser.email) // Unchanged
      expect(updated.updatedAt.getTime()).toBeGreaterThan(created.updatedAt.getTime())
    })

    it('should fail with NotFoundError when user does not exist', async () => {
      const result = await Effect.runPromise(
        repo.update('00000000-0000-0000-0000-000000000000', { name: 'Test' })
          .pipe(Effect.flip)
      )

      expect(result).toBeInstanceOf(NotFoundError)
    })
  })

  describe('delete', () => {
    it('should delete existing user', async () => {
      const newUser = {
        email: 'delete@example.com',
        name: 'To Delete',
        passwordHash: 'hash',
        role: 'user' as const,
      }

      const created = await Effect.runPromise(repo.create(newUser))

      await Effect.runPromise(repo.delete(created.id))

      const found = await Effect.runPromise(repo.findById(created.id))
      expect(found).toBeUndefined()
    })

    it('should fail with NotFoundError when user does not exist', async () => {
      const result = await Effect.runPromise(
        repo.delete('00000000-0000-0000-0000-000000000000').pipe(Effect.flip)
      )

      expect(result).toBeInstanceOf(NotFoundError)
    })
  })
})
```

---

## API Route Testing

### Test Hono Routes

**src/test/helpers/test-app.ts:**

```typescript
import { OpenAPIHono } from '@hono/zod-openapi'
import type { AppContext } from '@/types/context'
import { createUserService } from '@/services/user.service'
import { createUserRepository } from '@/db/repositories/user.repository'
import { getTestDatabase } from './test-db'

export const createTestApp = () => {
  const db = getTestDatabase()
  const userRepo = createUserRepository(db)
  const userService = createUserService(userRepo)

  const app = new OpenAPIHono<AppContext>()

  // Inject services
  app.use('*', async (c, next) => {
    c.set('userService', userService)
    await next()
  })

  return { app, userService }
}
```

**src/routes/users.test.ts:**

```typescript
import { describe, it, expect } from 'vitest'
import { Effect } from 'effect'
import { createTestApp } from '@/test/helpers/test-app'
import { userRoutes } from './users'

describe('User Routes', () => {
  describe('GET /users/:id', () => {
    it('should return user when exists', async () => {
      const { app, userService } = createTestApp()
      app.route('/users', userRoutes)

      // Create test user
      const user = await Effect.runPromise(
        userService.create({
          email: 'test@example.com',
          name: 'Test User',
          password: 'Password123!',
          role: 'user',
        })
      )

      // Make request
      const res = await app.request(`/users/${user.id}`)
      const json = await res.json()

      expect(res.status).toBe(200)
      expect(json.id).toBe(user.id)
      expect(json.email).toBe(user.email)
    })

    it('should return 404 when user does not exist', async () => {
      const { app } = createTestApp()
      app.route('/users', userRoutes)

      const res = await app.request('/users/00000000-0000-0000-0000-000000000000')
      const json = await res.json()

      expect(res.status).toBe(404)
      expect(json.error).toBeDefined()
    })

    it('should return 400 for invalid UUID', async () => {
      const { app } = createTestApp()
      app.route('/users', userRoutes)

      const res = await app.request('/users/invalid-uuid')

      expect(res.status).toBe(400)
    })
  })

  describe('POST /users', () => {
    it('should create user with valid input', async () => {
      const { app } = createTestApp()
      app.route('/users', userRoutes)

      const res = await app.request('/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'new@example.com',
          name: 'New User',
          password: 'Password123!',
          role: 'user',
        }),
      })
      const json = await res.json()

      expect(res.status).toBe(201)
      expect(json.email).toBe('new@example.com')
      expect(json.passwordHash).toBeUndefined() // Should not expose password hash
    })

    it('should return 400 for invalid input', async () => {
      const { app } = createTestApp()
      app.route('/users', userRoutes)

      const res = await app.request('/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'invalid-email',
          name: 'A', // Too short
          password: '123', // Too weak
        }),
      })

      expect(res.status).toBe(400)
    })

    it('should return 409 when email already exists', async () => {
      const { app, userService } = createTestApp()
      app.route('/users', userRoutes)

      // Create first user
      await Effect.runPromise(
        userService.create({
          email: 'duplicate@example.com',
          name: 'First User',
          password: 'Password123!',
          role: 'user',
        })
      )

      // Try to create duplicate
      const res = await app.request('/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: 'duplicate@example.com',
          name: 'Second User',
          password: 'Password123!',
          role: 'user',
        }),
      })

      expect(res.status).toBe(409)
    })
  })
})
```

---

## Testing Middleware

```typescript
import { describe, it, expect } from 'vitest'
import { OpenAPIHono } from '@hono/zod-openapi'
import { authenticate } from '@/middleware/auth'
import type { AppContext } from '@/types/context'

describe('Auth Middleware', () => {
  it('should reject requests without Authorization header', async () => {
    const app = new OpenAPIHono<AppContext>()
    app.use('*', authenticate)
    app.get('/protected', c => c.json({ message: 'success' }))

    const res = await app.request('/protected')

    expect(res.status).toBe(401)
  })

  it('should reject requests with invalid token', async () => {
    const app = new OpenAPIHono<AppContext>()
    app.use('*', authenticate)
    app.get('/protected', c => c.json({ message: 'success' }))

    const res = await app.request('/protected', {
      headers: { Authorization: 'Bearer invalid-token' },
    })

    expect(res.status).toBe(401)
  })

  it('should allow requests with valid token', async () => {
    const app = new OpenAPIHono<AppContext>()
    app.use('*', authenticate)
    app.get('/protected', c => c.json({ message: 'success' }))

    const validToken = 'valid-test-token' // Generate real token in actual test

    const res = await app.request('/protected', {
      headers: { Authorization: `Bearer ${validToken}` },
    })

    expect(res.status).toBe(200)
  })
})
```

---

## Test Fixtures

**src/test/helpers/fixtures.ts:**

```typescript
import { Effect } from 'effect'
import type { UserRepository } from '@/db/repositories/user.repository'
import type { User, NewUser } from '@/db/schema/users'

export const createTestUser = (
  repo: UserRepository,
  overrides?: Partial<NewUser>
): Effect.Effect<User, never> => {
  const defaultUser: NewUser = {
    email: `test-${Date.now()}@example.com`,
    name: 'Test User',
    passwordHash: 'hashed-password',
    role: 'user',
    isActive: true,
    ...overrides,
  }

  return repo.create(defaultUser).pipe(
    Effect.catchAll(() => Effect.die('Failed to create test user'))
  )
}

export const createTestUsers = (
  repo: UserRepository,
  count: number
): Effect.Effect<User[], never> => {
  return Effect.all(
    Array.from({ length: count }, (_, i) =>
      createTestUser(repo, {
        email: `user-${i}@example.com`,
        name: `User ${i}`,
      })
    )
  )
}
```

**Usage:**

```typescript
import { describe, it, expect } from 'vitest'
import { Effect } from 'effect'
import { createTestUser } from '@/test/helpers/fixtures'

describe('User Service', () => {
  it('should update existing user', async () => {
    const db = getTestDatabase()
    const repo = createUserRepository(db)
    const service = createUserService(repo)

    // Create test user
    const user = await Effect.runPromise(createTestUser(repo))

    // Update user
    const updated = await Effect.runPromise(
      service.update(user.id, { name: 'Updated Name' })
    )

    expect(updated.name).toBe('Updated Name')
  })
})
```

---

## Snapshot Testing

```typescript
import { describe, it, expect } from 'vitest'

describe('User API Response', () => {
  it('should match snapshot', async () => {
    const { app, userService } = createTestApp()
    app.route('/users', userRoutes)

    const user = await Effect.runPromise(
      userService.create({
        email: 'snapshot@example.com',
        name: 'Snapshot User',
        password: 'Password123!',
        role: 'user',
      })
    )

    const res = await app.request(`/users/${user.id}`)
    const json = await res.json()

    // Remove dynamic fields
    delete json.id
    delete json.createdAt
    delete json.updatedAt

    expect(json).toMatchInlineSnapshot(`
      {
        "email": "snapshot@example.com",
        "isActive": true,
        "name": "Snapshot User",
        "role": "user",
      }
    `)
  })
})
```

---

## Coverage Configuration

**vitest.config.ts:**

```typescript
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules',
        'dist',
        '**/*.test.ts',
        '**/*.spec.ts',
        'src/test/**',
        'src/db/migrations/**',
      ],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
})
```

**Run coverage:**

```bash
pnpm test:coverage
```

---

## Best Practices

1. **Use Testcontainers for integration tests** — real PostgreSQL, no mocks
2. **Clean database between tests** — `afterEach` truncate tables
3. **Test services with mocked repositories** — fast unit tests
4. **Test repositories with real database** — integration tests
5. **Test routes end-to-end** — full HTTP request/response cycle
6. **Use fixtures for test data** — reusable test user creation
7. **Test error cases** — not just happy paths
8. **Use `Effect.flip` to test failures** — extract error from Effect
9. **Mock external services** — API calls, email, etc.
10. **Set timeouts for container tests** — `beforeAll(..., 60000)`
11. **Test middleware in isolation** — separate from routes
12. **Use snapshot tests for API responses** — catch unexpected changes
13. **Aim for 80%+ code coverage** — but prioritize critical paths
14. **Run tests in CI/CD** — on every commit and PR
15. **Separate unit and integration tests** — run fast tests frequently
