import { fileURLToPath } from 'node:url';

import { defineConfig } from 'vitest/config';

/**
 * Vitest configuration for the frontend unit tests.
 *
 * Resolves the `@/*` path alias (mirrors tsconfig.json) so tests can import
 * application modules the same way the app does, and uses the jsdom
 * environment so component/DOM tests can be added later.
 */
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
});
