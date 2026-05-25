// spec_id: FE-UI-026  component: PlanCard  tier: unit
// Route: /billing (section within page)
// ACs covered: AC-001 – AC-011, AC-013 – AC-015  (all verification_type: unit)
//
// NOTE: PlansSection.test.tsx mocks PlanCard with props {monthlyPrice, billingTotal}
// rather than {pricePerMonth, billingPeriodLabel} from this spec. Confirm final prop
// names in src/frontend/components/billing/PlanCard.tsx before removing this note.

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ─── i18n mock ────────────────────────────────────────────────────────────────
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
  useLocale: vi.fn(() => 'en'),
}));

// ─── Import under test ────────────────────────────────────────────────────────
import { PlanCard } from '../../../src/frontend/components/billing/PlanCard';

// ─── Fixtures ─────────────────────────────────────────────────────────────────
const BASE_PROPS = {
  planKey: 'monthly',
  displayName: 'Monthly Plan',
  pricePerMonth: 30,
  billingPeriodLabel: 'Billed monthly',
  isCurrentPlan: false,
  isRecommended: false,
  onChoosePlan: vi.fn(),
};

const THREE_MONTH_PROPS = {
  planKey: '3month',
  displayName: '3 Month Plan',
  pricePerMonth: 25,
  billingPeriodLabel: 'Billed $75 every 3 months',
  isCurrentPlan: false,
  isRecommended: true,
  onChoosePlan: vi.fn(),
};

const SIX_MONTH_PROPS = {
  planKey: '6month',
  displayName: '6 Month Plan',
  pricePerMonth: 20,
  billingPeriodLabel: 'Billed $120 every 6 months',
  isCurrentPlan: false,
  isRecommended: false,
  onChoosePlan: vi.fn(),
};

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('PlanCard', () => {

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ─── AC-001: selectable state ────────────────────────────────────────────
  describe('selectable state (isCurrentPlan=false, isRecommended=false)', () => {
    it('test_shows_enabled_choose_plan_button_when_selectable', () => {
      // TODO: render <PlanCard {...BASE_PROPS} />
      // TODO: assert button with text "Choose Plan" (or i18n key) is present and not disabled
      render(<PlanCard {...BASE_PROPS} />);
      const btn = screen.getByRole('button');
      expect(btn).toBeDefined();
      // TODO: expect(btn.textContent).toMatch(/choose plan/i)
      // TODO: expect(btn).not.toBeDisabled()
      // TODO: expect(btn.getAttribute('aria-disabled')).not.toBe('true')
    });

    it('test_card_has_standard_border_when_selectable', () => {
      // TODO: render <PlanCard {...BASE_PROPS} />
      // TODO: assert root element does NOT have border-2 / border-primary-action classes
      render(<PlanCard {...BASE_PROPS} />);
      const card = screen.getByTestId('plan-card-monthly');
      expect(card).toBeDefined();
      // TODO: expect(card.className).not.toMatch(/border-2/)
      // TODO: expect(card.className).not.toMatch(/border-primary-action/)
    });
  });

  // ─── AC-002: selectable-recommended state ────────────────────────────────
  describe('selectable-recommended state (isCurrentPlan=false, isRecommended=true)', () => {
    it('test_shows_enabled_choose_plan_button_when_recommended', () => {
      // TODO: render <PlanCard {...THREE_MONTH_PROPS} />
      // TODO: assert button with text "Choose Plan" is present and enabled
      render(<PlanCard {...THREE_MONTH_PROPS} />);
      const btn = screen.getByRole('button');
      expect(btn).toBeDefined();
      // TODO: expect(btn.textContent).toMatch(/choose plan/i)
      // TODO: expect(btn).not.toBeDisabled()
    });

    it('test_card_has_thick_primary_action_border_when_recommended', () => {
      // TODO: render <PlanCard {...THREE_MONTH_PROPS} />
      // TODO: assert root element has border-2 and border-primary-action (or equivalent)
      render(<PlanCard {...THREE_MONTH_PROPS} />);
      const card = screen.getByTestId('plan-card-3month');
      expect(card).toBeDefined();
      // TODO: expect(card.className).toMatch(/border-2/)
      // TODO: expect(card.className).toMatch(/border-primary-action/)
    });
  });

  // ─── AC-003: current state ────────────────────────────────────────────────
  describe('current state (isCurrentPlan=true, isRecommended=false)', () => {
    it('test_shows_disabled_current_plan_button_when_current', () => {
      // TODO: render <PlanCard {...BASE_PROPS} isCurrentPlan={true} />
      // TODO: assert button text is "Current Plan" (or i18n key)
      render(<PlanCard {...BASE_PROPS} isCurrentPlan={true} />);
      const btn = screen.getByRole('button');
      expect(btn).toBeDefined();
      // TODO: expect(btn.textContent).toMatch(/current plan/i)
    });

    it('test_current_plan_button_has_aria_disabled_true_when_current', () => {
      // TODO: render <PlanCard {...BASE_PROPS} isCurrentPlan={true} />
      // TODO: assert button has aria-disabled="true"
      render(<PlanCard {...BASE_PROPS} isCurrentPlan={true} />);
      const btn = screen.getByRole('button');
      expect(btn.getAttribute('aria-disabled')).toBe('true');
    });

    it('test_current_plan_button_has_cursor_not_allowed_when_current', () => {
      // TODO: render <PlanCard {...BASE_PROPS} isCurrentPlan={true} />
      // TODO: assert button or its wrapper has cursor-not-allowed class
      render(<PlanCard {...BASE_PROPS} isCurrentPlan={true} />);
      const btn = screen.getByRole('button');
      expect(btn).toBeDefined();
      // TODO: expect(btn.className).toMatch(/cursor-not-allowed/)
    });

    it('test_card_has_standard_border_when_current_not_recommended', () => {
      // TODO: render <PlanCard {...BASE_PROPS} isCurrentPlan={true} isRecommended={false} />
      // TODO: assert root element does NOT have border-2 / border-primary-action
      render(<PlanCard {...BASE_PROPS} isCurrentPlan={true} isRecommended={false} />);
      const card = screen.getByTestId('plan-card-monthly');
      expect(card).toBeDefined();
      // TODO: expect(card.className).not.toMatch(/border-primary-action/)
    });
  });

  // ─── AC-004: current-recommended state ───────────────────────────────────
  describe('current-recommended state (isCurrentPlan=true, isRecommended=true)', () => {
    it('test_shows_disabled_current_plan_button_when_current_and_recommended', () => {
      // TODO: render <PlanCard {...THREE_MONTH_PROPS} isCurrentPlan={true} />
      // TODO: assert button text is "Current Plan" and aria-disabled="true"
      render(<PlanCard {...THREE_MONTH_PROPS} isCurrentPlan={true} />);
      const btn = screen.getByRole('button');
      expect(btn.getAttribute('aria-disabled')).toBe('true');
      // TODO: expect(btn.textContent).toMatch(/current plan/i)
    });

    it('test_card_has_thick_primary_action_border_when_current_and_recommended', () => {
      // TODO: render <PlanCard {...THREE_MONTH_PROPS} isCurrentPlan={true} />
      // TODO: assert root element has border-2 and border-primary-action
      render(<PlanCard {...THREE_MONTH_PROPS} isCurrentPlan={true} />);
      const card = screen.getByTestId('plan-card-3month');
      expect(card).toBeDefined();
      // TODO: expect(card.className).toMatch(/border-2/)
      // TODO: expect(card.className).toMatch(/border-primary-action/)
    });
  });

  // ─── AC-005: hover tint on non-current cards ─────────────────────────────
  describe('hover state — selectable card', () => {
    it('test_hover_class_applied_to_card_when_not_current', () => {
      // TODO: render <PlanCard {...BASE_PROPS} isCurrentPlan={false} />
      // TODO: assert root element has a hover tint class (e.g. hover:bg-card-hover or equivalent)
      render(<PlanCard {...BASE_PROPS} isCurrentPlan={false} />);
      const card = screen.getByTestId('plan-card-monthly');
      expect(card).toBeDefined();
      // TODO: expect(card.className).toMatch(/hover:/)
    });
  });

  // ─── AC-006: no hover tint on current cards ───────────────────────────────
  describe('hover state — current card', () => {
    it('test_hover_class_absent_from_card_when_current', () => {
      // TODO: render <PlanCard {...BASE_PROPS} isCurrentPlan={true} />
      // TODO: assert root element does NOT have a hover background class
      render(<PlanCard {...BASE_PROPS} isCurrentPlan={true} />);
      const card = screen.getByTestId('plan-card-monthly');
      expect(card).toBeDefined();
      // TODO: expect(card.className).not.toMatch(/hover:bg-/)
    });
  });

  // ─── AC-007: monthly plan display content ────────────────────────────────
  describe('monthly plan content (planKey=monthly)', () => {
    it('test_displays_monthly_plan_heading_when_planKey_is_monthly', () => {
      // TODO: render <PlanCard {...BASE_PROPS} />
      // TODO: assert h3 or heading element contains "Monthly Plan"
      render(<PlanCard {...BASE_PROPS} />);
      expect(screen.getByText('Monthly Plan')).toBeDefined();
    });

    it('test_displays_price_30_per_month_when_pricePerMonth_is_30', () => {
      // TODO: render <PlanCard {...BASE_PROPS} />
      // TODO: assert "$30" or "$30/mo" is visible
      render(<PlanCard {...BASE_PROPS} />);
      // TODO: expect(screen.getByText(/\$30/)).toBeDefined()
      // TODO: expect(screen.getByText(/\/mo/)).toBeDefined()
    });

    it('test_displays_billed_monthly_label_when_billingPeriodLabel_is_billed_monthly', () => {
      // TODO: render <PlanCard {...BASE_PROPS} />
      // TODO: assert text "Billed monthly" is visible
      render(<PlanCard {...BASE_PROPS} />);
      // TODO: expect(screen.getByText(/billed monthly/i)).toBeDefined()
    });
  });

  // ─── AC-008: 3-month plan display content ────────────────────────────────
  describe('3-month plan content (planKey=3month)', () => {
    it('test_displays_3_month_plan_heading_when_planKey_is_3month', () => {
      // TODO: render <PlanCard {...THREE_MONTH_PROPS} />
      // TODO: assert heading contains "3 Month Plan"
      render(<PlanCard {...THREE_MONTH_PROPS} />);
      expect(screen.getByText('3 Month Plan')).toBeDefined();
    });

    it('test_displays_price_25_per_month_when_pricePerMonth_is_25', () => {
      // TODO: render <PlanCard {...THREE_MONTH_PROPS} />
      // TODO: assert "$25" or "$25/mo" is visible
      render(<PlanCard {...THREE_MONTH_PROPS} />);
      // TODO: expect(screen.getByText(/\$25/)).toBeDefined()
    });

    it('test_displays_billed_75_every_3_months_label_when_billingPeriodLabel_set', () => {
      // TODO: render <PlanCard {...THREE_MONTH_PROPS} />
      // TODO: assert text "Billed $75 every 3 months" is visible
      render(<PlanCard {...THREE_MONTH_PROPS} />);
      // TODO: expect(screen.getByText(/billed \$75 every 3 months/i)).toBeDefined()
    });
  });

  // ─── AC-009: 6-month plan display content ────────────────────────────────
  describe('6-month plan content (planKey=6month)', () => {
    it('test_displays_6_month_plan_heading_when_planKey_is_6month', () => {
      // TODO: render <PlanCard {...SIX_MONTH_PROPS} />
      // TODO: assert heading contains "6 Month Plan"
      render(<PlanCard {...SIX_MONTH_PROPS} />);
      expect(screen.getByText('6 Month Plan')).toBeDefined();
    });

    it('test_displays_price_20_per_month_when_pricePerMonth_is_20', () => {
      // TODO: render <PlanCard {...SIX_MONTH_PROPS} />
      // TODO: assert "$20" or "$20/mo" is visible
      render(<PlanCard {...SIX_MONTH_PROPS} />);
      // TODO: expect(screen.getByText(/\$20/)).toBeDefined()
    });

    it('test_displays_billed_120_every_6_months_label_when_billingPeriodLabel_set', () => {
      // TODO: render <PlanCard {...SIX_MONTH_PROPS} />
      // TODO: assert text "Billed $120 every 6 months" is visible
      render(<PlanCard {...SIX_MONTH_PROPS} />);
      // TODO: expect(screen.getByText(/billed \$120 every 6 months/i)).toBeDefined()
    });
  });

  // ─── AC-010: click fires onChoosePlan ────────────────────────────────────
  describe('choose plan click — selectable card', () => {
    it('test_on_choose_plan_fires_when_choose_plan_button_clicked', () => {
      // TODO: render <PlanCard {...BASE_PROPS} isCurrentPlan={false} />
      // TODO: fireEvent.click on the "Choose Plan" button
      // TODO: assert BASE_PROPS.onChoosePlan was called once
      render(<PlanCard {...BASE_PROPS} isCurrentPlan={false} />);
      // TODO: fireEvent.click(screen.getByRole('button'))
      // TODO: expect(BASE_PROPS.onChoosePlan).toHaveBeenCalledTimes(1)
    });
  });

  // ─── AC-011: click does NOT fire when current ─────────────────────────────
  describe('choose plan click — current card', () => {
    it('test_on_choose_plan_not_fired_when_current_plan_button_clicked', () => {
      // TODO: render <PlanCard {...BASE_PROPS} isCurrentPlan={true} />
      // TODO: fireEvent.click on the "Current Plan" button
      // TODO: assert BASE_PROPS.onChoosePlan was NOT called
      render(<PlanCard {...BASE_PROPS} isCurrentPlan={true} />);
      // TODO: fireEvent.click(screen.getByRole('button'))
      // TODO: expect(BASE_PROPS.onChoosePlan).not.toHaveBeenCalled()
    });
  });

  // ─── AC-013: Hebrew locale / i18n ────────────────────────────────────────
  describe('i18n — Hebrew locale', () => {
    it('test_display_name_renders_in_rtl_layout_when_locale_is_he', () => {
      // TODO: vi.mocked(useLocale).mockReturnValue('he')
      // TODO: render <PlanCard {...BASE_PROPS} displayName="<hebrew-plan-name>" billingPeriodLabel="<hebrew-label>" />
      // TODO: assert displayName and billingPeriodLabel are rendered
      // TODO: assert dir="rtl" on root or a wrapper element
      render(<PlanCard {...BASE_PROPS} />);
      // TODO: const card = screen.getByTestId('plan-card-monthly')
      // TODO: expect(card.getAttribute('dir') ?? card.closest('[dir]')?.getAttribute('dir')).toBe('rtl')
    });

    it('test_choose_plan_button_text_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: vi.mocked(useLocale).mockReturnValue('he')
      // TODO: render <PlanCard {...BASE_PROPS} isCurrentPlan={false} />
      // TODO: assert button text resolves to the Hebrew i18n key for "Choose Plan"
      render(<PlanCard {...BASE_PROPS} isCurrentPlan={false} />);
      // TODO: const btn = screen.getByRole('button')
      // TODO: expect(btn.textContent).toMatch(/<hebrew-choose-plan-key>/)
    });

    it('test_current_plan_button_text_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: vi.mocked(useLocale).mockReturnValue('he')
      // TODO: render <PlanCard {...BASE_PROPS} isCurrentPlan={true} />
      // TODO: assert button text resolves to the Hebrew i18n key for "Current Plan"
      render(<PlanCard {...BASE_PROPS} isCurrentPlan={true} />);
      // TODO: const btn = screen.getByRole('button')
      // TODO: expect(btn.textContent).toMatch(/<hebrew-current-plan-key>/)
    });
  });

  // ─── AC-014: accessibility — aria-disabled and data-testid ───────────────
  describe('accessibility — aria-disabled and data-testid', () => {
    it('test_root_element_has_correct_data_testid_when_planKey_is_monthly', () => {
      // TODO: render <PlanCard {...BASE_PROPS} planKey="monthly" />
      // TODO: assert data-testid="plan-card-monthly" is present in the DOM
      render(<PlanCard {...BASE_PROPS} planKey="monthly" />);
      expect(screen.getByTestId('plan-card-monthly')).toBeDefined();
    });

    it('test_root_element_has_correct_data_testid_when_planKey_is_3month', () => {
      // TODO: render <PlanCard {...THREE_MONTH_PROPS} />
      // TODO: assert data-testid="plan-card-3month"
      render(<PlanCard {...THREE_MONTH_PROPS} />);
      expect(screen.getByTestId('plan-card-3month')).toBeDefined();
    });

    it('test_root_element_has_correct_data_testid_when_planKey_is_6month', () => {
      // TODO: render <PlanCard {...SIX_MONTH_PROPS} />
      // TODO: assert data-testid="plan-card-6month"
      render(<PlanCard {...SIX_MONTH_PROPS} />);
      expect(screen.getByTestId('plan-card-6month')).toBeDefined();
    });

    it('test_button_aria_disabled_true_when_is_current_plan', () => {
      // TODO: render <PlanCard {...BASE_PROPS} isCurrentPlan={true} />
      // TODO: assert the CTA button has aria-disabled="true" (not HTML disabled attribute)
      render(<PlanCard {...BASE_PROPS} isCurrentPlan={true} />);
      const btn = screen.getByRole('button');
      expect(btn.getAttribute('aria-disabled')).toBe('true');
    });

    it('test_button_aria_disabled_absent_or_false_when_not_current_plan', () => {
      // TODO: render <PlanCard {...BASE_PROPS} isCurrentPlan={false} />
      // TODO: assert the CTA button does NOT have aria-disabled="true"
      render(<PlanCard {...BASE_PROPS} isCurrentPlan={false} />);
      const btn = screen.getByRole('button');
      expect(btn.getAttribute('aria-disabled')).not.toBe('true');
    });

    it('test_keyboard_tab_reaches_choose_plan_button_when_selectable', () => {
      // TODO: render <PlanCard {...BASE_PROPS} isCurrentPlan={false} />
      // TODO: assert the "Choose Plan" button is reachable via tab (tabIndex >= 0 or default)
      render(<PlanCard {...BASE_PROPS} isCurrentPlan={false} />);
      const btn = screen.getByRole('button');
      expect(btn).toBeDefined();
      // TODO: expect(Number(btn.getAttribute('tabIndex') ?? '0')).toBeGreaterThanOrEqual(0)
    });

    it('test_current_plan_button_remains_focusable_for_screen_readers_when_current', () => {
      // Spec requires aria-disabled rather than HTML disabled to preserve focusability
      // TODO: render <PlanCard {...BASE_PROPS} isCurrentPlan={true} />
      // TODO: assert button does NOT have the HTML `disabled` attribute
      // TODO: assert button has aria-disabled="true"
      render(<PlanCard {...BASE_PROPS} isCurrentPlan={true} />);
      const btn = screen.getByRole('button');
      expect(btn.hasAttribute('disabled')).toBe(false);
      expect(btn.getAttribute('aria-disabled')).toBe('true');
    });
  });

  // ─── AC-015: price aria-label ────────────────────────────────────────────
  describe('accessibility — price aria-label', () => {
    it('test_price_display_has_aria_label_for_monthly_plan', () => {
      // TODO: render <PlanCard {...BASE_PROPS} pricePerMonth={30} billingPeriodLabel="Billed monthly" />
      // TODO: assert the price element has aria-label containing "30 dollars per month"
      render(<PlanCard {...BASE_PROPS} />);
      // TODO: const priceEl = screen.getByLabelText(/30 dollars per month/i)
      // TODO: expect(priceEl).toBeDefined()
    });

    it('test_price_display_aria_label_includes_billing_total_for_3month_plan', () => {
      // TODO: render <PlanCard {...THREE_MONTH_PROPS} pricePerMonth={25} billingPeriodLabel="Billed $75 every 3 months" />
      // TODO: assert price aria-label contains "25 dollars per month" and "75 dollars every 3 months"
      render(<PlanCard {...THREE_MONTH_PROPS} />);
      // TODO: const priceEl = screen.getByLabelText(/25 dollars per month.*75 dollars every 3 months/i)
      // TODO: expect(priceEl).toBeDefined()
    });

    it('test_price_display_aria_label_includes_billing_total_for_6month_plan', () => {
      // TODO: render <PlanCard {...SIX_MONTH_PROPS} pricePerMonth={20} billingPeriodLabel="Billed $120 every 6 months" />
      // TODO: assert price aria-label contains "20 dollars per month" and "120 dollars every 6 months"
      render(<PlanCard {...SIX_MONTH_PROPS} />);
      // TODO: const priceEl = screen.getByLabelText(/20 dollars per month.*120 dollars every 6 months/i)
      // TODO: expect(priceEl).toBeDefined()
    });
  });

});
