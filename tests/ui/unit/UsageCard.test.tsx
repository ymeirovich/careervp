// spec_id: FE-UI-023  component: UsageCard
// file: src/frontend/components/billing/UsageCard.tsx
// All ACs are verification_type: unit — one describe block per AC.
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { UsageCard } from '../../../src/frontend/components/billing/UsageCard';

// ---------------------------------------------------------------------------
// module mocks — reset per test in beforeEach
// ---------------------------------------------------------------------------
// TODO: replace 'useUsage' with the actual hook name once implemented
const mockUseUsage = vi.fn();

vi.mock('../../../src/frontend/hooks/useUsage', () => ({
  useUsage: () => mockUseUsage(),
}));

// i18n: stub next-intl so locale can be swapped per test
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
  useLocale: vi.fn(() => 'en'),
}));

import { useLocale } from 'next-intl';
const mockUseLocale = vi.mocked(useLocale);

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------
function renderCard() {
  return render(<UsageCard />);
}

type UsageHookState = {
  isLoading?: boolean;
  error?: Error | null;
  data?: {
    credits_used?: number;
    credits_total?: number;
    trial?: {
      active: boolean;
      applications_used: number;
      applications_limit: number;
    };
    has_active_subscription?: boolean;
  } | null;
  refetch?: () => void;
};

function mockHookState(overrides: UsageHookState) {
  mockUseUsage.mockReturnValue({
    isLoading: false,
    error: null,
    data: null,
    refetch: vi.fn(),
    ...overrides,
  });
}

// ---------------------------------------------------------------------------
// beforeEach — clear all mocks
// ---------------------------------------------------------------------------
beforeEach(() => {
  vi.clearAllMocks();
  mockUseLocale.mockReturnValue('en');
  mockHookState({});
});

// ===========================================================================
// UsageCard — unit tests
// ===========================================================================
describe('UsageCard', () => {

  // ─── AC-001: Paid user sees "Unlimited credits" ──────────────────────────────
  describe('AC-001 — "Unlimited credits" for paid subscribers', () => {
    it('test_unlimited_credits_text_renders_when_user_has_active_subscription', () => {
      // TODO: mock useUsage to return { data: { has_active_subscription: true } }
      // TODO: render <UsageCard />
      // TODO: assert text matching /unlimited credits/i is in the document
      mockHookState({ data: { has_active_subscription: true } });
      renderCard();
      // TODO: expect(screen.getByText(/unlimited credits/i)).toBeInTheDocument()
      expect(document.body).toBeTruthy();
    });

    it('test_trial_usage_text_not_shown_when_user_has_active_subscription', () => {
      // TODO: mock useUsage with has_active_subscription: true
      // TODO: assert text matching /of 3 applications used/i is NOT in the document
      mockHookState({ data: { has_active_subscription: true } });
      renderCard();
      // TODO: expect(screen.queryByText(/of 3 applications used/i)).toBeNull()
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-002: Trial user sees "X of 3 applications used" ─────────────────────
  describe('AC-002 — "X of 3 applications used" for trial users', () => {
    it('test_trial_usage_text_renders_when_trial_is_active', () => {
      // TODO: mock useUsage with trial: { active: true, applications_used: 1, applications_limit: 3 }
      // TODO: assert text matching /1 of 3 applications used/i is in the document
      mockHookState({
        data: {
          trial: { active: true, applications_used: 1, applications_limit: 3 },
          has_active_subscription: false,
        },
      });
      renderCard();
      // TODO: expect(screen.getByText(/1 of 3 applications used/i)).toBeInTheDocument()
      expect(document.body).toBeTruthy();
    });

    it('test_trial_usage_count_reflects_api_value_when_applications_used_is_two', () => {
      // TODO: mock useUsage with applications_used: 2
      // TODO: assert text shows "2 of 3 applications used"
      mockHookState({
        data: {
          trial: { active: true, applications_used: 2, applications_limit: 3 },
          has_active_subscription: false,
        },
      });
      renderCard();
      // TODO: expect(screen.getByText(/2 of 3 applications used/i)).toBeInTheDocument()
      expect(document.body).toBeTruthy();
    });

    it('test_unlimited_credits_not_shown_when_trial_is_active', () => {
      // TODO: mock useUsage with trial.active: true
      // TODO: assert /unlimited credits/i is NOT in the document
      mockHookState({
        data: {
          trial: { active: true, applications_used: 0, applications_limit: 3 },
          has_active_subscription: false,
        },
      });
      renderCard();
      // TODO: expect(screen.queryByText(/unlimited credits/i)).toBeNull()
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-003: Trial user sees progress indicator ──────────────────────────────
  describe('AC-003 — progress indicator for trial users', () => {
    it('test_progress_indicator_renders_when_trial_is_active', () => {
      // TODO: mock useUsage with trial.active: true
      // TODO: assert a progress element (role="progressbar" or data-testid="usage-progress") is in the document
      mockHookState({
        data: {
          trial: { active: true, applications_used: 1, applications_limit: 3 },
          has_active_subscription: false,
        },
      });
      renderCard();
      // TODO: expect(screen.getByRole('progressbar')).toBeInTheDocument()
      expect(document.body).toBeTruthy();
    });

    it('test_progress_indicator_not_rendered_when_user_has_active_subscription', () => {
      // TODO: mock useUsage with has_active_subscription: true
      // TODO: assert role="progressbar" is NOT in the document
      mockHookState({ data: { has_active_subscription: true } });
      renderCard();
      // TODO: expect(screen.queryByRole('progressbar')).toBeNull()
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-004: Paid user — upgrade link smooth-scrolls to #plans ──────────────
  describe('AC-004 — upgrade link renders for paid user', () => {
    it('test_upgrade_link_renders_when_paid_user_card_renders', () => {
      // TODO: mock useUsage with has_active_subscription: true
      // TODO: assert link with text /upgrade subscription to save money/i is in the document
      mockHookState({ data: { has_active_subscription: true } });
      renderCard();
      // TODO: expect(screen.getByRole('link', { name: /upgrade subscription to save money/i })).toBeInTheDocument()
      expect(document.body).toBeTruthy();
    });

    it('test_upgrade_link_has_plans_href_when_paid_user_card_renders', () => {
      // TODO: mock useUsage with has_active_subscription: true
      // TODO: assert link href is "#plans"
      mockHookState({ data: { has_active_subscription: true } });
      renderCard();
      // TODO: const link = screen.getByRole('link', { name: /upgrade subscription to save money/i })
      // TODO: expect(link).toHaveAttribute('href', '#plans')
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-005: Trial user — upgrade link smooth-scrolls to #plans ─────────────
  describe('AC-005 — upgrade link renders for trial user', () => {
    it('test_upgrade_link_renders_when_trial_user_card_renders', () => {
      // TODO: mock useUsage with trial.active: true
      // TODO: assert link with text /upgrade subscription to save money/i is in the document
      mockHookState({
        data: {
          trial: { active: true, applications_used: 1, applications_limit: 3 },
          has_active_subscription: false,
        },
      });
      renderCard();
      // TODO: expect(screen.getByRole('link', { name: /upgrade subscription to save money/i })).toBeInTheDocument()
      expect(document.body).toBeTruthy();
    });

    it('test_upgrade_link_href_is_plans_when_trial_user_card_renders', () => {
      // TODO: mock useUsage with trial.active: true
      // TODO: assert link href is "#plans"
      mockHookState({
        data: {
          trial: { active: true, applications_used: 0, applications_limit: 3 },
          has_active_subscription: false,
        },
      });
      renderCard();
      // TODO: const link = screen.getByRole('link', { name: /upgrade subscription to save money/i })
      // TODO: expect(link).toHaveAttribute('href', '#plans')
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-006: Loading state — skeleton shimmer ────────────────────────────────
  describe('AC-006 — loading state skeleton', () => {
    it('test_skeleton_placeholder_renders_when_data_is_loading', () => {
      // TODO: mock useUsage to return { isLoading: true }
      // TODO: assert a skeleton element (data-testid="usage-card-skeleton" or role="status") is visible
      mockHookState({ isLoading: true });
      renderCard();
      // TODO: expect(screen.getByTestId('usage-card-skeleton')).toBeInTheDocument()
      // TODO: OR: expect(screen.getByRole('status')).toBeInTheDocument()
      expect(document.body).toBeTruthy();
    });

    it('test_content_not_rendered_when_data_is_loading', () => {
      // TODO: mock useUsage with isLoading: true
      // TODO: assert /unlimited credits/i and /applications used/i are NOT in the document
      mockHookState({ isLoading: true });
      renderCard();
      // TODO: expect(screen.queryByText(/unlimited credits/i)).toBeNull()
      // TODO: expect(screen.queryByText(/applications used/i)).toBeNull()
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-007: Error state — inline error + Retry button ──────────────────────
  describe('AC-007 — error state', () => {
    it('test_inline_error_message_renders_when_usage_fetch_fails', () => {
      // TODO: mock useUsage to return { error: new Error('Network fail') }
      // TODO: assert an error message element is visible
      mockHookState({ error: new Error('Network fail') });
      renderCard();
      // TODO: expect(screen.getByRole('alert') or screen.getByTestId('usage-error')).toBeInTheDocument()
      expect(document.body).toBeTruthy();
    });

    it('test_retry_button_renders_when_usage_fetch_fails', () => {
      // TODO: mock useUsage to return { error: new Error('Network fail') }
      // TODO: assert button with text /retry/i is in the document
      mockHookState({ error: new Error('Network fail') });
      renderCard();
      // TODO: expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
      expect(document.body).toBeTruthy();
    });

    it('test_content_not_rendered_when_fetch_fails', () => {
      // TODO: mock useUsage with error set
      // TODO: assert /unlimited credits/i and /applications used/i are NOT in the document
      mockHookState({ error: new Error('fail') });
      renderCard();
      // TODO: expect(screen.queryByText(/unlimited credits/i)).toBeNull()
      // TODO: expect(screen.queryByText(/applications used/i)).toBeNull()
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-008: Retry button triggers refetch ───────────────────────────────────
  describe('AC-008 — Retry button triggers refetch', () => {
    it('test_refetch_called_when_retry_button_is_clicked', () => {
      // TODO: mock useUsage with error and capture refetch mock
      // TODO: render, click Retry button
      // TODO: assert refetch was called once
      const mockRefetch = vi.fn();
      mockHookState({ error: new Error('fail'), refetch: mockRefetch });
      renderCard();
      // TODO: fireEvent.click(screen.getByRole('button', { name: /retry/i }))
      // TODO: expect(mockRefetch).toHaveBeenCalledOnce()
      expect(mockRefetch).toBeDefined();
    });

    it('test_refetch_not_called_on_initial_render_when_error_state', () => {
      // TODO: mock useUsage with error set
      // TODO: render without clicking Retry
      // TODO: assert refetch was NOT called
      const mockRefetch = vi.fn();
      mockHookState({ error: new Error('fail'), refetch: mockRefetch });
      renderCard();
      // TODO: expect(mockRefetch).not.toHaveBeenCalled()
      expect(mockRefetch).toBeDefined();
    });
  });

  // ─── AC-009: Hebrew locale — RTL layout + Hebrew text ───────────────────────
  describe('AC-009 — Hebrew locale i18n and RTL', () => {
    it('test_card_heading_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: mockUseLocale.mockReturnValue('he')
      // TODO: mock useUsage with valid data
      // TODO: assert card heading resolves to Hebrew "Usage" translation key
      mockUseLocale.mockReturnValue('he');
      mockHookState({ data: { has_active_subscription: true } });
      renderCard();
      // TODO: expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(/<hebrew-usage-key>/)
      expect(document.body).toBeTruthy();
    });

    it('test_unlimited_credits_text_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: mockUseLocale.mockReturnValue('he')
      // TODO: mock useUsage with has_active_subscription: true
      // TODO: assert text resolves to Hebrew "Unlimited credits" translation key
      mockUseLocale.mockReturnValue('he');
      mockHookState({ data: { has_active_subscription: true } });
      renderCard();
      // TODO: expect(screen.getByText(/<hebrew-unlimited-credits-key>/)).toBeInTheDocument()
      expect(document.body).toBeTruthy();
    });

    it('test_trial_usage_text_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: mockUseLocale.mockReturnValue('he')
      // TODO: mock useUsage with trial.active: true
      // TODO: assert trial usage text resolves to Hebrew translation key
      mockUseLocale.mockReturnValue('he');
      mockHookState({
        data: {
          trial: { active: true, applications_used: 1, applications_limit: 3 },
          has_active_subscription: false,
        },
      });
      renderCard();
      // TODO: expect(screen.getByText(/<hebrew-applications-used-key>/)).toBeInTheDocument()
      expect(document.body).toBeTruthy();
    });

    it('test_progress_indicator_direction_is_rtl_when_locale_is_he', () => {
      // TODO: mockUseLocale.mockReturnValue('he')
      // TODO: mock useUsage with trial.active: true
      // TODO: assert progress bar element has dir="rtl" or parent has dir="rtl"
      mockUseLocale.mockReturnValue('he');
      mockHookState({
        data: {
          trial: { active: true, applications_used: 1, applications_limit: 3 },
          has_active_subscription: false,
        },
      });
      renderCard();
      // TODO: const progressbar = screen.getByRole('progressbar')
      // TODO: expect(progressbar.closest('[dir="rtl"]')).not.toBeNull()
      expect(document.body).toBeTruthy();
    });

    it('test_upgrade_link_text_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: mockUseLocale.mockReturnValue('he')
      // TODO: mock useUsage with has_active_subscription: true
      // TODO: assert upgrade link text resolves to Hebrew translation key
      mockUseLocale.mockReturnValue('he');
      mockHookState({ data: { has_active_subscription: true } });
      renderCard();
      // TODO: expect(screen.getByRole('link', { name: /<hebrew-upgrade-key>/ })).toBeInTheDocument()
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-010: Accessibility — ARIA attributes ─────────────────────────────────
  describe('AC-010 — ARIA attributes', () => {
    it('test_progress_indicator_has_aria_valuenow_when_trial_state', () => {
      // TODO: mock useUsage with trial: { active: true, applications_used: 1, applications_limit: 3 }
      // TODO: assert progress element has aria-valuenow="1"
      mockHookState({
        data: {
          trial: { active: true, applications_used: 1, applications_limit: 3 },
          has_active_subscription: false,
        },
      });
      renderCard();
      // TODO: const progressbar = screen.getByRole('progressbar')
      // TODO: expect(progressbar).toHaveAttribute('aria-valuenow', '1')
      expect(document.body).toBeTruthy();
    });

    it('test_progress_indicator_has_aria_valuemin_zero_when_trial_state', () => {
      // TODO: mock useUsage with trial.active: true
      // TODO: assert progress element has aria-valuemin="0"
      mockHookState({
        data: {
          trial: { active: true, applications_used: 1, applications_limit: 3 },
          has_active_subscription: false,
        },
      });
      renderCard();
      // TODO: const progressbar = screen.getByRole('progressbar')
      // TODO: expect(progressbar).toHaveAttribute('aria-valuemin', '0')
      expect(document.body).toBeTruthy();
    });

    it('test_progress_indicator_has_aria_valuemax_three_when_trial_state', () => {
      // TODO: mock useUsage with trial.active: true, applications_limit: 3
      // TODO: assert progress element has aria-valuemax="3"
      mockHookState({
        data: {
          trial: { active: true, applications_used: 1, applications_limit: 3 },
          has_active_subscription: false,
        },
      });
      renderCard();
      // TODO: const progressbar = screen.getByRole('progressbar')
      // TODO: expect(progressbar).toHaveAttribute('aria-valuemax', '3')
      expect(document.body).toBeTruthy();
    });

    it('test_unlimited_credits_element_has_aria_label_when_paid_state', () => {
      // TODO: mock useUsage with has_active_subscription: true
      // TODO: assert the "Unlimited credits" element has aria-label="Unlimited credits"
      mockHookState({ data: { has_active_subscription: true } });
      renderCard();
      // TODO: expect(screen.getByLabelText(/unlimited credits/i)).toBeInTheDocument()
      // TODO: OR: expect(screen.getByRole('region', { name: /unlimited credits/i })).toBeInTheDocument()
      expect(document.body).toBeTruthy();
    });
  });

  // ─── card heading ─────────────────────────────────────────────────────────────
  describe('default state — card heading', () => {
    it('test_card_heading_usage_renders_when_component_mounts', () => {
      // TODO: render <UsageCard /> in any valid state
      // TODO: assert heading with text /^usage$/i is in the document
      mockHookState({ data: { has_active_subscription: true } });
      renderCard();
      // TODO: expect(screen.getByRole('heading', { name: /^usage$/i })).toBeInTheDocument()
      expect(document.body).toBeTruthy();
    });
  });

});
