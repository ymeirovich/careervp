import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import CoverLettersPage from '../../../app/cover-letters/page';

vi.mock('../../../lib/auth', () => ({
  getCurrentToken: vi.fn().mockResolvedValue('test-jwt'),
}));

const BASE_URL = 'http://localhost:3000';
const server = setupServer();

const FIXTURE_COVER_LETTERS = [
  {
    applicationId: 'app-1',
    company_name: 'Acme Corp',
    job_title: 'Senior Engineer',
    status: 'ready',
    created_at: '2026-05-20T10:00:00Z',
  },
];

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

beforeEach(() => {
  document.documentElement.lang = 'en';
  window.history.pushState({}, '', '/cover-letters');
  server.use(
    http.get(`${BASE_URL}/cover-letters`, () => HttpResponse.json(FIXTURE_COVER_LETTERS)),
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

describe('CoverLettersPage', () => {
  it('renders the page header title and subheading', () => {
    renderWithQuery(<CoverLettersPage />);

    expect(within(screen.getByTestId('page-header')).getByTestId('page-header-title')).toHaveTextContent('Cover Letters');
    expect(within(screen.getByTestId('page-header')).getByTestId('page-header-subheading')).toHaveTextContent('All Cover Letters');
  });

  it('renders CoverLettersListTable below the header', async () => {
    renderWithQuery(<CoverLettersPage />);

    const header = screen.getByTestId('page-header');
    const table = await screen.findByTestId('cover-letters-list-table');
    expect(header.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('passes loading state while GET /cover-letters is in flight', async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });

    server.use(
      http.get(`${BASE_URL}/cover-letters`, async () => {
        await gate;
        return HttpResponse.json(FIXTURE_COVER_LETTERS);
      }),
    );

    renderWithQuery(<CoverLettersPage />);

    expect(await screen.findByTestId('cover-letters-list-table')).toHaveAttribute('data-is-loading', 'true');

    release();

    await waitFor(() => {
      expect(screen.getByTestId('cover-letters-list-table')).toHaveAttribute('data-is-loading', 'false');
    });
  });

  it('passes error state and retries on Retry click', async () => {
    let callCount = 0;
    server.use(
      http.get(`${BASE_URL}/cover-letters`, () => {
        callCount += 1;
        if (callCount === 1) {
          return HttpResponse.json({ error: 'Server error' }, { status: 500 });
        }
        return HttpResponse.json(FIXTURE_COVER_LETTERS);
      }),
    );

    renderWithQuery(<CoverLettersPage />);

    const table = await screen.findByTestId('cover-letters-list-table');
    await waitFor(() => {
      expect(table).toHaveAttribute('data-has-error', 'true');
      expect(table).toHaveAttribute('data-is-loading', 'false');
    });
    expect(within(table).getByText(/server error/i)).toBeInTheDocument();

    fireEvent.click(within(table).getByRole('button', { name: 'Retry' }));

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      expect(callCount).toBe(2);
    });
  });

  it('passes loaded data array to the table', async () => {
    renderWithQuery(<CoverLettersPage />);

    expect(await screen.findByText('Acme Corp')).toBeInTheDocument();
  });

  it('renders Hebrew page header strings when locale=he', () => {
    window.history.pushState({}, '', '/cover-letters?locale=he');

    renderWithQuery(<CoverLettersPage />);

    expect(screen.getByTestId('page-header-title')).toHaveTextContent('מכתבי פנייה');
    expect(screen.getByTestId('page-header-subheading')).toHaveTextContent('כל מכתבי הפנייה');
  });
});
