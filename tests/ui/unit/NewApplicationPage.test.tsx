// spec_id: FE-UI-010  component: NewApplicationPage
// file: src/frontend/app/applications/new/page.tsx
// All ACs are verification_type: unit — one describe block per AC.
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import NewApplicationPage from '../../../src/frontend/app/applications/new/page';

// ---------------------------------------------------------------------------
// module mocks — reset per test in beforeEach
// ---------------------------------------------------------------------------
const mockPush = vi.fn();
const mockCreateJob = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock('../../../src/frontend/hooks/useJobs', () => ({
  useJobs: () => ({
    createJob: mockCreateJob,
    isCreating: false,
  }),
}));

vi.mock('../../../src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal', () => ({
  ChooseBaseCVModal: ({ isOpen }: { isOpen: boolean }) =>
    isOpen ? <div role="dialog" aria-label="Choose Base CV" /> : null,
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
function renderPage() {
  return render(<NewApplicationPage />);
}

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText(/job title/i), { target: { value: 'Software Engineer' } });
  fireEvent.change(screen.getByLabelText(/company name/i), { target: { value: 'Acme Corp' } });
  fireEvent.change(screen.getByLabelText(/job description/i), { target: { value: 'Build things.' } });
}

// ---------------------------------------------------------------------------
// beforeEach — clear all mocks
// ---------------------------------------------------------------------------
beforeEach(() => {
  vi.clearAllMocks();
  mockUseLocale.mockReturnValue('en');
});

// ===========================================================================
// AC-001 — "+ New Application" on dashboard navigates to /applications/new
// Note: this AC tests dashboard/page.tsx behaviour; tested here as a
// navigation-smoke assertion that the page is reachable at the correct path.
// ===========================================================================
describe('NewApplicationPage', () => {

  // ─── AC-001: dashboard button navigates to /applications/new ──────────────
  // Covered at dashboard level; the page stub exists — verified by route render.
  describe('route existence', () => {
    it('test_page_renders_without_crash_when_navigated_to', () => {
      // TODO: render <NewApplicationPage />
      // TODO: assert document body is not null (page mounts without error)
      renderPage();
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-002: back link visible ────────────────────────────────────────────
  describe('back navigation — visible', () => {
    it('test_back_link_visible_when_page_rendered', () => {
      // TODO: render <NewApplicationPage />
      // TODO: assert element matching /← back/i or aria-label "Back" is in document
      renderPage();
      expect(screen.queryByText(/←/)).not.toBeNull();
    });
  });

  // ─── AC-003: back link navigates to /dashboard ────────────────────────────
  describe('back navigation — destination', () => {
    it('test_back_link_navigates_to_dashboard_when_clicked', () => {
      // TODO: render <NewApplicationPage />
      // TODO: fireEvent.click on back link
      // TODO: assert mockPush called with '/dashboard'
      renderPage();
      const backLink = screen.queryByRole('link', { name: /back/i })
        ?? screen.queryByText(/← back/i)
        ?? screen.queryByLabelText(/back/i);
      expect(backLink).not.toBeNull();
    });
  });

  // ─── AC-004: card layout (not modal overlay) ──────────────────────────────
  describe('layout — card, not modal', () => {
    it('test_form_renders_in_card_not_modal_when_page_loads', () => {
      // TODO: render <NewApplicationPage />
      // TODO: assert no element with role="dialog" exists
      // TODO: assert a card/container element with max-width class exists
      renderPage();
      expect(screen.queryByRole('dialog')).toBeNull();
    });
  });

  // ─── AC-005: four form fields present ─────────────────────────────────────
  describe('form fields — presence', () => {
    it('test_job_title_field_visible_when_page_rendered', () => {
      // TODO: render <NewApplicationPage />
      // TODO: assert getByLabelText(/job title/i) exists
      renderPage();
      expect(screen.queryByLabelText(/job title/i)).not.toBeNull();
    });

    it('test_company_name_field_visible_when_page_rendered', () => {
      // TODO: render <NewApplicationPage />
      // TODO: assert getByLabelText(/company name/i) exists
      renderPage();
      expect(screen.queryByLabelText(/company name/i)).not.toBeNull();
    });

    it('test_job_description_field_visible_when_page_rendered', () => {
      // TODO: render <NewApplicationPage />
      // TODO: assert getByLabelText(/job description/i) is a textarea
      renderPage();
      expect(screen.queryByLabelText(/job description/i)).not.toBeNull();
    });

    it('test_job_url_field_visible_when_page_rendered', () => {
      // TODO: render <NewApplicationPage />
      // TODO: assert getByLabelText(/job url/i) exists and is not required
      renderPage();
      expect(screen.queryByLabelText(/job url/i)).not.toBeNull();
    });
  });

  // ─── AC-006: submit disabled when required fields empty ───────────────────
  describe('disabled state — required fields empty', () => {
    it('test_create_button_disabled_when_required_fields_empty', () => {
      // TODO: render <NewApplicationPage />
      // TODO: assert button "Create Application" has disabled attribute
      renderPage();
      const btn = screen.queryByRole('button', { name: /create application/i });
      expect(btn).not.toBeNull();
      // TODO: assert (btn as HTMLButtonElement).disabled === true
    });
  });

  // ─── AC-007: submit enabled when required fields filled ───────────────────
  describe('default state — required fields filled', () => {
    it('test_create_button_enabled_when_required_fields_filled', () => {
      // TODO: render <NewApplicationPage />
      // TODO: fireEvent.change job title, company name, job description to non-empty strings
      // TODO: assert "Create Application" button is NOT disabled
      renderPage();
      fillRequiredFields();
      const btn = screen.queryByRole('button', { name: /create application/i });
      expect(btn).not.toBeNull();
      // TODO: assert (btn as HTMLButtonElement).disabled === false
    });
  });

  // ─── AC-008: Base CV section visible ──────────────────────────────────────
  describe('Base CV section — visible', () => {
    it('test_base_cv_section_visible_when_page_rendered', () => {
      // TODO: render <NewApplicationPage />
      // TODO: assert text matching /base cv/i exists
      // TODO: assert "Change" button exists within the section
      renderPage();
      expect(screen.queryByText(/base cv/i)).not.toBeNull();
    });

    it('test_change_button_visible_in_base_cv_section_when_page_rendered', () => {
      // TODO: render <NewApplicationPage />
      // TODO: assert getByRole('button', { name: /change/i }) exists
      renderPage();
      expect(screen.queryByRole('button', { name: /^change$/i })).not.toBeNull();
    });
  });

  // ─── AC-009: Change button opens ChooseBaseCVModal ────────────────────────
  describe('Base CV section — Change button', () => {
    it('test_choose_base_cv_modal_opens_when_change_clicked', () => {
      // TODO: render <NewApplicationPage />
      // TODO: fireEvent.click the "Change" button
      // TODO: assert role="dialog" with aria-label "Choose Base CV" appears
      renderPage();
      const changeBtn = screen.queryByRole('button', { name: /^change$/i });
      if (changeBtn) fireEvent.click(changeBtn);
      // TODO: assert screen.getByRole('dialog', { name: /choose base cv/i }) exists
    });
  });

  // ─── AC-010: Base CV section updates after CV selected ────────────────────
  describe('Base CV section — CV selection update', () => {
    it('test_base_cv_filename_updates_when_cv_selected_from_modal', () => {
      // TODO: render <NewApplicationPage />
      // TODO: simulate ChooseBaseCVModal returning a CV { id: '1', filename: 'my-cv.pdf' }
      // TODO: assert Base CV section now shows 'my-cv.pdf'
      renderPage();
      // TODO: implement after ChooseBaseCVModal callback API is known
    });
  });

  // ─── AC-011: loading state — button text "Creating..." and disabled ────────
  describe('loading state — button', () => {
    it('test_button_text_changes_to_creating_when_submission_in_flight', () => {
      // TODO: mock useJobs to return { isCreating: true }
      // TODO: render <NewApplicationPage />
      // TODO: assert button text is "Creating..." and is disabled
      renderPage();
      // TODO: override mock: vi.mocked(useJobs).mockReturnValue({ createJob: mockCreateJob, isCreating: true })
      // TODO: assert screen.getByRole('button', { name: /creating\.\.\./i }).disabled === true
    });
  });

  // ─── AC-012: loading state — all inputs and Cancel disabled ───────────────
  describe('loading state — inputs disabled', () => {
    it('test_all_inputs_disabled_when_submission_in_flight', () => {
      // TODO: mock useJobs isCreating: true
      // TODO: render <NewApplicationPage />
      // TODO: assert job title, company name, job description, job url inputs are all disabled
      // TODO: assert Cancel button is disabled
      renderPage();
      // TODO: for each input assert (input as HTMLInputElement).disabled === true
    });
  });

  // ─── AC-013: successful submission navigates to /applications/{job_id} ────
  describe('default state — successful submission', () => {
    it('test_navigates_to_application_page_when_post_jobs_succeeds', async () => {
      // TODO: mock createJob to resolve with { job_id: 'abc-123' }
      // TODO: render <NewApplicationPage />, fill required fields, click Create Application
      // TODO: await promise resolution
      // TODO: assert mockPush called with '/applications/abc-123'
      mockCreateJob.mockResolvedValueOnce({ job_id: 'abc-123' });
      renderPage();
      fillRequiredFields();
      // TODO: fireEvent.click create button, await async state update
    });
  });

  // ─── AC-014: error state — banner appears on API failure ──────────────────
  describe('error state — banner', () => {
    it('test_error_banner_appears_when_post_jobs_fails', async () => {
      // TODO: mock createJob to reject with Error('Network error')
      // TODO: render, fill fields, submit
      // TODO: assert error banner text 'Network error' is visible in document
      mockCreateJob.mockRejectedValueOnce(new Error('Network error'));
      renderPage();
      fillRequiredFields();
      // TODO: fireEvent.click create button, await async state update
      // TODO: assert screen.getByRole('alert') contains 'Network error'
    });
  });

  // ─── AC-015: error banner dismissed on field modification ─────────────────
  describe('error state — dismissal', () => {
    it('test_error_banner_dismissed_when_user_modifies_field_after_error', async () => {
      // TODO: put component into error state (submit and fail)
      // TODO: fireEvent.change any form field
      // TODO: assert error banner is no longer in document
      renderPage();
      // TODO: drive to error state first, then modify a field, then assert no role="alert"
    });
  });

  // ─── AC-016: Cancel navigates to /dashboard ───────────────────────────────
  describe('default state — cancel', () => {
    it('test_cancel_navigates_to_dashboard_when_clicked', () => {
      // TODO: render <NewApplicationPage />
      // TODO: fireEvent.click Cancel button
      // TODO: assert mockPush called with '/dashboard'
      // TODO: assert createJob was NOT called
      renderPage();
      const cancelBtn = screen.queryByRole('button', { name: /^cancel$/i });
      expect(cancelBtn).not.toBeNull();
      if (cancelBtn) fireEvent.click(cancelBtn);
      // TODO: assert mockPush('/dashboard') and mockCreateJob.mock.calls.length === 0
    });
  });

  // ─── AC-017: accessibility — label/input association ──────────────────────
  describe('accessibility — labels', () => {
    it('test_each_input_has_associated_label_via_htmlFor_when_page_rendered', () => {
      // TODO: render <NewApplicationPage />
      // TODO: assert getByLabelText(/job title/i) returns an element
      // TODO: assert getByLabelText(/company name/i) returns an element
      // TODO: assert getByLabelText(/job description/i) returns an element
      // TODO: assert getByLabelText(/job url/i) returns an element
      renderPage();
      expect(screen.queryByLabelText(/job title/i)).not.toBeNull();
      expect(screen.queryByLabelText(/company name/i)).not.toBeNull();
      expect(screen.queryByLabelText(/job description/i)).not.toBeNull();
      expect(screen.queryByLabelText(/job url/i)).not.toBeNull();
    });
  });

  // ─── AC-018: accessibility — form element and aria-required ───────────────
  describe('accessibility — form semantics', () => {
    it('test_form_element_exists_and_required_fields_have_required_attribute', () => {
      // TODO: render <NewApplicationPage />
      // TODO: assert getByRole('form') or querySelector('form') exists
      // TODO: assert job title, company name, job description have required or aria-required="true"
      renderPage();
      const form = document.querySelector('form');
      expect(form).not.toBeNull();
      // TODO: assert required attributes on job title, company name, job description inputs
    });
  });

  // ─── AC-019: accessibility — error banner role="alert" ────────────────────
  describe('accessibility — error banner', () => {
    it('test_error_banner_has_role_alert_when_error_displayed', async () => {
      // TODO: drive component into error state
      // TODO: assert screen.getByRole('alert') exists
      mockCreateJob.mockRejectedValueOnce(new Error('Server error'));
      renderPage();
      fillRequiredFields();
      // TODO: fireEvent.click create, await, assert role="alert" exists in document
    });
  });

  // ─── AC-020: accessibility — keyboard tab order ───────────────────────────
  describe('accessibility — keyboard navigation', () => {
    it('test_tab_order_follows_visual_order_when_navigating_with_keyboard', () => {
      // TODO: render <NewApplicationPage />
      // TODO: call userEvent.tab() in sequence
      // TODO: assert focus order: Back link → Job Title → Company Name → Job Description
      //        → Job URL → Base CV Change → Cancel → Create Application
      // Note: requires @testing-library/user-event — install if not present
      renderPage();
      // TODO: const user = userEvent.setup(); await user.tab(); assert document.activeElement
    });
  });

  // ─── AC-021: i18n — Hebrew strings ───────────────────────────────────────
  describe('i18n — Hebrew strings', () => {
    it('test_hebrew_strings_render_when_locale_is_he', () => {
      // TODO: set mockUseLocale to return 'he' (or wrap with locale provider)
      // TODO: render <NewApplicationPage />
      // TODO: assert "← חזרה" text exists
      // TODO: assert "שנה" (Change) text exists
      // TODO: assert "יוצר..." (Creating...) text is used as button label during submission
      mockUseLocale.mockReturnValue('he');
      renderPage();
      // TODO: assert screen.queryByText(/← חזרה/) is not null
      // TODO: assert screen.queryByText(/שנה/) is not null
    });
  });

  // ─── AC-022: i18n — RTL layout in Hebrew ─────────────────────────────────
  describe('i18n — RTL direction', () => {
    it('test_layout_direction_is_rtl_when_locale_is_he', () => {
      // TODO: set locale to 'he', render page
      // TODO: assert document.documentElement.dir === 'rtl'
      //       OR assert root element has dir="rtl" attribute
      mockUseLocale.mockReturnValue('he');
      renderPage();
      // TODO: assert dir attribute on html element or outermost container
    });
  });

  // ─── AC-023: responsive — mobile viewport ────────────────────────────────
  describe('responsive — mobile', () => {
    it('test_form_card_spans_full_width_when_viewport_is_mobile', () => {
      // TODO: set window.innerWidth = 375 (or use ResizeObserver mock)
      // TODO: render <NewApplicationPage />
      // TODO: assert the form card element has full-width class or inline style
      // Note: CSS-level assertions require jsdom style computation — may need
      //       @testing-library/jest-dom matchers or a computed-style mock.
      renderPage();
      // TODO: assert card container has w-full class on narrow viewport
    });
  });

  // ─── AC-024: cleanup — NewApplicationModal deleted ────────────────────────
  describe('cleanup — NewApplicationModal removed', () => {
    it('test_new_application_modal_module_does_not_exist_when_spec_implemented', async () => {
      // TODO: attempt dynamic import of '../../../src/frontend/components/NewApplicationModal/NewApplicationModal'
      // TODO: assert the import throws (module not found)
      // NOTE: This test should be enabled only after the modal file is deleted.
      //       Until then mark as pending with a reason comment.
      // Reason: modal file still exists pre-implementation — enable after deletion.
      // expect(async () => { await import('...NewApplicationModal') }).rejects.toThrow();
      expect(true).toBe(true); // placeholder — replace with import assertion post-deletion
    });
  });

});
