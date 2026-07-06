---
name: pulumi-gcp-ts
description: >
  Pulumi Infrastructure-as-Code in TypeScript on Google Cloud — best practices AND scaffolding a
  new IaC project from scratch (the **Pulumi / GCP / TypeScript path**). Use whenever building or
  reviewing Pulumi TS programs for GCP, OR scaffolding a new infrastructure project ("new Pulumi
  project", "set up infrastructure as code", "provision GCP with Pulumi", "IaC for this service").
  Covers project + stack layout, typed config, `ComponentResource` abstractions, CrossGuard
  policy-as-code, unit testing with Pulumi mocks, the keyless credential model (ADC + Workload
  Identity Federation), and state backends. Trigger for any Pulumi TS task — even "add a bucket",
  "create a component", "write a policy", or "add a stack". FIRST confirm the target: this is
  **infrastructure** (Pulumi), not an application backend — for a Hono API use `hono-ts-backend`,
  for Spring use `springboot-scaffold`. This skill is the source of truth for the `pulumi-gcp-ts`
  Copier preset (`templates/pulumi-gcp-ts/`); pinned versions here and in the template must match.
---

# Pulumi + TypeScript on GCP — Best Practices

Opinionated guide for production-grade Infrastructure-as-Code with Pulumi (TypeScript) on Google
Cloud. This is the **IaC path** — it provisions cloud resources, it is not an application runtime.

## Scaffolding a new IaC project (from scratch)

This skill backs the **`pulumi-gcp-ts` WellForge Copier preset**. Prefer generating the whole
project via `/wellforge:new` (or `copier copy … --data preset=pulumi-gcp-ts`) rather than hand-rolling
files — that gets you the CONTRACT-compliant wiring (manifest, mise tasks, quality gate, heartbeat)
for free. Confirm the target before scaffolding:

- **Is this infrastructure or an app?** Pulumi defines *cloud resources*. If the ask is a REST API /
  service, **STOP** and use `hono-ts-backend` (TS) or `springboot-scaffold` (JVM) instead.
- **Cloud + language.** This skill is GCP + TypeScript. A different cloud or language means a
  different provider package and a different preset — do not force GCP/TS here.
- **Brownfield:** if the repo already has a Pulumi program, match its stack layout and config
  conventions; extend, don't re-scaffold.

For deep reference on a specific area, read the matching file in `references/`:

| Topic | File |
|---|---|
| Project setup, tooling, pinned versions, mise tasks | `references/project-setup.md` |
| Stacks, typed config, ComponentResources, outputs | `references/stacks-and-components.md` |
| Testing with Pulumi mocks | `references/testing.md` |
| Policy-as-code (CrossGuard) | `references/policy-as-code.md` |

---

## Core Principles

- **Infrastructure is a program.** Real TypeScript — reuse via functions and
  `ComponentResource`s, not copy-paste YAML. Keep it strict (`strict: true`, no `any`).
- **One program, many stacks.** A *stack* is an isolated instance of the infrastructure
  (`dev`, `prod`). Never branch on environment with `if` in code — put per-environment values in
  `Pulumi.<stack>.yaml` and read them through config. Select with `pulumi stack select`.
- **Config, not constants.** Provider settings (`gcp:project`, `gcp:region`) and app values live in
  stack config. Config *parsing* logic lives in pure, unit-testable functions; the entry point reads
  `pulumi.Config` and passes plain values in.
- **Secrets are encrypted config** — `pulumi config set --secret <key> <value>`. Never in code,
  `.env`, or plain YAML. Never commit a service-account key.
- **ComponentResources encode safe defaults once.** Wrap related resources with a namespaced type
  token (`wellforge:gcp:SecureBucket`), pass `{ parent: this }`, call `registerOutputs`. Callers
  can't forget a control the policy pack requires.
- **Outputs are `Output<T>`, not values.** Compose with `.apply()` / `pulumi.interpolate` /
  `pulumi.all`. Never `await` an Output or read a raw `.value`.
- **Guardrails as code.** Ship a CrossGuard policy pack and enforce it on every `preview`/`up`.
- **Keyless auth.** Local: Application Default Credentials. CI: Workload Identity Federation. No
  long-lived key files, ever.
- **Test with mocks.** `pulumi.runtime.setMocks` asserts the *inputs* your program produces with
  zero cloud calls, on every PR.

---

## Pinned versions (source of truth)

The `pulumi-gcp-ts` template mirrors these — keep them in sync.

| Layer | Tech | Version |
|---|---|---|
| Runtime | Node | 22 |
| Package manager | pnpm | 10 |
| IaC engine | Pulumi CLI | 3 |
| Pulumi SDK | `@pulumi/pulumi` | ^3.145.0 |
| GCP provider | `@pulumi/gcp` | ^8.13.0 |
| Policy (CrossGuard) | `@pulumi/policy` | ^1.21.0 |
| Lint/format | `@biomejs/biome` | ^1.9.4 |
| Tests | `vitest` + `@vitest/coverage-v8` | ^2.1.8 |
| TypeScript | `typescript` | ^5.7.2 |

> **Runtime is CommonJS, not ESM.** Pulumi's Node runtime loads the program via ts-node; use
> `module: commonjs` in `tsconfig.json` and do **not** set `"type": "module"` in `package.json`.
> ESM entry points fail at `pulumi up`. (Vitest/Biome are happy either way.)

**Read `references/project-setup.md`** for the full `package.json`, `tsconfig.json`, mise tasks, and
scripts (`lint` / `typecheck` / `test` are what the WellForge `quality-node.yml` gate runs).

---

## Architecture Overview

```
infra/
├── Pulumi.yaml               ← project definition (name, runtime: nodejs)
├── Pulumi.dev.yaml           ← dev stack config (gcp:project, gcp:region, <project>:environment)
├── Pulumi.prod.yaml          ← prod stack config
├── index.ts                  ← THIN entry point: read config → wire components → export outputs
├── src/
│   ├── config.ts             ← PURE, unit-tested helpers (resolveRegion, buildLabels)
│   └── components/           ← reusable ComponentResources (SecureBucket example)
│       └── gcs-bucket.ts
├── policy/                   ← CrossGuard policy pack (self-contained package)
│   ├── PulumiPolicy.yaml
│   ├── package.json
│   └── index.ts
├── mise.toml                 ← install/build/test/lint + preview/up/destroy/refresh/policy
├── biome.json / tsconfig.json / vitest.config.ts
└── package.json
```

Keep `index.ts` a thin composition root (excluded from coverage; covered by `pulumi preview`). Put
anything reusable or testable in `src/`.

---

## Stacks & typed config (Quick Reference)

**Read `references/stacks-and-components.md`** for the full pattern.

```typescript
// index.ts — read config, pass plain values into pure helpers + components
import * as pulumi from '@pulumi/pulumi'
import { SecureBucket } from './src/components/gcs-bucket'
import { buildLabels, resolveRegion } from './src/config'

const gcpConfig = new pulumi.Config('gcp')
const appConfig = new pulumi.Config()

const environment = appConfig.get('environment') ?? pulumi.getStack()
const region = resolveRegion(gcpConfig.get('region'))
const labels = buildLabels(environment)

const assets = new SecureBucket('assets', { location: region, labels })

export const assetsBucket = assets.bucket.name
export const assetsBucketUrl = assets.url
```

```typescript
// src/config.ts — PURE helpers, no pulumi import, fully unit-testable
export const DEFAULT_REGION = 'europe-west6'

export function resolveRegion(configured: string | undefined): string {
  const trimmed = configured?.trim()
  return trimmed ? trimmed : DEFAULT_REGION
}

export function buildLabels(
  environment: string,
  extra: Record<string, string> = {}
): Record<string, string> {
  return { 'managed-by': 'pulumi', environment, ...extra }
}
```

---

## ComponentResources (Quick Reference)

Wrap related resources so secure defaults live in one place:

```typescript
import * as gcp from '@pulumi/gcp'
import * as pulumi from '@pulumi/pulumi'

export interface SecureBucketArgs {
  location: pulumi.Input<string>
  labels?: pulumi.Input<Record<string, string>>
  versioning?: boolean
  forceDestroy?: boolean
}

export class SecureBucket extends pulumi.ComponentResource {
  readonly bucket: gcp.storage.Bucket
  readonly url: pulumi.Output<string>

  constructor(name: string, args: SecureBucketArgs, opts?: pulumi.ComponentResourceOptions) {
    super('wellforge:gcp:SecureBucket', name, {}, opts)

    this.bucket = new gcp.storage.Bucket(name, {
      location: args.location,
      labels: args.labels,
      uniformBucketLevelAccess: true,       // no per-object ACLs
      publicAccessPrevention: 'enforced',   // never public
      forceDestroy: args.forceDestroy ?? false,
      versioning: { enabled: args.versioning ?? true },
      softDeletePolicy: { retentionDurationSeconds: 604800 }, // 7-day recovery window
    }, { parent: this })

    this.url = pulumi.interpolate`gs://${this.bucket.name}`
    this.registerOutputs({ bucket: this.bucket, url: this.url })
  }
}
```

- Namespaced type token `<org>:<service>:<Component>`.
- Every child gets `{ parent: this }`.
- Always `registerOutputs` (even `{}`) — it marks the component complete.
- Cross-stack wiring uses `StackReference`, never hard-coded IDs.

---

## Testing with Pulumi mocks (Quick Reference)

**Read `references/testing.md`** for the full pattern.

```typescript
import * as pulumi from '@pulumi/pulumi'
import { describe, expect, it } from 'vitest'

pulumi.runtime.setMocks({
  newResource: (args: pulumi.runtime.MockResourceArgs) => ({
    id: `${args.name}-id`,
    state: { ...args.inputs, name: args.name },
  }),
  call: () => ({}),
})

const value = <T>(o: pulumi.Output<T>): Promise<T> =>
  new Promise(resolve => o.apply(resolve))

describe('SecureBucket', () => {
  it('enforces secure defaults', async () => {
    const { SecureBucket } = await import('./gcs-bucket') // import AFTER setMocks
    const b = new SecureBucket('data', { location: 'EU' })
    expect(await value(b.bucket.publicAccessPrevention)).toBe('enforced')
    expect(await value(b.bucket.uniformBucketLevelAccess)).toBe(true)
  })
})
```

- Call `setMocks` **before** importing any module that constructs resources (dynamic `import()`).
- Assert the *inputs* (secure defaults, labels, naming) — mocks echo inputs back as state.
- Test pure helpers (`src/config.ts`) directly. Coverage is measured over `src/**`; `index.ts` is
  the composition root, exercised by `pulumi preview`, not unit tests.

---

## Policy-as-code — CrossGuard (Quick Reference)

**Read `references/policy-as-code.md`** for the full pack.

`policy/` is a **self-contained** package (its own `package.json` + `PulumiPolicy.yaml`) enforcing
guardrails at plan time. `mandatory` violations block the update; `advisory` only warn.

```typescript
import * as gcp from '@pulumi/gcp'
import { PolicyPack, validateResourceOfType } from '@pulumi/policy'

new PolicyPack('policies', {
  policies: [{
    name: 'gcs-public-access-prevention',
    description: 'GCS buckets must enforce public access prevention.',
    enforcementLevel: 'mandatory',
    validateResource: validateResourceOfType(gcp.storage.Bucket, (bucket, _args, report) => {
      if (bucket.publicAccessPrevention !== 'enforced') {
        report('Bucket must set publicAccessPrevention = "enforced".')
      }
    }),
  }],
})
```

Run it: `pulumi preview --policy-pack ./policy` (mise task `infra:policy`). Wire it into the deploy
workflow so no stack updates past the guardrails. The pack manages its own deps and sits outside the
unit-test quality gate — guardrails are exercised at deploy.

---

## Credentials & deploying

- **No key files, ever.** Local: `gcloud auth application-default login` (ADC). CI: **Workload
  Identity Federation** — the GitHub Actions OIDC token is exchanged for short-lived GCP credentials;
  no `credentials.json` secret. Git-ignore `credentials.json` / `gcp-key*.json` as a backstop.
- **State backend.** Default is Pulumi Cloud (`pulumi login`). To self-host, use a GCS backend
  (`pulumi login gs://<state-bucket>`) — create that bucket out-of-band with versioning on.
- **Flow.** PR → `pulumi preview` (the plan is the review artifact). Merge → `pulumi up` against the
  target stack **with `--policy-pack ./policy`**. Keep deploy in a **separate** workflow from the
  quality gate so PR CI stays keyless.

---

## Style Rules

- **Strict TypeScript, no `any`** — let inference work; type Args interfaces explicitly.
- **Pure functions for config logic** — no `pulumi` import in `src/config.ts` so it's unit-testable.
- **Thin `index.ts`** — read config, wire components, export outputs; no business logic.
- **ComponentResource for anything reused** — namespaced token, `{ parent: this }`, `registerOutputs`.
- **Never `await` an Output** — compose with `.apply` / `pulumi.interpolate` / `pulumi.all`.
- **Explicit resource names + a consistent `labels` map** (`managed-by` + `environment` minimum).
- **Secrets via `--secret` config**, references via `StackReference` — never hard-coded IDs or keys.
- **CommonJS** module output (`module: commonjs`, no `"type": "module"`).

---

## Quick Start Checklist

When starting a new Pulumi GCP TypeScript project:

- [ ] Scaffold via `/wellforge:new` → preset `pulumi-gcp-ts` (interview sets `gcp_project`/`gcp_region`)
- [ ] `mise install` (node, pnpm, pulumi) then `mise run install`
- [ ] `gcloud auth application-default login` (ADC — no key files)
- [ ] `pulumi stack init dev` / `pulumi stack init prod`; set config in `Pulumi.<stack>.yaml`
- [ ] Model reusable infra as `ComponentResource`s under `src/components/` with secure defaults
- [ ] Keep config parsing pure in `src/config.ts`; keep `index.ts` a thin composition root
- [ ] Write mock-based unit tests (`setMocks`) for components + direct tests for config helpers
- [ ] Extend the CrossGuard pack in `policy/`; run `mise run infra:policy`
- [ ] `mise run lint && mise run typecheck && mise run test` — the quality gate
- [ ] Wire a keyless deploy workflow (Workload Identity Federation) separate from the quality gate
- [ ] `pulumi preview` on PRs; `pulumi up --policy-pack ./policy` on merge
