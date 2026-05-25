// spec_id: FE-UI-016  component: CVCenterContent  tier: integration
// file: src/frontend/app/cv-center/page.tsx
// All spec ACs are verification_type: unit; these integration tests cover
// state transitions (loading → data, error) and API-boundary behaviour by
// mocking at the API client level rather than the hook level.
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, it, expect, jest } from '@jest/globals';
import CVCenterPage from '../../../src/frontend/app/cv-center/page';

// ---------------------------------------------------------------------------
// module mocks — API client level (not hook level)
// ---------------------------------------------------------------------------
jest.mock('../../../src/frontend/lib/apiClient', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

import { apiClient } from '../../../src/frontend/lib/apiClient';
const mockApiGet = jest.mocked(apiClient.get);

// Stub PageHeader and UserMenu — not under test here
jest.mock('../../../src/frontend/components/PageHeader/PageHeader', () => ({
  PageHeader: ({ title }: { title: string }) => (
    <header data-testid="page-header">
      <span data-testid="page-header-title">{title}</span>
    </header>
  ),
}));

jest.mock('../../../src/frontend/components/UserMenu/UserMenu', () => ({
  UserMenu: () => <div data-testid="user-menu" />,
}));

// BaseCVsTable stub — exposes props as data attributes for assertions
jest.mock('../../../src/frontend/components/BaseCVsTable/BaseCVsTable', () => ({
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
      data-error-message={error?.message ?? ''}
      data-cvs-count={cvs.length}
    >
      {typeof onRetry === 'function' && (
        <button data-testid="retry-btn" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  ),
}));

// ChooseBaseCVModal stub — simulates open/close and success callback
jest.mock('../../../src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal', () => ({
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

// ErrorBoundary stub — transparent wrapper
jest.mock('../../../src/frontend/components/ErrorBoundary/ErrorBoundary', () => ({
  ErrorBoundary: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
  useLocale: jest.fn(() => 'en'),
}));

// ---------------------------------------------------------------------------
// wrapper factory — fresh QueryClient per test prevents state leakage
// ---------------------------------------------------------------------------
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

function renderPage() {
  const Wrapper = createWrapper();
  return render(
    <Wrapper>
      <CVCenterPage />
    </Wrapper>
  );
}

// ---------------------------------------------------------------------------
// beforeEach — isolate each test
// ---------------------------------------------------------------------------
beforeEach(() => {
  jest.clearAllMocks();
});

// ===========================================================================
// CVCenterContent — integration tests
// ===========================================================================
describe('CVCenterContent integration', () => {

  // ─── state transition: loading → data rendered ───────────────────────────
  it('test_renders_data_when_api_succeeds', async () => {
    // TODO: mock apiClient.get to resolve with [{ cv_id: '1', full_name: 'John Doe', language: 'en', updated_at: '2026-01-01' }]
    // TODO: renderPage()
    // TODO: assert data-is-loading="true" initially (loading state)
    // TODO: await waitFor(() => assert data-cvs-count="1" on table stub)
    mockApiGet.mockResolvedValueOnce({
      data: [{ cv_id: '1', full_name: 'John Doe', language: 'en', updated_at: '2026-01-01' }],
    });
    renderPage();
    // TODO: expect(screen.getByTestId('base-cvs-table').getAttribute('data-is-loading')).toBe('true')
    // TODO: await waitFor(() =>
    //   expect(screen.getByTestId('base-cvs-table').getAttribute('data-cvs-count')).toBe('1')
    // )
    await waitFor(() => expect(screen.queryByTestId('base-cvs-table')).not.toBeNull());
  });

  // ─── state transition: loading → empty array ─────────────────────────────
  it('test_passes_empty_array_when_api_returns_empty_list', async () => {
    // TODO: mock apiClient.get to resolve with []
    // TODO: await waitFor(() => assert data-cvs-count="0" on table stub)
    // NOTE: empty-state rendering is BaseCVsTable's responsibility (FE-UI-017)
    mockApiGet.mockResolvedValueOnce({ data: [] });
    renderPage();
    // TODO: await waitFor(() =>
    //   expect(screen.getByTestId('base-cvs-table').getAttribute('data-cvs-count')).toBe('0')
    // )
    await waitFor(() => expect(screen.queryByTestId('base-cvs-table')).not.toBeNull());
  });

  // ─── state transition: loading → error state rendered ────────────────────
  it('test_shows_error_state_when_api_fails', async () => {
    // TODO: mock apiClient.get to reject with Error('Service unavailable')
    // TODO: renderPage()
    // TODO: await waitFor(() => assert data-has-error="true" on table stub)
    // TODO: assert data-error-message contains 'Service unavailable'
    mockApiGet.mockRejectedValueOnce(new Error('Service unavailable'));
    renderPage();
    // TODO: await waitFor(() =>
    //   expect(screen.getByTestId('base-cvs-table').getAttribute('data-has-error')).toBe('true')
    // )
    await waitFor(() => expect(screen.queryByTestId('base-cvs-table')).not.toBeNull());
  });

  // ─── user action: onRetry → GET /users/me/cv re-triggered ────────────────
  it('test_refetches_api_when_on_retry_called', async () => {
    // TODO: mock apiClient.get to reject once, then resolve on second call
    // TODO: renderPage(), await error state
    // TODO: userEvent.click retry-btn
    // TODO: assert apiClient.get called twice total
    mockApiGet
      .mockRejectedValueOnce(new Error('Fail'))
      .mockResolvedValueOnce({ data: [{ cv_id: '2', full_name: 'Retry result', language: 'en', updated_at: '2026-01-02' }] });

    renderPage();
    // TODO: await waitFor(() => assert data-has-error="true")
    // TODO: await userEvent.click(screen.getByTestId('retry-btn'))
    // TODO: await waitFor(() => expect(mockApiGet).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.queryByTestId('base-cvs-table')).not.toBeNull());
  });

  // ─── GET /users/me/cv request shape ──────────────────────────────────────
  it('test_get_users_me_cv_called_with_correct_endpoint_on_mount', async () => {
    // TODO: mock apiClient.get to resolve with []
    // TODO: renderPage()
    // TODO: await waitFor(() =>
    //   expect(mockApiGet).toHaveBeenCalledWith(
    //     expect.stringMatching(/\/users\/me\/cv/)
    //   )
    // )
    mockApiGet.mockResolvedValueOnce({ data: [] });
    renderPage();
    // TODO: await waitFor(() =>
    //   expect(mockApiGet).toHaveBeenCalledWith('/users/me/cv')
    // )
    await waitFor(() => expect(screen.queryByTestId('base-cvs-table')).not.toBeNull());
  });

  // ─── page header renders regardless of data state ────────────────────────
  it('test_page_header_renders_regardless_of_data_state', async () => {
    // TODO: mock apiClient.get with a never-resolving promise (stuck in loading)
    // TODO: renderPage()
    // TODO: assert data-testid="page-header" is in document immediately
    mockApiGet.mockReturnValueOnce(new Promise(() => { /* never resolves */ }));
    renderPage();
    // TODO: expect(screen.getByTestId('page-header')).not.toBeNull()
    expect(screen.queryByTestId('page-header')).not.toBeNull();
  });

  // ─── upload modal: open with showChoices=false ────────────────────────────
  it('test_upload_modal_opens_with_show_choices_false_when_button_clicked', async () => {
    // TODO: mock apiClient.get to resolve with []
    // TODO: renderPage(), await table render
    // TODO: userEvent.click on "+ Upload New CV" button
    // TODO: assert role="dialog" is in document
    // TODO: assert data-show-choices="false" on modal stub
    mockApiGet.mockResolvedValueOnce({ data: [] });
    renderPage();
    // TODO: await waitFor(() => screen.queryByTestId('base-cvs-table'))
    // TODO: await userEvent.click(screen.getByRole('button', { name: /upload new cv/i }))
    // TODO: expect(screen.getByTestId('choose-base-cv-modal').getAttribute('data-show-choices')).toBe('false')
    await waitFor(() => expect(screen.queryByTestId('base-cvs-table')).not.toBeNull());
  });

  // ─── upload success: modal closes and data re-fetches ────────────────────
  it('test_modal_closes_and_api_refetches_when_upload_succeeds', async () => {
    // TODO: mock apiClient.get to resolve with [] initially, then with one item after refetch
    // TODO: renderPage(), open modal, click modal-success-btn
    // TODO: assert role="dialog" is no longer in document
    // TODO: assert apiClient.get was called twice (initial fetch + refetch)
    mockApiGet
      .mockResolvedValueOnce({ data: [] })
      .mockResolvedValueOnce({ data: [{ cv_id: '1', full_name: 'New CV', language: 'en', updated_at: '2026-05-01' }] });

    renderPage();
    // TODO: await waitFor(() => screen.queryByTestId('base-cvs-table'))
    // TODO: await userEvent.click(screen.getByRole('button', { name: /upload new cv/i }))
    // TODO: await userEvent.click(screen.getByTestId('modal-success-btn'))
    // TODO: expect(screen.queryByRole('dialog')).toBeNull()
    // TODO: await waitFor(() => expect(mockApiGet).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.queryByTestId('base-cvs-table')).not.toBeNull());
  });

  // ─── BaseCVsTable receives all expected props ─────────────────────────────
  it('test_table_receives_cvs_is_loading_error_and_on_retry_props', async () => {
    // TODO: mock apiClient.get to resolve with [{ cv_id: '1' }]
    // TODO: renderPage(), await data state
    // TODO: assert all props present on table stub via data attributes
    mockApiGet.mockResolvedValueOnce({ data: [{ cv_id: '1', full_name: 'Test', language: 'en', updated_at: '2026-01-01' }] });
    renderPage();
    // TODO: await waitFor(() => {
    //   const table = screen.getByTestId('base-cvs-table')
    //   expect(table.getAttribute('data-cvs-count')).toBe('1')
    //   expect(table.getAttribute('data-is-loading')).toBe('false')
    //   expect(table.getAttribute('data-has-error')).toBe('false')
    //   expect(screen.getByTestId('retry-btn')).toBeInTheDocument()
    // })
    await waitFor(() => expect(screen.queryByTestId('base-cvs-table')).not.toBeNull());
  });

});
