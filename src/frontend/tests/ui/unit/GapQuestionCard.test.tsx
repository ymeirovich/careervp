import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { GapQuestionCard } from '../../../components/GapQuestionCard';
import type { GapQuestion } from '../../../lib/types';

// TipTap requires DOM range methods — polyfill for jsdom
function emptyClientRects(): DOMRectList {
  return {
    item: () => null,
    length: 0,
    [Symbol.iterator]: function* iterator() { return; },
  } as DOMRectList;
}
function emptyBoundingRect(): DOMRect {
  return new DOMRect(0, 0, 0, 0);
}

const baseQuestion: GapQuestion = {
  question_id: 'q1',
  question: 'Describe your Python experience',
  impact: 'HIGH',
  probability: 'MEDIUM',
  gap_score: 0.8,
  tags: [],
};

function makeProps(overrides: Partial<React.ComponentProps<typeof GapQuestionCard>> = {}) {
  return {
    question: baseQuestion,
    questionIndex: 0,
    applicationId: 'test-app-id',
    response: null,
    destination: '' as const,
    isEditing: false,
    onRequestEdit: vi.fn(),
    onSave: vi.fn().mockResolvedValue(undefined),
    onCancel: vi.fn(),
    ...overrides,
  };
}

function clickButton(name: string | RegExp) {
  fireEvent.click(screen.getByRole('button', { name }));
}

describe('GapQuestionCard', () => {
  beforeAll(() => {
    Object.defineProperty(Element.prototype, 'getClientRects', {
      configurable: true,
      value: emptyClientRects,
    });
    Object.defineProperty(Range.prototype, 'getClientRects', {
      configurable: true,
      value: emptyClientRects,
    });
    Object.defineProperty(Range.prototype, 'getBoundingClientRect', {
      configurable: true,
      value: emptyBoundingRect,
    });
    Object.defineProperty(Text.prototype, 'getClientRects', {
      configurable: true,
      value: emptyClientRects,
    });
  });

  // AC-001: unanswered read state shows orange "Answer" button
  it('shows question number, text, and Answer button when no response', () => {
    render(<GapQuestionCard {...makeProps()} />);
    expect(screen.getByText(/Describe your Python experience/)).toBeInTheDocument();
    expect(screen.getByText('1.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Answer' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument();
  });

  // AC-002: answered read state shows response block and "Edit" button
  it('shows Edit button and response block when response exists', () => {
    render(
      <GapQuestionCard
        {...makeProps({ response: 'I have 5 years of Python experience' })}
      />,
    );
    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Answer' })).not.toBeInTheDocument();
    const editors = screen.getAllByTestId('rich-text-editor');
    expect(editors.length).toBeGreaterThanOrEqual(1);
  });

  // AC-003: isEditing=true renders RichTextEditor + Save/Cancel
  it('renders RichTextEditor, Save, and Cancel when isEditing=true', () => {
    render(<GapQuestionCard {...makeProps({ isEditing: true })} />);
    expect(screen.getByTestId('rich-text-editor')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Save/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
  });

  // AC-003: editor present with existing response in edit mode
  it('shows editor in edit mode regardless of existing response', () => {
    render(
      <GapQuestionCard
        {...makeProps({ isEditing: true, response: 'Existing response text' })}
      />,
    );
    expect(screen.getByTestId('rich-text-editor')).toBeInTheDocument();
  });

  // AC-004: saving state — spinner and disabled Save button
  it('shows spinner and disables Save while saving', async () => {
    let resolvePromise!: () => void;
    const slowSave = vi.fn(
      () => new Promise<void>((res) => { resolvePromise = res; }),
    );

    render(<GapQuestionCard {...makeProps({ isEditing: true, onSave: slowSave })} />);
    act(() => { clickButton(/Save/); });

    const saveBtn = screen.getByRole('button', { name: /Save/ });
    expect(saveBtn).toBeDisabled();
    expect(screen.getByRole('status', { name: 'Saving' })).toBeInTheDocument();

    await act(async () => { resolvePromise(); });
    await waitFor(() => expect(saveBtn).not.toBeDisabled());
  });

  // AC-005: onSave rejection shows inline error and re-enables Save
  it('shows error message and re-enables Save on failure', async () => {
    const failSave = vi.fn().mockRejectedValue(new Error('Network error'));

    render(<GapQuestionCard {...makeProps({ isEditing: true, onSave: failSave })} />);
    await act(async () => { clickButton(/Save/); });

    await waitFor(() =>
      expect(screen.getByText('Failed to save. Please try again.')).toBeInTheDocument(),
    );
    expect(screen.getByRole('button', { name: /Save/ })).not.toBeDisabled();
  });

  // AC-006: Cancel calls onCancel
  it('calls onCancel when Cancel clicked', async () => {
    const onCancel = vi.fn();

    render(<GapQuestionCard {...makeProps({ isEditing: true, onCancel })} />);
    await act(async () => { clickButton('Cancel'); });

    expect(onCancel).toHaveBeenCalledOnce();
  });

  // AC-007: impact and probability badges always visible
  it('renders Impact and Prob badges in read state', () => {
    render(<GapQuestionCard {...makeProps()} />);
    expect(screen.getByText('Impact: HIGH')).toBeInTheDocument();
    expect(screen.getByText('Prob: MEDIUM')).toBeInTheDocument();
  });

  it('renders Impact and Prob badges in edit state', () => {
    render(<GapQuestionCard {...makeProps({ isEditing: true })} />);
    expect(screen.getByText('Impact: HIGH')).toBeInTheDocument();
    expect(screen.getByText('Prob: MEDIUM')).toBeInTheDocument();
  });

  // AC-009: saves with CV_IMPACT by default
  it('sends CV_IMPACT when user saves', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);

    render(<GapQuestionCard {...makeProps({ isEditing: true, onSave, destination: '' })} />);
    await act(async () => { clickButton(/Save/); });

    await waitFor(() => expect(onSave).toHaveBeenCalled());
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ destination: 'CV_IMPACT' }),
    );
  });

  // AC-010: isEditing=false — clicking Answer calls onRequestEdit, no self-transition
  it('calls onRequestEdit and does not self-transition when Answer clicked (isEditing=false)', async () => {
    const onRequestEdit = vi.fn();

    render(<GapQuestionCard {...makeProps({ onRequestEdit })} />);
    await act(async () => { clickButton('Answer'); });

    expect(onRequestEdit).toHaveBeenCalledOnce();
    expect(screen.queryByTestId('rich-text-editor')).not.toBeInTheDocument();
  });

  it('calls onRequestEdit when Edit clicked (answered, isEditing=false)', async () => {
    const onRequestEdit = vi.fn();

    render(
      <GapQuestionCard
        {...makeProps({ response: 'Some answer', onRequestEdit })}
      />,
    );
    await act(async () => { clickButton('Edit'); });
    expect(onRequestEdit).toHaveBeenCalledOnce();
  });

  // AC-011/AC-012: plain text and Markdown render in read-only editor
  it('renders plain text response in read state without crashing', () => {
    render(
      <GapQuestionCard
        {...makeProps({ response: 'Plain text response without formatting' })}
      />,
    );
    expect(screen.getAllByTestId('rich-text-editor').length).toBeGreaterThanOrEqual(1);
  });

  // AC-013: editor has aria-labelledby pointing to question text
  it('sets aria-labelledby on editor pointing to question text', () => {
    render(<GapQuestionCard {...makeProps({ isEditing: true })} />);
    const editor = screen.getByRole('textbox');
    const labelledById = editor.getAttribute('aria-labelledby');
    expect(labelledById).toBeTruthy();
    const labelEl = document.getElementById(labelledById!);
    expect(labelEl).toBeInTheDocument();
    expect(labelEl!.textContent).toContain('Describe your Python experience');
  });

  // AC-014: toolbar buttons have aria-labels
  it('toolbar buttons have aria-labels in edit mode', () => {
    render(<GapQuestionCard {...makeProps({ isEditing: true })} />);
    expect(screen.getByRole('button', { name: 'Bold' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Italic' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Underline' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Bullet list' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Numbered list' })).toBeInTheDocument();
  });

  // onSave called with correct questionId
  it('passes questionId to onSave', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);

    render(<GapQuestionCard {...makeProps({ isEditing: true, onSave })} />);
    await act(async () => { clickButton(/Save/); });

    await waitFor(() => expect(onSave).toHaveBeenCalled());
    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({ questionId: 'q1' }),
    );
  });
});
