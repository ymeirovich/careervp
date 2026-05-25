// spec_id: FE-UI-015  component: TailoredCVsListTable  tier: integration
// file: src/frontend/components/TailoredCVsListTable/TailoredCVsListTable.tsx
// Framework: Jest + @testing-library/react
// Covers state transitions and API-level integration within page context.
// Note: all 28 ACs are verification_type: unit. These tests validate the
// component mounted inside a QueryClientProvider, mocking at the API client
// level rather than the hook level.

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TailoredCVsListTable } from '../../../src/frontend/components/TailoredCVsListTable/TailoredCVsListTable';

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

const FIXTURE_API_RESPONSE = [
  {
    id: 'cv-1',
    applicationId: 'app-1',
    title: 'Senior_Engineer_cv.pdf',
    language: 'English',
    lastUpdated: '2026-05-20T10:00:00Z',
    status: 'ready' as const,
  },
  {
    id: 'cv-2',
    applicationId: 'app-2',
    title: 'Product_Manager_cv.pdf',
    language: 'Hebrew',
    lastUpdated: '2026-05-15T09:00:00Z',
    status: 'processing' as const,
  },
];

// ---------------------------------------------------------------------------
// Provider wrapper
// ---------------------------------------------------------------------------

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

// ---------------------------------------------------------------------------
// API client mock
// ---------------------------------------------------------------------------

// TODO: import the API client module used by the component's data hook
// vi.mock('../../../src/frontend/lib/api/tailoredCvsApi', () => ({
//   getTailoredCvs: vi.fn(),
// }));
// import { getTailoredCvs } from '../../../src/frontend/lib/api/tailoredCvsApi';
// const mockGetTailoredCvs = vi.mocked(getTailoredCvs);

// ===========================================================================
// TailoredCVsListTable integration
// ===========================================================================

describe('TailoredCVsListTable integration', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ─── state transition: loading → data rendered ───────────────────────────

  it('test_renders_data_when_api_succeeds', async () => {
    // TODO: mock API client to resolve with FIXTURE_API_RESPONSE
    // TODO: render component with createWrapper()
    // TODO: await waitFor(() => screen.getByText('Senior_Engineer_cv.pdf'))
    // TODO: assert all fixture rows are visible
  });

  it('test_loading_state_shown_before_api_resolves', async () => {
    // TODO: mock API client to delay resolution (e.g. never-resolving promise)
    // TODO: render component with createWrapper()
    // TODO: assert 3 skeleton rows are visible immediately
    // TODO: assert real data rows are absent
  });

  it('test_loading_state_disappears_after_api_resolves', async () => {
    // TODO: mock API client to resolve with FIXTURE_API_RESPONSE after 50ms
    // TODO: render with createWrapper()
    // TODO: assert skeleton rows appear first
    // TODO: await waitFor(() => expect(screen.queryAllByTestId('skeleton-row')).toHaveLength(0))
    // TODO: assert real data rows are visible
  });

  // ─── state transition: API error → error state rendered ──────────────────

  it('test_shows_error_state_when_api_fails', async () => {
    // TODO: mock API client to reject with new Error('Network error')
    // TODO: render with createWrapper()
    // TODO: await waitFor(() => screen.getByRole('button', { name: /retry/i }))
    // TODO: assert error message is visible
  });

  it('test_shows_retry_button_inside_table_card_when_api_fails', async () => {
    // TODO: mock API client to reject
    // TODO: render with createWrapper()
    // TODO: await error state
    // TODO: assert retry button is present inside the table card container
  });

  // ─── user action → API call triggered → UI updates ───────────────────────

  it('test_clicking_retry_triggers_api_refetch_when_in_error_state', async () => {
    // TODO: mock API client to reject on first call, resolve on second call
    // TODO: render with createWrapper()
    // TODO: await error state
    // TODO: fireEvent.click on Retry button
    // TODO: await waitFor(() => expect(mockGetTailoredCvs).toHaveBeenCalledTimes(2))
    // TODO: assert data rows appear after successful retry
  });

  it('test_data_rows_appear_after_successful_retry_when_first_call_failed', async () => {
    // TODO: mock API client: first call rejects, second call resolves with FIXTURE_API_RESPONSE
    // TODO: render, await error, click Retry
    // TODO: await waitFor(() => screen.getByText('Senior_Engineer_cv.pdf'))
  });

  // ─── empty state transition ───────────────────────────────────────────────

  it('test_shows_empty_state_when_api_returns_empty_array', async () => {
    // TODO: mock API client to resolve with []
    // TODO: render with createWrapper()
    // TODO: await waitFor(() => screen.getByText(/no tailored cvs yet/i))
  });

  it('test_empty_state_cta_link_present_when_api_returns_empty_array', async () => {
    // TODO: mock API client to resolve with []
    // TODO: render with createWrapper()
    // TODO: await empty state
    // TODO: assert link to /applications is visible
  });

  // ─── search interaction within page context ───────────────────────────────

  it('test_search_filters_rows_after_data_loads_when_user_types_query', async () => {
    // TODO: mock API client to resolve with FIXTURE_API_RESPONSE
    // TODO: render with createWrapper()
    // TODO: await data rows visible
    // TODO: fireEvent.change on search input with value 'Hebrew'
    // TODO: assert only the Hebrew-language row remains visible
  });

  // ─── sort interaction within page context ─────────────────────────────────

  it('test_clicking_column_header_re_orders_rows_when_data_is_loaded', async () => {
    // TODO: mock API client to resolve with FIXTURE_API_RESPONSE
    // TODO: render with createWrapper()
    // TODO: await data rows visible
    // TODO: fireEvent.click on Title column header
    // TODO: assert rows reorder alphabetically by title ascending
  });

});
