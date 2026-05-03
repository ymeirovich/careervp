/**
 * E2E tests: Full application creation and hub flow
 *
 * These tests verify the complete user journey from dashboard through
 * creating a new application to interacting with the Application Hub.
 *
 * These tests WILL FAIL until the full App.jsx implementation is in place:
 *   - New Application Form with all required fields
 *   - Save & Analyze creating an entry and navigating to hub
 *   - Hub showing 6 module cards for the new application
 *   - Generate module action triggering processing state
 *   - Download flow opening DownloadFormatModal
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeAll } from 'vitest';

// Note: @testing-library/user-event not installed. Using fireEvent.
// Install with: cd src/frontend && npm install --save-dev @testing-library/user-event

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
// E2E_01 — Dashboard → New App Form
// ---------------------------------------------------------------------------
describe("E2E_01 — Navigate to New Application Form from dashboard", () => {
  it("clicking + New Application from dashboard opens the form", async () => {
    render(<App />);

    const addBtn = screen.queryByRole('button', { name: /new application/i })
      ?? screen.queryByText(/\+ new application/i);

    expect(addBtn, '"+ New Application" button on dashboard').not.toBeNull();

    if (addBtn) {
      fireEvent.click(addBtn);

      const formTitle = await screen.findByText(/new application/i)
        .catch(() => null);
      const jobTitleField = screen.queryByLabelText(/job title/i)
        ?? screen.queryByPlaceholderText(/job title/i);

      expect(
        formTitle ?? jobTitleField,
        'New Application Form should be visible'
      ).not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// E2E_02 — Fill form and submit
// ---------------------------------------------------------------------------
describe("E2E_02 — Fill out New Application Form and submit", () => {
  it("completes form and activates Save & Analyze button", () => {
    render(<App />);

    // Navigate to new-app form
    const addBtn = screen.queryByRole('button', { name: /new application/i })
      ?? screen.queryByText(/\+ new application/i);
    if (addBtn) fireEvent.click(addBtn);

    // Fill required fields
    const titleField = screen.queryByLabelText(/job title/i)
      ?? screen.queryByPlaceholderText(/job title/i);
    const companyField = screen.queryByLabelText(/company name/i)
      ?? screen.queryByPlaceholderText(/company/i);
    const descField = screen.queryByLabelText(/job description/i)
      ?? screen.queryByPlaceholderText(/description/i);

    if (titleField) fireEvent.change(titleField, { target: { value: 'Frontend Engineer' } });
    if (companyField) fireEvent.change(companyField, { target: { value: 'Acme Corp' } });
    if (descField) fireEvent.change(descField, { target: { value: 'We need a skilled frontend engineer to build React applications' } });

    const submitBtn = screen.queryByRole('button', { name: /save.*analyze/i })
      ?? screen.queryByRole('button', { name: /analyze/i });

    expect(submitBtn, 'Save & Analyze button after filling fields').not.toBeNull();

    if (submitBtn) {
      expect(
        (submitBtn as HTMLButtonElement).disabled,
        'Save & Analyze should be enabled after filling all required fields'
      ).toBe(false);
    }
  });
});

// ---------------------------------------------------------------------------
// E2E_03 — Submit navigates to hub
// ---------------------------------------------------------------------------
describe("E2E_03 — Submitting form navigates to Application Hub", () => {
  it("clicking Save & Analyze transitions to Application Hub", async () => {
    render(<App />);

    const addBtn = screen.queryByRole('button', { name: /new application/i })
      ?? screen.queryByText(/\+ new application/i);
    if (addBtn) fireEvent.click(addBtn);

    const titleField = screen.queryByLabelText(/job title/i)
      ?? screen.queryByPlaceholderText(/job title/i);
    const companyField = screen.queryByLabelText(/company name/i)
      ?? screen.queryByPlaceholderText(/company/i);
    const descField = screen.queryByLabelText(/job description/i)
      ?? screen.queryByPlaceholderText(/description/i);

    if (titleField) fireEvent.change(titleField, { target: { value: 'Frontend Engineer' } });
    if (companyField) fireEvent.change(companyField, { target: { value: 'Acme Corp' } });
    if (descField) fireEvent.change(descField, { target: { value: 'Build React apps' } });

    const submitBtn = screen.queryByRole('button', { name: /save.*analyze/i })
      ?? screen.queryByRole('button', { name: /analyze/i });

    if (submitBtn && !(submitBtn as HTMLButtonElement).disabled) {
      fireEvent.click(submitBtn);

      await waitFor(() => {
        const hubIndicator = screen.queryByText(/application hub/i)
          ?? screen.queryByText(/value proposition report/i)
          ?? screen.queryByTestId('hub-screen');
        expect(hubIndicator, 'Application Hub visible after form submission').not.toBeNull();
      }, { timeout: 3000 });
    }
  });
});

// ---------------------------------------------------------------------------
// E2E_04 — Hub shows all 6 modules for new application
// ---------------------------------------------------------------------------
describe("E2E_04 — Hub displays all 6 modules for newly created application", () => {
  it("all 6 module cards are present after form submission", () => {
    render(<App />);

    // Navigate through form → hub
    const addBtn = screen.queryByRole('button', { name: /new application/i });
    if (addBtn) {
      fireEvent.click(addBtn);
      const titleField = screen.queryByLabelText(/job title/i);
      const companyField = screen.queryByLabelText(/company name/i);
      const descField = screen.queryByLabelText(/job description/i);
      if (titleField) fireEvent.change(titleField, { target: { value: 'Engineer' } });
      if (companyField) fireEvent.change(companyField, { target: { value: 'Corp' } });
      if (descField) fireEvent.change(descField, { target: { value: 'Build things' } });

      const submitBtn = screen.queryByRole('button', { name: /save.*analyze/i });
      if (submitBtn && !(submitBtn as HTMLButtonElement).disabled) {
        fireEvent.click(submitBtn);
      }
    }

    const expectedModules = [
      'Value Proposition Report',
      'Tailored CV',
      'Cover Letter',
      'Gap Analysis',
      'Interview Prep',
      'Company Research',
    ];

    for (const moduleName of expectedModules) {
      const moduleEl = screen.queryByText(new RegExp(moduleName, 'i'));
      expect(moduleEl, `"${moduleName}" module on hub`).not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// E2E_05 — Download format selection
// ---------------------------------------------------------------------------
describe("E2E_05 — Download format selection flow", () => {
  it("DownloadFormatModal offers .docx and .pdf and closes on selection", () => {
    render(<App />);

    // Trigger a download action anywhere in the app
    const downloadBtn = screen.queryByRole('button', { name: /download/i });

    if (downloadBtn) {
      fireEvent.click(downloadBtn);

      const docxBtn = screen.queryByRole('button', { name: /\.docx/i });
      const pdfBtn = screen.queryByRole('button', { name: /\.pdf/i });

      expect(docxBtn, '.docx format button in DownloadFormatModal').not.toBeNull();
      expect(pdfBtn, '.pdf format button in DownloadFormatModal').not.toBeNull();

      if (docxBtn) {
        fireEvent.click(docxBtn);
        // Modal should close after selection
        const modal = screen.queryByText(/select download format/i);
        expect(modal, 'DownloadFormatModal should close after format selection').toBeNull();
      }
    }
  });
});
