// spec_id: FE-UI-013  component: CoverLettersListTable  tier: e2e
// route: /cover-letters   route-slug: cover-letters-list-table
// Framework: Playwright
// Covers complete user flows for the CoverLettersListTable within the Cover Letters page.
// Note: tests/e2e/cover-letters.spec.ts covers FE-UI-012 (CoverLettersPage shell).
//       This file covers FE-UI-013 (the table component embedded in that page).

import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// Shared fixture for stable API intercept
// ---------------------------------------------------------------------------

const FIXTURE_COVER_LETTERS = [
  {
    applicationId: 'app-1',
    company_name: 'Acme Corp',
    job_title: 'Senior Engineer',
    status: 'ready',
    created_at: '2026-05-20T10:00:00Z',
  },
  {
    applicationId: 'app-2',
    company_name: 'Beta Ltd',
    job_title: 'Product Manager',
    status: 'processing',
    created_at: '2026-05-15T09:00:00Z',
  },
  {
    applicationId: 'app-3',
    company_name: 'Gamma Inc',
    job_title: 'Data Analyst',
    status: 'failed',
    created_at: '2026-05-10T08:00:00Z',
  },
];

// ===========================================================================
// Cover Letters page — CoverLettersListTable
// ===========================================================================

test.describe('Cover Letters page — CoverLettersListTable', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: set auth cookie or localStorage token for a valid test user session
    // TODO: intercept GET /cover-letters and return FIXTURE_COVER_LETTERS
    await page.route('**/cover-letters', async (route) => {
      // TODO: route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(FIXTURE_COVER_LETTERS) })
      await route.continue();
    });
    // TODO: await page.goto('/cover-letters')
    // TODO: await page.waitForSelector('[data-testid="cover-letters-list-table"]')
    await page.goto('/cover-letters');
  });

  // ─── Primary flow: table renders with data rows ────────────────────────────

  test('test_table_renders_all_cover_letter_rows_when_page_loaded', async ({ page }) => {
    // TODO: assert 3 data rows are visible in the table body
    // TODO: await expect(page.getByText('Acme Corp')).toBeVisible()
    // TODO: await expect(page.getByText('Beta Ltd')).toBeVisible()
    // TODO: await expect(page.getByText('Gamma Inc')).toBeVisible()
  });

  // ─── Sorting flow ─────────────────────────────────────────────────────────

  test('test_rows_reorder_when_company_column_header_clicked', async ({ page }) => {
    // TODO: click the Company column header
    // TODO: await expect(page.locator('tbody tr').first()).toContainText('Acme Corp')
    // TODO: click the Company column header again (descending)
    // TODO: await expect(page.locator('tbody tr').first()).toContainText('Gamma Inc')
  });

  // ─── Search flow ──────────────────────────────────────────────────────────

  test('test_search_filters_table_when_user_types_company_name', async ({ page }) => {
    // TODO: await page.getByRole('searchbox').fill('acme')
    // TODO: await expect(page.getByText('Acme Corp')).toBeVisible()
    // TODO: await expect(page.getByText('Beta Ltd')).not.toBeVisible()
  });

  test('test_no_matching_message_shown_when_search_yields_zero_results', async ({ page }) => {
    // TODO: await page.getByRole('searchbox').fill('zzznomatch')
    // TODO: await expect(page.getByText(/no matching cover letters/i)).toBeVisible()
  });

  // ─── View navigation ──────────────────────────────────────────────────────

  test('test_clicking_view_navigates_to_cover_letter_route_when_row_exists', async ({ page }) => {
    // TODO: click the first 'View' link in the table
    // TODO: await page.waitForURL('**/applications/app-1/cover-letter')
    // TODO: expect(page.url()).toContain('/applications/app-1/cover-letter')
  });

  // ─── Loading state ────────────────────────────────────────────────────────

  test('test_skeleton_rows_visible_during_api_fetch @slow', async ({ page }) => {
    // TODO: intercept GET /cover-letters with a 2-second delay
    await page.route('**/cover-letters', async (route) => {
      // TODO: await new Promise(resolve => setTimeout(resolve, 2000))
      // TODO: route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(FIXTURE_COVER_LETTERS) })
      await route.continue();
    });
    // TODO: navigate to /cover-letters
    // TODO: immediately assert skeleton rows are present (data-testid="skeleton-row")
    // TODO: await skeleton rows to disappear and real data to appear
    await page.goto('/cover-letters');
  });

  // ─── Error state + retry ──────────────────────────────────────────────────

  test('test_error_state_and_retry_flow_when_api_fails_then_succeeds', async ({ page }) => {
    let callCount = 0;
    await page.route('**/cover-letters', async (route) => {
      callCount++;
      // TODO: if (callCount === 1) route.fulfill({ status: 500, body: JSON.stringify({ message: 'error' }) })
      // TODO: else route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(FIXTURE_COVER_LETTERS) })
      await route.continue();
    });
    // TODO: navigate to /cover-letters
    // TODO: await expect(page.getByRole('button', { name: /retry/i })).toBeVisible()
    // TODO: await page.getByRole('button', { name: /retry/i }).click()
    // TODO: await expect(page.getByText('Acme Corp')).toBeVisible()
    await page.goto('/cover-letters');
  });

  // ─── Empty state ──────────────────────────────────────────────────────────

  test('test_empty_state_shown_when_api_returns_no_cover_letters', async ({ page }) => {
    await page.route('**/cover-letters', async (route) => {
      // TODO: route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
      await route.continue();
    });
    // TODO: navigate to /cover-letters
    // TODO: await expect(page.getByText(/no cover letters yet/i)).toBeVisible()
    // TODO: assert column headers are still visible
    await page.goto('/cover-letters');
  });

  // ─── Responsive card layout ───────────────────────────────────────────────

  test('test_card_layout_shown_when_viewport_is_mobile_width @slow', async ({ page }) => {
    // TODO: await page.setViewportSize({ width: 375, height: 812 })
    // TODO: navigate to /cover-letters (or reload)
    // TODO: assert <table> element is not visible (hidden on mobile)
    // TODO: assert card elements are visible (one per cover letter)
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/cover-letters');
  });

  // ─── Keyboard accessibility ───────────────────────────────────────────────

  test('test_keyboard_enter_on_column_header_sorts_rows_when_focused', async ({ page }) => {
    // TODO: tab to the Company column header
    // TODO: await page.keyboard.press('Tab') until Company th is focused
    // TODO: await page.keyboard.press('Enter')
    // TODO: assert aria-sort="ascending" on Company th
  });

  // ─── i18n: Hebrew ────────────────────────────────────────────────────────

  test('test_table_renders_hebrew_column_headers_when_locale_is_he @slow', async ({ page }) => {
    // TODO: navigate to /cover-letters with Hebrew locale (cookie or query param)
    // TODO: await expect(page.getByRole('columnheader', { name: /<hebrew-company>/ })).toBeVisible()
    // TODO: repeat for all 5 column headers
    await page.goto('/cover-letters?locale=he');
  });

  // ─── Visual regression baselines ─────────────────────────────────────────

  test('visual regression baseline — default state @slow', async ({ page }) => {
    // TODO: await page.waitForSelector('tbody tr') — ensure data loaded before screenshot
    await expect(page).toHaveScreenshot('cover-letters-list-table-default-baseline.png');
  });

  test('visual regression baseline — loading state @slow', async ({ page }) => {
    await page.route('**/cover-letters', async (route) => {
      // TODO: delay resolution to capture skeleton in screenshot
      // TODO: await new Promise(() => {}); // never resolves — captures skeleton
      await route.continue();
    });
    await page.goto('/cover-letters');
    await expect(page).toHaveScreenshot('cover-letters-list-table-loading-baseline.png');
  });

  test('visual regression baseline — empty state @slow', async ({ page }) => {
    await page.route('**/cover-letters', async (route) => {
      // TODO: route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
      await route.continue();
    });
    await page.goto('/cover-letters');
    // TODO: await page.waitForText(/no cover letters yet/i)
    await expect(page).toHaveScreenshot('cover-letters-list-table-empty-baseline.png');
  });

  test('visual regression baseline — error state @slow', async ({ page }) => {
    await page.route('**/cover-letters', async (route) => {
      // TODO: route.fulfill({ status: 500, body: JSON.stringify({ message: 'Server error' }) })
      await route.continue();
    });
    await page.goto('/cover-letters');
    // TODO: await page.waitForSelector('[role="button"][name=/retry/i]')
    await expect(page).toHaveScreenshot('cover-letters-list-table-error-baseline.png');
  });

  test('visual regression baseline — mobile card layout @slow', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    // TODO: await page.waitForSelector('[data-testid="cover-letter-card"]')
    await expect(page).toHaveScreenshot('cover-letters-list-table-mobile-baseline.png');
  });

});
