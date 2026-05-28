/**
 * Playwright configuration for CareerVP UI upgrade e2e tests.
 *
 * Tests live at: tests/e2e/
 * Auth state:    tests/e2e/.auth/user.json  (gitignored)
 *
 * BASE_URL is set by the e2e-smoke GitHub Actions workflow.
 * For local runs: BASE_URL=https://ui-upgrade.<app-id>.amplifyapp.com npx playwright test
 */

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",

  // Run test files sequentially — auth state is shared across workers
  fullyParallel: false,

  // Fail fast in CI on first failure (set retries=1 to allow one re-run)
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,

  // 2 workers in CI; 1 locally to avoid auth race conditions
  workers: process.env.CI ? 2 : 1,

  reporter: [
    ["html", { outputFolder: "playwright-report" }],
    ["list"],
  ],

  use: {
    // Target URL — Amplify preview in CI, localhost:3000 locally
    baseURL: process.env.BASE_URL || "http://localhost:3000",

    // Reuse the authenticated session saved by global-setup.setup.ts
    storageState: "tests/e2e/.auth/user.json",

    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",

    // Generous timeout — Amplify cold starts can be slow
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  projects: [
    // ── 1. Authentication setup ────────────────────────────────────────────
    // Runs loginAs once, saves storageState, must complete before test workers start.
    {
      name: "setup",
      testMatch: /.*\.setup\.ts/,
      use: {
        // No pre-existing storage state for the setup step itself
        storageState: undefined,
      },
    },

    // ── 2. Main test runner ────────────────────────────────────────────────
    // Depends on setup completing successfully.
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      dependencies: ["setup"],
    },
  ],

  // No webServer — tests always run against a deployed URL (Amplify or localhost)
});
