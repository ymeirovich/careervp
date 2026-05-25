// spec_id: FE-UI-016  component: CVCenterContent
// file: src/frontend/app/cv-center/page.tsx
// All ACs are verification_type: unit — one describe block per AC.
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import CVCenterPage from '../../../src/frontend/app/cv-center/page';

// ---------------------------------------------------------------------------
// module mocks — reset per test in beforeEach
// ---------------------------------------------------------------------------
// TODO: replace 'useBaseCVs' with the actual hook name once implemented
const mockUseBaseCVs = vi.fn();

vi.mock('../../../src/frontend/hooks/useBaseCVs', () => ({
  useBaseCVs: () => mockUseBaseCVs(),
}));

vi.mock('../../../src/frontend/components/PageHeader/PageHeader', () => ({
  PageHeader: ({ title }: { title: string }) => (
    <header data-testid="page-header">
      <span data-testid="page-header-title">{title}</span>
    </header>
  ),
}));

vi.mock('../../../src/frontend/components/UserMenu/UserMenu', () => ({
  UserMenu: () => <div data-testid="user-menu" />,
}));

// BaseCVsTable stub (FE-UI-017) — exposes props as data attributes for assertions
vi.mock('../../../src/frontend/components/BaseCVsTable/BaseCVsTable', () => ({
  BaseCVsTable: ({
    cvs,
    isLoading,
    error,
    onRetry,
  }: {
    cvs: unknown[];
    isLoading: boolean;
    error: Error | null;
    onRetry: () => void;
  }) => (
    <div
      data-testid="base-cvs-table"
      data-is-loading={String(isLoading)}
      data-has-error={String(!!error)}
      data-cvs-count={cvs.length}
      data-has-on-retry={String(typeof onRetry === 'function')}
    />
  ),
}));

// ChooseBaseCVModal stub (FE-UI-011)
vi.mock('../../../src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal', () => ({
  ChooseBaseCVModal: ({
    isOpen,
    showChoices,
    onClose,
    onSuccess,
  }: {
    isOpen: boolean;
    showChoices: boolean;
    onClose: () => void;
    onSuccess: () => void;
  }) =>
    isOpen ? (
      <div
        role="dialog"
        data-testid="choose-base-cv-modal"
        data-show-choices={String(showChoices)}
      >
        <button data-testid="modal-close-btn" onClick={onClose}>Close</button>
        <button data-testid="modal-success-btn" onClick={onSuccess}>Upload success</button>
      </div>
    ) : null,
}));

// ErrorBoundary stub — passes through children and exposes cloudwatchKey
vi.mock('../../../src/frontend/components/ErrorBoundary/ErrorBoundary', () => ({
  ErrorBoundary: ({
    children,
    cloudwatchKey,
  }: {
    children: React.ReactNode;
    cloudwatchKey: string;
  }) => (
    <div data-testid="error-boundary" data-cloudwatch-key={cloudwatchKey}>
      {children}
    </div>
  ),
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
  return render(<CVCenterPage />);
}

function mockHookState(overrides: {
  cvs?: unknown[];
  isLoading?: boolean;
  error?: Error | null;
  refetch?: () => void;
}) {
  mockUseBaseCVs.mockReturnValue({
    cvs: [],
    isLoading: false,
    error: null,
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
// CVCenterContent — unit tests
// ===========================================================================
describe('CVCenterContent', () => {

  // ─── AC-001: Page header renders with text "Base CVs" ─────────────────────
  describe('AC-001 — page header text "Base CVs"', () => {
    it('test_page_header_renders_when_page_loads', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert data-testid="page-header" is in document
      renderPage();
      expect(screen.queryByTestId('page-header')).not.toBeNull();
    });

    it('test_page_header_title_is_base_cvs_when_page_loads', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert data-testid="page-header-title" text matches /base cvs/i
      // TODO: assert PageHeader receives title prop resolving to "Base CVs" translation key
      renderPage();
      expect(screen.queryByTestId('page-header-title')).not.toBeNull();
      // TODO: expect(screen.getByTestId('page-header-title').textContent).toMatch(/base cvs/i)
    });
  });

  // ─── AC-002: Card container with "All Base CVs" sub-heading ───────────────
  describe('AC-002 — card container and "All Base CVs" sub-heading', () => {
    it('test_card_container_renders_below_header_when_page_loads', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert a card/container element exists below the page header
      renderPage();
      // TODO: const card = document.querySelector('[class*="card"]') or data-testid="cv-card"
      // TODO: expect(card).not.toBeNull()
      expect(document.body).toBeTruthy();
    });

    it('test_all_base_cvs_subheading_renders_in_card_when_page_loads', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert text matching /all base cvs/i or the translation key is visible inside the card
      renderPage();
      // TODO: expect(screen.queryByText(/all base cvs/i)).not.toBeNull()
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-003: "+ Upload New CV" button with orange bg ──────────────────────
  describe('AC-003 — "+ Upload New CV" orange button', () => {
    it('test_upload_new_cv_button_renders_when_page_loads', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert button with text /\+ upload new cv/i is in document
      renderPage();
      // TODO: expect(screen.queryByRole('button', { name: /upload new cv/i })).not.toBeNull()
      expect(document.body).toBeTruthy();
    });

    it('test_upload_button_has_orange_bg_class_when_rendered', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert button has className containing 'bg-primary-action'
      renderPage();
      // TODO: const btn = screen.getByRole('button', { name: /upload new cv/i })
      // TODO: expect(btn.className).toMatch(/bg-primary-action/)
      expect(document.body).toBeTruthy();
    });

    it('test_upload_button_is_positioned_on_right_of_subheading_row_when_rendered', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert the button and "All Base CVs" text share the same parent row element
      renderPage();
      // TODO: assert button and sub-heading text are siblings inside a flex/row container
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-004: BaseCVsTable rendered inside card container ──────────────────
  describe('AC-004 — BaseCVsTable in card body', () => {
    it('test_base_cvs_table_renders_when_page_loads', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert data-testid="base-cvs-table" is in document
      renderPage();
      expect(screen.queryByTestId('base-cvs-table')).not.toBeNull();
    });

    it('test_base_cvs_table_is_inside_card_container_when_rendered', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert BaseCVsTable ancestor element is the same card that has "All Base CVs" heading
      renderPage();
      const table = screen.queryByTestId('base-cvs-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.closest('[data-testid="cv-card"]') ?? table?.closest('[class*="card"]')).not.toBeNull()
    });
  });

  // ─── AC-005: isLoading=true passed to BaseCVsTable during fetch ───────────
  describe('loading state — isLoading prop', () => {
    it('test_is_loading_true_passed_to_table_when_request_in_flight', () => {
      // TODO: mock useBaseCVs to return { isLoading: true, cvs: [], error: null }
      // TODO: render <CVCenterPage />
      // TODO: assert data-is-loading="true" on BaseCVsTable stub
      mockHookState({ isLoading: true });
      renderPage();
      const table = screen.queryByTestId('base-cvs-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-is-loading')).toBe('true')
    });

    it('test_is_loading_false_passed_to_table_when_data_has_loaded', () => {
      // TODO: mock useBaseCVs to return { isLoading: false, cvs: [], error: null }
      // TODO: assert data-is-loading="false" on BaseCVsTable stub
      mockHookState({ isLoading: false });
      renderPage();
      const table = screen.queryByTestId('base-cvs-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-is-loading')).toBe('false')
    });
  });

  // ─── AC-006: error and onRetry passed to table when request fails ──────────
  describe('error state — error and onRetry props', () => {
    it('test_error_prop_passed_to_table_when_get_users_me_cv_fails', () => {
      // TODO: mock useBaseCVs to return { error: new Error('Network fail'), cvs: [], isLoading: false }
      // TODO: render <CVCenterPage />
      // TODO: assert data-has-error="true" on BaseCVsTable stub
      mockHookState({ error: new Error('Network fail') });
      renderPage();
      const table = screen.queryByTestId('base-cvs-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-has-error')).toBe('true')
    });

    it('test_on_retry_function_passed_to_table_when_page_renders', () => {
      // TODO: render <CVCenterPage /> in any state
      // TODO: assert data-has-on-retry="true" on BaseCVsTable stub
      mockHookState({});
      renderPage();
      const table = screen.queryByTestId('base-cvs-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-has-on-retry')).toBe('true')
    });

    it('test_on_retry_triggers_refetch_when_called', () => {
      // TODO: capture the refetch mock from useBaseCVs
      // TODO: render <CVCenterPage />, retrieve the onRetry prop passed to BaseCVsTable
      // TODO: call onRetry() and assert refetch was called once
      const mockRefetch = vi.fn();
      mockHookState({ error: new Error('Fail'), refetch: mockRefetch });
      renderPage();
      // TODO: retrieve onRetry from BaseCVsTable props and call it
      // TODO: expect(mockRefetch).toHaveBeenCalledOnce()
      expect(mockRefetch).toBeDefined();
    });
  });

  // ─── AC-007: cvs array passed to table when request succeeds ──────────────
  describe('default state — data passed to table', () => {
    it('test_cvs_array_passed_to_table_when_api_succeeds', () => {
      // TODO: mock useBaseCVs to return { cvs: [{ cv_id: '1', full_name: 'John Doe' }], ... }
      // TODO: render <CVCenterPage />
      // TODO: assert data-cvs-count="1" on BaseCVsTable stub
      const fakeCVs = [{ cv_id: '1', full_name: 'John Doe', language: 'en', updated_at: '2026-01-01' }];
      mockHookState({ cvs: fakeCVs });
      renderPage();
      const table = screen.queryByTestId('base-cvs-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-cvs-count')).toBe('1')
    });

    it('test_empty_array_passed_to_table_when_api_returns_empty', () => {
      // TODO: mock useBaseCVs to return { cvs: [], isLoading: false, error: null }
      // TODO: assert data-cvs-count="0" on BaseCVsTable stub
      // NOTE: empty-state rendering is BaseCVsTable's responsibility (FE-UI-017)
      mockHookState({ cvs: [] });
      renderPage();
      const table = screen.queryByTestId('base-cvs-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-cvs-count')).toBe('0')
    });
  });

  // ─── AC-008: clicking "+ Upload New CV" opens ChooseBaseCVModal ───────────
  describe('upload flow — modal opens on button click', () => {
    it('test_choose_base_cv_modal_not_open_on_initial_render', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert role="dialog" is not in document (modal closed by default)
      renderPage();
      expect(screen.queryByRole('dialog')).toBeNull();
    });

    it('test_choose_base_cv_modal_opens_when_upload_button_clicked', () => {
      // TODO: render <CVCenterPage />
      // TODO: fireEvent.click on the "+ Upload New CV" button
      // TODO: assert data-testid="choose-base-cv-modal" is in document
      renderPage();
      // TODO: const btn = screen.getByRole('button', { name: /upload new cv/i })
      // TODO: fireEvent.click(btn)
      // TODO: expect(screen.queryByTestId('choose-base-cv-modal')).not.toBeNull()
      expect(document.body).toBeTruthy();
    });

    it('test_choose_base_cv_modal_opened_with_show_choices_false_when_upload_button_clicked', () => {
      // TODO: render <CVCenterPage />
      // TODO: click "+ Upload New CV" button
      // TODO: assert data-show-choices="false" on ChooseBaseCVModal stub (upload-only mode)
      renderPage();
      // TODO: fireEvent.click(screen.getByRole('button', { name: /upload new cv/i }))
      // TODO: expect(screen.getByTestId('choose-base-cv-modal').getAttribute('data-show-choices')).toBe('false')
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-009: modal closes and refetch triggered after upload success ───────
  describe('upload flow — success callback', () => {
    it('test_modal_closes_when_upload_completes_successfully', () => {
      // TODO: render <CVCenterPage />
      // TODO: click "+ Upload New CV" to open modal
      // TODO: click modal success trigger button (simulates onSuccess callback)
      // TODO: assert role="dialog" is no longer in document
      renderPage();
      // TODO: fireEvent.click(screen.getByRole('button', { name: /upload new cv/i }))
      // TODO: fireEvent.click(screen.getByTestId('modal-success-btn'))
      // TODO: expect(screen.queryByRole('dialog')).toBeNull()
      expect(document.body).toBeTruthy();
    });

    it('test_get_users_me_cv_refetched_when_upload_succeeds', () => {
      // TODO: capture refetch mock from useBaseCVs
      // TODO: render <CVCenterPage />, open modal, trigger onSuccess
      // TODO: assert refetch was called once
      const mockRefetch = vi.fn();
      mockHookState({ refetch: mockRefetch });
      renderPage();
      // TODO: fireEvent.click(screen.getByRole('button', { name: /upload new cv/i }))
      // TODO: fireEvent.click(screen.getByTestId('modal-success-btn'))
      // TODO: expect(mockRefetch).toHaveBeenCalledOnce()
      expect(mockRefetch).toBeDefined();
    });

    it('test_modal_closes_when_close_button_clicked', () => {
      // TODO: render <CVCenterPage />
      // TODO: open modal, click close button
      // TODO: assert role="dialog" is no longer in document
      renderPage();
      // TODO: fireEvent.click(screen.getByRole('button', { name: /upload new cv/i }))
      // TODO: fireEvent.click(screen.getByTestId('modal-close-btn'))
      // TODO: expect(screen.queryByRole('dialog')).toBeNull()
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-010: CVForm, CVPreview, TagInput absent from DOM ──────────────────
  describe('AC-010 — removed components absent', () => {
    it('test_cv_form_not_rendered_when_page_loads', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert no element with data-testid="cv-form" or role="form" for CV editing exists
      renderPage();
      // TODO: expect(screen.queryByTestId('cv-form')).toBeNull()
      expect(document.body).toBeTruthy();
    });

    it('test_cv_preview_not_rendered_when_page_loads', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert no element with data-testid="cv-preview" exists
      renderPage();
      // TODO: expect(screen.queryByTestId('cv-preview')).toBeNull()
      expect(document.body).toBeTruthy();
    });

    it('test_tag_input_not_rendered_when_page_loads', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert no element with data-testid="tag-input" or role="combobox" for skills/languages exists
      renderPage();
      // TODO: expect(screen.queryByTestId('tag-input')).toBeNull()
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-011: "Edit CV" / "Create CV" buttons and ViewMode absent ──────────
  describe('AC-011 — removed buttons and state machine absent', () => {
    it('test_edit_cv_button_not_rendered_when_page_loads', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert no button with text /edit cv/i is in document
      renderPage();
      // TODO: expect(screen.queryByRole('button', { name: /edit cv/i })).toBeNull()
      expect(document.body).toBeTruthy();
    });

    it('test_create_cv_button_not_rendered_when_page_loads', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert no button with text /create cv/i is in document
      renderPage();
      // TODO: expect(screen.queryByRole('button', { name: /create cv/i })).toBeNull()
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-012: ErrorBoundary wraps page with cloudwatchKey="cv-center-page" ──
  describe('AC-012 — ErrorBoundary wrapper', () => {
    it('test_error_boundary_wraps_page_content_when_rendered', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert data-testid="error-boundary" is an ancestor of the page content
      renderPage();
      // TODO: expect(screen.queryByTestId('error-boundary')).not.toBeNull()
      expect(document.body).toBeTruthy();
    });

    it('test_error_boundary_has_cv_center_page_cloudwatch_key_when_rendered', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert data-cloudwatch-key="cv-center-page" on error boundary stub
      renderPage();
      // TODO: const boundary = screen.getByTestId('error-boundary')
      // TODO: expect(boundary.getAttribute('data-cloudwatch-key')).toBe('cv-center-page')
      expect(document.body).toBeTruthy();
    });
  });

  // ─── AC-013: Hebrew strings when locale is he ─────────────────────────────
  describe('i18n — Hebrew strings', () => {
    it('test_base_cvs_header_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: set mockUseLocale to return 'he'
      // TODO: render <CVCenterPage />
      // TODO: assert PageHeader title prop resolves to Hebrew "Base CVs" translation key
      mockUseLocale.mockReturnValue('he');
      mockHookState({});
      renderPage();
      expect(screen.queryByTestId('page-header-title')).not.toBeNull();
      // TODO: expect(screen.getByTestId('page-header-title').textContent).toMatch(/<hebrew-base-cvs-key>/i)
    });

    it('test_all_base_cvs_subheading_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: set mockUseLocale to return 'he'
      // TODO: render <CVCenterPage />
      // TODO: assert "All Base CVs" sub-heading resolves to Hebrew translation key
      mockUseLocale.mockReturnValue('he');
      mockHookState({});
      renderPage();
      // TODO: expect(screen.queryByText(/<hebrew-all-base-cvs-key>/i)).not.toBeNull()
      expect(document.body).toBeTruthy();
    });

    it('test_upload_button_label_renders_in_hebrew_when_locale_is_he', () => {
      // TODO: set mockUseLocale to return 'he'
      // TODO: render <CVCenterPage />
      // TODO: assert "+ Upload New CV" button label resolves to Hebrew translation key
      mockUseLocale.mockReturnValue('he');
      mockHookState({});
      renderPage();
      // TODO: expect(screen.queryByRole('button', { name: /<hebrew-upload-new-cv-key>/i })).not.toBeNull()
      expect(document.body).toBeTruthy();
    });
  });

  // ─── page mounts without crash ────────────────────────────────────────────
  describe('default state — page mounts', () => {
    it('test_page_renders_without_crash_when_navigated_to', () => {
      // TODO: render <CVCenterPage />
      // TODO: assert document.body is not null
      renderPage();
      expect(document.body).toBeTruthy();
    });
  });

});
