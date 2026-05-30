'use client';

import React, { useId, useState } from 'react';
import { Save as SaveIcon } from 'lucide-react';
import { RichTextEditor } from '../RichTextEditor';
import type { GapQuestion } from '../../lib/types';

export interface GapQuestionCardProps {
  question: GapQuestion;
  questionIndex: number;
  response: string | null;
  destination: 'CV_IMPACT' | 'INTERVIEW_MVP_ONLY' | '';
  isEditing: boolean;
  onRequestEdit: () => void;
  onSave: (data: {
    questionId: string;
    response: string;
    destination: 'CV_IMPACT' | 'INTERVIEW_MVP_ONLY';
  }) => Promise<void>;
  onCancel: () => void;
}

type SaveState = 'idle' | 'saving' | 'error';

function impactBadgeClass(v?: string): string {
  if (v === 'HIGH') return 'bg-state-active/10 text-state-active';
  if (v === 'MEDIUM') return 'bg-state-warning/10 text-state-warning';
  return 'bg-surface-subtle text-text-muted';
}

export function GapQuestionCard({
  question,
  questionIndex,
  response,
  destination,
  isEditing,
  onRequestEdit,
  onSave,
  onCancel,
}: GapQuestionCardProps) {
  const questionTextId = useId();
  const [editorContent, setEditorContent] = useState(response ?? '');
  const [localDestination, setLocalDestination] = useState<'CV_IMPACT' | 'INTERVIEW_MVP_ONLY'>(
    destination || 'CV_IMPACT',
  );
  const [saveState, setSaveState] = useState<SaveState>('idle');

  const hasResponse = Boolean(response);

  const handleAnswerOrEdit = () => {
    if (!isEditing) {
      setEditorContent(response ?? '');
      setLocalDestination(destination || 'CV_IMPACT');
      setSaveState('idle');
      onRequestEdit();
    }
  };

  const handleSave = async () => {
    setSaveState('saving');
    try {
      await onSave({
        questionId: question.question_id,
        response: editorContent,
        destination: localDestination,
      });
      setSaveState('idle');
    } catch {
      setSaveState('error');
    }
  };

  const handleCancel = () => {
    setEditorContent(response ?? '');
    setLocalDestination(destination || 'CV_IMPACT');
    setSaveState('idle');
    onCancel();
  };

  const isSaving = saveState === 'saving';

  return (
    <div className="rounded-xl border border-border-default shadow-sm p-4 bg-card">
      {/* Header row: question number + text + badges */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p id={questionTextId} className="text-sm font-medium text-text-primary">
            <span className="font-semibold">{questionIndex + 1}.</span> {question.question}
          </p>

          {/* Impact / probability badges */}
          <div className="mt-1 flex flex-wrap items-center gap-2">
            {question.impact && (
              <span
                className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold ${impactBadgeClass(question.impact)}`}
              >
                Impact: {question.impact}
              </span>
            )}
            {question.probability && (
              <span
                className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold ${impactBadgeClass(question.probability)}`}
              >
                Prob: {question.probability}
              </span>
            )}
          </div>
        </div>

        {/* Action button — read state only */}
        {!isEditing && (
          <div className="shrink-0 mt-1">
            {hasResponse ? (
              <button
                type="button"
                onClick={handleAnswerOrEdit}
                className="rounded-md border border-primary-action bg-transparent px-3 py-1.5 text-sm font-medium text-primary-action hover:bg-primary-action/10 transition-colors"
              >
                Edit
              </button>
            ) : (
              <button
                type="button"
                onClick={handleAnswerOrEdit}
                className="rounded-md bg-primary-action px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-action/90 transition-colors"
              >
                Answer
              </button>
            )}
          </div>
        )}
      </div>

      {/* Read-state response block */}
      {!isEditing && hasResponse && (
        <div className="mt-3 bg-surface-subtle rounded-lg p-3">
          <RichTextEditor
            content={response!}
            onChange={() => undefined}
            readOnly
            ariaLabelledBy={questionTextId}
          />
        </div>
      )}

      {/* Edit state */}
      {isEditing && (
        <div className="mt-3 space-y-3">
          <RichTextEditor
            content={editorContent}
            onChange={setEditorContent}
            readOnly={isSaving}
            ariaLabelledBy={questionTextId}
          />

          {/* Advanced options — collapsed */}
          <details className="text-sm">
            <summary className="cursor-pointer select-none font-medium text-text-secondary hover:text-text-primary">
              Advanced options
            </summary>
            <div className="mt-2 space-y-1 pl-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name={`destination-${question.question_id}`}
                  value="CV_IMPACT"
                  checked={localDestination === 'CV_IMPACT'}
                  onChange={() => setLocalDestination('CV_IMPACT')}
                />
                <span>Include in CV</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name={`destination-${question.question_id}`}
                  value="INTERVIEW_MVP_ONLY"
                  checked={localDestination === 'INTERVIEW_MVP_ONLY'}
                  onChange={() => setLocalDestination('INTERVIEW_MVP_ONLY')}
                />
                <span>Interview Only</span>
              </label>
            </div>
          </details>

          {/* Error message */}
          {saveState === 'error' && (
            <p className="text-sm text-state-error" role="alert">
              Failed to save. Please try again.
            </p>
          )}

          {/* Save / Cancel row */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleCancel}
              disabled={isSaving}
              className="text-sm font-medium text-text-secondary hover:text-text-primary disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving}
              className="inline-flex items-center gap-1.5 rounded-md bg-primary-action px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-action/90 disabled:opacity-70 transition-colors"
            >
              {isSaving ? (
                <span
                  className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent"
                  role="status"
                  aria-label="Saving"
                />
              ) : (
                <SaveIcon className="h-4 w-4" aria-hidden />
              )}
              Save
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default GapQuestionCard;
