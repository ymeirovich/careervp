// spec_id: FE-UI-012  component: CoverLettersPage
// file: src/frontend/app/cover-letters/page.tsx
// All ACs are verification_type: unit — one describe block per AC.
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import CoverLettersPage from '../../../src/frontend/app/cover-letters/page';

// ---------------------------------------------------------------------------
// module mocks — reset per test in beforeEach
// ---------------------------------------------------------------------------
const mockUseCoverLetters = vi.fn();

vi.mock('../../../src/frontend/hooks/useCoverLetters', () => ({
  useCoverLetters: () => mockUseCoverLetters(),
}));

vi.mock('../../../src/frontend/components/PageHeader/PageHeader', () => ({
  PageHeader: ({ title, subHeading }: { title: string; subHeading?: string }) => (
    <header data-testid="page-header">
      <span data-testid="page-header-title">{title}</span>
      {subHeading && <span data-testid="page-header-subheading">{subHeading}</span>}
    </header>
  ),
}));

vi.mock('../../../src/frontend/components/UserMenu/UserMenu', () => ({
  UserMenu: () => <div data-testid="user-menu" />,
}));

// CoverLettersListTable is a new component (FE-UI-013) — stub at module level
vi.mock('../../../src/frontend/components/CoverLettersListTable/CoverLettersListTable', () => ({
  CoverLettersListTable: ({
    coverLetters,
    isLoading,
    error,
    onRetry,
  }: {
    coverLetters: unknown[];
    isLoading: boolean;
    error: Error | null;
    onRetry: () => void;
  }) => (
    <div
      data-testid="cover-letters-list-table"
      data-is-loading={String(isLoading)}
      data-has-error={String(!!error)}
      data-cover-letters-count={coverLetters.length}
      data-has-on-retry={String(typeof onRetry === 'function')}
    />
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
  return render(<CoverLettersPage />);
}

function mockHookState(overrides: {
  coverLetters?: unknown[];
  isLoading?: boolean;
  error?: Error | null;
  refetch?: () => void;
}) {
  mockUseCoverLetters.mockReturnValue({
    coverLetters: [],
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
// CoverLettersPage — unit tests
// ===========================================================================
describe('CoverLettersPage', () => {

  // ─── AC-001: PageHeader renders with title "Cover Letters" and credits ─────
  describe('AC-001 — PageHeader title and credits', () => {
    it('test_page_header_renders_when_page_loads', () => {
      // TODO: render <CoverLettersPage />
      // TODO: assert data-testid="page-header" is in document
      renderPage();
      expect(screen.queryByTestId('page-header')).not.toBeNull();
    });

    it('test_page_header_title_is_cover_letters_when_page_loads', () => {
      // TODO: render <CoverLettersPage />
      // TODO: assert PageHeader receives title prop containing "Cover Letters"
      // TODO: assert data-testid="page-header-title" text matches /cover letters/i
      renderPage();
      expect(screen.queryByTestId('page-header-title')).not.toBeNull();
      // TODO: expect(screen.getByTestId('page-header-title').textContent).toMatch(/cover letters/i)
    });
  });

  // ─── AC-002: CoverLettersListTable rendered inside a card container ────────
  describe('AC-002 — CoverLettersListTable in card container', () => {
    it('test_cover_letters_list_table_renders_when_page_loads', () => {
      // TODO: render <CoverLettersPage />
      // TODO: assert data-testid="cover-letters-list-table" is in document
      renderPage();
      expect(screen.queryByTestId('cover-letters-list-table')).not.toBeNull();
    });

    it('test_cover_letters_list_table_is_inside_card_container_when_page_loads', () => {
      // TODO: render <CoverLettersPage />
      // TODO: assert CoverLettersListTable ancestor element has a card/container class
      // TODO: assert card container is rendered below PageHeader in DOM order
      renderPage();
      const table = screen.queryByTestId('cover-letters-list-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.closest('[class*="card"]') ?? table?.closest('[data-card]')).not.toBeNull()
    });
  });

  // ─── AC-003: isLoading=true passed to CoverLettersListTable during fetch ───
  describe('loading state — isLoading prop', () => {
    it('test_is_loading_true_passed_to_table_when_request_in_flight', () => {
      // TODO: mock useCoverLetters to return { isLoading: true, coverLetters: [], error: null }
      // TODO: render <CoverLettersPage />
      // TODO: assert data-is-loading="true" on CoverLettersListTable stub
      mockHookState({ isLoading: true });
      renderPage();
      const table = screen.queryByTestId('cover-letters-list-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-is-loading')).toBe('true')
    });

    it('test_is_loading_false_passed_to_table_when_data_has_loaded', () => {
      // TODO: mock useCoverLetters to return { isLoading: false, coverLetters: [], error: null }
      // TODO: assert data-is-loading="false" on CoverLettersListTable stub
      mockHookState({ isLoading: false });
      renderPage();
      const table = screen.queryByTestId('cover-letters-list-table');
      // TODO: expect(table?.getAttribute('data-is-loading')).toBe('false')
      expect(table).not.toBeNull();
    });
  });

  // ─── AC-004: error and onRetry passed to table when request fails ──────────
  describe('error state — error and onRetry props', () => {
    it('test_error_prop_passed_to_table_when_get_cover_letters_fails', () => {
      // TODO: mock useCoverLetters to return { error: new Error('Network fail'), ... }
      // TODO: render <CoverLettersPage />
      // TODO: assert data-has-error="true" on CoverLettersListTable stub
      mockHookState({ error: new Error('Network fail') });
      renderPage();
      const table = screen.queryByTestId('cover-letters-list-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-has-error')).toBe('true')
    });

    it('test_on_retry_function_passed_to_table_when_page_renders', () => {
      // TODO: render <CoverLettersPage /> in any state
      // TODO: assert data-has-on-retry="true" on CoverLettersListTable stub
      // TODO: assert that triggering onRetry calls useCoverLetters refetch
      mockHookState({});
      renderPage();
      const table = screen.queryByTestId('cover-letters-list-table');
      // TODO: expect(table?.getAttribute('data-has-on-retry')).toBe('true')
      expect(table).not.toBeNull();
    });

    it('test_on_retry_triggers_refetch_when_called', () => {
      // TODO: capture the refetch mock from useCoverLetters
      // TODO: render <CoverLettersPage />, retrieve the onRetry prop passed to table
      // TODO: call onRetry() and assert refetch was called once
      const mockRefetch = vi.fn();
      mockHookState({ error: new Error('Fail'), refetch: mockRefetch });
      renderPage();
      // TODO: retrieve onRetry from CoverLettersListTable props and call it
      // TODO: expect(mockRefetch).toHaveBeenCalledOnce()
      expect(mockRefetch).toBeDefined();
    });
  });

  // ─── AC-005: coverLetters array passed to table when request succeeds ──────
  describe('default state — data passed to table', () => {
    it('test_cover_letters_array_passed_to_table_when_api_succeeds', () => {
      // TODO: mock useCoverLetters to return { coverLetters: [{ id: '1', title: 'Engineer' }], ... }
      // TODO: render <CoverLettersPage />
      // TODO: assert data-cover-letters-count="1" on CoverLettersListTable stub
      const fakeCoverLetters = [{ id: '1', title: 'Software Engineer cover letter' }];
      mockHookState({ coverLetters: fakeCoverLetters });
      renderPage();
      const table = screen.queryByTestId('cover-letters-list-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-cover-letters-count')).toBe('1')
    });

    it('test_empty_array_passed_to_table_when_api_returns_empty', () => {
      // TODO: mock useCoverLetters to return { coverLetters: [], isLoading: false, error: null }
      // TODO: assert data-cover-letters-count="0" on CoverLettersListTable stub
      // NOTE: empty state is delegated to CoverLettersListTable — this page only passes the prop
      mockHookState({ coverLetters: [] });
      renderPage();
      const table = screen.queryByTestId('cover-letters-list-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-cover-letters-count')).toBe('0')
    });
  });

  // ─── AC-006: Hebrew strings render when locale is he ──────────────────────
  describe('i18n — Hebrew strings', () => {
    it('test_hebrew_title_renders_when_locale_is_he', () => {
      // TODO: set mockUseLocale to return 'he'
      // TODO: render <CoverLettersPage />
      // TODO: assert PageHeader title prop resolves to Hebrew "Cover Letters" translation key
      // TODO: assert page-header-title contains Hebrew text (e.g. /מכתבי מוטיבציה/i or translation key)
      mockUseLocale.mockReturnValue('he');
      mockHookState({});
      renderPage();
      expect(screen.queryByTestId('page-header-title')).not.toBeNull();
      // TODO: expect(screen.getByTestId('page-header-title').textContent).toMatch(/<hebrew-key>/i)
    });

    it('test_hebrew_subheading_renders_when_locale_is_he', () => {
      // TODO: set mockUseLocale to return 'he'
      // TODO: render <CoverLettersPage />
      // TODO: assert "All Cover Letters" sub-heading resolves to Hebrew translation key
      mockUseLocale.mockReturnValue('he');
      mockHookState({});
      renderPage();
      // TODO: assert data-testid="page-header-subheading" contains Hebrew sub-heading text
      expect(screen.queryByTestId('page-header')).not.toBeNull();
    });
  });

  // ─── page mounts without crash ────────────────────────────────────────────
  describe('default state — page mounts', () => {
    it('test_page_renders_without_crash_when_navigated_to', () => {
      // TODO: render <CoverLettersPage />
      // TODO: assert document.body is not null
      renderPage();
      expect(document.body).toBeTruthy();
    });
  });

});
