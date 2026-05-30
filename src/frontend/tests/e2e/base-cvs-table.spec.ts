// spec_id: FE-UI-017  component: BaseCVsTable
// Route: /cv-center
// E2E: complete user flows on the CV Center page.
// All ACs are verification_type: unit; these tests verify live browser behaviour
// and establish a visual regression baseline.

import { test, expect } from '@playwright/test';

test.describe('CV Center — BaseCVsTable @batch4', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate — call shared auth helper (e.g. loginAs(page, 'test-user'))
    // TODO: navigate to /cv-center
    // TODO: await page.waitForSelector('[role="table"]')
  });

  // ─── Primary flow: data loads and table is visible ────────────────────────

  test('test_table_renders_with_data_on_cv_center_page', async ({ page }) => {
    // TODO: assert page.getByRole('table') is visible
    // TODO: assert at least one data row is visible (tbody tr)
    // TODO: assert 7 column headers are visible
  });

  // ─── Sorting flow ─────────────────────────────────────────────────────────

  test('test_clicking_file_name_header_sorts_rows_ascending', async ({ page }) => {
    // TODO: click the "File Name" column header
    // TODO: await sort re-render
    // TODO: assert first row contains the alphabetically first full_name
    // TODO: assert File Name <th> has aria-sort="ascending"
  });

  test('test_clicking_file_name_header_twice_sorts_rows_descending', async ({ page }) => {
    // TODO: click "File Name" header twice
    // TODO: await re-render
    // TODO: assert first row contains the alphabetically last full_name
    // TODO: assert File Name <th> has aria-sort="descending"
  });

  // ─── Navigation flow ──────────────────────────────────────────────────────

  test('test_clicking_view_navigates_to_cv_detail_route', async ({ page }) => {
    // TODO: get all "View" links
    // TODO: click the first "View" link
    // TODO: await navigation
    // TODO: assert page.url() matches /\/cv-center\/[^/]+/
  });

  // ─── Actions flow ─────────────────────────────────────────────────────────

  test('test_clicking_set_as_default_triggers_expected_behaviour', async ({ page }) => {
    // TODO: click "Set as Default" for the first row
    // TODO: assert expected UI feedback (e.g. toast, badge change, or network call)
    // NOTE: exact assertion depends on parent page (FE-UI-016) implementation
  });

  test('test_clicking_delete_triggers_expected_behaviour', async ({ page }) => {
    // TODO: click "Delete" for the first row
    // TODO: assert expected confirmation or row removal
    // NOTE: exact assertion depends on parent page (FE-UI-016) delete flow
  });

  // ─── Empty state flow ─────────────────────────────────────────────────────

  test('test_empty_state_renders_with_cta_when_no_cvs_exist', async ({ page }) => {
    // TODO: authenticate as a user with no uploaded base CVs
    // TODO: navigate to /cv-center
    // TODO: assert page.getByText(/no primary cvs uploaded yet/i) is visible
    // TODO: assert "+ Upload New CV" CTA button is visible
  });

  // ─── Error state flow ─────────────────────────────────────────────────────

  test('test_error_state_and_retry_render_when_api_fails', async ({ page }) => {
    // TODO: intercept GET /users/me/cv and respond with 500
    // TODO: navigate to /cv-center
    // TODO: assert inline error message is visible
    // TODO: assert Retry button is visible
    // TODO: remove network intercept
    // TODO: click Retry and assert data loads successfully
  });

  // ─── Keyboard accessibility flow ──────────────────────────────────────────

  test('test_column_header_sortable_via_keyboard_enter @slow', async ({ page }) => {
    // TODO: focus the Language column header via page.focus(selector)
    // TODO: page.keyboard.press('Enter')
    // TODO: await sort re-render
    // TODO: assert Language <th> has aria-sort="ascending"
  });

  // ─── Visual regression baseline ───────────────────────────────────────────

  test('visual regression baseline @slow', async ({ page }) => {
    // TODO: await all skeleton animations to settle
    // TODO: await data rows visible
    await expect(page).toHaveScreenshot('cv-center-base-cvs-table-baseline.png');
  });

  test('visual regression baseline — empty state @slow', async ({ page }) => {
    // TODO: authenticate as a user with no uploaded base CVs
    // TODO: navigate to /cv-center
    // TODO: await empty state visible
    await expect(page).toHaveScreenshot('cv-center-base-cvs-table-empty-baseline.png');
  });

});
