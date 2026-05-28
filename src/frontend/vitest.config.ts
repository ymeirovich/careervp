import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontend_root = dirname(fileURLToPath(import.meta.url));
const repo_root = resolve(frontend_root, '..', '..');

export default defineConfig({
  root: repo_root,
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['src/frontend/tests/vitest-setup.ts', 'src/frontend/tests/ui/setup.ts'],
    include: [
      // Canvas App UI tests (spec-v4)
      'tests/ui/**/*.test.tsx',
      'tests/ui/**/*.test.ts',
      'src/frontend/tests/ui/**/*.test.tsx',
      'src/frontend/tests/ui/**/*.test.ts',
      'src/frontend/tests/**/*.vitest.ts',
      'src/frontend/tests/**/*.vitest.tsx',
      'src/frontend/tests/unit/auth-context.test.tsx',
      'src/frontend/tests/unit/state-adapters.test.ts',
      'src/frontend/tests/unit/hub-status-deriver.test.ts',
      'src/frontend/tests/unit/module-card.test.tsx',
      'src/frontend/tests/regression/cross-module-invalidation.test.ts',
      'src/frontend/tests/regression/cta-label-consistency.test.tsx',
      'src/frontend/tests/regression/state-machine-transitions.test.ts',
      'src/frontend/tests/integration/api-polling.test.ts',
      'src/frontend/tests/integration/cognito-auth.test.ts',
      'src/frontend/tests/integration/hub-state-integration.test.ts',
      'src/frontend/tests/unit/api-methods.test.ts',
      'src/frontend/tests/unit/artifact-storage.test.ts',
      'src/frontend/tests/integration/api-client.test.ts',
      'src/frontend/tests/unit/module-card-actions.test.tsx',
      'src/frontend/tests/integration/hub-state.test.ts',
      'src/frontend/tests/unit/vpr-page.test.tsx',
      'src/frontend/tests/unit/gap-analysis-page.test.tsx',
      'src/frontend/tests/unit/export-dropdown.test.tsx',
    ],
  },
});
