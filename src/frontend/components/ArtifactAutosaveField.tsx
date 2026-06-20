import React from 'react';
import { ConflictModal } from './ConflictModal';
import { RestoreDraftBanner } from './RestoreDraftBanner';
import {
  type ArtifactAutosaveResult,
  type ArtifactBaseVersion,
  useArtifactAutosave,
} from '../hooks/useArtifactAutosave';

interface RenderState {
  onBlur: () => void;
  isDirty: boolean;
  isSaving: boolean;
}

interface ArtifactAutosaveFieldProps {
  artifactType: string;
  artifactId: string | null;
  fieldKey: string;
  value: string;
  baseline: string;
  onValueChange: (value: string) => void;
  serverUpdatedAt?: string | null;
  baseVersion?: ArtifactBaseVersion;
  save: (value: string, context: { baseVersion: ArtifactBaseVersion }) => Promise<ArtifactAutosaveResult>;
  onSaved: (result: ArtifactAutosaveResult) => void;
  fetchLatest?: () => Promise<ArtifactAutosaveResult>;
  onReloaded?: (result: ArtifactAutosaveResult) => void;
  onRequestEdit?: () => void;
  renderField: (state: RenderState) => React.ReactNode;
}

export function ArtifactAutosaveField({
  artifactType,
  artifactId,
  fieldKey,
  value,
  baseline,
  onValueChange,
  serverUpdatedAt,
  baseVersion,
  save,
  onSaved,
  fetchLatest,
  onReloaded,
  onRequestEdit,
  renderField,
}: ArtifactAutosaveFieldProps) {
  const autosave = useArtifactAutosave({
    artifactType,
    artifactId,
    fieldKey,
    value,
    baseline,
    onValueChange,
    serverUpdatedAt,
    baseVersion,
    save,
    onSaved,
    fetchLatest,
    onReloaded,
  });

  return (
    <div className="flex flex-col gap-3">
      {autosave.draftBanner && (
        <RestoreDraftBanner
          updatedAt={autosave.draftBanner.updatedAt}
          onRestore={() => {
            autosave.draftBanner?.restore();
            onRequestEdit?.();
          }}
          onDiscard={() => autosave.draftBanner?.discard()}
        />
      )}

      {autosave.error && (
        <div className="rounded-md border border-state-error bg-state-error/10 px-4 py-3 text-sm text-state-error">
          {autosave.error}
        </div>
      )}

      {renderField({
        onBlur: autosave.onBlur,
        isDirty: autosave.isDirty,
        isSaving: autosave.isSaving,
      })}

      {autosave.conflict && (
        <ConflictModal
          message={autosave.conflict.message}
          onDismiss={autosave.conflict.dismiss}
          onReload={autosave.conflict.reload}
          onOverwrite={autosave.conflict.overwrite}
        />
      )}
    </div>
  );
}

export default ArtifactAutosaveField;
