# Project Setup — Hono + TypeScript

Complete reference for initializing a production-ready Hono TypeScript backend project.

---

## Prerequisites

- **Node.js 20+** (LTS recommended)
- **pnpm 9+** — `npm install -g pnpm` or `corepack enable pnpm`
- **Docker & Docker Compose** for local PostgreSQL

---

## Initial Setup

```bash
# Create project directory
mkdir my-hono-api
cd my-hono-api

# Initialize pnpm project
pnpm init

# Initialize TypeScript
pnpm add -D typescript @types/node tsx
pnpm exec tsc --init
```

---

## Dependencies

### Core Dependencies

```bash
pnpm add hono @hono/zod-openapi effect zod
```

- **hono** — web framework
- **@hono/zod-openapi** — OpenAPI spec generation from Zod schemas
- **effect** — functional error handling and composition
- **zod** — runtime validation and type inference

### Database

```bash
pnpm add drizzle-orm postgres
pnpm add -D drizzle-kit
```

- **drizzle-orm** — type-safe SQL query builder
- **postgres** — PostgreSQL client (faster than pg)
- **drizzle-kit** — migration generator and studio

### Development Tools

```bash
pnpm add -D @biomejs/biome vitest @vitest/coverage-v8 testcontainers
```

- **@biomejs/biome** — fast linter and formatter (replaces ESLint + Prettier)
- **vitest** — fast test runner with TypeScript support
- **@vitest/coverage-v8** — code coverage
- **testcontainers** — Docker containers for integration tests

### Optional Utilities

```bash
pnpm add @hono/node-server  # Node.js adapter
pnpm add pino pino-pretty   # Structured logging
pnpm add @node-rs/bcrypt    # Fast password hashing
pnpm add jose               # JWT utilities
```

---

## Package.json Scripts

```json
{
  "name": "my-hono-api",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "tsx watch --clear-screen=false src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "lint": "biome check .",
    "lint:fix": "biome check --write .",
    "format": "biome format --write .",
    "typecheck": "tsc --noEmit",
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage",
    "db:generate": "drizzle-kit generate",
    "db:migrate": "drizzle-kit migrate",
    "db:push": "drizzle-kit push",
    "db:studio": "drizzle-kit studio",
    "db:drop": "drizzle-kit drop"
  },
  "dependencies": {
    "@hono/node-server": "^1.13.7",
    "@hono/zod-openapi": "^0.18.4",
    "@node-rs/bcrypt": "^1.11.0",
    "drizzle-orm": "^0.37.0",
    "effect": "^3.12.5",
    "hono": "^4.6.15",
    "jose": "^5.9.6",
    "pino": "^9.5.0",
    "pino-pretty": "^13.0.0",
    "postgres": "^3.4.5",
    "zod": "^3.24.1"
  },
  "devDependencies": {
    "@biomejs/biome": "^1.9.4",
    "@types/node": "^22.10.5",
    "@vitest/coverage-v8": "^2.1.8",
    "drizzle-kit": "^0.28.1",
    "testcontainers": "^10.17.0",
    "tsx": "^4.19.2",
    "typescript": "^5.7.2",
    "vitest": "^2.1.8"
  },
  "engines": {
    "node": ">=20.0.0",
    "pnpm": ">=9.0.0"
  }
}
```

---

## TypeScript Configuration

**tsconfig.json:**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "lib": ["ES2023"],
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "allowJs": true,
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noImplicitReturns": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "forceConsistentCasingInFileNames": true,
    "isolatedModules": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "**/*.spec.ts", "**/*.test.ts"]
}
```

**Key settings:**

- `strict: true` — enables all strict type-checking
- `noUncheckedIndexedAccess: true` — array/object access returns `T | undefined`
- `moduleResolution: "bundler"` — modern resolution for ESM
- `paths` — path aliases (`@/` maps to `src/`)

---

## Biome Configuration

**biome.json:**

```json
{
  "$schema": "https://biomejs.dev/schemas/1.9.4/schema.json",
  "organizeImports": {
    "enabled": true
  },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true,
      "suspicious": {
        "noExplicitAny": "error",
        "noExtraNonNullAssertion": "error"
      },
      "style": {
        "useConst": "error",
        "useTemplate": "warn"
      },
      "correctness": {
        "noUnusedVariables": "error"
      }
    }
  },
  "formatter": {
    "enabled": true,
    "formatWithErrors": false,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 100
  },
  "javascript": {
    "formatter": {
      "quoteStyle": "single",
      "trailingCommas": "es5",
      "semicolons": "asNeeded",
      "arrowParentheses": "asNeeded"
    }
  },
  "files": {
    "ignore": ["node_modules", "dist", "coverage", ".next", ".turbo"]
  }
}
```

---

## Drizzle Configuration

**drizzle.config.ts:**

```typescript
import { defineConfig } from 'drizzle-kit'

export default defineConfig({
  schema: './src/db/schema/index.ts',
  out: './src/db/migrations',
  dialect: 'postgresql',
  dbCredentials: {
    url: process.env.DATABASE_URL || 'postgres://postgres:postgres@localhost:5432/mydb',
  },
  verbose: true,
  strict: true,
})
```

---

## Vitest Configuration

**vitest.config.ts:**

```typescript
import { defineConfig } from 'vitest/config'
import path from 'node:path'

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules', 'dist', '**/*.test.ts', '**/*.spec.ts'],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

**src/test/setup.ts:**

```typescript
import { beforeAll, afterAll } from 'vitest'

beforeAll(() => {
  // Setup test environment
  process.env.NODE_ENV = 'test'
})

afterAll(() => {
  // Cleanup
})
```

---

## Environment Variables

**.env.example:**

```bash
NODE_ENV=development
PORT=3000

# Database
DATABASE_URL=postgres://postgres:postgres@localhost:5432/mydb

# Auth
JWT_SECRET=your-secret-key-min-32-characters-long

# Logging
LOG_LEVEL=info
```

**.env** (never commit):

```bash
cp .env.example .env
```

**src/config/env.ts:**

```typescript
import { z } from 'zod'

const envSchema = z.object({
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
  PORT: z.coerce.number().int().positive().default(3000),
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),
  LOG_LEVEL: z.enum(['trace', 'debug', 'info', 'warn', 'error', 'fatal']).default('info'),
})

export const env = envSchema.parse(process.env)

export type Env = z.infer<typeof envSchema>
```

---

## Docker Compose for Local Development

**docker-compose.yml:**

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: mydb
    ports:
      - '5432:5432'
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U postgres']
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

**Start database:**

```bash
docker compose up -d
```

---

## Project Structure Template

```
my-hono-api/
├── src/
│   ├── index.ts                    # Entry point
│   ├── app.ts                      # Hono app instance
│   ├── config/
│   │   ├── env.ts                  # Environment validation
│   │   ├── database.ts             # DB connection pool
│   │   └── logger.ts               # Logger instance
│   ├── routes/
│   │   ├── index.ts                # Route registry
│   │   ├── users.ts                # User routes
│   │   └── health.ts               # Health check
│   ├── middleware/
│   │   ├── error-handler.ts        # Global error handler
│   │   ├── logger.ts               # Request logger
│   │   ├── auth.ts                 # Auth middleware
│   │   └── rate-limit.ts           # Rate limiting
│   ├── services/
│   │   ├── user.service.ts         # Business logic
│   │   └── auth.service.ts
│   ├── db/
│   │   ├── schema/
│   │   │   ├── users.ts            # User schema
│   │   │   └── index.ts            # Schema exports
│   │   ├── migrations/             # Generated migrations
│   │   └── repositories/
│   │       └── user.repository.ts
│   ├── lib/
│   │   ├── errors.ts               # Error types
│   │   ├── result.ts               # Result helpers
│   │   └── validation.ts           # Zod utilities
│   ├── types/
│   │   ├── context.ts              # Hono context types
│   │   └── api.ts                  # API types
│   └── test/
│       ├── setup.ts                # Test setup
│       └── helpers/
│           └── test-db.ts          # Test database utilities
├── .env.example
├── .gitignore
├── biome.json
├── docker-compose.yml
├── drizzle.config.ts
├── package.json
├── pnpm-lock.yaml
├── tsconfig.json
└── vitest.config.ts
```

---

## Minimal Entry Point

**src/index.ts:**

```typescript
import { serve } from '@hono/node-server'
import { createApp } from './app'
import { env } from './config/env'
import { logger } from './config/logger'

const app = createApp()

const port = env.PORT

serve(
  {
    fetch: app.fetch,
    port,
  },
  info => {
    logger.info(`Server running at http://localhost:${info.port}`)
  }
)
```

**src/app.ts:**

```typescript
import { OpenAPIHono } from '@hono/zod-openapi'
import { logger as loggerMiddleware } from './middleware/logger'
import { errorHandler } from './middleware/error-handler'
import { healthRoute } from './routes/health'

export const createApp = () => {
  const app = new OpenAPIHono()

  // Global middleware
  app.use('*', loggerMiddleware)
  app.onError(errorHandler)

  // Routes
  app.route('/health', healthRoute)

  // OpenAPI docs
  app.doc('/openapi.json', {
    openapi: '3.1.0',
    info: {
      title: 'My Hono API',
      version: '1.0.0',
    },
  })

  return app
}
```

---

## Git Ignore

**.gitignore:**

```
node_modules/
dist/
coverage/
.env
.env.local
.DS_Store
*.log
.vscode/
.idea/
```

---

## Next Steps

1. Run `pnpm install`
2. Start PostgreSQL with `docker compose up -d`
3. Generate initial migration: `pnpm db:generate`
4. Run migration: `pnpm db:migrate`
5. Start dev server: `pnpm dev`
6. Open http://localhost:3000/health
7. View OpenAPI docs: http://localhost:3000/openapi.json

---

## Production Dockerfile

**Dockerfile:**

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# Enable pnpm
RUN corepack enable pnpm

# Copy dependency files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy source
COPY . .

# Build
RUN pnpm build

# Production image
FROM node:20-alpine

# Create non-root user
RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001

WORKDIR /app

# Enable pnpm
RUN corepack enable pnpm

# Copy built assets
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/package.json ./
COPY --from=builder --chown=nodejs:nodejs /app/pnpm-lock.yaml ./

# Install production deps only
RUN pnpm install --prod --frozen-lockfile

USER nodejs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1))"

CMD ["node", "dist/index.js"]
```

**Build and run:**

```bash
docker build -t my-hono-api .
docker run -p 3000:3000 --env-file .env my-hono-api
```
