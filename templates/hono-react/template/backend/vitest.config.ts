import path from 'node:path'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    setupFiles: ['./src/test/setup.ts'],
    // The DEFAULT lane must stay Docker-free. Without this exclude, vitest's default
    // `**/*.test.ts` swallowed src/db/*.integration.test.ts — which has no Testcontainers
    // setup of its own, because vitest.integration.config.ts owns that — so `mise run
    // test` tried to reach a real database and failed with ECONNREFUSED on a clean
    // machine. Integration tests have exactly one entry point:
    //   mise run backend:test:integration   (vitest.integration.config.ts)
    exclude: ['src/**/*.integration.test.ts', 'node_modules', 'dist'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules',
        'dist',
        '**/*.test.ts',
        '**/*.spec.ts',
        'src/test/**',
        'src/db/migrations/**',
      ],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
