/**
 * E2E tests for artifact viewer pages.
 * These tests use Playwright and require a running dev server.
 * They are excluded from the vitest unit test run.
 */
import { test, expect } from '@playwright/test';

const MOCK_HUB = {
  application: { application_id: 'job1', state: 'active', created_at: '', trial_credit_consumed: false },
  job: { job_id: 'job1', user_id: 'u1', title: 'Software Engineer', company_name: 'Acme Corp', status: 'active', created_at: '', requirements: [] },
  cv: { cv_id: 'cv1' },
  gap_analysis: { questions: [], responses: [] },
  artifacts: {
    vpr: { status: 'completed', artifact_id: 'art1' },
    cover_letter: { status: 'pending', artifact_id: null },
    interview_prep: { status: 'pending', artifact_id: null },
    cv_tailored: { status: 'pending', artifact_id: null },
    gap_analysis: { status: 'pending', artifact_id: null },
  },
};

const MOCK_VPR_STATUS = {
  id: 'art1',
  status: 'completed',
  result: { download_url: 'https://s3.example.com/vpr.json' },
};

const MOCK_FULL_VPR = {
  applicationId: 'job1',
  metadata: { reportDate: '2026-01-01', candidateName: 'Jane Doe', targetRole: 'Software Engineer', targetCompany: 'Acme Corp' },
  executiveSummary: {
    overallFitScore: 85,
    fitRationale: 'Strong alignment with role requirements.',
    topThreeStrengths: [{ strength: 'Leadership', evidence: 'Led teams', relevanceToRole: 'Critical' }],
    topThreeConcerns: [{ concern: 'Python gap', severity: 'medium', mitigation: 'Fast learner' }],
    recommendedApproach: 'aggressive_apply',
  },
  roleAlignment: { coreResponsibilities: [], requirementBreakdown: { mustHave: [], niceToHave: [] } },
  experienceMapping: { relevantExperiences: [], experienceGaps: [] },
  skillsAnalysis: { technicalSkills: [], softSkills: [] },
  evidenceGaps: { priorityGapsToAddress: [] },
  differentiators: { uniqueStrengths: [], positioningStatement: '' },
  concernsAndMitigations: { likelyObjections: [], preemptiveResponses: [] },
  valueProposition: { primaryValue: { statement: '', evidence: '', outcomeForCompany: '' }, elevatorPitch: '' },
  applicationStrategy: { messagingApproach: 'Lead with results', atsKeywords: { primary: [], secondary: [] }, cvLeadDifferentiator: '', sectionsToCompress: [] },
};

test.describe('VPR page navigation', () => {
  test('navigate from hub to VPR page and back', async ({ page }) => {
    // Mock the API routes
    await page.route('**/applications/job1', (route) => route.fulfill({ json: MOCK_HUB }));
    await page.route('**/vpr/art1/status', (route) => route.fulfill({ json: MOCK_VPR_STATUS }));
    await page.route('https://s3.example.com/vpr.json', (route) => route.fulfill({ json: MOCK_FULL_VPR }));
    await page.route('**/jobs/job1', (route) =>
      route.fulfill({ json: { job_id: 'job1', role_title: 'Software Engineer', company: 'Acme Corp', status: 'active', created_at: '', user_id: 'u1', requirements: [] } }),
    );

    await page.goto('/applications/job1/vpr?id=art1');
    await expect(page.getByTestId('vpr-exec-summary')).toBeVisible({ timeout: 10000 });

    // Back to hub
    await page.getByRole('button', { name: /back to hub/i }).click();
    await expect(page).toHaveURL('/applications/job1');
  });
});

test.describe('Gap analysis page', () => {
  test('shows questions and allows saving', async ({ page }) => {
    const mockQuestions = {
      questions: [
        { question_id: 'q1', question: 'Tell me about your Python experience', impact: 'HIGH', probability: 'HIGH', gap_score: 8, tags: [] },
        { question_id: 'q2', question: 'How do you handle ambiguity?', impact: 'MEDIUM', probability: 'MEDIUM', gap_score: 5, tags: [] },
      ],
    };

    await page.route('**/jobs/job1/gap-questions', (route) => route.fulfill({ json: mockQuestions }));
    await page.route('**/applications/job1', (route) => route.fulfill({ json: MOCK_HUB }));
    await page.route('**/users/me/cv', (route) => route.fulfill({ json: { cvs: [{ cv_id: 'cv1', user_id: 'u1', full_name: 'Jane' }] } }));
    await page.route('**/jobs/job1/gap-responses', (route) => route.fulfill({ status: 200, json: {} }));

    await page.goto('/applications/job1/gap-analysis');

    await expect(page.getByTestId('question-row-0')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('question-row-1')).toBeVisible();

    // Fill in an answer
    const textareas = page.getByPlaceholder('Your answer…');
    await textareas.first().fill('I have 3 years of Python experience.');

    // Save
    await page.getByTestId('save-responses').click();

    // Check POST was made
    await page.waitForRequest((req) => req.url().includes('/gap-responses') && req.method() === 'POST');
  });
});
