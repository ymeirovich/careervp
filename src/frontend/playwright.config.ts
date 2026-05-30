/**
 * Playwright configuration for CareerVP UI upgrade e2e tests.
 *
 * Config lives in src/frontend/ — that's where @playwright/test is installed.
 * Tests live at repo root: tests/e2e/
 * Auth state:              tests/e2e/.auth/user.json  (gitignored)
 *
 * Run from src/frontend/:
 *   BASE_URL=https://ui-upgrade.<app-id>.amplifyapp.com npx playwright test
 */

import { defineConfig, devices } from "@playwright/test";
import path from "path";

// Paths are relative to this config file (src/frontend/)
const REPO_ROOT = path.resolve(__dirname, "../..");
const E2E_DIR = path.join(REPO_ROOT, "tests/e2e");
const AUTH_FILE = path.join(REPO_ROOT, "tests/e2e/.auth/user.json");

export default defineConfig({
  testDir: E2E_DIR,

  // Run test files sequentially — auth state is shared across workers
  fullyParallel: false,

  // Fail fast in CI on first --only occurrence
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
    storageState: AUTH_FILE,

    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",

    // Generous timeout — Amplify cold starts can be slow
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  projects: [
    // ── 1. Authentication setup ────────────────────────────────────────────
    {
      name: "setup",
      testMatch: /.*\.setup\.ts/,
      use: { storageState: undefined },
    },

    // ── 2. Main test runner ────────────────────────────────────────────────
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      dependencies: ["setup"],
    },
  ],

  // No webServer — tests always run against a deployed URL (Amplify or localhost)
});
