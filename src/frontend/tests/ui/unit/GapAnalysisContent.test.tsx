import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import type { GapQuestionCardProps } from '../../../components/GapQuestionCard/GapQuestionCard';

// ---------------------------------------------------------------------------
// Hoisted mocks
// ---------------------------------------------------------------------------

const apiMocks = vi.hoisted(() => ({
  getGapQuestions: vi.fn(),
  getApplication: vi.fn(),
  saveGapResponses: vi.fn(),
}));

// Capture latest rendered card props for interaction tests
type CardSnapshot = Pick<GapQuestionCardProps, 'question' | 'questionIndex' | 'response' | 'destination' | 'isEditing' | 'onRequestEdit' | 'onSave' | 'onCancel'>;
let cardSnapshots: CardSnapshot[] = [];

vi.mock('../../../components/GapQuestionCard/GapQuestionCard', () => ({
  GapQuestionCard: (props: GapQuestionCardProps) => {
    cardSnapshots[props.questionIndex] = { ...props };
    return (
      <div
        data-testid={`question-row-${props.questionIndex}`}
        data-editing={String(props.isEditing)}
        data-question-id={props.question.question_id}
      >
        <span data-testid={`q-text-${props.questionIndex}`}>{props.question.question}</span>
        <button
          data-testid={`request-edit-${props.questionIndex}`}
          onClick={props.onRequestEdit}
        >
          {props.response ? 'Edit' : 'Answer'}
        </button>
        <button
          data-testid={`mock-save-${props.questionIndex}`}
          onClick={() =>
            void props.onSave({
              questionId: props.question.question_id,
              response: 'saved answer',
              destination: 'CV_IMPACT',
            })
          }
        >
          Save
        </button>
        <button data-testid={`mock-cancel-${props.questionIndex}`} onClick={props.onCancel}>
          Cancel
        </button>
      </div>
    );
  },
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => ({ get: () => null }),
  useParams: () => ({ id: 'job1' }),
}));

vi.mock('../../../api/methods', () => ({
  api: apiMocks,
}));

vi.mock('../../../components/ErrorBoundary/ErrorBoundary', () => ({
  ErrorBoundary: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const QUESTIONS = [
  { question_id: 'q1', question: 'Describe your Python experience', impact: 'HIGH' as const, probability: 'HIGH' as const, gap_score: 8, tags: [] },
  { question_id: 'q2', question: 'How have you handled deadlines?', impact: 'MEDIUM' as const, probability: 'LOW' as const, gap_score: 5, tags: [] },
  { question_id: 'q3', question: 'Describe a leadership situation', impact: 'LOW' as const, probability: 'MEDIUM' as const, gap_score: 3, tags: [] },
  { question_id: 'q4', question: 'What is your team experience?', impact: 'HIGH' as const, probability: 'HIGH' as const, gap_score: 7, tags: [] },
  { question_id: 'q5', question: 'Describe a conflict resolution', impact: 'MEDIUM' as const, probability: 'MEDIUM' as const, gap_score: 4, tags: [] },
];

const HUB_EMPTY = {
  application: { application_id: 'job1', state: 'active', created_at: '', trial_credit_consumed: false },
  job: { job_id: 'job1', user_id: 'u1', title: 'Engineer', company_name: 'Acme', status: 'active', created_at: '', requirements: [] },
  cv: { cv_id: 'cv1' },
  gap_analysis: { questions: [], responses: [] },
  artifacts: {
    vpr: { status: 'pending' as const, artifact_id: null },
    cover_letter: { status: 'pending' as const, artifact_id: null },
    interview_prep: { status: 'pending' as const, artifact_id: null },
    cv_tailored: { status: 'pending' as const, artifact_id: null },
    gap_analysis: { status: 'pending' as const, artifact_id: null },
  },
};

const hubWith2Answered = {
  ...HUB_EMPTY,
  gap_analysis: {
    questions: [],
    responses: [
      { question_id: 'q1', response: 'I have 3 years Python experience' },
      { question_id: 'q2', response: 'I prioritize tasks by deadline' },
    ],
  },
};

// ---------------------------------------------------------------------------
// Import page (dynamic to pick up mocks)
// ---------------------------------------------------------------------------

let GapAnalysisPage: React.ComponentType<{ params: Promise<{ id: string }> }>;

beforeEach(async () => {
  vi.clearAllMocks();
  cardSnapshots = [];
  document.documentElement.lang = 'en';
  window.history.pushState({}, '', '/applications/job1/gap-analysis');

  apiMocks.getApplication.mockResolvedValue(HUB_EMPTY);
  apiMocks.getGapQuestions.mockResolvedValue(QUESTIONS);
  apiMocks.saveGapResponses.mockResolvedValue(undefined);

  const mod = await import('../../../app/applications/[id]/gap-analysis/page');
  GapAnalysisPage = mod.default;
});

afterEach(() => {
  vi.restoreAllMocks();
});

function renderPage() {
  return render(<GapAnalysisPage params={Promise.resolve({ id: 'job1' })} />);
}

async function renderAndWait() {
  renderPage();
  await waitFor(() => expect(screen.getByTestId('questions-list')).toBeDefined());
}

// ---------------------------------------------------------------------------
// AC-001: skeleton cards while loading
// ---------------------------------------------------------------------------

describe('AC-001 — loading skeleton', () => {
  it('shows 3 skeleton cards before data arrives', () => {
    let resolveQuestions!: (v: typeof QUESTIONS) => void;
    apiMocks.getGapQuestions.mockReturnValue(new Promise((r) => { resolveQuestions = r; }));

    renderPage();

    expect(screen.getByTestId('skeleton-cards')).toBeDefined();
    expect(screen.queryByTestId('questions-list')).toBeNull();

    act(() => resolveQuestions(QUESTIONS));
  });

  it('does not show a centered spinner while loading', () => {
    let resolve!: (v: typeof QUESTIONS) => void;
    apiMocks.getGapQuestions.mockReturnValue(new Promise((r) => { resolve = r; }));

    renderPage();

    expect(screen.queryByRole('status')).toBeNull();
    act(() => resolve(QUESTIONS));
  });
});

// ---------------------------------------------------------------------------
// AC-002: page title styling
// ---------------------------------------------------------------------------

describe('AC-002 — page title', () => {
  it('displays "Gap Analysis Questions" with text-2xl font-bold', async () => {
    await renderAndWait();

    const title = screen.getByTestId('page-title');
    expect(title).toHaveTextContent('Gap Analysis Questions');
    expect(title.className).toMatch(/text-2xl/);
    expect(title.className).toMatch(/font-bold/);
  });
});

// ---------------------------------------------------------------------------
// AC-003: subtitle text
// ---------------------------------------------------------------------------

describe('AC-003 — subtitle', () => {
  it('displays the correct subtitle', async () => {
    await renderAndWait();

    expect(screen.getByTestId('page-subtitle')).toHaveTextContent(
      'Answer some questions to fill in gaps between your CV and this role',
    );
  });
});

// ---------------------------------------------------------------------------
// AC-004: back link
// ---------------------------------------------------------------------------

describe('AC-004 — back link', () => {
  it('renders "← Back" link pointing to /applications/job1', async () => {
    await renderAndWait();

    const link = screen.getByTestId('back-link');
    expect(link).toHaveTextContent('← Back');
    expect(link).toHaveAttribute('href', '/applications/job1');
  });

  it('back link renders before the subtitle in DOM order', async () => {
    await renderAndWait();

    const backLink = screen.getByTestId('back-link');
    const subtitle = screen.getByTestId('page-subtitle');
    expect(
      backLink.compareDocumentPosition(subtitle) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// AC-005: progress bar value and label
// ---------------------------------------------------------------------------

describe('AC-005 — progress bar', () => {
  it('shows "2 out of 5 answered" when 2 of 5 questions have saved responses', async () => {
    apiMocks.getApplication.mockResolvedValue(hubWith2Answered);

    renderPage();
    await waitFor(() => expect(screen.getByTestId('questions-list')).toBeDefined());

    expect(screen.getByTestId('progress-label')).toHaveTextContent('2 out of 5 answered');
  });

  it('progress bar value updates after a question is saved', async () => {
    apiMocks.getApplication.mockResolvedValue(HUB_EMPTY);
    await renderAndWait();

    expect(screen.getByTestId('progress-label')).toHaveTextContent('0 out of 5 answered');

    // Simulate saving q1
    await act(async () => {
      fireEvent.click(screen.getByTestId('mock-save-0'));
      await Promise.resolve();
    });

    await waitFor(() =>
      expect(screen.getByTestId('progress-label')).toHaveTextContent('1 out of 5 answered'),
    );
  });
});

// ---------------------------------------------------------------------------
// AC-006: no global Edit/Save/Cancel bar
// ---------------------------------------------------------------------------

describe('AC-006 — no global edit bar', () => {
  it('does not render a sticky global save-responses bar', async () => {
    await renderAndWait();

    // The old sticky header had data-testid="save-responses" — it must not exist
    expect(screen.queryByTestId('save-responses')).toBeNull();
    // No element with the sticky/global-edit-bar structure
    expect(document.querySelector('[class*="sticky"]')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// AC-007: no Generate Questions button
// ---------------------------------------------------------------------------

describe('AC-007 — no generate button', () => {
  it('does not render a Generate Questions button', async () => {
    await renderAndWait();

    expect(screen.queryByTestId('generate-gap-questions')).toBeNull();
    expect(screen.queryByRole('button', { name: /generate questions/i })).toBeNull();
  });

  it('does not show a generate button even when there are no questions', async () => {
    apiMocks.getGapQuestions.mockResolvedValue([]);

    renderPage();
    await waitFor(() => expect(screen.getByTestId('empty-state')).toBeDefined());

    expect(screen.queryByRole('button', { name: /generate/i })).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// AC-008: empty state
// ---------------------------------------------------------------------------

describe('AC-008 — empty state', () => {
  it('shows error message and hub link when API returns no questions', async () => {
    apiMocks.getGapQuestions.mockResolvedValue([]);

    renderPage();
    await waitFor(() => expect(screen.getByTestId('empty-state')).toBeDefined());

    expect(screen.getByTestId('empty-state-message')).toHaveTextContent(
      'There was an error, contact site administrator.',
    );
    const link = screen.getByTestId('empty-back-link');
    expect(link).toHaveAttribute('href', '/applications/job1');
  });
});

// ---------------------------------------------------------------------------
// AC-009: error banner on fetch failure
// ---------------------------------------------------------------------------

describe('AC-009 — error banner', () => {
  it('shows inline error banner when getGapQuestions rejects', async () => {
    apiMocks.getGapQuestions.mockRejectedValue(new Error('Network error'));

    renderPage();
    await waitFor(() => expect(screen.getByTestId('error-banner')).toBeDefined());

    expect(screen.getByTestId('error-banner')).toHaveAttribute('role', 'alert');
    expect(screen.getByTestId('retry-button')).toBeDefined();
    expect(screen.queryByTestId('questions-list')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// AC-010: retry button re-fetches
// ---------------------------------------------------------------------------

describe('AC-010 — retry', () => {
  it('re-calls getGapQuestions on Retry click and shows questions on success', async () => {
    apiMocks.getGapQuestions.mockRejectedValueOnce(new Error('fail'));

    renderPage();
    await waitFor(() => expect(screen.getByTestId('error-banner')).toBeDefined());

    apiMocks.getGapQuestions.mockResolvedValue(QUESTIONS.slice(0, 2));

    fireEvent.click(screen.getByTestId('retry-button'));

    await waitFor(() => expect(screen.getByTestId('questions-list')).toBeDefined());
    expect(screen.queryByTestId('error-banner')).toBeNull();
    expect(apiMocks.getGapQuestions).toHaveBeenCalledTimes(2);
  });
});

// ---------------------------------------------------------------------------
// AC-011: multi-editor guard
// ---------------------------------------------------------------------------

describe('AC-011 — multi-editor guard', () => {
  it('shows guard modal and keeps current editor open when Continue Editing is clicked', async () => {
    await renderAndWait();

    // Open Q1 for editing
    fireEvent.click(screen.getByTestId('request-edit-0'));
    await waitFor(() =>
      expect(screen.getByTestId('question-row-0')).toHaveAttribute('data-editing', 'true'),
    );

    // Click Answer on Q2 while Q1 is open → guard modal should appear
    fireEvent.click(screen.getByTestId('request-edit-1'));
    expect(screen.getByTestId('guard-modal')).toBeDefined();

    // Click "Continue Editing" → modal closes, Q2 stays in read, Q1 stays in edit
    fireEvent.click(screen.getByTestId('guard-continue-btn'));
    await waitFor(() => expect(screen.queryByTestId('guard-modal')).toBeNull());
    expect(screen.getByTestId('question-row-0')).toHaveAttribute('data-editing', 'true');
    expect(screen.getByTestId('question-row-1')).toHaveAttribute('data-editing', 'false');
  });

  it('cancels current editor without opening new question when OK is clicked', async () => {
    await renderAndWait();

    fireEvent.click(screen.getByTestId('request-edit-0'));
    await waitFor(() =>
      expect(screen.getByTestId('question-row-0')).toHaveAttribute('data-editing', 'true'),
    );

    fireEvent.click(screen.getByTestId('request-edit-2'));
    expect(screen.getByTestId('guard-modal')).toBeDefined();

    // Click "OK" → modal closes, Q1 is cancelled, Q2 does NOT open
    fireEvent.click(screen.getByTestId('guard-ok-btn'));
    await waitFor(() => expect(screen.queryByTestId('guard-modal')).toBeNull());
    expect(screen.getByTestId('question-row-0')).toHaveAttribute('data-editing', 'false');
    expect(screen.getByTestId('question-row-2')).toHaveAttribute('data-editing', 'false');
  });
});

// ---------------------------------------------------------------------------
// AC-012: GapQuestionCard receives correct props
// ---------------------------------------------------------------------------

describe('AC-012 — GapQuestionCard props', () => {
  it('renders each question via GapQuestionCard with required props', async () => {
    apiMocks.getApplication.mockResolvedValue(hubWith2Answered);
    renderPage();
    await waitFor(() => expect(screen.getByTestId('questions-list')).toBeDefined());

    // All 5 cards render
    for (let i = 0; i < 5; i++) {
      expect(screen.getByTestId(`question-row-${i}`)).toBeDefined();
    }

    // q1 has a saved response
    expect(screen.getByTestId('request-edit-0')).toHaveTextContent('Edit');
    // q3 has no response
    expect(screen.getByTestId('request-edit-2')).toHaveTextContent('Answer');
  });

  it('passes isEditing=true only to the currently editing card', async () => {
    await renderAndWait();

    fireEvent.click(screen.getByTestId('request-edit-1'));

    await waitFor(() =>
      expect(screen.getByTestId('question-row-1')).toHaveAttribute('data-editing', 'true'),
    );
    expect(screen.getByTestId('question-row-0')).toHaveAttribute('data-editing', 'false');
    expect(screen.getByTestId('question-row-2')).toHaveAttribute('data-editing', 'false');
  });
});

// ---------------------------------------------------------------------------
// AC-013: Hebrew locale
// ---------------------------------------------------------------------------

describe('AC-013 — Hebrew locale', () => {
  beforeEach(() => {
    document.documentElement.lang = 'he';
  });

  it('displays Hebrew title, subtitle, back link, and empty-state text', async () => {
    apiMocks.getGapQuestions.mockResolvedValue([]);

    renderPage();
    await waitFor(() => expect(screen.getByTestId('empty-state')).toBeDefined());

    expect(screen.getByTestId('page-title')).toHaveTextContent('שאלות ניתוח פערים');
    expect(screen.getByTestId('page-subtitle')).toHaveTextContent('ענה על כמה שאלות');
    expect(screen.getByTestId('back-link')).toHaveTextContent('← חזרה');
    expect(screen.getByTestId('empty-state-message')).toHaveTextContent('אירעה שגיאה');
  });

  it('shows Hebrew progress label', async () => {
    apiMocks.getApplication.mockResolvedValue(hubWith2Answered);
    renderPage();
    await waitFor(() => expect(screen.getByTestId('questions-list')).toBeDefined());

    expect(screen.getByTestId('progress-label')).toHaveTextContent('2 מתוך 5 נענו');
  });

  it('shows Hebrew error banner and retry button', async () => {
    apiMocks.getGapQuestions.mockRejectedValue(new Error('fail'));
    renderPage();
    await waitFor(() => expect(screen.getByTestId('error-banner')).toBeDefined());

    expect(screen.getByTestId('retry-button')).toHaveTextContent('נסה שוב');
  });
});

// ---------------------------------------------------------------------------
// AC-015: onSave calls saveGapResponses with single question
// ---------------------------------------------------------------------------

describe('AC-015 — per-question save', () => {
  it('calls saveGapResponses with single question response on card save', async () => {
    await renderAndWait();

    await act(async () => {
      fireEvent.click(screen.getByTestId('mock-save-0'));
      await Promise.resolve();
    });

    await waitFor(() =>
      expect(apiMocks.saveGapResponses).toHaveBeenCalledWith('job1', [
        { question_id: 'q1', response: 'saved answer' },
      ]),
    );
  });

  it('resets editingQuestionId to null after successful save', async () => {
    await renderAndWait();

    fireEvent.click(screen.getByTestId('request-edit-0'));
    await waitFor(() =>
      expect(screen.getByTestId('question-row-0')).toHaveAttribute('data-editing', 'true'),
    );

    await act(async () => {
      fireEvent.click(screen.getByTestId('mock-save-0'));
      await Promise.resolve();
    });

    await waitFor(() =>
      expect(screen.getByTestId('question-row-0')).toHaveAttribute('data-editing', 'false'),
    );
  });
});

// ---------------------------------------------------------------------------
// AC-016: ProgressBar accessibility
// ---------------------------------------------------------------------------

describe('AC-016 — progress bar accessibility', () => {
  it('has role=progressbar with aria attributes', async () => {
    apiMocks.getApplication.mockResolvedValue(hubWith2Answered);
    renderPage();
    await waitFor(() => expect(screen.getByTestId('questions-list')).toBeDefined());

    const bar = screen.getByRole('progressbar');
    expect(bar).toHaveAttribute('aria-valuenow', '40');
    expect(bar).toHaveAttribute('aria-valuemin', '0');
    expect(bar).toHaveAttribute('aria-valuemax', '100');
    expect(bar).toHaveAttribute('aria-label', '2 out of 5 answered');
  });
});
