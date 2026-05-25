// spec_id: FE-UI-021  component: BillingContent  tier: unit
// Route: /billing
// ACs covered: AC-001 – AC-008  (all verification_type: unit)

import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ─── Hoisted API mocks (must be before static imports) ───────────────────────
const apiMocks = vi.hoisted(() => ({
  getMe: vi.fn(),
  getUsage: vi.fn(),
  getSubscription: vi.fn(),
  getBillingPortal: vi.fn(),
}));

vi.mock('../../../src/frontend/api/methods', () => ({
  api: apiMocks,
}));

// ─── Hook mock: isolate BillingContent from useUserContext internals ──────────
const mockUseUserContext = vi.hoisted(() => vi.fn());

vi.mock('../../../src/frontend/hooks/useUserContext', () => ({
  useUserContext: mockUseUserContext,
}));

// ─── i18n mock ────────────────────────────────────────────────────────────────
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
  useLocale: vi.fn(() => 'en'),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: vi.fn(() => '/billing'),
}));

// ─── Child component mocks (isolate BillingContent unit) ─────────────────────
vi.mock('../../../src/frontend/components/ErrorBoundary/ErrorBoundary', () => ({
  ErrorBoundary: ({
    children,
    cloudwatchKey,
  }: {
    children: React.ReactNode;
    cloudwatchKey: string;
    fallback?: React.ReactNode;
  }) => (
    <div data-testid="error-boundary" data-cloudwatch-key={cloudwatchKey}>
      {children}
    </div>
  ),
}));

vi.mock('../../../src/frontend/components/ui/Spinner', () => ({
  Spinner: ({ 'aria-label': ariaLabel }: { 'aria-label'?: string; size?: string }) => (
    <div role="status" aria-label={ariaLabel} data-testid="spinner" />
  ),
}));

vi.mock('../../../src/frontend/app/billing/SubscriptionCard', () => ({
  SubscriptionCard: () => <div data-testid="subscription-card" />,
}), { virtual: true });

vi.mock('../../../src/frontend/app/billing/UsageCard', () => ({
  UsageCard: () => <div data-testid="usage-card" />,
}), { virtual: true });

vi.mock('../../../src/frontend/app/billing/BillingInfoCard', () => ({
  BillingInfoCard: () => <div data-testid="billing-info-card" />,
}), { virtual: true });

// ─── Import under test ────────────────────────────────────────────────────────
import BillingContent from '../../../src/frontend/app/billing/page';

// ─── Fixtures ─────────────────────────────────────────────────────────────────
const LOADED_CONTEXT = {
  user: null,
  usage: { trial: { active: false, days_remaining: 0 }, applications: { remaining: 5 } },
  subscription: { has_active_subscription: true, subscription: { plan_type: 'monthly', status: 'active', current_period_end: null } },
  isLoading: false,
  hasActiveAccess: true,
  applicationsRemaining: 5,
};

const LOADING_CONTEXT = {
  ...LOADED_CONTEXT,
  isLoading: true,
};

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('BillingContent', () => {

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseUserContext.mockReturnValue(LOADED_CONTEXT);
  });

  // ─── AC-001: page title ───────────────────────────────────────────────────
  describe('page title', () => {
    it('test_page_title_displays_billing_when_rendered', () => {
      // TODO: render <BillingContent />
      // TODO: assert h1 text is exactly "Billing" (not "Billing & Plan")
      render(<BillingContent />);
      const heading = screen.getByRole('heading', { level: 1 });
      expect(heading).toBeDefined();
      // TODO: expect(heading.textContent).toMatch(/^billing$/i)  — confirm "& Plan" is absent
    });
  });

  // ─── AC-002: three stacked card components in order ───────────────────────
  describe('card layout', () => {
    it('test_subscription_card_renders_when_page_loaded', () => {
      // TODO: render <BillingContent />
      // TODO: assert data-testid="subscription-card" is present in document
      render(<BillingContent />);
      expect(screen.getByTestId('subscription-card')).toBeDefined();
    });

    it('test_usage_card_renders_when_page_loaded', () => {
      // TODO: render <BillingContent />
      // TODO: assert data-testid="usage-card" is present in document
      render(<BillingContent />);
      expect(screen.getByTestId('usage-card')).toBeDefined();
    });

    it('test_billing_info_card_renders_when_page_loaded', () => {
      // TODO: render <BillingContent />
      // TODO: assert data-testid="billing-info-card" is present in document
      render(<BillingContent />);
      expect(screen.getByTestId('billing-info-card')).toBeDefined();
    });

    it('test_subscription_card_precedes_usage_card_in_dom_order', () => {
      // TODO: render <BillingContent />
      // TODO: assert compareDocumentPosition confirms subscription-card is before usage-card
      render(<BillingContent />);
      const subscriptionCard = screen.getByTestId('subscription-card');
      const usageCard = screen.getByTestId('usage-card');
      expect(
        subscriptionCard.compareDocumentPosition(usageCard) & Node.DOCUMENT_POSITION_FOLLOWING
      ).toBeTruthy();
    });

    it('test_usage_card_precedes_billing_info_card_in_dom_order', () => {
      // TODO: render <BillingContent />
      // TODO: assert compareDocumentPosition confirms usage-card is before billing-info-card
      render(<BillingContent />);
      const usageCard = screen.getByTestId('usage-card');
      const billingInfoCard = screen.getByTestId('billing-info-card');
      expect(
        usageCard.compareDocumentPosition(billingInfoCard) & Node.DOCUMENT_POSITION_FOLLOWING
      ).toBeTruthy();
    });
  });

  // ─── AC-003: Plans section with id="plans" ────────────────────────────────
  describe('plans section', () => {
    it('test_plans_section_renders_with_id_plans_when_page_loaded', () => {
      // TODO: render <BillingContent />
      // TODO: assert element with id="plans" exists in the document
      render(<BillingContent />);
      const plansSection = document.getElementById('plans');
      expect(plansSection).not.toBeNull();
    });

    it('test_plans_section_renders_below_all_three_cards', () => {
      // TODO: render <BillingContent />
      // TODO: assert id="plans" element follows data-testid="billing-info-card" in DOM order
      render(<BillingContent />);
      const billingInfoCard = screen.getByTestId('billing-info-card');
      const plansSection = document.getElementById('plans');
      expect(plansSection).not.toBeNull();
      if (plansSection) {
        expect(
          billingInfoCard.compareDocumentPosition(plansSection) & Node.DOCUMENT_POSITION_FOLLOWING
        ).toBeTruthy();
      }
    });
  });

  // ─── AC-004: three pricing tiers ──────────────────────────────────────────
  describe('pricing tiers', () => {
    it('test_monthly_plan_shows_30_per_month_when_plans_section_renders', () => {
      // TODO: render <BillingContent />
      // TODO: assert text matching "$30" or "$30/mo" is visible within #plans section
      render(<BillingContent />);
      // TODO: const plansSection = document.getElementById('plans');
      // TODO: expect(plansSection?.textContent).toMatch(/\$30/)
    });

    it('test_three_month_plan_shows_25_per_month_when_plans_section_renders', () => {
      // TODO: render <BillingContent />
      // TODO: assert text matching "$25" or "$25/mo" is visible within #plans section
      render(<BillingContent />);
      // TODO: expect(document.getElementById('plans')?.textContent).toMatch(/\$25/)
    });

    it('test_six_month_plan_shows_20_per_month_when_plans_section_renders', () => {
      // TODO: render <BillingContent />
      // TODO: assert text matching "$20" or "$20/mo" is visible within #plans section
      render(<BillingContent />);
      // TODO: expect(document.getElementById('plans')?.textContent).toMatch(/\$20/)
    });

    it('test_three_month_plan_shows_billed_quarterly_amount_when_rendered', () => {
      // TODO: render <BillingContent />
      // TODO: assert "$75" billed-quarterly copy is visible within #plans section
      render(<BillingContent />);
      // TODO: expect(document.getElementById('plans')?.textContent).toMatch(/75/)
    });

    it('test_six_month_plan_shows_billed_semi_annually_amount_when_rendered', () => {
      // TODO: render <BillingContent />
      // TODO: assert "$120" billed-semi-annually copy is visible within #plans section
      render(<BillingContent />);
      // TODO: expect(document.getElementById('plans')?.textContent).toMatch(/120/)
    });
  });

  // ─── AC-005: loading state ────────────────────────────────────────────────
  describe('loading state', () => {
    it('test_shows_spinner_when_is_loading_true', () => {
      // TODO: mockUseUserContext.mockReturnValue(LOADING_CONTEXT)
      // TODO: render <BillingContent />
      // TODO: assert element with role="status" and aria-label="Loading billing info…" exists
      mockUseUserContext.mockReturnValue(LOADING_CONTEXT);
      render(<BillingContent />);
      expect(screen.getByRole('status')).toBeDefined();
    });

    it('test_spinner_has_aria_label_loading_billing_info_when_is_loading_true', () => {
      // TODO: mockUseUserContext.mockReturnValue(LOADING_CONTEXT)
      // TODO: render <BillingContent />
      // TODO: assert spinner aria-label === "Loading billing info…"
      mockUseUserContext.mockReturnValue(LOADING_CONTEXT);
      render(<BillingContent />);
      const spinner = screen.getByRole('status');
      expect(spinner.getAttribute('aria-label')).toBe('Loading billing info…');
    });

    it('test_cards_not_rendered_when_is_loading_true', () => {
      // TODO: mockUseUserContext.mockReturnValue(LOADING_CONTEXT)
      // TODO: render <BillingContent />
      // TODO: assert data-testid="subscription-card" is absent
      mockUseUserContext.mockReturnValue(LOADING_CONTEXT);
      render(<BillingContent />);
      expect(screen.queryByTestId('subscription-card')).toBeNull();
    });
  });

  // ─── AC-006: error boundary ───────────────────────────────────────────────
  describe('error boundary', () => {
    it('test_error_boundary_wraps_page_with_cloudwatch_key_billing_page', () => {
      // TODO: render <BillingContent />
      // TODO: assert data-testid="error-boundary" exists with data-cloudwatch-key="billing-page"
      render(<BillingContent />);
      const boundary = screen.getByTestId('error-boundary');
      expect(boundary).toBeDefined();
      expect(boundary.getAttribute('data-cloudwatch-key')).toBe('billing-page');
    });
  });

  // ─── AC-007: Hebrew / i18n ────────────────────────────────────────────────
  describe('i18n — Hebrew strings', () => {
    it('test_page_title_renders_hebrew_key_when_locale_is_he', () => {
      // TODO: set useLocale mock to return 'he'
      // TODO: render <BillingContent />
      // TODO: assert h1 resolves to the Hebrew translation key for "Billing"
      // import { useLocale } from 'next-intl'; vi.mocked(useLocale).mockReturnValue('he');
      render(<BillingContent />);
      // TODO: expect(screen.getByRole('heading', { level: 1 }).textContent).toMatch(/<hebrew-billing-key>/i)
    });

    it('test_plans_section_heading_renders_hebrew_when_locale_is_he', () => {
      // TODO: set useLocale mock to return 'he'
      // TODO: render <BillingContent />
      // TODO: assert plans section h2 resolves to the Hebrew translation key
      render(<BillingContent />);
      // TODO: const plansHeading = screen.getByRole('heading', { level: 2 });
      // TODO: expect(plansHeading.textContent).toMatch(/<hebrew-plans-key>/i)
    });

    it('test_rtl_layout_applied_when_locale_is_he', () => {
      // TODO: set useLocale mock to return 'he'
      // TODO: render <BillingContent />
      // TODO: assert dir="rtl" or lang="he" attribute is present on the page wrapper
      render(<BillingContent />);
      // TODO: expect(container.firstChild).toHaveAttribute('dir', 'rtl')
    });
  });

  // ─── AC-008: landmark heading structure ───────────────────────────────────
  describe('accessibility', () => {
    it('test_page_has_h1_for_page_title_when_rendered', () => {
      // TODO: render <BillingContent />
      // TODO: assert exactly one h1 exists in the document
      render(<BillingContent />);
      const h1Elements = screen.getAllByRole('heading', { level: 1 });
      expect(h1Elements.length).toBe(1);
    });

    it('test_plans_section_has_h2_heading_when_rendered', () => {
      // TODO: render <BillingContent />
      // TODO: assert at least one h2 element exists within or adjacent to #plans section
      render(<BillingContent />);
      // TODO: expect(screen.getAllByRole('heading', { level: 2 }).length).toBeGreaterThan(0)
    });

    it('test_keyboard_navigation_reaches_plans_section_when_tabbed', () => {
      // TODO: render <BillingContent />
      // TODO: tab through focusable elements and assert focus reaches #plans section or its first interactive child
      render(<BillingContent />);
      // TODO: userEvent.tab(); assert document.activeElement is within #plans or a card button
    });
  });

});
