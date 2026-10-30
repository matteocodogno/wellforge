# Database Patterns — Drizzle ORM + PostgreSQL

Complete patterns for type-safe database access with Drizzle ORM, PostgreSQL, and Effect TS.

---

## Database Connection

**src/config/database.ts:**

```typescript
import { drizzle } from 'drizzle-orm/postgres-js'
import postgres from 'postgres'
import { env } from './env'
import * as schema from '@/db/schema'

// Create PostgreSQL client
const client = postgres(env.DATABASE_URL, {
  max: 10,
  idle_timeout: 20,
  connect_timeout: 10,
})

// Create Drizzle instance
export const db = drizzle(client, { schema })

export type Database = typeof db

// Graceful shutdown
export const closeDatabase = async () => {
  await client.end()
}
```

---

## Schema Definition

### Basic Table

```typescript
import { pgTable, uuid, text, timestamp, boolean } from 'drizzle-orm/pg-core'

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  email: text('email').notNull().unique(),
  name: text('name').notNull(),
  passwordHash: text('password_hash').notNull(),
  isActive: boolean('is_active').notNull().default(true),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow(),
})

// Infer types
export type User = typeof users.$inferSelect
export type NewUser = typeof users.$inferInsert
```

### Enums

```typescript
import { pgEnum } from 'drizzle-orm/pg-core'

export const roleEnum = pgEnum('role', ['user', 'admin', 'moderator'])
export const statusEnum = pgEnum('status', ['draft', 'published', 'archived'])

export const posts = pgTable('posts', {
  id: uuid('id').primaryKey().defaultRandom(),
  title: text('title').notNull(),
  content: text('content').notNull(),
  status: statusEnum('status').notNull().default('draft'),
  authorId: uuid('author_id')
    .notNull()
    .references(() => users.id, { onDelete: 'cascade' }),
  createdAt: timestamp('created_at').notNull().defaultNow(),
  updatedAt: timestamp('updated_at').notNull().defaultNow(),
})

export type Post = typeof posts.$inferSelect
export type NewPost = typeof posts.$inferInsert
```

### Relations

```typescript
import { relations } from 'drizzle-orm'

export const usersRelations = relations(users, ({ many }) => ({
  posts: many(posts),
  comments: many(comments),
}))

export const postsRelations = relations(posts, ({ one, many }) => ({
  author: one(users, {
    fields: [posts.authorId],
    references: [users.id],
  }),
  comments: many(comments),
}))

export const comments = pgTable('comments', {
  id: uuid('id').primaryKey().defaultRandom(),
  content: text('content').notNull(),
  postId: uuid('post_id')
    .notNull()
    .references(() => posts.id, { onDelete: 'cascade' }),
  authorId: uuid('author_id')
    .notNull()
    .references(() => users.id, { onDelete: 'cascade' }),
  createdAt: timestamp('created_at').notNull().defaultNow(),
})

export type Comment = typeof comments.$inferSelect
export type NewComment = typeof comments.$inferInsert

export const commentsRelations = relations(comments, ({ one }) => ({
  post: one(posts, {
    fields: [comments.postId],
    references: [posts.id],
  }),
  author: one(users, {
    fields: [comments.authorId],
    references: [users.id],
  }),
}))
```

### Advanced Column Types

```typescript
import {
  pgTable,
  uuid,
  text,
  integer,
  real,
  jsonb,
  index,
  uniqueIndex,
} from 'drizzle-orm/pg-core'

export const products = pgTable(
  'products',
  {
    id: uuid('id').primaryKey().defaultRandom(),
    name: text('name').notNull(),
    description: text('description'),
    price: integer('price').notNull(), // Store in cents
    stock: integer('stock').notNull().default(0),
    rating: real('rating'),
    metadata: jsonb('metadata').$type<{
      dimensions?: { width: number; height: number; depth: number }
      weight?: number
      manufacturer?: string
    }>(),
    tags: text('tags').array(),
    createdAt: timestamp('created_at').notNull().defaultNow(),
    updatedAt: timestamp('updated_at').notNull().defaultNow(),
  },
  table => ({
    nameIdx: index('products_name_idx').on(table.name),
    priceIdx: index('products_price_idx').on(table.price),
    tagsIdx: index('products_tags_idx').on(table.tags),
  })
)

export type Product = typeof products.$inferSelect
export type NewProduct = typeof products.$inferInsert
```

---

## Repository Pattern

### Basic Repository

```typescript
import { Effect } from 'effect'
import { eq } from 'drizzle-orm'
import type { Database } from '@/config/database'
import { users, type User, type NewUser } from '@/db/schema/users'
import { NotFoundError, DatabaseError } from '@/lib/errors'

export const createUserRepository = (db: Database) => ({
  findById: (id: string): Effect.Effect<User | undefined, DatabaseError> =>
    Effect.tryPromise({
      try: () => db.query.users.findFirst({ where: eq(users.id, id) }),
      catch: error => new DatabaseError({ message: 'Query failed', cause: error }),
    }),

  findByEmail: (email: string): Effect.Effect<User | undefined, DatabaseError> =>
    Effect.tryPromise({
      try: () => db.query.users.findFirst({ where: eq(users.email, email) }),
      catch: error => new DatabaseError({ message: 'Query failed', cause: error }),
    }),

  list: (filters: {
    limit: number
    offset: number
  }): Effect.Effect<User[], DatabaseError> =>
    Effect.tryPromise({
      try: () =>
        db.query.users.findMany({
          limit: filters.limit,
          offset: filters.offset,
          orderBy: (users, { desc }) => [desc(users.createdAt)],
        }),
      catch: error => new DatabaseError({ message: 'Query failed', cause: error }),
    }),

  create: (data: NewUser): Effect.Effect<User, DatabaseError> =>
    Effect.tryPromise({
      try: async () => {
        const [user] = await db.insert(users).values(data).returning()
        return user!
      },
      catch: error => new DatabaseError({ message: 'Insert failed', cause: error }),
    }),

  update: (
    id: string,
    data: Partial<NewUser>
  ): Effect.Effect<User, NotFoundError | DatabaseError> =>
    Effect.tryPromise({
      try: async () => {
        const [user] = await db
          .update(users)
          .set({ ...data, updatedAt: new Date() })
          .where(eq(users.id, id))
          .returning()
        return user
      },
      catch: error => new DatabaseError({ message: 'Update failed', cause: error }),
    }).pipe(
      Effect.flatMap(user =>
        user
          ? Effect.succeed(user)
          : Effect.fail(new NotFoundError({ resource: 'User', id }))
      )
    ),

  delete: (id: string): Effect.Effect<void, NotFoundError | DatabaseError> =>
    Effect.tryPromise({
      try: async () => {
        const result = await db.delete(users).where(eq(users.id, id)).returning()
        return result[0]
      },
      catch: error => new DatabaseError({ message: 'Delete failed', cause: error }),
    }).pipe(
      Effect.flatMap(user =>
        user
          ? Effect.succeed(undefined)
          : Effect.fail(new NotFoundError({ resource: 'User', id }))
      )
    ),
})

export type UserRepository = ReturnType<typeof createUserRepository>
```

### Repository with Relations

```typescript
import { Effect } from 'effect'
import { eq, desc } from 'drizzle-orm'
import type { Database } from '@/config/database'
import { posts, type Post, type NewPost } from '@/db/schema/posts'

export const createPostRepository = (db: Database) => ({
  findById: (id: string): Effect.Effect<Post | undefined, DatabaseError> =>
    Effect.tryPromise({
      try: () =>
        db.query.posts.findFirst({
          where: eq(posts.id, id),
          with: {
            author: true,
            comments: {
              with: {
                author: true,
              },
            },
          },
        }),
      catch: error => new DatabaseError({ message: 'Query failed', cause: error }),
    }),

  findByAuthor: (authorId: string): Effect.Effect<Post[], DatabaseError> =>
    Effect.tryPromise({
      try: () =>
        db.query.posts.findMany({
          where: eq(posts.authorId, authorId),
          orderBy: [desc(posts.createdAt)],
          with: {
            author: true,
          },
        }),
      catch: error => new DatabaseError({ message: 'Query failed', cause: error }),
    }),

  create: (data: NewPost): Effect.Effect<Post, DatabaseError> =>
    Effect.tryPromise({
      try: async () => {
        const [post] = await db.insert(posts).values(data).returning()
        return post!
      },
      catch: error => new DatabaseError({ message: 'Insert failed', cause: error }),
    }),
})

export type PostRepository = ReturnType<typeof createPostRepository>
```

---

## Query Patterns

### Filtering

```typescript
import { and, or, eq, ne, gt, gte, lt, lte, like, ilike, inArray } from 'drizzle-orm'

// Simple filter
const activeUsers = await db.query.users.findMany({
  where: eq(users.isActive, true),
})

// Multiple conditions (AND)
const adminUsers = await db.query.users.findMany({
  where: and(
    eq(users.isActive, true),
    eq(users.role, 'admin')
  ),
})

// OR conditions
const specialUsers = await db.query.users.findMany({
  where: or(
    eq(users.role, 'admin'),
    eq(users.role, 'moderator')
  ),
})

// Comparison operators
const recentPosts = await db.query.posts.findMany({
  where: gt(posts.createdAt, new Date('2024-01-01')),
})

// LIKE / ILIKE (case-insensitive)
const searchUsers = await db.query.users.findMany({
  where: ilike(users.name, '%john%'),
})

// IN operator
const selectedUsers = await db.query.users.findMany({
  where: inArray(users.id, ['uuid1', 'uuid2', 'uuid3']),
})
```

### Sorting

```typescript
import { asc, desc } from 'drizzle-orm'

// Single field
const sortedUsers = await db.query.users.findMany({
  orderBy: [desc(users.createdAt)],
})

// Multiple fields
const sortedPosts = await db.query.posts.findMany({
  orderBy: [desc(posts.createdAt), asc(posts.title)],
})
```

### Pagination

```typescript
const getUsers = (page: number, limit: number) => {
  const offset = (page - 1) * limit

  return Effect.tryPromise({
    try: async () => {
      const [data, [{ count }]] = await Promise.all([
        db.query.users.findMany({
          limit,
          offset,
          orderBy: [desc(users.createdAt)],
        }),
        db.select({ count: count() }).from(users),
      ])

      return {
        data,
        pagination: {
          page,
          limit,
          total: Number(count),
          totalPages: Math.ceil(Number(count) / limit),
        },
      }
    },
    catch: error => new DatabaseError({ message: 'Query failed', cause: error }),
  })
}
```

### Aggregations

```typescript
import { count, sum, avg, min, max } from 'drizzle-orm'

// Count
const userCount = await db.select({ count: count() }).from(users)

// Sum
const totalRevenue = await db
  .select({ total: sum(orders.amount) })
  .from(orders)

// Average
const avgRating = await db
  .select({ avg: avg(products.rating) })
  .from(products)

// Group by
const postsByStatus = await db
  .select({
    status: posts.status,
    count: count(),
  })
  .from(posts)
  .groupBy(posts.status)
```

### Joins

```typescript
import { eq } from 'drizzle-orm'

// Inner join
const usersWithPosts = await db
  .select({
    user: users,
    post: posts,
  })
  .from(users)
  .innerJoin(posts, eq(users.id, posts.authorId))

// Left join
const allUsersWithPosts = await db
  .select({
    user: users,
    post: posts,
  })
  .from(users)
  .leftJoin(posts, eq(users.id, posts.authorId))
```

---

## Transactions

### Basic Transaction

```typescript
import { Effect } from 'effect'

const transferFunds = (
  fromAccountId: string,
  toAccountId: string,
  amount: number
): Effect.Effect<void, DatabaseError> =>
  Effect.tryPromise({
    try: () =>
      db.transaction(async tx => {
        // Debit from account
        await tx
          .update(accounts)
          .set({ balance: sql`${accounts.balance} - ${amount}` })
          .where(eq(accounts.id, fromAccountId))

        // Credit to account
        await tx
          .update(accounts)
          .set({ balance: sql`${accounts.balance} + ${amount}` })
          .where(eq(accounts.id, toAccountId))
      }),
    catch: error => new DatabaseError({ message: 'Transaction failed', cause: error }),
  })
```

### Transaction with Effect Composition

```typescript
import { Effect } from 'effect'

const createUserWithProfile = (
  userData: NewUser,
  profileData: NewProfile
): Effect.Effect<{ user: User; profile: Profile }, DatabaseError> =>
  Effect.tryPromise({
    try: () =>
      db.transaction(async tx => {
        const [user] = await tx.insert(users).values(userData).returning()

        const [profile] = await tx
          .insert(profiles)
          .values({ ...profileData, userId: user!.id })
          .returning()

        return { user: user!, profile: profile! }
      }),
    catch: error => new DatabaseError({ message: 'Transaction failed', cause: error }),
  })
```

---

## Migrations

### Generate Migration

```bash
pnpm db:generate
```

This reads your schema and generates SQL migration files in `src/db/migrations/`.

### Run Migrations

```bash
pnpm db:migrate
```

### Manual Migration

**src/db/migrations/0001_add_user_role.sql:**

```sql
ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user';
CREATE INDEX users_role_idx ON users(role);
```

---

## Full-Text Search

```typescript
import { sql } from 'drizzle-orm'

// Create tsvector column
export const posts = pgTable('posts', {
  id: uuid('id').primaryKey().defaultRandom(),
  title: text('title').notNull(),
  content: text('content').notNull(),
  searchVector: sql`tsvector`.as('search_vector'),
})

// Generate search vector (in migration)
/*
ALTER TABLE posts
ADD COLUMN search_vector tsvector
GENERATED ALWAYS AS (
  to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, ''))
) STORED;

CREATE INDEX posts_search_idx ON posts USING GIN (search_vector);
*/

// Search query
const searchPosts = (query: string): Effect.Effect<Post[], DatabaseError> =>
  Effect.tryPromise({
    try: () =>
      db
        .select()
        .from(posts)
        .where(
          sql`${posts.searchVector} @@ plainto_tsquery('english', ${query})`
        ),
    catch: error => new DatabaseError({ message: 'Search failed', cause: error }),
  })
```

---

## Schema Organization

**src/db/schema/index.ts:**

```typescript
export * from './users'
export * from './posts'
export * from './comments'
export * from './products'
```

**src/db/schema/users.ts:**

```typescript
import { pgTable, uuid, text, timestamp, boolean } from 'drizzle-orm/pg-core'

export const users = pgTable('users', {
  // ... columns
})

export type User = typeof users.$inferSelect
export type NewUser = typeof users.$inferInsert
```

---

## Connection Pool Configuration

```typescript
import postgres from 'postgres'

const client = postgres(env.DATABASE_URL, {
  max: 10, // Maximum connections
  idle_timeout: 20, // Close idle connections after 20s
  connect_timeout: 10, // Connection timeout
  ssl: env.NODE_ENV === 'production' ? 'require' : false,
  onnotice: () => {}, // Suppress notices in development
  transform: {
    undefined: null, // Convert undefined to null
  },
})
```

---

## Best Practices

1. **Use repositories** — encapsulate all database access in repository functions
2. **Return Effect types** — wrap all database operations in `Effect.tryPromise`
3. **Infer types from schema** — use `$inferSelect` and `$inferInsert`, never manual types
4. **Use transactions for multi-step operations** — ensure atomicity
5. **Index frequently queried columns** — email, foreign keys, timestamps
6. **Use relations for joins** — leverage Drizzle's relation API for type-safe joins
7. **Never expose database errors to clients** — wrap in `DatabaseError`
8. **Use prepared statements** — Drizzle handles this automatically
9. **Close connections on shutdown** — implement graceful shutdown
10. **Separate schema files by domain** — users.ts, posts.ts, orders.ts
11. **Store money as integers** — use cents/pennies to avoid floating-point issues
12. **Use JSONB for flexible metadata** — type it with `.$type<T>()`
13. **Use enums for fixed sets** — role, status, type fields
14. **Always handle undefined in queries** — `findFirst` returns `T | undefined`
15. **Use `defaultNow()` for timestamps** — let database handle creation time
