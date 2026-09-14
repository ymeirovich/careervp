/**
 * Playwright auth helper for CareerVP e2e tests.
 *
 * Usage in a spec file:
 *   import { loginAs } from './helpers/auth';
 *   await loginAs(page, 'test-user');
 *
 * Credentials are read from environment variables set in GitHub Actions secrets
 * or a local .env.e2e file (never committed).
 *
 * Local development:
 *   Create src/frontend/.env.e2e (gitignored):
 *     E2E_TEST_EMAIL=your-test-user@example.com
 *     E2E_TEST_PASSWORD=your-test-password
 */

import type { Page } from "@playwright/test";

// ---------------------------------------------------------------------------
// User registry
// ---------------------------------------------------------------------------

interface TestUser {
  email: string;
  password: string;
}

const TEST_USERS: Record<string, TestUser> = {
  "test-user": {
    email: process.env.E2E_TEST_EMAIL ?? "",
    password: process.env.E2E_TEST_PASSWORD ?? "",
  },
};

// ---------------------------------------------------------------------------
// loginAs
// ---------------------------------------------------------------------------

/**
 * Navigate to /login and authenticate.
 *
 * The app's own /login page only collects an email address ("Continue
 * securely"); it then redirects to the Cognito Hosted UI (PKCE authorization
 * code flow — see lib/pkce.ts) where the password is actually entered, and
 * finally redirects back to /callback, which exchanges the code for tokens
 * and lands the user on /dashboard. This helper drives both hops.
 *
 * Waits for redirect back to the app (away from the Cognito hosted domain)
 * to confirm success. Throws if credentials are not configured.
 */
export async function loginAs(
  page: Page,
  userName: keyof typeof TEST_USERS = "test-user"
): Promise<void> {
  const user = TEST_USERS[userName];

  if (!user) {
    throw new Error(`loginAs: unknown user "${userName}"`);
  }
  if (!user.email || !user.password) {
    throw new Error(
      `loginAs: E2E_TEST_EMAIL and E2E_TEST_PASSWORD must be set.\n` +
        `For local runs create tests/e2e/.env.e2e with those values.`
    );
  }

  await page.goto("/login");
  await page.waitForLoadState("networkidle");

  // Hop 1: the app's own page — email only, then redirect to the hosted UI.
  await page.getByLabel(/email/i).fill(user.email);
  await page
    .getByRole("button", { name: /continue|sign in|log in|login/i })
    .click();

  // Hop 2: Cognito Hosted UI — a separate origin, so wait for navigation
  // there before looking for its fields. The hosted widget renders its
  // email/password/submit inputs twice (a duplicated hidden copy alongside
  // the real one, sharing the same id — a quirk of Cognito's managed login
  // widget, not something this app controls), so every selector below is
  // scoped with `:visible` to avoid the strict-mode/invisible-element traps
  // that come from matching the hidden duplicate.
  await page.waitForURL(/\/oauth2\/authorize|\/login\?/, { timeout: 20_000 });
  await page.waitForLoadState("networkidle");

  const hostedUsername = page.locator('input[name="username"]:visible').first();
  if (await hostedUsername.isVisible().catch(() => false)) {
    await hostedUsername.fill(user.email);
  }
  await page.locator('input[name="password"]:visible').fill(user.password);
  await page.locator('input[type="submit"]:visible').click();

  // Confirm redirect all the way back to the app (via /callback) — the
  // hosted UI origin is left behind, not just the app's /login path.
  await page.waitForURL((url) => !url.href.includes("amazoncognito.com"), {
    timeout: 20_000,
  });
  await page.waitForLoadState("networkidle");
}

// ---------------------------------------------------------------------------
// navigateToApplication
// ---------------------------------------------------------------------------

/**
 * Navigate to a known /applications/[id] route.
 * The application_id must exist for the test user in the dev environment.
 */
export async function navigateToApplication(
  page: Page,
  applicationId: string
): Promise<void> {
  await page.goto(`/applications/${applicationId}`);
  await page.waitForLoadState("networkidle");
}
