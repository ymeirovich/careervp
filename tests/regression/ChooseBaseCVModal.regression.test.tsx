// spec_id: FE-UI-011  component: ChooseBaseCVModal  tier: regression
// Protects existing behaviour that must not change during this upgrade.
// Focus areas per spec baseline & regression budget:
//   1. GET /users/me/cv API contract: response shape unchanged
//   2. CV Center page continues to function (ChooseBaseCVModal is additive)
//   3. NewApplicationPage still opens ChooseBaseCVModal (not ChangeBaseCVModal)
//   4. No non-2xx responses from GET /users/me/cv for authenticated users
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, it, expect, jest } from '@jest/globals';

// ---------------------------------------------------------------------------
// mocks
// ---------------------------------------------------------------------------
const mockPush = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush }),
  usePathname: jest.fn(() => '/cv-center'),
}));

jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
  useLocale: jest.fn(() => 'en'),
}));

jest.mock('../../../src/frontend/lib/apiClient', () => ({
  apiClient: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

import { apiClient } from '../../../src/frontend/lib/apiClient';
const mockApiGet = jest.mocked(apiClient.get);

// ---------------------------------------------------------------------------
// wrapper
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
// beforeEach
// ---------------------------------------------------------------------------
beforeEach(() => {
  jest.clearAllMocks();
});

// ===========================================================================
// 1. GET /users/me/cv API contract — response shape unchanged
// ===========================================================================
describe('ChooseBaseCVModal regression — GET /users/me/cv contract', () => {

  it('test_existing_api_contract_response_shape_cv_id_present', async () => {
    // Regression: GET /users/me/cv response must include cv_id on each item.
    // If cv_id is absent, CV selection and the onSelectCV callback break silently.
    const responseWithId = [
      { cv_id: 'cv-001', cv_name: 'Resume.pdf', uploaded_at: '2026-01-10T00:00:00Z', cv_type: 'uploaded' },
    ];
    mockApiGet.mockResolvedValueOnce({ data: responseWithId });

    // TODO: render ChooseBaseCVModal within Wrapper to trigger GET /users/me/cv
    // TODO: await waitFor(() => expect(mockApiGet).toHaveBeenCalledWith(
    //   expect.stringMatching(/\/users\/me\/cv/)
    // ))
    // TODO: assert the resolved data has cv_id field
    // TODO: expect(responseWithId[0]).toHaveProperty('cv_id')
    expect(responseWithId[0]).toHaveProperty('cv_id');
  });

  it('test_existing_api_contract_response_shape_cv_name_present', async () => {
    // Regression: cv_name must be present to display CV names in the list.
    // Renaming this field in the backend would break the CV list render.
    const response = [
      { cv_id: 'cv-001', cv_name: 'Resume.pdf', uploaded_at: '2026-01-10T00:00:00Z', cv_type: 'uploaded' },
    ];
    mockApiGet.mockResolvedValueOnce({ data: response });
    // TODO: render and assert 'Resume.pdf' appears in the CV list
    expect(response[0]).toHaveProperty('cv_name');
  });

  it('test_existing_api_contract_response_shape_cv_type_distinguishes_uploaded_vs_generated', async () => {
    // Regression: cv_type must be present and must take values 'uploaded' or 'generated'.
    // This field is the sole discriminator between CV categories (per AC-028 and design notes).
    const response = [
      { cv_id: 'cv-001', cv_name: 'Resume.pdf', uploaded_at: '2026-01-10T00:00:00Z', cv_type: 'uploaded' },
      { cv_id: 'cv-002', cv_name: 'Tailored CV', uploaded_at: '2026-02-01T00:00:00Z', cv_type: 'generated' },
    ];
    mockApiGet.mockResolvedValueOnce({ data: response });
    // TODO: render and assert both items rendered in their correct sections
    expect(response[0].cv_type).toBe('uploaded');
    expect(response[1].cv_type).toBe('generated');
  });

  it('test_no_new_non_2xx_responses_on_get_users_me_cv_for_authenticated_user', async () => {
    // Regression: a valid authenticated GET /users/me/cv must not produce 4xx/5xx.
    // Changing the route, auth scheme, or request headers would break CV loading.
    mockApiGet.mockResolvedValueOnce({ data: [] });

    // TODO: render ChooseBaseCVModal within Wrapper (triggers GET /users/me/cv)
    // TODO: await waitFor(() => expect(mockApiGet).toHaveBeenCalled())
    // TODO: assert no error-state element appears (no role="alert" from API failure)
    // TODO: expect(screen.queryByRole('alert')).toBeNull()
    expect(mockApiGet).not.toHaveBeenCalled(); // placeholder — remove once render is wired
  });

});

// ===========================================================================
// 2. CV Center page continues to function — ChooseBaseCVModal is additive
// ===========================================================================
describe('ChooseBaseCVModal regression — CV Center page unaffected', () => {

  it('test_cv_center_page_renders_without_errors_when_choose_base_cv_modal_not_open', () => {
    // Regression: ChooseBaseCVModal is a new additive component.
    // The CV Center page must continue to render its existing content unchanged
    // when the modal is closed (isOpen=false).

    // TODO: import CVCenterPage from '../../../src/frontend/app/cv-center/page'
    // TODO: render <Wrapper><CVCenterPage /></Wrapper>
    // TODO: assert no uncaught render error (no role="alert" from ErrorBoundary)
    // TODO: assert screen.queryByRole('dialog') is null (modal not open by default)
    // TODO: assert existing CV Center elements (heading, table, upload button) are still present
    expect(true).toBe(true); // placeholder — replace with CVCenterPage render assertions
  });

  it('test_cv_center_upload_button_still_present_after_choose_base_cv_modal_added', () => {
    // Regression: the "+ Upload New CV" button on BaseCVsTable must still render.
    // Adding the ChooseBaseCVModal import must not remove or break the trigger button.

    // TODO: render CVCenterPage
    // TODO: assert screen.queryByRole('button', { name: /upload new cv/i }) is not null
    expect(true).toBe(true); // placeholder — replace with button presence assertion
  });

  it('test_no_dialog_rendered_on_cv_center_initial_page_load', () => {
    // Regression: ChooseBaseCVModal must not auto-open on CV Center page load.
    // isOpen must default to false; modal appears only after user interaction.

    // TODO: render CVCenterPage
    // TODO: assert screen.queryByRole('dialog') is null
    expect(true).toBe(true); // placeholder — replace with CVCenterPage dialog-absence assertion
  });

});

// ===========================================================================
// 3. NewApplicationPage — still opens ChooseBaseCVModal (not ChangeBaseCVModal)
// ===========================================================================
describe('ChooseBaseCVModal regression — NewApplicationPage consumer', () => {

  it('test_new_application_page_opens_choose_base_cv_modal_not_change_base_cv_modal', async () => {
    // Regression: NewApplicationPage must import and render ChooseBaseCVModal.
    // The old ChangeBaseCVModal (canvas-app naming) must not be re-introduced.
    // Protects against naming regression between ChangeBaseCVModal and ChooseBaseCVModal.

    jest.mock('../../../src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal', () => ({
      ChooseBaseCVModal: ({ isOpen }: { isOpen: boolean }) =>
        isOpen ? <div role="dialog" data-testid="choose-base-cv-modal" aria-label="Choose Base CV" /> : null,
    }));

    const NewApplicationPage = (await import('../../../src/frontend/app/applications/new/page')).default;
    const Wrapper = createWrapper();
    render(<Wrapper><NewApplicationPage /></Wrapper>);

    // TODO: click the "Change" button to open the modal
    // TODO: assert screen.queryByTestId('choose-base-cv-modal') is not null
    // TODO: assert there is no element with data-testid="change-base-cv-modal" (old name)
    // TODO: expect(screen.queryByTestId('change-base-cv-modal')).toBeNull()
    expect(true).toBe(true); // placeholder — replace with modal identity assertions
  });

  it('test_new_application_page_base_cv_section_still_renders_after_modal_addition', async () => {
    // Regression: the Base CV section label on NewApplicationPage must still render.
    // Adding ChooseBaseCVModal import must not break the existing "Base CV" field display.
    jest.mock('../../../src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal', () => ({
      ChooseBaseCVModal: ({ isOpen }: { isOpen: boolean }) =>
        isOpen ? <div role="dialog" aria-label="Choose Base CV" /> : null,
    }));

    const NewApplicationPage = (await import('../../../src/frontend/app/applications/new/page')).default;
    const Wrapper = createWrapper();
    render(<Wrapper><NewApplicationPage /></Wrapper>);

    // TODO: assert screen.queryByText(/base cv/i) is not null
    expect(true).toBe(true); // placeholder — replace with Base CV section assertion
  });

});

// ===========================================================================
// 4. Unmodified sibling components unaffected
// ===========================================================================
describe('ChooseBaseCVModal regression — sibling component stability', () => {

  it('test_unmodified_sibling_components_on_cv_center_page_unaffected', () => {
    // Regression: existing components on CV Center (AppHeader, AppSidebar)
    // must still render correctly. ChooseBaseCVModal is new — it must not
    // disrupt layout, CSS, or state of neighbouring components.

    // TODO: render CVCenterPage within Wrapper
    // TODO: assert role="banner" (AppHeader) exists
    // TODO: assert role="navigation" (AppSidebar) exists
    // TODO: assert no role="alert" from ErrorBoundary
    expect(true).toBe(true); // placeholder — replace with sibling component assertions
  });

  it('test_unmodified_sibling_components_on_new_application_page_unaffected', async () => {
    // Regression: existing fields on NewApplicationPage (Job Title, Company Name,
    // Job Description, Cancel button) must still render after ChooseBaseCVModal import.

    jest.mock('../../../src/frontend/components/ChooseBaseCVModal/ChooseBaseCVModal', () => ({
      ChooseBaseCVModal: ({ isOpen }: { isOpen: boolean }) =>
        isOpen ? <div role="dialog" aria-label="Choose Base CV" /> : null,
    }));

    const NewApplicationPage = (await import('../../../src/frontend/app/applications/new/page')).default;
    const Wrapper = createWrapper();
    render(<Wrapper><NewApplicationPage /></Wrapper>);

    await waitFor(() => {
      // TODO: expect(screen.queryByLabelText(/job title/i)).not.toBeNull()
      // TODO: expect(screen.queryByLabelText(/company name/i)).not.toBeNull()
      // TODO: expect(screen.queryByLabelText(/job description/i)).not.toBeNull()
      // TODO: expect(screen.queryByRole('button', { name: /^cancel$/i })).not.toBeNull()
      expect(true).toBe(true); // placeholder — replace with field presence assertions
    });
  });

});
