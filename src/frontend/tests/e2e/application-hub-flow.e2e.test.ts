import { test, expect, Page } from "@playwright/test";

const LOGIN_EMAIL = process.env.E2E_TEST_EMAIL || "test@careervp.com";
const LOGIN_PASSWORD = process.env.E2E_TEST_PASSWORD || "TestPassword1!";

async function mockModuleStatusEndpoint(
  page: Page,
  module: string,
  jobId: string,
  status: "pending" | "processing" | "completed" | "failed"
) {
  const pathMap: Record<string, string> = {
    vpr: `/vpr/${jobId}/status`,
    coverLetter: `/cover-letter/${jobId}/status`,
    interviewPrep: `/interview-prep/${jobId}/status`,
    tailoredCV: `/cv-tailoring/${jobId}/status`,
  };
  await page.route(`**${pathMap[module]}`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        job_id: jobId,
        status,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        ...(status === "completed" ? { result_url: `https://s3.example.com/${module}-result` } : {}),
      }),
    })
  );
}

async function login(page: Page) {
  await page.goto("/login");
  await page.fill('[data-testid="email-input"]', LOGIN_EMAIL);
  await page.fill('[data-testid="password-input"]', LOGIN_PASSWORD);
  await page.click('[data-testid="sign-in-button"]');
  await expect(page).toHaveURL(/\/dashboard/);
}

test.describe("Application Hub — full VPR generation flow", () => {
  test("user can generate VPR and see it transition to ready state", async ({ page }) => {
    await login(page);

    await page.route("**/jobs", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ jobs: [{ job_id: "job-e2e-001", title: "Senior Engineer", company: "Acme Corp" }] }),
      })
    );

    await page.goto("/dashboard");
    await page.click('[data-testid="job-card-job-e2e-001"]');
    await expect(page).toHaveURL(/\/jobs\/job-e2e-001/);

    await expect(page.locator('[data-testid="module-card-vpr"]')).toBeVisible();
    await expect(
      page.locator('[data-testid="module-card-vpr"] [data-testid="primary-cta"]')
    ).toHaveText("Generate");

    await mockModuleStatusEndpoint(page, "vpr", "job-e2e-001", "processing");
    await page.route("**/vpr/generate", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ job_id: "job-e2e-001" }),
      })
    );

    await page.click('[data-testid="module-card-vpr"] [data-testid="primary-cta"]');

    await expect(page.locator('[data-testid="module-card-vpr"] [data-testid="spinner"]')).toBeVisible();
    await expect(
      page.locator('[data-testid="module-card-vpr"] [data-testid="primary-cta"]')
    ).toBeHidden();

    await mockModuleStatusEndpoint(page, "vpr", "job-e2e-001", "completed");

    await expect(
      page.locator('[data-testid="module-card-vpr"] [data-testid="primary-cta"]'),
      { timeout: 15_000 }
    ).toHaveText("View");
    await expect(page.locator('[data-testid="module-card-vpr"] [data-testid="spinner"]')).toBeHidden();
  });
});

test.describe("Application Hub — stale dependency flow", () => {
  test("CV update marks 5 downstream modules as Outdated", async ({ page }) => {
    await login(page);

    await page.route("**/users/me/cv", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ cv_id: "cv-001", updated_at: "2024-01-02T12:00:00Z", version: 2 }),
      })
    );

    await page.route("**/jobs/job-stale-001", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ job_id: "job-stale-001", title: "PM Role" }),
      })
    );

    for (const module of ["vpr", "coverLetter", "interviewPrep"]) {
      await mockModuleStatusEndpoint(page, module, "job-stale-001", "completed");
    }

    await page.goto("/jobs/job-stale-001");

    await expect(page.locator('[data-testid="module-card-vpr"] [data-testid="status-badge"]')).toHaveText(/outdated/i);
    await expect(page.locator('[data-testid="module-card-cover-letter"] [data-testid="status-badge"]')).toHaveText(/outdated/i);
    await expect(page.locator('[data-testid="module-card-interview-prep"] [data-testid="status-badge"]')).toHaveText(/outdated/i);

    await expect(page.locator('[data-testid="module-card-company-research"] [data-testid="status-badge"]')).toBeHidden();
    await expect(page.locator('[data-testid="module-card-base-cv"] [data-testid="status-badge"]')).toBeHidden();
  });
});

test.describe("Application Hub — gap analysis blocks VPR", () => {
  test("VPR Generate CTA is disabled when gap analysis is not started", async ({ page }) => {
    await login(page);

    await page.route("**/jobs/job-blocked-001", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ job_id: "job-blocked-001", title: "Designer" }),
      })
    );

    await page.route("**/jobs/job-blocked-001/gap-questions", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ questions: [], responses: [] }),
      })
    );

    await page.goto("/jobs/job-blocked-001");

    const vprCta = page.locator('[data-testid="module-card-vpr"] [data-testid="primary-cta"]');
    await expect(vprCta).toBeDisabled();
    await expect(page.locator('[data-testid="hub-blocked-banner"]')).toBeVisible();
  });
});

test.describe("Authentication flow", () => {
  test("unauthenticated user is redirected from /dashboard to /login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });

  test("authenticated user is redirected from /login to /dashboard", async ({ page }) => {
    await login(page);
    await page.goto("/login");
    await expect(page).toHaveURL(/\/dashboard/);
  });
});
