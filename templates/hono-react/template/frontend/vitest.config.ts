// Vitest config lives HERE, not in vite.config.ts — the same split the backend already
// uses. Keeping a `test` block inside vite.config.ts cannot type-check with this preset's
// pins: vite is ^6 while vitest is ^2, and vitest 2 carries its own vite 5, so
// `defineConfig` from `vitest/config` types the config against vite 5 while
// `@vitejs/plugin-react` returns a vite 6 Plugin. Measured, both ways round:
//   defineConfig from 'vite'          → TS2769, "'test' does not exist in UserConfigExport"
//   defineConfig from 'vitest/config' → TS2769, vite 5 Plugin vs vite 6 Plugin
// A triple-slash `/// <reference types="vitest" />` does not augment the type either.
// Splitting the files removes the conflict without touching the pins — bumping vitest to
// ^3 is specs/003-ts-stack-migration, not a side effect of a formatting fix.
import path from 'node:path'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
