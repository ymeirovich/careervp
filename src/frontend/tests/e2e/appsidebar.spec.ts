// spec_id: FE-UI-003  component: AppSidebar  route: all authenticated routes
import { test, expect } from '@playwright/test';

// Route slug used for snapshot filenames: appsidebar
// All authenticated routes render AppSidebar via AppShell — use /dashboard as canonical host

test.describe('Dashboard — AppSidebar @batch2', () => {

  test.beforeEach(async ({ page }) => {
    // TODO: authenticate (set session cookie or use storageState with a saved auth fixture)
    // TODO: await page.goto('/dashboard')
    // TODO: await page.waitForSelector('[data-testid="app-sidebar"]') — or equivalent stable selector
  });

  // -------------------------------------------------------------------------
  // AC-001 — 7 nav items present in a live browser
  // -------------------------------------------------------------------------
  test('test_seven_nav_items_present_in_sidebar', async ({ page }) => {
    // TODO: count <a> or nav-item elements inside the sidebar
    // TODO: expect(navItems).toHaveCount(7)
  });

  // -------------------------------------------------------------------------
  // AC-013 — "CV Center" label absent in a live browser
  // -------------------------------------------------------------------------
  test('test_cv_center_label_absent_in_sidebar', async ({ page }) => {
    // TODO: const cvCenter = page.getByText('CV Center')
    // TODO: await expect(cvCenter).toHaveCount(0)
  });

  // -------------------------------------------------------------------------
  // AC-005 — active state renders on a real navigation
  // -------------------------------------------------------------------------
  test('test_applications_item_active_when_navigated_to_applications', async ({ page }) => {
    // TODO: await page.goto('/applications')
    // TODO: locate "Applications" nav item
    // TODO: await expect(applicationsItem).toHaveClass(/border-primary-action/)
    // TODO: await expect(icon inside applicationsItem).toHaveClass(/text-primary-action/)
  });

  // -------------------------------------------------------------------------
  // AC-003 + AC-004 — new items link to correct routes
  // -------------------------------------------------------------------------
  test('test_tailored_cvs_link_navigates_to_tailored_cvs_route', async ({ page }) => {
    // TODO: click the "Tailored CVs" nav link
    // TODO: await expect(page).toHaveURL(/\/tailored-cvs/)
    // NOTE: page may return 404 until route page is built (see RT-003); assert URL only, not page content
  });

  test('test_cover_letters_link_navigates_to_cover_letters_route', async ({ page }) => {
    // TODO: click the "Cover Letters" nav link
    // TODO: await expect(page).toHaveURL(/\/cover-letters/)
    // NOTE: see RT-003 — assert URL only until route page exists
  });

  // -------------------------------------------------------------------------
  // AC-010 — mobile hamburger visible below md
  // -------------------------------------------------------------------------
  test('test_hamburger_visible_and_sidebar_hidden_on_mobile @slow', async ({ page }) => {
    // TODO: await page.setViewportSize({ width: 375, height: 812 })
    // TODO: await page.goto('/dashboard')
    // TODO: await expect(page.getByRole('button', { name: /menu/i })).toBeVisible()
    // TODO: locate sidebar element and assert it is not visible
  });

  // -------------------------------------------------------------------------
  // AC-011 — tablet icon-only rail
  // -------------------------------------------------------------------------
  test('test_icon_rail_renders_on_tablet_width @slow', async ({ page }) => {
    // TODO: await page.setViewportSize({ width: 768, height: 1024 })
    // TODO: await page.goto('/dashboard')
    // TODO: assert sidebar is visible but labels are hidden
    // TODO: assert sidebar width is narrower than 220px (icon-only rail)
  });

  // -------------------------------------------------------------------------
  // AC-012 — desktop full sidebar
  // -------------------------------------------------------------------------
  test('test_full_sidebar_renders_on_desktop_width', async ({ page }) => {
    // TODO: await page.setViewportSize({ width: 1280, height: 800 })
    // TODO: await page.goto('/dashboard')
    // TODO: await expect(page.getByText('Dashboard')).toBeVisible()
    // TODO: await expect(page.getByText('Base CVs')).toBeVisible()
    // TODO: await expect(page.getByText('Tailored CVs')).toBeVisible()
    // TODO: await expect(page.getByText('Cover Letters')).toBeVisible()
  });

  // -------------------------------------------------------------------------
  // visual regression baseline (desktop, default route)
  // -------------------------------------------------------------------------
  test('visual regression baseline @slow', async ({ page }) => {
    // TODO: await page.setViewportSize({ width: 1280, height: 800 })
    // TODO: await page.goto('/dashboard')
    await expect(page).toHaveScreenshot('appsidebar-desktop-baseline.png');
  });

  // -------------------------------------------------------------------------
  // visual regression baseline (tablet rail)
  // -------------------------------------------------------------------------
  test('visual regression baseline tablet-rail @slow', async ({ page }) => {
    // TODO: await page.setViewportSize({ width: 768, height: 1024 })
    // TODO: await page.goto('/dashboard')
    await expect(page).toHaveScreenshot('appsidebar-tablet-rail-baseline.png');
  });

  // -------------------------------------------------------------------------
  // visual regression baseline (mobile overlay — open state)
  // -------------------------------------------------------------------------
  test('visual regression baseline mobile-overlay-open @slow', async ({ page }) => {
    // TODO: await page.setViewportSize({ width: 375, height: 812 })
    // TODO: await page.goto('/dashboard')
    // TODO: click hamburger to open overlay
    await expect(page).toHaveScreenshot('appsidebar-mobile-overlay-baseline.png');
  });

});
