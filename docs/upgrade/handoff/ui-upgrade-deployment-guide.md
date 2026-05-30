# CareerVP UI Upgrade — Deployment & Implementation Guide

> **Scope:** 26 specs (FE-UI-001 → FE-UI-026), organized into 6 batches.
> Amplify replaces S3+CloudFront. One `ui-upgrade` branch, one commit per spec.
> All specs are `verification_type: unit / pre_merge` — e2e tests are post-deploy smoke only.

---

## Table of Contents

1. [Batch Map](#1-batch-map)
2. [One-Time Setup](#2-one-time-setup)
   - 2.1 [AWS Amplify — replace S3+CloudFront](#21-aws-amplify--replace-s3cloudfront)
   - 2.2 [GitHub Secrets](#22-github-secrets)
   - 2.3 [Create the upgrade branch](#23-create-the-upgrade-branch)
   - 2.4 [GitHub Actions — unit check workflow](#24-github-actions--unit-check-workflow)
   - 2.5 [GitHub Actions — e2e smoke workflow](#25-github-actions--e2e-smoke-workflow)
   - 2.6 [Playwright config](#26-playwright-config)
   - 2.7 [Playwright auth helper](#27-playwright-auth-helper)
   - 2.8 [Retire the S3 deploy workflow](#28-retire-the-s3-deploy-workflow)
3. [Per-Spec Implementation Loop](#3-per-spec-implementation-loop)
4. [Batch 1 — UI Primitives](#4-batch-1--ui-primitives)
5. [Batch 2 — Layout Shell](#5-batch-2--layout-shell)
6. [Batch 3 — Dashboard & New Application Flow](#6-batch-3--dashboard--new-application-flow)
7. [Batch 4 — New List Pages & CV Center](#7-batch-4--new-list-pages--cv-center)
8. [Batch 5 — Gap Analysis](#8-batch-5--gap-analysis)
9. [Batch 6 — Billing](#9-batch-6--billing)
10. [Final Merge to Main](#10-final-merge-to-main)

---

## 1. Batch Map

All 26 specs, ordered by dependency. Each batch is independently deployable — no spec in a later batch depends on a spec from a later batch.

| Batch | Specs | Theme | Deps | Live URL | Auth required |
|-------|-------|-------|------|----------|---------------|
| **1** | 001, 002, 006, 007 | UI Primitives | none | No | No |
| **2** | 003, 004, 005 | Layout Shell | Batch 1 | Smoke only | Yes (header/sidebar) |
| **3** | 009, 008, 011, 010 | Dashboard + New App Flow | Batch 1+2 | Yes | Yes |
| **4** | 013, 012, 015, 014, 017, 016 | New List Pages + CV Center | Batch 2+3 | Yes | Yes |
| **5** | 020, 019, 018 | Gap Analysis | Batch 1+2 | Yes | Yes + app data |
| **6** | 026, 025, 022, 023, 024, 021 | Billing | Batch 1+2 | Yes | Yes |

### Dependency rationale

- **Badge (001)** is consumed by StatusBadge → ModuleCard → JobsTable → every page. Must be first.
- **ProgressBar (002)** is consumed by GapAnalysisContent (018). Must precede Batch 5.
- **AppSidebar (003)** adds the `/cover-letters` and `/tailored-cvs` nav items. Must precede Batch 4.
- **HubLayout (005)** wraps all `/applications/[id]` pages. Must precede Batches 3–5.
- **ChooseBaseCVModal (011)** is a shared dependency of NewApplicationPage (010) and CVCenterContent (016). Implement 011 before 010 and 016.
- **RichTextEditor (020)** → **GapQuestionCard (019)** → **GapAnalysisContent (018)**. Implement leaf-first within Batch 5.
- **PlanCard (026)** → **PlansSection (025)** → **BillingContent (021)**. Implement leaf-first within Batch 6.

---

## 2. One-Time Setup

Run this section exactly once before touching any spec.

---

### 2.1 AWS Amplify — replace S3+CloudFront

#### A. Create the Amplify app (AWS Console)

1. Open **AWS Console → Amplify → New app → Host web app**
2. Select **GitHub** as source → authorize → choose the `careervp` repo
3. Branch: **`ui-upgrade`** (you will push this branch in step 2.3 below; set it up now so Amplify is ready)
4. **Build settings** — Amplify auto-detects Next.js. Override the build spec with the content below (needed because the frontend lives in a subdirectory)

```yaml
# amplify.yml  — place at repo root
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - cd src/frontend
        - npm ci
    build:
      commands:
        - cd src/frontend
        - npm run typecheck
        - npm run build
  artifacts:
    baseDirectory: src/frontend/out
    files:
      - "**/*"
  cache:
    paths:
      - src/frontend/node_modules/**/*
```

5. **Environment variables** — add each in the Amplify console under *App settings → Environment variables*:

| Variable | Value source |
|---|---|
| `NEXT_PUBLIC_API_URL` | Same value as `secrets.API_URL` in current workflow |
| `NEXT_PUBLIC_COGNITO_USER_POOL_ID` | Same as current secret |
| `NEXT_PUBLIC_COGNITO_CLIENT_ID` | Same as current secret |

6. Click **Save and deploy**. Note the generated Amplify app ID (format: `dXXXXXXXXXXXX`). You will need it for CI.

#### B. Note the preview URL

After the first build succeeds, Amplify assigns a branch URL:
```
https://ui-upgrade.<app-id>.amplifyapp.com
```
This is your `AMPLIFY_PREVIEW_URL` for e2e tests.

#### C. (Optional) Custom domain

If you want a friendlier URL (e.g. `upgrade.careervp.app`), configure it under *App settings → Custom domains*. Not required for the upgrade workflow.

#### D. AWS CLI — verify the app exists

```bash
aws amplify list-apps --region us-east-1 \
  --query "apps[?name=='careervp-ui-upgrade'].{appId:appId,name:name,defaultDomain:defaultDomain}" \
  --output table
```

---

### 2.2 GitHub Secrets

Add these in **GitHub → repo → Settings → Secrets and variables → Actions**:

| Secret name | Value |
|---|---|
| `AMPLIFY_APP_ID` | The Amplify app ID from step 2.1A |
| `AMPLIFY_PREVIEW_URL` | `https://ui-upgrade.<app-id>.amplifyapp.com` |
| `E2E_TEST_EMAIL` | Email of your existing Cognito test user |
| `E2E_TEST_PASSWORD` | Password of your existing Cognito test user |
| `AWS_DEPLOY_ROLE_ARN` | Same IAM role already used by deploy-frontend.yml |

> **Note:** `API_URL`, `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID` already exist as secrets — no action needed for those.

---

### 2.3 Create the upgrade branch

```bash
# From main — make sure you are clean
git checkout main
git pull origin main

# Create and push the upgrade branch
git checkout -b ui-upgrade
git push -u origin ui-upgrade
```

Amplify will detect the push and queue its first (empty) build. It will succeed because there are no code changes yet. This validates the build config before you write any code.

---

### 2.4 GitHub Actions — unit check workflow

Create this file. It runs on every push to `ui-upgrade` and blocks the workflow if typecheck, vitest, or jest unit tests fail.

```yaml
# .github/workflows/ui-upgrade-checks.yml
name: UI Upgrade — Pre-merge Checks

on:
  push:
    branches: [ui-upgrade]
    paths:
      - "src/frontend/**"

permissions:
  contents: read

jobs:
  typecheck:
    name: TypeScript
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: src/frontend/package-lock.json
      - run: cd src/frontend && npm ci
      - run: cd src/frontend && npm run typecheck

  vitest-ui:
    name: Vitest UI unit tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: src/frontend/package-lock.json
      - run: cd src/frontend && npm ci
      - run: cd src/frontend && npx vitest run --config vitest.config.ts
        env:
          CI: true

  jest-unit:
    name: Jest unit tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: src/frontend/package-lock.json
      - run: cd src/frontend && npm ci
      - run: cd src/frontend && npm run test:unit -- --passWithNoTests
        env:
          CI: true
```

---

### 2.5 GitHub Actions — e2e smoke workflow

This workflow is **manually triggered** (`workflow_dispatch`). You run it after you confirm the Amplify deploy succeeded. It takes the Amplify preview URL as an optional input (defaults to the secret).

```yaml
# .github/workflows/e2e-smoke.yml
name: UI Upgrade — E2E Smoke Tests

on:
  workflow_dispatch:
    inputs:
      preview_url:
        description: "Amplify preview URL (leave blank to use secret)"
        required: false
        default: ""
      batch:
        description: "Batch to test (1-6, or 'all')"
        required: false
        default: "all"

permissions:
  contents: read

jobs:
  e2e:
    name: Playwright E2E — Batch ${{ github.event.inputs.batch }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: src/frontend/package-lock.json

      - name: Install frontend dependencies
        run: cd src/frontend && npm ci

      - name: Install Playwright browsers
        run: cd src/frontend && npx playwright install --with-deps chromium

      - name: Run Playwright e2e tests
        run: |
          BATCH="${{ github.event.inputs.batch }}"
          URL="${{ github.event.inputs.preview_url }}"
          BASE="${URL:-${{ secrets.AMPLIFY_PREVIEW_URL }}}"

          echo "Running e2e against: $BASE  (batch: $BATCH)"

          if [ "$BATCH" = "all" ]; then
            npx playwright test tests/e2e/ --config playwright.config.ts
          else
            npx playwright test tests/e2e/ --config playwright.config.ts \
              --grep "@batch$BATCH"
          fi
        env:
          BASE_URL: ${{ github.event.inputs.preview_url || secrets.AMPLIFY_PREVIEW_URL }}
          E2E_TEST_EMAIL: ${{ secrets.E2E_TEST_EMAIL }}
          E2E_TEST_PASSWORD: ${{ secrets.E2E_TEST_PASSWORD }}

      - name: Upload Playwright report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report-batch-${{ github.event.inputs.batch }}
          path: playwright-report/
          retention-days: 14
```

---

### 2.6 Playwright config

No `playwright.config.ts` exists in the repo yet. Create it at the **repo root** (because `tests/e2e/` is at the root).

```typescript
// playwright.config.ts  (repo root)
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false, // sequential — auth state is shared
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : 1,
  reporter: [["html"], ["list"]],

  use: {
    baseURL: process.env.BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    // Reuse authenticated session across tests in the same spec file
    storageState: "tests/e2e/.auth/user.json",
  },

  projects: [
    // Setup project — runs loginAs once, saves storageState
    {
      name: "setup",
      testMatch: /.*\.setup\.ts/,
      use: { storageState: undefined }, // no pre-existing state for setup
    },

    // Main browser project — depends on setup
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      dependencies: ["setup"],
    },
  ],

  // Do not start a local dev server — tests run against Amplify or localhost
  // webServer is intentionally omitted
});
```

---

### 2.7 Playwright auth helper

The e2e stubs all call `loginAs(page, 'test-user')`. Create the implementation plus the setup file that saves auth state.

#### Auth helper

```typescript
// tests/e2e/helpers/auth.ts
import type { Page } from "@playwright/test";

export interface TestUser {
  email: string;
  password: string;
}

const TEST_USERS: Record<string, TestUser> = {
  "test-user": {
    email: process.env.E2E_TEST_EMAIL ?? "",
    password: process.env.E2E_TEST_PASSWORD ?? "",
  },
};

/**
 * Navigate to /login and authenticate as the named test user.
 * Waits for redirect to /dashboard to confirm success.
 *
 * @example  await loginAs(page, 'test-user');
 */
export async function loginAs(page: Page, userName: keyof typeof TEST_USERS) {
  const user = TEST_USERS[userName];
  if (!user?.email || !user?.password) {
    throw new Error(
      `loginAs: credentials for "${userName}" not found. ` +
        `Set E2E_TEST_EMAIL and E2E_TEST_PASSWORD env vars.`
    );
  }

  await page.goto("/login");
  await page.waitForLoadState("networkidle");

  await page.getByLabel(/email/i).fill(user.email);
  await page.getByLabel(/password/i).fill(user.password);
  await page.getByRole("button", { name: /sign in|log in/i }).click();

  // Wait for redirect away from /login — indicates successful auth
  await page.waitForURL((url) => !url.pathname.includes("/login"), {
    timeout: 15_000,
  });
}
```

#### Global setup file (saves auth state once per run)

```typescript
// tests/e2e/global-setup.setup.ts
import { test as setup, expect } from "@playwright/test";
import { loginAs } from "./helpers/auth";
import path from "path";
import fs from "fs";

const AUTH_FILE = path.join(__dirname, ".auth/user.json");

setup("authenticate", async ({ page }) => {
  // Skip if auth file already fresh (< 1 hour old)
  if (fs.existsSync(AUTH_FILE)) {
    const age = Date.now() - fs.statSync(AUTH_FILE).mtimeMs;
    if (age < 60 * 60 * 1000) {
      console.log("Auth state cache hit — skipping login");
      return;
    }
  }

  await loginAs(page, "test-user");
  await expect(page).toHaveURL(/dashboard/);

  // Save signed-in cookies/localStorage for all subsequent tests
  fs.mkdirSync(path.dirname(AUTH_FILE), { recursive: true });
  await page.context().storageState({ path: AUTH_FILE });
  console.log("Auth state saved to", AUTH_FILE);
});
```

Add `.auth/` to `.gitignore`:

```bash
echo "tests/e2e/.auth/" >> .gitignore
```

---

### 2.8 Retire the S3 deploy workflow

The `deploy-frontend.yml` workflow deploys to S3+CloudFront. Once the Amplify setup is confirmed working (after Batch 1), disable it by adding a branch filter so it never fires on `ui-upgrade`, and add a note that it will be fully removed post-merge.

```yaml
# In deploy-frontend.yml — change the on: trigger:
on:
  push:
    branches:
      - main          # keep for now during transition
      # ui-upgrade intentionally excluded — Amplify handles it
    paths:
      - "src/frontend/**"
```

After the final merge to `main` (step 10), the `deploy-frontend.yml` workflow is deleted entirely and Amplify takes over for `main` as well.

---

## 3. Per-Spec Implementation Loop

Every spec follows this exact loop. Do not deviate.

```
┌─────────────────────────────────────────────────────┐
│  IMPLEMENT  →  LOCAL CHECK  →  COMMIT  →  PUSH      │
│       ↓                              ↓              │
│  (if tests fail, fix here)     CI runs unit checks  │
│                                      ↓              │
│                              Amplify auto-deploys   │
│                              (~3-5 min)             │
│                                      ↓              │
│                         YOU confirm deploy success  │
│                                      ↓              │
│                         (Batches 2-6 only)          │
│                         Trigger e2e smoke manually  │
│                                      ↓              │
│                         Update spec status          │
│                         implemented → validated     │
└─────────────────────────────────────────────────────┘
```

### 3.1 Understanding Vitest output during the upgrade

**There are 50 test stub files** pre-created at `tests/ui/unit/` and `tests/ui/integration/` (repo root) for all 26 specs. Vitest picks all of them up via the `tests/ui/**/*.test.tsx` glob. Files for unimplemented specs fail with `ERR_MODULE_NOT_FOUND` because they import components that don't exist yet.

**Classification rule — apply this to every failure you see:**

| Failure pattern | What it means | Action |
|---|---|---|
| `ERR_MODULE_NOT_FOUND` for a spec you **haven't** implemented | Expected noise — future stub importing a not-yet-created component | **Ignore. No action.** |
| `ERR_MODULE_NOT_FOUND` for the spec you **just** implemented | Test file path or import path mismatch — see below | Investigate |
| Actual assertion failure (`expected X to equal Y`) | Real bug in your implementation | Fix |

**If your own spec's tests show `ERR_MODULE_NOT_FOUND`:**
The test file was created at `tests/ui/unit/` (repo root) but CI Vitest only picks up
`src/frontend/tests/ui/`. Move the file and fix three things:

```bash
# 1. Move the file to the canonical location
mv tests/ui/unit/MyComponent.test.tsx        src/frontend/tests/ui/unit/
mv tests/ui/integration/MyComponent.test.tsx src/frontend/tests/ui/integration/

# 2. Fix component imports (remove the src/frontend/ prefix):
#    ../../../src/frontend/components/ui/Foo  →  ../../../components/ui/Foo

# 3. Add setup imports at the top of each test file:
#    import '../../vitest-setup';
#    import '../setup';

# 4. Replace any Jest globals with Vitest:
#    import { jest } from '@jest/globals'  →  import { vi } from 'vitest'
#    jest.fn()             →  vi.fn()
#    jest.clearAllMocks()  →  vi.clearAllMocks()
```

**This is why `verify-spec.sh` runs targeted, not the full suite.** The full suite will always show noise until all 26 specs are implemented.

---

### 3.2 Claude implementation prompt template

Use this prompt for each spec. Replace `[SPEC-ID]` and `[SPEC-TITLE]`.

```
Implement spec [SPEC-ID]: [SPEC-TITLE].

Source spec: docs/upgrade/specs/[SPEC-FILE].md

Rules:
1. Read the spec in full before writing any code.
2. Implement ONLY what is listed in the Fix Plan. Do not add features not in the spec.
3. Do not modify files outside the spec's "Files to modify" list without explicit justification.
4. After implementation, run the TARGETED verification — not the full vitest suite:
     ./scripts/ui-upgrade/verify-spec.sh [SPEC-ID]
   This runs only the tests for this spec plus the pre-existing regression suite.
   Do NOT run npx vitest run without a file filter — it will show ERR_MODULE_NOT_FOUND
   for all unimplemented future specs. That is expected noise, not your failure.
5. Write or update the unit test file referenced in the spec's Traceability Matrix.
   CRITICAL — get these three things right or the CI run will fail:

   a) FILE LOCATION — place test files at:
        src/frontend/tests/ui/unit/<ComponentName>.test.tsx       ← unit
        src/frontend/tests/ui/integration/<ComponentName>.test.tsx ← integration
      NOT at tests/ui/unit/ (that is the repo-root stub directory, invisible to CI).

   b) IMPORT PATHS — all imports inside the test file must be relative to src/frontend/:
        import { Foo } from '../../../components/ui/Foo';   ✓
        import { Foo } from '../../../src/frontend/...'     ✗ (double-prefix)
      Also add these two setup lines at the top of every test file:
        import '../../vitest-setup';
        import '../setup';
      (required for toBeInTheDocument(), toBeVisible(), toHaveAttribute(), etc.)

   c) TEST FRAMEWORK — use Vitest, not Jest:
        import { describe, it, expect, vi, beforeEach } from 'vitest';   ✓
        import { jest } from '@jest/globals';                             ✗
      Replace jest.fn() → vi.fn(), jest.clearAllMocks() → vi.clearAllMocks(), etc.

   Tests must cover every AC listed. Do not use placeholder/TODO test bodies.
6. Update the spec file status from `draft` to `implemented` and fill in the
   code_reference column (file:line) in the Traceability Matrix.
7. Do NOT mark the spec `validated`. That gate requires live Amplify evidence.
8. Do NOT change tokens.css unless the spec explicitly says to.
9. Do NOT pre-create test stub files for other specs. One spec, one test file.
10. Report: list of files changed, targeted test results (pass count), and any
    deviation from the spec with justification.
```

### 3.2 Local verification script

Run this before every commit. It catches issues before CI does.

```bash
#!/usr/bin/env bash
# scripts/ui-upgrade/verify-spec.sh
# Usage: ./scripts/ui-upgrade/verify-spec.sh FE-UI-001

set -euo pipefail

SPEC_ID="${1:-}"
if [[ -z "$SPEC_ID" ]]; then
  echo "Usage: $0 <SPEC-ID>  e.g. $0 FE-UI-001"
  exit 1
fi

cd "$(git rev-parse --show-toplevel)/src/frontend"

echo ""
echo "══════════════════════════════════════"
echo "  Verifying $SPEC_ID"
echo "══════════════════════════════════════"

echo ""
echo "▶ TypeScript..."
npm run typecheck
echo "  ✓ TypeScript clean"

echo ""
echo "▶ Vitest UI tests..."
npx vitest run --config vitest.config.ts --reporter verbose 2>&1 | tail -20
echo "  ✓ Vitest passed"

echo ""
echo "▶ Jest unit tests..."
npm run test:unit -- --passWithNoTests 2>&1 | tail -20
echo "  ✓ Jest unit passed"

echo ""
echo "══════════════════════════════════════"
echo "  $SPEC_ID local checks PASSED"
echo "  Ready to commit."
echo "══════════════════════════════════════"
```

```bash
chmod +x scripts/ui-upgrade/verify-spec.sh
mkdir -p scripts/ui-upgrade
```

### 3.3 Commit convention

One commit per spec, always:

```bash
# Example for FE-UI-001
git add src/frontend/components/ui/Badge.tsx \
        src/frontend/components/ui/StatusBadge.tsx \
        src/frontend/tests/ui/unit/Badge.test.tsx \
        docs/upgrade/specs/FE-UI-001-badge-soft-variant.md

git commit -m "feat(ui): FE-UI-001 Badge soft variant

- Add soft?: boolean prop to Badge and StatusBadge
- Add softVariantStyles map (green/blue/amber/gray tints)
- Error variant unchanged (solid red) per spec AC-003
- All 12 ACs covered in Badge.test.tsx

Spec status: implemented"
```

### 3.4 How to trigger the e2e smoke run (Batches 2–6)

After confirming Amplify shows "Deployment successful":

```bash
# Via GitHub CLI (recommended)
gh workflow run e2e-smoke.yml \
  --ref ui-upgrade \
  --field batch=<BATCH_NUMBER> \
  --field preview_url="https://ui-upgrade.<app-id>.amplifyapp.com"

# Watch the run
gh run list --workflow=e2e-smoke.yml --limit=1
gh run watch  # streams live output
```

Or from the GitHub UI: **Actions → UI Upgrade — E2E Smoke Tests → Run workflow**.

### 3.5 Checking Amplify deploy status from CLI

```bash
# Get the latest build for the ui-upgrade branch
aws amplify list-jobs \
  --app-id "$AMPLIFY_APP_ID" \
  --branch-name ui-upgrade \
  --region us-east-1 \
  --max-results 1 \
  --query "jobSummaries[0].{status:status,commitId:commitId,startTime:startTime}" \
  --output table
```

Status will be `RUNNING`, `SUCCEED`, or `FAILED`.

---

## 4. Batch 1 — UI Primitives

**Specs:** FE-UI-001, FE-UI-002, FE-UI-006, FE-UI-007
**Gate:** Unit tests only. No live URL required. No e2e smoke run after this batch.
**Why first:** These components have zero external dependencies and cascade to every other component in the app. Must land before any layout or feature work.

### Implementation order within batch

```
FE-UI-006 ErrorBoundary  →  FE-UI-007 Spinner  →  FE-UI-002 ProgressBar  →  FE-UI-001 Badge
```

ErrorBoundary and Spinner first because they have no inbound dependencies from other specs. Badge last because it is consumed by StatusBadge, ModuleCard, and JobsTable — leave it until the primitive shape is locked.

### Spec prompts

#### FE-UI-006 — ErrorBoundary

```
Implement spec FE-UI-006: Finalize ErrorBoundary — behavior contract for redesign.

Source spec: docs/upgrade/specs/FE-UI-006-errorboundary-behavior-contract.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- ErrorBoundary has ZERO existing test coverage (noted in project instructions cascade risk table).
- The test file referenced in the Traceability Matrix is tests/ui/unit/ErrorBoundary.test.tsx.
  Create it from scratch — cover every AC.
- Do not change any component that imports ErrorBoundary. This spec is self-contained.
```

#### FE-UI-007 — Spinner

```
Implement spec FE-UI-007: Finalize Spinner — behavior contract for redesign.

Source spec: docs/upgrade/specs/FE-UI-007-spinner-behavior-contract.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- Spinner has ZERO existing test coverage.
- Test file: src/frontend/tests/ui/unit/Spinner.test.tsx. Create from scratch.
- Spinner is a pure presentational component. No API calls, no state.
```

#### FE-UI-002 — ProgressBar

```
Implement spec FE-UI-002: Upgrade ProgressBar — add visible label row and rounded ends.

Source spec: docs/upgrade/specs/FE-UI-002-progressbar-label-and-rounding.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- ProgressBar is consumed by GapAnalysisContent (FE-UI-018, Batch 5). The label row
  and rounded ends must be backward-compatible — existing usages without a label prop
  must render identically to today.
- Test file: src/frontend/tests/ui/unit/ProgressBar.test.tsx.
```

#### FE-UI-001 — Badge

```
Implement spec FE-UI-001: Upgrade Badge — add soft/outlined rendering variant.

Source spec: docs/upgrade/specs/FE-UI-001-badge-soft-variant.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- Badge is a high cascade-risk component. Read the "Imports this component" list in the
  Architecture Map before touching anything.
- Modify ONLY Badge.tsx and StatusBadge.tsx. Do not touch ModuleCard or JobsTable —
  those are separate specs (Batches 2 and 3).
- The soft prop must be optional (boolean | undefined) and default to false.
  Existing usages with no soft prop must render identically (AC-008, AC-009 enforce this).
- Test file: src/frontend/tests/ui/unit/Badge.test.tsx. All 12 ACs must be covered.
```

### Batch 1 completion checklist

```
[ ] FE-UI-006 status = implemented, Traceability Matrix filled, tests pass
[ ] FE-UI-007 status = implemented, Traceability Matrix filled, tests pass
[ ] FE-UI-002 status = implemented, Traceability Matrix filled, tests pass
[ ] FE-UI-001 status = implemented, Traceability Matrix filled, tests pass
[ ] All 4 commits pushed to ui-upgrade
[ ] GitHub Actions ui-upgrade-checks.yml green on all 4 commits
[ ] No e2e run needed — Batch 1 is unit-only
```

---

## 5. Batch 2 — Layout Shell

**Specs:** FE-UI-003, FE-UI-004, FE-UI-005
**Gate:** Unit tests (pre-merge) + e2e smoke after deploy.
**Why before Batch 3:** AppSidebar adds the nav items for `/cover-letters` and `/tailored-cvs`. HubLayout restructures the application hub wrapper. All downstream page specs depend on this shell being in place.

### Implementation order within batch

```
FE-UI-003 AppSidebar  →  FE-UI-004 AppHeader  →  FE-UI-005 HubLayout
```

Sidebar first so nav links are available when HubLayout is tested on the live site.

### Spec prompts

#### FE-UI-003 — AppSidebar

```
Implement spec FE-UI-003: Upgrade AppSidebar — restructure navigation from 5 to 7 items
with updated icons and active state.

Source spec: docs/upgrade/specs/FE-UI-003-appsidebar-nav-restructure.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- The two new nav items (/cover-letters, /tailored-cvs) link to pages that do NOT exist yet
  (they are created in Batch 4). The nav links must be present and functional even though
  the destination pages 404 until Batch 4 is deployed. This is expected and acceptable.
- Verify the existing 5 nav items still render with correct routes and icons after the change.
- Test file: src/frontend/tests/ui/unit/AppSidebar.test.tsx.
```

#### FE-UI-004 — AppHeader

```
Implement spec FE-UI-004: Upgrade AppHeader — credits label format and account dropdown
menu items.

Source spec: docs/upgrade/specs/FE-UI-004-appheader-credits-and-dropdown.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- The account dropdown requires the user to be authenticated. Unit tests must mock
  the auth context — do not require a live Cognito session in Vitest.
- Test file: src/frontend/tests/ui/unit/AppHeader.test.tsx.
```

#### FE-UI-005 — HubLayout

```
Implement spec FE-UI-005: Upgrade HubLayout — add JobDetailHeader slot and adjust module
grid to 2-column default.

Source spec: docs/upgrade/specs/FE-UI-005-hublayout-job-header-and-grid.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- HubLayout wraps ALL /applications/[id] sub-pages. The grid change is high-risk.
  Run a visual diff mentally against the screenshots for: top, middle, bottom hub sections.
- The JobDetailHeader slot is additive (new prop). The layout must still render correctly
  when the slot is not provided (backward-compatible with current usage until Batch 3 wires it up).
- Test file: src/frontend/tests/ui/unit/HubLayout.test.tsx.
```

### Batch 2 e2e smoke tests

After all 3 specs are committed and Amplify reports success, trigger the smoke run:

```bash
gh workflow run e2e-smoke.yml \
  --ref ui-upgrade \
  --field batch=2

  gh workflow run e2e-smoke.yml \
  --ref ui-upgrade \
  --field batch=2 \
  --field update_snapshots=true
```

**What to verify manually on the Amplify URL before running e2e:**
- Sidebar shows 7 items (Dashboard, Applications, Cover Letters, Tailored CVs, CV Center, Billing, Settings)
- Active state highlights correctly on each route
- `/cover-letters` and `/tailored-cvs` return 404 (expected — Batch 4)
- Header credits label format matches mockup
- Account dropdown opens and shows correct items
- `/applications/[id]` renders the 2-column grid

### Batch 2 completion checklist

```
[ ] FE-UI-003 status = implemented, tests pass
[ ] FE-UI-004 status = implemented, tests pass
[ ] FE-UI-005 status = implemented, tests pass
[ ] All 3 commits pushed, ui-upgrade-checks.yml green
[ ] Amplify build: SUCCEED
[ ] Manual visual check on Amplify URL passed
[ ] e2e-smoke.yml batch=2 triggered and green
[ ] FE-UI-003, 004, 005 status updated to validated
```

---

## 6. Batch 3 — Dashboard & New Application Flow

**Specs:** FE-UI-009, FE-UI-008, FE-UI-011, FE-UI-010
**Gate:** Unit tests + e2e smoke. Auth required.
**Why this order:** StatsRow and JobsTable are dashboard-level and independent. ChooseBaseCVModal (011) must be built before NewApplicationPage (010) since it is an import dependency.

### Implementation order within batch

```
FE-UI-009 StatsRow  →  FE-UI-008 JobsTable  →  FE-UI-011 ChooseBaseCVModal  →  FE-UI-010 NewApplicationPage
```

### Spec prompts

#### FE-UI-009 — StatsRow

```
Implement spec FE-UI-009: Upgrade StatsRow — increase pill corner radius and add loading skeleton.

Source spec: docs/upgrade/specs/FE-UI-009-statsrow-pill-radius.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- StatsRow is on /dashboard only. No cascade risk to application pages.
- Loading skeleton uses animate-pulse — test in Vitest by mocking the data-loading state.
- Test file: src/frontend/tests/ui/unit/StatsRow.test.tsx.
```

#### FE-UI-008 — JobsTable

```
Implement spec FE-UI-008: Upgrade JobsTable — dual-mode (dashboard widget + applications full-list).

Source spec: docs/upgrade/specs/FE-UI-008-jobstable-dual-mode-upgrade.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- JobsTable now renders in two modes: compact widget mode on /dashboard, and full-list
  mode on /applications. The mode is determined by a prop (check the spec for the exact
  prop name).
- Badge (FE-UI-001, Batch 1) is already implemented. JobsTable may now use Badge with
  soft={false} for the dashboard and soft={true} for the applications list if the spec
  calls for it.
- The existing dashboard tests must still pass — the widget mode is backward-compatible.
- Test file: src/frontend/tests/ui/unit/JobsTable.test.tsx.
```

#### FE-UI-011 — ChooseBaseCVModal

```
Implement spec FE-UI-011: Create ChooseBaseCVModal — shared CV picker with choice and
upload-only modes.

Source spec: docs/upgrade/specs/FE-UI-011-choosebasecvmodal-shared-cv-picker.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- ChooseBaseCVModal is a NEW component (does not exist yet). Create the file at
  src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx.
- It operates in two modes: choice mode (used by NewApplicationPage) and upload-only
  mode (used by CVCenterContent, Batch 4). Both modes must be implemented now.
- The API call for fetching existing CVs uses GET /users/me/cv — mock this in Vitest.
- Test file: src/frontend/tests/ui/unit/ChooseBaseCVModal.test.tsx.
```

#### FE-UI-010 — NewApplicationPage

```
Implement spec FE-UI-010: Replace NewApplicationModal — full-page form with back navigation
and CV picker.

Source spec: docs/upgrade/specs/FE-UI-010-newapplicationpage-replace-modal.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- This replaces the modal with a new page at /applications/new. Create the page file at
  src/frontend/app/applications/new/page.tsx.
- ChooseBaseCVModal (FE-UI-011) is already implemented — import it.
- The dashboard must no longer open the old NewApplicationModal. If the old modal trigger
  still exists in JobsTable or dashboard/page.tsx, update those references to navigate to
  /applications/new instead. This is within scope because it is required for the spec to work.
- API calls used: GET /users/me/cv, POST /jobs — mock both in Vitest.
- Test file: src/frontend/tests/ui/unit/NewApplicationPage.test.tsx.
```

### Batch 3 completion checklist

```
[ ] FE-UI-009 status = implemented, tests pass
[ ] FE-UI-008 status = implemented, tests pass
[ ] FE-UI-011 status = implemented, tests pass
[ ] FE-UI-010 status = implemented, tests pass
[ ] All 4 commits pushed, ui-upgrade-checks.yml green
[ ] Amplify build: SUCCEED
[ ] Manual smoke: /dashboard renders StatsRow + JobsTable widget correctly
[ ] Manual smoke: /applications shows JobsTable in full-list mode
[ ] Manual smoke: "New Application" navigates to /applications/new (not modal)
[ ] Manual smoke: CV picker works in choice mode
[ ] e2e-smoke.yml batch=3 green
[ ] FE-UI-009, 008, 011, 010 status = validated
```

---

## 7. Batch 4 — New List Pages & CV Center

**Specs:** FE-UI-013, FE-UI-012, FE-UI-015, FE-UI-014, FE-UI-017, FE-UI-016
**Gate:** Unit tests + e2e smoke. Auth required. AppSidebar (003) must be live (Batch 2).
**Why this order:** Table components before page components (pages import their table).

### Implementation order within batch

```
FE-UI-013 CoverLettersListTable
    → FE-UI-012 CoverLettersPage
FE-UI-015 TailoredCVsListTable
    → FE-UI-014 TailoredCVsPage
FE-UI-017 BaseCVsTable
    → FE-UI-016 CVCenterContent
```

The three sub-groups are independent of each other and can be implemented in parallel if you choose, but commit them in the order shown to keep the branch history readable.

### Spec prompts

#### FE-UI-013 — CoverLettersListTable

```
Implement spec FE-UI-013: CoverLettersListTable — new list table.

Source spec: docs/upgrade/specs/FE-UI-013-coverletterslisttable-new-list-table.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- NEW component. Create at src/frontend/components/CoverLettersListTable/CoverLettersListTable.tsx.
- API: GET /cover-letters — mock in Vitest.
- Badge (soft variant, Batch 1) is available. Use it for status display per the spec.
- Test file: src/frontend/tests/ui/unit/CoverLettersListTable.test.tsx.
```

#### FE-UI-012 — CoverLettersPage

```
Implement spec FE-UI-012: CoverLettersPage — new list page.

Source spec: docs/upgrade/specs/FE-UI-012-coverletterspage-new-list-page.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- NEW page. Create at src/frontend/app/cover-letters/page.tsx.
- CoverLettersListTable (FE-UI-013) is already implemented — import it.
- The AppSidebar nav item for /cover-letters is already live (Batch 2). This page
  resolves the 404 that has existed since Batch 2.
- Test file: src/frontend/tests/ui/unit/CoverLettersPage.test.tsx.
```

#### FE-UI-015 — TailoredCVsListTable

```
Implement spec FE-UI-015: TailoredCVsListTable — new list table.

Source spec: docs/upgrade/specs/FE-UI-015-tailoredcvslisttable-new-list-table.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- NEW component. Create at src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx.
- API: GET /cv-tailorings — mock in Vitest.
- Test file: src/frontend/tests/ui/unit/TailoredCVsListTable.test.tsx.
```

#### FE-UI-014 — TailoredCVsPage

```
Implement spec FE-UI-014: TailoredCVsPage — new list page.

Source spec: docs/upgrade/specs/FE-UI-014-tailoredcvspage-new-list-page.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- NEW page. Create at src/frontend/app/tailored-cvs/page.tsx.
- TailoredCVsListTable (FE-UI-015) is already implemented — import it.
- Resolves the /tailored-cvs 404 that has existed since Batch 2.
- Test file: src/frontend/tests/ui/unit/TailoredCVsPage.test.tsx.
```

#### FE-UI-017 — BaseCVsTable

```
Implement spec FE-UI-017: new BaseCVsTable — multi-CV data table with sorting and status badges.

Source spec: docs/upgrade/specs/FE-UI-017-basecvstable-new-list-table.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- NEW component. Create at src/frontend/components/BaseCVsTable/BaseCVsTable.tsx.
- API: GET /users/me/cv — mock in Vitest.
- Badge with soft variant is available. Status display should use soft badges per the spec.
- Test file: src/frontend/tests/ui/unit/BaseCVsTable.test.tsx.
```

#### FE-UI-016 — CVCenterContent

```
Implement spec FE-UI-016: replace CVCenterContent — single-CV form to multi-CV table listing page.

Source spec: docs/upgrade/specs/FE-UI-016-cvcentercontent-replace-with-table-listing.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- This replaces the existing single-CV form on /cv-center with a table listing.
  BaseCVsTable (FE-UI-017) and ChooseBaseCVModal (FE-UI-011, Batch 3) are already implemented.
- The old CVCenterContent code is being replaced, not extended. Delete the old single-CV
  form implementation. The spec is authoritative on what the new page renders.
- API: GET /users/me/cv, POST /users/me/cv — both used; mock in Vitest.
- Test file: src/frontend/tests/ui/unit/CVCenterContent.test.tsx.
```

### Batch 4 completion checklist

```
[ ] FE-UI-013, 012, 015, 014, 017, 016 status = implemented, tests pass
[ ] All 6 commits pushed, ui-upgrade-checks.yml green
[ ] Amplify build: SUCCEED
[ ] Manual smoke: /cover-letters renders list (not 404)
[ ] Manual smoke: /tailored-cvs renders list (not 404)
[ ] Manual smoke: /cv-center renders table view (not old single-CV form)
[ ] e2e-smoke.yml batch=4 green
[ ] All 6 specs status = validated
```

---

## 8. Batch 5 — Gap Analysis

**Specs:** FE-UI-020, FE-UI-019, FE-UI-018
**Gate:** Unit tests + e2e smoke. Auth + a real application with gap questions required.
**Why leaf-first:** RichTextEditor is a standalone TipTap wrapper. GapQuestionCard imports it. GapAnalysisContent imports GapQuestionCard and ProgressBar.

### Implementation order within batch

```
FE-UI-020 RichTextEditor  →  FE-UI-019 GapQuestionCard  →  FE-UI-018 GapAnalysisContent
```

### Spec prompts

#### FE-UI-020 — RichTextEditor

```
Implement spec FE-UI-020: new RichTextEditor — TipTap rich text input with toolbar and
Markdown storage.

Source spec: docs/upgrade/specs/FE-UI-020-richtexteditor-new.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- NEW component. Create at src/frontend/components/RichTextEditor/RichTextEditor.tsx.
- TipTap is the chosen library. Before writing any code, use the Context7 MCP tool to
  fetch the current TipTap docs: resolve-library-id for "tiptap" then query-docs for
  "editor setup react typescript". Verify the exact import paths before implementing.
- Markdown storage means the component stores/outputs Markdown text (not HTML).
  Use the @tiptap/extension-markdown package if available, or implement a Markdown
  serializer. Check the spec for the authoritative approach.
- This component has no API calls. It is fully controlled (value + onChange pattern).
- Test file: src/frontend/tests/ui/unit/RichTextEditor.test.tsx. Test the toolbar actions and
  controlled value behavior.
```

#### FE-UI-019 — GapQuestionCard

```
Implement spec FE-UI-019: new GapQuestionCard — per-question card with edit lifecycle
and collapsed advanced section.

Source spec: docs/upgrade/specs/FE-UI-019-gapquestioncard-new.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- NEW component. Create at src/frontend/components/GapQuestionCard/GapQuestionCard.tsx.
- RichTextEditor (FE-UI-020) is already implemented — import it for the answer input.
- The edit lifecycle states (read → editing → saving → saved/error) must be managed
  internally in the card. No parent state required for the lifecycle.
- Test file: src/frontend/tests/ui/unit/GapQuestionCard.test.tsx. Cover all lifecycle state transitions.
```

#### FE-UI-018 — GapAnalysisContent

```
Implement spec FE-UI-018: modify GapAnalysisContent — restructure to per-question editing
with progress bar.

Source spec: docs/upgrade/specs/FE-UI-018-gapanalysiscontent-restructure.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- This modifies the existing gap analysis page at src/frontend/app/applications/[id]/gap-analysis/page.tsx.
- GapQuestionCard (FE-UI-019) and ProgressBar (FE-UI-002, Batch 1) are both available.
- The module pages use direct api.* calls in useEffect (not React Query) — preserve this pattern.
- API calls: GET /jobs/{jobId}/gap-questions, POST /jobs/{jobId}/gap-responses,
  GET /applications/{application_id}, GET /users/me/cv — mock all in Vitest.
- Test file: src/frontend/tests/ui/unit/GapAnalysisContent.test.tsx. Cover the progress bar update
  as questions are answered.
```

### Batch 5 e2e note

The e2e tests for gap analysis require an application that has gap questions generated. Before triggering the e2e smoke run, ensure your Cognito test user has at least one application with gap questions in the dev environment.

```bash
gh workflow run e2e-smoke.yml \
  --ref ui-upgrade \
  --field batch=5
```

### Batch 5 completion checklist

```
[ ] FE-UI-020, 019, 018 status = implemented, tests pass
[ ] All 3 commits pushed, ui-upgrade-checks.yml green
[ ] Amplify build: SUCCEED
[ ] Test user has application with gap questions in dev env
[ ] Manual smoke: /applications/[id]/gap-analysis shows per-question card layout
[ ] Manual smoke: ProgressBar advances as questions are answered
[ ] Manual smoke: RichTextEditor toolbar renders and saves Markdown
[ ] e2e-smoke.yml batch=5 green
[ ] FE-UI-020, 019, 018 status = validated
```

---

## 9. Batch 6 — Billing

**Specs:** FE-UI-026, FE-UI-025, FE-UI-022, FE-UI-023, FE-UI-024, FE-UI-021
**Gate:** Unit tests + e2e smoke. Auth + subscription data required.
**Why leaf-first:** PlanCard → PlansSection. SubscriptionCard, UsageCard, BillingInfoCard are independent leaves. BillingContent assembles all of them.

### Implementation order within batch

```
FE-UI-026 PlanCard
FE-UI-025 PlansSection        (imports PlanCard)
FE-UI-022 SubscriptionCard
FE-UI-023 UsageCard
FE-UI-024 BillingInfoCard
FE-UI-021 BillingContent      (assembles all of the above)
```

The first five can be implemented in any order relative to each other (they have no intra-batch dependencies except PlanCard → PlansSection). Implement BillingContent last.

### Spec prompts

#### FE-UI-026 — PlanCard

```
Implement spec FE-UI-026: new PlanCard — data-driven pricing card with current/recommended/
selectable states.

Source spec: docs/upgrade/specs/FE-UI-026-plancard-new.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- NEW component. Create at src/frontend/components/billing/PlanCard.tsx.
- Three visual states: current (user's active plan), recommended (highlighted), selectable.
  The state is prop-driven (data in, no internal state for selection).
- API: none directly. PlanCard is purely presentational.
- Test file: src/frontend/tests/ui/unit/PlanCard.test.tsx. Cover all three states.
```

#### FE-UI-025 — PlansSection

```
Implement spec FE-UI-025: new PlansSection — 3-tier pricing section with scroll anchor on
/billing page.

Source spec: docs/upgrade/specs/FE-UI-025-planssection-new.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- NEW component. Create at src/frontend/components/billing/PlansSection.tsx.
- PlanCard (FE-UI-026) is already implemented — import it.
- The scroll anchor (#plans) must be a real HTML id attribute on the section wrapper.
- Test file: src/frontend/tests/ui/unit/PlansSection.test.tsx.
```

#### FE-UI-022 — SubscriptionCard

```
Implement spec FE-UI-022: new SubscriptionCard — current subscription status card with
state badges.

Source spec: docs/upgrade/specs/FE-UI-022-subscriptioncard-new.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- NEW component. Create at src/frontend/components/billing/SubscriptionCard.tsx.
- Badge (soft variant, Batch 1) is available for subscription status display.
- API: GET /users/me/subscription — mock in Vitest.
- Test file: src/frontend/tests/ui/unit/SubscriptionCard.test.tsx. Cover trial, active, and cancelled states.
```

#### FE-UI-023 — UsageCard

```
Implement spec FE-UI-023: new UsageCard — credits usage display with upgrade link.

Source spec: docs/upgrade/specs/FE-UI-023-usagecard-new.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- NEW component. Create at src/frontend/components/billing/UsageCard.tsx.
- API: GET /users/me/usage — mock in Vitest.
- ProgressBar (FE-UI-002, Batch 1) may be used for the credits bar if the spec calls for it.
  Check the spec before assuming.
- Test file: src/frontend/tests/ui/unit/UsageCard.test.tsx.
```

#### FE-UI-024 — BillingInfoCard

```
Implement spec FE-UI-024: new BillingInfoCard — payment method display with Manage Billing CTA.

Source spec: docs/upgrade/specs/FE-UI-024-billinginfocard-new.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- NEW component. Create at src/frontend/components/billing/BillingInfoCard.tsx.
- The Manage Billing CTA calls POST /billing/portal — mock in Vitest.
- Test file: src/frontend/tests/ui/unit/BillingInfoCard.test.tsx.
```

#### FE-UI-021 — BillingContent

```
Implement spec FE-UI-021: modify BillingContent — restructure page to 3 stacked cards +
Plans section.

Source spec: docs/upgrade/specs/FE-UI-021-billingcontent-page-restructure.md

Rules (standard — see section 3.1 of the deployment guide).

Additional context:
- This replaces the existing billing page layout. SubscriptionCard, UsageCard, BillingInfoCard,
  and PlansSection are all already implemented — assemble them here.
- API calls: POST /billing/checkout, POST /billing/portal, GET /users/me/subscription,
  GET /users/me/usage — mock all in Vitest.
- The Plans section must be reachable via the #plans scroll anchor.
- Test file: src/frontend/tests/ui/unit/BillingContent.test.tsx. Cover card assembly and CTA wiring.
```

### Batch 6 completion checklist

```
[ ] FE-UI-026, 025, 022, 023, 024, 021 status = implemented, tests pass
[ ] All 6 commits pushed, ui-upgrade-checks.yml green
[ ] Amplify build: SUCCEED
[ ] Manual smoke: /billing shows 3 cards stacked + Plans section below
[ ] Manual smoke: Manage Billing CTA fires correctly
[ ] Manual smoke: #plans anchor scroll works
[ ] e2e-smoke.yml batch=6 green
[ ] All 6 specs status = validated
```

---

## 10. Final Merge to Main

Run this section only after **all 26 specs are `validated`** and the Amplify preview has been signed off visually against every mockup screenshot.

### 10.1 Pre-merge final check

```bash
# From ui-upgrade branch
./scripts/ui-upgrade/verify-spec.sh ALL

# Confirm spec statuses
grep -r "^status:" docs/upgrade/specs/*.md | grep -v "validated" && echo "FAIL: not all specs validated" || echo "OK: all specs validated"

# Run full test suite locally
cd src/frontend
npm run typecheck
npx vitest run --config vitest.config.ts
npm run test:unit
npm run test:integration -- --passWithNoTests
```

### 10.2 Add main to Amplify

Before merging, add `main` as a second Amplify branch so the production deployment is handled by Amplify from day one.

```bash
# AWS CLI — add main branch to Amplify
aws amplify create-branch \
  --app-id "$AMPLIFY_APP_ID" \
  --branch-name main \
  --region us-east-1

# Set the same environment variables for main as ui-upgrade has
# (Do this in the Amplify Console → App settings → Environment variables → Branch-specific)
```

### 10.3 Merge

```bash
# Use the existing safe merge helper
./scripts/git/safe_merge_to_main.sh ui-upgrade
```

### 10.4 Retire deploy-frontend.yml

```bash
# Delete the old S3 deployment workflow
git rm .github/workflows/deploy-frontend.yml
git commit -m "chore: remove S3 deploy workflow — replaced by AWS Amplify"
git push origin main
```

### 10.5 Verify production on main

```bash
# Wait for Amplify main build to complete
aws amplify list-jobs \
  --app-id "$AMPLIFY_APP_ID" \
  --branch-name main \
  --region us-east-1 \
  --max-results 1 \
  --query "jobSummaries[0].{status:status}" \
  --output text

# Trigger a final e2e run against production
gh workflow run e2e-smoke.yml \
  --ref main \
  --field batch=all \
  --field preview_url="https://main.<app-id>.amplifyapp.com"
```

### 10.6 Post-merge cleanup

```bash
# Tag the release
git tag -a "ui-upgrade-v1.0" -m "UI Upgrade complete — all 26 specs validated"
git push origin ui-upgrade-v1.0

# Archive the upgrade branch (do not delete — preserves spec history)
# The branch remains in GitHub for reference but Amplify auto-deploy for it can be disabled:
aws amplify delete-branch \
  --app-id "$AMPLIFY_APP_ID" \
  --branch-name ui-upgrade \
  --region us-east-1
```

---

## Appendix A — Spec status quick reference

To check the current status of all specs at any time:

```bash
grep -r "^status:" docs/upgrade/specs/*.md | \
  sed 's/docs\/upgrade\/specs\///' | \
  sed 's/\.md:status: /\t/' | \
  column -t
```

## Appendix B — Amplify build troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Build fails: `Cannot find module` | `npm ci` ran in wrong directory | Check `amplify.yml` — `cd src/frontend` before `npm ci` |
| Build fails: `NEXT_PUBLIC_*` undefined | Env vars not set in Amplify Console | Add under App settings → Environment variables |
| Build fails: typecheck error | Spec introduced a type error | Fix locally, re-push |
| Build succeeds but page 404s | `out/` directory not produced | Confirm `next.config.js` has `output: 'export'` |
| E2E: `loginAs` times out | Auth form selector mismatch | Update `page.getByLabel(/email/i)` to match the actual label text on the login page |
| E2E: storageState stale | Cognito token expired | Delete `tests/e2e/.auth/user.json` and re-run setup |

## Appendix C — Environment variable checklist for Amplify

Before the first Amplify build, verify all of these are set in the Amplify Console:

```
NEXT_PUBLIC_API_URL              ← from current secrets.API_URL
NEXT_PUBLIC_COGNITO_USER_POOL_ID ← from current secrets.COGNITO_USER_POOL_ID
NEXT_PUBLIC_COGNITO_CLIENT_ID    ← from current secrets.COGNITO_CLIENT_ID
```

These are the only three `NEXT_PUBLIC_` variables consumed by the build (confirmed from `deploy-frontend.yml` env block).
