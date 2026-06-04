# Performance Reference — Code Splitting & Memoisation

## 1. Route-Level Code Splitting

**Rule: every page component is `React.lazy`. No exceptions.**

This keeps the initial bundle small. TanStack Router integrates with `React.lazy` natively.

### Pattern

```typescript
// src/lib/router.ts
import { createRouter, createRoute, createRootRoute, lazyRouteComponent } from '@tanstack/react-router'
import { RootLayout } from '../App'

const rootRoute = createRootRoute({ component: RootLayout })

// ✅ Every page is lazy — the import() call is the split point
const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/dashboard',
  component: lazyRouteComponent(() => import('../features/dashboard/DashboardPage')),
})

const usersRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/users',
  component: lazyRouteComponent(() => import('../features/users/UsersPage')),
})

const routeTree = rootRoute.addChildren([dashboardRoute, usersRoute])
export const router = createRouter({ routeTree })
```

`lazyRouteComponent` is TanStack Router's wrapper around `React.lazy` — it handles default export detection automatically.

### Suspense fallback at the root

```typescript
// src/App.tsx — the RootLayout wraps the outlet in Suspense
import { Outlet } from '@tanstack/react-router'
import { Suspense } from 'react'
import { LoadingOverlay } from '@mantine/core'

const RootLayout = () => (
  <div className="min-h-screen">
    <AppNav />
    <main>
      <Suspense fallback={<LoadingOverlay visible />}>
        <Outlet />
      </Suspense>
    </main>
  </div>
)
export { RootLayout }
```

One `<Suspense>` boundary at the router outlet is sufficient for route transitions. Do not nest multiple Suspense boundaries unless you need granular loading states inside a page.

### Manual `React.lazy` (for non-route heavy components)

Use sparingly — only for components that are large, rarely shown, and not on the critical path (e.g. a heavy chart, a rich text editor):

```typescript
import { lazy, Suspense } from 'react'
import { Loader } from '@mantine/core'

const HeavyChart = lazy(() => import('./HeavyChart'))

const DashboardPage = () => (
  <Suspense fallback={<Loader />}>
    <HeavyChart />
  </Suspense>
)
```

---

## 2. `useMemo` and `useCallback` — when to use and when NOT to

### The default: do NOT add them

`useMemo` and `useCallback` have a cost: memory for the cached value, bookkeeping per render, and added cognitive load. **Premature memoisation is a net negative.** React is fast; unnecessary memoisation often slows things down.

### When to add `useMemo`

Add `useMemo` only when **all three** conditions are true:

1. The computation is measurably expensive (sorting/filtering large lists, heavy transforms).
2. The component re-renders frequently for unrelated reasons.
3. You have profiled it and seen the problem.

```typescript
// ✅ Justified — sorting 10k items on every render of a frequently-updating parent
const sortedUsers = useMemo(
  () => [...users].sort((a, b) => a.name.localeCompare(b.name)),
  [users]
)

// ❌ Not justified — trivially cheap
const fullName = useMemo(() => `${user.first} ${user.last}`, [user.first, user.last])
// Just write: const fullName = `${user.first} ${user.last}`
```

### When to add `useCallback`

Add `useCallback` only when the callback is passed as a prop to a **memoised child component** (`React.memo`) and would otherwise break the memo. Without `React.memo` on the child, `useCallback` has no effect.

```typescript
// ✅ Justified — passed to a React.memo child
const handleDelete = useCallback((id: string) => {
  deleteMutation.mutate(id)
}, [deleteMutation])

return <UserTable onDelete={handleDelete} />  // UserTable is React.memo

// ❌ Not justified — child is not memoised, callback is not in deps of anything
const handleClick = useCallback(() => setOpen(true), [])
```

### When to add `React.memo`

Wrap a component in `React.memo` only when:

1. It is a **shared component** (in `src/components/`) that renders frequently.
2. Its props are **stable** (primitives or memoised objects/callbacks).
3. It has a measurable re-render cost.

```typescript
// src/components/UserCard/UserCard.tsx
import { memo } from 'react'

type UserCardProps = {
  user: User
  onSelect: (id: string) => void
}

// ✅ Justified for a shared card rendered in long lists
const UserCard = memo(({ user, onSelect }: UserCardProps) => (
  <Card onClick={() => onSelect(user.id)}>
    <Text>{user.name}</Text>
  </Card>
))
UserCard.displayName = 'UserCard'
export default UserCard
```

**Never** wrap feature-internal components or page-level components in `React.memo` — their parent re-renders are intentional.

---

## 3. Quick Decision Table

| Situation | Action |
|---|---|
| New component, no performance issue observed | No memo |
| Callback passed to `React.memo` child | `useCallback` |
| Expensive derivation (large list sort/filter) | `useMemo` |
| Shared UI component in long list | `React.memo` + stable props |
| Page-level component | Never `React.memo` |
| Feature-internal component | Never `React.memo` |
| Cheap inline value | No memo |
| "It might be slow" | Profile first, then decide |

---

## 4. Bundle Analysis

Add to `vite.config.ts` for CI bundle size tracking:

```bash
pnpm add -D rollup-plugin-visualizer
```

```typescript
// vite.config.ts
import { visualizer } from 'rollup-plugin-visualizer'

export default defineConfig({
  plugins: [
    react(),
    visualizer({ open: false, filename: 'dist/stats.html' }),
  ],
})
```

Run `pnpm build` and open `dist/stats.html` to inspect chunk sizes before shipping.
