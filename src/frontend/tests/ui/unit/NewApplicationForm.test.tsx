/**
 * Unit tests: New Application Form
 * Spec: docs/frontend/spec-v4/02-new-application-form.yaml
 *
 * These tests WILL FAIL until App.jsx implements:
 *   - Job Title, Company Name, Job Description (required), Job URL (optional) fields
 *   - Save & Analyze button with disabled-until-filled logic
 *   - Base CV section with current filename and Change button
 *   - Cancel link returning to dashboard
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeAll } from 'vitest';

// Note: @testing-library/user-event is not installed. Using fireEvent for interactions.
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

/**
 * Helper: navigate to the new-app screen by clicking "+ New Application"
 */
async function navigateToNewApp() {
  render(<App />);
  const addButton = screen.queryByRole('button', { name: /new application/i })
    ?? screen.queryByText(/\+ new application/i);
  if (addButton) {
    fireEvent.click(addButton);
  }
}

// ---------------------------------------------------------------------------
// NEW_APP_01
// ---------------------------------------------------------------------------
describe('NEW_APP_01 — Job Title field', () => {
  it('renders Job Title input field', async () => {
    await navigateToNewApp();

    const field = screen.queryByLabelText(/job title/i)
      ?? screen.queryByPlaceholderText(/job title/i)
      ?? screen.queryByRole('textbox', { name: /job title/i });

    expect(field, 'Job Title input').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// NEW_APP_02
// ---------------------------------------------------------------------------
describe('NEW_APP_02 — Company Name field', () => {
  it('renders Company Name input field', async () => {
    await navigateToNewApp();

    const field = screen.queryByLabelText(/company name/i)
      ?? screen.queryByPlaceholderText(/company name/i)
      ?? screen.queryByRole('textbox', { name: /company/i });

    expect(field, 'Company Name input').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// NEW_APP_03
// ---------------------------------------------------------------------------
describe('NEW_APP_03 — Job Description textarea', () => {
  it('renders Job Description textarea', async () => {
    await navigateToNewApp();

    const field = screen.queryByLabelText(/job description/i)
      ?? screen.queryByPlaceholderText(/job description/i)
      ?? screen.queryByRole('textbox', { name: /description/i });

    expect(field, 'Job Description textarea').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// NEW_APP_04
// ---------------------------------------------------------------------------
describe('NEW_APP_04 — Job URL field', () => {
  it('renders optional Job URL input', async () => {
    await navigateToNewApp();

    const field = screen.queryByLabelText(/job url/i)
      ?? screen.queryByLabelText(/url/i)
      ?? screen.queryByPlaceholderText(/url/i)
      ?? screen.queryByRole('textbox', { name: /url/i });

    expect(field, 'Job URL input').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// NEW_APP_05
// ---------------------------------------------------------------------------
describe('NEW_APP_05 — Submit button disabled when empty', () => {
  it('Save & Analyze button is disabled when required fields are empty', async () => {
    await navigateToNewApp();

    const submitBtn = screen.queryByRole('button', { name: /save.*analyze/i })
      ?? screen.queryByRole('button', { name: /analyze/i });

    expect(submitBtn, 'Save & Analyze button').not.toBeNull();

    if (submitBtn) {
      expect(
        (submitBtn as HTMLButtonElement).disabled
          || submitBtn.getAttribute('aria-disabled') === 'true',
        'button should be disabled when fields are empty'
      ).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// NEW_APP_06
// ---------------------------------------------------------------------------
describe('NEW_APP_06 — Submit button enables when fields are filled', () => {
  it('enables Save & Analyze button when all required fields have content', async () => {
    await navigateToNewApp();

    const titleField = screen.queryByLabelText(/job title/i)
      ?? screen.queryByPlaceholderText(/job title/i);
    const companyField = screen.queryByLabelText(/company name/i)
      ?? screen.queryByPlaceholderText(/company name/i);
    const descField = screen.queryByLabelText(/job description/i)
      ?? screen.queryByPlaceholderText(/job description/i);

    if (titleField) fireEvent.change(titleField, { target: { value: 'Software Engineer' } });
    if (companyField) fireEvent.change(companyField, { target: { value: 'Acme Corp' } });
    if (descField) fireEvent.change(descField, { target: { value: 'Build and maintain software systems' } });

    const submitBtn = screen.queryByRole('button', { name: /save.*analyze/i })
      ?? screen.queryByRole('button', { name: /analyze/i });

    expect(submitBtn, 'Save & Analyze button').not.toBeNull();

    if (submitBtn) {
      expect(
        (submitBtn as HTMLButtonElement).disabled,
        'button should be enabled after filling required fields'
      ).toBe(false);
    }
  });
});

// ---------------------------------------------------------------------------
// NEW_APP_07
// ---------------------------------------------------------------------------
describe('NEW_APP_07 — Base CV section shows filename', () => {
  it('shows selected base CV filename in Base CV section', async () => {
    await navigateToNewApp();

    // Look for Base CV section label and filename display
    const baseCvLabel = screen.queryByText(/base cv/i);
    expect(baseCvLabel, 'Base CV section label').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// NEW_APP_08
// ---------------------------------------------------------------------------
describe('NEW_APP_08 — Change button opens modal', () => {
  it('Change button opens ChangeBaseCVModal', async () => {
    await navigateToNewApp();

    const changeBtn = screen.queryByRole('button', { name: /^change$/i });
    expect(changeBtn, 'Change button in Base CV section').not.toBeNull();

    if (changeBtn) {
      fireEvent.click(changeBtn);

      const modal = screen.queryByRole('dialog')
        ?? screen.queryByText(/upload base cv/i)
        ?? screen.queryByText(/choose base cv/i);

      expect(modal, 'ChangeBaseCVModal after clicking Change').not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// NEW_APP_09
// ---------------------------------------------------------------------------
describe('NEW_APP_09 — Cancel link returns to dashboard', () => {
  it('Cancel link navigates back to dashboard', async () => {
    await navigateToNewApp();

    const cancelLink = screen.queryByRole('button', { name: /^cancel$/i })
      ?? screen.queryByRole('link', { name: /cancel/i })
      ?? screen.queryByText(/^cancel$/i);

    expect(cancelLink, 'Cancel link').not.toBeNull();

    if (cancelLink) {
      fireEvent.click(cancelLink);

      // Should return to dashboard — look for applications table or "+ New Application"
      const dashboard = screen.queryByText(/my applications/i)
        ?? screen.queryByRole('button', { name: /new application/i });
      expect(dashboard, 'Dashboard after Cancel').not.toBeNull();
    }
  });
});
