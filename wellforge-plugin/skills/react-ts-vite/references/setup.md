# Setup Reference — Tooling & Environment

## 1. Environment Variables

### The rule
Every env var exposed to the browser **must** be prefixed `VITE_`. Vite statically replaces them at build time via `import.meta.env`. Never use `process.env` in frontend code.

### Files
```
.env                  # committed — defaults only, no secrets
.env.local            # git-ignored — local overrides
.env.development      # git-ignored — dev secrets
.env.production       # git-ignored — prod secrets
```

### Typing `import.meta.env`

Create `src/vite-env.d.ts` (extends Vite's default triple-slash reference):

```typescript
/// <reference types="vite/client" />

type ImportMetaEnv = {
  readonly VITE_API_BASE_URL: string
  readonly VITE_APP_NAME: string
  readonly VITE_FEATURE_FLAG_NEW_DASHBOARD: 'true' | 'false'
  // add every VITE_ var used in the codebase here
}

type ImportMeta = {
  readonly env: ImportMetaEnv
}
```

TypeScript will now enforce that only declared vars are accessed, and they are typed — no more `string | undefined` surprises.

### Accessing env vars

```typescript
// ✅ Correct — typed, via a central config module
// src/config.ts
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL,
  appName: import.meta.env.VITE_APP_NAME,
  featureNewDashboard: import.meta.env.VITE_FEATURE_FLAG_NEW_DASHBOARD === 'true',
} as const

// In consuming code
import { config } from '@/config'
const url = `${config.apiBaseUrl}/users`

// ❌ Never scatter import.meta.env across files
fetch(`${import.meta.env.VITE_API_BASE_URL}/users`)
```

Always access env vars through `src/config.ts`. This gives one place to audit, mock in tests, and add runtime validation.

### Runtime validation (optional but recommended)

```typescript
// src/config.ts
import { Schema } from '@effect/schema'
import { Effect, pipe } from 'effect'

const EnvSchema = Schema.Struct({
  VITE_API_BASE_URL: Schema.String.pipe(Schema.nonEmpty()),
  VITE_APP_NAME: Schema.String.pipe(Schema.nonEmpty()),
})

const parseEnv = pipe(
  Effect.try(() => Schema.decodeUnknownSync(EnvSchema)(import.meta.env)),
  Effect.mapError(e => new Error(`Invalid env config: ${e}`)),
  Effect.runSync
)

export const config = {
  apiBaseUrl: parseEnv.VITE_API_BASE_URL,
  appName: parseEnv.VITE_APP_NAME,
} as const
```

This crashes at startup (not silently at runtime) if a required var is missing.

---

## 2. ESLint

### Installation

```bash
pnpm add -D eslint @eslint/js typescript-eslint eslint-plugin-react-hooks eslint-plugin-react-refresh
```

### `eslint.config.ts` (flat config)

```typescript
import js from '@eslint/js'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist', 'node_modules'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.strictTypeChecked],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parserOptions: {
        project: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      // React Hooks
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],

      // Enforce skill conventions
      '@typescript-eslint/consistent-type-definitions': ['error', 'type'],
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/explicit-function-return-type': 'off', // inferred is fine
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],

      // Functional patterns
      'prefer-const': 'error',
      'no-var': 'error',
    },
  }
)
```

---

## 3. Prettier

### Installation

```bash
pnpm add -D prettier prettier-plugin-tailwindcss
```

### `.prettierrc`

```json
{
  "semi": false,
  "singleQuote": true,
  "trailingComma": "es5",
  "printWidth": 100,
  "tabWidth": 2,
  "plugins": ["prettier-plugin-tailwindcss"]
}
```

`prettier-plugin-tailwindcss` auto-sorts Tailwind class names — always include it.

### `.prettierignore`

```
dist
node_modules
*.skill
```

---

## 4. lint-staged + husky

Run linting and formatting only on staged files — never on the entire project.

### Installation

```bash
pnpm add -D husky lint-staged
pnpm exec husky init
```

### `package.json` additions

```json
{
  "scripts": {
    "prepare": "husky"
  },
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix --max-warnings 0",
      "prettier --write"
    ],
    "*.{json,md,yml,yaml}": [
      "prettier --write"
    ]
  }
}
```

### `.husky/pre-commit`

```bash
#!/bin/sh
pnpm exec lint-staged
```

### `.husky/commit-msg` (optional — conventional commits)

```bash
#!/bin/sh
pnpm exec commitlint --edit "$1"
```

---

## 5. Full `package.json` scripts block

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint . --max-warnings 0",
    "lint:fix": "eslint . --fix",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "type-check": "tsc --noEmit",
    "prepare": "husky"
  }
}
```

Run `pnpm lint && pnpm type-check` in CI. Never commit with lint errors (`--max-warnings 0`).
