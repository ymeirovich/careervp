import { describe, it, expect, beforeAll, afterEach, afterAll, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

// Mock lib/auth so tests don't touch real Cognito
vi.mock('../../lib/auth', () => ({
  getCurrentToken: vi.fn().mockResolvedValue('test-jwt'),
  signOut: vi.fn(),
  signIn: vi.fn(),
  signUp: vi.fn(),
  confirmSignUp: vi.fn(),
  resendConfirmationCode: vi.fn(),
  forgotPassword: vi.fn(),
  confirmForgotPassword: vi.fn(),
  getCurrentCognitoUser: vi.fn().mockReturnValue(null),
}));

const BASE_URL = 'http://localhost:3000';

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }));
afterEach(() => {
  server.resetHandlers();
  vi.restoreAllMocks();
});
afterAll(() => server.close());

import { api } from '../../api/methods';
import { ApiError } from '../../api/client';

describe('api.getJob', () => {
  it('normalises role_title → title and company → company_name', async () => {
    server.use(
      http.get(`${BASE_URL}/jobs/1`, () =>
        HttpResponse.json({ role_title: 'Engineer', company: 'Acme', job_id: '1', user_id: 'u1', status: 'active', created_at: '2024-01-01', requirements: [] }),
      ),
    );

    const result = await api.getJob('1');
    expect(result.title).toBe('Engineer');
    expect(result.company_name).toBe('Acme');
  });
});

describe('api.getApplication', () => {
  it('returns null on 404', async () => {
    server.use(
      http.get(`${BASE_URL}/applications/missing`, () =>
        HttpResponse.json({ error: 'Not found' }, { status: 404 }),
      ),
    );

    const result = await api.getApplication('missing');
    expect(result).toBeNull();
  });
});

describe('api.getCV', () => {
  it('unwraps cvs array and returns first element', async () => {
    server.use(
      http.get(`${BASE_URL}/users/me/cv`, () =>
        HttpResponse.json({ cvs: [{ cv_id: 'cv1', user_id: 'u1', full_name: 'Test', language: 'en', contact_info: {}, experience: [], education: [], skills: [], certifications: [], top_achievements: [], languages: [] }] }),
      ),
    );

    const result = await api.getCV();
    expect(result?.cv_id).toBe('cv1');
  });

  it('returns null when cvs array is empty', async () => {
    server.use(
      http.get(`${BASE_URL}/users/me/cv`, () =>
        HttpResponse.json({ cvs: [] }),
      ),
    );

    const result = await api.getCV();
    expect(result).toBeNull();
  });
});

describe('api.generateVPR', () => {
  it('sends cache-busting UUID as job_id, actual jobId as application_id', async () => {
    let capturedBody: Record<string, unknown> = {};

    server.use(
      http.post(`${BASE_URL}/vpr/generate`, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ request_id: 'task-1', status: 'processing' });
      }),
    );

    await api.generateVPR({ application_id: 'job123', cv_id: 'cv1', gap_response_ids: [] });

    expect(capturedBody.application_id).toBe('job123');
    expect(typeof capturedBody.job_id).toBe('string');
    expect(capturedBody.job_id).not.toBe('job123');
    // UUID format validation
    expect(capturedBody.job_id).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i,
    );
    expect(capturedBody.job_id).not.toBe(capturedBody.application_id);
  });
});

describe('api.getCoverLettersList', () => {
  it('uses job_id as applicationId and preserves artifact id (regression: item.id was used as appId causing 404)', async () => {
    const rawItem = {
      id: 'cl-artifact-abc',
      status: 'completed',
      job_id: 'job-123',
      company_name: 'Acme',
      job_title: 'Engineer',
      created_at: '2026-05-01T00:00:00Z',
    };

    server.use(
      http.get(`${BASE_URL}/cover-letters`, () => HttpResponse.json([rawItem])),
      http.get(`${BASE_URL}/jobs`, () => HttpResponse.json({ jobs: [] })),
    );

    const result = await api.getCoverLettersList();

    expect(result).toHaveLength(1);
    expect(result[0].applicationId).toBe('job-123');
    expect(result[0].artifact_id).toBe('cl-artifact-abc');
    expect(result[0].status).toBe('ready');
  });

  it('does not fall back to item.id as applicationId when job_id is absent', async () => {
    const rawItem = {
      id: 'cl-artifact-xyz',
      status: 'completed',
      company_name: 'Beta',
      job_title: 'Designer',
      created_at: '2026-05-02T00:00:00Z',
    };

    server.use(
      http.get(`${BASE_URL}/cover-letters`, () => HttpResponse.json([rawItem])),
      http.get(`${BASE_URL}/jobs`, () => HttpResponse.json({ jobs: [] })),
    );

    const result = await api.getCoverLettersList();

    expect(result[0].applicationId).toBe('');
    expect(result[0].artifact_id).toBe('cl-artifact-xyz');
  });
});

describe('ApiError', () => {
  it('thrown with status and message on 4xx', async () => {
    server.use(
      http.get(`${BASE_URL}/users/me`, () =>
        HttpResponse.json({ error: 'Invalid input' }, { status: 422 }),
      ),
    );

    let caught: unknown;
    try {
      await api.getMe();
    } catch (err) {
      caught = err;
    }

    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as ApiError).status).toBe(422);
    expect((caught as ApiError).message).toBe('Invalid input');
  });
});
