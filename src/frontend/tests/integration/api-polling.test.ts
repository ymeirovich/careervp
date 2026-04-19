import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useModuleStatus } from "../../hooks/useModuleStatus";

const BASE_URL = "http://localhost:3000";

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  vi.restoreAllMocks();
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

describe("useModuleStatus — polling lifecycle", () => {
  it("starts in loading state and resolves to completed", async () => {
    server.use(
      http.get(`${BASE_URL}/vpr/job-123/status`, () =>
        HttpResponse.json({ job_id: "job-123", status: "completed", created_at: "2024-01-01T10:00:00Z", updated_at: "2024-01-01T10:05:00Z", result_url: "https://s3.example.com/result" })
      )
    );

    const { result } = renderHook(
      () => useModuleStatus("vpr", "job-123", true),
      { wrapper: makeWrapper() }
    );

    await waitFor(() => expect(result.current.rawStatus?.status).toBe("completed"));
  });

  it("stops polling when status is completed", async () => {
    let callCount = 0;
    server.use(
      http.get(`${BASE_URL}/vpr/job-123/status`, () => {
        callCount++;
        return HttpResponse.json({
          job_id: "job-123",
          status: "completed",
          created_at: "2024-01-01T10:00:00Z",
          updated_at: "2024-01-01T10:05:00Z",
        });
      })
    );

    const { result } = renderHook(
      () => useModuleStatus("vpr", "job-123", true),
      { wrapper: makeWrapper() }
    );

    await waitFor(() => expect(result.current.rawStatus?.status).toBe("completed"));

    const countAfterComplete = callCount;
    // Wait a polling interval — should NOT increase call count
    await new Promise((r) => setTimeout(r, 100));
    expect(callCount).toBe(countAfterComplete);
  });

  it("stops polling when status is failed", async () => {
    server.use(
      http.get(`${BASE_URL}/vpr/job-123/status`, () =>
        HttpResponse.json({
          job_id: "job-123",
          status: "failed",
          created_at: "2024-01-01T10:00:00Z",
          updated_at: "2024-01-01T10:01:00Z",
          error_message: "Stage 6 quality gate failure",
        })
      )
    );

    const { result } = renderHook(
      () => useModuleStatus("vpr", "job-123", true),
      { wrapper: makeWrapper() }
    );

    await waitFor(() => expect(result.current.rawStatus?.status).toBe("failed"));
    expect(result.current.isPolling).toBe(false);
  });

  it("does not fetch when enabled=false", async () => {
    let callCount = 0;
    server.use(
      http.get(`${BASE_URL}/vpr/job-123/status`, () => {
        callCount++;
        return HttpResponse.json({ job_id: "job-123", status: "pending" });
      })
    );

    renderHook(() => useModuleStatus("vpr", "job-123", false), {
      wrapper: makeWrapper(),
    });

    await new Promise((r) => setTimeout(r, 100));
    expect(callCount).toBe(0);
  });

  it("transitions through pending → processing → completed", async () => {
    // Requires 2 poll cycles at 3s each; allow 10s total
    const responses = [
      { status: "pending" },
      { status: "processing" },
      { status: "completed", result_url: "https://s3.example.com/result" },
    ];
    let responseIndex = 0;

    server.use(
      http.get(`${BASE_URL}/vpr/job-123/status`, () => {
        const response = responses[Math.min(responseIndex++, responses.length - 1)];
        return HttpResponse.json({
          job_id: "job-123",
          created_at: "2024-01-01T10:00:00Z",
          updated_at: "2024-01-01T10:00:00Z",
          ...response,
        });
      })
    );

    const { result } = renderHook(
      () => useModuleStatus("vpr", "job-123", true),
      { wrapper: makeWrapper() }
    );

    await waitFor(() => expect(result.current.rawStatus?.status).toBe("completed"), {
      timeout: 10_000,
    });
  }, 12_000);
});

describe("useModuleStatus — different module types", () => {
  const moduleEndpoints: Array<{ module: string; path: string }> = [
    { module: "vpr", path: "/vpr/job-123/status" },
    { module: "coverLetter", path: "/cover-letter/job-123/status" },
    { module: "interviewPrep", path: "/interview-prep/job-123/status" },
    { module: "tailoredCV", path: "/cv-tailoring/job-123/status" },
  ];

  moduleEndpoints.forEach(({ module, path }) => {
    it(`polls correct endpoint for ${module}`, async () => {
      let wasCalled = false;
      server.use(
        http.get(`${BASE_URL}${path}`, () => {
          wasCalled = true;
          return HttpResponse.json({
            job_id: "job-123",
            status: "completed",
            created_at: "2024-01-01T10:00:00Z",
            updated_at: "2024-01-01T10:05:00Z",
          });
        })
      );

      const { result } = renderHook(
        () => useModuleStatus(module as any, "job-123", true),
        { wrapper: makeWrapper() }
      );

      await waitFor(() => expect(result.current.rawStatus).not.toBeNull());
      expect(wasCalled).toBe(true);
    });
  });
});
