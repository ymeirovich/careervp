'use client';

import { useEffect, useRef, useState } from 'react';
import { ApiError } from '../api/client';
import { normalizeMarkdown } from '../components/RichTextEditor/markdownSerializer';

export type ArtifactBaseVersion = string | number | null;

export interface ArtifactAutosaveResult {
  value: string;
  baseVersion?: ArtifactBaseVersion;
  updatedAt?: string | null;
  metadata?: unknown;
}

interface DraftRecord {
  markdown: string;
  updatedAt: string;
  baseVersion: ArtifactBaseVersion;
}

interface ConflictState {
  message: string;
}

interface UseArtifactAutosaveOptions {
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
}

interface DraftBannerState {
  updatedAt: string;
  value: string;
  baseVersion: ArtifactBaseVersion;
}

function buildDraftKey(artifactType: string, artifactId: string, fieldKey: string): string {
  return `careervp:draft:${artifactType}:${artifactId}:${fieldKey}`;
}

function readDraft(key: string): DraftRecord | null {
  const raw = localStorage.getItem(key);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as Partial<DraftRecord>;
    if (typeof parsed.markdown !== 'string' || typeof parsed.updatedAt !== 'string') {
      localStorage.removeItem(key);
      return null;
    }
    return {
      markdown: parsed.markdown,
      updatedAt: parsed.updatedAt,
      baseVersion: parsed.baseVersion ?? null,
    };
  } catch {
    localStorage.removeItem(key);
    return null;
  }
}

function writeDraft(key: string, value: string, baseVersion: ArtifactBaseVersion): void {
  const payload: DraftRecord = {
    markdown: value,
    updatedAt: new Date().toISOString(),
    baseVersion,
  };
  localStorage.setItem(key, JSON.stringify(payload));
}

function parseTimestamp(value: string | null | undefined): number | null {
  if (!value) return null;
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? null : timestamp;
}

function isConflictError(error: unknown): boolean {
  return error instanceof ApiError && error.status === 409;
}

export function useArtifactAutosave({
  artifactType,
  artifactId,
  fieldKey,
  value,
  baseline,
  onValueChange,
  serverUpdatedAt,
  baseVersion = null,
  save,
  onSaved,
  fetchLatest,
  onReloaded,
}: UseArtifactAutosaveOptions) {
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftBanner, setDraftBanner] = useState<DraftBannerState | null>(null);
  const [conflictState, setConflictState] = useState<ConflictState | null>(null);

  const saveInFlightRef = useRef<Promise<boolean> | null>(null);
  const valueRef = useRef(value);
  const baselineRef = useRef(baseline);
  const baseVersionRef = useRef<ArtifactBaseVersion>(baseVersion);
  const latestInspectionKeyRef = useRef<string | null>(null);
  const hasMountedRef = useRef(false);

  valueRef.current = value;
  baselineRef.current = baseline;
  baseVersionRef.current = baseVersion;

  const draftKey = artifactId ? buildDraftKey(artifactType, artifactId, fieldKey) : null;
  const isDirty = normalizeMarkdown(value) !== normalizeMarkdown(baseline);

  useEffect(() => {
    if (!draftKey) return;

    const inspectionKey = `${draftKey}:${serverUpdatedAt ?? ''}`;
    if (latestInspectionKeyRef.current === inspectionKey) return;
    latestInspectionKeyRef.current = inspectionKey;

    const draft = readDraft(draftKey);
    if (!draft) {
      setDraftBanner(null);
      return;
    }

    const localUpdatedAt = parseTimestamp(draft.updatedAt);
    const remoteUpdatedAt = parseTimestamp(serverUpdatedAt);
    const shouldRestore =
      localUpdatedAt !== null
      && (remoteUpdatedAt === null || localUpdatedAt > remoteUpdatedAt);

    if (!shouldRestore) {
      localStorage.removeItem(draftKey);
      setDraftBanner(null);
      return;
    }

    setDraftBanner({
      updatedAt: draft.updatedAt,
      value: draft.markdown,
      baseVersion: draft.baseVersion,
    });
  }, [draftKey, serverUpdatedAt]);

  useEffect(() => {
    if (!draftKey) return;

    if (!hasMountedRef.current) {
      hasMountedRef.current = true;
      return;
    }

    if (!isDirty) {
      localStorage.removeItem(draftKey);
      return;
    }

    writeDraft(draftKey, value, baseVersionRef.current);
  }, [baseVersion, draftKey, isDirty, value]);

  useEffect(() => {
    if (!isSaving) return;

    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = '';
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isSaving]);

  useEffect(() => {
    return () => {
      if (!draftKey || saveInFlightRef.current || !isDirty) return;
      void save(valueRef.current, { baseVersion: baseVersionRef.current }).catch(() => undefined);
    };
  }, [draftKey, isDirty, save]);

  const clearDraft = () => {
    if (!draftKey) return;
    localStorage.removeItem(draftKey);
    setDraftBanner(null);
  };

  const persist = async (nextValue: string, versionOverride?: ArtifactBaseVersion): Promise<boolean> => {
    if (!artifactId) return false;
    if (normalizeMarkdown(nextValue) === normalizeMarkdown(baselineRef.current)) {
      clearDraft();
      return true;
    }
    if (saveInFlightRef.current) {
      await saveInFlightRef.current;
      return false;
    }

    const versionToSend = versionOverride ?? baseVersionRef.current;
    if (draftKey) {
      writeDraft(draftKey, nextValue, versionToSend);
    }

    const savePromise = (async () => {
      setIsSaving(true);
      setError(null);

      try {
        const result = await save(nextValue, { baseVersion: versionToSend });
        onSaved(result);
        clearDraft();
        setConflictState(null);
        return true;
      } catch (saveError) {
        if (isConflictError(saveError)) {
          setConflictState({
            message: 'A newer server version exists for this field.',
          });
          return false;
        }

        setError('Autosave failed. Your draft is still stored locally.');
        return false;
      } finally {
        setIsSaving(false);
        saveInFlightRef.current = null;
      }
    })();

    saveInFlightRef.current = savePromise;
    return savePromise;
  };

  const restoreDraft = () => {
    if (!draftBanner) return;
    onValueChange(draftBanner.value);
    baseVersionRef.current = draftBanner.baseVersion;
    setDraftBanner(null);
    setError(null);
  };

  const discardDraft = () => {
    clearDraft();
    setError(null);
  };

  const reloadFromServer = async () => {
    if (!fetchLatest || !onReloaded) return;
    setError(null);
    const latest = await fetchLatest();
    onReloaded(latest);
    clearDraft();
    setConflictState(null);
  };

  const overwrite = async () => {
    if (!fetchLatest) return;
    setError(null);
    try {
      const latest = await fetchLatest();
      await persist(valueRef.current, latest.baseVersion ?? null);
    } catch {
      setError('Unable to resolve the conflict. Please reload and try again.');
    }
  };

  return {
    onBlur: () => {
      void persist(valueRef.current);
    },
    isDirty,
    isSaving,
    saveNow: () => persist(valueRef.current),
    error,
    clearError: () => setError(null),
    discardDraft,
    draftBanner: draftBanner
      ? {
          updatedAt: draftBanner.updatedAt,
          restore: restoreDraft,
          discard: discardDraft,
        }
      : null,
    conflict: conflictState
      ? {
          message: conflictState.message,
          dismiss: () => setConflictState(null),
          reload: reloadFromServer,
          overwrite,
        }
      : null,
  };
}

export default useArtifactAutosave;
