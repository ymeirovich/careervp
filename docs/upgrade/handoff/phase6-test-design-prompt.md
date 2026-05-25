# Phase 6 — Test Design
**Model:** Sonnet
**When:** After a spec reaches approved/pending status
**Run:** One spec per conversation

---

## How to Use

1. Open a new conversation
2. Paste the prompt below with the spec content
3. Paste the existing test file for the component (if one exists)

---

## Prompt

```
ROLE: Frontend test engineer writing test stubs for a React component upgrade.
OUTPUT: Complete test file stubs with describe blocks, test names, imports, and TODO markers.
No prose. No implementation code — stubs only.

TASK: Given the spec for {COMPONENT_NAME}, produce test stubs at all levels.

THINK before writing:
1. Which ACs map to isolated component behaviour? → unit tests
2. Which ACs require page context or state transitions? → integration tests
3. Which ACs require a real browser flow or visual assertion? → e2e tests
4. Which states need a dedicated test case?
5. What currently passes that must not regress? → regression tests

THEN produce four test files:

---

## UNIT TESTS (70% of coverage target)

File: tests/ui/unit/{ComponentName}.test.tsx
Framework: Vitest + @testing-library/react

Rules:
- One assertion per test where practical
- Test name pattern: test_{behavior}_when_{condition}
- Mock API at hook level — never at network level
- Reset mocks between tests (beforeEach)

Required coverage:
- One test per AC marked verification_type: unit
- One test per state: loading, error, empty, disabled (if in spec)
- Keyboard navigation test (if spec includes accessibility AC)
- ARIA label/role test (if spec includes accessibility AC)
- Hebrew string render test (if spec includes i18n AC)
- TypeScript: no `any` types in test file

Stub structure:
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { {ComponentName} } from '{FILE_PATH}';

describe('{ComponentName}', () => {

  describe('default state', () => {
    it('test_{behavior}_when_default', () => {
      // TODO: render component with default props
      // TODO: assert {AC-001 expected outcome}
    });
  });

  describe('loading state', () => {
    it('test_shows_loading_indicator_when_data_fetching', () => {
      // TODO: render with isLoading=true
      // TODO: assert {loading AC expected outcome}
    });
  });

  // ... one describe block per state

  describe('accessibility', () => {
    it('test_keyboard_navigation_when_focused', () => {
      // TODO: assert tab order and focus behaviour
    });
  });

});

---

## INTEGRATION TESTS (20% of coverage target)

File: tests/ui/integration/{ComponentName}.test.tsx
Framework: Jest + @testing-library/react

Rules:
- Render component within its page context (wrap with providers)
- Mock at API client level (not hook level)
- Test state transitions: loading → data → error
- Each test independent — no shared state between tests

Required coverage:
- One test per AC marked verification_type: integration
- State transition: loading → data rendered
- State transition: API error → error state rendered
- User action → API call triggered → UI updates

Stub structure:
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { {ComponentName} } from '{FILE_PATH}';

const createWrapper = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('{ComponentName} integration', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('test_renders_data_when_api_succeeds', async () => {
    // TODO: mock api client response
    // TODO: render with wrapper
    // TODO: await data and assert
  });

  it('test_shows_error_state_when_api_fails', async () => {
    // TODO: mock api client to reject
    // TODO: assert error state renders
  });

});

---

## E2E TESTS (10% of coverage target)

File: tests/e2e/{route-slug}.spec.ts
Framework: Playwright

Rules:
- Test complete user flows — not isolated components
- Include visual snapshot assertion for regression baseline
- Mark with @slow if flow exceeds 10 seconds

Required coverage:
- One test per AC marked verification_type: live
- Visual snapshot: await page.screenshot({ path: 'tests/e2e/snapshots/{route-slug}-baseline.png' })
- Critical user action that changes component state

Stub structure:
import { test, expect } from '@playwright/test';

test.describe('{PAGE_TITLE} — {ComponentName}', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate and navigate to {ROUTE}
  });

  test('test_{primary_flow}', async ({ page }) => {
    // TODO: interact with {ComponentName}
    // TODO: assert {AC-003 expected outcome}
  });

  test('visual regression baseline @slow', async ({ page }) => {
    await expect(page).toHaveScreenshot('{route-slug}-{component}-baseline.png');
  });

});

---

## REGRESSION TESTS

File: tests/regression/{ComponentName}.regression.test.ts (or .tsx)
Framework: Jest

Rules:
- Assert existing behaviour that must not change
- Use snapshot or explicit assertion — no visual screenshots here
- Focus on API contract: response shape, status codes

Required coverage:
- Assert no new non-2xx responses on API calls used by this component
- Assert current rendering of components NOT in scope for this upgrade
- If component had existing tests: assert they still pass unchanged

Stub structure:
import { {ComponentName} } from '{FILE_PATH}';

describe('{ComponentName} regression', () => {

  it('test_existing_api_contract_unchanged', () => {
    // TODO: assert GET {API_ENDPOINT} response shape matches prior contract
  });

  it('test_unmodified_sibling_components_unaffected', () => {
    // TODO: render page and assert sibling component output unchanged
  });

});

---

## CONTEXT

spec_id: {SPEC_ID}
Component: {COMPONENT_NAME}
File: {FILE_PATH}
Route: {ROUTE}
Route slug: {ROUTE_SLUG}
API endpoints: {LIST FROM SPEC}

Spec content (paste full spec markdown):
{PASTE docs/upgrade/specs/{ComponentName}.md}

Existing test file (paste if exists, otherwise write "none"):
{PASTE OR "none"}

## PROHIBITED
- Do not write implementation logic inside stubs — TODO markers only
- Do not use real API calls in unit or integration tests
- Do not skip accessibility tests if spec includes accessibility ACs
- Do not use `any` type in TypeScript test files
- Do not mark tests as `.skip` without a reason comment
- Do not write a test without at least one assertion placeholder

STOP: Output the four test files, each labelled by filename.
```

---

## Existing Test Files to Check Before Running

Some components already have test files. Check these before generating stubs — incorporate existing tests rather than replacing them:

| Component | Existing test file(s) |
|---|---|
| ModuleCard | tests/unit/module-card.test.tsx, tests/unit/module-card-actions.test.tsx |
| ExportDropdown | tests/unit/export-dropdown.test.tsx |
| gap-analysis page | tests/unit/gap-analysis-page.test.tsx |
| vpr page | tests/unit/vpr-page.test.tsx |
| ApplicationHub | tests/ui/unit/ApplicationHub.test.tsx |
| Billing | tests/ui/unit/Billing.test.tsx |
| Plans | tests/ui/unit/Plans.test.tsx |
| Settings | tests/ui/unit/Settings.test.tsx |
| NewApplicationForm | tests/ui/unit/NewApplicationForm.test.tsx |
| BaseCVsTable | tests/ui/unit/BaseCVsTable.test.tsx |
| CoverLettersTable | tests/ui/unit/CoverLettersTable.test.tsx |
| TailoredCVsTable | tests/ui/unit/TailoredCVsTable.test.tsx |

**ErrorBoundary, Spinner, Button — no existing tests.** Phase 6 for these generates net-new test files.
