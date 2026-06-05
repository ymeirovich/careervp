import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ExportDropdown } from '../../components/ExportDropdown/ExportDropdown';
import { ApiError } from '../../api/client';

vi.mock('../../api/methods', () => ({
  api: apiMocks,
}));

const apiMocks = vi.hoisted(() => ({
  exportArtifact: vi.fn(),
}));

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
    apiMocks.exportArtifact.mockRejectedValue(
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

    apiMocks.exportArtifact.mockResolvedValue({
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
    apiMocks.exportArtifact.mockRejectedValue(
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

  it('closes dropdown when clicking outside', async () => {
    render(<ExportDropdown {...DEFAULT_PROPS} />);
    fireEvent.click(screen.getByRole('button', { name: /export/i }));
    expect(await screen.findByText('Download as Word (.docx)')).toBeDefined();

    fireEvent.mouseDown(document.body);

    await waitFor(() => {
      expect(screen.queryByText('Download as Word (.docx)')).toBeNull();
    });
  });

  it('closes dropdown after format selected', async () => {
    apiMocks.exportArtifact.mockResolvedValue({
      download_url: 'https://example.com/file.docx',
      expires_at: '2030-01-01T00:00:00Z',
    });

    render(<ExportDropdown {...DEFAULT_PROPS} />);
    fireEvent.click(screen.getByRole('button', { name: /export/i }));

    const docxBtn = await screen.findByText('Download as Word (.docx)');
    fireEvent.click(docxBtn);

    await waitFor(() => {
      expect(screen.queryByText('Download as Word (.docx)')).toBeNull();
    });
  });

  it('calls api.exportArtifact with jobId, moduleType, and docx format when DOCX clicked', async () => {
    apiMocks.exportArtifact.mockResolvedValue({
      download_url: 'https://example.com/file.docx',
      expires_at: '2030-01-01T00:00:00Z',
    });

    render(<ExportDropdown {...DEFAULT_PROPS} />);
    fireEvent.click(screen.getByRole('button', { name: /export/i }));

    const docxBtn = await screen.findByText('Download as Word (.docx)');
    fireEvent.click(docxBtn);

    await waitFor(() => {
      expect(apiMocks.exportArtifact).toHaveBeenCalledWith('job1', 'vpr', 'docx');
    });
  });

  it('calls api.exportArtifact with jobId, moduleType, and pdf format when PDF clicked', async () => {
    apiMocks.exportArtifact.mockResolvedValue({
      download_url: 'https://example.com/file.pdf',
      expires_at: '2030-01-01T00:00:00Z',
    });

    render(<ExportDropdown {...DEFAULT_PROPS} />);
    fireEvent.click(screen.getByRole('button', { name: /export/i }));

    const pdfBtn = await screen.findByText('Download as PDF');
    fireEvent.click(pdfBtn);

    await waitFor(() => {
      expect(apiMocks.exportArtifact).toHaveBeenCalledWith('job1', 'vpr', 'pdf');
    });
  });

  it('shows Exporting… and disables button while request is in flight', async () => {
    let resolveExport!: (v: { download_url: string; expires_at: string }) => void;
    apiMocks.exportArtifact.mockImplementation(
      () => new Promise<{ download_url: string; expires_at: string }>(resolve => {
        resolveExport = resolve;
      }),
    );

    render(<ExportDropdown {...DEFAULT_PROPS} />);
    fireEvent.click(screen.getByRole('button', { name: /export/i }));

    const docxBtn = await screen.findByText('Download as Word (.docx)');
    fireEvent.click(docxBtn);

    await waitFor(() => {
      const btn = screen.getByRole('button', { name: /exporting/i }) as HTMLButtonElement;
      expect(btn).toBeDefined();
      expect(btn.disabled).toBe(true);
    });

    resolveExport({ download_url: 'https://example.com/file.docx', expires_at: '2030-01-01T00:00:00Z' });
  });

  it('re-enables button after successful export', async () => {
    apiMocks.exportArtifact.mockResolvedValue({
      download_url: 'https://example.com/file.docx',
      expires_at: '2030-01-01T00:00:00Z',
    });

    render(<ExportDropdown {...DEFAULT_PROPS} />);
    fireEvent.click(screen.getByRole('button', { name: /export/i }));

    const docxBtn = await screen.findByText('Download as Word (.docx)');
    fireEvent.click(docxBtn);

    await waitFor(() => {
      // dropdown is closed after selection; only the trigger button remains
      const btn = screen.getByRole('button') as HTMLButtonElement;
      expect(btn.textContent).toContain('Export');
      expect(btn.textContent).not.toContain('Exporting');
      expect(btn.disabled).toBe(false);
    });
  });

  it('re-enables button after export error', async () => {
    apiMocks.exportArtifact.mockRejectedValue(new ApiError(500, 'Server error'));

    render(<ExportDropdown {...DEFAULT_PROPS} />);
    fireEvent.click(screen.getByRole('button', { name: /export/i }));

    const docxBtn = await screen.findByText('Download as Word (.docx)');
    fireEvent.click(docxBtn);

    await waitFor(() => {
      const btn = screen.getByRole('button') as HTMLButtonElement;
      expect(btn.textContent).not.toContain('Exporting');
      expect(btn.disabled).toBe(false);
    });
  });

  it.each(['vpr', 'cover_letter', 'interview_prep', 'cv_tailored'] as const)(
    'passes correct moduleType %s to exportArtifact',
    async (moduleType) => {
      apiMocks.exportArtifact.mockResolvedValue({
        download_url: 'https://example.com/file.docx',
        expires_at: '2030-01-01T00:00:00Z',
      });

      render(<ExportDropdown jobId="job1" moduleType={moduleType} artifactId="art1" />);
      fireEvent.click(screen.getByRole('button', { name: /export/i }));

      const docxBtn = await screen.findByText('Download as Word (.docx)');
      fireEvent.click(docxBtn);

      await waitFor(() => {
        expect(apiMocks.exportArtifact).toHaveBeenCalledWith('job1', moduleType, 'docx');
      });
    },
  );
});
