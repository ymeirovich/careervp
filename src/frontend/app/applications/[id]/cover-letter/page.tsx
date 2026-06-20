'use client';

import React, { useState, useEffect, use, Suspense, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { api } from '../../../../api/methods';
import { ConflictModal } from '../../../../components/ConflictModal';
import { ErrorBoundary } from '../../../../components/ErrorBoundary/ErrorBoundary';
import { ExportDropdown } from '../../../../components/ExportDropdown/ExportDropdown';
import { RichTextEditor } from '../../../../components/RichTextEditor/RichTextEditor';
import { RestoreDraftBanner } from '../../../../components/RestoreDraftBanner';
import { Spinner } from '../../../../components/ui/Spinner';
import { useArtifactAutosave } from '../../../../hooks/useArtifactAutosave';
import type { JobDetail } from '../../../../lib/types';

function CoverLetterContent({ jobId }: { jobId: string }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryId = searchParams.get('id');
  const isEditMode = searchParams.get('mode') === 'edit';

  const [fullText, setFullText] = useState<string | null>(null);
  const [artifactId, setArtifactId] = useState<string | null>(null);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const [editText, setEditText] = useState('');
  const [originalText, setOriginalText] = useState('');
  const [serverUpdatedAt, setServerUpdatedAt] = useState<string | null>(null);
  const [baseVersion, setBaseVersion] = useState<string | number | null>(null);

  const enterEditMode = useCallback(() => {
    const base = `/applications/${jobId}/cover-letter${queryId ? `?id=${queryId}` : ''}`;
    router.replace(`${base}${queryId ? '&' : '?'}mode=edit`);
  }, [jobId, queryId, router]);

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      const [hubResult, jobResult] = await Promise.allSettled([
        api.getApplication(jobId),
        api.getJob(jobId),
      ]);

      const hub = hubResult.status === 'fulfilled' ? hubResult.value : null;
      const jobData = jobResult.status === 'fulfilled' ? jobResult.value : null;
      setJob(jobData);

      const resolvedArtifactId = hub?.artifacts.cover_letter?.artifact_id ?? queryId;
      const artifactStatus = hub?.artifacts.cover_letter?.status;

      if (!resolvedArtifactId || (artifactStatus && artifactStatus !== 'completed' && !queryId)) {
        router.replace(`/applications/${jobId}`);
        return;
      }

      setArtifactId(resolvedArtifactId);

      try {
        const data = await api.getCoverLetter(resolvedArtifactId);
        const text = data.result?.cover_letter ?? null;
        setFullText(text);
        if (!text) {
          router.replace(`/applications/${jobId}`);
          return;
        }
        setEditText(text);
        setOriginalText(text);
        setServerUpdatedAt(data.updated_at ?? null);
        setBaseVersion(data.version ?? data.updated_at ?? null);
      } catch (err) {
        setError('Failed to load cover letter.');
        console.error(err);
        throw err;
      } finally {
        setLoading(false);
      }
    };
    void init();
  }, [jobId, queryId, router]);

  const exitEditMode = useCallback(() => {
    const base = `/applications/${jobId}/cover-letter${queryId ? `?id=${queryId}` : ''}`;
    router.replace(base);
  }, [jobId, queryId, router]);

  const autosave = useArtifactAutosave({
    artifactType: 'cover_letter',
    artifactId,
    fieldKey: 'cover_letter',
    value: editText,
    baseline: originalText,
    onValueChange: setEditText,
    serverUpdatedAt,
    baseVersion,
    save: async (nextValue, context) => {
      if (!artifactId) {
        return { value: nextValue, baseVersion: context.baseVersion, updatedAt: serverUpdatedAt };
      }
      const updated = await api.patchCoverLetter(artifactId, {
        cover_letter: nextValue,
        base_version: context.baseVersion,
      });
      return {
        value: updated.result?.cover_letter ?? nextValue,
        baseVersion: updated.version ?? updated.updated_at ?? context.baseVersion ?? null,
        updatedAt: updated.updated_at ?? new Date().toISOString(),
      };
    },
    onSaved: (result) => {
      setFullText(result.value);
      setEditText(result.value);
      setOriginalText(result.value);
      setServerUpdatedAt(result.updatedAt ?? serverUpdatedAt);
      setBaseVersion(result.baseVersion ?? baseVersion);
    },
    fetchLatest: async () => {
      if (!artifactId) {
        return { value: originalText, baseVersion, updatedAt: serverUpdatedAt };
      }
      const latest = await api.getCoverLetter(artifactId);
      return {
        value: latest.result?.cover_letter ?? '',
        baseVersion: latest.version ?? latest.updated_at ?? null,
        updatedAt: latest.updated_at ?? null,
      };
    },
    onReloaded: (result) => {
      setFullText(result.value);
      setEditText(result.value);
      setOriginalText(result.value);
      setServerUpdatedAt(result.updatedAt ?? null);
      setBaseVersion(result.baseVersion ?? null);
    },
  });

  const handleCancel = () => {
    setEditText(originalText);
    autosave.discardDraft();
    autosave.clearError();
    exitEditMode();
  };

  const handleCopy = async () => {
    const text = isEditMode ? editText : (fullText ?? '');
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard not available
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner size="lg" aria-label="Loading Cover Letter…" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-state-error/10 border border-state-error px-4 py-3 text-sm text-state-error">
        {error}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6" data-testid="cover-letter-page">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-text-primary">Cover Letter</h1>
            {isEditMode && autosave.isDirty && (
              <span className="rounded-full bg-state-warning/15 px-2.5 py-0.5 text-xs font-medium text-state-warning">
                Unsaved changes
              </span>
            )}
          </div>
          {job && (
            <p className="text-sm text-text-muted">{job.title} · {job.company_name}</p>
          )}
        </div>
        <div className="flex gap-2 shrink-0 flex-wrap">
          {isEditMode ? (
            <>
              <button
                onClick={() => {
                  void (async () => {
                    const didSave = await autosave.saveNow();
                    if (didSave) {
                      exitEditMode();
                    }
                  })();
                }}
                disabled={autosave.isSaving}
                className="rounded-md bg-primary-action px-3 py-2 text-sm font-bold text-white hover:opacity-90 disabled:opacity-60 flex items-center gap-2"
              >
                {autosave.isSaving && <Spinner size="sm" aria-label="" />}
                {autosave.isSaving ? 'Saving…' : 'Save'}
              </button>
              <button
                onClick={handleCancel}
                disabled={autosave.isSaving}
                className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle disabled:opacity-60"
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              {artifactId && (
                <button
                  onClick={enterEditMode}
                  className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle"
                  data-testid="cover-letter-edit-button"
                >
                  Edit
                </button>
              )}
              <button
                onClick={() => void handleCopy()}
                className="rounded-md bg-primary-action px-3 py-2 text-sm font-bold text-white hover:opacity-90"
                data-testid="copy-to-clipboard"
              >
                {copied ? 'Copied!' : 'Copy to Clipboard'}
              </button>
              {artifactId && (
                <ExportDropdown jobId={jobId} moduleType="cover_letter" artifactId={artifactId} companyName={job?.company_name ?? ''} jobTitle={job?.title ?? ''} />
              )}
            </>
          )}
          <button
            onClick={() => router.push(`/applications/${jobId}`)}
            className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle"
          >
            ← Back to Hub
          </button>
        </div>
      </div>

      {!isEditMode && copied && (
        <div className="rounded-md bg-state-active/10 border border-state-active px-4 py-3 text-sm font-medium text-state-active">
          Copied to clipboard
        </div>
      )}

      {autosave.draftBanner && (
        <RestoreDraftBanner
          updatedAt={autosave.draftBanner.updatedAt}
          onRestore={() => {
            autosave.draftBanner?.restore();
            if (!isEditMode) {
              enterEditMode();
            }
          }}
          onDiscard={() => autosave.draftBanner?.discard()}
        />
      )}

      {autosave.error && (
        <div className="rounded-md bg-state-error/10 border border-state-error px-4 py-3 text-sm text-state-error">
          {autosave.error}
        </div>
      )}

      <div className="rounded-md border border-border-default bg-card p-6 flex flex-col gap-4">
        <h2 className="text-base font-bold text-text-primary">Cover Letter</h2>
        {isEditMode ? (
          <RichTextEditor
            content={editText}
            onChange={setEditText}
            onBlur={autosave.onBlur}
            readOnly={autosave.isSaving}
            placeholder="Write your cover letter…"
          />
        ) : (
          fullText && (
            <div data-testid="cover-letter-text">
              <RichTextEditor
                content={fullText}
                onChange={() => undefined}
                readOnly
              />
            </div>
          )
        )}
      </div>

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

export default function CoverLetterPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: jobId } = use(params);
  return (
    <ErrorBoundary cloudwatchKey="cover-letter-page">
      <Suspense fallback={<div className="flex justify-center py-12"><Spinner size="lg" aria-label="Loading…" /></div>}>
        <CoverLetterContent jobId={jobId} />
      </Suspense>
    </ErrorBoundary>
  );
}
