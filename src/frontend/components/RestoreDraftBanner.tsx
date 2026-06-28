import React from 'react';

interface RestoreDraftBannerProps {
  updatedAt?: string | null;
  onRestore: () => void;
  onDiscard: () => void;
}

function formatUpdatedAt(updatedAt?: string | null): string | null {
  if (!updatedAt) return null;
  const parsed = Date.parse(updatedAt);
  if (Number.isNaN(parsed)) return null;

  return new Intl.DateTimeFormat('en', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(parsed));
}

export function RestoreDraftBanner({
  updatedAt,
  onRestore,
  onDiscard,
}: RestoreDraftBannerProps) {
  const formattedUpdatedAt = formatUpdatedAt(updatedAt);

  return (
    <div className="rounded-md border border-state-warning bg-state-warning/10 px-4 py-3 text-sm text-text-primary">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-col gap-1">
          <p className="font-medium">Restore unsaved changes?</p>
          {formattedUpdatedAt && (
            <p className="text-xs text-text-muted">Local draft from {formattedUpdatedAt}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onRestore}
            className="rounded-md bg-primary-action px-3 py-2 text-sm font-bold text-white hover:opacity-90"
          >
            Restore
          </button>
          <button
            type="button"
            onClick={onDiscard}
            className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle"
          >
            Discard
          </button>
        </div>
      </div>
    </div>
  );
}

export default RestoreDraftBanner;
