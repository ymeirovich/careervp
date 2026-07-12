import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';

import { apiClient, ApiError, setAuthContext } from '../../api/client';
import { api } from '../../api/methods';
import {
  assertFlatErrorEnvelope,
  assertPatchEcho,
  validateBothTruths,
} from '../../lib/contractOracle';
import {
  applicationHubFixture,
  asyncTaskFixtures,
  cvTailoringRequestNullFixture,
  flatErrorFixture,
  interviewPrepPatchFixture,
  vprStatusSuccessFixture,
} from '../contract/oracleFixtures';

const BASE_URL = 'http://localhost:3000';
process.env.NEXT_PUBLIC_API_URL = BASE_URL;
apiClient.defaults.baseURL = BASE_URL;

jest.mock('../../lib/auth', () => ({
  getCurrentToken: jest.fn().mockResolvedValue('test-jwt'),
}));

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();
  jest.clearAllMocks();
});
afterAll(() => server.close());

describe('F-01 MSW contract oracle', () => {
  it('oracle_msw_ci_green_on_fixed_shapes validates FE fetch responses against both truths', async () => {
    let capturedCvTailoringRequest: unknown;

    server.use(
      http.get(`${BASE_URL}/applications/${applicationHubFixture.application.application_id}`, () => {
        validateBothTruths('ApplicationHubData', applicationHubFixture);
        return HttpResponse.json(applicationHubFixture);
      }),
      http.get(`${BASE_URL}/vpr/${vprStatusSuccessFixture.id}/status`, () => {
        validateBothTruths('VPRStatusResponse', vprStatusSuccessFixture);
        return HttpResponse.json(vprStatusSuccessFixture);
      }),
      http.post(`${BASE_URL}/cv-tailoring/generate`, async ({ request }) => {
        capturedCvTailoringRequest = await request.json();
        validateBothTruths('CVTailoringRequest', capturedCvTailoringRequest);
        validateBothTruths('AsyncTaskResponse', asyncTaskFixtures.requestOnly);
        return HttpResponse.json(asyncTaskFixtures.requestOnly);
      }),
    );

    const application = await api.getApplication(applicationHubFixture.application.application_id);
    const vprStatus = await api.pollVPRStatus(vprStatusSuccessFixture.id ?? '');
    const task = await api.generateCV(cvTailoringRequestNullFixture);

    expect(application?.application.application_id).toBe(applicationHubFixture.job.job_id);
    expect(vprStatus.result?.download_url).toBe(vprStatusSuccessFixture.result?.download_url);
    expect(capturedCvTailoringRequest).toEqual(cvTailoringRequestNullFixture);
    expect(task.request_id).toBe(asyncTaskFixtures.requestOnly.request_id);
  });

  it('oracle_s3_item_5_stale_base_version_returns_409', async () => {
    server.use(
      http.patch(`${BASE_URL}/interview-prep/ip-artifact-1`, () =>
        HttpResponse.json(flatErrorFixture, { status: 409 }),
      ),
    );

    let caught: unknown;
    try {
      await api.patchInterviewPrep('ip-artifact-1', {
        question_id: 'q1',
        answer: 'Stale answer',
        base_version: 1,
      });
    } catch (err) {
      caught = err;
    }

    expect(() => assertFlatErrorEnvelope(flatErrorFixture)).not.toThrow();
    expect(caught).toBeInstanceOf(ApiError);
    expect((caught as ApiError).status).toBe(409);
  });

  it('oracle_s3_item_5_patch_success_echoes_answer_version_and_updated_at', async () => {
    server.use(
      http.patch(`${BASE_URL}/interview-prep/ip-artifact-1`, () => {
        validateBothTruths('InterviewPrepPatchResponse', interviewPrepPatchFixture);
        return HttpResponse.json(interviewPrepPatchFixture);
      }),
    );

    const patched = await api.patchInterviewPrep('ip-artifact-1', {
      question_id: 'q1',
      answer: interviewPrepPatchFixture.answer,
      base_version: 2,
    });

    expect(() => assertPatchEcho(patched)).not.toThrow();
  });

  it('oracle_s3_item_10_401_refresh_retries_once_then_signs_out', async () => {
    const refreshSession = jest.fn().mockResolvedValue('fresh-jwt');
    const signOut = jest.fn();
    setAuthContext({ refreshSession, signOut });

    server.use(
      http.get(`${BASE_URL}/users/me`, () => HttpResponse.json({ error: 'Unauthorized' }, { status: 401 })),
    );

    await expect(api.getMe()).rejects.toBeInstanceOf(ApiError);

    expect(refreshSession).toHaveBeenCalledTimes(1);
    expect(signOut).toHaveBeenCalledTimes(1);
  });
});
