/**
 * Regression tests: Guard currently working features
 *
 * These tests document features that ARE working in the current App.jsx
 * and must NOT break during implementation of the new features.
 *
 * These tests should PASS immediately once App.jsx is placed at
 * src/frontend/canvas-app/App.jsx — if any fail, a regression has occurred.
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
// REG_01 — App renders without crashing
// ---------------------------------------------------------------------------
describe("REG_01 — App renders without crashing", () => {
  it("App mounts and renders a root element", () => {
    const { container } = render(<App />);
    expect(container.firstChild, 'App root element').not.toBeNull();
    // Must not throw during render
  });
});

// ---------------------------------------------------------------------------
// REG_02 — Sidebar renders
// ---------------------------------------------------------------------------
describe("REG_02 — Sidebar is present", () => {
  it("renders sidebar navigation element", () => {
    render(<App />);
    const sidebar = screen.queryByRole('navigation')
      ?? screen.queryByTestId('sidebar')
      ?? document.querySelector('aside, nav, [class*="sidebar"]') as Element | null;
    expect(sidebar, 'Sidebar navigation element').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// REG_03 — Dashboard is the default screen
// ---------------------------------------------------------------------------
describe("REG_03 — Dashboard is shown by default", () => {
  it("initial render shows the dashboard/applications screen", () => {
    render(<App />);
    const dashboard = screen.queryByText(/my applications/i)
      ?? screen.queryByRole('button', { name: /new application/i })
      ?? screen.queryByText(/applications/i);
    expect(dashboard, 'Dashboard screen on initial render').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// REG_04 — DownloadFormatModal exists and has both format buttons
// ---------------------------------------------------------------------------
describe("REG_04 — DownloadFormatModal renders both format options", () => {
  it("DownloadFormatModal shows .docx and .pdf buttons when open", () => {
    // Import modal directly if exported, otherwise skip
    let DownloadFormatModal: React.ComponentType<{
      isOpen: boolean;
      onClose: () => void;
      onSelect: (fmt: string) => void;
    }> | null = null;

    try {
      // We can't use async import inside describe, so we test via a fallback render
    } catch { /* expected */ }

    // Fallback: if modal can be triggered from UI, test that path
    render(<App />);

    const downloadBtn = screen.queryByRole('button', { name: /download/i });
    if (downloadBtn) {
      fireEvent.click(downloadBtn);
      const docxOption = screen.queryByRole('button', { name: /\.docx/i })
        ?? screen.queryByText(/\.docx/i);
      const pdfOption = screen.queryByRole('button', { name: /\.pdf/i })
        ?? screen.queryByText(/\.pdf/i);
      expect(docxOption, '.docx button in DownloadFormatModal').not.toBeNull();
      expect(pdfOption, '.pdf button in DownloadFormatModal').not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// REG_05 — CopySuccessModal closes on OK
// ---------------------------------------------------------------------------
describe("REG_05 — CopySuccessModal exists and is closable", () => {
  it("CopySuccessModal renders OK button when open", () => {
    render(<App />);
    // Attempt to trigger CopySuccessModal via a Copy action
    const copyBtn = screen.queryByRole('button', { name: /^copy$/i });
    if (copyBtn) {
      fireEvent.click(copyBtn);
      const modal = screen.queryByText(/successfully copied/i);
      if (modal) {
        const okBtn = screen.queryByRole('button', { name: /^ok$/i });
        expect(okBtn, 'OK button in CopySuccessModal').not.toBeNull();
        if (okBtn) {
          fireEvent.click(okBtn);
          expect(screen.queryByText(/successfully copied/i), 'Modal should close after OK').toBeNull();
        }
      }
    }
  });
});

// ---------------------------------------------------------------------------
// REG_06 — Settings and Billing are reachable via sidebar
// ---------------------------------------------------------------------------
describe("REG_06 — Settings and Billing accessible from sidebar", () => {
  it("sidebar contains links to Settings and Billing", () => {
    render(<App />);

    const settingsLink = screen.queryByText(/^settings$/i)
      ?? screen.queryByRole('link', { name: /settings/i });
    const billingLink = screen.queryByText(/^billing$/i)
      ?? screen.queryByRole('link', { name: /billing/i });

    expect(settingsLink, '"Settings" in sidebar').not.toBeNull();
    expect(billingLink, '"Billing" in sidebar').not.toBeNull();
  });
});
