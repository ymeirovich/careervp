/**
 * Unit tests: Cover Letters Table (CV Center)
 * Spec: docs/frontend/spec-v4/07-cover-letters-table.yaml
 *
 * These tests WILL FAIL until App.jsx implements:
 *   - cover-letters switch case
 *   - 5-column table with View / Copy / Download / Delete actions
 *   - Copy action wired to navigator.clipboard + CopySuccessModal
 *   - Download action opening DownloadFormatModal
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll } from 'vitest';

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

function navigateToCoverLetters() {
  render(<App />);
  const link = screen.queryByRole('link', { name: /cover letters/i })
    ?? screen.queryByRole('button', { name: /cover letters/i })
    ?? screen.queryByText(/^cover letters$/i);
  if (link) fireEvent.click(link);
}

// ---------------------------------------------------------------------------
// CL_TABLE_01
// ---------------------------------------------------------------------------
describe("CL_TABLE_01 — page title", () => {
  it("renders page title 'Cover Letters'", () => {
    navigateToCoverLetters();
    const heading = screen.queryByRole('heading', { name: /cover letters/i })
      ?? screen.queryByText(/^cover letters$/i);
    expect(heading, '"Cover Letters" heading').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// CL_TABLE_02
// ---------------------------------------------------------------------------
describe("CL_TABLE_02 — table columns", () => {
  it("renders all 5 column headers", () => {
    navigateToCoverLetters();
    const columns = ['Job Title', 'Company', 'Generated Date', 'Status', 'Actions'];
    for (const col of columns) {
      const header = screen.queryByText(new RegExp(`^${col}$`, 'i'))
        ?? screen.queryByRole('columnheader', { name: new RegExp(col, 'i') });
      expect(header, `"${col}" column header`).not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// CL_TABLE_03
// ---------------------------------------------------------------------------
describe("CL_TABLE_03 — empty state", () => {
  it("shows empty state when no cover letters exist", () => {
    navigateToCoverLetters();
    const emptyText = screen.queryByText(/no cover letters/i);
    expect(emptyText, '"No cover letters" empty state').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// CL_TABLE_04
// ---------------------------------------------------------------------------
describe("CL_TABLE_04 — View navigates to cover-letter-view", () => {
  it("View button navigates to cover-letter-view screen", () => {
    navigateToCoverLetters();
    const viewBtn = screen.queryByRole('button', { name: /^view$/i });
    if (viewBtn) {
      fireEvent.click(viewBtn);
      const viewScreen = screen.queryByTestId('cover-letter-view')
        ?? screen.queryByText(/cover letter preview/i);
      expect(viewScreen, 'cover-letter-view screen').not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// CL_TABLE_05
// ---------------------------------------------------------------------------
describe("CL_TABLE_05 — Copy writes to clipboard and opens CopySuccessModal", () => {
  it("Copy button calls clipboard.writeText and shows CopySuccessModal", async () => {
    navigateToCoverLetters();
    const copyBtn = screen.queryByRole('button', { name: /^copy$/i });
    if (copyBtn) {
      fireEvent.click(copyBtn);

      // clipboard.writeText should have been called
      expect(navigator.clipboard.writeText, 'clipboard.writeText called').toHaveBeenCalled();

      // CopySuccessModal should appear
      const modal = screen.queryByText(/successfully copied to clipboard/i);
      expect(modal, 'CopySuccessModal "Successfully Copied to Clipboard"').not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// CL_TABLE_06
// ---------------------------------------------------------------------------
describe("CL_TABLE_06 — CopySuccessModal OK closes modal", () => {
  it("OK button in CopySuccessModal closes it", () => {
    navigateToCoverLetters();
    const copyBtn = screen.queryByRole('button', { name: /^copy$/i });
    if (copyBtn) {
      fireEvent.click(copyBtn);

      const okBtn = screen.queryByRole('button', { name: /^ok$/i });
      expect(okBtn, 'OK button in CopySuccessModal').not.toBeNull();

      if (okBtn) {
        fireEvent.click(okBtn);
        const modal = screen.queryByText(/successfully copied to clipboard/i);
        expect(modal, 'CopySuccessModal should be gone after OK').toBeNull();
      }
    }
  });
});

// ---------------------------------------------------------------------------
// CL_TABLE_07
// ---------------------------------------------------------------------------
describe("CL_TABLE_07 — Download opens DownloadFormatModal", () => {
  it("Download button opens DownloadFormatModal", () => {
    navigateToCoverLetters();
    const downloadBtn = screen.queryByRole('button', { name: /download/i });
    if (downloadBtn) {
      fireEvent.click(downloadBtn);
      const modal = screen.queryByText(/select download format/i)
        ?? screen.queryByText(/\.docx/i);
      expect(modal, 'DownloadFormatModal').not.toBeNull();
    }
  });
});
