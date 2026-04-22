import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/vitest-setup.ts'],
    include: [
      'tests/**/*.vitest.ts',
      'tests/**/*.vitest.tsx',
      'tests/unit/state-adapters.test.ts',
      'tests/unit/hub-status-deriver.test.ts',
      'tests/unit/module-card.test.tsx',
      'tests/regression/cross-module-invalidation.test.ts',
      'tests/regression/cta-label-consistency.test.tsx',
      'tests/regression/state-machine-transitions.test.ts',
      'tests/integration/api-polling.test.ts',
      'tests/integration/cognito-auth.test.ts',
      'tests/integration/hub-state-integration.test.ts',
    ],
  },
});
