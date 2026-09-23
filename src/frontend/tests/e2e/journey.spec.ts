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
 * J4/J5 note: the original draft of this file numbered them VPR-generates (J4)
 * then gap-analysis-submit (J5). That order cannot happen for a real customer —
 * the backend's artifact dependency graph (artifact_dependency_resolver.py)
 * requires vpr's upstream `company_research`, which itself requires
 * `gap_analysis`; requesting VPR first returns 409 upstream_required every
 * time. Swapped so J4/J5 match the order a customer actually goes through,
 * per rule 3 ("renumbering is fine") — each step's own assertions are
 * unchanged, only which label attaches to which step.
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
  J4: "gap analysis submit",
  J5: "VPR generates",
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
// Browser-side diagnostics
// ---------------------------------------------------------------------------
//
// J3's first failure against deployed code (2026-09-21) reported nothing but
// `waitForURL: Timeout 240000ms exceeded`. What actually happened: the click
// landed, POST /jobs answered 403 trial_expired, and the form rendered that
// reason above the fold of a scrolled page. The browser knew the answer the
// whole time and the report discarded it, so the failure was misdiagnosed as
// client-side and "no network request is issued".
//
// Everything the page says about itself is now recorded into the proof.

const MAX_DIAGNOSTICS = 50;
const MAX_DIAGNOSTIC_CHARS = 400;

const diagnosticsByStep: Partial<Record<StepId, string[]>> = {};
let diagnostics: string[] = [];
let pendingBodies: Promise<unknown>[] = [];

function note(line: string): void {
  if (diagnostics.length < MAX_DIAGNOSTICS) diagnostics.push(line.slice(0, MAX_DIAGNOSTIC_CHARS));
}

/** Record console errors, uncaught exceptions, failed requests, and every
 *  4xx/5xx response together with its body — the body is where the API states
 *  its reason, and that reason is the thing worth keeping. */
function attachDiagnostics(page: Page): void {
  diagnostics = [];
  pendingBodies = [];

  page.on("console", (msg) => {
    if (msg.type() === "error" || msg.type() === "warning") note(`console.${msg.type()}: ${msg.text()}`);
  });
  page.on("pageerror", (err) => note(`pageerror: ${err.message}`));
  page.on("requestfailed", (req) =>
    note(`requestfailed: ${req.method()} ${req.url()} — ${req.failure()?.errorText ?? "unknown"}`),
  );
  page.on("response", (res) => {
    if (res.status() < 400) return;
    const head = `http ${res.status()}: ${res.request().method()} ${res.url()}`;
    pendingBodies.push(
      res.text().then(
        (body) => note(`${head} — ${body}`),
        () => note(head),
      ),
    );
  });
}

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

  // Response bodies resolve asynchronously; settle them before reporting.
  await Promise.allSettled(pendingBodies);
  if (diagnostics.length > 0) diagnosticsByStep[id] = [...diagnostics];

  if (testInfo.status === "passed") {
    results[id] = "pass";
  } else if (testInfo.status === "skipped") {
    results[id] = "not reached";
  } else {
    const message = (testInfo.error?.message ?? testInfo.status).split("\n")[0];
    // Lead with the server's own rejection when there is one — a status line
    // beats a symptom every time.
    const httpError = diagnostics.find((d) => d.startsWith("http "));
    results[id] = httpError ? `fail: ${message} [${httpError}]` : `fail: ${message}`;
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
    browser_diagnostics: diagnosticsByStep,
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

// The operator's own SysAid application, used as the journey's input. A
// synthetic CV and an "Example Corp" job posting cannot exercise this product:
// company research has nothing to research, and gap analysis has no real
// distance between a CV and a role to find. These are the actual artifacts.
const CV_PATH = path.join(
  REPO_ROOT,
  "docs/architecture/careervp_prompts/02_Yitzchak_Meirovich_Learning_Experience_Specialist_SysAid.docx",
);
const JOB_DESCRIPTION = fs.readFileSync(
  path.join(REPO_ROOT, "docs/features/Sysaid Job Description.txt"),
  "utf8",
);
const JOB_TITLE = "Learning Experience Specialist";
const COMPANY_NAME = "SysAid";
// A real, reachable company site: the backend probes the URL (domain_validator.py)
// and company research resolves the company from it.
const COMPANY_URL = "https://www.sysaid.com";

/** Wait for an artifact page to leave its loading/queued state. */
async function waitForArtifact(page: Page, bodyPattern: RegExp): Promise<void> {
  await expect(page.getByText(bodyPattern).first()).toBeVisible({ timeout: GENERATION_TIMEOUT_MS });
}

/**
 * Generate a module from the Application Hub and land on its artifact page.
 *
 * The hub (app/applications/[id]/page.tsx) renders one ModuleCard per module,
 * each carrying `data-testid="module-card-{moduleId}"` and a primary CTA
 * `data-testid="primary-cta"` whose label is state-driven: "Generate" (or
 * "Retry") while nothing exists, empty during generation, "View" once ready
 * (ModuleCard.tsx getPrimaryLabel). Matching by visible button text alone is
 * ambiguous — every generatable module's card says "Generate" — and the
 * cards' own headings (e.g. "Value Proposition Report") already contain
 * words like "value proposition", so asserting on hub body text would pass
 * even if generation never ran. Driving the specific card's CTA and then
 * following it to the real artifact page is what actually proves generation
 * happened.
 */
async function generateFromHub(
  page: Page,
  moduleId: string,
  hubUrl: string,
  artifactBodyPattern: RegExp,
): Promise<void> {
  await page.goto(hubUrl);
  const card = page.getByTestId(`module-card-${moduleId}`);
  await expect(card).toBeVisible({ timeout: PAGE_TIMEOUT_MS });

  const cta = card.getByTestId("primary-cta");
  const label = (await cta.textContent().catch(() => ""))?.trim().toLowerCase();
  if (label === "generate" || label === "retry") {
    await cta.click();
  }

  // Poll instead of a single assertion: the CTA disappears entirely while
  // processing (getPrimaryLabel returns null), so it must be re-queried.
  await expect(card.getByTestId("primary-cta")).toHaveText(/view/i, {
    timeout: GENERATION_TIMEOUT_MS,
  });
  await card.getByTestId("primary-cta").click();

  await waitForArtifact(page, artifactBodyPattern);
  await expect(page.getByText(/failed|error/i)).toHaveCount(0);
}

// ---------------------------------------------------------------------------
// The journey
// ---------------------------------------------------------------------------

let applicationUrl = "";

test.describe("THE JOURNEY", () => {
  test.beforeEach(async ({ page }) => {
    page.setDefaultTimeout(PAGE_TIMEOUT_MS);
    attachDiagnostics(page);
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
    // The picker accepts .pdf/.doc/.docx and not .txt (ChooseBaseCVModal), so
    // the previous synthetic text buffer was never a file a customer could pick.
    await page.setInputFiles('input[type="file"]', CV_PATH);

    const confirm = page.getByRole("button", { name: /upload|save|confirm/i }).last();
    if (await confirm.isEnabled().catch(() => false)) await confirm.click();

    // The CV must appear in the list — an upload that 200s but stores nothing
    // is the exact failure this step exists to catch.
    await expect
      .poll(async () => page.getByRole("row").count(), { timeout: GENERATION_TIMEOUT_MS })
      .toBeGreaterThan(before);
  });

  test("J3 create application", async ({ page }) => {
    // Submission enqueues gap-question generation and redirects immediately
    // (HANDOFF-09: the LLM call moved to an SQS worker, off the request path)
    // — this no longer needs the full generation budget, but keeps it as
    // headroom rather than risking flakiness from an untested tighter bound.
    test.setTimeout(GENERATION_TIMEOUT_MS + 60_000);
    await page.goto("/applications/new");

    await page.getByLabel(/job title|position/i).fill(JOB_TITLE);
    await page.getByLabel(/company/i).fill(COMPANY_NAME);
    await page.getByLabel(/job description|description/i).fill(JOB_DESCRIPTION);
    // The form's submit button stays disabled until a job URL is present too,
    // and the backend probes the URL for real reachability (domain_validator.py)
    // before accepting it — a synthetic path 404s, so this must be a live page.
    await page.getByLabel(/job url|url/i).fill(COMPANY_URL);

    // Selecting a base CV here is what makes gap-analysis questions exist at
    // all: handleSubmit (applications/new/page.tsx) only calls
    // generateGapQuestions when a cvId is available, falling back silently
    // to a bare application otherwise — the gap-analysis page itself never
    // generates questions, it only reads ones that already exist.
    await page.getByRole("button", { name: /change/i }).click();
    await page.getByTestId("choose-base-cv-row-uploaded").first().getByRole("button", { name: /select/i }).click();

    await page.getByRole("button", { name: /create|submit|save/i }).first().click();

    // Landing on an application URL is the proof; a form that clears itself is not.
    // With a base CV attached, handleSubmit redirects straight to
    // /applications/{id}/gap-analysis instead of the bare hub (it skips
    // straight to the next thing the customer needs to do) — accept either.
    // `new` is excluded from the id segment: otherwise this pattern also
    // matches the starting /applications/new page itself, and waitForURL
    // resolves immediately without waiting for any real navigation — a false
    // pass that never submits anything.
    // A rejected submit must fail *here*, in the API's own words. On
    // 2026-09-21 this waited the full 240s and reported a navigation timeout
    // while the form had been displaying the rejection the whole time — which
    // is exactly how a plain 403 got misread as a client-side defect. Scoped
    // to the card because the app shell renders its own role="alert" banners.
    const rejection = page.getByTestId("new-application-card").getByRole("alert").first();
    const navigated = page.waitForURL(/\/applications\/(?!new\/?$)[^/]+(\/gap-analysis)?\/?$/, {
      timeout: GENERATION_TIMEOUT_MS,
    });
    // Each branch carries its own catch: the loser of the race settles later,
    // and must not surface as an unhandled rejection after the test moves on.
    const outcome = await Promise.race([
      navigated.then(() => "navigated" as const).catch(() => "exhausted" as const),
      rejection
        .waitFor({ state: "visible", timeout: GENERATION_TIMEOUT_MS })
        .then(() => "rejected" as const)
        .catch(() => "exhausted" as const),
    ]);

    if (outcome === "rejected") {
      const stated = (await rejection.textContent().catch(() => null))?.trim();
      throw new Error(`create-application was rejected: ${stated || "(error shown, but it said nothing)"}`);
    }
    if (outcome === "exhausted") {
      throw new Error("create-application neither navigated nor surfaced an error");
    }
    applicationUrl = page.url().replace(/\/gap-analysis\/?$/, "").replace(/\/$/, "");
    expect(applicationUrl).toMatch(/\/applications\/(?!new$)[^/]+$/);
  });

  test("J4 gap analysis submit", async ({ page }) => {
    // Generous beyond GENERATION_TIMEOUT_MS: the LLM call now runs in an SQS
    // worker (HANDOFF-09), off the request path, but this budget covers queue
    // delivery plus generation. The page polls itself every 3s (useEffect in
    // gap-analysis/page.tsx) and shows a "generating" state while status is
    // pending/processing, so no manual reload loop is needed here anymore —
    // waiting on the questions list (with its own auto-wait) is sufficient.
    const GAP_QUESTIONS_TIMEOUT_MS = 2 * GENERATION_TIMEOUT_MS;
    test.setTimeout(GAP_QUESTIONS_TIMEOUT_MS + 60_000);
    await page.goto(`${applicationUrl}/gap-analysis`);

    const questionCards = page.getByTestId("questions-list").locator("> div");
    const generationFailedBanner = page.getByTestId("generation-failed-banner");
    const outcome = await Promise.race([
      questionCards
        .first()
        .waitFor({ state: "visible", timeout: GAP_QUESTIONS_TIMEOUT_MS })
        .then(() => "ready" as const)
        .catch(() => "exhausted" as const),
      generationFailedBanner
        .waitFor({ state: "visible", timeout: GAP_QUESTIONS_TIMEOUT_MS })
        .then(() => "failed" as const)
        .catch(() => "exhausted" as const),
    ]);

    if (outcome === "failed") {
      throw new Error("gap-question generation reported status=failed");
    }
    if (outcome === "exhausted") {
      throw new Error("gap-question generation neither completed nor reported failed in time");
    }

    const count = await questionCards.count();
    expect(count).toBeGreaterThan(0);

    // One question can be open for editing at a time (GapQuestionCard's own
    // guard) — the rich-text answer field is a contenteditable ProseMirror
    // node, not a plain <textarea>. Answer → fill → Save, one card at a time.
    for (let i = 0; i < count; i += 1) {
      await questionCards.nth(i).getByRole("button", { name: /^answer$/i }).click();
      const editable = questionCards.nth(i).locator('[contenteditable="true"]');
      if (i === 0) {
        // Exercise the AI Assist path for real (RichTextEditor's toolbar
        // button -> POST /ai/assist -> ai-assist-lambda), not a synthetic
        // fill — only on the first question, to keep this loop's LLM cost
        // bounded. The button replaces the editor's content via
        // editor.commands.setContent on success, so waiting for the field to
        // stop being empty is the real completion signal (not the button's
        // own "Generating…" label, which can transiently race the click).
        await questionCards.nth(i).getByRole("button", { name: /ai assist/i }).click();
        await expect(editable).not.toBeEmpty({ timeout: GENERATION_TIMEOUT_MS });
      } else {
        await editable.fill(
          "I led a three-person team migrating a monolith to Lambda over eight months.",
        );
      }
      await questionCards.nth(i).getByRole("button", { name: /^save$/i }).click();
      // Not "the Save button went away": while the request is in flight the
      // button renders a spinner carrying aria-label="Saving", which makes its
      // accessible name "Saving Save" and stops /^save$/ matching. That is the
      // save STARTING. Waiting on it let this loop open the next question
      // mid-save, where the page's own guard correctly blocked it — read for a
      // full run as "J4 is broken". Edit only renders once the card has left
      // edit state holding a stored response, so it means the answer landed.
      await expect(questionCards.nth(i).getByRole("button", { name: /^edit$/i })).toBeVisible({
        timeout: PAGE_TIMEOUT_MS,
      });
    }

    await page.getByTestId("submit-all-btn").click();

    // Submitting redirects to the hub — persistence is the claim, so reload
    // there before believing the module actually recorded completion.
    await page.waitForURL((url) => !url.pathname.includes("/gap-analysis"), {
      timeout: GENERATION_TIMEOUT_MS,
    });
    await page.reload();
    await expect(page.getByText(/complete gap analysis to unlock/i)).toHaveCount(0);
  });

  test("J5 VPR generates", async ({ page }) => {
    test.setTimeout(2 * GENERATION_TIMEOUT_MS + 60_000);
    // VPR's backend dependency is company_research, not gap_analysis directly
    // (artifact_dependency_resolver.py DEPENDENCIES) — company research is not
    // one of the customer-facing steps this journey counts, but it is a real,
    // mandatory precondition the hub exposes as its own card, so it has to be
    // driven here or every VPR request 409s upstream_required.
    await generateFromHub(page, "companyResearch", applicationUrl, /research|overview|about|industry|culture/i);
    await generateFromHub(page, "vpr", applicationUrl, /value proposition|vpr|match score|fit/i);
  });

  test("J6 tailored CV", async ({ page }) => {
    test.setTimeout(GENERATION_TIMEOUT_MS + 60_000);
    await generateFromHub(page, "tailoredCV", applicationUrl, /experience|summary|skills/i);
  });

  test("J7 cover letter", async ({ page }) => {
    test.setTimeout(GENERATION_TIMEOUT_MS + 60_000);
    await generateFromHub(page, "coverLetter", applicationUrl, /dear|sincerely|regards|hiring/i);
  });

  test("J8 interview prep", async ({ page }) => {
    test.setTimeout(GENERATION_TIMEOUT_MS + 60_000);
    await generateFromHub(page, "interviewPrep", applicationUrl, /question|answer|tell me about|why/i);
  });

  test("J9 export", async ({ page }) => {
    test.setTimeout(GENERATION_TIMEOUT_MS + 60_000);
    await page.goto(`${applicationUrl}/cv-tailored`);

    // ExportDropdown renders a toggle whose only behaviour is setOpen(o => !o);
    // the real download buttons are rendered inside the menu it opens. The
    // previous selector matched the toggle, so J9 opened the dropdown and then
    // waited four minutes for a download that needed a second click — the
    // export Lambda was never invoked once.
    const dropdown = page.getByTestId("export-dropdown");
    await expect(dropdown).toBeVisible({ timeout: 60_000 });
    await dropdown.getByRole("button", { name: /^export/i }).click();

    // Word, not PDF. export_handler._handle_export returns 501 for
    // format=pdf ("PDF export is not yet available."); only docx is
    // implemented. Clicking PDF would surface 'Export is coming soon!' and
    // fire no download event — failing J9 with the identical timeout for a
    // completely different reason.
    const downloadItem = dropdown.getByRole("button", { name: /download as word/i });
    await expect(downloadItem).toBeVisible();

    // Arm the listener around the click that actually triggers the download,
    // not around the toggle.
    const downloadPromise = page.waitForEvent("download", { timeout: GENERATION_TIMEOUT_MS });
    await downloadItem.click();

    const download = await downloadPromise;
    const file = await download.path();
    expect(file).toBeTruthy();

    // A zero-byte download is a successful-looking failure.
    const size = file ? fs.statSync(file).size : 0;
    expect(size).toBeGreaterThan(1000);
  });
});
