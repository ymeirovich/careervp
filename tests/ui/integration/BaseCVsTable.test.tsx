// spec_id: FE-UI-017  component: BaseCVsTable  tier: integration
// file: src/frontend/components/BaseCVsTable/BaseCVsTable.tsx
// Framework: Jest + @testing-library/react
// Covers state transitions and API-level integration within page context.
// Note: all 31 ACs are verification_type: unit. These tests validate the
// component mounted inside a QueryClientProvider, mocking at the API client
// level rather than the hook level.

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BaseCVsTable } from '../../../src/frontend/components/BaseCVsTable/BaseCVsTable';

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------

const FIXTURE_API_RESPONSE = [
  {
    id: 'cv-1',
    full_name: 'John Doe',
    language: 'English',
    created_at: '2026-05-20T10:00:00Z',
    updated_at: '2026-05-20T10:00:00Z',
    status: 'ready' as const,
    used_in: 3,
  },
  {
    id: 'cv-2',
    full_name: 'Jane Smith',
    language: 'Hebrew',
    created_at: '2026-05-15T09:00:00Z',
    updated_at: '2026-05-15T09:00:00Z',
    status: 'processing' as const,
    used_in: 1,
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
// vi.mock('../../../src/frontend/lib/api/baseCvsApi', () => ({
//   getBaseCvs: vi.fn(),
// }));
// import { getBaseCvs } from '../../../src/frontend/lib/api/baseCvsApi';
// const mockGetBaseCvs = vi.mocked(getBaseCvs);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('BaseCVsTable integration', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ─── State transition: loading → data rendered ────────────────────────────

  it('test_renders_data_when_api_succeeds', async () => {
    // TODO: mock API client to resolve with FIXTURE_API_RESPONSE
    // TODO: render <BaseCVsTable> in a configuration that triggers data fetch,
    //       wrapped with createWrapper()
    // TODO: await data rendering (waitFor(() => screen.getByText('John Doe')))
    // TODO: assert both rows are visible in the table
  });

  it('test_shows_loading_skeleton_before_api_resolves', async () => {
    // TODO: mock API client with a promise that does not resolve immediately
    // TODO: render component inside wrapper
    // TODO: assert 3 skeleton rows are present before data arrives
    // TODO: assert real data rows are NOT yet visible
  });

  it('test_transitions_from_loading_to_data_when_api_resolves', async () => {
    // TODO: mock API client with a delayed resolve returning FIXTURE_API_RESPONSE
    // TODO: render component inside wrapper
    // TODO: assert skeleton rows present initially
    // TODO: await API resolution
    // TODO: assert skeleton rows gone and data rows visible
  });

  // ─── State transition: API error → error state rendered ──────────────────

  it('test_shows_error_state_when_api_fails', async () => {
    // TODO: mock API client to reject with new Error('Network error')
    // TODO: render component inside wrapper
    // TODO: await waitFor(() => screen.getByRole('button', { name: /retry/i }))
    // TODO: assert inline error message is visible
    // TODO: assert Retry button is visible
  });

  it('test_transitions_from_loading_to_error_when_api_rejects', async () => {
    // TODO: mock API client with a delayed rejection
    // TODO: render and assert skeleton rows initially
    // TODO: await rejection
    // TODO: assert skeleton rows gone and error state rendered
  });

  // ─── User action → API call triggered → UI updates ───────────────────────

  it('test_retry_button_click_triggers_new_api_call_when_in_error_state', async () => {
    // TODO: mock API client to fail on first call, succeed on second
    // TODO: render and await error state
    // TODO: fireEvent.click on Retry button
    // TODO: assert API client was called twice
    // TODO: await data render and assert rows visible
  });

  it('test_on_set_default_prop_receives_correct_cv_id_when_called_from_page_context', async () => {
    // TODO: mock API client to resolve with FIXTURE_API_RESPONSE
    // TODO: render <BaseCVsTable> with onSetDefault spy prop inside wrapper
    // TODO: await data load
    // TODO: fireEvent.click on "Set as Default" for first row
    // TODO: assert onSetDefault spy called with 'cv-1'
  });

  it('test_on_delete_prop_receives_correct_cv_id_when_called_from_page_context', async () => {
    // TODO: mock API client to resolve with FIXTURE_API_RESPONSE
    // TODO: render with onDelete spy prop inside wrapper
    // TODO: await data load
    // TODO: fireEvent.click on "Delete" for second row
    // TODO: assert onDelete spy called with 'cv-2'
  });

  // ─── Empty state in page context ─────────────────────────────────────────

  it('test_shows_empty_state_when_api_returns_empty_array', async () => {
    // TODO: mock API client to resolve with []
    // TODO: render inside wrapper
    // TODO: await waitFor(() => screen.getByText(/no primary cvs uploaded yet/i))
    // TODO: assert CTA button is visible
  });

  it('test_on_upload_new_prop_called_when_cta_clicked_in_empty_state', async () => {
    // TODO: mock API client to resolve with []
    // TODO: render with onUploadNew spy prop inside wrapper
    // TODO: await empty state
    // TODO: fireEvent.click on "+ Upload New CV" CTA
    // TODO: assert onUploadNew spy called once
  });

});
