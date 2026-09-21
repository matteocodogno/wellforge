// Vitest config as its own file, matching the hono preset and the backends: the `test`
// block does not belong in vite.config.ts, where the vite/vitest type versions have to
// agree for it to compile at all.
import path from 'node:path'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
