import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import CVCenterPage from '../../../app/cv-center/page';
import type { BaseCVListItem } from '../../../components/BaseCVsTable';

vi.mock('../../../lib/auth', () => ({
  getCurrentToken: vi.fn().mockResolvedValue('test-jwt'),
}));

vi.mock('../../../components/ErrorBoundary/ErrorBoundary', () => ({
  ErrorBoundary: ({ children, cloudwatchKey }: { children: React.ReactNode; cloudwatchKey: string }) => (
    <div data-testid="error-boundary" data-cloudwatch-key={cloudwatchKey}>
      {children}
    </div>
  ),
}));

const BASE_URL = 'http://localhost:3000';
const server = setupServer();

const BASE_CVS: BaseCVListItem[] = [
  {
    cv_id: 'cv-1',
    full_name: 'Dana Product CV',
    language: 'English',
    created_at: '2026-05-01T08:00:00Z',
    updated_at: '2026-05-20T10:00:00Z',
    status: 'ready',
    used_in_count: 1,
  },
];

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

beforeEach(() => {
  document.documentElement.lang = 'en';
  window.history.pushState({}, '', '/cv-center');
  server.use(http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json({ cvs: BASE_CVS })));
});

afterEach(() => {
  server.resetHandlers();
  vi.restoreAllMocks();
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

describe('CVCenterContent', () => {
  it('renders the Base CVs header, All Base CVs card heading, upload button, and BaseCVsTable', async () => {
    renderWithQuery(<CVCenterPage />);

    expect(screen.getByTestId('page-header-title')).toHaveTextContent('Base CVs');
    expect(screen.getByTestId('base-cvs-card-heading')).toHaveTextContent('All Base CVs');

    const card = screen.getByTestId('base-cvs-card');
    const uploadButton = within(card).getByRole('button', { name: '+ Upload New CV' });
    expect(uploadButton).toHaveClass('bg-primary-action');
    expect(within(card).getByTestId('base-cvs-table')).toBeInTheDocument();

    expect(await screen.findByText('Dana Product CV')).toBeInTheDocument();
  });

  it('passes loading state to BaseCVsTable while GET /users/me/cv is in flight', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });

    server.use(
      http.get(`${BASE_URL}/users/me/cv`, async () => {
        await gate;
        return HttpResponse.json({ cvs: BASE_CVS });
      }),
    );

    renderWithQuery(<CVCenterPage />);

    expect(await screen.findByTestId('base-cvs-table')).toHaveAttribute('data-is-loading', 'true');

    release();

    await waitFor(() => {
      expect(screen.getByTestId('base-cvs-table')).toHaveAttribute('data-is-loading', 'false');
    });
  });

  it('passes error state to BaseCVsTable and retries GET /users/me/cv', async () => {
    let callCount = 0;
    server.use(
      http.get(`${BASE_URL}/users/me/cv`, () => {
        callCount += 1;
        if (callCount === 1) return HttpResponse.json({ error: 'Could not load base CVs' }, { status: 500 });
        return HttpResponse.json({ cvs: BASE_CVS });
      }),
    );

    renderWithQuery(<CVCenterPage />);

    const table = await screen.findByTestId('base-cvs-table');
    await waitFor(() => {
      expect(table).toHaveAttribute('data-has-error', 'true');
      expect(table).toHaveAttribute('data-is-loading', 'false');
    });
    expect(within(table).getByText('Could not load base CVs')).toBeInTheDocument();

    fireEvent.click(within(table).getByRole('button', { name: 'Retry' }));

    await waitFor(() => {
      expect(screen.getByText('Dana Product CV')).toBeInTheDocument();
      expect(callCount).toBe(2);
    });
  });

  it('passes a successful response array to BaseCVsTable', async () => {
    server.use(http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json(BASE_CVS)));

    renderWithQuery(<CVCenterPage />);

    expect(await screen.findByText('Dana Product CV')).toBeInTheDocument();
    expect(screen.getByTestId('base-cvs-table')).toHaveAttribute('data-base-cvs-count', '1');
  });

  it('opens ChooseBaseCVModal in upload-only mode from the card upload button', async () => {
    renderWithQuery(<CVCenterPage />);

    fireEvent.click(within(screen.getByTestId('base-cvs-card')).getByRole('button', { name: '+ Upload New CV' }));

    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Upload Base CV' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /select uploaded cv/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /select generated cv/i })).not.toBeInTheDocument();
  });

  it('posts the uploaded file, closes the modal, and refetches GET /users/me/cv', async () => {
    let getCallCount = 0;
    let postBody: unknown = null;

    server.use(
      http.get(`${BASE_URL}/users/me/cv`, () => {
        getCallCount += 1;
        if (getCallCount === 1) return HttpResponse.json({ cvs: [] });
        return HttpResponse.json({ cvs: BASE_CVS });
      }),
      http.post(`${BASE_URL}/users/me/cv`, async ({ request }) => {
        postBody = await request.json();
        return HttpResponse.json({ cv_id: 'cv-1', success: true }, { status: 201 });
      }),
    );

    renderWithQuery(<CVCenterPage />);

    fireEvent.click(await screen.findByRole('button', { name: '+ Upload New CV' }));
    const file = new File(['cv content'], 'base-cv.txt', { type: 'text/plain' });
    fireEvent.change(screen.getByTestId('choose-base-cv-file-input'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: /^upload$/i }));

    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      expect(screen.getByText('Dana Product CV')).toBeInTheDocument();
      expect(getCallCount).toBe(2);
      expect(postBody).toEqual(expect.objectContaining({ file_name: 'base-cv.txt', file_type: 'txt' }));
    });
  });

  it('does not render the old single-CV form, preview, or mode actions', async () => {
    renderWithQuery(<CVCenterPage />);

    await screen.findByTestId('base-cvs-table');

    expect(screen.queryByText('Basic Information')).not.toBeInTheDocument();
    expect(screen.queryByText('Professional Summary')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Edit CV' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Create CV' })).not.toBeInTheDocument();
  });

  it('wraps CVCenterContent in ErrorBoundary with the cv-center-page CloudWatch key', () => {
    renderWithQuery(<CVCenterPage />);

    expect(screen.getByTestId('error-boundary')).toHaveAttribute('data-cloudwatch-key', 'cv-center-page');
  });

  it('renders Hebrew page strings when locale=he', () => {
    window.history.pushState({}, '', '/cv-center?locale=he');

    renderWithQuery(<CVCenterPage />);

    expect(screen.getByTestId('cv-center-page')).toHaveAttribute('dir', 'rtl');
    expect(screen.getByTestId('page-header-title')).toHaveTextContent('קורות חיים בסיסיים');
    expect(screen.getByTestId('base-cvs-card-heading')).toHaveTextContent('כל קורות החיים הבסיסיים');
    expect(screen.getByRole('button', { name: '+ העלאת קורות חיים חדשים' })).toBeInTheDocument();
  });
});
