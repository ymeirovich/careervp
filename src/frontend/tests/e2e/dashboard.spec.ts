// spec_id: FE-UI-009  component: StatsRow
// Route: /dashboard
// E2E notes: all ACs are verification_type: unit — no live ACs exist for this spec.
// These tests establish a visual regression baseline and verify pill rendering and
// loading skeleton in a real browser on the /dashboard route.
import { test, expect } from '@playwright/test';

test.describe('Dashboard — StatsRow', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate — call shared auth helper (e.g. loginAs(page, 'test-user'))
    // TODO: navigate to /dashboard
    // TODO: await page.waitForSelector('[data-testid="stats-row"]') or equivalent selector
  });

  // ---------------------------------------------------------------------------
  // AC-001: pill corner radius
  // ---------------------------------------------------------------------------
  test('test_pill_containers_have_rounded_xl_class_on_page', async ({ page }) => {
    // Verifies AC-001 in a real browser on the /dashboard route
    // TODO: locate all three pill containers (e.g. via data-testid or class selector)
    // TODO: for each pill element, evaluate classList via page.evaluate
    // TODO: assert each classList includes "rounded-xl"
    // TODO: assert each classList does NOT include "rounded-lg"
  });

  // ---------------------------------------------------------------------------
  // AC-002 / AC-003 / AC-004: loading skeleton
  // ---------------------------------------------------------------------------
  test('test_skeleton_renders_with_pulse_animation_during_loading @slow', async ({ page }) => {
    // Verifies ACs 002–004: skeleton visible before data resolves
    // TODO: intercept the data source (mock network or delay API) to hold loading state
    // TODO: navigate to /dashboard and assert loading skeletons appear before resolve
    // TODO: assert 3 elements with "animate-pulse" class are present
    // TODO: assert plan/credits/status text is absent during loading
  });

  // ---------------------------------------------------------------------------
  // AC-005: data renders normally after loading
  // ---------------------------------------------------------------------------
  test('test_data_pills_visible_after_loading_resolves', async ({ page }) => {
    // AC-005: once data loads, pills render with values and rounded-xl
    // TODO: navigate to /dashboard and await data load
    // TODO: assert plan label and value are visible
    // TODO: assert credits fraction is visible
    // TODO: assert "Active" or "Inactive" status is visible
    // TODO: assert no "animate-pulse" element remains
  });

  // ---------------------------------------------------------------------------
  // visual regression baseline
  // ---------------------------------------------------------------------------
  test('visual regression baseline @slow', async ({ page }) => {
    // Establish screenshot baseline for StatsRow on /dashboard.
    // On first run this creates the snapshot; subsequent runs diff against it.
    // TODO: await data load and any transitions/animations to settle
    // TODO: optionally scroll to stats row region for a cropped screenshot
    await expect(page).toHaveScreenshot('dashboard-statsrow-baseline.png');
  });

});
