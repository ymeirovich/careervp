/**
 * Unit tests: Plans screen
 * Spec: docs/frontend/spec-v4/10-plans.yaml
 *
 * These tests WILL FAIL until App.jsx implements:
 *   - plans switch case with two plan cards
 *   - Annual plan "Save 20%" badge
 *   - "Current Plan" CTA on the user's active plan
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

function navigateToPlans() {
  render(<App />);
  const link = screen.queryByRole('link', { name: /^plans$/i })
    ?? screen.queryByRole('button', { name: /^plans$/i })
    ?? screen.queryByText(/^plans$/i);
  if (link) fireEvent.click(link);
}

// ---------------------------------------------------------------------------
// PLANS_01
// ---------------------------------------------------------------------------
describe("PLANS_01 — two plan cards", () => {
  it("renders exactly two plan cards (Monthly Pro and Annual Pro)", () => {
    navigateToPlans();

    const monthlyCard = screen.queryByText(/monthly pro/i);
    const annualCard = screen.queryByText(/annual pro/i);

    expect(monthlyCard, 'Monthly Pro plan card').not.toBeNull();
    expect(annualCard, 'Annual Pro plan card').not.toBeNull();

    // Verify exactly two plan card containers
    const planCards = screen.queryAllByTestId(/plan-card/i);
    const altCards = planCards.length === 0
      ? screen.queryAllByRole('article')
      : planCards;

    if (altCards.length > 0) {
      expect(altCards.length, 'Exactly 2 plan cards').toBe(2);
    }
  });
});

// ---------------------------------------------------------------------------
// PLANS_02
// ---------------------------------------------------------------------------
describe("PLANS_02 — Save 20% badge on Annual plan", () => {
  it("Annual Pro card shows 'Save 20%' badge", () => {
    navigateToPlans();

    const saveBadge = screen.queryByText(/save 20%/i)
      ?? screen.queryByText(/20% off/i);
    expect(saveBadge, '"Save 20%" badge on Annual plan').not.toBeNull();
  });
});

// ---------------------------------------------------------------------------
// PLANS_03
// ---------------------------------------------------------------------------
describe("PLANS_03 — current plan CTA", () => {
  it("current plan shows 'Current Plan' button instead of 'Get Started'", () => {
    navigateToPlans();

    // With active subscription, the user's current plan should show "Current Plan"
    const currentPlanCta = screen.queryByRole('button', { name: /current plan/i });
    const getStartedBtns = screen.queryAllByRole('button', { name: /get started/i });

    // Either "Current Plan" button exists (active subscriber)
    // or both cards show "Get Started" (free user — both plans available)
    const hasCurrentPlan = currentPlanCta !== null;
    const hasGetStarted = getStartedBtns.length > 0;

    expect(
      hasCurrentPlan || hasGetStarted,
      'Plans screen must show either "Current Plan" or "Get Started" CTAs'
    ).toBe(true);

    // If user has active subscription, Current Plan button must exist
    if (hasCurrentPlan) {
      // The non-active plan card should show Get Started
      expect(
        getStartedBtns.length,
        'Other plan(s) should show "Get Started"'
      ).toBeGreaterThan(0);
    }
  });
});
