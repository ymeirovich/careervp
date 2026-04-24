import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ExportDropdown } from '../../components/ExportDropdown/ExportDropdown';
import { ApiError } from '../../api/client';

vi.mock('../../api/methods', () => ({
  api: {
    exportArtifact: vi.fn(),
  },
}));

const { api } = await import('../../api/methods');

const DEFAULT_PROPS = {
  jobId: 'job1',
  moduleType: 'vpr' as const,
  artifactId: 'art1',
};

describe('ExportDropdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders export button', () => {
    render(<ExportDropdown {...DEFAULT_PROPS} />);
    expect(screen.getByTestId('export-dropdown')).toBeDefined();
    expect(screen.getByRole('button', { name: /export/i })).toBeDefined();
  });

  it('renders DOCX and PDF options when opened', async () => {
    render(<ExportDropdown {...DEFAULT_PROPS} />);
    fireEvent.click(screen.getByRole('button', { name: /export/i }));
    await waitFor(() => {
      expect(screen.getByText('Download as Word (.docx)')).toBeDefined();
      expect(screen.getByText('Download as PDF')).toBeDefined();
    });
  });

  it('shows coming-soon error message when API returns 501', async () => {
    (api.exportArtifact as ReturnType<typeof vi.fn>).mockRejectedValue(
      new ApiError(501, 'Not Implemented'),
    );

    render(<ExportDropdown {...DEFAULT_PROPS} />);
    fireEvent.click(screen.getByRole('button', { name: /export/i }));

    const docxBtn = await screen.findByText('Download as Word (.docx)');
    fireEvent.click(docxBtn);

    await waitFor(() => {
      expect(screen.getByText('Export is coming soon!')).toBeDefined();
    });
  });

  it('triggers browser download when API returns 200', async () => {
    const clickMock = vi.fn();
    const originalCreateElement = document.createElement.bind(document);
    const createElementSpy = vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      if (tag === 'a') {
        const a = originalCreateElement('a') as HTMLAnchorElement;
        a.click = clickMock;
        return a;
      }
      return originalCreateElement(tag);
    });

    (api.exportArtifact as ReturnType<typeof vi.fn>).mockResolvedValue({
      download_url: 'https://example.com/file.docx',
      expires_at: '2026-04-24T00:00:00Z',
    });

    render(<ExportDropdown {...DEFAULT_PROPS} />);
    fireEvent.click(screen.getByRole('button', { name: /export/i }));

    const docxBtn = await screen.findByText('Download as Word (.docx)');
    fireEvent.click(docxBtn);

    await waitFor(() => {
      expect(clickMock).toHaveBeenCalled();
    });

    createElementSpy.mockRestore();
  });

  it('shows generic error for non-501 failures', async () => {
    (api.exportArtifact as ReturnType<typeof vi.fn>).mockRejectedValue(
      new ApiError(500, 'Server error'),
    );

    render(<ExportDropdown {...DEFAULT_PROPS} />);
    fireEvent.click(screen.getByRole('button', { name: /export/i }));

    const pdfBtn = await screen.findByText('Download as PDF');
    fireEvent.click(pdfBtn);

    await waitFor(() => {
      expect(screen.getByText('Download failed. Please try again.')).toBeDefined();
    });
  });
});
