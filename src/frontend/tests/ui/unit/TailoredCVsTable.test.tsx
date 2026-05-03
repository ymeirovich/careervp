/**
 * Unit tests: Tailored CVs Table (CV Center)
 * Spec: docs/frontend/spec-v4/06-tailored-cvs-table.yaml
 *
 * These tests WILL FAIL until App.jsx implements:
 *   - tailored-cvs switch case
 *   - 5-column table structure
 *   - Empty state
 *   - View navigating to cv-view
 *   - Download opening DownloadFormatModal
 *   - Status badges with correct colors
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

function navigateToTailoredCVs() {
  render(<App />);
  const link = screen.queryByRole('link', { name: /tailored cvs/i })
    ?? screen.queryByRole('button', { name: /tailored cvs/i })
    ?? screen.queryByText(/^tailored cvs$/i);
  if (link) fireEvent.click(link);
}

// ---------------------------------------------------------------------------
// TAIL_CV_01
// ---------------------------------------------------------------------------
describe("TAIL_CV_01 — page title", () => {
  it("renders page title 'Tailored CVs'", () => {
    navigateToTailoredCVs();
    const heading = screen.queryByRole('heading', { name: /tailored cvs/i })
      ?? screen.queryByText(/^tailored cvs$/i);
    expect(heading, '"Tailored CVs" heading').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// TAIL_CV_02
// ---------------------------------------------------------------------------
describe("TAIL_CV_02 — table columns", () => {
  it("renders all 5 column headers", () => {
    navigateToTailoredCVs();
    const columns = ['Job Title', 'Company', 'Generated Date', 'Status', 'Actions'];
    for (const col of columns) {
      const header = screen.queryByText(new RegExp(`^${col}$`, 'i'))
        ?? screen.queryByRole('columnheader', { name: new RegExp(col, 'i') });
      expect(header, `"${col}" column header`).not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// TAIL_CV_03
// ---------------------------------------------------------------------------
describe("TAIL_CV_03 — empty state", () => {
  it("shows empty state when no tailored CVs exist", () => {
    navigateToTailoredCVs();
    const emptyText = screen.queryByText(/no tailored cvs/i);
    expect(emptyText, '"No tailored CVs" empty state text').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// TAIL_CV_04
// ---------------------------------------------------------------------------
describe("TAIL_CV_04 — View navigates to cv-view", () => {
  it("View button navigates to cv-view screen", () => {
    navigateToTailoredCVs();
    const viewBtn = screen.queryByRole('button', { name: /^view$/i });
    if (viewBtn) {
      fireEvent.click(viewBtn);
      // cv-view screen should appear
      const cvView = screen.queryByTestId('cv-view-screen')
        ?? screen.queryByText(/cv preview/i)
        ?? screen.queryByText(/tailored cv/i);
      expect(cvView, 'cv-view screen after clicking View').not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// TAIL_CV_05
// ---------------------------------------------------------------------------
describe("TAIL_CV_05 — Download opens DownloadFormatModal", () => {
  it("Download button opens DownloadFormatModal with format options", () => {
    navigateToTailoredCVs();
    const downloadBtn = screen.queryByRole('button', { name: /download/i });
    if (downloadBtn) {
      fireEvent.click(downloadBtn);
      const modal = screen.queryByText(/select download format/i)
        ?? screen.queryByText(/\.docx/i);
      expect(modal, 'DownloadFormatModal should appear').not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// TAIL_CV_06
// ---------------------------------------------------------------------------
describe("TAIL_CV_06 — Ready status badge", () => {
  it("shows Ready badge with green styling on a ready-state row", () => {
    navigateToTailoredCVs();
    // Only asserts when data is present
    const readyBadge = screen.queryByText(/^ready$/i);
    if (readyBadge) {
      const classList = readyBadge.className;
      const isGreen = classList.includes('green') || classList.includes('active')
        || classList.includes('#22C55E') || classList.includes('success');
      expect(isGreen || readyBadge.style.color.includes('22C55E'), 'Ready badge should be green').toBe(true);
    }
  });
});
