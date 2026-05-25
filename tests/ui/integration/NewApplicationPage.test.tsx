// spec_id: FE-UI-010  component: NewApplicationPage  tier: integration
// file: src/frontend/app/applications/new/page.tsx
// All ACs are verification_type: unit in the spec; these integration tests
// cover state transitions (loading → data, error) and API-boundary behaviour
// by mocking at the API client level rather than the hook level.
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, it, expect, jest } from '@jest/globals';
import NewApplicationPage from '../../../src/frontend/app/applications/new/page';

// ---------------------------------------------------------------------------
// module mocks — API client level (not hook level)
// ---------------------------------------------------------------------------
const mockPush = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
}));

// Mock the API client that useJobs calls internally — not useJobs itself
jest.mock('../../../src/frontend/lib/apiClient', () => ({
  apiClient: {
    post: jest.fn(),
  },
}));

import { apiClient } from '../../../src/frontend/lib/apiClient';
const mockApiPost = jest.mocked(apiClient.post);

jest.mock('../../../src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal', () => ({
  ChooseBaseCVModal: ({ isOpen }: { isOpen: boolean }) =>
    isOpen ? <div role="dialog" aria-label="Choose Base CV" /> : null,
}));

// i18n stub
jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
  useLocale: jest.fn(() => 'en'),
}));

// ---------------------------------------------------------------------------
// wrapper factory — fresh QueryClient per test prevents state leakage
// ---------------------------------------------------------------------------
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------
function renderPage() {
  const Wrapper = createWrapper();
  return render(
    <Wrapper>
      <NewApplicationPage />
    </Wrapper>
  );
}

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText(/job title/i), { target: { value: 'Software Engineer' } });
  fireEvent.change(screen.getByLabelText(/company name/i), { target: { value: 'Acme Corp' } });
  fireEvent.change(screen.getByLabelText(/job description/i), { target: { value: 'Build things.' } });
}

// ---------------------------------------------------------------------------
// beforeEach — isolate each test
// ---------------------------------------------------------------------------
beforeEach(() => {
  jest.clearAllMocks();
});

// ===========================================================================
// NewApplicationPage — integration tests
// ===========================================================================
describe('NewApplicationPage integration', () => {

  // ─── state transition: default → loading → success ───────────────────────
  it('test_renders_data_when_api_succeeds', async () => {
    // TODO: mock apiClient.post to resolve with { job_id: 'abc-123' }
    // TODO: renderPage(), fill required fields, click Create Application
    // TODO: assert loading state ("Creating..." button text) appears while in flight
    // TODO: await waitFor(() => assert mockPush('/applications/abc-123') called)
    mockApiPost.mockResolvedValueOnce({ data: { job_id: 'abc-123' } });
    renderPage();
    fillRequiredFields();
    // TODO: fireEvent.click(screen.getByRole('button', { name: /create application/i }))
    // TODO: await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/applications/abc-123'))
  });

  // ─── state transition: default → loading → error ─────────────────────────
  it('test_shows_error_state_when_api_fails', async () => {
    // TODO: mock apiClient.post to reject with Error('Server unavailable')
    // TODO: renderPage(), fill required fields, click Create Application
    // TODO: await waitFor(() => assert role="alert" exists with 'Server unavailable' text)
    mockApiPost.mockRejectedValueOnce(new Error('Server unavailable'));
    renderPage();
    fillRequiredFields();
    // TODO: fireEvent.click(screen.getByRole('button', { name: /create application/i }))
    // TODO: await waitFor(() => expect(screen.getByRole('alert')).toBeVisible())
  });

  // ─── state transition: error → field edit → error banner dismissed ────────
  it('test_error_banner_dismissed_when_field_edited_after_api_failure', async () => {
    // TODO: drive page into error state (submit → reject)
    // TODO: fireEvent.change any field to a new value
    // TODO: assert role="alert" no longer in document
    mockApiPost.mockRejectedValueOnce(new Error('Oops'));
    renderPage();
    fillRequiredFields();
    // TODO: submit, await error, then edit, assert banner gone
  });

  // ─── loading state: inputs disabled during submission ─────────────────────
  it('test_inputs_and_cancel_disabled_during_submission', async () => {
    // TODO: mock apiClient.post to return a never-resolving promise (in-flight)
    // TODO: renderPage(), fill required fields, click Create Application
    // TODO: without awaiting, assert job title, company name, job description, job url
    //       and Cancel button are all disabled
    mockApiPost.mockReturnValueOnce(new Promise(() => { /* never resolves */ }));
    renderPage();
    fillRequiredFields();
    // TODO: click submit
    // TODO: assert each input: (el as HTMLInputElement).disabled === true
    // TODO: assert Cancel button disabled
  });

  // ─── user action: Cancel → no API call, navigate to /dashboard ────────────
  it('test_cancel_does_not_call_api_and_navigates_to_dashboard', () => {
    // TODO: renderPage()
    // TODO: fill some fields (but do NOT submit)
    // TODO: fireEvent.click Cancel button
    // TODO: assert mockApiPost.mock.calls.length === 0
    // TODO: assert mockPush called with '/dashboard'
    renderPage();
    const cancelBtn = screen.queryByRole('button', { name: /^cancel$/i });
    if (cancelBtn) fireEvent.click(cancelBtn);
    // TODO: expect(mockApiPost).not.toHaveBeenCalled()
    // TODO: expect(mockPush).toHaveBeenCalledWith('/dashboard')
  });

  // ─── user action: Change button → ChooseBaseCVModal opens ─────────────────
  it('test_choose_base_cv_modal_opens_when_change_clicked', () => {
    // TODO: renderPage()
    // TODO: fireEvent.click the "Change" button in Base CV section
    // TODO: assert role="dialog" with label "Choose Base CV" is in document
    renderPage();
    const changeBtn = screen.queryByRole('button', { name: /^change$/i });
    if (changeBtn) fireEvent.click(changeBtn);
    // TODO: expect(screen.getByRole('dialog', { name: /choose base cv/i })).toBeInTheDocument()
  });

  // ─── POST /jobs request body shape ────────────────────────────────────────
  it('test_post_jobs_called_with_correct_request_body_shape', async () => {
    // TODO: mock apiClient.post to resolve
    // TODO: renderPage(), fill all fields including optional URL, submit
    // TODO: assert apiClient.post was called with endpoint '/jobs' and body:
    //       { title: '...', company_name: '...', description: '...', url: '...' }
    //       (url field present only when filled — omitted or undefined when empty)
    mockApiPost.mockResolvedValueOnce({ data: { job_id: 'xyz' } });
    renderPage();
    fillRequiredFields();
    fireEvent.change(screen.getByLabelText(/job url/i), { target: { value: 'https://example.com/job' } });
    // TODO: click submit
    // TODO: await waitFor(() => expect(mockApiPost).toHaveBeenCalledWith(
    //   '/jobs',
    //   expect.objectContaining({
    //     title: 'Software Engineer',
    //     company_name: 'Acme Corp',
    //     description: 'Build things.',
    //     url: 'https://example.com/job',
    //   })
    // ))
  });

  // ─── POST /jobs omits url when field is empty ─────────────────────────────
  it('test_post_jobs_omits_url_when_job_url_field_is_empty', async () => {
    // TODO: mock apiClient.post to resolve, renderPage(), fill only required fields
    // TODO: assert apiClient.post body does not contain url key (or url is undefined)
    mockApiPost.mockResolvedValueOnce({ data: { job_id: 'xyz' } });
    renderPage();
    fillRequiredFields();
    // TODO: click submit, await, assert url absent from call args
  });

  // ─── Back link navigates to /dashboard without API call ───────────────────
  it('test_back_link_navigates_to_dashboard_without_api_call', () => {
    // TODO: renderPage()
    // TODO: fireEvent.click back link
    // TODO: assert mockApiPost not called
    // TODO: assert mockPush('/dashboard') called
    renderPage();
    const backLink = screen.queryByRole('link', { name: /back/i })
      ?? screen.queryByText(/← back/i);
    if (backLink) fireEvent.click(backLink);
    // TODO: expect(mockApiPost).not.toHaveBeenCalled()
    // TODO: expect(mockPush).toHaveBeenCalledWith('/dashboard')
  });

  // ─── AC-022 integration: RTL direction when locale is Hebrew ─────────────
  it('test_layout_direction_rtl_when_locale_he_within_provider_tree', () => {
    // TODO: override locale mock to return 'he'
    // TODO: renderPage() within wrapper
    // TODO: assert root element or document dir attribute is 'rtl'
    renderPage();
    // TODO: set locale = 'he', re-render, assert dir="rtl"
  });

});
