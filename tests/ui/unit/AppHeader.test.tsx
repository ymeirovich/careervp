import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AppHeader } from '../../../src/frontend/components/layout/AppHeader';

vi.mock('next/navigation', () => ({
  usePathname: vi.fn(() => '/dashboard'),
}));

import { usePathname } from 'next/navigation';

const mockUsePathname = vi.mocked(usePathname);

describe('AppHeader', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue('/dashboard');
  });

  // ─── AC-001: Credits format with used=1, total=3 ────────────────────────────

  describe('credits label — partial usage', () => {
    it('test_credits_label_format_when_one_of_three_used', () => {
      // TODO: render <AppHeader creditsUsed={1} creditsTotal={3} isUnlimited={false} />
      // TODO: assert screen.getByText('Credits: 1 / 3') exists
    });
  });

  // ─── AC-002: Credits format with used=0, total=3 ────────────────────────────

  describe('credits label — zero used', () => {
    it('test_credits_label_format_when_zero_of_three_used', () => {
      // TODO: render <AppHeader creditsUsed={0} creditsTotal={3} isUnlimited={false} />
      // TODO: assert screen.getByText('Credits: 0 / 3') exists
    });
  });

  // ─── AC-003: Unlimited display ───────────────────────────────────────────────

  describe('credits label — unlimited plan', () => {
    it('test_credits_label_shows_unlimited_when_isUnlimited_true', () => {
      // TODO: render <AppHeader isUnlimited={true} />
      // TODO: assert screen.getByText('Unlimited') exists
    });
  });

  // ─── AC-004: Dropdown menu appears on account button click ──────────────────

  describe('account dropdown — opens', () => {
    it('test_dropdown_appears_when_account_button_clicked', () => {
      // TODO: render <AppHeader userName="Test User" />
      // TODO: fireEvent.click on the account button
      // TODO: assert screen.getByText('Help') is in the document
      // TODO: assert screen.getByText('Log out') is in the document
      // TODO: assert screen.getByText('Upgrade') is in the document
    });

    it('test_dropdown_not_visible_before_account_button_clicked', () => {
      // TODO: render <AppHeader userName="Test User" />
      // TODO: assert screen.queryByText('Help') is null (dropdown hidden by default)
    });
  });

  // ─── AC-005: Log out item has red text styling ───────────────────────────────

  describe('account dropdown — logout styling', () => {
    it('test_logout_item_has_red_text_class_when_dropdown_open', () => {
      // TODO: render <AppHeader userName="Test User" />
      // TODO: fireEvent.click on the account button to open dropdown
      // TODO: get the 'Log out' element
      // TODO: assert element has class matching text-state-error (or red color equivalent)
    });
  });

  // ─── AC-006: Upgrade button has orange filled styling ───────────────────────

  describe('account dropdown — upgrade button styling', () => {
    it('test_upgrade_button_has_orange_filled_class_when_dropdown_open', () => {
      // TODO: render <AppHeader userName="Test User" />
      // TODO: fireEvent.click on the account button to open dropdown
      // TODO: get the 'Upgrade' element
      // TODO: assert element has class matching bg-primary-action and text-white (or orange equivalent)
    });
  });

  // ─── AC-007: Upgrade button navigates to /billing ───────────────────────────

  describe('account dropdown — upgrade navigation', () => {
    it('test_upgrade_click_navigates_to_billing_when_dropdown_open', () => {
      // TODO: mock next/navigation router.push (or Link href)
      // TODO: render <AppHeader userName="Test User" />
      // TODO: fireEvent.click account button to open dropdown
      // TODO: fireEvent.click 'Upgrade' item
      // TODO: assert router.push was called with '/billing' OR assert Link href is '/billing'
    });
  });

  // ─── AC-009: PAGE_TITLES — /cv-center → "Base CVs" ──────────────────────────

  describe('page title — /cv-center', () => {
    it('test_page_title_shows_base_cvs_when_pathname_is_cv_center', () => {
      // TODO: mockUsePathname.mockReturnValue('/cv-center')
      // TODO: render <AppHeader />
      // TODO: assert screen.getByRole('heading', { name: 'Base CVs' }) exists
    });
  });

  // ─── AC-010: PAGE_TITLES — /tailored-cvs → "Tailored CVs" ──────────────────

  describe('page title — /tailored-cvs', () => {
    it('test_page_title_shows_tailored_cvs_when_pathname_is_tailored_cvs', () => {
      // TODO: mockUsePathname.mockReturnValue('/tailored-cvs')
      // TODO: render <AppHeader />
      // TODO: assert screen.getByRole('heading', { name: 'Tailored CVs' }) exists
    });
  });

  // ─── AC-011: PAGE_TITLES — /cover-letters → "Cover Letters" ─────────────────

  describe('page title — /cover-letters', () => {
    it('test_page_title_shows_cover_letters_when_pathname_is_cover_letters', () => {
      // TODO: mockUsePathname.mockReturnValue('/cover-letters')
      // TODO: render <AppHeader />
      // TODO: assert screen.getByRole('heading', { name: 'Cover Letters' }) exists
    });
  });

  // ─── AC-012: PAGE_TITLES — /applications/[id] → "Job Application Hub" ───────

  describe('page title — /applications/[id]', () => {
    it('test_page_title_shows_job_application_hub_when_pathname_matches_applications_id', () => {
      // TODO: mockUsePathname.mockReturnValue('/applications/abc123')
      // TODO: render <AppHeader />
      // TODO: assert screen.getByRole('heading', { name: 'Job Application Hub' }) exists
    });
  });

  // ─── AC-013: Old "X / Y applications" text must not exist ───────────────────

  describe('credits label — old format removed', () => {
    it('test_old_applications_suffix_format_not_rendered_when_not_unlimited', () => {
      // TODO: render <AppHeader creditsUsed={2} creditsTotal={3} isUnlimited={false} />
      // TODO: assert screen.queryByText(/\d+ \/ \d+ applications/) returns null
    });

    it('test_old_applications_suffix_format_not_rendered_when_unlimited', () => {
      // TODO: render <AppHeader isUnlimited={true} />
      // TODO: assert screen.queryByText(/\d+ \/ \d+ applications/) returns null
    });
  });

  // ─── Dropdown toggle — closes on second click ────────────────────────────────

  describe('account dropdown — toggles closed', () => {
    it('test_dropdown_closes_when_account_button_clicked_again', () => {
      // TODO: render <AppHeader userName="Test User" />
      // TODO: fireEvent.click account button → dropdown opens
      // TODO: fireEvent.click account button again → dropdown closes
      // TODO: assert screen.queryByText('Help') is null
    });
  });

  // ─── Accessibility: role="menu" and role="menuitem" ─────────────────────────

  describe('accessibility', () => {
    it('test_dropdown_has_menu_role_when_open', () => {
      // TODO: render <AppHeader userName="Test User" />
      // TODO: fireEvent.click account button to open dropdown
      // TODO: assert screen.getByRole('menu') exists
    });

    it('test_dropdown_items_have_menuitem_role_when_open', () => {
      // TODO: render <AppHeader userName="Test User" />
      // TODO: fireEvent.click account button to open dropdown
      // TODO: assert screen.getAllByRole('menuitem').length >= 3
    });

    it('test_keyboard_escape_closes_dropdown_when_focused', () => {
      // TODO: render <AppHeader userName="Test User" />
      // TODO: fireEvent.click account button to open dropdown
      // TODO: fireEvent.keyDown(document, { key: 'Escape' })
      // TODO: assert screen.queryByRole('menu') is null
    });

    it('test_account_button_has_accessible_label', () => {
      // TODO: render <AppHeader userName="Test User" />
      // TODO: assert the account button has aria-label or accessible name containing user name
    });
  });
});
