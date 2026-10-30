# Architecture Reference

## Project Scaffold

```
my-app/
├── public/
├── src/
│   ├── main.tsx                  # Entry point
│   ├── App.tsx                   # Root component + Router setup
│   │
│   ├── components/               # Shared UI components (used across ≥2 features)
│   │   ├── Button/
│   │   │   └── Button.tsx
│   │   ├── Modal/
│   │   │   └── Modal.tsx
│   │   └── index.ts              # Barrel export
│   │
│   ├── hooks/                    # Shared hooks (used across ≥2 features)
│   │   ├── useDebounce.ts
│   │   ├── usePagination.ts
│   │   └── index.ts
│   │
│   ├── contexts/                 # Shared contexts (app-wide state)
│   │   ├── AuthContext/
│   │   │   ├── AuthContext.tsx   # Context definition + Provider
│   │   │   ├── useAuth.ts        # Consumer hook
│   │   │   └── index.ts
│   │   └── ThemeContext/
│   │       ├── ThemeContext.tsx
│   │       ├── useTheme.ts
│   │       └── index.ts
│   │
│   ├── utils/                    # Pure utility functions & Effect TS helpers
│   │   ├── date.ts
│   │   ├── format.ts
│   │   └── http.ts               # Effect TS HTTP layer
│   │
│   ├── types/                    # Shared domain types
│   │   ├── api.ts
│   │   └── domain.ts
│   │
│   ├── lib/                      # Third-party configuration (query client, router, etc.)
│   │   ├── queryClient.ts
│   │   └── router.ts
│   │
│   └── features/                 # Feature modules (vertical slices)
│       ├── dashboard/
│       │   ├── components/       # Components used only inside this feature
│       │   │   ├── DashboardCard.tsx
│       │   │   └── StatsWidget.tsx
│       │   ├── hooks/            # Hooks used only inside this feature
│       │   │   └── useDashboardData.ts
│       │   ├── contexts/         # Contexts scoped to this feature
│       │   │   └── DashboardFilterContext.tsx
│       │   ├── utils/            # Feature-local utilities
│       │   │   └── chartHelpers.ts
│       │   ├── types.ts          # Feature-local types
│       │   └── DashboardPage.tsx # Route-level page component
│       │
│       └── users/
│           ├── components/
│           │   ├── UserCard.tsx
│           │   └── UserTable.tsx
│           ├── hooks/
│           │   ├── useUsers.ts
│           │   └── useUserMutation.ts
│           ├── types.ts
│           └── UsersPage.tsx
│
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
└── package.json
```

## Placement Rules

| Code | Rule |
|---|---|
| Component used in 1 feature | `features/<name>/components/` |
| Component used in 2+ features | `src/components/` |
| Hook used in 1 feature | `features/<name>/hooks/` |
| Hook used in 2+ features | `src/hooks/` |
| Context scoped to 1 feature | `features/<name>/contexts/` |
| Context app-wide | `src/contexts/` |
| Type used in 1 feature | `features/<name>/types.ts` |
| Type used across features | `src/types/` |
| Pure utility | `src/utils/` or `features/<name>/utils/` |

## Routing (TanStack Router)

Define routes as a tree in `src/lib/router.ts`. Each route maps to exactly one Page component from a feature folder.

```typescript
// src/lib/router.ts
import { createRouter, createRoute, createRootRoute } from '@tanstack/react-router'
import { RootLayout } from '../App'
import { DashboardPage } from '../features/dashboard/DashboardPage'
import { UsersPage } from '../features/users/UsersPage'

const rootRoute = createRootRoute({ component: RootLayout })

const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/dashboard',
  component: DashboardPage,
})

const usersRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/users',
  component: UsersPage,
})

const routeTree = rootRoute.addChildren([dashboardRoute, usersRoute])

export const router = createRouter({ routeTree })
```

## TanStack Query Setup

```typescript
// src/lib/queryClient.ts
import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 2,
    },
  },
})
```

## Vite Config

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

Always use the `@/` alias for imports instead of relative `../../` paths.

## tsconfig.json (strict)

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] },
    "skipLibCheck": true
  }
}
```
