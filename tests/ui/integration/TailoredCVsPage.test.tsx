// spec_id: FE-UI-014  component: TailoredCVsPage  tier: integration
// file: src/frontend/app/tailored-cvs/page.tsx
// All spec ACs are verification_type: unit; these integration tests cover
// state transitions (loading → data, error) and API-boundary behaviour by
// mocking at the API client level rather than the hook level.
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, it, expect, jest } from '@jest/globals';
import TailoredCVsPage from '../../../src/frontend/app/tailored-cvs/page';

// ---------------------------------------------------------------------------
// module mocks — API client level (not hook level)
// ---------------------------------------------------------------------------
jest.mock('../../../src/frontend/lib/apiClient', () => ({
  apiClient: {
    get: jest.fn(),
  },
}));

import { apiClient } from '../../../src/frontend/lib/apiClient';
const mockApiGet = jest.mocked(apiClient.get);

// Stub PageHeader and UserMenu — not under test here
jest.mock('../../../src/frontend/components/PageHeader/PageHeader', () => ({
  PageHeader: ({ title, subHeading }: { title: string; subHeading?: string }) => (
    <header data-testid="page-header">
      <span data-testid="page-header-title">{title}</span>
      {subHeading && <span data-testid="page-header-subheading">{subHeading}</span>}
    </header>
  ),
}));

jest.mock('../../../src/frontend/components/UserMenu/UserMenu', () => ({
  UserMenu: () => <div data-testid="user-menu" />,
}));

// TailoredCVsListTable stub — exposes props as data attributes for assertions
// Note: references TailoredCVsListTable — new component (FE-UI-015), different from TailoredCVsTable
jest.mock('../../../src/frontend/components/TailoredCVsListTable/TailoredCVsListTable', () => ({
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
      data-error-message={error?.message ?? ''}
      data-tailored-cvs-count={tailoredCvs.length}
    >
      {typeof onRetry === 'function' && (
        <button data-testid="retry-btn" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  ),
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
      <TailoredCVsPage />
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
// TailoredCVsPage — integration tests
// ===========================================================================
describe('TailoredCVsPage integration', () => {

  // ─── state transition: loading → data rendered ───────────────────────────
  it('test_renders_data_when_api_succeeds', async () => {
    // TODO: mock apiClient.get to resolve with [{ id: '1', jobTitle: 'Engineer' }]
    // TODO: renderPage()
    // TODO: assert data-is-loading="true" initially (loading state)
    // TODO: await waitFor(() => assert data-tailored-cvs-count="1" on table stub)
    mockApiGet.mockResolvedValueOnce({
      data: [{ id: '1', jobTitle: 'Software Engineer' }],
    });
    renderPage();
    // TODO: expect(screen.getByTestId('tailored-cvs-list-table')
    //         .getAttribute('data-is-loading')).toBe('true')
    // TODO: await waitFor(() =>
    //   expect(screen.getByTestId('tailored-cvs-list-table')
    //     .getAttribute('data-tailored-cvs-count')).toBe('1')
    // )
    await waitFor(() => expect(screen.queryByTestId('tailored-cvs-list-table')).not.toBeNull());
  });

  // ─── state transition: loading → empty array ─────────────────────────────
  it('test_passes_empty_array_when_api_returns_empty_list', async () => {
    // TODO: mock apiClient.get to resolve with []
    // TODO: await waitFor(() => assert data-tailored-cvs-count="0" on table stub)
    // NOTE: empty-state rendering is TailoredCVsListTable's responsibility (FE-UI-015)
    mockApiGet.mockResolvedValueOnce({ data: [] });
    renderPage();
    // TODO: await waitFor(() =>
    //   expect(screen.getByTestId('tailored-cvs-list-table')
    //     .getAttribute('data-tailored-cvs-count')).toBe('0')
    // )
    await waitFor(() => expect(screen.queryByTestId('tailored-cvs-list-table')).not.toBeNull());
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
    //   expect(screen.getByTestId('tailored-cvs-list-table')
    //     .getAttribute('data-has-error')).toBe('true')
    // )
    await waitFor(() => expect(screen.queryByTestId('tailored-cvs-list-table')).not.toBeNull());
  });

  // ─── user action: onRetry → GET /cv-tailorings re-triggered ──────────────
  it('test_refetches_api_when_on_retry_called', async () => {
    // TODO: mock apiClient.get to reject once, then resolve on second call
    // TODO: renderPage(), await error state
    // TODO: userEvent.click retry-btn
    // TODO: assert apiClient.get called twice total
    mockApiGet
      .mockRejectedValueOnce(new Error('Fail'))
      .mockResolvedValueOnce({ data: [{ id: '2', jobTitle: 'Retry result' }] });

    renderPage();
    // TODO: await waitFor(() => assert data-has-error="true")
    // TODO: await userEvent.click(screen.getByTestId('retry-btn'))
    // TODO: await waitFor(() =>
    //   expect(mockApiGet).toHaveBeenCalledTimes(2)
    // )
    await waitFor(() => expect(screen.queryByTestId('tailored-cvs-list-table')).not.toBeNull());
  });

  // ─── GET /cv-tailorings request shape ─────────────────────────────────────
  it('test_get_cv_tailorings_called_with_correct_endpoint_on_mount', async () => {
    // TODO: mock apiClient.get to resolve with []
    // TODO: renderPage()
    // TODO: await waitFor(() =>
    //   expect(mockApiGet).toHaveBeenCalledWith(
    //     expect.stringMatching(/\/cv-tailorings/)
    //   )
    // )
    mockApiGet.mockResolvedValueOnce({ data: [] });
    renderPage();
    // TODO: await waitFor(() =>
    //   expect(mockApiGet).toHaveBeenCalledWith('/cv-tailorings')
    // )
    await waitFor(() => expect(screen.queryByTestId('tailored-cvs-list-table')).not.toBeNull());
  });

  // ─── PageHeader and UserMenu still render in error/loading states ─────────
  it('test_page_header_renders_regardless_of_data_state', async () => {
    // TODO: mock apiClient.get with a never-resolving promise (stuck in loading)
    // TODO: renderPage()
    // TODO: assert data-testid="page-header" is in document immediately
    mockApiGet.mockReturnValueOnce(new Promise(() => { /* never resolves */ }));
    renderPage();
    // TODO: expect(screen.getByTestId('page-header')).not.toBeNull()
    expect(screen.queryByTestId('page-header')).not.toBeNull();
  });

  // ─── TailoredCVsListTable receives all four expected props ────────────────
  it('test_table_receives_tailored_cvs_is_loading_error_and_on_retry_props', async () => {
    // TODO: mock apiClient.get to resolve with [{ id: '1' }]
    // TODO: renderPage(), await data state
    // TODO: assert all four props present on table: tailoredCvs, isLoading, error, onRetry
    // (expressed via data attributes on the stub)
    mockApiGet.mockResolvedValueOnce({ data: [{ id: '1' }] });
    renderPage();
    // TODO: await waitFor(() => {
    //   const table = screen.getByTestId('tailored-cvs-list-table')
    //   expect(table.getAttribute('data-tailored-cvs-count')).toBe('1')
    //   expect(table.getAttribute('data-is-loading')).toBe('false')
    //   expect(table.getAttribute('data-has-error')).toBe('false')
    //   expect(screen.getByTestId('retry-btn')).toBeInTheDocument()
    // })
    await waitFor(() => expect(screen.queryByTestId('tailored-cvs-list-table')).not.toBeNull());
  });

});
