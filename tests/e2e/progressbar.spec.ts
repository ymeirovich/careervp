// spec_id: FE-UI-002  component: ProgressBar
// Route: /applications/[id] (ProgressBar renders on all routes via ModuleCard)
// E2E notes: all ACs are verification_type: unit — no live ACs exist for this spec.
// These tests establish a visual regression baseline and verify showLabel rendering
// in a real browser via a known application route once ModuleCard is updated (parent spec).
import { test, expect } from '@playwright/test';

test.describe('Application Detail — ProgressBar label', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate — call shared auth helper (e.g. loginAs(page, 'test-user'))
    // TODO: navigate to a known /applications/[id] route that renders ModuleCard
    //       with ProgressBar showLabel={true}
    // TODO: await page.waitForSelector('[role="progressbar"]')
  });

  test('test_visible_progress_label_renders_on_page', async ({ page }) => {
    // Verifies AC-001 / AC-002 in a real browser context
    // (depends on ModuleCard parent spec updating to pass showLabel={true})
    // TODO: locate a ProgressBar element on the page via role="progressbar"
    // TODO: assert a sibling or ancestor element contains visible text "Progress"
    // TODO: assert a sibling or ancestor element contains a visible percentage string (e.g. /\d+%/)
  });

  test('test_percentage_value_matches_module_progress_on_page', async ({ page }) => {
    // Verifies the displayed percentage reflects the actual module progress value
    // TODO: read expected progress value from the page data (e.g. data attribute or API response)
    // TODO: assert the visible percentage text matches the expected value
  });

  test('test_bar_height_and_rounded_ends_unchanged_on_page @slow', async ({ page }) => {
    // Regression guard per q16: h-2 height and rounded-full must not regress
    // TODO: locate the track div inside role="progressbar"
    // TODO: assert computed height equals 8px (h-2 in Tailwind)
    // TODO: assert border-radius is non-zero (rounded-full)
  });

  test('visual regression baseline @slow', async ({ page }) => {
    // Establish screenshot baseline for ProgressBar with showLabel on this route.
    // On first run this creates the snapshot; subsequent runs diff against it.
    // TODO: scroll page to region containing a ProgressBar with showLabel={true}
    // TODO: await animations/transitions to settle (e.g. page.waitForTimeout(300))
    await expect(page).toHaveScreenshot('applications-hub-progressbar-baseline.png');
  });

});
