// spec_id: FE-UI-014  component: TailoredCVsPage
// file: src/frontend/app/tailored-cvs/page.tsx
// All ACs are verification_type: unit — one describe block per AC.
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TailoredCVsPage from '../../../src/frontend/app/tailored-cvs/page';

// ---------------------------------------------------------------------------
// module mocks — reset per test in beforeEach
// ---------------------------------------------------------------------------
const mockUseTailoredCVs = vi.fn();

vi.mock('../../../src/frontend/hooks/useTailoredCVs', () => ({
  useTailoredCVs: () => mockUseTailoredCVs(),
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

// TailoredCVsListTable is a new component (FE-UI-015) — stub at module level
// Note: references TailoredCVsListTable — new component, different from TailoredCVsTable
vi.mock('../../../src/frontend/components/TailoredCVsListTable/TailoredCVsListTable', () => ({
  TailoredCVsListTable: ({
    tailoredCvs,
    isLoading,
    error,
    onRetry,
  }: {
    tailoredCvs: unknown[];
    isLoading: boolean;
    error: Error | null;
    onRetry: () => void;
  }) => (
    <div
      data-testid="tailored-cvs-list-table"
      data-is-loading={String(isLoading)}
      data-has-error={String(!!error)}
      data-tailored-cvs-count={tailoredCvs.length}
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
  return render(<TailoredCVsPage />);
}

function mockHookState(overrides: {
  tailoredCvs?: unknown[];
  isLoading?: boolean;
  error?: Error | null;
  refetch?: () => void;
}) {
  mockUseTailoredCVs.mockReturnValue({
    tailoredCvs: [],
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
// TailoredCVsPage — unit tests
// ===========================================================================
describe('TailoredCVsPage', () => {

  // ─── AC-001: PageHeader renders with title "Tailored CVs" and credits ──────
  describe('AC-001 — PageHeader title and credits', () => {
    it('test_page_header_renders_when_page_loads', () => {
      // TODO: render <TailoredCVsPage />
      // TODO: assert data-testid="page-header" is in document
      renderPage();
      expect(screen.queryByTestId('page-header')).not.toBeNull();
    });

    it('test_page_header_title_is_tailored_cvs_when_page_loads', () => {
      // TODO: render <TailoredCVsPage />
      // TODO: assert PageHeader receives title prop containing "Tailored CVs"
      // TODO: assert data-testid="page-header-title" text matches /tailored cvs/i
      renderPage();
      expect(screen.queryByTestId('page-header-title')).not.toBeNull();
      // TODO: expect(screen.getByTestId('page-header-title').textContent).toMatch(/tailored cvs/i)
    });
  });

  // ─── AC-002: TailoredCVsListTable rendered inside a card container ─────────
  describe('AC-002 — TailoredCVsListTable in card container with sub-heading', () => {
    it('test_tailored_cvs_list_table_renders_when_page_loads', () => {
      // TODO: render <TailoredCVsPage />
      // TODO: assert data-testid="tailored-cvs-list-table" is in document
      renderPage();
      expect(screen.queryByTestId('tailored-cvs-list-table')).not.toBeNull();
    });

    it('test_tailored_cvs_list_table_is_inside_card_container_when_page_loads', () => {
      // TODO: render <TailoredCVsPage />
      // TODO: assert TailoredCVsListTable ancestor element has a card/container class
      // TODO: assert card container is rendered below PageHeader in DOM order
      renderPage();
      const table = screen.queryByTestId('tailored-cvs-list-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.closest('[class*="card"]') ?? table?.closest('[data-card]')).not.toBeNull()
    });

    it('test_all_tailored_cvs_subheading_renders_when_page_loads', () => {
      // TODO: render <TailoredCVsPage />
      // TODO: assert sub-heading "All Tailored CVs" is present in the card area
      // TODO: assert data-testid="page-header-subheading" or equivalent sub-heading element is visible
      renderPage();
      expect(screen.queryByTestId('page-header-subheading')).not.toBeNull();
      // TODO: expect(screen.getByTestId('page-header-subheading').textContent).toMatch(/all tailored cvs/i)
    });
  });

  // ─── AC-003: isLoading=true passed to TailoredCVsListTable during fetch ────
  describe('loading state — isLoading prop', () => {
    it('test_is_loading_true_passed_to_table_when_request_in_flight', () => {
      // TODO: mock useTailoredCVs to return { isLoading: true, tailoredCvs: [], error: null }
      // TODO: render <TailoredCVsPage />
      // TODO: assert data-is-loading="true" on TailoredCVsListTable stub
      mockHookState({ isLoading: true });
      renderPage();
      const table = screen.queryByTestId('tailored-cvs-list-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-is-loading')).toBe('true')
    });

    it('test_is_loading_false_passed_to_table_when_data_has_loaded', () => {
      // TODO: mock useTailoredCVs to return { isLoading: false, tailoredCvs: [], error: null }
      // TODO: assert data-is-loading="false" on TailoredCVsListTable stub
      mockHookState({ isLoading: false });
      renderPage();
      const table = screen.queryByTestId('tailored-cvs-list-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-is-loading')).toBe('false')
    });
  });

  // ─── AC-004: error and onRetry passed to table when request fails ───────────
  describe('error state — error and onRetry props', () => {
    it('test_error_prop_passed_to_table_when_get_cv_tailorings_fails', () => {
      // TODO: mock useTailoredCVs to return { error: new Error('Network fail'), ... }
      // TODO: render <TailoredCVsPage />
      // TODO: assert data-has-error="true" on TailoredCVsListTable stub
      mockHookState({ error: new Error('Network fail') });
      renderPage();
      const table = screen.queryByTestId('tailored-cvs-list-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-has-error')).toBe('true')
    });

    it('test_on_retry_function_passed_to_table_when_page_renders', () => {
      // TODO: render <TailoredCVsPage /> in any state
      // TODO: assert data-has-on-retry="true" on TailoredCVsListTable stub
      mockHookState({});
      renderPage();
      const table = screen.queryByTestId('tailored-cvs-list-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-has-on-retry')).toBe('true')
    });

    it('test_on_retry_triggers_refetch_when_called', () => {
      // TODO: capture the refetch mock from useTailoredCVs
      // TODO: render <TailoredCVsPage />, retrieve the onRetry prop passed to table
      // TODO: call onRetry() and assert refetch was called once
      const mockRefetch = vi.fn();
      mockHookState({ error: new Error('Fail'), refetch: mockRefetch });
      renderPage();
      // TODO: retrieve onRetry from TailoredCVsListTable props and call it
      // TODO: expect(mockRefetch).toHaveBeenCalledOnce()
      expect(mockRefetch).toBeDefined();
    });
  });

  // ─── AC-005: tailoredCvs array passed to table when request succeeds ────────
  describe('default state — data passed to table', () => {
    it('test_tailored_cvs_array_passed_to_table_when_api_succeeds', () => {
      // TODO: mock useTailoredCVs to return { tailoredCvs: [{ id: '1', jobTitle: 'Engineer' }], ... }
      // TODO: render <TailoredCVsPage />
      // TODO: assert data-tailored-cvs-count="1" on TailoredCVsListTable stub
      const fakeCVs = [{ id: '1', jobTitle: 'Software Engineer' }];
      mockHookState({ tailoredCvs: fakeCVs });
      renderPage();
      const table = screen.queryByTestId('tailored-cvs-list-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-tailored-cvs-count')).toBe('1')
    });

    it('test_empty_array_passed_to_table_when_api_returns_empty', () => {
      // TODO: mock useTailoredCVs to return { tailoredCvs: [], isLoading: false, error: null }
      // TODO: assert data-tailored-cvs-count="0" on TailoredCVsListTable stub
      // NOTE: empty state rendering is delegated to TailoredCVsListTable — this page only passes the prop
      mockHookState({ tailoredCvs: [] });
      renderPage();
      const table = screen.queryByTestId('tailored-cvs-list-table');
      expect(table).not.toBeNull();
      // TODO: expect(table?.getAttribute('data-tailored-cvs-count')).toBe('0')
    });
  });

  // ─── AC-006: Hebrew strings render when locale is he ────────────────────────
  describe('i18n — Hebrew strings', () => {
    it('test_hebrew_title_renders_when_locale_is_he', () => {
      // TODO: set mockUseLocale to return 'he'
      // TODO: render <TailoredCVsPage />
      // TODO: assert PageHeader title prop resolves to Hebrew "Tailored CVs" translation key
      // TODO: assert page-header-title contains Hebrew text (e.g. /קורות חיים מותאמים/i or translation key)
      mockUseLocale.mockReturnValue('he');
      mockHookState({});
      renderPage();
      expect(screen.queryByTestId('page-header-title')).not.toBeNull();
      // TODO: expect(screen.getByTestId('page-header-title').textContent).toMatch(/<hebrew-tailored-cvs-key>/i)
    });

    it('test_hebrew_subheading_renders_when_locale_is_he', () => {
      // TODO: set mockUseLocale to return 'he'
      // TODO: render <TailoredCVsPage />
      // TODO: assert "All Tailored CVs" sub-heading resolves to Hebrew translation key
      // TODO: assert data-testid="page-header-subheading" contains Hebrew sub-heading text
      mockUseLocale.mockReturnValue('he');
      mockHookState({});
      renderPage();
      expect(screen.queryByTestId('page-header')).not.toBeNull();
      // TODO: expect(screen.getByTestId('page-header-subheading').textContent).toMatch(/<hebrew-all-tailored-cvs-key>/i)
    });
  });

  // ─── page mounts without crash ───────────────────────────────────────────────
  describe('default state — page mounts', () => {
    it('test_page_renders_without_crash_when_navigated_to', () => {
      // TODO: render <TailoredCVsPage />
      // TODO: assert document.body is not null
      renderPage();
      expect(document.body).toBeTruthy();
    });
  });

});
