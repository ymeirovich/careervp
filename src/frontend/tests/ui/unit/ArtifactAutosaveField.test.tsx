import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ArtifactAutosaveField } from '../../../components/ArtifactAutosaveField';

describe('ArtifactAutosaveField', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('renders a restore banner when a newer local draft exists', async () => {
    localStorage.setItem(
      'careervp:draft:cover_letter:artifact-1:field-1',
      JSON.stringify({
        markdown: 'Draft value',
        updatedAt: '2026-06-20T12:00:00Z',
        baseVersion: null,
      }),
    );

    const onValueChange = vi.fn();

    render(
      <ArtifactAutosaveField
        artifactType="cover_letter"
        artifactId="artifact-1"
        fieldKey="field-1"
        value="Server value"
        baseline="Server value"
        onValueChange={onValueChange}
        serverUpdatedAt="2026-06-20T10:00:00Z"
        baseVersion={null}
        save={vi.fn()}
        onSaved={vi.fn()}
        renderField={() => <div data-testid="field">Field</div>}
      />,
    );

    expect(await screen.findByText('Restore unsaved changes?')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Restore' }));
    expect(onValueChange).toHaveBeenCalledWith('Draft value');
  });

  it('saves on blur when the value is dirty', async () => {
    const save = vi.fn().mockResolvedValue({
      value: 'Updated value',
      baseVersion: 2,
      updatedAt: '2026-06-20T12:00:00Z',
    });
    const onSaved = vi.fn();

    render(
      <ArtifactAutosaveField
        artifactType="cover_letter"
        artifactId="artifact-1"
        fieldKey="field-1"
        value="Updated value"
        baseline="Server value"
        onValueChange={vi.fn()}
        serverUpdatedAt={null}
        baseVersion={1}
        save={save}
        onSaved={onSaved}
        renderField={({ onBlur }) => (
          <button type="button" onBlur={onBlur}>
            Trigger blur
          </button>
        )}
      />,
    );

    fireEvent.blur(screen.getByRole('button', { name: 'Trigger blur' }));

    await waitFor(() => {
      expect(save).toHaveBeenCalledWith('Updated value', { baseVersion: 1 });
    });
    expect(onSaved).toHaveBeenCalledWith({
      value: 'Updated value',
      baseVersion: 2,
      updatedAt: '2026-06-20T12:00:00Z',
    });
  });
});
