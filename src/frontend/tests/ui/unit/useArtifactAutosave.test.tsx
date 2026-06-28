import React from 'react';
import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useArtifactAutosave } from '../../../hooks/useArtifactAutosave';

describe('useArtifactAutosave', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('surfaces a restore banner when a newer local draft exists', () => {
    localStorage.setItem(
      'careervp:draft:cover_letter:artifact-1:cover_letter',
      JSON.stringify({
        markdown: 'Local draft',
        updatedAt: '2026-06-20T12:00:00Z',
        baseVersion: null,
      }),
    );

    const { result } = renderHook(() =>
      useArtifactAutosave({
        artifactType: 'cover_letter',
        artifactId: 'artifact-1',
        fieldKey: 'cover_letter',
        value: 'Server value',
        baseline: 'Server value',
        onValueChange: vi.fn(),
        serverUpdatedAt: '2026-06-20T10:00:00Z',
        baseVersion: null,
        save: vi.fn(),
        onSaved: vi.fn(),
      }));

    expect(result.current.draftBanner).not.toBeNull();
  });

  it('does not save on blur when the field is clean', async () => {
    const save = vi.fn();

    const { result } = renderHook(() =>
      useArtifactAutosave({
        artifactType: 'cover_letter',
        artifactId: 'artifact-1',
        fieldKey: 'cover_letter',
        value: 'Same value',
        baseline: 'Same value',
        onValueChange: vi.fn(),
        serverUpdatedAt: null,
        baseVersion: null,
        save,
        onSaved: vi.fn(),
      }));

    result.current.onBlur();

    expect(save).not.toHaveBeenCalled();
  });
});
