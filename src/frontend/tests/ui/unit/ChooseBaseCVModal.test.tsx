import React, { useState } from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

vi.mock('../../../lib/auth', () => ({
  getCurrentToken: vi.fn().mockResolvedValue('test-jwt'),
}));

import { ChooseBaseCVModal, type ChooseBaseCVItem } from '../../../components/ChooseBaseCVModal';

const BASE_URL = 'http://localhost:3000';

const uploadedCv: ChooseBaseCVItem = {
  cv_id: 'uploaded-1',
  full_name: 'Uploaded CV',
  language: 'en',
  updated_at: '2026-05-01T00:00:00.000Z',
  cv_type: 'uploaded',
};

const generatedCv: ChooseBaseCVItem = {
  cv_id: 'generated-1',
  full_name: 'Generated CV',
  language: 'en',
  updated_at: '2026-05-02T00:00:00.000Z',
  cv_type: 'generated',
};

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

beforeEach(() => {
  document.documentElement.lang = 'en';
  server.use(
    http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json({ cvs: [uploadedCv, generatedCv] })),
  );
});

afterEach(() => {
  server.resetHandlers();
  vi.restoreAllMocks();
});

afterAll(() => server.close());

function renderModal(
  props: Partial<React.ComponentProps<typeof ChooseBaseCVModal>> = {},
) {
  const onClose = props.onClose ?? vi.fn();
  const view = render(
    <ChooseBaseCVModal
      isOpen
      onClose={onClose}
      onSelectCV={vi.fn()}
      onUpload={vi.fn()}
      {...props}
    />,
  );

  return { ...view, onClose };
}

function renderClosableModal(props: Partial<React.ComponentProps<typeof ChooseBaseCVModal>> = {}) {
  const onCloseSpy = vi.fn();

  function Harness() {
    const [isOpen, setIsOpen] = useState(true);
    return (
      <ChooseBaseCVModal
        isOpen={isOpen}
        onClose={() => {
          onCloseSpy();
          setIsOpen(false);
        }}
        onSelectCV={vi.fn()}
        onUpload={vi.fn()}
        {...props}
      />
    );
  }

  const view = render(<Harness />);
  return { ...view, onCloseSpy };
}

describe('FE-UI-011 — ChooseBaseCVModal render guard', () => {
  it('does not render modal markup when closed', () => {
    render(<ChooseBaseCVModal isOpen={false} onClose={vi.fn()} />);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.queryByText('Choose Base CV')).not.toBeInTheDocument();
    expect(screen.queryByText('Upload Base CV')).not.toBeInTheDocument();
  });
});

describe('FE-UI-011 — choice mode', () => {
  it('renders heading, choice buttons, OR divider, and an existing CV table', async () => {
    renderModal({ showChoices: true });

    expect(screen.getByRole('heading', { name: 'Choose Base CV' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /select uploaded cv/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /select generated cv/i })).toBeInTheDocument();
    expect(screen.getByText('OR')).toBeInTheDocument();
    expect(screen.getByTestId('choose-base-cv-table')).toBeInTheDocument();

    expect(await screen.findByText('Uploaded CV')).toBeInTheDocument();
  });

  it('selects the first uploaded CV when Select uploaded CV is clicked', async () => {
    const onSelectCV = vi.fn();
    renderModal({ showChoices: true, onSelectCV });

    await screen.findByText('Uploaded CV');
    fireEvent.click(screen.getByRole('button', { name: /select uploaded cv/i }));

    expect(onSelectCV).toHaveBeenCalledWith(expect.objectContaining({ cv_id: 'uploaded-1' }), 'uploaded');
  });

  it('selects the first generated CV when Select generated CV is clicked', async () => {
    const onSelectCV = vi.fn();
    renderModal({ showChoices: true, onSelectCV });

    await screen.findByText('Uploaded CV');
    fireEvent.click(screen.getByRole('button', { name: /select generated cv/i }));

    expect(onSelectCV).toHaveBeenCalledWith(expect.objectContaining({ cv_id: 'generated-1' }), 'generated');
    expect(await screen.findByText('Generated CV')).toBeInTheDocument();
  });

  it('keeps generated CVs distinct from uploaded base CVs in row selection', async () => {
    const onSelectCV = vi.fn();
    renderModal({ showChoices: true, onSelectCV });

    const generatedButton = screen.getByRole('button', { name: /select generated cv/i });
    await waitFor(() => expect(generatedButton).toBeEnabled());

    fireEvent.click(generatedButton);
    const generatedRow = await screen.findByTestId('choose-base-cv-row-generated');

    fireEvent.click(within(generatedRow).getByRole('button', { name: 'Select' }));

    expect(onSelectCV).toHaveBeenLastCalledWith(expect.objectContaining({ cv_id: 'generated-1' }), 'generated');
  });
});

describe('FE-UI-011 — upload-only mode', () => {
  it('renders upload-only title with no choice buttons', () => {
    renderModal({ showChoices: false });

    expect(screen.getByRole('heading', { name: 'Upload Base CV' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /select uploaded cv/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /select generated cv/i })).not.toBeInTheDocument();
    expect(screen.getByTestId('choose-base-cv-file-input')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^upload$/i })).toBeDisabled();
  });
});

describe('FE-UI-011 — file upload behavior', () => {
  it('shows filename and enables Upload after file selection', () => {
    renderModal({ showChoices: false });

    const input = screen.getByTestId('choose-base-cv-file-input');
    const file = new File(['cv content'], 'cv.pdf', { type: 'application/pdf' });

    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByText('cv.pdf')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^upload$/i })).toBeEnabled();
  });

  it('opens the OS file picker directly from the Upload New CV trigger', () => {
    renderModal({ showChoices: true });

    const input = screen.getByTestId('choose-base-cv-file-input') as HTMLInputElement;
    const clickSpy = vi.spyOn(input, 'click').mockImplementation(() => undefined);

    fireEvent.click(screen.getByTestId('choose-base-cv-file-trigger'));

    expect(clickSpy).toHaveBeenCalledTimes(1);
  });

  it('fires onUpload with the selected file when Upload is clicked', async () => {
    const onUpload = vi.fn().mockResolvedValue(undefined);
    renderModal({ showChoices: false, onUpload });

    const file = new File(['cv content'], 'cv.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });

    fireEvent.change(screen.getByTestId('choose-base-cv-file-input'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: /^upload$/i }));

    await waitFor(() => expect(onUpload).toHaveBeenCalledWith(file));
  });
});

describe('FE-UI-011 — empty state', () => {
  it('disables choice buttons and highlights upload section when no CVs exist', async () => {
    server.use(http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json({ cvs: [] })));

    renderModal({ showChoices: true });

    await screen.findByText('No CVs available');

    expect(screen.getByRole('button', { name: /select uploaded cv/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /select generated cv/i })).toBeDisabled();
    expect(screen.getByRole('heading', { name: 'Upload New CV' }).closest('form')).toHaveClass('border-primary-action');
  });
});

describe('FE-UI-011 — close behavior', () => {
  it('fires onClose and removes the modal when X is clicked', () => {
    const { onCloseSpy } = renderClosableModal({ showChoices: false });

    fireEvent.click(screen.getByRole('button', { name: 'Close' }));

    expect(onCloseSpy).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('fires onClose and removes the modal on Escape', () => {
    const { onCloseSpy } = renderClosableModal({ showChoices: false });

    fireEvent.keyDown(screen.getByTestId('choose-base-cv-modal-overlay'), { key: 'Escape' });

    expect(onCloseSpy).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('fires onClose when the backdrop is clicked', () => {
    const { onCloseSpy } = renderClosableModal({ showChoices: false });

    fireEvent.click(screen.getByTestId('choose-base-cv-modal-overlay'));

    expect(onCloseSpy).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});

describe('FE-UI-011 — accessibility', () => {
  it('sets dialog semantics and labels', () => {
    renderModal({ showChoices: false });

    const dialog = screen.getByRole('dialog');
    const heading = screen.getByRole('heading', { name: 'Upload Base CV' });
    const subtitle = screen.getByText('Upload your CV in PDF, DOC, or DOCX format.');

    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', heading.id);
    expect(dialog).toHaveAttribute('aria-describedby', subtitle.id);
  });

  it('moves focus inside the modal and traps Tab navigation', async () => {
    renderModal({ showChoices: false });

    await waitFor(() => expect(screen.getByRole('button', { name: 'Close' })).toHaveFocus());

    const cancelButton = screen.getByRole('button', { name: 'Cancel' });
    cancelButton.focus();
    fireEvent.keyDown(screen.getByTestId('choose-base-cv-modal-overlay'), { key: 'Tab' });

    expect(screen.getByRole('button', { name: 'Close' })).toHaveFocus();
  });

  it('uses disabled button attributes for unavailable actions', async () => {
    server.use(http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json({ cvs: [] })));

    renderModal({ showChoices: true });

    await screen.findByText('No CVs available');

    const button = screen.getByRole('button', { name: /select uploaded cv/i });
    expect(button).toBeDisabled();
    expect(button).toHaveClass('disabled:opacity-50');
    expect(button).toHaveClass('disabled:cursor-not-allowed');
  });
});

describe('FE-UI-011 — Hebrew copy', () => {
  it('renders Hebrew choice-mode strings when locale is he', () => {
    document.documentElement.lang = 'he';

    renderModal({ showChoices: true });

    expect(screen.getByRole('heading', { name: 'בחר קורות חיים בסיסיים' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /בחר קורות חיים שהועלו/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /בחר קורות חיים שנוצרו/ })).toBeInTheDocument();
    expect(screen.getAllByText('העלה קורות חיים חדשים').length).toBeGreaterThan(0);
    expect(screen.getByText('או')).toBeInTheDocument();
  });

  it('renders Hebrew upload-only strings when locale is he', () => {
    document.documentElement.lang = 'he';

    renderModal({ showChoices: false });

    expect(screen.getByRole('heading', { name: 'העלה קורות חיים בסיסיים' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^העלה$/ })).toBeInTheDocument();
  });
});

describe('FE-UI-011 — responsive class contract', () => {
  it('uses full-width modal constraints with viewport padding for narrow screens', () => {
    renderModal({ showChoices: false });

    expect(screen.getByTestId('choose-base-cv-modal-overlay')).toHaveClass('px-4');
    expect(screen.getByRole('dialog')).toHaveClass('w-full');
  });
});
