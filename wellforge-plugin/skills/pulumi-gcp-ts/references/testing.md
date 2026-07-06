# Testing Pulumi programs with mocks

Pulumi unit tests run the program against a **mock runtime** — no cloud calls, no credentials, fast
enough for every PR. They assert the *inputs* your program produces: secure defaults, labels, naming,
wiring. This is the deterministic half; `pulumi preview` covers end-to-end plan correctness.

## Vitest config

Measure coverage over `src/**` only — `index.ts` is the composition root (exercised by `preview`,
not unit tests).

```typescript
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/**/*.ts'],
      exclude: ['**/*.test.ts', '**/*.spec.ts'],
    },
  },
})
```

## Set mocks before importing resources

`setMocks` must run **before** any module that constructs resources is loaded — so import the module
under test with a dynamic `import()` *inside* the test (top-level `import` would load it too early).

```typescript
import * as pulumi from '@pulumi/pulumi'
import { describe, expect, it } from 'vitest'

pulumi.runtime.setMocks({
  newResource: (args: pulumi.runtime.MockResourceArgs) => ({
    id: `${args.name}-id`,
    // Echo inputs back as state; surface the logical name so `.name` resolves deterministically.
    state: { ...args.inputs, name: args.name },
  }),
  call: () => ({}),   // stub provider function calls (getProject, getZones, ...)
})

// Resolve an Output<T> to a plain value in tests.
const value = <T>(o: pulumi.Output<T>): Promise<T> =>
  new Promise(resolve => o.apply(resolve))
```

## Asserting a component's inputs

```typescript
describe('SecureBucket', () => {
  it('enforces secure defaults', async () => {
    const { SecureBucket } = await import('./gcs-bucket')
    const b = new SecureBucket('data', { location: 'EU', labels: { environment: 'dev' } })

    expect(await value(b.bucket.uniformBucketLevelAccess)).toBe(true)
    expect(await value(b.bucket.publicAccessPrevention)).toBe('enforced')
    expect(await value(b.bucket.versioning)).toEqual({ enabled: true })
    expect(await value(b.url)).toBe('gs://data')
  })

  it('honours explicit overrides', async () => {
    const { SecureBucket } = await import('./gcs-bucket')
    const b = new SecureBucket('scratch', { location: 'EU', versioning: false, forceDestroy: true })
    expect(await value(b.bucket.versioning)).toEqual({ enabled: false })
    expect(await value(b.bucket.forceDestroy)).toBe(true)
  })
})
```

Why `state: { ...args.inputs, name: args.name }`? Under mocks, a resource's outputs come from the
`state` you return. Echoing `inputs` lets you assert what the program *set*; adding `name` makes
`bucket.name` (and any `pulumi.interpolate` built from it) resolve to the logical name instead of
`undefined`.

## Testing pure helpers directly

No runtime needed — plain functions, plain assertions. This is where most branch coverage comes from.

```typescript
import { DEFAULT_REGION, buildLabels, resolveRegion } from './config'

it('falls back to the default region when blank', () => {
  expect(resolveRegion('   ')).toBe(DEFAULT_REGION)
})

it('lets extra labels override the defaults', () => {
  expect(buildLabels('dev', { environment: 'override' }).environment).toBe('override')
})
```

## What mocks do and don't cover

- ✅ Resource **inputs** (properties you set), component structure, naming, label propagation.
- ✅ Pure config/transform logic.
- ❌ Whether the cloud accepts the plan, IAM correctness end-to-end, drift. Those belong to
  `pulumi preview` in CI (keyless, via Workload Identity Federation) and to the CrossGuard policy
  pack — see `policy-as-code.md`.

## The `call` mock

Provider *functions* (`gcp.organizations.getProject`, `gcp.compute.getZones`, …) go through `call`.
Return canned data keyed on `args.token` when a resource under test invokes one:

```typescript
call: (args: pulumi.runtime.MockCallArgs) => {
  if (args.token === 'gcp:organizations/getProject:getProject') {
    return { projectId: 'test-project', number: '1234567890' }
  }
  return {}
}
```
