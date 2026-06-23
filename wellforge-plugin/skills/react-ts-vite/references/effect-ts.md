# Effect TS Patterns Reference

Effect TS replaces try/catch, Promise chains, and ad-hoc error handling. Use it for all async operations, HTTP calls, validation, and business logic with failure modes.

## Installation

```bash
pnpm add effect @effect/schema
```

---

## Core Concepts Used in This Stack

| Concept | Purpose |
|---|---|
| `Effect<A, E, R>` | A computation yielding `A`, failing with `E`, needing `R` |
| `pipe` | Left-to-right function composition |
| `Effect.tryPromise` | Wrap a Promise into an Effect |
| `Effect.runPromise` | Execute an Effect (at the boundary only) |
| `Schema` | Runtime validation with typed errors |
| `Option` | Replace `null`/`undefined` |
| `Either` | Synchronous success/failure |

---

## HTTP / Data Fetching

```typescript
// src/utils/http.ts
import { Effect, pipe } from 'effect'

type HttpError =
  | { _tag: 'NetworkError'; message: string }
  | { _tag: 'ParseError'; message: string }
  | { _tag: 'HttpError'; status: number; message: string }

const fetchJson = <T>(url: string): Effect.Effect<T, HttpError> =>
  pipe(
    Effect.tryPromise({
      try: () => fetch(url),
      catch: (e): HttpError => ({
        _tag: 'NetworkError',
        message: String(e),
      }),
    }),
    Effect.flatMap(response =>
      response.ok
        ? Effect.tryPromise({
            try: () => response.json() as Promise<T>,
            catch: (e): HttpError => ({
              _tag: 'ParseError',
              message: String(e),
            }),
          })
        : Effect.fail<HttpError>({
            _tag: 'HttpError',
            status: response.status,
            message: response.statusText,
          })
    )
  )

export { fetchJson }
export type { HttpError }
```

---

## Schema Validation

```typescript
// features/users/types.ts
import { Schema } from '@effect/schema'

const UserSchema = Schema.Struct({
  id: Schema.String,
  name: Schema.String,
  email: Schema.String.pipe(Schema.pattern(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)),
  role: Schema.Literal('admin', 'viewer', 'editor'),
  createdAt: Schema.DateFromString,
})

type User = Schema.Schema.Type<typeof UserSchema>

export { UserSchema }
export type { User }
```

---

## Feature Data Layer (fetcher + validator combined)

```typescript
// features/users/hooks/useUsers.ts — the Effect-powered queryFn
import { Effect, pipe } from 'effect'
import { Schema } from '@effect/schema'
import { fetchJson } from '@/utils/http'
import { UserSchema } from '../types'
import type { HttpError } from '@/utils/http'

type UsersError = HttpError | { _tag: 'ValidationError'; message: string }

const fetchUsersEffect = (): Promise<User[]> =>
  pipe(
    fetchJson<unknown[]>('/api/users'),
    Effect.flatMap(raw =>
      Effect.tryPromise({
        try: () =>
          Promise.resolve(
            raw.map(item => Schema.decodeUnknownSync(UserSchema)(item))
          ),
        catch: (e): UsersError => ({
          _tag: 'ValidationError',
          message: String(e),
        }),
      })
    ),
    Effect.runPromise   // ← only at the boundary (queryFn)
  )

const useUsers = () =>
  useQuery({
    queryKey: ['users'],
    queryFn: fetchUsersEffect,
  })

export { useUsers }
```

---

## Option — Replace null/undefined

```typescript
import { Option, pipe } from 'effect'

// Wrapping a nullable value
const findUser = (id: string, users: User[]): Option.Option<User> =>
  Option.fromNullable(users.find(u => u.id === id))

// Consuming
const getUserName = (id: string, users: User[]): string =>
  pipe(
    findUser(id, users),
    Option.map(u => u.name),
    Option.getOrElse(() => 'Unknown')
  )

// In a component via hook
const useSelectedUser = (id: string) => {
  const { data: users = [] } = useUsers()
  return useMemo(() => findUser(id, users), [id, users])
}

// In JSX — match on Option
const UserDetail = ({ userId }: { userId: string }) => {
  const userOption = useSelectedUser(userId)

  return pipe(
    userOption,
    Option.match({
      onNone: () => <p>User not found</p>,
      onSome: user => <p>{user.name}</p>,
    })
  )
}
```

---

## Either — Synchronous validation

```typescript
import { Either, pipe } from 'effect'

type ValidationError = { field: string; message: string }

const validateEmail = (email: string): Either.Either<string, ValidationError> =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
    ? Either.right(email)
    : Either.left({ field: 'email', message: 'Invalid email format' })

// In a form hook
const useUserForm = () => {
  const [email, setEmail] = useState('')

  const emailValidation = useMemo(() => validateEmail(email), [email])

  const emailError = pipe(
    emailValidation,
    Either.match({
      onLeft: err => err.message,
      onRight: () => null,
    })
  )

  const isValid = Either.isRight(emailValidation)

  return { email, setEmail, emailError, isValid }
}
```

---

## pipe — Composing transformations

```typescript
import { pipe, Array as A, Option } from 'effect'

// Transforming a list functionally
const getActiveAdminNames = (users: User[]): string[] =>
  pipe(
    users,
    A.filter(u => u.active && u.role === 'admin'),
    A.map(u => u.name),
    A.sort(String.localeCompare)  // Effect's Order-aware sort
  )
```

---

## Effect Boundary Rule

**`Effect.runPromise` / `Effect.runSync` must only be called at integration boundaries:**

| Boundary | Where |
|---|---|
| TanStack Query `queryFn` / `mutationFn` | `features/<n>/hooks/use*.ts` |
| Form submit handlers | `features/<n>/hooks/use*Form.ts` |
| Event handlers returning void | inside hook callbacks |

Never call `Effect.runPromise` inside a component. Always inside a hook.

```typescript
// ✅ Correct — boundary is in the hook's mutationFn
const useCreateUser = () =>
  useMutation({
    mutationFn: (payload: CreateUserPayload) =>
      pipe(
        validatePayloadEffect(payload),
        Effect.flatMap(createUserEffect),
        Effect.runPromise   // ← boundary here, inside the hook
      ),
  })

// ❌ Wrong — boundary inside component
const CreateUserPage = () => {
  const handleSubmit = () => {
    Effect.runPromise(createUserEffect(data))  // ← never here
  }
}
```

---

## Error Display Convention

Errors surfaced by TanStack Query have type `Error`. Map them in the hook:

```typescript
type UserQueryError =
  | { _tag: 'NetworkError'; message: string }
  | { _tag: 'ValidationError'; message: string }

const useUsers = () => {
  const query = useQuery({
    queryKey: ['users'],
    queryFn: fetchUsersEffect,
  })

  const errorMessage = query.error
    ? getErrorMessage(query.error as UserQueryError)
    : null

  return { ...query, errorMessage }
}

const getErrorMessage = (e: UserQueryError): string => {
  switch (e._tag) {
    case 'NetworkError': return 'Network unavailable. Please retry.'
    case 'ValidationError': return 'Unexpected data from server.'
  }
}
```
