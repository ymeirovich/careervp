import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [
      './tests/vitest-setup.ts',
      './tests/ui/setup.ts',
    ],
    include: [
      // Canvas App UI tests (spec-v4)
      // All paths are relative to src/frontend (this config's directory).
      // Spec tests live at src/frontend/tests/ui/ — matched by tests/ui/**
      // Repo-root tests/ui/ stubs are intentionally excluded (outside this root).
      'tests/ui/**/*.test.tsx',
      'tests/ui/**/*.test.ts',
      'tests/**/*.vitest.ts',
      'tests/**/*.vitest.tsx',
      'tests/unit/auth-context.test.tsx',
      'tests/unit/state-adapters.test.ts',
      'tests/unit/hub-status-deriver.test.ts',
      'tests/unit/module-card.test.tsx',
      'tests/regression/cross-module-invalidation.test.ts',
      'tests/regression/cta-label-consistency.test.tsx',
      'tests/regression/state-machine-transitions.test.ts',
      'tests/integration/api-polling.test.ts',
      'tests/integration/cognito-auth.test.ts',
      'tests/integration/hub-state-integration.test.ts',
      'tests/unit/api-methods.test.ts',
      'tests/unit/artifact-storage.test.ts',
      'tests/integration/api-client.test.ts',
      'tests/unit/module-card-actions.test.tsx',
      'tests/integration/hub-state.test.ts',
      'tests/unit/vpr-page.test.tsx',
      'tests/unit/gap-analysis-page.test.tsx',
      'tests/unit/export-dropdown.test.tsx',
    ],
  },
});
