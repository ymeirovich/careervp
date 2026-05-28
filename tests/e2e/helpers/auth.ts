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
 * Waits for redirect away from /login to confirm success.
 * Throws if credentials are not configured.
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

  // Fill credentials — uses accessible label selectors, tolerant of label text variation
  await page.getByLabel(/email/i).fill(user.email);
  await page.getByLabel(/password/i).fill(user.password);

  // Submit — tolerates "Sign in", "Log in", "Login" button text
  await page
    .getByRole("button", { name: /sign in|log in|login/i })
    .click();

  // Confirm redirect away from the login page
  await page.waitForURL((url) => !url.pathname.includes("/login"), {
    timeout: 20_000,
  });
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
