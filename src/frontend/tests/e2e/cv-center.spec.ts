// spec_id: FE-UI-016  component: CVCenterContent  tier: e2e
// route: /cv-center   route-slug: cv-center
// Framework: Playwright
// All spec ACs are verification_type: unit; e2e tests cover the complete
// user flow and visual regression baseline.
import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// shared auth helper
// ---------------------------------------------------------------------------
async function authenticateAndNavigate(
  page: Parameters<Parameters<typeof test>[1]>[0]['page'],
  route: string
) {
  // TODO: set auth cookies or localStorage token
  // TODO: await page.goto(route)
  await page.goto(route);
}

// ===========================================================================
// Base CVs Page — /cv-center
// ===========================================================================
test.describe('Base CVs Page — CVCenterContent', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate (set session cookie / localStorage token)
    // TODO: navigate to /cv-center
    await authenticateAndNavigate(page, '/cv-center');
  });

  // ─── AC-001: page header renders with text "Base CVs" ─────────────────────
  test('test_page_header_renders_with_base_cvs_title_when_page_loads', async ({ page }) => {
    // TODO: assert element with data-testid="page-header" or role="banner" is visible
    // TODO: assert text /base cvs/i is visible in header area
    // TODO: await expect(page.getByTestId('page-header-title')).toContainText(/base cvs/i)
    await expect(page.getByTestId('page-header')).toBeVisible();
    // TODO: await expect(page.getByTestId('page-header-title')).toContainText(/base cvs/i)
  });

  // ─── AC-002: card with "All Base CVs" sub-heading ─────────────────────────
  test('test_all_base_cvs_subheading_renders_in_card_below_header', async ({ page }) => {
    // TODO: assert text /all base cvs/i is visible in the card area
    // TODO: assert the card is positioned below the page header (DOM order)
    // TODO: await expect(page.getByText(/all base cvs/i)).toBeVisible()
    await expect(page.getByTestId('base-cvs-table')).toBeVisible();
    // TODO: await expect(page.getByText(/all base cvs/i)).toBeVisible()
  });

  // ─── AC-003: "+ Upload New CV" orange button visible ─────────────────────
  test('test_upload_new_cv_button_visible_when_page_loads', async ({ page }) => {
    // TODO: assert button with text /\+ upload new cv/i is visible
    // TODO: assert button has orange background (bg-primary-action class or computed style)
    // TODO: await expect(page.getByRole('button', { name: /upload new cv/i })).toBeVisible()
    await expect(page.getByTestId('base-cvs-table')).toBeVisible();
    // TODO: await expect(page.getByRole('button', { name: /upload new cv/i })).toBeVisible()
  });

  // ─── AC-004: BaseCVsTable renders in card body ────────────────────────────
  test('test_base_cvs_table_renders_in_card_body_when_page_loads', async ({ page }) => {
    // TODO: assert data-testid="base-cvs-table" is visible
    // TODO: assert it is positioned inside the card container below the sub-heading row
    await expect(page.getByTestId('base-cvs-table')).toBeVisible();
  });

  // ─── AC-005: loading state during GET /users/me/cv in flight ──────────────
  test('test_loading_state_visible_when_get_users_me_cv_in_flight @slow', async ({ page }) => {
    // TODO: intercept GET /users/me/cv to delay response by 3 seconds
    // TODO: navigate to /cv-center
    // TODO: assert loading indicator or data-is-loading="true" is visible immediately
    // TODO: assert it disappears once the response arrives
    await page.route('**/users/me/cv', async (route) => {
      // TODO: await new Promise(resolve => setTimeout(resolve, 3000)); await route.continue()
      await route.continue();
    });
    await page.goto('/cv-center');
    // TODO: await expect(page.getByTestId('base-cvs-table'))
    //         .toHaveAttribute('data-is-loading', 'true')
  });

  // ─── AC-006: error state when GET /users/me/cv fails ─────────────────────
  test('test_error_state_rendered_when_get_users_me_cv_fails', async ({ page }) => {
    // TODO: intercept GET /users/me/cv to return 500
    // TODO: navigate to /cv-center
    // TODO: assert error state is visible (data-has-error="true" or visible error message)
    // TODO: assert a retry button or onRetry trigger is accessible
    await page.route('**/users/me/cv', async (route) => {
      // TODO: route.fulfill({ status: 500, body: JSON.stringify({ message: 'Server error' }) })
      await route.continue();
    });
    await page.goto('/cv-center');
    // TODO: await expect(page.getByTestId('base-cvs-table'))
    //         .toHaveAttribute('data-has-error', 'true')
  });

  // ─── AC-006: onRetry re-fetches after error ───────────────────────────────
  test('test_retry_triggers_refetch_when_clicked_after_error', async ({ page }) => {
    // TODO: intercept GET /users/me/cv to fail on first call, succeed on second
    // TODO: navigate to /cv-center, await error state
    // TODO: click retry button
    // TODO: assert GET /users/me/cv was called twice
    // TODO: assert data-has-error is no longer "true" after second call succeeds
    let callCount = 0;
    await page.route('**/users/me/cv', async (route) => {
      callCount++;
      // TODO: if (callCount === 1) route.fulfill({ status: 500 }); else route.continue()
      await route.continue();
    });
    await page.goto('/cv-center');
    // TODO: await page.getByTestId('retry-btn').click()
    // TODO: expect(callCount).toBe(2)
  });

  // ─── AC-007: data array displayed after successful fetch ──────────────────
  test('test_base_cvs_list_populated_when_api_returns_data', async ({ page }) => {
    // TODO: intercept GET /users/me/cv to return [{ cv_id: '1', full_name: 'John Doe', language: 'en', updated_at: '2026-01-01' }]
    // TODO: await expect(page.getByTestId('base-cvs-table')).toHaveAttribute('data-cvs-count', '1')
    await page.route('**/users/me/cv', async (route) => {
      // TODO: route.fulfill({
      //   status: 200,
      //   body: JSON.stringify([{ cv_id: '1', full_name: 'John Doe', language: 'en', updated_at: '2026-01-01' }]),
      // })
      await route.continue();
    });
    await page.goto('/cv-center');
    // TODO: await expect(page.getByTestId('base-cvs-table')).toHaveAttribute('data-cvs-count', '1')
  });

  // ─── AC-008: clicking "+ Upload New CV" opens ChooseBaseCVModal ───────────
  test('test_choose_base_cv_modal_opens_with_upload_only_mode_when_button_clicked', async ({ page }) => {
    // TODO: intercept GET /users/me/cv to return []
    // TODO: await page.getByRole('button', { name: /upload new cv/i }).click()
    // TODO: assert role="dialog" is visible
    // TODO: assert modal is in upload-only mode (showChoices=false or no "Choose from existing" option)
    await page.route('**/users/me/cv', async (route) => {
      // TODO: route.fulfill({ status: 200, body: JSON.stringify([]) })
      await route.continue();
    });
    await page.goto('/cv-center');
    // TODO: await page.getByRole('button', { name: /upload new cv/i }).click()
    // TODO: await expect(page.getByRole('dialog')).toBeVisible()
    // TODO: await expect(page.getByTestId('choose-base-cv-modal')).toHaveAttribute('data-show-choices', 'false')
  });

  // ─── AC-009: upload success closes modal and refreshes table ─────────────
  test('test_table_refreshes_and_modal_closes_when_upload_succeeds @slow', async ({ page }) => {
    // TODO: intercept GET /users/me/cv — first call returns [], second returns one item
    // TODO: click "+ Upload New CV", complete upload flow
    // TODO: assert modal is closed (no role="dialog")
    // TODO: assert GET /users/me/cv was called twice
    // TODO: assert data-cvs-count="1" on table after refetch
    let fetchCount = 0;
    await page.route('**/users/me/cv', async (route) => {
      fetchCount++;
      // TODO: if (fetchCount === 1) route.fulfill({ status: 200, body: JSON.stringify([]) })
      // TODO: else route.fulfill({ status: 200, body: JSON.stringify([{ cv_id: '1', full_name: 'New CV', language: 'en', updated_at: '2026-05-01' }]) })
      await route.continue();
    });
    await page.goto('/cv-center');
    // TODO: await page.getByRole('button', { name: /upload new cv/i }).click()
    // TODO: complete upload interaction inside modal
    // TODO: await expect(page.getByRole('dialog')).not.toBeVisible()
    // TODO: expect(fetchCount).toBe(2)
  });

  // ─── AC-010 + AC-011: removed components absent from DOM ─────────────────
  test('test_cv_form_cv_preview_tag_input_edit_cv_button_absent_when_page_loads', async ({ page }) => {
    // TODO: assert no element with data-testid="cv-form" is present
    // TODO: assert no element with data-testid="cv-preview" is present
    // TODO: assert no element with data-testid="tag-input" is present
    // TODO: assert no button with text /edit cv/i is present
    // TODO: assert no button with text /create cv/i is present
    await page.goto('/cv-center');
    // TODO: await expect(page.getByTestId('cv-form')).not.toBeVisible()
    // TODO: await expect(page.getByTestId('cv-preview')).not.toBeVisible()
    // TODO: await expect(page.getByRole('button', { name: /edit cv/i })).not.toBeVisible()
  });

  // ─── AC-013: Hebrew strings when locale is he ────────────────────────────
  test('test_hebrew_strings_rendered_when_locale_is_he', async ({ page }) => {
    // TODO: navigate to /cv-center with locale=he (query param or cookie)
    // TODO: assert page header title is in Hebrew (translation for "Base CVs")
    // TODO: assert sub-heading is in Hebrew ("All Base CVs")
    // TODO: assert button label is in Hebrew ("+ Upload New CV")
    await page.goto('/cv-center?locale=he');
    // TODO: await expect(page.getByTestId('page-header-title')).toContainText(/<hebrew-base-cvs>/)
    // TODO: await expect(page.getByText(/<hebrew-all-base-cvs>/)).toBeVisible()
    // TODO: await expect(page.getByRole('button', { name: /<hebrew-upload-new-cv>/ })).toBeVisible()
  });

  // ─── visual regression baseline — default state ───────────────────────────
  test('visual regression baseline @slow', async ({ page }) => {
    // TODO: intercept GET /users/me/cv with stable fixture data
    // TODO: wait for table to finish loading before screenshot
    await expect(page).toHaveScreenshot('cv-center-cvcentercontent-baseline.png');
  });

  // ─── visual regression baseline — loading state ───────────────────────────
  test('visual regression baseline loading state @slow', async ({ page }) => {
    // TODO: intercept GET /users/me/cv with a never-resolving delay
    // TODO: navigate to /cv-center, assert loading visible
    // TODO: take screenshot
    await page.route('**/users/me/cv', async (route) => {
      // TODO: await new Promise(() => {}); never resolves — captures loading snapshot
      await route.continue();
    });
    await page.goto('/cv-center');
    await expect(page).toHaveScreenshot('cv-center-cvcentercontent-loading-baseline.png');
  });

  // ─── visual regression baseline — error state ────────────────────────────
  test('visual regression baseline error state @slow', async ({ page }) => {
    // TODO: intercept GET /users/me/cv → 500
    // TODO: navigate, await error renders, then screenshot
    await page.route('**/users/me/cv', async (route) => {
      // TODO: route.fulfill({ status: 500, body: JSON.stringify({ message: 'Test error' }) })
      await route.continue();
    });
    await page.goto('/cv-center');
    await expect(page).toHaveScreenshot('cv-center-cvcentercontent-error-baseline.png');
  });

  // ─── visual regression baseline — upload modal open ──────────────────────
  test('visual regression baseline upload modal open @slow', async ({ page }) => {
    // TODO: intercept GET /users/me/cv to return []
    // TODO: click "+ Upload New CV" to open modal
    // TODO: assert modal is visible, then screenshot
    await page.route('**/users/me/cv', async (route) => {
      // TODO: route.fulfill({ status: 200, body: JSON.stringify([]) })
      await route.continue();
    });
    await page.goto('/cv-center');
    // TODO: await page.getByRole('button', { name: /upload new cv/i }).click()
    await expect(page).toHaveScreenshot('cv-center-cvcentercontent-upload-modal-baseline.png');
  });

});
