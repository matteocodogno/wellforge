# Coding Conventions Reference

## 1. Types, Never Interfaces

```typescript
// ✅ Correct
type User = {
  id: string
  name: string
  email: string
}

type ApiResponse<T> = {
  data: T
  meta: PaginationMeta
}

type ButtonVariant = 'primary' | 'secondary' | 'ghost'

// ❌ Wrong
interface User { ... }
interface ApiResponse<T> { ... }
```

**Why**: `type` is more composable (union, intersection, mapped types). Avoid `interface` in all cases.

---

## 2. Arrow Functions Everywhere

```typescript
// ✅ Correct — component
const UserCard = ({ user }: UserCardProps) => {
  return <div>{user.name}</div>
}
export default UserCard

// ✅ Correct — hook
const useUsers = () => {
  const query = useQuery({ queryKey: ['users'], queryFn: fetchUsers })
  return query
}

// ✅ Correct — utility
const formatDate = (date: Date): string =>
  new Intl.DateTimeFormat('it-CH').format(date)

// ✅ Correct — event handler
const handleClick = (id: string) => () => {
  // ...
}

// ❌ Wrong
function UserCard(props) { ... }
function useUsers() { ... }
function formatDate(date) { ... }
```

---

## 3. Logic in Hooks, Not Components

Components must be thin render trees. Extract everything else.

```typescript
// ❌ Wrong — logic inside component
const UsersPage = () => {
  const [users, setUsers] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    setIsLoading(true)
    fetch('/api/users')
      .then(r => r.json())
      .then(data => { setUsers(data); setIsLoading(false) })
      .catch(e => { setError(e); setIsLoading(false) })
  }, [])

  const sortedUsers = users.sort((a, b) => a.name.localeCompare(b.name))
  // ...
}

// ✅ Correct — logic in hook
// features/users/hooks/useUsers.ts
const useUsers = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: fetchUsersEffect,
  })

  const sortedUsers = useMemo(
    () => [...(data ?? [])].sort((a, b) => a.name.localeCompare(b.name)),
    [data]
  )

  return { users: sortedUsers, isLoading, error }
}

// features/users/UsersPage.tsx — only rendering
const UsersPage = () => {
  const { users, isLoading, error } = useUsers()

  if (isLoading) return <Spinner />
  if (error) return <ErrorBanner error={error} />

  return (
    <ul>
      {users.map(u => <UserCard key={u.id} user={u} />)}
    </ul>
  )
}
export default UsersPage
```

---

## 4. Context for State

```typescript
// src/contexts/AuthContext/AuthContext.tsx
import { createContext, useState, useCallback } from 'react'

type AuthState = {
  user: User | null
  token: string | null
}

type AuthContextValue = AuthState & {
  login: (credentials: Credentials) => Promise<void>
  logout: () => void
}

// ✅ Export context for the consumer hook only — never use useContext directly in feature code
export const AuthContext = createContext<AuthContextValue | null>(null)

type AuthProviderProps = {
  children: React.ReactNode
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const [state, setState] = useState<AuthState>({ user: null, token: null })

  const login = useCallback(async (credentials: Credentials) => {
    const result = await loginEffect(credentials)
    setState(result)
  }, [])

  const logout = useCallback(() => {
    setState({ user: null, token: null })
  }, [])

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// src/contexts/AuthContext/useAuth.ts
import { useContext } from 'react'
import { AuthContext } from './AuthContext'

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
```

---

## 5. One Component Per File

```
// ✅ Correct
UserCard.tsx     → exports default UserCard
UserTable.tsx    → exports default UserTable

// ❌ Wrong
UserComponents.tsx → exports UserCard, UserTable, UserAvatar
```

Sub-components that are tightly coupled and never used standalone may be defined in the same file but **must not be exported**.

---

## 6. Props Types

```typescript
// ✅ Always define a Props type named <ComponentName>Props
type UserCardProps = {
  user: User
  onSelect?: (id: string) => void
  className?: string
}

const UserCard = ({ user, onSelect, className }: UserCardProps) => {
  // ...
}
export default UserCard
```

---

## 7. Immutability and Functional Patterns

```typescript
// ✅ Spread, map, filter — never mutate
const updatedUsers = users.map(u =>
  u.id === targetId ? { ...u, name: newName } : u
)

const activeUsers = users.filter(u => u.active)

// ❌ Never
users.push(newUser)
users[0].name = 'New'
array.sort(fn)  // sort mutates — use [...array].sort(fn)
```

---

## 8. Import Order

1. React and React ecosystem (`react`, `react-dom`)
2. Third-party libraries (`@tanstack/react-query`, `effect`, etc.)
3. Internal shared (`@/components`, `@/hooks`, `@/contexts`, `@/utils`, `@/types`)
4. Feature-local (relative `./`, `../`)
5. Type-only imports last (`import type { ... }`)

```typescript
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { pipe } from 'effect'
import { useAuth } from '@/contexts/AuthContext'
import { UserCard } from '@/components'
import { useUserFilters } from './hooks/useUserFilters'
import type { User } from './types'
```

---

## 9. TanStack Query Conventions

```typescript
// One hook per file — each hook in its own .ts file named after the hook
// All hooks for a feature live in features/<feature>/hooks/
// features/users/hooks/useUsers.ts
const useUsers = (filters?: UserFilters) => {
  return useQuery({
    queryKey: ['users', filters],
    queryFn: () => fetchUsersEffect(filters),
    select: data => [...data].sort((a, b) => a.name.localeCompare(b.name)),
  })
}

// Mutations in separate hook
// features/users/hooks/useUserMutation.ts
const useCreateUser = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CreateUserPayload) => createUserEffect(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })
}
```

---

## 10. Styling Conventions — Mantine + Tailwind

Mantine is the component library. Tailwind is for layout composition only.

```typescript
// ✅ Mantine for all UI primitives
import { Button, TextInput, Card, Group, Stack, Text } from '@mantine/core'

const UserCard = ({ user, onSelect }: UserCardProps) => (
  <Card shadow="sm" padding="lg" radius="md" withBorder>
    <Group justify="space-between">
      <Text fw={500}>{user.name}</Text>
      <Button size="xs" variant="light" onClick={() => onSelect(user.id)}>
        View
      </Button>
    </Group>
  </Card>
)

// ✅ Tailwind for grid/flex layout between Mantine components
const UsersPage = () => (
  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
    {users.map(u => <UserCard key={u.id} user={u} onSelect={handleSelect} />)}
  </div>
)

// ❌ Never build UI with raw Tailwind HTML when a Mantine component exists
<button className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700">
  Submit
</button>

// ❌ Never use inline styles
<div style={{ marginTop: 16, color: 'red' }}>Error</div>
```

For conditional Tailwind classes use the `cn` utility:

```typescript
// src/utils/cn.ts
const cn = (...classes: (string | undefined | false | null)[]) =>
  classes.filter(Boolean).join(' ')

export { cn }
```

---

## 11. File Naming

| Artifact | Convention | Example |
|---|---|---|
| Component | PascalCase `.tsx` | `UserCard.tsx` |
| Hook | camelCase `use` prefix `.ts` | `useUsers.ts` |
| Context file | PascalCase `Context` suffix `.tsx` | `AuthContext.tsx` |
| Consumer hook | camelCase `use` prefix `.ts` | `useAuth.ts` |
| Utility | camelCase `.ts` | `formatDate.ts` |
| Types file | camelCase `.ts` | `types.ts` or `user.ts` |
| Barrel | `index.ts` | `index.ts` |

---

## 12. Barrel Exports

Use `index.ts` to create clean public APIs for each folder:

```typescript
// src/components/index.ts
export { default as Button } from './Button/Button'
export { default as Modal } from './Modal/Modal'
export { default as Spinner } from './Spinner/Spinner'

// Consuming code
import { Button, Modal } from '@/components'
```

Never barrel-export from feature folders — features are private vertical slices.
