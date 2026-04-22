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
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

const defaultApplication = {
  application_id: "app-001",
  job_id: JOB_ID,
  user_id: "user-001",
  created_at: "2024-01-01T10:00:00Z",
  updated_at: "2024-01-01T10:00:00Z",
  is_finalized: false,
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

// 404 → query error → data=undefined → rawStatus=null → deriveModuleStatus returns 'notStarted'
const notFound = () => new HttpResponse(null, { status: 404 });

const processingModule = {
  job_id: JOB_ID,
  status: "processing" as const,
  created_at: "2024-01-01T10:00:00Z",
  updated_at: "2024-01-01T10:01:00Z",
};

const completedModule = {
  job_id: JOB_ID,
  status: "completed" as const,
  created_at: "2024-01-01T10:00:00Z",
  updated_at: "2024-01-01T10:05:00Z",
  result_url: "https://s3.example.com/vpr-result",
};

describe("useApplicationHub — initial states", () => {
  it("returns INIT when all modules have no raw status", async () => {
    server.use(
      http.get(`${BASE_URL}/applications/${JOB_ID}`, () => HttpResponse.json(defaultApplication)),
      http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json(defaultCV)),
      http.get(`${BASE_URL}/jobs/${JOB_ID}/gap-questions`, () => HttpResponse.json(defaultGapAnalysis)),
      http.get(`${BASE_URL}/vpr/${JOB_ID}/status`, notFound),
      http.get(`${BASE_URL}/cv-tailoring/${JOB_ID}/status`, notFound),
      http.get(`${BASE_URL}/cover-letter/${JOB_ID}/status`, notFound),
      http.get(`${BASE_URL}/interview-prep/${JOB_ID}/status`, notFound),
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
  it("returns LOADING when VPR is processing", async () => {
    server.use(
      http.get(`${BASE_URL}/applications/${JOB_ID}`, () => HttpResponse.json(defaultApplication)),
      http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json(defaultCV)),
      http.get(`${BASE_URL}/jobs/${JOB_ID}/gap-questions`, () => HttpResponse.json(defaultGapAnalysis)),
      http.get(`${BASE_URL}/vpr/${JOB_ID}/status`, () => HttpResponse.json(processingModule)),
      http.get(`${BASE_URL}/cv-tailoring/${JOB_ID}/status`, notFound),
      http.get(`${BASE_URL}/cover-letter/${JOB_ID}/status`, notFound),
      http.get(`${BASE_URL}/interview-prep/${JOB_ID}/status`, notFound),
    );

    const { result } = renderHook(
      () => useApplicationHub(JOB_ID),
      { wrapper: makeWrapper() }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hubState?.hubStatus).toBe("LOADING");
  });

  it("VPR module with completed status has View action", async () => {
    server.use(
      http.get(`${BASE_URL}/applications/${JOB_ID}`, () => HttpResponse.json(defaultApplication)),
      http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json(defaultCV)),
      http.get(`${BASE_URL}/jobs/${JOB_ID}/gap-questions`, () => HttpResponse.json(defaultGapAnalysis)),
      http.get(`${BASE_URL}/vpr/${JOB_ID}/status`, () => HttpResponse.json(completedModule)),
      http.get(`${BASE_URL}/cv-tailoring/${JOB_ID}/status`, notFound),
      http.get(`${BASE_URL}/cover-letter/${JOB_ID}/status`, notFound),
      http.get(`${BASE_URL}/interview-prep/${JOB_ID}/status`, notFound),
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

describe("useApplicationHub — finalized state", () => {
  it("returns FINALIZED when application is finalized", async () => {
    server.use(
      http.get(`${BASE_URL}/applications/${JOB_ID}`, () =>
        HttpResponse.json({ ...defaultApplication, is_finalized: true })
      ),
      http.get(`${BASE_URL}/users/me/cv`, () => HttpResponse.json(defaultCV)),
      http.get(`${BASE_URL}/jobs/${JOB_ID}/gap-questions`, () => HttpResponse.json(defaultGapAnalysis)),
      http.get(`${BASE_URL}/vpr/${JOB_ID}/status`, () => HttpResponse.json(completedModule)),
      http.get(`${BASE_URL}/cv-tailoring/${JOB_ID}/status`, () => HttpResponse.json(completedModule)),
      http.get(`${BASE_URL}/cover-letter/${JOB_ID}/status`, () => HttpResponse.json(completedModule)),
      http.get(`${BASE_URL}/interview-prep/${JOB_ID}/status`, () => HttpResponse.json(completedModule)),
    );

    const { result } = renderHook(
      () => useApplicationHub(JOB_ID),
      { wrapper: makeWrapper() }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hubState?.hubStatus).toBe("FINALIZED");
  });
});
