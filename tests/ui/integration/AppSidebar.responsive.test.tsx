// spec_id: FE-UI-003  component: AppSidebar  file: src/frontend/components/layout/AppSidebar.tsx
// Integration notes: AC-010/011/012 test responsive breakpoint behaviour.
// Viewport resizing is simulated via window.innerWidth + resize event since jsdom
// does not implement real CSS media queries — assertions target class/attribute
// changes driven by a JS breakpoint hook inside AppSidebar.
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, it, expect, jest } from '@jest/globals';
import { AppSidebar } from '../../../src/frontend/components/layout/AppSidebar';

// ---------------------------------------------------------------------------
// next/navigation mock — pathname not relevant for responsive tests
// ---------------------------------------------------------------------------
jest.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
  useRouter: () => ({ push: jest.fn() }),
}));

// ---------------------------------------------------------------------------
// wrapper factory
// ---------------------------------------------------------------------------
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

// ---------------------------------------------------------------------------
// viewport helper — sets window.innerWidth and fires resize
// ---------------------------------------------------------------------------
function setViewportWidth(width: number): void {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  });
  fireEvent(window, new Event('resize'));
}

// ---------------------------------------------------------------------------
// AC-010 — mobile viewport (< 768px): sidebar hidden, hamburger visible
// ---------------------------------------------------------------------------
describe('AppSidebar responsive — mobile (AC-010)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setViewportWidth(375);
  });

  it('test_sidebar_hidden_by_default_when_viewport_below_md', async () => {
    // TODO: render <AppSidebar /> with createWrapper()
    // TODO: assert sidebar element is not visible (hidden class or aria-hidden)
  });

  it('test_hamburger_button_visible_when_viewport_below_md', async () => {
    // TODO: render <AppSidebar /> with createWrapper()
    // TODO: assert a button with aria-label containing "menu" or role="button" for hamburger is in the document
  });

  it('test_sidebar_overlays_when_hamburger_clicked_on_mobile', async () => {
    // TODO: render <AppSidebar /> with createWrapper()
    // TODO: find and click the hamburger button
    // TODO: await waitFor — assert sidebar element becomes visible
  });

  it('test_sidebar_closes_when_hamburger_clicked_again_on_mobile', async () => {
    // TODO: render <AppSidebar /> with createWrapper()
    // TODO: click hamburger to open, click again to close
    // TODO: assert sidebar returns to hidden state
  });
});

// ---------------------------------------------------------------------------
// AC-011 — tablet viewport (768px–1023px): icon-only rail, no text labels
// ---------------------------------------------------------------------------
describe('AppSidebar responsive — tablet rail (AC-011)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setViewportWidth(768);
  });

  it('test_sidebar_renders_as_icon_rail_when_viewport_is_md', async () => {
    // TODO: render <AppSidebar /> with createWrapper()
    // TODO: assert sidebar is visible
    // TODO: assert sidebar has a class indicating icon-only/rail mode (e.g., no 'w-[220px]', narrower width class)
  });

  it('test_nav_labels_hidden_when_viewport_is_md', async () => {
    // TODO: render <AppSidebar /> with createWrapper()
    // TODO: assert text labels (e.g., "Dashboard", "Applications") are not visible (aria-hidden or hidden class)
    // TODO: assert nav icons remain visible
  });

  it('test_seven_icons_still_present_when_tablet_rail_mode', async () => {
    // TODO: render <AppSidebar /> with createWrapper()
    // TODO: query icon elements within the sidebar nav
    // TODO: assert 7 icons are rendered despite labels being hidden
  });
});

// ---------------------------------------------------------------------------
// AC-012 — desktop viewport (≥ 1024px): full sidebar with icons + labels
// ---------------------------------------------------------------------------
describe('AppSidebar responsive — desktop expanded (AC-012)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setViewportWidth(1280);
  });

  it('test_sidebar_renders_at_full_width_when_viewport_is_lg', async () => {
    // TODO: render <AppSidebar /> with createWrapper()
    // TODO: assert sidebar element has class 'w-[220px]' or equivalent full-width token
  });

  it('test_nav_labels_visible_when_viewport_is_lg', async () => {
    // TODO: render <AppSidebar /> with createWrapper()
    // TODO: assert screen.getByText('Dashboard') is visible
    // TODO: assert screen.getByText('Applications') is visible
  });

  it('test_all_seven_labels_present_when_desktop_expanded', async () => {
    // TODO: render <AppSidebar /> with createWrapper()
    // TODO: assert all 7 label strings are visible: Dashboard, Applications, Base CVs, Tailored CVs, Cover Letters, Billing, Settings
  });
});
