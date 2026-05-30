// spec_id: FE-UI-007  component: Spinner  route: all routes (shared)
// No live ACs in spec (both ACs are verification_type: unit / pre_merge).
// E2E stubs cover the Button inline loading flow observable in a real browser
// and establish a visual regression baseline for the spinner-in-button state.
import { test, expect } from '@playwright/test';

// ---------------------------------------------------------------------------
// Suite: Spinner inline loading — dashboard route (representative shared route)
// ---------------------------------------------------------------------------
test.describe('Dashboard — Spinner inline button loading (FE-UI-007)', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate user (set auth cookie / local-storage token)
    // TODO: navigate to /dashboard
  });

  // -------------------------------------------------------------------------
  // AC-002 coverage: Button with Spinner in a real browser context
  // -------------------------------------------------------------------------
  test('test_button_shows_spinner_and_is_disabled_when_action_in_progress', async ({ page }) => {
    // AC-002: spinner at sm size + disabled button + loading label visible
    // TODO: locate a Button that triggers an async action (e.g., form submit or module action)
    // TODO: click the button to initiate the action
    // TODO: assert button has disabled attribute during the async action
    // TODO: assert element with data-testid="spinner" is visible
    // TODO: assert loading label text (e.g., "Creating..." or "Saving...") is visible
  });

  test('test_spinner_disappears_and_button_re_enables_when_action_completes', async ({ page }) => {
    // AC-002 cleanup: loading state must not persist after action resolves
    // TODO: trigger async action via button click
    // TODO: wait for the action to complete (network idle or response assertion)
    // TODO: assert data-testid="spinner" is NOT visible
    // TODO: assert button no longer has disabled attribute
  });

  // -------------------------------------------------------------------------
  // AC-001 coverage: page-level loading uses skeleton, not Spinner
  // -------------------------------------------------------------------------
  test('test_page_level_loading_shows_skeleton_not_spinner_when_data_fetching', async ({ page }) => {
    // AC-001: on initial page load, data-fetch loading state must not render a Spinner
    // TODO: intercept the API request that drives page data (route.fulfill with delay)
    // TODO: navigate to /dashboard
    // TODO: assert data-testid="spinner" is NOT present during data loading
    // TODO: assert a skeleton placeholder element is visible instead
  });

  // -------------------------------------------------------------------------
  // Visual regression baseline @slow
  // -------------------------------------------------------------------------
  test('visual regression baseline — spinner in button @slow', async ({ page }) => {
    // Establishes screenshot baseline for Spinner rendered inside a Button.
    // Re-run with `--update-snapshots` when intentional visual changes land.
    // TODO: navigate to a page with an accessible Button that accepts isLoading
    // TODO: trigger loading state (intercept API to keep button in loading state)
    // TODO: assert spinner element is visible before capturing screenshot
    await expect(page).toHaveScreenshot('spinner-button-inline-baseline.png');
  });

});

// ---------------------------------------------------------------------------
// Suite: Spinner absent on section loading — applications route
// ---------------------------------------------------------------------------
test.describe('Applications — Spinner contract on section loading (FE-UI-007)', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate user
    // TODO: navigate to /applications/:id (use a seeded application id)
  });

  test('test_no_spinner_in_section_loading_when_module_data_fetching', async ({ page }) => {
    // AC-001: module-level data loading on the applications page must use skeleton,
    // not a page/section Spinner.
    // TODO: intercept module data API to simulate slow response
    // TODO: navigate to /applications/:id
    // TODO: assert data-testid="spinner" is NOT present in the main content area
    // TODO: assert skeleton shimmer element IS visible in the module section
  });

});
