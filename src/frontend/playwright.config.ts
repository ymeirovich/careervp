/**
 * Playwright configuration for CareerVP UI upgrade e2e tests.
 *
 * Config and tests both live in src/frontend/ so @playwright/test resolves.
 * Tests:      src/frontend/tests/e2e/
 * Auth state: src/frontend/tests/e2e/.auth/user.json  (gitignored)
 *
 * Run from src/frontend/:
 *   BASE_URL=https://ui-upgrade.<app-id>.amplifyapp.com npx playwright test
 */

import { defineConfig, devices } from "@playwright/test";
import fs from "fs";
import path from "path";

// ---------------------------------------------------------------------------
// Load .env.e2e into process.env.
//
// helpers/auth.ts reads process.env.E2E_TEST_EMAIL / E2E_TEST_PASSWORD and its
// error message tells you to create a .env.e2e file -- but nothing ever loaded
// one and `dotenv` is not a dependency, so the documented local workflow could
// not work. `make journey` therefore failed in global setup for anyone who did
// not already have the variables exported, which is why the journey had not
// been measured since 2026-09-14.
//
// Both paths named in the codebase are honoured: auth.ts's docstring says
// src/frontend/.env.e2e, its thrown error says tests/e2e/.env.e2e.
//
// Real environment variables always win, so GitHub Actions secrets are
// unaffected by this.
// ---------------------------------------------------------------------------
for (const rel of [".env.e2e", "tests/e2e/.env.e2e"]) {
  const file = path.resolve(__dirname, rel);
  if (!fs.existsSync(file)) continue;
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (!m) continue;
    const [, key, rawValue] = m;
    if (process.env[key]) continue; // never override a real env var
    process.env[key] = rawValue.replace(/^(['"])(.*)\1$/, "$2");
  }
}

// Tests live co-located at src/frontend/tests/e2e/ so @playwright/test resolves
const AUTH_FILE = "./tests/e2e/.auth/user.json";

export default defineConfig({
  testDir: "./tests/e2e",
  // *.test.ts files belong to Jest — only Playwright spec/setup files here
  testIgnore: ["**/*.test.ts"],

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

    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",

    // Generous timeout — Amplify cold starts can be slow
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  projects: [
    // ── 1. Authentication setup ────────────────────────────────────────────
    // storageState is NOT set here — the file doesn't exist yet when setup runs.
    // Setting storageState: undefined in a project does not override a global
    // storageState, so we keep storageState out of the global use block entirely.
    {
      name: "setup",
      testMatch: /.*\.setup\.ts/,
    },

    // ── 2. Main test runner ────────────────────────────────────────────────
    // storageState is set here so only the chromium project loads the auth file
    // (which setup has already written at this point).
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], storageState: AUTH_FILE },
      dependencies: ["setup"],
    },
  ],

  // No webServer — tests always run against a deployed URL (Amplify or localhost)
});
