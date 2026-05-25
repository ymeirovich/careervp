// spec_id: FE-UI-001  component: Badge
// Route: /applications/[id] (soft badges appear on all routes where Badge is used)
// E2E notes: all ACs are verification_type: unit — no live ACs exist for this spec.
// These tests establish a visual regression baseline and verify soft prop rendering
// in a real browser via a known application route.
import { test, expect } from '@playwright/test';

test.describe('Application Detail — Badge soft variant', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate — call shared auth helper (e.g. loginAs(page, 'test-user'))
    // TODO: navigate to a known /applications/[id] route that renders soft Badge variants
    // TODO: await page.waitForSelector('[data-testid="status-badge"]')
  });

  test('test_soft_success_badge_renders_green_tinted_on_page', async ({ page }) => {
    // Verifies AC-001 in a real browser context
    // TODO: locate a badge element representing a "Complete" or "Final" module status
    //       rendered with soft={true} (once parent components are updated)
    // TODO: assert computed background-color or class attribute contains green-tinted value
    // TODO: assert computed color is not white (i.e. not solid)
  });

  test('test_soft_error_badge_retains_solid_red_on_page', async ({ page }) => {
    // Verifies AC-003 in a real browser context
    // TODO: locate a badge element representing a "Failed" module status
    // TODO: assert the badge retains solid red styling (no soft tinting)
  });

  test('test_solid_badges_unaffected_on_pages_not_using_soft_prop @slow', async ({ page }) => {
    // Regression: pages that do not pass soft={true} must be visually unchanged
    // TODO: navigate to a route rendering Badge without soft prop
    // TODO: assert badge uses solid style classes
    // TODO: assert no tinted background class is present
  });

  test('visual regression baseline @slow', async ({ page }) => {
    // Establish screenshot baseline for all Badge variants on this route.
    // On first run this creates the snapshot; subsequent runs diff against it.
    // TODO: scroll page to region containing Badge components
    // TODO: await animations/transitions to settle
    await expect(page).toHaveScreenshot('badge-soft-variant-baseline.png');
  });

});
