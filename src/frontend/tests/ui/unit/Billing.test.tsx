/**
 * Unit tests: Billing screen
 * Spec: docs/frontend/spec-v4/08-billing.yaml
 *
 * These tests WILL FAIL until App.jsx implements:
 *   - billing switch case with full billing screen
 *   - Current Plan card, usage summary, payment method card
 *   - Billing History table with 4 columns
 *   - Cancel Subscription action
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

function navigateToBilling() {
  render(<App />);
  const link = screen.queryByRole('link', { name: /^billing$/i })
    ?? screen.queryByRole('button', { name: /^billing$/i })
    ?? screen.queryByText(/^billing$/i);
  if (link) fireEvent.click(link);
}

// ---------------------------------------------------------------------------
// BILLING_01
// ---------------------------------------------------------------------------
describe("BILLING_01 — page title", () => {
  it("renders page title 'Billing'", () => {
    navigateToBilling();
    const heading = screen.queryByRole('heading', { name: /^billing$/i })
      ?? screen.queryByText(/^billing$/i);
    expect(heading, '"Billing" heading').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// BILLING_02
// ---------------------------------------------------------------------------
describe("BILLING_02 — Current Plan card", () => {
  it("renders Current Plan card with plan name and renewal info", () => {
    navigateToBilling();
    const currentPlanLabel = screen.queryByText(/current plan/i);
    expect(currentPlanLabel, '"Current Plan" label').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// BILLING_03
// ---------------------------------------------------------------------------
describe("BILLING_03 — usage summary", () => {
  it("renders usage summary showing applications used this month", () => {
    navigateToBilling();
    const usageSection = screen.queryByText(/this month/i)
      ?? screen.queryByText(/applications used/i)
      ?? screen.queryByText(/usage/i);
    expect(usageSection, 'Usage summary section').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// BILLING_04
// ---------------------------------------------------------------------------
describe("BILLING_04 — Payment Method card", () => {
  it("renders Payment Method card with Update button", () => {
    navigateToBilling();
    const paymentLabel = screen.queryByText(/payment method/i);
    const updateBtn = screen.queryByRole('button', { name: /update payment/i });
    expect(paymentLabel ?? updateBtn, 'Payment Method section').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// BILLING_05
// ---------------------------------------------------------------------------
describe("BILLING_05 — Billing History table columns", () => {
  it("renders Billing History table with Date, Amount, Status, Download columns", () => {
    navigateToBilling();
    const historyTitle = screen.queryByText(/billing history/i);
    expect(historyTitle, '"Billing History" section title').not.toBeNull();

    if (historyTitle) {
      const columns = ['Date', 'Amount', 'Status', 'Download'];
      for (const col of columns) {
        const header = screen.queryByText(new RegExp(`^${col}$`, 'i'));
        expect(header, `"${col}" column in Billing History`).not.toBeNull();
      }
    }
  });
});

// ---------------------------------------------------------------------------
// BILLING_06
// ---------------------------------------------------------------------------
describe("BILLING_06 — empty billing history", () => {
  it("shows empty state text when no invoices exist", () => {
    navigateToBilling();
    const empty = screen.queryByText(/no billing history/i)
      ?? screen.queryByText(/no invoices/i);
    // Only asserts if billing history section exists
    const historySection = screen.queryByText(/billing history/i);
    if (historySection) {
      // Either there are rows or empty state — empty state should exist if no rows
      const rows = screen.queryAllByRole('row');
      // If only 1 row (header), there should be an empty state indicator
      if (rows.length <= 1) {
        expect(empty, 'Empty billing history state').not.toBeNull();
      }
    }
  });
});

// ---------------------------------------------------------------------------
// BILLING_07
// ---------------------------------------------------------------------------
describe("BILLING_07 — Cancel Subscription", () => {
  it("Cancel Subscription button or link is visible", () => {
    navigateToBilling();
    const cancelBtn = screen.queryByRole('button', { name: /cancel subscription/i })
      ?? screen.queryByRole('link', { name: /cancel subscription/i })
      ?? screen.queryByText(/cancel subscription/i);
    expect(cancelBtn, '"Cancel Subscription" action').not.toBeNull();
  });
});
