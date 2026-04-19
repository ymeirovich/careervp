# Test Implementation Instructions

## Prerequisites

Install test dependencies before running any tests:

```bash
cd src/frontend
npm install --save-dev \
  vitest \
  @vitest/ui \
  @testing-library/react \
  @testing-library/user-event \
  @testing-library/jest-dom \
  msw \
  @playwright/test \
  happy-dom
```

---

## 1. Unit Tests (Vitest + React Testing Library)

**Location:** `src/frontend/tests/unit/`

**Setup file:** `src/frontend/tests/setup.ts`

```ts
import "@testing-library/jest-dom";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => cleanup());
```

**Vitest config** (`src/frontend/vitest.config.ts`):

```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "happy-dom",
    setupFiles: ["./tests/setup.ts"],
    globals: true,
  },
});
```

**Run unit tests:**

```bash
cd src/frontend
npx vitest run tests/unit/
```

**Run with watch mode during development:**

```bash
npx vitest tests/unit/ --watch
```

**What to implement first (in order):**

1. `src/frontend/types/enums.ts` — HubStatus, ModuleStatus, ModuleType enums
2. `src/frontend/adapters/mapApplicationDataToHubState.ts` — adapter functions
3. `src/frontend/components/ModuleCard/ModuleCard.tsx` — the core component

The unit tests for adapters (`state-adapters.test.ts`) have no UI dependencies and should pass before building any React components.

---

## 2. Integration Tests (Vitest + MSW)

**Location:** `src/frontend/tests/integration/`

**MSW setup** (`src/frontend/tests/msw-setup.ts`):

```ts
import { setupServer } from "msw/node";
import { beforeAll, afterAll, afterEach } from "vitest";

export const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

Import this in each integration test file:

```ts
import "../msw-setup";
```

**Run integration tests:**

```bash
npx vitest run tests/integration/
```

**Order of implementation:**

1. Implement `src/frontend/api/client.ts` (base API client)
2. Implement `src/frontend/hooks/useModuleStatus.ts` (polling hook)
3. Implement `src/frontend/contexts/AuthContext.tsx` (auth context)
4. Then run `api-polling.test.ts` and `cognito-auth.test.ts`

---

## 3. E2E Tests (Playwright)

**Location:** `src/frontend/tests/e2e/`

**Playwright config** (`src/frontend/playwright.config.ts`):

```ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: "html",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "Mobile Chrome", use: { ...devices["Pixel 5"] } },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
  },
});
```

**Install Playwright browsers:**

```bash
npx playwright install --with-deps chromium
```

**Run E2E tests:**

```bash
# Requires dev server running at localhost:3000
npx playwright test

# Run specific test file
npx playwright test tests/e2e/application-hub-flow.e2e.test.ts

# Run with UI mode (recommended during development)
npx playwright test --ui
```

**Environment variables for E2E:**

```bash
# .env.test.local
E2E_TEST_EMAIL=test@careervp.com
E2E_TEST_PASSWORD=TestPassword1!
```

**Important:** E2E tests use Playwright's `page.route()` to mock API responses. They do NOT call the real backend. The `application-hub-flow.e2e.test.ts` file mocks all module status endpoints inline.

**Required `data-testid` attributes** — Components must expose these for E2E tests to work:

| Component | data-testid |
|-----------|------------|
| ModuleCard (per module) | `module-card-{moduleType}` e.g. `module-card-vpr` |
| Primary CTA button | `primary-cta` |
| Spinner | `spinner` |
| Status badge | `status-badge` |
| Hub blocked banner | `hub-blocked-banner` |
| Email input | `email-input` |
| Password input | `password-input` |
| Sign-in button | `sign-in-button` |
| Job card | `job-card-{jobId}` |

---

## 4. Regression Tests (Vitest)

**Location:** `src/frontend/tests/regression/`

These tests are pure logic tests — no React rendering needed for most of them.

**Run regression tests:**

```bash
npx vitest run tests/regression/
```

**CI requirement:** Regression tests MUST pass before every merge to `main`. Add to GitHub Actions:

```yaml
- name: Regression tests
  run: cd src/frontend && npx vitest run tests/regression/ --reporter=verbose
```

**When to add new regression tests:**

- When adding a new ModuleType (update `cross-module-invalidation.test.ts`)
- When adding a new ModuleStatus (update `state-machine-transitions.test.ts` and `cta-label-consistency.test.ts`)
- When changing cross-module dependency rules (update `cross-module-invalidation.test.ts`)
- When changing CTA labels in the design spec (update `cta-label-consistency.test.ts`)

---

## 5. Running All Tests

```bash
cd src/frontend

# Unit + integration + regression (fast, no browser)
npx vitest run

# E2E only (requires dev server)
npx playwright test

# Full suite (CI)
npx vitest run && npx playwright test
```

**Package.json scripts to add:**

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:ui": "vitest --ui",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:all": "vitest run && playwright test",
    "typecheck": "tsc --noEmit"
  }
}
```

---

## 6. Test Implementation Sequence

Follow this order to avoid writing tests for code that doesn't exist yet:

```
Phase A — Pure logic (no React):
  1. src/frontend/types/enums.ts
  2. src/frontend/types/hub-state.ts
  3. src/frontend/adapters/mapApplicationDataToHubState.ts
     → Run: vitest run tests/unit/state-adapters.test.ts
     → Run: vitest run tests/regression/

Phase B — React components:
  4. src/frontend/components/ModuleCard/ModuleCard.tsx
     → Run: vitest run tests/unit/module-card.test.tsx
     → Run: vitest run tests/regression/cta-label-consistency.test.ts

Phase C — Hooks + API:
  5. src/frontend/api/client.ts
  6. src/frontend/api/queryKeys.ts
  7. src/frontend/hooks/useModuleStatus.ts
     → Run: vitest run tests/integration/api-polling.test.ts

Phase D — Auth:
  8. src/frontend/contexts/AuthContext.tsx
     → Run: vitest run tests/integration/cognito-auth.test.ts

Phase E — E2E (after pages are built):
  9. src/frontend/app/... (all pages)
     → Run: playwright test
```
