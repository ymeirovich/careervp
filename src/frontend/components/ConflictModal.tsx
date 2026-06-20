import React from 'react';

interface ConflictModalProps {
  message?: string;
  onReload: () => void | Promise<void>;
  onOverwrite: () => void | Promise<void>;
  onDismiss: () => void;
}

export function ConflictModal({
  message = 'This field changed on the server after you loaded it.',
  onReload,
  onOverwrite,
  onDismiss,
}: ConflictModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4" role="dialog" aria-modal="true" aria-labelledby="autosave-conflict-title">
      <div className="w-full max-w-md rounded-xl border border-border-default bg-card p-6 shadow-xl">
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <h2 id="autosave-conflict-title" className="text-lg font-bold text-text-primary">
              Save conflict
            </h2>
            <p className="text-sm text-text-secondary">{message}</p>
          </div>
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onDismiss}
              className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle"
            >
              Close
            </button>
            <button
              type="button"
              onClick={() => void onReload()}
              className="rounded-md border border-border-default px-3 py-2 text-sm text-text-primary hover:bg-surface-subtle"
            >
              Reload
            </button>
            <button
              type="button"
              onClick={() => void onOverwrite()}
              className="rounded-md bg-primary-action px-3 py-2 text-sm font-bold text-white hover:opacity-90"
            >
              Overwrite
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ConflictModal;
