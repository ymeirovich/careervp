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
  setupFilesAfterSetup: ['<rootDir>/tests/setup.ts'],
  collectCoverageFrom: [
    'tests/**/*.test.ts',
    '!tests/payloads/**',
  ],
  coverageDirectory: 'coverage',
  verbose: true,
  testTimeout: 30000,
  // Group tests by type
  projects: [
    {
      displayName: 'unit',
      testMatch: ['<rootDir>/tests/unit/**/*.test.ts'],
      transform: { '^.+\\.ts$': 'ts-jest' },
      testEnvironment: 'node',
    },
    {
      displayName: 'integration',
      testMatch: ['<rootDir>/tests/integration/**/*.test.ts'],
      transform: { '^.+\\.ts$': 'ts-jest' },
      testEnvironment: 'node',
    },
    {
      displayName: 'e2e',
      testMatch: ['<rootDir>/tests/e2e/**/*.test.ts'],
      transform: { '^.+\\.ts$': 'ts-jest' },
      testEnvironment: 'node',
      testTimeout: 60000,
    },
    {
      displayName: 'regression',
      testMatch: ['<rootDir>/tests/regression/**/*.test.ts'],
      transform: { '^.+\\.ts$': 'ts-jest' },
      testEnvironment: 'node',
    },
  ],
};

export default config;
