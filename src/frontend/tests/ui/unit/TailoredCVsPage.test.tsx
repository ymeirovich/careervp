import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import TailoredCVsPage from '../../../app/tailored-cvs/page';

vi.mock('../../../lib/auth', () => ({
  getCurrentToken: vi.fn().mockResolvedValue('test-jwt'),
}));

const BASE_URL = 'http://localhost:3000';
const server = setupServer();

const FIXTURE_TAILORED_CVS = [
  {
    id: 'tcv-1',
    applicationId: 'app-1',
    title: 'Senior Engineer — Tailored CV',
    language: 'en',
    status: 'ready',
    updated_at: '2026-05-20T10:00:00Z',
  },
];

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

beforeEach(() => {
  document.documentElement.lang = 'en';
  window.history.pushState({}, '', '/tailored-cvs');
  server.use(
    http.get(`${BASE_URL}/cv-tailorings`, () => HttpResponse.json(FIXTURE_TAILORED_CVS)),
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

describe('TailoredCVsPage', () => {
  it('renders the page header title and card subheading', () => {
    renderWithQuery(<TailoredCVsPage />);

    expect(within(screen.getByTestId('page-header')).getByTestId('page-header-title')).toHaveTextContent('Tailored CVs');
    expect(within(screen.getByTestId('tailored-cvs-card')).getByTestId('page-header-subheading')).toHaveTextContent('All Tailored CVs');
  });

  it('renders TailoredCVsListTable below the header', async () => {
    renderWithQuery(<TailoredCVsPage />);

    const header = screen.getByTestId('page-header');
    const table = await screen.findByTestId('tailored-cvs-list-table');
    expect(header.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('passes loading state while GET /cv-tailorings is in flight', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });

    server.use(
      http.get(`${BASE_URL}/cv-tailorings`, async () => {
        await gate;
        return HttpResponse.json(FIXTURE_TAILORED_CVS);
      }),
    );

    renderWithQuery(<TailoredCVsPage />);

    expect(await screen.findByTestId('tailored-cvs-list-table')).toHaveAttribute('data-is-loading', 'true');

    release();

    await waitFor(() => {
      expect(screen.getByTestId('tailored-cvs-list-table')).toHaveAttribute('data-is-loading', 'false');
    });
  });

  it('passes error state and retries on Retry click', async () => {
    let callCount = 0;
    server.use(
      http.get(`${BASE_URL}/cv-tailorings`, () => {
        callCount += 1;
        if (callCount === 1) {
          return HttpResponse.json({ error: 'Server error' }, { status: 500 });
        }
        return HttpResponse.json(FIXTURE_TAILORED_CVS);
      }),
    );

    renderWithQuery(<TailoredCVsPage />);

    const table = await screen.findByTestId('tailored-cvs-list-table');
    await waitFor(() => {
      expect(table).toHaveAttribute('data-has-error', 'true');
      expect(table).toHaveAttribute('data-is-loading', 'false');
    });
    expect(within(table).getByText(/server error/i)).toBeInTheDocument();

    fireEvent.click(within(table).getByRole('button', { name: 'Retry' }));

    await waitFor(() => {
      expect(screen.getByText('Senior Engineer — Tailored CV')).toBeInTheDocument();
      expect(callCount).toBe(2);
    });
  });

  it('passes loaded data array to the table', async () => {
    renderWithQuery(<TailoredCVsPage />);

    expect(await screen.findByText('Senior Engineer — Tailored CV')).toBeInTheDocument();
  });

  it('renders Hebrew page header strings when locale=he', () => {
    window.history.pushState({}, '', '/tailored-cvs?locale=he');

    renderWithQuery(<TailoredCVsPage />);

    expect(screen.getByTestId('page-header-title')).toHaveTextContent('קורות חיים מותאמים');
    expect(screen.getByTestId('page-header-subheading')).toHaveTextContent('כל קורות החיים המותאמים');
  });
});

