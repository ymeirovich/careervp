/**
 * Playwright global setup — runs once before all e2e specs.
 * Logs in as test-user and saves auth state to .auth/user.json.
 * All spec files reuse this state via storageState in playwright.config.ts.
 *
 * This file matches the testMatch pattern /.*\.setup\.ts/ in playwright.config.ts.
 */

import { test as setup, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";
import path from "path";
import fs from "fs";

const AUTH_FILE = path.join(__dirname, ".auth/user.json");
const MAX_AGE_MS = 55 * 60 * 1000; // 55 minutes — Cognito tokens expire at 60 min

setup("authenticate as test-user", async ({ page }) => {
  // Re-use cached auth state if it is still fresh
  if (fs.existsSync(AUTH_FILE)) {
    const ageSec = (Date.now() - fs.statSync(AUTH_FILE).mtimeMs) / 1000;
    if (ageSec < MAX_AGE_MS / 1000) {
      console.log(
        `[setup] Auth cache hit (age: ${Math.round(ageSec)}s) — skipping login`
      );
      return;
    }
    console.log(`[setup] Auth cache stale (age: ${Math.round(ageSec)}s) — re-authenticating`);
  }

  await loginAs(page, "test-user");

  // Confirm we landed somewhere meaningful (not an error page)
  await expect(page).not.toHaveURL(/error|not-found|404/);

  // Persist cookies + localStorage for all subsequent test workers
  fs.mkdirSync(path.dirname(AUTH_FILE), { recursive: true });
  await page.context().storageState({ path: AUTH_FILE });

  console.log("[setup] Auth state saved →", AUTH_FILE);
});
