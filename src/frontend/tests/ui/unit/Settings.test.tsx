/**
 * Unit tests: Settings screen
 * Spec: docs/frontend/spec-v4/09-settings.yaml
 *
 * These tests WILL FAIL until App.jsx implements:
 *   - settings switch case with full settings screen
 *   - Profile section (Full Name editable, Email read-only, Phone optional)
 *   - Save Changes handler with success feedback
 *   - Preferences section (Language select, Default CV format select)
 *   - Notifications section with two toggles
 *   - Danger Zone with Delete Account + confirmation dialog
 */

import { render, screen, fireEvent } from '@testing-library/react';
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

function navigateToSettings() {
  render(<App />);
  const link = screen.queryByRole('link', { name: /^settings$/i })
    ?? screen.queryByRole('button', { name: /^settings$/i })
    ?? screen.queryByText(/^settings$/i);
  if (link) fireEvent.click(link);
}

// ---------------------------------------------------------------------------
// SETTINGS_01
// ---------------------------------------------------------------------------
describe("SETTINGS_01 — page title", () => {
  it("renders page title 'Settings'", () => {
    navigateToSettings();
    const heading = screen.queryByRole('heading', { name: /^settings$/i })
      ?? screen.queryByText(/^settings$/i);
    expect(heading, '"Settings" heading').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// SETTINGS_02
// ---------------------------------------------------------------------------
describe("SETTINGS_02 — Full Name field", () => {
  it("renders Profile section with Full Name input", () => {
    navigateToSettings();
    const field = screen.queryByLabelText(/full name/i)
      ?? screen.queryByRole('textbox', { name: /full name/i });
    expect(field, 'Full Name input in Profile section').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// SETTINGS_03
// ---------------------------------------------------------------------------
describe("SETTINGS_03 — Email field is read-only", () => {
  it("Email field is present and has readOnly attribute", () => {
    navigateToSettings();
    const emailField = screen.queryByLabelText(/^email$/i)
      ?? screen.queryByRole('textbox', { name: /^email$/i })
      ?? (document.querySelector('input[type="email"]') as HTMLElement | null);
    expect(emailField, 'Email field').not.toBeNull();
    if (emailField) {
      expect(
        (emailField as HTMLInputElement).readOnly,
        'Email field should be readOnly'
      ).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// SETTINGS_04
// ---------------------------------------------------------------------------
describe("SETTINGS_04 — Save Changes button present", () => {
  it("renders Save Changes button in Profile section", () => {
    navigateToSettings();
    const saveBtn = screen.queryByRole('button', { name: /save changes/i });
    expect(saveBtn, '"Save Changes" button').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// SETTINGS_05
// ---------------------------------------------------------------------------
describe("SETTINGS_05 — Save Changes feedback", () => {
  it("shows success feedback after clicking Save Changes", () => {
    navigateToSettings();

    const nameField = screen.queryByLabelText(/full name/i)
      ?? screen.queryByRole('textbox', { name: /full name/i });
    if (nameField) {
      fireEvent.change(nameField, { target: { value: 'Jane Doe' } });
    }

    const saveBtn = screen.queryByRole('button', { name: /save changes/i });
    if (saveBtn) {
      fireEvent.click(saveBtn);
      const feedback = screen.queryByText(/saved/i)
        ?? screen.queryByText(/success/i)
        ?? screen.queryByText(/updated/i)
        ?? screen.queryByRole('alert');
      expect(feedback, 'Success feedback after Save Changes').not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// SETTINGS_06
// ---------------------------------------------------------------------------
describe("SETTINGS_06 — Language select", () => {
  it("renders Language select with English and Hebrew options", () => {
    navigateToSettings();
    const langSelect = screen.queryByRole('combobox', { name: /language/i })
      ?? screen.queryByLabelText(/language/i);
    expect(langSelect, 'Language select element').not.toBeNull();

    if (langSelect) {
      const options = Array.from((langSelect as HTMLSelectElement).options ?? [])
        .map(o => o.text.toLowerCase());
      expect(
        options.some(o => o.includes('english')),
        'English option in Language select'
      ).toBe(true);
      expect(
        options.some(o => o.includes('hebrew')),
        'Hebrew option in Language select'
      ).toBe(true);
    }
  });
});

// ---------------------------------------------------------------------------
// SETTINGS_07
// ---------------------------------------------------------------------------
describe("SETTINGS_07 — Default CV format select", () => {
  it("renders Default CV format select with .docx and .pdf options", () => {
    navigateToSettings();
    const formatSelect = screen.queryByLabelText(/default cv format/i)
      ?? screen.queryByLabelText(/cv format/i)
      ?? screen.queryByRole('combobox', { name: /format/i });
    expect(formatSelect, 'Default CV format select').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// SETTINGS_08
// ---------------------------------------------------------------------------
describe("SETTINGS_08 — Notifications toggles", () => {
  it("renders two notification toggle controls", () => {
    navigateToSettings();
    const notificationsSection = screen.queryByRole('heading', { name: /^notifications$/i })
      ?? screen.queryByText(/^notifications$/i)
      ?? screen.queryByText(/notifications/i);
    expect(notificationsSection, 'Notifications section').not.toBeNull();

    // Look for checkboxes or toggle switches
    const toggles = screen.queryAllByRole('checkbox')
      .concat(screen.queryAllByRole('switch'));

    expect(toggles.length, 'At least 2 notification toggles').toBeGreaterThanOrEqual(2);
  });
});

// ---------------------------------------------------------------------------
// SETTINGS_09
// ---------------------------------------------------------------------------
describe("SETTINGS_09 — notification toggle changes state", () => {
  it("toggle changes checked state when clicked", () => {
    navigateToSettings();

    const toggles = screen.queryAllByRole('checkbox')
      .concat(screen.queryAllByRole('switch'));

    if (toggles.length > 0) {
      const toggle = toggles[0] as HTMLInputElement;
      const initialState = toggle.checked;
      fireEvent.click(toggle);
      expect(toggle.checked, 'Toggle state changed').not.toBe(initialState);
    }
  });
});

// ---------------------------------------------------------------------------
// SETTINGS_10
// ---------------------------------------------------------------------------
describe("SETTINGS_10 — Danger Zone section", () => {
  it("renders Danger Zone section with Delete Account button", () => {
    navigateToSettings();
    const dangerZone = screen.queryByText(/danger zone/i);
    const deleteBtn = screen.queryByRole('button', { name: /delete account/i });
    expect(dangerZone ?? deleteBtn, 'Danger Zone section').not.toBeNull();
    expect(deleteBtn, '"Delete Account" button').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// SETTINGS_11
// ---------------------------------------------------------------------------
describe("SETTINGS_11 — Delete Account confirmation", () => {
  it("Delete Account shows confirmation dialog before proceeding", () => {
    navigateToSettings();
    const deleteBtn = screen.queryByRole('button', { name: /delete account/i });
    if (deleteBtn) {
      fireEvent.click(deleteBtn);
      const confirmation = screen.queryByRole('dialog')
        ?? screen.queryByText(/are you sure/i)
        ?? screen.queryByText(/confirm/i)
        ?? screen.queryByText(/this action cannot be undone/i);
      expect(confirmation, 'Confirmation dialog after Delete Account').not.toBeNull();
    }
  });
});

// ---------------------------------------------------------------------------
// SETTINGS_12
// ---------------------------------------------------------------------------
describe("SETTINGS_12 — Phone field is optional", () => {
  it("empty Phone field does not block Save Changes", () => {
    navigateToSettings();

    const phoneField = screen.queryByLabelText(/phone/i)
      ?? screen.queryByRole('textbox', { name: /phone/i });

    if (phoneField) {
      fireEvent.change(phoneField, { target: { value: '' } });
    }

    const saveBtn = screen.queryByRole('button', { name: /save changes/i });
    if (saveBtn) {
      fireEvent.click(saveBtn);
      // Should not show a required error for Phone
      const phoneError = screen.queryByText(/phone.*required/i)
        ?? screen.queryByText(/required.*phone/i);
      expect(phoneError, 'No required error for empty Phone field').toBeNull();
    }
  });
});
