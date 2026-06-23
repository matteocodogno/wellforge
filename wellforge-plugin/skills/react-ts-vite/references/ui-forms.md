# UI, Forms & Error Boundaries Reference

## 1. Mantine UI

Mantine is the component library. Use Mantine components **first**. Use Tailwind only for layout composition, spacing between Mantine components, and cases where no Mantine component fits.

### Installation

```bash
pnpm add @mantine/core @mantine/hooks @mantine/form @mantine/dates @mantine/notifications
pnpm add -D postcss postcss-preset-mantine postcss-simple-vars
```

### Provider setup (`src/main.tsx`)

```typescript
import { MantineProvider, createTheme } from '@mantine/core'
import { Notifications } from '@mantine/notifications'
import '@mantine/core/styles.css'
import '@mantine/notifications/styles.css'

const theme = createTheme({
  fontFamily: 'Inter, sans-serif',
  primaryColor: 'blue',
  // extend here: colors, components defaults, radius, etc.
})

const root = document.getElementById('root')!
ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <MantineProvider theme={theme}>
      <Notifications />
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </MantineProvider>
  </React.StrictMode>
)
```

### Tailwind + Mantine coexistence

Mantine uses CSS variables for theming. Tailwind is used for layout. To avoid conflicts:

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  // Disable Tailwind's preflight to avoid resetting Mantine's base styles
  corePlugins: {
    preflight: false,
  },
} satisfies Config
```

### Usage pattern

```typescript
// ✅ Mantine for all UI components
import { Button, TextInput, Stack, Group, Card, Text, Badge } from '@mantine/core'

const UserCard = ({ user }: UserCardProps) => (
  <Card shadow="sm" padding="lg" radius="md" withBorder>
    <Group justify="space-between">
      <Text fw={500}>{user.name}</Text>
      <Badge color={user.active ? 'green' : 'gray'}>
        {user.active ? 'Active' : 'Inactive'}
      </Badge>
    </Group>
    <Text size="sm" c="dimmed" mt="xs">{user.email}</Text>
  </Card>
)
export default UserCard

// ✅ Tailwind only for layout composition between Mantine components
const UsersPage = () => {
  const { users } = useUsers()
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {users.map(u => <UserCard key={u.id} user={u} />)}
    </div>
  )
}
export default UsersPage

// ❌ Never replace Mantine components with raw Tailwind HTML
<button className="rounded bg-blue-600 px-4 py-2 text-white">Submit</button>
```

### Notifications

```typescript
import { notifications } from '@mantine/notifications'

// In a hook — after mutation success/error
const useCreateUser = () => {
  return useMutation({
    mutationFn: createUserEffect,
    onSuccess: () => {
      notifications.show({
        title: 'User created',
        message: 'The user has been added successfully.',
        color: 'green',
      })
    },
    onError: () => {
      notifications.show({
        title: 'Error',
        message: 'Could not create user. Please try again.',
        color: 'red',
      })
    },
  })
}
```

---

## 2. React Hook Form + Effect Schema

### Installation

```bash
pnpm add react-hook-form @hookform/resolvers
# @effect/schema already installed from main stack
```

### Pattern: schema → resolver → hook → component

**Step 1 — Define schema in the feature's `types.ts`**

```typescript
// features/users/types.ts
import { Schema } from '@effect/schema'

const CreateUserSchema = Schema.Struct({
  name: Schema.String.pipe(Schema.minLength(2), Schema.maxLength(100)),
  email: Schema.String.pipe(Schema.pattern(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)),
  role: Schema.Literal('admin', 'viewer', 'editor'),
})

type CreateUserFormValues = Schema.Schema.Type<typeof CreateUserSchema>

export { CreateUserSchema }
export type { CreateUserFormValues }
```

**Step 2 — Create a custom Effect Schema resolver**

```typescript
// src/utils/effectSchemaResolver.ts
import { Schema } from '@effect/schema'
import { Effect, pipe } from 'effect'
import type { Resolver } from 'react-hook-form'

const effectSchemaResolver =
  <T>(schema: Schema.Schema<T, unknown>): Resolver<T> =>
  async values =>
    pipe(
      Effect.try(() => Schema.decodeUnknownSync(schema)(values)),
      Effect.match({
        onFailure: error => ({
          values: {},
          errors: Object.fromEntries(
            // map ParseError issues to RHF error shape
            (error as Schema.ParseError).issues?.map(issue => [
              issue.path.join('.'),
              { type: 'validation', message: issue.message },
            ]) ?? [['root', { type: 'validation', message: String(error) }]]
          ),
        }),
        onSuccess: data => ({ values: data as never, errors: {} }),
      }),
      Effect.runPromise
    )

export { effectSchemaResolver }
```

**Step 3 — Encapsulate form logic in a hook**

```typescript
// features/users/hooks/useCreateUserForm.ts
import { useForm } from 'react-hook-form'
import { effectSchemaResolver } from '@/utils/effectSchemaResolver'
import { CreateUserSchema } from '../types'
import { useCreateUser } from './useUserMutation'
import type { CreateUserFormValues } from '../types'

const useCreateUserForm = () => {
  const mutation = useCreateUser()

  const form = useForm<CreateUserFormValues>({
    resolver: effectSchemaResolver(CreateUserSchema),
    defaultValues: { name: '', email: '', role: 'viewer' },
  })

  const onSubmit = form.handleSubmit((values: CreateUserFormValues) => {
    mutation.mutate(values)
  })

  return { form, onSubmit, isPending: mutation.isPending }
}

export { useCreateUserForm }
```

**Step 4 — Component is a pure render tree**

```typescript
// features/users/components/CreateUserForm.tsx
import { TextInput, Select, Button, Stack } from '@mantine/core'
import { Controller } from 'react-hook-form'
import { useCreateUserForm } from '../hooks/useCreateUserForm'

const CreateUserForm = () => {
  const { form, onSubmit, isPending } = useCreateUserForm()
  const { control, formState: { errors } } = form

  return (
    <Stack gap="md" component="form" onSubmit={onSubmit}>
      <Controller
        name="name"
        control={control}
        render={({ field }) => (
          <TextInput
            {...field}
            label="Name"
            error={errors.name?.message}
            required
          />
        )}
      />
      <Controller
        name="email"
        control={control}
        render={({ field }) => (
          <TextInput
            {...field}
            label="Email"
            type="email"
            error={errors.email?.message}
            required
          />
        )}
      />
      <Controller
        name="role"
        control={control}
        render={({ field }) => (
          <Select
            {...field}
            label="Role"
            data={['admin', 'viewer', 'editor']}
            error={errors.role?.message}
          />
        )}
      />
      <Button type="submit" loading={isPending}>
        Create User
      </Button>
    </Stack>
  )
}
export default CreateUserForm
```

---

## 3. Error Boundaries

### Installation

```bash
pnpm add react-error-boundary
```

### Placement rules

| Location | Boundary |
|---|---|
| App root (`main.tsx`) | Catches catastrophic failures |
| Each route-level page | Isolates route errors from the rest of the app |
| Each async data region | Isolates query errors from siblings |

### Standard fallback component

```typescript
// src/components/ErrorFallback/ErrorFallback.tsx
import { Button, Stack, Text, Title } from '@mantine/core'
import type { FallbackProps } from 'react-error-boundary'

const ErrorFallback = ({ error, resetErrorBoundary }: FallbackProps) => (
  <Stack align="center" justify="center" className="min-h-[200px]" gap="md">
    <Title order={4}>Something went wrong</Title>
    <Text size="sm" c="dimmed">{error instanceof Error ? error.message : 'Unknown error'}</Text>
    <Button variant="outline" onClick={resetErrorBoundary}>Try again</Button>
  </Stack>
)
export default ErrorFallback
```

### Route-level usage (wraps every page)

```typescript
// Applied inside the router — see architecture.md
// Each route component wraps its content:

import { ErrorBoundary } from 'react-error-boundary'
import ErrorFallback from '@/components/ErrorFallback/ErrorFallback'

const UsersPage = () => (
  <ErrorBoundary FallbackComponent={ErrorFallback}>
    <UsersPageContent />
  </ErrorBoundary>
)
export default UsersPage

// UsersPageContent is the actual feature content (also one file)
```

### App-root usage

```typescript
// src/main.tsx
import { ErrorBoundary } from 'react-error-boundary'
import ErrorFallback from '@/components/ErrorFallback/ErrorFallback'

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <MantineProvider theme={theme}>
        ...
      </MantineProvider>
    </ErrorBoundary>
  </React.StrictMode>
)
```

### With TanStack Query — `throwOnError`

To let query errors propagate to the nearest ErrorBoundary:

```typescript
// features/users/hooks/useUsers.ts
const useUsers = () =>
  useQuery({
    queryKey: ['users'],
    queryFn: fetchUsersEffect,
    throwOnError: true,  // ← surfaces errors to ErrorBoundary
  })
```

When `throwOnError: true`, remove the `if (error)` branch from the component — the boundary handles it.
