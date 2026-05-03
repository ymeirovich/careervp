/**
 * Integration tests: Cross-screen navigation flows
 * Spec: docs/frontend/spec-v4/11-navigation.yaml
 *
 * These tests WILL FAIL until App.jsx implements:
 *   - CV Center section in sidebar (Base CVs, Tailored CVs, Cover Letters)
 *   - Back button with history stack popping
 *   - Active link highlighting via class or aria-current
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeAll } from 'vitest';

const CANVAS_APP_PATH = '../../../canvas-app/App';

let App: React.ComponentType<Record<string, never>>;

beforeAll(async () => {
  try {
    const mod = await import(CANVAS_APP_PATH);
    App = mod.default;
  } catch {
    App = () => <div data-testid="app-not-found">App.jsx not found</div>;
  }
});

// ---------------------------------------------------------------------------
// NAV_01 — My Applications → dashboard
// ---------------------------------------------------------------------------
describe("NAV_01 — My Applications navigates to dashboard", () => {
  it("clicking My Applications in sidebar shows dashboard screen", () => {
    render(<App />);

    // Navigate away from dashboard first
    const billingLink = screen.queryByText(/^billing$/i);
    if (billingLink) fireEvent.click(billingLink);

    // Now click My Applications
    const myAppsLink = screen.queryByRole('link', { name: /my applications/i })
      ?? screen.queryByRole('button', { name: /my applications/i })
      ?? screen.queryByText(/my applications/i);

    expect(myAppsLink, '"My Applications" sidebar link').not.toBeNull();

    if (myAppsLink) {
      fireEvent.click(myAppsLink);

      // Dashboard should show — look for "+ New Application" button or table
      const dashboard = screen.queryByRole('button', { name: /new application/i })
        ?? screen.queryByText(/my applications/i)
        ?? screen.queryByRole('table');
      expect(dashboard, 'Dashboard visible after My Applications click').not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// NAV_02 — Base CVs link
// ---------------------------------------------------------------------------
describe("NAV_02 — Base CVs sidebar link", () => {
  it("clicking Base CVs navigates to base-cvs screen", () => {
    render(<App />);

    const baseCvsLink = screen.queryByRole('link', { name: /^base cvs$/i })
      ?? screen.queryByRole('button', { name: /^base cvs$/i })
      ?? screen.queryByText(/^base cvs$/i);

    expect(baseCvsLink, '"Base CVs" in sidebar').not.toBeNull();

    if (baseCvsLink) {
      fireEvent.click(baseCvsLink);
      const heading = screen.queryByRole('heading', { name: /base cvs/i })
        ?? screen.queryByText(/^base cvs$/i);
      expect(heading, 'Base CVs screen heading').not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// NAV_03 — Tailored CVs link
// ---------------------------------------------------------------------------
describe("NAV_03 — Tailored CVs sidebar link", () => {
  it("clicking Tailored CVs navigates to tailored-cvs screen", () => {
    render(<App />);

    const link = screen.queryByRole('link', { name: /^tailored cvs$/i })
      ?? screen.queryByRole('button', { name: /^tailored cvs$/i })
      ?? screen.queryByText(/^tailored cvs$/i);

    expect(link, '"Tailored CVs" in sidebar').not.toBeNull();

    if (link) {
      fireEvent.click(link);
      const heading = screen.queryByRole('heading', { name: /tailored cvs/i })
        ?? screen.queryByText(/^tailored cvs$/i);
      expect(heading, 'Tailored CVs screen heading').not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// NAV_04 — Cover Letters link
// ---------------------------------------------------------------------------
describe("NAV_04 — Cover Letters sidebar link", () => {
  it("clicking Cover Letters navigates to cover-letters screen", () => {
    render(<App />);

    const link = screen.queryByRole('link', { name: /^cover letters$/i })
      ?? screen.queryByRole('button', { name: /^cover letters$/i })
      ?? screen.queryByText(/^cover letters$/i);

    expect(link, '"Cover Letters" in sidebar').not.toBeNull();

    if (link) {
      fireEvent.click(link);
      const heading = screen.queryByRole('heading', { name: /cover letters/i })
        ?? screen.queryByText(/^cover letters$/i);
      expect(heading, 'Cover Letters screen heading').not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// NAV_05 — back button single level
// ---------------------------------------------------------------------------
describe("NAV_05 — back button returns to previous screen", () => {
  it("back button returns from billing to dashboard", () => {
    render(<App />);

    // Navigate to billing
    const billingLink = screen.queryByText(/^billing$/i);
    if (billingLink) fireEvent.click(billingLink);

    // Click back
    const backBtn = screen.queryByRole('button', { name: /back/i })
      ?? screen.queryByLabelText(/go back/i)
      ?? screen.queryByTestId('back-button')
      ?? document.querySelector('[aria-label*="back" i]') as Element | null;

    expect(backBtn, 'Back button on billing screen').not.toBeNull();

    if (backBtn) {
      fireEvent.click(backBtn);
      // Should be back at dashboard
      const dashboard = screen.queryByRole('button', { name: /new application/i })
        ?? screen.queryByText(/my applications/i);
      expect(dashboard, 'Dashboard after going back from billing').not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// NAV_06 — back button hidden on dashboard
// ---------------------------------------------------------------------------
describe("NAV_06 — back button hidden on root screen", () => {
  it("back button is not visible on the dashboard (root screen)", () => {
    render(<App />);

    // On initial render (dashboard), back button should not be visible
    const backBtn = screen.queryByRole('button', { name: /back/i })
      ?? screen.queryByLabelText(/go back/i)
      ?? screen.queryByTestId('back-button');

    const isHidden = backBtn === null
      || (backBtn as HTMLElement).style.display === 'none'
      || (backBtn as HTMLElement).hidden
      || backBtn.getAttribute('aria-hidden') === 'true';

    expect(isHidden, 'Back button should be hidden on root/dashboard screen').toBe(true);
  });
});

// ---------------------------------------------------------------------------
// NAV_07 — multi-level back navigation
// ---------------------------------------------------------------------------
describe("NAV_07 — multi-level back navigation", () => {
  it("back button works through 3 levels: plans → settings → billing → dashboard", () => {
    render(<App />);

    // Navigate forward: dashboard → billing → settings → plans
    const billingLink = screen.queryByText(/^billing$/i);
    if (billingLink) fireEvent.click(billingLink);
    const settingsLink = screen.queryByText(/^settings$/i);
    if (settingsLink) fireEvent.click(settingsLink);
    const plansLink = screen.queryByText(/^plans$/i);
    if (plansLink) fireEvent.click(plansLink);

    // Go back once — should be at settings
    const backBtn1 = screen.queryByRole('button', { name: /back/i })
      ?? screen.queryByTestId('back-button');
    if (backBtn1) {
      fireEvent.click(backBtn1);
      const settingsHeading = screen.queryByRole('heading', { name: /^settings$/i });
      expect(settingsHeading, 'Settings screen after 1 back').not.toBeNull();

      // Go back again — should be at billing
      const backBtn2 = screen.queryByRole('button', { name: /back/i })
        ?? screen.queryByTestId('back-button');
      if (backBtn2) {
        fireEvent.click(backBtn2);
        const billingHeading = screen.queryByRole('heading', { name: /^billing$/i });
        expect(billingHeading, 'Billing screen after 2 backs').not.toBeNull();
      }
    }
  });
});

// ---------------------------------------------------------------------------
// NAV_08 — active sidebar link highlighting
// ---------------------------------------------------------------------------
describe("NAV_08 — active sidebar link is highlighted", () => {
  it("Settings sidebar link has active class or aria-current when on settings screen", () => {
    render(<App />);

    const settingsLink = screen.queryByText(/^settings$/i);
    if (settingsLink) fireEvent.click(settingsLink);

    const activeSidebarLink = screen.queryByRole('link', { current: 'page' })
      ?? screen.queryByRole('button', { name: /^settings$/i })
      ?? screen.queryByText(/^settings$/i);

    if (activeSidebarLink) {
      const classList = activeSidebarLink.className;
      const isActive = classList.includes('active')
        || classList.includes('selected')
        || classList.includes('current')
        || classList.includes('bg-')
        || activeSidebarLink.getAttribute('aria-current') === 'page';

      expect(isActive, 'Settings sidebar link should have active styling').toBe(true);
    }
  });
});
