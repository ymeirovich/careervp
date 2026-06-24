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
  TailoredCvListStatus,
  InterviewPrepRequest,
  InterviewPrepPatchResponse,
  InterviewPrepStatusResponse,
  CVTailoringRequest,
  CVTailoredStatusResponse,
  CVSections,
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

  updateMe: (data: { name?: string }): Promise<User> =>
    apiClient.put<User>('/users/me', data).then((r) => r.data),

  getUsage: (): Promise<Usage> =>
    apiClient.get<Usage>('/users/me/usage').then((r) => r.data),

  getSubscription: (): Promise<SubscriptionResponse> =>
    apiClient.get<SubscriptionResponse>('/users/me/subscription').then((r) => r.data),

  createBillingPortal: (data?: { return_url?: string }): Promise<{ portal_url: string }> =>
    apiClient.post<{ portal_url: string }>('/billing/portal', data ?? {}).then((r) => r.data),

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

  // Backend returns an envelope: `{ status: 'not_generated' | 'failed', company_research: null }`
  // when absent, or the flat CompanyResearchResult fields plus `status: 'completed'` when present.
  // Only a completed result is a real artifact; anything else unwraps to null.
  getCompanyResearch: (jobId: string): Promise<CompanyResearchResult | null> =>
    apiFetchOrNull(() =>
      apiClient
        .get<CompanyResearchResult & { status?: string }>(`/company-research/${jobId}`)
        .then((r) => (r.data?.status === 'completed' ? r.data : null)),
    ),

  cancelCompanyResearch: (jobId: string): Promise<{ status: string }> =>
    apiClient.post<{ status: string }>(`/company-research/${jobId}/cancel`, {}).then((r) => r.data),

  // ── CV ──
  getCVById: async (cvId: string): Promise<UserCV | null> =>
    apiFetchOrNull(() =>
      apiClient.get<UserCV>(`/users/me/cv/${cvId}`).then((r) => r.data),
    ),

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

  cancelVpr: (vprId: string): Promise<{ status: string }> =>
    apiClient.post<{ status: string }>(`/vpr/${vprId}/cancel`, {}).then((r) => r.data),

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

  cancelCoverLetter: (coverLetterId: string): Promise<{ status: string }> =>
    apiClient.post<{ status: string }>(`/cover-letter/${coverLetterId}/cancel`, {}).then((r) => r.data),

  getCoverLetter: (artifactId: string): Promise<CoverLetterStatusResponse> =>
    apiClient
      .get<CoverLetterStatusResponse>(`/cover-letter/${artifactId}/status`)
      .then((r) => r.data),

  patchCoverLetter: (
    artifactId: string,
    body: { cover_letter: string; base_version?: string | number | null },
  ): Promise<CoverLetterStatusResponse> =>
    apiClient.patch<CoverLetterStatusResponse>(`/cover-letter/${artifactId}`, body).then((r) => r.data),

  getCoverLettersList: async (): Promise<CoverLetterListItem[]> => {
    type RawCL = { id: string; status: string; cv_id?: string; job_id?: string; applicationId?: string; company_name?: string; job_title?: string; created_at: string };
    const [clRes, jobsRes] = await Promise.allSettled([
      apiClient.get<RawCL[] | { cover_letters?: RawCL[] }>('/cover-letters'),
      apiClient.get<{ jobs: Job[] }>('/jobs'),
    ]);
    if (clRes.status === 'rejected') throw clRes.reason as Error;
    const clData = clRes.value.data;
    const rawItems: RawCL[] = Array.isArray(clData) ? clData : ((clData as { cover_letters?: RawCL[] } | null)?.cover_letters ?? []);
    const jobsData = jobsRes.status === 'fulfilled' ? jobsRes.value.data : null;
    const jobMap = new Map<string, Job>((jobsData?.jobs ?? []).map((j) => [j.job_id, j]));
    return rawItems.map((item) => {
      const appId = item.applicationId ?? item.job_id ?? '';
      const job = jobMap.get(appId);
      const s = item.status;
      const status: CoverLetterListItem['status'] =
        s === 'completed' || s === 'done' || s === 'ready' ? 'ready' :
        s === 'processing' || s === 'pending' ? 'processing' :
        item.company_name ? (s as CoverLetterListItem['status']) : 'failed';
      return {
        applicationId: appId,
        artifact_id: item.id,
        company_name: item.company_name ?? job?.company_name ?? '—',
        job_title: item.job_title ?? job?.title ?? '—',
        status,
        created_at: item.created_at,
      };
    });
  },

  // ── Interview Prep ──
  generateInterviewPrep: (data: InterviewPrepRequest): Promise<AsyncTaskResponse> =>
    apiClient.post<AsyncTaskResponse>('/interview-prep/generate', data).then((r) => r.data),

  pollInterviewPrepStatus: (asyncTaskId: string): Promise<InterviewPrepStatusResponse> =>
    apiClient
      .get<InterviewPrepStatusResponse>(`/interview-prep/${asyncTaskId}/status`)
      .then((r) => r.data),

  cancelInterviewPrep: (interviewPrepId: string): Promise<{ status: string }> =>
    apiClient.post<{ status: string }>(`/interview-prep/${interviewPrepId}/cancel`, {}).then((r) => r.data),

  getInterviewPrep: (artifactId: string): Promise<InterviewPrepStatusResponse> =>
    apiClient
      .get<InterviewPrepStatusResponse>(`/interview-prep/${artifactId}/status`)
      .then((r) => r.data),

  patchInterviewPrep: (
    artifactId: string,
    body: { question_id: string; answer: string; base_version?: string | number | null },
  ): Promise<InterviewPrepPatchResponse> =>
    apiClient.patch<InterviewPrepPatchResponse>(`/interview-prep/${artifactId}`, body).then((r) => r.data),

  // ── CV Tailoring ──
  generateCV: (data: CVTailoringRequest): Promise<AsyncTaskResponse> =>
    apiClient.post<AsyncTaskResponse>('/cv-tailoring/generate', data).then((r) => r.data),

  pollCVTailored: (cvTailoringId: string): Promise<CVTailoredStatusResponse> =>
    apiClient
      .get<CVTailoredStatusResponse>(`/cv-tailoring/${cvTailoringId}/status`)
      .then((r) => r.data),

  cancelCvTailoring: (cvTailoringId: string): Promise<{ status: string }> =>
    apiClient.post<{ status: string }>(`/cv-tailoring/${cvTailoringId}/cancel`, {}).then((r) => r.data),

  getCVTailored: (cvTailoringId: string): Promise<CVTailoredStatusResponse> =>
    apiClient
      .get<CVTailoredStatusResponse>(`/cv-tailoring/${cvTailoringId}/status`)
      .then((r) => r.data),

  patchCVTailored: (
    artifactId: string,
    body: { cv_sections?: CVSections; tailored_cv?: string; base_version?: string | number | null },
  ): Promise<CVTailoredStatusResponse> =>
    apiClient.patch<CVTailoredStatusResponse>(`/cv-tailoring/${artifactId}`, body).then((r) => r.data),

  getTailoredCvsList: async (): Promise<TailoredCvListItem[]> => {
    type RawTCv = { id?: string; status?: string; cv_id?: string; job_id?: string; language?: string; job_title?: string; created_at?: string; updated_at?: string };
    const [cvRes, jobsRes] = await Promise.allSettled([
      apiClient.get<RawTCv[] | { tailored_cvs?: RawTCv[]; cv_tailorings?: RawTCv[] }>('/cv-tailorings'),
      apiClient.get<{ jobs: Job[] }>('/jobs'),
    ]);
    if (cvRes.status === 'rejected') throw cvRes.reason as Error;
    const cvData = cvRes.value.data;
    const rawItems: RawTCv[] = Array.isArray(cvData)
      ? cvData
      : ((cvData as { tailored_cvs?: RawTCv[] }).tailored_cvs
          ?? (cvData as { cv_tailorings?: RawTCv[] }).cv_tailorings
          ?? []);
    const jobsData = jobsRes.status === 'fulfilled' ? jobsRes.value.data : null;
    const jobMap = new Map<string, Job>((jobsData?.jobs ?? []).map((j) => [j.job_id, j]));
    return rawItems.map((item) => {
      const appId = item.job_id ?? '';
      const job = jobMap.get(appId);
      const s = item.status ?? '';
      const status: TailoredCvListStatus =
        s === 'completed' || s === 'ready' ? 'ready' :
        s === 'processing' || s === 'pending' ? 'processing' :
        s === 'edited' ? 'edited' : 'failed';
      const jobTitle = item.job_title ?? job?.title ?? '';
      const companyName = job?.company_name ?? '';
      const title = jobTitle && companyName
        ? `${jobTitle} — ${companyName}`
        : jobTitle || companyName || item.id || 'Tailored CV';
      return {
        id: item.id ?? '',
        applicationId: appId,
        title,
        language: item.language ?? 'en',
        status,
        updated_at: item.updated_at ?? item.created_at ?? '',
      };
    });
  },

  // ── Export ──
  exportArtifact: (jobId: string, moduleType: string, format: 'docx' | 'pdf'): Promise<ExportResponse> =>
    apiClient
      .get<ExportResponse>(`/jobs/${jobId}/artifacts/${moduleType}/export?format=${format}`)
      .then((r) => r.data),

  // ── AI Assist ──
  postAiAssist: (request: {
    artifact_type: 'gap_analysis' | 'cv_tailored' | 'cover_letter' | 'interview_prep';
    artifact_id: string;
    application_id: string;
    field_key: string;
    current_text: string;
    locale?: string;
  }): Promise<{ generated_markdown: string; model: string; tokens: number }> =>
    apiClient
      .post<{ generated_markdown: string; model: string; tokens: number }>('/ai/assist', request)
      .then((r) => r.data),
};
