# Stacks, typed config, ComponentResources & outputs

## Stacks = environments

A **stack** is an isolated, independently-configured instance of the same program. Model each
environment as a stack (`dev`, `prod`), never as an `if (env === 'prod')` branch in code.

```bash
pulumi stack init dev          # creates the stack + Pulumi.dev.yaml
pulumi stack select dev
pulumi config set gcp:project my-project-dev
pulumi config set gcp:region europe-west6
pulumi up
```

Per-environment differences (project ID, region, machine sizes, replica counts) live in
`Pulumi.<stack>.yaml`. The program reads them through `pulumi.Config` and adapts — same code, every
environment.

## Typed config: keep parsing pure

Split config into (a) pure, testable helpers and (b) a thin read at the entry point. The helpers have
**no** `pulumi` import, so they unit-test without the runtime.

```typescript
// src/config.ts — pure
export const DEFAULT_REGION = 'europe-west6'

export function resolveRegion(configured: string | undefined): string {
  const trimmed = configured?.trim()
  return trimmed ? trimmed : DEFAULT_REGION
}

export function buildLabels(
  environment: string,
  extra: Record<string, string> = {}
): Record<string, string> {
  // managed-by + environment always present; extra wins on collision
  return { 'managed-by': 'pulumi', environment, ...extra }
}
```

```typescript
// index.ts — reads pulumi.Config, delegates to the pure helpers
const gcpConfig = new pulumi.Config('gcp')
const appConfig = new pulumi.Config()

const environment = appConfig.get('environment') ?? pulumi.getStack()
const region = resolveRegion(gcpConfig.get('region'))
const labels = buildLabels(environment)
```

Config accessors:
- `config.get('k')` → `string | undefined` (optional)
- `config.require('k')` → `string` (fails fast if missing)
- `config.getObject<T>('k')` / `requireObject<T>('k')` → structured values
- `config.getSecret('k')` / `requireSecret('k')` → `Output<string>` for encrypted config

Secrets are set out-of-band and stored encrypted in the stack file:
```bash
pulumi config set --secret dbPassword 's3cr3t'
```
Read them as `Output<string>` and pass straight into resources — never log or `.apply(console.log)` a
secret.

## ComponentResources

Encapsulate a unit of infrastructure so its safe defaults live in exactly one place.

```typescript
export class SecureBucket extends pulumi.ComponentResource {
  readonly bucket: gcp.storage.Bucket
  readonly url: pulumi.Output<string>

  constructor(name: string, args: SecureBucketArgs, opts?: pulumi.ComponentResourceOptions) {
    super('wellforge:gcp:SecureBucket', name, {}, opts)   // 1. namespaced type token

    this.bucket = new gcp.storage.Bucket(name, {
      /* secure defaults */
    }, { parent: this })                                   // 2. children parented to the component

    this.url = pulumi.interpolate`gs://${this.bucket.name}`
    this.registerOutputs({ bucket: this.bucket, url: this.url }) // 3. always registerOutputs
  }
}
```

Rules:
1. **Type token** `<org>:<module>:<Component>` — unique and stable; it appears in state and policy.
2. **Parent every child** with `{ parent: this }` so the resource tree and deletes are correct.
3. **`registerOutputs`** (even `{}`) marks the component complete and surfaces its outputs.
4. Accept `pulumi.Input<T>` for args (callers may pass Outputs); expose `pulumi.Output<T>` fields.

## Working with Outputs

Resource attributes resolve asynchronously — they are `Output<T>`, not plain values.

```typescript
const url = pulumi.interpolate`https://${cdn.domain}/assets`         // string interpolation
const arnUpper = bucket.name.apply(n => n.toUpperCase())            // transform
const combined = pulumi.all([a.id, b.id]).apply(([x, y]) => `${x}:${y}`)  // combine
```

Never `await` an Output, never read a synchronous `.value`. Export what humans or other stacks need:

```typescript
export const assetsBucket = assets.bucket.name   // becomes a stack output
```

## Cross-stack references

Consume another stack's outputs with `StackReference` — never hard-code IDs.

```typescript
const net = new pulumi.StackReference('acme/networking/prod')
const subnetId = net.getOutput('subnetId')
new gcp.compute.Instance('vm', { networkInterfaces: [{ subnetwork: subnetId }] })
```

## Providers (when you need an explicit one)

The default GCP provider reads `gcp:project` / `gcp:region` from config. Only create an explicit
`gcp.Provider` when a stack spans multiple projects/regions, then pass it via
`{ provider }` on the affected resources.
