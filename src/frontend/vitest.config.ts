import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/vitest-setup.ts'],
    include: ['tests/**/*.vitest.ts', 'tests/**/*.vitest.tsx', 'tests/integration/api-polling.test.ts', 'tests/integration/cognito-auth.test.ts'],
  },
});
