import type { Config } from 'jest';

const config: Config = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/tests'],
  testMatch: [
    '**/*.test.ts',
  ],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
  transform: {
    '^.+\\.ts$': 'ts-jest',
  },
  setupFiles: ['<rootDir>/tests/setup.ts'],
  collectCoverageFrom: [
    'tests/**/*.test.ts',
    '!tests/payloads/**',
  ],
  coverageDirectory: 'coverage',
  verbose: true,
  testTimeout: 30000,
  projects: [
    {
      displayName: 'unit',
      testMatch: ['<rootDir>/tests/unit/**/*.test.ts'],
      testPathIgnorePatterns: [
        '<rootDir>/tests/unit/state-adapters.test.ts',
        '<rootDir>/tests/unit/hub-status-deriver.test.ts',
      ],
      transform: { '^.+\\.ts$': 'ts-jest' },
      testEnvironment: 'node',
    },
    {
      displayName: 'integration',
      testMatch: ['<rootDir>/tests/integration/**/*.test.ts'],
      testPathIgnorePatterns: [
        '<rootDir>/tests/integration/cognito-auth.test.ts',
        '<rootDir>/tests/integration/api-polling.test.ts',
        '<rootDir>/tests/integration/hub-state-integration.test.ts',
      ],
      transform: { '^.+\\.ts$': 'ts-jest' },
      testEnvironment: 'node',
    },
    {
      displayName: 'e2e',
      testMatch: ['<rootDir>/tests/e2e/**/*.test.ts'],
      transform: { '^.+\\.ts$': 'ts-jest' },
      testEnvironment: 'node',
    },
    {
      displayName: 'regression',
      testMatch: ['<rootDir>/tests/regression/**/*.test.ts'],
      testPathIgnorePatterns: [
        '<rootDir>/tests/regression/state-machine-transitions.test.ts',
        '<rootDir>/tests/regression/cross-module-invalidation.test.ts',
        '<rootDir>/tests/regression/cta-label-consistency.test.tsx',
      ],
      transform: { '^.+\\.ts$': 'ts-jest' },
      testEnvironment: 'node',
    },
    {
      displayName: 'critical',
      testMatch: [
        '<rootDir>/tests/unit/backward-compat-*.test.ts',
        '<rootDir>/tests/unit/webhook-out-of-order*.test.ts',
        '<rootDir>/tests/unit/webhook-stale-data*.test.ts',
        '<rootDir>/tests/unit/lifecycle-trial-no-restart.test.ts',
        '<rootDir>/tests/unit/observability-*.test.ts',
        '<rootDir>/tests/integration/concurrent-checkout.integration.test.ts',
        '<rootDir>/tests/integration/race-condition-*.integration.test.ts',
        '<rootDir>/tests/integration/stripe-*.integration.test.ts',
        '<rootDir>/tests/integration/partial-failure-*.integration.test.ts',
        '<rootDir>/tests/integration/subscription-cache-stale.integration.test.ts',
        '<rootDir>/tests/integration/state-*.integration.test.ts',
        '<rootDir>/tests/integration/lifecycle-resubscribe-*.integration.test.ts',
      ],
      transform: { '^.+\\.ts$': 'ts-jest' },
      testEnvironment: 'node',
    },
    {
      displayName: 'perf',
      testMatch: ['<rootDir>/tests/perf/**/*.test.ts'],
      transform: { '^.+\\.ts$': 'ts-jest' },
      testEnvironment: 'node',
    },
    {
      displayName: 'ops',
      testMatch: ['<rootDir>/tests/ops/**/*.test.ts'],
      transform: { '^.+\\.ts$': 'ts-jest' },
      testEnvironment: 'node',
    },
    {
      displayName: 'security',
      testMatch: ['<rootDir>/tests/security/**/*.test.ts'],
      transform: { '^.+\\.ts$': 'ts-jest' },
      testEnvironment: 'node',
    },
  ],
};

export default config;
