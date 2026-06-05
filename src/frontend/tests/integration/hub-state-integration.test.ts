import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useApplicationHub } from "../../hooks/useApplicationHub";

const BASE_URL = "http://localhost:3000";
const JOB_ID = "job-integration-001";

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  localStorage.clear();
});
afterAll(() => server.close());

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

// Base application with spec-10 artifacts field (all pending, no task IDs)
const defaultApplication = {
  application_id: "app-001",
  job_id: JOB_ID,
  user_id: "user-001",
  created_at: "2024-01-01T10:00:00Z",
  updated_at: "2024-01-01T10:00:00Z",
  is_finalized: false,
  artifacts: {
    vpr: { artifact_id: null, status: "pending" },
    cover_letter: { artifact_id: null, status: "pending" },
    interview_prep: { artifact_id: null, status: "pending" },
    cv_tailored: { artifact_id: null, status: "pending" },
    gap_analysis: { artifact_id: null, status: "pending" },
  },
};

const defaultCV = {
  cv_id: "cv-001",
  created_at: "2024-01-01T09:00:00Z",
  updated_at: "2024-01-01T09:00:00Z",
  version: 1,
};

const defaultGapAnalysis = {
  job_id: JOB_ID,
  questions: [],
};

describe("useApplicationHub — initial states", () => {
  it("returns INIT when all modules have no raw status", async () => {
    server.use(
      http.get(`${BASE_URL}/applications/${JOB_ID}`, () => HttpResponse.json(defaultApplication)),
      http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json(defaultCV)),
      http.get(`${BASE_URL}/jobs/${JOB_ID}/gap-questions`, () => HttpResponse.json(defaultGapAnalysis)),
    );

    const { result } = renderHook(
      () => useApplicationHub(JOB_ID),
      { wrapper: makeWrapper() }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hubState?.hubStatus).toBe("INIT");
  });

  it("returns null hubState for empty jobId", async () => {
    const { result } = renderHook(
      () => useApplicationHub(""),
      { wrapper: makeWrapper() }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hubState).toBeNull();
  });
});

describe("useApplicationHub — module status transitions", () => {
  it("returns LOADING when VPR artifact status is processing", async () => {
    const appWithProcessingVPR = {
      ...defaultApplication,
      artifacts: {
        ...defaultApplication.artifacts,
        // artifact_id = JOB_ID so polling hits /vpr/${JOB_ID}/status
        vpr: { artifact_id: JOB_ID, status: "processing" },
      },
    };

    server.use(
      http.get(`${BASE_URL}/applications/${JOB_ID}`, () => HttpResponse.json(appWithProcessingVPR)),
      http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json(defaultCV)),
      http.get(`${BASE_URL}/jobs/${JOB_ID}/gap-questions`, () => HttpResponse.json(defaultGapAnalysis)),
      // Polling endpoint (may fire after initial load)
      http.get(`${BASE_URL}/vpr/${JOB_ID}/status`, () =>
        HttpResponse.json({ status: "processing" })
      ),
    );

    const { result } = renderHook(
      () => useApplicationHub(JOB_ID),
      { wrapper: makeWrapper() }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hubState?.hubStatus).toBe("LOADING");
  });

  it("VPR module with completed artifact status has View action", async () => {
    const appWithCompletedVPR = {
      ...defaultApplication,
      artifacts: {
        ...defaultApplication.artifacts,
        vpr: { artifact_id: JOB_ID, status: "completed" },
      },
    };

    server.use(
      http.get(`${BASE_URL}/applications/${JOB_ID}`, () => HttpResponse.json(appWithCompletedVPR)),
      http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json(defaultCV)),
      http.get(`${BASE_URL}/jobs/${JOB_ID}/gap-questions`, () => HttpResponse.json(defaultGapAnalysis)),
      http.get(`${BASE_URL}/vpr/${JOB_ID}/status`, () =>
        HttpResponse.json({ status: "completed", result_url: "https://s3.example.com/vpr" })
      ),
    );

    const { result } = renderHook(
      () => useApplicationHub(JOB_ID),
      { wrapper: makeWrapper() }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    const vprModule = result.current.hubState?.modules?.vpr;
    expect(vprModule?.status).toBe("ready");
    expect(vprModule?.primaryAction?.label).toBe("View");
  });
});

describe("useApplicationHub — gap analysis status from application payload", () => {
  const cvWithWrapper = { cvs: [{ cv_id: "cv-001", full_name: "Test User" }] };

  it("gap_analysis.responses with 10 items → gapAnalysis status ready", async () => {
    const responses = Array.from({ length: 10 }, (_, i) => ({
      question_id: `q${i}`,
      response: `answer ${i}`,
    }));
    const appWithResponses = {
      ...defaultApplication,
      gap_analysis: { questions: responses.map((r) => ({ question_id: r.question_id, question: `q${r.question_id}` })), responses },
    };

    server.use(
      http.get(`${BASE_URL}/applications/${JOB_ID}`, () => HttpResponse.json(appWithResponses)),
      http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json(cvWithWrapper)),
      http.get(`${BASE_URL}/jobs/${JOB_ID}/gap-questions`, () => HttpResponse.json(defaultGapAnalysis)),
      http.get(`${BASE_URL}/company-research/${JOB_ID}`, () => HttpResponse.json(null, { status: 404 })),
    );

    const { result } = renderHook(() => useApplicationHub(JOB_ID), { wrapper: makeWrapper() });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hubState?.modules.gapAnalysis.status).toBe("ready");
  });

  it("gap_analysis.questions present, responses empty → gapAnalysis status processing", async () => {
    const appWithQuestions = {
      ...defaultApplication,
      gap_analysis: {
        questions: [{ question_id: "q1", question: "Tell me about yourself" }],
        responses: [],
      },
    };

    server.use(
      http.get(`${BASE_URL}/applications/${JOB_ID}`, () => HttpResponse.json(appWithQuestions)),
      http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json(cvWithWrapper)),
      http.get(`${BASE_URL}/jobs/${JOB_ID}/gap-questions`, () => HttpResponse.json(defaultGapAnalysis)),
      http.get(`${BASE_URL}/company-research/${JOB_ID}`, () => HttpResponse.json(null, { status: 404 })),
    );

    const { result } = renderHook(() => useApplicationHub(JOB_ID), { wrapper: makeWrapper() });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hubState?.modules.gapAnalysis.status).toBe("processing");
  });

  it("gap_analysis questions and responses both empty → gapAnalysis status notStarted", async () => {
    const appWithEmptyGap = {
      ...defaultApplication,
      gap_analysis: { questions: [], responses: [] },
    };

    server.use(
      http.get(`${BASE_URL}/applications/${JOB_ID}`, () => HttpResponse.json(appWithEmptyGap)),
      http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json(cvWithWrapper)),
      http.get(`${BASE_URL}/jobs/${JOB_ID}/gap-questions`, () => HttpResponse.json(defaultGapAnalysis)),
      http.get(`${BASE_URL}/company-research/${JOB_ID}`, () => HttpResponse.json(null, { status: 404 })),
    );

    const { result } = renderHook(() => useApplicationHub(JOB_ID), { wrapper: makeWrapper() });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hubState?.modules.gapAnalysis.status).toBe("notStarted");
  });

  it("10 gap responses → hubStatus is NOT PROCESSING_BLOCKED", async () => {
    const responses = Array.from({ length: 10 }, (_, i) => ({
      question_id: `q${i}`,
      response: `answer ${i}`,
    }));
    const appWithResponses = {
      ...defaultApplication,
      gap_analysis: { questions: [], responses },
    };

    server.use(
      http.get(`${BASE_URL}/applications/${JOB_ID}`, () => HttpResponse.json(appWithResponses)),
      http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json(cvWithWrapper)),
      http.get(`${BASE_URL}/jobs/${JOB_ID}/gap-questions`, () => HttpResponse.json(defaultGapAnalysis)),
      http.get(`${BASE_URL}/company-research/${JOB_ID}`, () => HttpResponse.json(null, { status: 404 })),
    );

    const { result } = renderHook(() => useApplicationHub(JOB_ID), { wrapper: makeWrapper() });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hubState?.hubStatus).not.toBe("PROCESSING_BLOCKED");
  });
});

describe("useApplicationHub — finalized state", () => {
  it("returns FINALIZED when application is finalized", async () => {
    const finalizedApp = {
      ...defaultApplication,
      is_finalized: true,
      artifacts: {
        vpr: { artifact_id: JOB_ID, status: "completed" },
        cover_letter: { artifact_id: JOB_ID, status: "completed" },
        interview_prep: { artifact_id: JOB_ID, status: "completed" },
        cv_tailored: { artifact_id: JOB_ID, status: "completed" },
        gap_analysis: { artifact_id: null, status: "pending" },
      },
    };

    server.use(
      http.get(`${BASE_URL}/applications/${JOB_ID}`, () => HttpResponse.json(finalizedApp)),
      http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json(defaultCV)),
      http.get(`${BASE_URL}/jobs/${JOB_ID}/gap-questions`, () => HttpResponse.json(defaultGapAnalysis)),
      http.get(`${BASE_URL}/vpr/${JOB_ID}/status`, () =>
        HttpResponse.json({ status: "completed" })
      ),
      http.get(`${BASE_URL}/cover-letter/${JOB_ID}/status`, () =>
        HttpResponse.json({ status: "completed" })
      ),
      http.get(`${BASE_URL}/interview-prep/${JOB_ID}/status`, () =>
        HttpResponse.json({ status: "completed" })
      ),
      http.get(`${BASE_URL}/cv-tailoring/${JOB_ID}/status`, () =>
        HttpResponse.json({ status: "completed" })
      ),
    );

    const { result } = renderHook(
      () => useApplicationHub(JOB_ID),
      { wrapper: makeWrapper() }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hubState?.hubStatus).toBe("FINALIZED");
  });
});
