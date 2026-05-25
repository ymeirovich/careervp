// spec_id: FE-UI-005
// Component: HubLayout (+ ApplicationHubPage for AC-012)
// File: src/frontend/components/layout/HubLayout.tsx
// Page: src/frontend/app/applications/[id]/page.tsx
// Route: /applications/[id]
// ACs covered (integration): AC-007, AC-008, AC-012

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { jest, describe, it, expect, beforeEach } from '@jest/globals';

jest.mock('next/link', () => ({
  default: ({ href, children, ...props }: { href: string; children: React.ReactNode; [key: string]: unknown }) => (
    <a href={href} {...props}>{children}</a>
  ),
}));

jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({ push: jest.fn(), replace: jest.fn() })),
  useParams: jest.fn(() => ({ id: 'test-application-id' })),
}));

// Mock the useApplicationHub hook at the module level — not at network level.
// This keeps the component tree real while controlling returned data.
jest.mock('../../../src/frontend/hooks/useApplicationHub', () => ({
  useApplicationHub: jest.fn(),
}));

import { useApplicationHub } from '../../../src/frontend/hooks/useApplicationHub';
import { HubLayout } from '../../../src/frontend/components/layout/HubLayout';

// TODO: import ApplicationHubPage for AC-012
// import ApplicationHubPage from '../../../src/frontend/app/applications/[id]/page';

const mockUseApplicationHub = jest.mocked(useApplicationHub);

const LONG_DESCRIPTION =
  'This is a very long job description that exceeds three lines of visible text. ' +
  'It contains multiple sentences to ensure the line-clamp truncation is triggered. ' +
  'Additional content here to push well past the three-line threshold in any viewport. ' +
  'Even more content to be absolutely certain the text is long enough.';

const mockApiJobDetail = {
  job_title: 'Product Manager',
  company_name: 'Beta Inc',
  job_url: 'https://example.com/pm-role',
  job_description: LONG_DESCRIPTION,
};

const createWrapper = () => {
  // TODO: add QueryClientProvider and any AuthContext providers required by ApplicationHubPage
  // const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  // return ({ children }: { children: React.ReactNode }) => (
  //   <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  // );
  return ({ children }: { children: React.ReactNode }) => <>{children}</>;
};

describe('HubLayout integration', () => {

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ─── AC-007: "Show more" expands description and button becomes "Show less" ──

  it('test_description_expands_and_button_becomes_show_less_when_show_more_clicked', async () => {
    // TODO: render <HubLayout hubStatus="ACTIVE" jobTitle="PM Role" companyName="Beta" jobUrl="https://example.com" jobDescription={LONG_DESCRIPTION}><div /></HubLayout>
    // TODO: assert initial state: button text is "Show more"
    // TODO: assert description element has line-clamp-3 class
    // TODO: fireEvent.click(screen.getByRole('button', { name: /Show more/ }))
    // TODO: await waitFor(() => assert description element does NOT have line-clamp-3 class)
    // TODO: assert screen.getByRole('button', { name: /Show less/ }) is in the document
    // TODO: assert screen.queryByRole('button', { name: /Show more/ }) is null
  });

  // ─── AC-008: "Show less" collapses description and button reverts to "Show more"

  it('test_description_truncates_and_button_reverts_to_show_more_when_show_less_clicked', async () => {
    // TODO: render <HubLayout hubStatus="ACTIVE" jobTitle="PM Role" companyName="Beta" jobUrl="https://example.com" jobDescription={LONG_DESCRIPTION}><div /></HubLayout>
    // TODO: fireEvent.click(screen.getByRole('button', { name: /Show more/ })) — expand first
    // TODO: await waitFor(() => assert button text is "Show less")
    // TODO: fireEvent.click(screen.getByRole('button', { name: /Show less/ }))
    // TODO: await waitFor(() => assert description element has line-clamp-3 class again)
    // TODO: assert screen.getByRole('button', { name: /Show more/ }) is in the document
    // TODO: assert screen.queryByRole('button', { name: /Show less/ }) is null
  });

  // ─── AC-007 + AC-008: Full toggle cycle ─────────────────────────────────────

  it('test_toggle_cycle_expand_then_collapse_then_expand_again', async () => {
    // TODO: render HubLayout with LONG_DESCRIPTION
    // TODO: click "Show more" → assert expanded
    // TODO: click "Show less" → assert collapsed
    // TODO: click "Show more" again → assert expanded (toggle is stateless between cycles)
  });

  // ─── AC-012: ApplicationHubPage passes job_title from API to HubLayout ───────

  it('test_job_title_prop_matches_api_response_when_application_hub_page_loads', async () => {
    // TODO: mockUseApplicationHub.mockReturnValue({
    //   hubState: { ...mockApiJobDetail, hubStatus: 'ACTIVE' },
    //   isLoading: false,
    //   error: null,
    // });
    // TODO: render <ApplicationHubPage params={{ id: 'test-application-id' }} /> with createWrapper()
    // TODO: await waitFor(() => assert screen.getByRole('heading', { level: 2, name: 'Product Manager' }) is in the document)
    //        — confirms the page passes job_title from API response as jobTitle prop to HubLayout
  });

  it('test_company_name_prop_matches_api_response_when_application_hub_page_loads', async () => {
    // TODO: mockUseApplicationHub.mockReturnValue({
    //   hubState: { ...mockApiJobDetail, hubStatus: 'ACTIVE' },
    //   isLoading: false,
    //   error: null,
    // });
    // TODO: render <ApplicationHubPage params={{ id: 'test-application-id' }} /> with createWrapper()
    // TODO: await waitFor(() => assert screen.getByText('Beta Inc') is in the document)
  });

  it('test_no_job_detail_section_rendered_when_api_returns_no_job_title', async () => {
    // TODO: mockUseApplicationHub.mockReturnValue({
    //   hubState: { hubStatus: 'ACTIVE', job_title: undefined },
    //   isLoading: false,
    //   error: null,
    // });
    // TODO: render <ApplicationHubPage params={{ id: 'test-application-id' }} /> with createWrapper()
    // TODO: await waitFor(() => assert screen.queryByRole('heading', { level: 2 }) is null)
    //        — confirms graceful fallback per AC-010 when API omits job fields
  });

  it('test_hub_layout_still_renders_children_when_api_call_is_loading', async () => {
    // TODO: mockUseApplicationHub.mockReturnValue({ hubState: null, isLoading: true, error: null })
    // TODO: render <ApplicationHubPage params={{ id: 'test-application-id' }} /> with createWrapper()
    // TODO: assert the page renders without throwing (loading state is handled at page level, not HubLayout)
  });

});
