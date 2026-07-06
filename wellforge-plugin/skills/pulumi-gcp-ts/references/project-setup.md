# Project setup, tooling & pinned versions

The `pulumi-gcp-ts` Copier preset generates all of this. Hand-build only when a preset isn't an
option; keep versions in sync with the SKILL.md table (the source of truth).

## `package.json` (the `infra/` program)

CommonJS — **no** `"type": "module"`. Pulumi's Node runtime loads the program via ts-node and an ESM
entry point fails at `pulumi up`.

```json
{
  "name": "<slug>-infra",
  "version": "0.1.0",
  "private": true,
  "main": "index.ts",
  "scripts": {
    "build": "tsc --noEmit",
    "typecheck": "tsc --noEmit",
    "lint": "biome check .",
    "lint:fix": "biome check --write .",
    "format": "biome format --write .",
    "test": "vitest",
    "test:coverage": "vitest --coverage"
  },
  "dependencies": {
    "@pulumi/gcp": "^8.13.0",
    "@pulumi/pulumi": "^3.145.0"
  },
  "devDependencies": {
    "@biomejs/biome": "^1.9.4",
    "@types/node": "^22.10.5",
    "@vitest/coverage-v8": "^2.1.8",
    "typescript": "^5.7.2",
    "vitest": "^2.1.8"
  },
  "engines": { "node": ">=20.0.0", "pnpm": ">=9.0.0" }
}
```

`build` is a compile check (`--noEmit`) — a Pulumi program is never bundled to `dist/`, the CLI runs
the TS directly. `lint` / `typecheck` / `test` are exactly what the WellForge `quality-node.yml` gate
invokes, so the gate works on the `infra` working-directory with no special-casing.

## `tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "moduleResolution": "node",
    "lib": ["ES2020"],
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noImplicitReturns": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "sourceMap": true,
    "outDir": "bin"
  },
  "include": ["index.ts", "src/**/*"],
  "exclude": ["node_modules", "bin", "policy", "**/*.test.ts"]
}
```

`policy/` is excluded — it is a **separate package** with its own `tsconfig.json` (see
`policy-as-code.md`). Test files are excluded from `tsc` (vitest transpiles them via esbuild).

## `Pulumi.yaml` and per-stack config

```yaml
# Pulumi.yaml — the project
name: <slug>
runtime: nodejs
description: <one line>
```

```yaml
# Pulumi.dev.yaml — one file per stack. Non-secret values only.
# Secrets:  pulumi config set --secret <key> <value>
config:
  gcp:project: <gcp-project-id>
  gcp:region: europe-west6
  <slug>:environment: dev
```

Provider config uses the `gcp:` namespace; app config uses the project name as namespace
(`<slug>:environment`). Never put secrets in these YAML files — encrypted config lands here as
ciphertext only via `pulumi config set --secret`.

## mise tasks (`infra/mise.toml`)

Tools (node, pnpm, pulumi) are pinned in the **root** `mise.toml`; the infra file only defines tasks:

```toml
[tasks.install]   # pnpm install
[tasks.build]     # pnpm build      (tsc --noEmit)
[tasks.typecheck] # pnpm typecheck
[tasks.test]      # pnpm test --run
[tasks.lint]      # pnpm lint        (biome check)
[tasks.preview]   # pulumi preview
[tasks.up]        # pulumi up
[tasks.destroy]   # pulumi destroy
[tasks.refresh]   # pulumi refresh
[tasks.policy]    # pulumi preview --policy-pack ./policy
```

Root aggregates map `install/build/test/lint` to `infra:*` and `dev` → `infra:preview` (a preview is
the closest read-only "run this locally" for infrastructure).

## Biome

Reuse the WellForge TS Biome config (single quotes, no semicolons, 2-space, 100 cols,
`noExplicitAny: error`, `noUnusedVariables: error`). Add `policy` and `bin` to `files.ignore` — the
policy pack manages its own quality and generated output must not be linted.

## `.gitignore` essentials

```
node_modules/
bin/
coverage/
*.tsbuildinfo
Pulumi.*.local.yaml       # per-developer stack overrides
.pulumi/
credentials.json          # backstop — you should be using ADC / WIF, not key files
gcp-key*.json
```
