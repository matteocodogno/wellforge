# Policy-as-code with CrossGuard

CrossGuard is Pulumi's policy engine. A **policy pack** validates resources at `preview`/`up` time and
can block updates that violate a rule — guardrails enforced by the tool, not by review discipline.
Where unit tests check *your* code's intent, policies check *every* resource against org rules,
including ones a future contributor adds.

## The pack is a separate package

`policy/` is self-contained — its own `package.json`, `tsconfig.json`, and `PulumiPolicy.yaml`. Pulumi
installs and runs it independently when you pass `--policy-pack ./policy`. It is intentionally outside
the infra program's `tsconfig`/Biome/quality-gate: guardrails are exercised at deploy, not by the
unit-test gate.

```
policy/
├── PulumiPolicy.yaml     # name, runtime: nodejs, description
├── package.json          # @pulumi/policy + @pulumi/gcp + @pulumi/pulumi
├── tsconfig.json         # module: commonjs, include: ["index.ts"]
└── index.ts              # the PolicyPack
```

```yaml
# PulumiPolicy.yaml
name: <slug>-policies
runtime: nodejs
description: CrossGuard guardrails for <project> — enforced at preview/up time.
```

```json
// package.json — versions match the SKILL.md table
{
  "name": "<slug>-policies",
  "version": "0.1.0",
  "private": true,
  "main": "index.ts",
  "dependencies": {
    "@pulumi/gcp": "^8.13.0",
    "@pulumi/policy": "^1.21.0",
    "@pulumi/pulumi": "^3.145.0"
  },
  "devDependencies": { "@types/node": "^22.10.5", "typescript": "^5.7.2" }
}
```

## Writing policies

```typescript
import * as gcp from '@pulumi/gcp'
import { PolicyPack, validateResourceOfType } from '@pulumi/policy'

new PolicyPack('<slug>-policies', {
  policies: [
    {
      name: 'gcs-public-access-prevention',
      description: 'GCS buckets must enforce public access prevention.',
      enforcementLevel: 'mandatory',                 // blocks the update
      validateResource: validateResourceOfType(
        gcp.storage.Bucket,
        (bucket, _args, reportViolation) => {
          if (bucket.publicAccessPrevention !== 'enforced') {
            reportViolation('Bucket must set publicAccessPrevention = "enforced".')
          }
        }
      ),
    },
    {
      name: 'gcs-uniform-bucket-level-access',
      description: 'GCS buckets must use uniform bucket-level access (no per-object ACLs).',
      enforcementLevel: 'mandatory',
      validateResource: validateResourceOfType(
        gcp.storage.Bucket,
        (bucket, _args, reportViolation) => {
          if (bucket.uniformBucketLevelAccess !== true) {
            reportViolation('Bucket must enable uniformBucketLevelAccess.')
          }
        }
      ),
    },
    {
      name: 'require-environment-label',
      description: 'Labelled resources should carry an "environment" label for cost + ownership.',
      enforcementLevel: 'advisory',                  // warns only
      validateResource: (args, reportViolation) => {
        const labels = (args.props as { labels?: Record<string, string> }).labels
        if (labels && labels.environment === undefined) {
          reportViolation('Resource is missing the "environment" label.')
        }
      },
    },
  ],
})
```

- **`validateResourceOfType(Type, fn)`** narrows to one resource type with typed props — prefer it
  over a raw `validateResource` when the rule targets a specific resource.
- **`validateResource(args, report)`** sees every resource; read `args.type` / `args.props` for
  cross-cutting rules (labels, naming, tags).
- **`validateStack(args, report)`** (not shown) runs once with all resources — use it for
  relationships (e.g. "every bucket must have a corresponding log sink").

## Enforcement levels

| Level | Effect |
|---|---|
| `mandatory` | Violation **fails** `preview`/`up` — the update is blocked. |
| `advisory` | Violation prints a warning; the update proceeds. |
| `disabled` | Rule is skipped. |

Start new rules `advisory`, watch real runs, then promote to `mandatory` once clean — the same
defer-don't-lower spirit as WellForge rigor tiers.

## Running it

```bash
pulumi preview --policy-pack ./policy      # mise run infra:policy
pulumi up --policy-pack ./policy           # enforce on deploy
```

Wire `--policy-pack ./policy` into the deploy workflow so **no** stack can be updated past the
guardrails, including changes that skipped local checks. For org-wide reuse, publish the pack to
Pulumi Cloud (`pulumi policy publish`) and enforce it across every stack from a policy group instead
of committing it per-repo.
