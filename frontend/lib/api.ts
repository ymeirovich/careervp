import { getCurrentToken } from "./auth";
import type {
  User,
  Usage,
  SubscriptionResponse,
  Job,
  CreateJobInput,
  JobDetail,
  ApplicationHubData,
  CompanyResearchRequest,
  CompanyResearchResult,
  UserCV,
  GapQuestion,
  GapAnalysisRequest,
  GapAnalysisResponse,
  GapResponse,
  VPRGenerateRequest,
  AsyncTaskResponse,
  VPRStatusResponse,
  CoverLetterRequest,
  CoverLetterStatusResponse,
  InterviewPrepRequest,
  InterviewPrepStatusResponse,
  CVTailoringRequest,
  CVTailoredStatusResponse,
} from "./types";

// Route through the Next.js proxy to avoid CORS preflight issues with API Gateway.
const API_BASE = "/api/proxy";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getCurrentToken();

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }

  return res.json() as Promise<T>;
}

async function apiFetchOrNull<T>(
  path: string,
  init?: RequestInit
): Promise<T | null> {
  try {
    return await apiFetch<T>(path, init);
  } catch (err) {
    if (err instanceof Error && err.message.startsWith("API 404")) return null;
    throw err;
  }
}

export const api = {
  getMe: () => apiFetch<User>("/users/me"),
  getUsage: () => apiFetch<Usage>("/users/me/usage"),
  getSubscription: () =>
    apiFetch<SubscriptionResponse>("/users/me/subscription"),
  getJobs: async (): Promise<Job[]> => {
    const data = await apiFetch<{ jobs: Job[] }>("/jobs");
    return data.jobs ?? [];
  },
  createJob: (data: CreateJobInput) =>
    apiFetch<Job>("/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Jobs
  getJob: async (jobId: string): Promise<JobDetail> => {
    const data = await apiFetch<
      Omit<JobDetail, "title" | "company_name"> & {
        role_title: string;
        company: string;
      }
    >(`/jobs/${jobId}`);
    return {
      ...data,
      title: data.role_title,
      company_name: data.company,
    };
  },

  // Application Hub
  getApplication: (jobId: string): Promise<ApplicationHubData | null> =>
    apiFetchOrNull<ApplicationHubData>(`/applications/${jobId}`),

  // Company Research
  fetchCompanyResearch: (
    data: CompanyResearchRequest
  ): Promise<AsyncTaskResponse> =>
    apiFetch<AsyncTaskResponse>("/company-research/fetch", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getCompanyResearch: (jobId: string): Promise<CompanyResearchResult | null> =>
    apiFetchOrNull<CompanyResearchResult>(`/company-research/${jobId}`),

  // CV
  getCV: async (): Promise<UserCV | null> => {
    const data = await apiFetchOrNull<{ cvs: UserCV[] }>("/users/me/cv");
    return data?.cvs?.[0] ?? null;
  },
  saveCV: (data: Partial<UserCV>): Promise<UserCV> =>
    apiFetch<UserCV>("/users/me/cv", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Gap Analysis
  getGapQuestions: async (jobId: string): Promise<GapQuestion[]> => {
    const result = await apiFetchOrNull<{ questions: GapQuestion[] }>(
      `/jobs/${jobId}/gap-questions`
    );
    return result?.questions ?? [];
  },
  generateGapQuestions: (
    data: GapAnalysisRequest
  ): Promise<GapAnalysisResponse> =>
    apiFetch<GapAnalysisResponse>("/gap-analysis/questions", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  saveGapResponses: (jobId: string, responses: GapResponse[]): Promise<void> =>
    apiFetch<void>(`/jobs/${jobId}/gap-responses`, {
      method: "POST",
      body: JSON.stringify({ responses }),
    }),

  // VPR — async generation
  generateVPR: (data: VPRGenerateRequest): Promise<AsyncTaskResponse> =>
    apiFetch<AsyncTaskResponse>("/vpr/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  pollVPRStatus: (asyncTaskId: string): Promise<VPRStatusResponse> =>
    apiFetch<VPRStatusResponse>(`/vpr/${asyncTaskId}/status`),

  // Cover Letter — async generation
  generateCoverLetter: (data: CoverLetterRequest): Promise<AsyncTaskResponse> =>
    apiFetch<AsyncTaskResponse>("/cover-letter/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  pollCoverLetterStatus: (
    asyncTaskId: string
  ): Promise<CoverLetterStatusResponse> =>
    apiFetch<CoverLetterStatusResponse>(`/cover-letter/${asyncTaskId}/status`),

  // Interview Prep — async generation
  generateInterviewPrep: (
    data: InterviewPrepRequest
  ): Promise<AsyncTaskResponse> =>
    apiFetch<AsyncTaskResponse>("/interview-prep/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  pollInterviewPrepStatus: (
    asyncTaskId: string
  ): Promise<InterviewPrepStatusResponse> =>
    apiFetch<InterviewPrepStatusResponse>(
      `/interview-prep/${asyncTaskId}/status`
    ),

  // CV Tailoring — async generation
  generateCV: (data: CVTailoringRequest): Promise<AsyncTaskResponse> =>
    apiFetch<AsyncTaskResponse>("/cv-tailoring/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  pollCVTailored: (cvTailoringId: string): Promise<CVTailoredStatusResponse> =>
    apiFetch<CVTailoredStatusResponse>(`/cv-tailoring/${cvTailoringId}`),

  // Display pages — fetch completed artifact by artifact_id
  getVPR: (artifactId: string): Promise<VPRStatusResponse> =>
    apiFetch<VPRStatusResponse>(`/vpr/${artifactId}/status`),
  getCoverLetter: (artifactId: string): Promise<CoverLetterStatusResponse> =>
    apiFetch<CoverLetterStatusResponse>(`/cover-letter/${artifactId}`),
  getInterviewPrep: (
    artifactId: string
  ): Promise<InterviewPrepStatusResponse> =>
    apiFetch<InterviewPrepStatusResponse>(
      `/interview-prep/${artifactId}/status`
    ),
  getCVTailored: (cvTailoringId: string): Promise<CVTailoredStatusResponse> =>
    apiFetch<CVTailoredStatusResponse>(`/cv-tailoring/${cvTailoringId}`),
};
