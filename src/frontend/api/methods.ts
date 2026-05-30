import { apiClient, apiFetchOrNull } from './client';
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
  CoverLetterListItem,
  TailoredCvListItem,
  InterviewPrepRequest,
  InterviewPrepStatusResponse,
  CVTailoringRequest,
  CVTailoredStatusResponse,
  ExportResponse,
} from '../lib/types';

type RawGapQuestion = {
  question_id?: string;
  id?: string;
  question?: string;
  text?: string;
  impact?: 'HIGH' | 'MEDIUM' | 'LOW';
  probability?: 'HIGH' | 'MEDIUM' | 'LOW';
  gap_score?: number;
  tags?: string[];
};

function normaliseGapQuestion(raw: RawGapQuestion): GapQuestion {
  return {
    question_id: raw.question_id ?? raw.id ?? '',
    question: raw.question ?? raw.text ?? '',
    impact: raw.impact ?? 'MEDIUM',
    probability: raw.probability ?? 'MEDIUM',
    gap_score: raw.gap_score ?? 0,
    tags: raw.tags ?? [],
  };
}

export const api = {
  // ── User ──
  getMe: (): Promise<User> =>
    apiClient.get<User>('/users/me').then((r) => r.data),

  getUsage: (): Promise<Usage> =>
    apiClient.get<Usage>('/users/me/usage').then((r) => r.data),

  getSubscription: (): Promise<SubscriptionResponse> =>
    apiClient.get<SubscriptionResponse>('/users/me/subscription').then((r) => r.data),

  // ── Jobs ──
  getJobs: async (): Promise<Job[]> => {
    const r = await apiClient.get<{ jobs: Job[] }>('/jobs');
    return r.data.jobs ?? [];
  },

  createJob: (data: CreateJobInput): Promise<Job> =>
    apiClient.post<Job>('/jobs', data).then((r) => r.data),

  getJob: async (jobId: string): Promise<JobDetail> => {
    const r = await apiClient.get<
      Omit<JobDetail, 'title' | 'company_name'> & { role_title: string; company: string }
    >(`/jobs/${jobId}`);
    return {
      ...r.data,
      title: r.data.role_title,
      company_name: r.data.company,
    };
  },

  // ── Applications ──
  getApplication: (jobId: string): Promise<ApplicationHubData | null> =>
    apiFetchOrNull(() =>
      apiClient.get<ApplicationHubData>(`/applications/${jobId}`).then((r) => r.data),
    ),

  // ── Company Research ──
  fetchCompanyResearch: (data: CompanyResearchRequest): Promise<AsyncTaskResponse> =>
    apiClient.post<AsyncTaskResponse>('/company-research/fetch', data).then((r) => r.data),

  getCompanyResearch: (jobId: string): Promise<CompanyResearchResult | null> =>
    apiFetchOrNull(() =>
      apiClient.get<CompanyResearchResult>(`/company-research/${jobId}`).then((r) => r.data),
    ),

  // ── CV ──
  getCV: async (): Promise<UserCV | null> => {
    const data = await apiFetchOrNull(() =>
      apiClient.get<{ cvs: UserCV[] }>('/users/me/cv').then((r) => r.data),
    );
    return data?.cvs?.[0] ?? null;
  },

  saveCV: (data: Partial<UserCV>): Promise<UserCV> =>
    apiClient.post<UserCV>('/users/me/cv', data).then((r) => r.data),

  // ── Gap Analysis ──
  getGapQuestions: async (jobId: string): Promise<GapQuestion[]> => {
    const data = await apiFetchOrNull(() =>
      apiClient
        .get<{ questions: RawGapQuestion[] }>(`/jobs/${jobId}/gap-questions`)
        .then((r) => r.data),
    );
    return (data?.questions ?? []).map(normaliseGapQuestion);
  },

  generateGapQuestions: (data: GapAnalysisRequest): Promise<GapAnalysisResponse> =>
    apiClient.post<GapAnalysisResponse>('/gap-analysis/questions', data).then((r) => r.data),

  saveGapResponses: (jobId: string, responses: GapResponse[]): Promise<void> =>
    apiClient.post<void>(`/jobs/${jobId}/gap-responses`, { responses }).then(() => undefined),

  // ── VPR ──
  generateVPR: (data: Omit<VPRGenerateRequest, 'job_id'>): Promise<AsyncTaskResponse> =>
    apiClient
      .post<AsyncTaskResponse>('/vpr/generate', {
        ...data,
        job_id: crypto.randomUUID(),
      })
      .then((r) => r.data),

  pollVPRStatus: (asyncTaskId: string): Promise<VPRStatusResponse> =>
    apiClient.get<VPRStatusResponse>(`/vpr/${asyncTaskId}/status`).then((r) => r.data),

  getVPR: (artifactId: string): Promise<VPRStatusResponse> =>
    apiClient.get<VPRStatusResponse>(`/vpr/${artifactId}/status`).then((r) => r.data),

  // ── Cover Letter ──
  generateCoverLetter: (data: Omit<CoverLetterRequest, 'job_id'>): Promise<AsyncTaskResponse> =>
    apiClient
      .post<AsyncTaskResponse>('/cover-letter/generate', {
        ...data,
        job_id: crypto.randomUUID(),
      })
      .then((r) => r.data),

  pollCoverLetterStatus: (asyncTaskId: string): Promise<CoverLetterStatusResponse> =>
    apiClient
      .get<CoverLetterStatusResponse>(`/cover-letter/${asyncTaskId}/status`)
      .then((r) => r.data),

  getCoverLetter: (artifactId: string): Promise<CoverLetterStatusResponse> =>
    apiClient
      .get<CoverLetterStatusResponse>(`/cover-letter/${artifactId}/status`)
      .then((r) => r.data),

  getCoverLettersList: async (): Promise<CoverLetterListItem[]> => {
    const r = await apiClient.get<CoverLetterListItem[] | { cover_letters?: CoverLetterListItem[] }>('/cover-letters');
    return Array.isArray(r.data) ? r.data : (r.data.cover_letters ?? []);
  },

  // ── Interview Prep ──
  generateInterviewPrep: (data: InterviewPrepRequest): Promise<AsyncTaskResponse> =>
    apiClient.post<AsyncTaskResponse>('/interview-prep/generate', data).then((r) => r.data),

  pollInterviewPrepStatus: (asyncTaskId: string): Promise<InterviewPrepStatusResponse> =>
    apiClient
      .get<InterviewPrepStatusResponse>(`/interview-prep/${asyncTaskId}/status`)
      .then((r) => r.data),

  getInterviewPrep: (artifactId: string): Promise<InterviewPrepStatusResponse> =>
    apiClient
      .get<InterviewPrepStatusResponse>(`/interview-prep/${artifactId}/status`)
      .then((r) => r.data),

  // ── CV Tailoring ──
  generateCV: (data: CVTailoringRequest): Promise<AsyncTaskResponse> =>
    apiClient.post<AsyncTaskResponse>('/cv-tailoring/generate', data).then((r) => r.data),

  pollCVTailored: (cvTailoringId: string): Promise<CVTailoredStatusResponse> =>
    apiClient
      .get<CVTailoredStatusResponse>(`/cv-tailoring/${cvTailoringId}/status`)
      .then((r) => r.data),

  getCVTailored: (cvTailoringId: string): Promise<CVTailoredStatusResponse> =>
    apiClient
      .get<CVTailoredStatusResponse>(`/cv-tailoring/${cvTailoringId}/status`)
      .then((r) => r.data),

  getTailoredCvsList: async (): Promise<TailoredCvListItem[]> => {
    const r = await apiClient.get<TailoredCvListItem[] | { cv_tailorings?: TailoredCvListItem[] }>('/cv-tailorings');
    return Array.isArray(r.data) ? r.data : (r.data.cv_tailorings ?? []);
  },

  // ── Export ──
  exportArtifact: (jobId: string, moduleType: string, format: 'docx' | 'pdf'): Promise<ExportResponse> =>
    apiClient
      .get<ExportResponse>(`/jobs/${jobId}/artifacts/${moduleType}/export?format=${format}`)
      .then((r) => r.data),
};
