# Routing & Middleware — Hono + TypeScript

Complete patterns for building type-safe routes and middleware with Hono and OpenAPI integration.

---

## Route Definition with OpenAPI

Use `@hono/zod-openapi` to define routes with automatic OpenAPI spec generation.

### Basic GET Route

```typescript
import { OpenAPIHono, createRoute, z } from '@hono/zod-openapi'

const app = new OpenAPIHono()

const getUserRoute = createRoute({
  method: 'get',
  path: '/users/{id}',
  request: {
    params: z.object({
      id: z.string().uuid(),
    }),
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: z.object({
            id: z.string().uuid(),
            email: z.string().email(),
            name: z.string(),
            createdAt: z.string().datetime(),
          }),
        },
      },
      description: 'User found successfully',
    },
    404: {
      content: {
        'application/json': {
          schema: z.object({
            error: z.string(),
          }),
        },
      },
      description: 'User not found',
    },
  },
  tags: ['Users'],
  summary: 'Get user by ID',
  description: 'Retrieve a single user by their unique identifier',
})

app.openapi(getUserRoute, async c => {
  const { id } = c.req.valid('param')

  return await userService
    .findById(id)
    .pipe(
      Effect.map(user => c.json(user, 200)),
      Effect.catchTag('NotFoundError', () =>
        Effect.succeed(c.json({ error: 'User not found' }, 404))
      ),
      Effect.runPromise
    )
})
```

---

## POST Route with Body Validation

```typescript
const createUserRoute = createRoute({
  method: 'post',
  path: '/users',
  request: {
    body: {
      content: {
        'application/json': {
          schema: z.object({
            email: z.string().email(),
            name: z.string().min(2).max(100),
            password: z.string().min(8),
          }),
        },
      },
      required: true,
    },
  },
  responses: {
    201: {
      content: {
        'application/json': {
          schema: UserSchema,
        },
      },
      description: 'User created successfully',
    },
    400: {
      content: {
        'application/json': {
          schema: z.object({
            error: z.string(),
            field: z.string().optional(),
          }),
        },
      },
      description: 'Validation error',
    },
    409: {
      content: {
        'application/json': {
          schema: z.object({
            error: z.string(),
          }),
        },
      },
      description: 'User already exists',
    },
  },
  tags: ['Users'],
  summary: 'Create new user',
})

app.openapi(createUserRoute, async c => {
  const input = c.req.valid('json')

  return await userService
    .create(input)
    .pipe(
      Effect.map(user => c.json(user, 201)),
      Effect.catchTag('ValidationError', err =>
        Effect.succeed(c.json({ error: err.message, field: err.field }, 400))
      ),
      Effect.catchTag('DuplicateError', err =>
        Effect.succeed(c.json({ error: err.message }, 409))
      ),
      Effect.runPromise
    )
})
```

---

## PATCH Route with Partial Updates

```typescript
const updateUserRoute = createRoute({
  method: 'patch',
  path: '/users/{id}',
  request: {
    params: z.object({
      id: z.string().uuid(),
    }),
    body: {
      content: {
        'application/json': {
          schema: z.object({
            name: z.string().min(2).max(100).optional(),
            email: z.string().email().optional(),
          }).refine(data => Object.keys(data).length > 0, {
            message: 'At least one field must be provided',
          }),
        },
      },
      required: true,
    },
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: UserSchema,
        },
      },
      description: 'User updated successfully',
    },
    404: {
      content: {
        'application/json': {
          schema: z.object({ error: z.string() }),
        },
      },
      description: 'User not found',
    },
  },
  tags: ['Users'],
})

app.openapi(updateUserRoute, async c => {
  const { id } = c.req.valid('param')
  const updates = c.req.valid('json')

  return await userService
    .update(id, updates)
    .pipe(
      Effect.map(user => c.json(user, 200)),
      Effect.catchTag('NotFoundError', () =>
        Effect.succeed(c.json({ error: 'User not found' }, 404))
      ),
      Effect.runPromise
    )
})
```

---

## DELETE Route

```typescript
const deleteUserRoute = createRoute({
  method: 'delete',
  path: '/users/{id}',
  request: {
    params: z.object({
      id: z.string().uuid(),
    }),
  },
  responses: {
    204: {
      description: 'User deleted successfully',
    },
    404: {
      content: {
        'application/json': {
          schema: z.object({ error: z.string() }),
        },
      },
      description: 'User not found',
    },
  },
  tags: ['Users'],
})

app.openapi(deleteUserRoute, async c => {
  const { id } = c.req.valid('param')

  return await userService
    .delete(id)
    .pipe(
      Effect.map(() => c.body(null, 204)),
      Effect.catchTag('NotFoundError', () =>
        Effect.succeed(c.json({ error: 'User not found' }, 404))
      ),
      Effect.runPromise
    )
})
```

---

## Query Parameters

```typescript
const listUsersRoute = createRoute({
  method: 'get',
  path: '/users',
  request: {
    query: z.object({
      page: z.coerce.number().int().positive().default(1),
      limit: z.coerce.number().int().positive().max(100).default(20),
      role: z.enum(['user', 'admin']).optional(),
      search: z.string().optional(),
    }),
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: z.object({
            data: z.array(UserSchema),
            pagination: z.object({
              page: z.number(),
              limit: z.number(),
              total: z.number(),
              totalPages: z.number(),
            }),
          }),
        },
      },
      description: 'List of users',
    },
  },
  tags: ['Users'],
})

app.openapi(listUsersRoute, async c => {
  const query = c.req.valid('query')

  return await userService
    .list(query)
    .pipe(
      Effect.map(result => c.json(result, 200)),
      Effect.runPromise
    )
})
```

---

## Headers Validation

```typescript
const protectedRoute = createRoute({
  method: 'get',
  path: '/protected',
  request: {
    headers: z.object({
      authorization: z.string().regex(/^Bearer .+$/),
      'x-api-key': z.string().optional(),
    }),
  },
  responses: {
    200: {
      content: {
        'application/json': {
          schema: z.object({ message: z.string() }),
        },
      },
      description: 'Success',
    },
    401: {
      content: {
        'application/json': {
          schema: z.object({ error: z.string() }),
        },
      },
      description: 'Unauthorized',
    },
  },
  security: [{ Bearer: [] }],
})
```

---

## Middleware Patterns

### Request Logger

```typescript
import { type MiddlewareHandler } from 'hono'
import { logger } from '@/config/logger'

export const requestLogger: MiddlewareHandler = async (c, next) => {
  const start = Date.now()
  const { method, url } = c.req

  await next()

  const duration = Date.now() - start
  const status = c.res.status

  logger.info({
    method,
    url,
    status,
    duration: `${duration}ms`,
  })
}
```

### Authentication Middleware

```typescript
import { type MiddlewareHandler } from 'hono'
import { Effect } from 'effect'
import type { AppContext } from '@/types/context'

export const authenticate: MiddlewareHandler<AppContext> = async (c, next) => {
  const authHeader = c.req.header('Authorization')

  if (!authHeader?.startsWith('Bearer ')) {
    return c.json({ error: 'Missing or invalid authorization header' }, 401)
  }

  const token = authHeader.slice(7)

  return await Effect.gen(function* (_) {
    const authService = c.get('authService')
    const user = yield* _(authService.verifyToken(token))
    c.set('user', user)
    return yield* _(Effect.promise(() => next()))
  }).pipe(
    Effect.catchAll(err =>
      Effect.succeed(c.json({ error: 'Invalid or expired token' }, 401))
    ),
    Effect.runPromise
  )
}
```

### Role-Based Authorization

```typescript
import { type MiddlewareHandler } from 'hono'
import type { AppContext } from '@/types/context'

export const requireRole = (...roles: string[]): MiddlewareHandler<AppContext> => {
  return async (c, next) => {
    const user = c.get('user')

    if (!user) {
      return c.json({ error: 'Unauthorized' }, 401)
    }

    if (!roles.includes(user.role)) {
      return c.json({ error: 'Forbidden: insufficient permissions' }, 403)
    }

    await next()
  }
}

// Usage
app.use('/admin/*', authenticate, requireRole('admin'))
```

### Rate Limiting

```typescript
import { type MiddlewareHandler } from 'hono'

const rateLimitStore = new Map<string, { count: number; resetAt: number }>()

export const rateLimit = (
  maxRequests: number,
  windowMs: number
): MiddlewareHandler => {
  return async (c, next) => {
    const ip = c.req.header('x-forwarded-for') || c.req.header('x-real-ip') || 'unknown'
    const now = Date.now()

    const existing = rateLimitStore.get(ip)

    if (existing && existing.resetAt > now) {
      if (existing.count >= maxRequests) {
        return c.json(
          { error: 'Too many requests', retryAfter: Math.ceil((existing.resetAt - now) / 1000) },
          429
        )
      }
      existing.count++
    } else {
      rateLimitStore.set(ip, {
        count: 1,
        resetAt: now + windowMs,
      })
    }

    await next()
  }
}

// Usage
app.use('/api/*', rateLimit(100, 60000)) // 100 requests per minute
```

### CORS Middleware

```typescript
import { cors } from 'hono/cors'

app.use('*', cors({
  origin: ['https://example.com', 'https://app.example.com'],
  allowMethods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowHeaders: ['Content-Type', 'Authorization'],
  exposeHeaders: ['Content-Length', 'X-Request-Id'],
  maxAge: 86400,
  credentials: true,
}))
```

### Error Handler Middleware

```typescript
import { type ErrorHandler } from 'hono'
import { logger } from '@/config/logger'

export const errorHandler: ErrorHandler = (err, c) => {
  logger.error({
    error: err.message,
    stack: err.stack,
    path: c.req.path,
    method: c.req.method,
  })

  // Zod validation errors
  if (err.name === 'ZodError') {
    return c.json(
      {
        error: 'Validation failed',
        issues: err.issues,
      },
      400
    )
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

// Usage in app.ts
app.onError(errorHandler)
```

### Request ID Middleware

```typescript
import { type MiddlewareHandler } from 'hono'
import { randomUUID } from 'node:crypto'

export const requestId: MiddlewareHandler = async (c, next) => {
  const id = c.req.header('x-request-id') || randomUUID()
  c.set('requestId', id)
  c.header('x-request-id', id)
  await next()
}
```

---

## Context Type Extensions

**types/context.ts:**

```typescript
import type { User } from '@/db/schema/users'
import type { UserService } from '@/services/user.service'
import type { AuthService } from '@/services/auth.service'

export type AppContext = {
  Variables: {
    user?: User
    requestId: string
    userService: UserService
    authService: AuthService
  }
}
```

Usage in routes:

```typescript
import { OpenAPIHono } from '@hono/zod-openapi'
import type { AppContext } from '@/types/context'

const app = new OpenAPIHono<AppContext>()

app.openapi(route, async c => {
  const user = c.get('user') // Type-safe access
  const userService = c.get('userService')
  // ...
})
```

---

## Route Organization

**routes/index.ts:**

```typescript
import { OpenAPIHono } from '@hono/zod-openapi'
import type { AppContext } from '@/types/context'
import { userRoutes } from './users'
import { authRoutes } from './auth'
import { healthRoute } from './health'

export const createRouter = () => {
  const app = new OpenAPIHono<AppContext>()

  app.route('/health', healthRoute)
  app.route('/auth', authRoutes)
  app.route('/users', userRoutes)

  return app
}
```

**routes/users.ts:**

```typescript
import { OpenAPIHono } from '@hono/zod-openapi'
import type { AppContext } from '@/types/context'
import { authenticate, requireRole } from '@/middleware/auth'

export const userRoutes = new OpenAPIHono<AppContext>()

// Public route
userRoutes.openapi(getUserRoute, async c => { /* ... */ })

// Protected routes
userRoutes.use('*', authenticate)
userRoutes.openapi(createUserRoute, async c => { /* ... */ })
userRoutes.openapi(updateUserRoute, async c => { /* ... */ })

// Admin-only routes
userRoutes.use('/admin/*', requireRole('admin'))
userRoutes.openapi(deleteUserRoute, async c => { /* ... */ })
```

---

## OpenAPI Documentation

**app.ts:**

```typescript
import { OpenAPIHono } from '@hono/zod-openapi'
import { swaggerUI } from '@hono/swagger-ui'

const app = new OpenAPIHono()

// ... routes ...

// OpenAPI spec
app.doc('/openapi.json', {
  openapi: '3.1.0',
  info: {
    title: 'My Hono API',
    version: '1.0.0',
    description: 'A production-grade Hono TypeScript API',
  },
  servers: [
    {
      url: 'http://localhost:3000',
      description: 'Development server',
    },
    {
      url: 'https://api.example.com',
      description: 'Production server',
    },
  ],
  security: [{ Bearer: [] }],
  components: {
    securitySchemes: {
      Bearer: {
        type: 'http',
        scheme: 'bearer',
        bearerFormat: 'JWT',
      },
    },
  },
})

// Swagger UI
app.get('/docs', swaggerUI({ url: '/openapi.json' }))

export { app }
```

---

## Health Check Endpoint

**routes/health.ts:**

```typescript
import { OpenAPIHono, createRoute, z } from '@hono/zod-openapi'
import { db } from '@/config/database'
import { Effect } from 'effect'

const healthRoute = createRoute({
  method: 'get',
  path: '/',
  responses: {
    200: {
      content: {
        'application/json': {
          schema: z.object({
            status: z.literal('healthy'),
            timestamp: z.string().datetime(),
            services: z.object({
              database: z.enum(['up', 'down']),
            }),
          }),
        },
      },
      description: 'Service is healthy',
    },
    503: {
      content: {
        'application/json': {
          schema: z.object({
            status: z.literal('unhealthy'),
            timestamp: z.string().datetime(),
            services: z.object({
              database: z.enum(['up', 'down']),
            }),
          }),
        },
      },
      description: 'Service is unhealthy',
    },
  },
  tags: ['Health'],
})

const app = new OpenAPIHono()

app.openapi(healthRoute, async c => {
  const checkDatabase = Effect.tryPromise({
    try: () => db.execute('SELECT 1'),
    catch: () => 'down' as const,
  }).pipe(Effect.map(() => 'up' as const))

  const dbStatus = await Effect.runPromise(
    checkDatabase.pipe(Effect.catchAll(() => Effect.succeed('down' as const)))
  )

  const isHealthy = dbStatus === 'up'
  const status = isHealthy ? 200 : 503

  return c.json(
    {
      status: isHealthy ? 'healthy' : 'unhealthy',
      timestamp: new Date().toISOString(),
      services: {
        database: dbStatus,
      },
    },
    status
  )
})

export { app as healthRoute }
```

---

## Best Practices

1. **Always use `createRoute` for type-safe routes** — never use raw `.get()` / `.post()`
2. **Define schemas with Zod** — co-locate with route definitions
3. **Use Effect for async operations** — `.pipe(Effect.runPromise)` to execute
4. **Middleware order matters** — logger → CORS → auth → rate-limit → routes
5. **Type-safe context** — extend `AppContext` type for all context variables
6. **Organize routes by resource** — one file per resource (users.ts, posts.ts, etc.)
7. **Use middleware for cross-cutting concerns** — auth, logging, rate-limiting
8. **Always return proper HTTP status codes** — 2xx success, 4xx client errors, 5xx server errors
9. **Document with OpenAPI** — every route should have complete OpenAPI spec
10. **Health checks must be simple** — fast response, minimal dependencies checked
