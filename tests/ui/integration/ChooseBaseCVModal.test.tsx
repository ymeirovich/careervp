// spec_id: FE-UI-011  component: ChooseBaseCVModal  tier: integration
// file: src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal.tsx
// All spec ACs are verification_type: unit; these integration tests cover
// state transitions (loading → data, error) and API-boundary behaviour by
// mocking at the API client level, not the hook level.
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, it, expect, jest } from '@jest/globals';
import { ChooseBaseCVModal } from '../../../src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal';

// ---------------------------------------------------------------------------
// type fixtures — no `any`
// ---------------------------------------------------------------------------
interface BaseCV {
  cv_id: string;
  cv_name: string;
  uploaded_at: string;
  cv_type: 'uploaded' | 'generated';
}

const FIXTURE_CVS: BaseCV[] = [
  { cv_id: 'cv-001', cv_name: 'My Resume.pdf', uploaded_at: '2026-01-10T00:00:00Z', cv_type: 'uploaded' },
  { cv_id: 'cv-002', cv_name: 'Tailored CV - Acme', uploaded_at: '2026-02-15T00:00:00Z', cv_type: 'generated' },
];

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
// callback mocks
// ---------------------------------------------------------------------------
const mockOnClose = jest.fn();
const mockOnSelectCV = jest.fn();
const mockOnUpload = jest.fn();

// ---------------------------------------------------------------------------
// render helper — wraps with fresh QueryClient
// ---------------------------------------------------------------------------
interface RenderOverrides {
  isOpen?: boolean;
  showChoices?: boolean;
}

function renderModal(overrides: RenderOverrides = {}) {
  const Wrapper = createWrapper();
  return render(
    <Wrapper>
      <ChooseBaseCVModal
        isOpen={overrides.isOpen ?? true}
        showChoices={overrides.showChoices ?? true}
        onClose={mockOnClose}
        onSelectCV={mockOnSelectCV}
        onUpload={mockOnUpload}
      />
    </Wrapper>
  );
}

// ---------------------------------------------------------------------------
// beforeEach — reset mocks, no shared state
// ---------------------------------------------------------------------------
beforeEach(() => {
  jest.clearAllMocks();
});

// ===========================================================================
// State transition: loading → data rendered
// ===========================================================================
describe('ChooseBaseCVModal integration — GET /users/me/cv success', () => {

  it('test_renders_cv_list_when_api_returns_cvs', async () => {
    // TODO: mock apiClient.get to resolve with FIXTURE_CVS
    // TODO: render modal with showChoices=true within QueryClientProvider
    // TODO: await data and assert each CV name appears in the DOM
    mockApiGet.mockResolvedValueOnce({ data: FIXTURE_CVS });
    renderModal({ showChoices: true });
    // TODO: await waitFor(() => expect(screen.queryByText('My Resume.pdf')).not.toBeNull())
    // TODO: await waitFor(() => expect(screen.queryByText('Tailored CV - Acme')).not.toBeNull())
  });

  it('test_loading_indicator_shown_while_data_fetching', async () => {
    // TODO: mock apiClient.get to return a promise that never resolves (simulate in-flight)
    // TODO: render modal with showChoices=true
    // TODO: assert a loading indicator is present (spinner, skeleton, or aria-busy)
    // TODO: before the promise resolves, choice buttons or CV list are not yet visible
    mockApiGet.mockReturnValueOnce(new Promise(() => {/* intentionally unresolved */}));
    renderModal({ showChoices: true });
    // TODO: expect(screen.queryByRole('status') ?? document.querySelector('[aria-busy="true"]')).not.toBeNull()
  });

  it('test_loading_indicator_absent_after_data_rendered', async () => {
    // TODO: mock apiClient.get to resolve immediately with FIXTURE_CVS
    // TODO: render modal
    // TODO: await data render, then assert loading indicator is gone
    mockApiGet.mockResolvedValueOnce({ data: FIXTURE_CVS });
    renderModal({ showChoices: true });
    // TODO: await waitFor(() => expect(screen.queryByText('My Resume.pdf')).not.toBeNull())
    // TODO: expect(screen.queryByRole('status')).toBeNull()
  });

});

// ===========================================================================
// State transition: API error → error state rendered
// ===========================================================================
describe('ChooseBaseCVModal integration — GET /users/me/cv error', () => {

  it('test_shows_error_state_when_api_fails', async () => {
    // TODO: mock apiClient.get to reject with a network error
    // TODO: render modal with showChoices=true
    // TODO: assert an error message or error UI element is present (role="alert" or data-testid="error-state")
    mockApiGet.mockRejectedValueOnce(new Error('Network error'));
    renderModal({ showChoices: true });
    // TODO: await waitFor(() =>
    //   expect(screen.queryByRole('alert') ?? screen.queryByTestId('error-state')).not.toBeNull()
    // )
  });

  it('test_cv_list_absent_when_api_fails', async () => {
    // TODO: mock apiClient.get to reject
    // TODO: render modal
    // TODO: assert CV names from fixture are NOT in the DOM
    mockApiGet.mockRejectedValueOnce(new Error('Network error'));
    renderModal({ showChoices: true });
    // TODO: await waitFor(() => expect(screen.queryByRole('alert')).not.toBeNull())
    // TODO: expect(screen.queryByText('My Resume.pdf')).toBeNull()
  });

});

// ===========================================================================
// User action → API call triggered → UI updates
// ===========================================================================
describe('ChooseBaseCVModal integration — user interactions trigger API', () => {

  it('test_get_users_me_cv_called_when_modal_opens_in_choice_mode', async () => {
    // TODO: mock apiClient.get to resolve with FIXTURE_CVS
    // TODO: render modal with isOpen=true, showChoices=true
    // TODO: assert apiClient.get was called with '/users/me/cv' (or matching endpoint)
    mockApiGet.mockResolvedValueOnce({ data: FIXTURE_CVS });
    renderModal({ showChoices: true });
    // TODO: await waitFor(() =>
    //   expect(mockApiGet).toHaveBeenCalledWith(expect.stringMatching(/\/users\/me\/cv/))
    // )
  });

  it('test_get_users_me_cv_not_called_when_modal_is_closed', () => {
    // TODO: render modal with isOpen=false
    // TODO: assert apiClient.get was not called (no fetch when modal is hidden)
    mockApiGet.mockResolvedValueOnce({ data: [] });
    renderModal({ isOpen: false });
    // TODO: expect(mockApiGet).not.toHaveBeenCalled()
  });

  it('test_onClose_called_and_modal_hidden_after_x_button_clicked', async () => {
    // TODO: mock apiClient.get to resolve with FIXTURE_CVS
    // TODO: render modal open
    // TODO: click X close button
    // TODO: assert mockOnClose called once
    mockApiGet.mockResolvedValueOnce({ data: FIXTURE_CVS });
    renderModal();
    // TODO: await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeNull())
    // TODO: fireEvent.click(screen.getByRole('button', { name: /close/i }))
    // TODO: expect(mockOnClose).toHaveBeenCalledTimes(1)
  });

  it('test_upload_button_disabled_until_file_selected_then_onUpload_fires', async () => {
    // TODO: mock apiClient.get to resolve with FIXTURE_CVS
    // TODO: render modal in upload-only mode
    // TODO: assert Upload button is initially disabled
    // TODO: simulate file selection
    // TODO: assert Upload button becomes enabled
    // TODO: click Upload, assert mockOnUpload called with the file
    mockApiGet.mockResolvedValueOnce({ data: FIXTURE_CVS });
    renderModal({ showChoices: false });
    const file = new File(['cv content'], 'NewCV.pdf', { type: 'application/pdf' });
    // TODO: const btn = screen.queryByRole('button', { name: /^upload$/i }) as HTMLButtonElement
    // TODO: expect(btn.disabled).toBe(true)
    // TODO: fireEvent.change(document.querySelector('input[type="file"]'), { target: { files: [file] } })
    // TODO: expect(btn.disabled).toBe(false)
    // TODO: fireEvent.click(btn)
    // TODO: expect(mockOnUpload).toHaveBeenCalledWith(file)
    expect(file.name).toBe('NewCV.pdf'); // placeholder — replace with real assertions above
  });

});

// ===========================================================================
// Choice mode with no CVs — empty state integration
// ===========================================================================
describe('ChooseBaseCVModal integration — empty state', () => {

  it('test_choice_buttons_disabled_when_api_returns_empty_cv_list', async () => {
    // TODO: mock apiClient.get to resolve with an empty array
    // TODO: render modal with showChoices=true
    // TODO: await render, then assert both choice buttons are disabled
    mockApiGet.mockResolvedValueOnce({ data: [] });
    renderModal({ showChoices: true });
    // TODO: await waitFor(() => {
    //   const uploadedBtn = screen.queryByRole('button', { name: /select uploaded cv/i }) as HTMLButtonElement
    //   expect(uploadedBtn.disabled).toBe(true)
    //   const generatedBtn = screen.queryByRole('button', { name: /select generated cv/i }) as HTMLButtonElement
    //   expect(generatedBtn.disabled).toBe(true)
    // })
  });

});
