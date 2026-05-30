import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { DashboardContext, type DashboardContextValue } from '../../../contexts/DashboardContext';
import DashboardPage from '../../../app/dashboard/page';
import NewApplicationPage from '../../../app/applications/new/page';

const { mockPush } = vi.hoisted(() => ({
  mockPush: vi.fn(),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
}));

vi.mock('../../../lib/auth', () => ({
  getCurrentToken: vi.fn().mockResolvedValue('test-jwt'),
}));

const BASE_URL = 'http://localhost:3000';
const server = setupServer();

const dashboardContext: DashboardContextValue = {
  applicationsRemaining: 3,
  hasActiveAccess: true,
  isLoading: false,
  subscription: null,
  usage: {
    applications: { remaining: 3, used: 0 },
    trial: {
      active: true,
      days_elapsed: 1,
      days_remaining: 13,
      ends_at: '2026-06-12T00:00:00.000Z',
    },
  },
  userName: 'Test User',
};

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

beforeEach(() => {
  mockPush.mockClear();
  document.documentElement.lang = 'en';
  window.history.pushState({}, '', '/applications/new');
  server.use(
    http.get(`${BASE_URL}/jobs`, () => HttpResponse.json({ jobs: [] })),
    http.get(`${BASE_URL}/users/me/cv`, () =>
      HttpResponse.json({
        cvs: [
          {
            cv_id: 'cv-1',
            cv_type: 'uploaded',
            file_name: 'base-cv.pdf',
            updated_at: '2026-05-01T00:00:00.000Z',
          },
        ],
      }),
    ),
    http.post(`${BASE_URL}/jobs`, () => HttpResponse.json({ job_id: 'job-123' })),
  );
});

afterEach(() => {
  server.resetHandlers();
});

afterAll(() => server.close());

function renderWithQuery(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function renderNewApplicationPage() {
  return renderWithQuery(<NewApplicationPage />);
}

function renderDashboardPage() {
  return renderWithQuery(
    <DashboardContext.Provider value={dashboardContext}>
      <DashboardPage />
    </DashboardContext.Provider>,
  );
}

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText(/job title/i), { target: { value: 'Software Engineer' } });
  fireEvent.change(screen.getByLabelText(/company name/i), { target: { value: 'Acme Corp' } });
  fireEvent.change(screen.getByLabelText(/job description/i), {
    target: { value: 'Build resilient customer-facing frontend systems.' },
  });
}

describe('FE-UI-010 — dashboard entry point', () => {
  it('navigates to /applications/new instead of opening the old modal', () => {
    renderDashboardPage();

    fireEvent.click(screen.getByTestId('new-application-btn'));

    expect(mockPush).toHaveBeenCalledWith('/applications/new');
    expect(screen.queryByRole('dialog', { name: /new application/i })).not.toBeInTheDocument();
  });
});

describe('FE-UI-010 — NewApplicationPage layout and fields', () => {
  it('renders a full-page card form with back navigation and the required fields', () => {
    renderNewApplicationPage();

    expect(screen.getByRole('button', { name: '← Back' })).toBeInTheDocument();
    expect(screen.getByTestId('new-application-page')).toHaveClass('max-w-3xl', { exact: false });
    expect(screen.queryByRole('dialog', { name: /new application/i })).not.toBeInTheDocument();

    expect(screen.getByLabelText(/job title/i)).toBeRequired();
    expect(screen.getByLabelText(/company name/i)).toBeRequired();
    expect(screen.getByLabelText(/job description/i)).toBeRequired();
    expect(screen.getByLabelText(/job url/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create Application' })).toBeDisabled();
  });

  it('enables Create Application only after required fields are filled', () => {
    renderNewApplicationPage();

    const createButton = screen.getByRole('button', { name: 'Create Application' });
    expect(createButton).toBeDisabled();

    fillRequiredFields();

    expect(createButton).toBeEnabled();
  });

  it('navigates back to the dashboard from Back and Cancel', () => {
    renderNewApplicationPage();

    fireEvent.click(screen.getByRole('button', { name: '← Back' }));
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(mockPush).toHaveBeenCalledWith('/dashboard');
    expect(mockPush).toHaveBeenCalledTimes(2);
  });
});

describe('FE-UI-010 — base CV picker', () => {
  it('opens ChooseBaseCVModal in choice mode and updates the selected filename', async () => {
    renderNewApplicationPage();

    expect(screen.getByText('Base CV')).toBeInTheDocument();
    expect(screen.getByTestId('selected-base-cv-name')).toHaveTextContent('No CV selected');

    fireEvent.click(screen.getByRole('button', { name: 'Change' }));

    expect(screen.getByRole('heading', { name: 'Choose Base CV' })).toBeInTheDocument();
    const row = await screen.findByTestId('choose-base-cv-row-uploaded');

    fireEvent.click(within(row).getByRole('button', { name: 'Select' }));

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByTestId('selected-base-cv-name')).toHaveTextContent('base-cv.pdf');
  });
});

describe('FE-UI-010 — submission states', () => {
  it('posts the existing /jobs payload, disables the form while creating, and redirects on success', async () => {
    let releasePost: () => void = () => undefined;
    const postGate = new Promise<void>((resolve) => {
      releasePost = resolve;
    });
    let capturedBody: unknown;

    server.use(
      http.post(`${BASE_URL}/jobs`, async ({ request }) => {
        capturedBody = await request.json();
        await postGate;
        return HttpResponse.json({ job_id: 'new-job-456' });
      }),
    );

    renderNewApplicationPage();
    fillRequiredFields();
    fireEvent.change(screen.getByLabelText(/job url/i), { target: { value: 'https://acme.example/jobs/1' } });

    fireEvent.click(screen.getByRole('button', { name: 'Create Application' }));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Creating...' })).toBeDisabled());
    expect(screen.getByLabelText(/job title/i)).toBeDisabled();
    expect(screen.getByLabelText(/company name/i)).toBeDisabled();
    expect(screen.getByLabelText(/job description/i)).toBeDisabled();
    expect(screen.getByLabelText(/job url/i)).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();

    releasePost();

    await waitFor(() => {
      expect(capturedBody).toEqual({
        company_name: 'Acme Corp',
        description: 'Build resilient customer-facing frontend systems.',
        title: 'Software Engineer',
        url: 'https://acme.example/jobs/1',
      });
      expect(mockPush).toHaveBeenCalledWith('/applications/new-job-456');
    });
  });

  it('shows an error banner and clears it when a field changes', async () => {
    server.use(
      http.post(`${BASE_URL}/jobs`, () => HttpResponse.json({ error: 'Unable to create job' }, { status: 500 })),
    );

    renderNewApplicationPage();
    fillRequiredFields();
    fireEvent.click(screen.getByRole('button', { name: 'Create Application' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to create job');

    fireEvent.change(screen.getByLabelText(/job title/i), { target: { value: 'Senior Software Engineer' } });

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('FE-UI-010 — Hebrew locale', () => {
  it('renders Hebrew strings and RTL layout when locale=he', () => {
    window.history.pushState({}, '', '/applications/new?locale=he');

    renderNewApplicationPage();

    expect(screen.getByTestId('new-application-page')).toHaveAttribute('dir', 'rtl');
    expect(screen.getByRole('button', { name: '← חזרה' })).toBeInTheDocument();
    expect(screen.getByLabelText(/שם המשרה/)).toBeInTheDocument();
    expect(screen.getByText('קורות חיים בסיסיים')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'שנה' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'צור הגשה' })).toBeDisabled();
  });
});
