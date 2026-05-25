// spec_id: FE-UI-022  component: SubscriptionCard  tier: unit
// Route: /billing
// ACs covered: AC-001 – AC-014  (all verification_type: unit)

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ─── Hoisted hook mock ────────────────────────────────────────────────────────
const mockUseSubscription = vi.hoisted(() => vi.fn());

vi.mock('../../../src/frontend/hooks/useSubscription', () => ({
  useSubscription: mockUseSubscription,
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

// ─── Import under test ────────────────────────────────────────────────────────
import { SubscriptionCard } from '../../../src/frontend/components/billing/SubscriptionCard';

// ─── Fixtures ─────────────────────────────────────────────────────────────────
const ACTIVE_SUBSCRIPTION = {
  plan_type: 'Pro Monthly',
  status: 'active',
  cancel_at_period_end: false,
  current_period_end: '2026-06-24T00:00:00Z',
  next_charge_amount: 3000, // cents
};

const CANCELLING_SUBSCRIPTION = {
  ...ACTIVE_SUBSCRIPTION,
  cancel_at_period_end: true,
};

const TRIALING_SUBSCRIPTION = {
  ...ACTIVE_SUBSCRIPTION,
  status: 'trialing',
  cancel_at_period_end: false,
};

const PAST_DUE_SUBSCRIPTION = {
  ...ACTIVE_SUBSCRIPTION,
  status: 'past_due',
  cancel_at_period_end: false,
};

const EXPIRED_SUBSCRIPTION = {
  plan_type: null,
  status: 'canceled',
  cancel_at_period_end: false,
  current_period_end: null,
  next_charge_amount: null,
};

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('SubscriptionCard', () => {

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSubscription.mockReturnValue({
      subscription: ACTIVE_SUBSCRIPTION,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
  });

  // ─── AC-001: active state → green "Active" badge ──────────────────────────
  describe('active state', () => {
    it('test_renders_active_badge_when_status_is_active', () => {
      // TODO: render <SubscriptionCard /> with active subscription fixture
      // TODO: assert element with text "Active" is present in the document
    });

    it('test_active_badge_has_green_styling_when_status_is_active', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert badge element has a class or data-attribute indicating green/success colour
    });
  });

  // ─── AC-002: cancelling state → yellow "Cancelling" badge + "Active until" text ──
  describe('cancelling state', () => {
    beforeEach(() => {
      mockUseSubscription.mockReturnValue({
        subscription: CANCELLING_SUBSCRIPTION,
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
      });
    });

    it('test_renders_cancelling_badge_when_cancel_at_period_end_is_true', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert element with text "Cancelling" is present
    });

    it('test_cancelling_badge_has_yellow_styling_when_cancelling', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert badge element has a class or data-attribute indicating yellow/warning colour
    });

    it('test_shows_active_until_formatted_date_when_cancelling', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert text matching "Active until" followed by a date string is visible
    });
  });

  // ─── AC-003: trial state → blue "Trial" badge + days remaining ────────────
  describe('trial state', () => {
    beforeEach(() => {
      mockUseSubscription.mockReturnValue({
        subscription: TRIALING_SUBSCRIPTION,
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
      });
    });

    it('test_renders_trial_badge_when_status_is_trialing', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert element with text "Trial" is present
    });

    it('test_trial_badge_has_blue_styling_when_trialing', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert badge element has a class or data-attribute indicating blue/info colour
    });

    it('test_shows_trial_days_remaining_when_status_is_trialing', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert text referencing days remaining (e.g. "X days remaining" or "X days left") is visible
    });
  });

  // ─── AC-004: past-due state → red "Past Due" badge + payment prompt ───────
  describe('past-due state', () => {
    beforeEach(() => {
      mockUseSubscription.mockReturnValue({
        subscription: PAST_DUE_SUBSCRIPTION,
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
      });
    });

    it('test_renders_past_due_badge_when_status_is_past_due', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert element with text "Past Due" is present
    });

    it('test_past_due_badge_has_red_styling_when_past_due', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert badge element has a class or data-attribute indicating red/danger colour
    });

    it('test_shows_payment_update_prompt_when_status_is_past_due', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert a payment-related prompt or notice is visible (e.g. "update payment" or "payment overdue")
    });
  });

  // ─── AC-005: plan-type pill ────────────────────────────────────────────────
  describe('plan-type pill', () => {
    it('test_renders_plan_type_pill_with_plan_type_value_when_active', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert element with text "Pro Monthly" (matching ACTIVE_SUBSCRIPTION.plan_type) is visible
    });

    it('test_plan_type_pill_reflects_three_month_plan_when_plan_type_is_pro_3_month', () => {
      // TODO: mockUseSubscription.mockReturnValue({ subscription: { ...ACTIVE_SUBSCRIPTION, plan_type: 'Pro 3-Month' }, ... })
      // TODO: render <SubscriptionCard />
      // TODO: assert text "Pro 3-Month" is visible
    });
  });

  // ─── AC-006: renewal date ─────────────────────────────────────────────────
  describe('renewal date', () => {
    it('test_renders_renewal_date_from_current_period_end_when_present', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert a formatted date derived from ACTIVE_SUBSCRIPTION.current_period_end is visible
      // TODO: assert date is in localized format (e.g. "Jun 24, 2026" for en locale)
    });

    it('test_renewal_date_absent_when_current_period_end_is_null', () => {
      // TODO: mockUseSubscription with subscription.current_period_end = null
      // TODO: render <SubscriptionCard />
      // TODO: assert no renewal date text is rendered (or a fallback dash/placeholder is shown)
    });
  });

  // ─── AC-007: next charge amount ───────────────────────────────────────────
  describe('next charge amount', () => {
    it('test_renders_formatted_currency_from_next_charge_amount_when_present', () => {
      // TODO: render <SubscriptionCard /> with ACTIVE_SUBSCRIPTION (next_charge_amount: 3000)
      // TODO: assert text "$30.00" (or locale-equivalent) is visible
    });

    it('test_next_charge_absent_when_next_charge_amount_is_null', () => {
      // TODO: mockUseSubscription with subscription.next_charge_amount = null
      // TODO: render <SubscriptionCard />
      // TODO: assert next charge text is absent or a suitable fallback is shown
    });
  });

  // ─── AC-008: "View Plans" CTA scrolls to #plans ───────────────────────────
  describe('"View Plans" CTA', () => {
    it('test_view_plans_cta_is_visible_when_status_is_active', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert button or link with text "View Plans" is visible
    });

    it('test_clicking_view_plans_scrolls_to_plans_anchor_when_active', () => {
      // TODO: spy on window.scrollIntoView or window.location.hash
      // TODO: render <SubscriptionCard />
      // TODO: fireEvent.click the "View Plans" button
      // TODO: assert scroll target or href "#plans" was triggered
    });
  });

  // ─── AC-009: cancelling state → "Resubscribe" CTA ────────────────────────
  describe('"Resubscribe" CTA in cancelling state', () => {
    beforeEach(() => {
      mockUseSubscription.mockReturnValue({
        subscription: CANCELLING_SUBSCRIPTION,
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
      });
    });

    it('test_cta_text_is_resubscribe_when_cancelling', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert button/link with text "Resubscribe" is visible
    });

    it('test_view_plans_cta_absent_when_cancelling', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert "View Plans" button is NOT present when cancel_at_period_end=true
    });
  });

  // ─── AC-010: loading state → skeleton shimmer ─────────────────────────────
  describe('loading state', () => {
    beforeEach(() => {
      mockUseSubscription.mockReturnValue({
        subscription: null,
        isLoading: true,
        isError: false,
        refetch: vi.fn(),
      });
    });

    it('test_shows_skeleton_placeholder_when_data_is_loading', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert a skeleton or shimmer element is present (data-testid="skeleton" or role="status" / aria-busy)
    });

    it('test_subscription_content_absent_when_loading', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert "Active", "View Plans", and plan-type pill text are NOT rendered while loading
    });
  });

  // ─── AC-011: error state → inline error + "Retry" button ─────────────────
  describe('error state', () => {
    beforeEach(() => {
      mockUseSubscription.mockReturnValue({
        subscription: null,
        isLoading: false,
        isError: true,
        refetch: vi.fn(),
      });
    });

    it('test_shows_inline_error_message_when_fetch_fails', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert an error message element is visible inside the card (not a full-page error)
    });

    it('test_shows_retry_button_when_error_state_active', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert button with text "Retry" is visible
    });
  });

  // ─── AC-012: "Retry" button triggers refetch ──────────────────────────────
  describe('"Retry" button', () => {
    it('test_clicking_retry_calls_refetch_when_error_state_active', () => {
      const mockRefetch = vi.fn();
      mockUseSubscription.mockReturnValue({
        subscription: null,
        isLoading: false,
        isError: true,
        refetch: mockRefetch,
      });
      // TODO: render <SubscriptionCard />
      // TODO: fireEvent.click the "Retry" button
      // TODO: expect(mockRefetch).toHaveBeenCalledTimes(1)
    });
  });

  // ─── AC-013: Hebrew locale → all text Hebrew + RTL layout ────────────────
  describe('i18n — Hebrew strings', () => {
    it('test_badge_text_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: vi.mocked(useLocale from next-intl).mockReturnValue('he')
      // TODO: render <SubscriptionCard />
      // TODO: assert badge text matches Hebrew translation key for "Active" (not the English word)
    });

    it('test_plan_type_pill_renders_hebrew_when_locale_is_he', () => {
      // TODO: vi.mocked(useLocale).mockReturnValue('he')
      // TODO: render <SubscriptionCard />
      // TODO: assert plan-type pill text is a Hebrew string
    });

    it('test_cta_text_renders_hebrew_when_locale_is_he', () => {
      // TODO: vi.mocked(useLocale).mockReturnValue('he')
      // TODO: render <SubscriptionCard />
      // TODO: assert CTA button text is a Hebrew string
    });

    it('test_rtl_layout_applied_when_locale_is_he', () => {
      // TODO: vi.mocked(useLocale).mockReturnValue('he')
      // TODO: render <SubscriptionCard /> and capture container
      // TODO: assert dir="rtl" attribute is present on the card wrapper element
    });
  });

  // ─── AC-014: accessibility — status badge role/aria-label ─────────────────
  describe('accessibility', () => {
    it('test_status_badge_has_role_status_when_rendered', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert screen.getByRole('status') is present (the badge element)
    });

    it('test_status_badge_has_aria_label_describing_subscription_state_when_active', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert role="status" element has aria-label that describes the state
      // TODO: e.g. aria-label="Subscription status: Active"
    });

    it('test_status_badge_aria_label_reflects_state_when_cancelling', () => {
      mockUseSubscription.mockReturnValue({
        subscription: CANCELLING_SUBSCRIPTION,
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
      });
      // TODO: render <SubscriptionCard />
      // TODO: assert aria-label on role="status" badge references "Cancelling"
    });

    it('test_keyboard_navigation_reaches_cta_button_when_focused', () => {
      // TODO: render <SubscriptionCard />
      // TODO: tab to the CTA button and assert document.activeElement is the expected button
    });
  });

  // ─── expired / no-subscription state ──────────────────────────────────────
  describe('expired / no subscription state', () => {
    beforeEach(() => {
      mockUseSubscription.mockReturnValue({
        subscription: EXPIRED_SUBSCRIPTION,
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
      });
    });

    it('test_shows_no_active_subscription_text_when_status_is_canceled', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert text "No active subscription" (or i18n key equivalent) is visible
    });

    it('test_cta_text_is_choose_a_plan_when_no_subscription', () => {
      // TODO: render <SubscriptionCard />
      // TODO: assert button/link with text "Choose a Plan" is visible
    });
  });

});
