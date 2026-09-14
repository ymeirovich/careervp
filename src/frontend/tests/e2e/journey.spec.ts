/**
 * THE JOURNEY — the one test that defines "done".
 *
 * Nine steps, in the order a paying customer performs them. It runs in serial:
 * when a step fails, the rest are skipped, and the test reports one number —
 * how far a customer gets today.
 *
 *     REACHED 4 of 9
 *
 * That number is the project's position. It only goes up when real capability
 * is added, it goes down the moment something regresses, and it cannot be
 * argued with. Every other test in this repo answers "does this component
 * behave?"; this one answers "can someone use the product?".
 *
 * Rules for editing this file
 * ---------------------------
 * 1. Never add a `TODO` here. A step either asserts something real or it does
 *    not exist. A step that asserts nothing reports green and teaches you
 *    a falsehood — that failure mode already cost this project months.
 * 2. Never soften a step to make it pass. Lowering the bar moves the number
 *    without moving the product, which is the only way this instrument can lie.
 * 3. Steps may only be added at the end, or inserted when the product genuinely
 *    grows a step. Renumbering is fine; redefining J5 to mean something easier
 *    is not.
 *
 * First run
 * ---------
 * Expect this to fail early, and expect some failures to be *selector* problems
 * rather than product problems — this file is written against the routes and
 * roles the app is believed to expose. When a step fails, read the error: it
 * names what it looked for. Fixing a selector is calibration, not cheating.
 * Fixing it by deleting the assertion is cheating.
 *
 * Run it
 * ------
 *     cd src/frontend
 *     BASE_URL=http://localhost:3000 npx playwright test journey.spec.ts
 *
 * Requires E2E_TEST_EMAIL / E2E_TEST_PASSWORD (see helpers/auth.ts).
 */

import { test, expect, type Page } from "@playwright/test";
import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

test.describe.configure({ mode: "serial" });

// ---------------------------------------------------------------------------
// Step registry — the definition of the product, in order
// ---------------------------------------------------------------------------

const STEP_IDS = ["J1", "J2", "J3", "J4", "J5", "J6", "J7", "J8", "J9"] as const;
type StepId = (typeof STEP_IDS)[number];

const STEP_NAMES: Record<StepId, string> = {
  J1: "sign in",
  J2: "upload base CV",
  J3: "create application",
  J4: "VPR generates",
  J5: "gap analysis submit",
  J6: "tailored CV",
  J7: "cover letter",
  J8: "interview prep",
  J9: "export",
};

// Artifact generation calls an LLM behind a queue. These are deliberately
// generous: a slow step is a different problem from a broken one, and
// conflating them wastes days.
const GENERATION_TIMEOUT_MS = Number(process.env.JOURNEY_GENERATION_TIMEOUT_MS ?? 240_000);
const PAGE_TIMEOUT_MS = 30_000;

// ---------------------------------------------------------------------------
// Proof recording
// ---------------------------------------------------------------------------

const results: Partial<Record<StepId, string>> = {};

function git(args: string): string {
  try {
    return execSync(`git ${args}`, { encoding: "utf8", timeout: 10_000 }).trim();
  } catch {
    return "";
  }
}

const GIT_SHA = git("rev-parse HEAD");
const GIT_SHORT = GIT_SHA.slice(0, 7) || "nogit";
const GIT_DIRTY = git("status --porcelain").length > 0;
const RUN_STAMP = new Date().toISOString().replace(/[:-]/g, "").split(".")[0];

// Repo root, so evidence lands in one place regardless of where playwright ran.
const REPO_ROOT = git("rev-parse --show-toplevel") || process.cwd();
const SHOT_DIR = path.join(REPO_ROOT, "docs/evidence/journey", `${RUN_STAMP}-${GIT_SHORT}`);

/** Highest N such that J1..JN all passed. Not the count of passing steps —
 *  a customer cannot skip a broken step, so neither does this number. */
function reachedFrom(recorded: Partial<Record<StepId, string>>): number {
  let reached = 0;
  for (const id of STEP_IDS) {
    if (recorded[id] === "pass") reached += 1;
    else break;
  }
  return reached;
}

async function shot(page: Page, id: StepId): Promise<void> {
  fs.mkdirSync(SHOT_DIR, { recursive: true });
  const slug = STEP_NAMES[id].replace(/\s+/g, "-");
  await page.screenshot({ path: path.join(SHOT_DIR, `${id}-${slug}.png`), fullPage: true });
}

test.afterEach(async ({ page }, testInfo) => {
  const id = testInfo.title.slice(0, 2) as StepId;
  if (!STEP_IDS.includes(id)) return;

  if (testInfo.status === "passed") {
    results[id] = "pass";
  } else if (testInfo.status === "skipped") {
    results[id] = "not reached";
  } else {
    const message = (testInfo.error?.message ?? testInfo.status).split("\n")[0];
    results[id] = `fail: ${message}`;
  }

  // Screenshot every step, pass or fail — the failing frame is the most
  // useful one and the passing frames are the regression baseline.
  if (results[id] !== "not reached") {
    try {
      await shot(page, id);
    } catch {
      /* a closed page is not worth failing the run over */
    }
  }
});

test.afterAll(async () => {
  const reached = reachedFrom(results);
  const steps: Record<string, string> = {};
  for (const id of STEP_IDS) steps[id] = results[id] ?? "not run";

  const proof = {
    kind: "journey",
    journey_reached: reached,
    journey_total: STEP_IDS.length,
    steps,
    step_names: STEP_NAMES,
    git_sha: GIT_SHA || null,
    git_short: GIT_SHORT,
    git_dirty: GIT_DIRTY,
    git_branch: git("rev-parse --abbrev-ref HEAD") || null,
    // Supplied by `make journey`, which reads the DeployedGitSha stack output.
    deployed_sha: process.env.DEPLOYED_SHA ?? null,
    base_url: process.env.BASE_URL ?? "http://localhost:3000",
    stack: process.env.JOURNEY_STACK ?? "CareerVpCrudDevx",
    screenshots: path.relative(REPO_ROOT, SHOT_DIR),
    timestamp: new Date().toISOString(),
  };

  const dir = path.join(REPO_ROOT, "docs/evidence");
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `journey-${RUN_STAMP}-${GIT_SHORT}.json`);
  fs.writeFileSync(file, `${JSON.stringify(proof, null, 2)}\n`, "utf8");

  const dirtyNote = GIT_DIRTY ? "  [DIRTY TREE — this proof is not reproducible]" : "";
  process.stdout.write(`\nREACHED ${reached} of ${STEP_IDS.length}${dirtyNote}\nproof: ${path.relative(REPO_ROOT, file)}\n`);
});

// ---------------------------------------------------------------------------
// Small helpers. Each returns a locator that tolerates reasonable UI variation
// but never tolerates absence — if nothing matches, the step fails loudly.
// ---------------------------------------------------------------------------

/** A CV file the parser can actually read; deliberately obviously synthetic. */
const SYNTHETIC_CV = [
  "Jane Doe",
  "Software Engineer",
  "jane.doe@example.com",
  "",
  "Experience",
  "Acme Corp — Backend Engineer, 2020-2024.",
  "Built Python services on AWS Lambda and DynamoDB. Led a team of three.",
  "",
  "Education",
  "BSc Computer Science, Example University, 2020.",
  "",
  "Skills",
  "Python, TypeScript, AWS, DynamoDB, REST APIs",
].join("\n");

const JOB_DESCRIPTION = [
  "Senior Backend Engineer — Serverless",
  "",
  "We are looking for an engineer with strong Python and AWS Lambda experience.",
  "You will design DynamoDB access patterns, own API contracts, and mentor others.",
  "Requirements: 5+ years Python, production AWS, event-driven architecture,",
  "and experience leading technical projects end to end.",
].join("\n");

/** Wait for an artifact page to leave its loading/queued state. */
async function waitForArtifact(page: Page, bodyPattern: RegExp): Promise<void> {
  await expect(page.getByText(bodyPattern).first()).toBeVisible({ timeout: GENERATION_TIMEOUT_MS });
}

// ---------------------------------------------------------------------------
// The journey
// ---------------------------------------------------------------------------

let applicationUrl = "";

test.describe("THE JOURNEY", () => {
  test.beforeEach(async ({ page }) => {
    page.setDefaultTimeout(PAGE_TIMEOUT_MS);
  });

  test("J1 sign in", async ({ page }) => {
    // Auth state is established by global-setup.setup.ts. This step proves the
    // session actually works against this environment, which is a different
    // claim from "setup did not throw".
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByRole("navigation").or(page.getByTestId("app-sidebar")).first()).toBeVisible();
  });

  test("J2 upload base CV", async ({ page }) => {
    await page.goto("/cv-center");

    const before = await page.getByRole("row").count();

    await page.getByRole("button", { name: /upload|add cv|new cv/i }).first().click();
    await page.setInputFiles('input[type="file"]', {
      name: "jane-doe-cv.txt",
      mimeType: "text/plain",
      buffer: Buffer.from(SYNTHETIC_CV, "utf8"),
    });

    const confirm = page.getByRole("button", { name: /upload|save|confirm/i }).last();
    if (await confirm.isEnabled().catch(() => false)) await confirm.click();

    // The CV must appear in the list — an upload that 200s but stores nothing
    // is the exact failure this step exists to catch.
    await expect
      .poll(async () => page.getByRole("row").count(), { timeout: GENERATION_TIMEOUT_MS })
      .toBeGreaterThan(before);
  });

  test("J3 create application", async ({ page }) => {
    await page.goto("/applications/new");

    await page.getByLabel(/job title|position/i).fill("Senior Backend Engineer");
    await page.getByLabel(/company/i).fill("Example Corp");
    await page.getByLabel(/job description|description/i).fill(JOB_DESCRIPTION);

    await page.getByRole("button", { name: /create|submit|save/i }).first().click();

    // Landing on an application URL is the proof; a form that clears itself is not.
    await page.waitForURL(/\/applications\/[^/]+$/, { timeout: GENERATION_TIMEOUT_MS });
    applicationUrl = page.url();
    expect(applicationUrl).toMatch(/\/applications\/[^/]+$/);
  });

  test("J4 VPR generates", async ({ page }) => {
    test.setTimeout(GENERATION_TIMEOUT_MS + 60_000);
    await page.goto(applicationUrl);

    const trigger = page.getByRole("button", { name: /generate.*vpr|value proposition|start analysis/i }).first();
    if (await trigger.isVisible().catch(() => false)) await trigger.click();

    // Assert on content, not on a spinner disappearing: a failed generation
    // also stops spinning.
    await waitForArtifact(page, /value proposition|vpr|match score|fit/i);
    await expect(page.getByText(/failed|error/i)).toHaveCount(0);
  });

  test("J5 gap analysis submit", async ({ page }) => {
    test.setTimeout(GENERATION_TIMEOUT_MS + 60_000);
    await page.goto(`${applicationUrl}/gap-analysis`);

    const questions = page.getByRole("textbox");
    await expect(questions.first()).toBeVisible({ timeout: GENERATION_TIMEOUT_MS });

    const count = await questions.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i += 1) {
      await questions.nth(i).fill("I led a three-person team migrating a monolith to Lambda over eight months.");
    }

    await page.getByRole("button", { name: /submit|save|continue|finish/i }).first().click();

    // Persistence is the claim, so reload before believing it.
    await page.waitForLoadState("networkidle");
    await page.reload();
    await expect(page.getByText(/submitted|complete|thank you|answers saved/i).first()).toBeVisible({ timeout: GENERATION_TIMEOUT_MS });
  });

  test("J6 tailored CV", async ({ page }) => {
    test.setTimeout(GENERATION_TIMEOUT_MS + 60_000);
    await page.goto(`${applicationUrl}/cv-tailored`);

    const trigger = page.getByRole("button", { name: /generate|tailor|create/i }).first();
    if (await trigger.isVisible().catch(() => false)) await trigger.click();

    await waitForArtifact(page, /experience|summary|skills/i);
    await expect(page.getByText(/failed|error/i)).toHaveCount(0);
  });

  test("J7 cover letter", async ({ page }) => {
    test.setTimeout(GENERATION_TIMEOUT_MS + 60_000);
    await page.goto(`${applicationUrl}/cover-letter`);

    const trigger = page.getByRole("button", { name: /generate|create|write/i }).first();
    if (await trigger.isVisible().catch(() => false)) await trigger.click();

    await waitForArtifact(page, /dear|sincerely|regards|hiring/i);
    await expect(page.getByText(/failed|error/i)).toHaveCount(0);
  });

  test("J8 interview prep", async ({ page }) => {
    test.setTimeout(GENERATION_TIMEOUT_MS + 60_000);
    await page.goto(`${applicationUrl}/interview-prep`);

    const trigger = page.getByRole("button", { name: /generate|create|prepare/i }).first();
    if (await trigger.isVisible().catch(() => false)) await trigger.click();

    await waitForArtifact(page, /question|answer|tell me about|why/i);
    await expect(page.getByText(/failed|error/i)).toHaveCount(0);
  });

  test("J9 export", async ({ page }) => {
    test.setTimeout(GENERATION_TIMEOUT_MS + 60_000);
    await page.goto(`${applicationUrl}/cv-tailored`);

    const downloadPromise = page.waitForEvent("download", { timeout: GENERATION_TIMEOUT_MS });
    await page.getByRole("button", { name: /export|download|pdf|docx/i }).first().click();

    const download = await downloadPromise;
    const file = await download.path();
    expect(file).toBeTruthy();

    // A zero-byte download is a successful-looking failure.
    const size = file ? fs.statSync(file).size : 0;
    expect(size).toBeGreaterThan(1000);
  });
});
