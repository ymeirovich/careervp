import { z } from 'zod';
import type {
  ApiErrorEnvelope,
  ApplicationHubData,
  AsyncTaskResponse,
  CompanyResearchResult,
  CoverLetterStatusResponse,
  CVTailoredStatusResponse,
  CVTailoringRequest,
  ExportResponse,
  HubArtifact,
  InterviewPrepPatchResponse,
  InterviewPrepStatusResponse,
  VPRStatusResponse,
} from './types';

export const artifactStatusValues = [
  'pending',
  'processing',
  'completed',
  'failed',
  'cancelled',
  'expired',
  'not_generated',
  'edited',
] as const;

export const artifactStatusSchema = z.enum(artifactStatusValues);

export const hubArtifactSchema = z.object({
  status: artifactStatusSchema,
  artifact_id: z.string().nullable(),
});

export const asyncTaskResponseSchema = z.object({
  request_id: z.string().optional(),
  job_id: z.string().optional(),
  status: z.enum(['processing', 'completed']),
  estimated_time_seconds: z.number().optional(),
});

const jobDetailSchema = z.object({
  job_id: z.string(),
  user_id: z.string(),
  title: z.string(),
  company_name: z.string(),
  description: z.string().optional(),
  status: z.string(),
  created_at: z.string(),
  url: z.string().optional(),
  requirements: z.array(z.string()),
});

export const applicationHubDataSchema = z.object({
  application: z.object({
    application_id: z.string(),
    state: z.string(),
    created_at: z.string(),
    trial_credit_consumed: z.boolean(),
  }),
  job: jobDetailSchema,
  cv: z.object({ cv_id: z.string() }).nullable(),
  gap_analysis: z.object({
    questions: z.array(z.record(z.string(), z.unknown())),
    responses: z.array(z.object({ question_id: z.string() }).catchall(z.unknown())),
  }),
  artifacts: z.object({
    vpr: hubArtifactSchema,
    cover_letter: hubArtifactSchema,
    interview_prep: hubArtifactSchema,
    cv_tailored: hubArtifactSchema,
    gap_analysis: hubArtifactSchema,
  }),
  reload_route: z.string().optional(),
});

const vprDifferentiatorSchema = z.object({
  text: z.string(),
  source: z.string(),
});

export const vprStatusResponseSchema = z.object({
  id: z.string().optional(),
  status: artifactStatusSchema,
  result: z
    .object({
      uvp: z.string().optional(),
      strategic_narrative: z.string().optional(),
      company_job_fit_score: z.number().optional(),
      differentiators: z.array(vprDifferentiatorSchema).optional(),
      meta_evaluation: z
        .object({
          persuasion_score: z.number(),
          completeness_score: z.number(),
        })
        .optional(),
      download_url: z.string().optional(),
    })
    .optional(),
  created_at: z.string().optional(),
  completed_at: z.string().optional(),
  error: z.string().optional(),
});

const prepQuestionSchema = z.object({
  id: z.string(),
  text: z.string(),
  question_type: z.string(),
  answer: z.string().nullable().optional(),
  answer_version: z.number().optional(),
  answer_updated_at: z.string().nullable().optional(),
  suggested_answer: z
    .object({
      format: z.string(),
      situation: z.string().optional(),
      task: z.string().optional(),
      action: z.string().optional(),
      result: z.string().optional(),
      full_text: z.string().optional(),
    })
    .optional(),
});

export const interviewPrepStatusResponseSchema = z.object({
  id: z.string().optional(),
  status: z.string(),
  updated_at: z.string().optional(),
  version: z.number().optional(),
  result: z
    .object({
      questions: z.array(prepQuestionSchema).optional(),
      questions_to_ask: z.array(z.object({ question: z.string(), purpose: z.string() })).optional(),
      pre_interview_checklist: z.array(z.string()).optional(),
      salary_guidance: z.string().nullable().optional(),
      interview_report: z.object({ readiness_summary: z.string() }).optional(),
    })
    .optional(),
  error: z.string().optional(),
});

export const interviewPrepPatchResponseSchema = z.object({
  status: z.string(),
  interview_prep_id: z.string().optional(),
  question_id: z.string(),
  answer: z.string(),
  answer_version: z.number().optional(),
  answer_updated_at: z.string().nullable().optional(),
});

export const coverLetterStatusResponseSchema = z.object({
  id: z.string().optional(),
  status: z.string(),
  updated_at: z.string().optional(),
  version: z.number().optional(),
  result: z.object({ cover_letter: z.string().optional() }).optional(),
  error: z.string().optional(),
});

const cvSectionsSchema = z.object({
  contact: z.object({
    name: z.string(),
    email: z.string().nullable().optional(),
    phone: z.string().nullable().optional(),
    linkedin: z.string().nullable().optional(),
    location: z.string().nullable().optional(),
  }),
  summary: z.string(),
  skills: z.object({
    technical: z.array(z.string()),
    soft: z.array(z.string()),
  }),
  experience: z.array(
    z.object({
      company: z.string(),
      title: z.string(),
      start_date: z.string(),
      end_date: z.string().nullable().optional(),
      is_current: z.boolean(),
      location: z.string().nullable().optional(),
      bullets: z.array(
        z.object({
          text: z.string(),
          source: z.string(),
          user_edited: z.boolean(),
          quantified: z.boolean(),
        }),
      ),
    }),
  ),
  education: z.array(
    z.object({
      degree: z.string(),
      field: z.string(),
      institution: z.string(),
      graduation_date: z.string(),
      gpa: z.string().nullable().optional(),
    }),
  ),
  certifications: z.array(z.object({ name: z.string(), issuer: z.string(), date: z.string() })),
  languages: z.array(z.string()).nullable().optional(),
});

export const cvTailoredStatusResponseSchema = z.object({
  id: z.string().optional(),
  status: artifactStatusSchema,
  version: z.number().optional(),
  language: z.string().optional(),
  generated_at: z.string().optional(),
  updated_at: z.string().optional(),
  result: z
    .object({
      tailored_cv: z.string().optional(),
      cv_sections: cvSectionsSchema.optional(),
      ats_score: z.number().optional(),
      ats_grade: z.string().optional(),
      ats_result: z
        .object({
          total_score: z.number(),
          grade: z.string(),
          components: z.object({
            keyword_match: z.number(),
            quantified_bullets: z.number(),
            section_headers: z.number(),
            formatting_safety: z.number(),
            summary_keyword_density: z.number(),
          }),
          keywords_matched: z.array(z.string()),
          keywords_missing: z.array(z.string()),
          keyword_match_score_1_10: z.number(),
        })
        .optional(),
      keyword_match_score: z.number().optional(),
      keywords_matched: z.array(z.string()).optional(),
      keywords_missing: z.array(z.string()).optional(),
      fact_verification_detail: z
        .object({
          passed: z.boolean(),
          items_corrected: z.number(),
          items_removed: z.number(),
        })
        .optional(),
      suggestions: z.array(z.string()).optional(),
      keyword_matches: z.object({ matched: z.array(z.string()), missing: z.array(z.string()) }).optional(),
    })
    .optional(),
});

export const cvTailoringRequestSchema = z
  .object({
    cv_id: z.string(),
    job_id: z.string(),
    vpr_id: z.string().nullable(),
  })
  .strict();

export const companyResearchResultSchema = z.object({
  id: z.string(),
  company_name: z.string().nullable().optional(),
  mission: z.string().nullable().optional(),
  values: z.array(z.string()).nullable().optional(),
  culture: z.string().nullable().optional(),
  recent_news: z.array(z.union([z.object({ title: z.string().optional(), date: z.string().optional() }), z.string()])).nullable().optional(),
  products: z.array(z.string()).nullable().optional(),
  funding_status: z.string().nullable().optional(),
  size_range: z.string().nullable().optional(),
  industry: z.string().nullable().optional(),
});

export const exportResponseSchema = z.object({
  download_url: z.string(),
  expires_at: z.string(),
});

export const flatErrorEnvelopeSchema = z
  .object({
    error: z.string().optional(),
    message: z.string().optional(),
    classification: z.string().optional(),
    error_code: z.string().optional(),
    field: z.string().optional(),
  })
  .strict()
  .refine((value) => value.error !== undefined || value.message !== undefined, {
    message: 'flat error envelope requires error or message',
  });

export const contractSchemas = {
  ApplicationHubData: applicationHubDataSchema,
  AsyncTaskResponse: asyncTaskResponseSchema,
  CompanyResearchResult: companyResearchResultSchema,
  CoverLetterStatusResponse: coverLetterStatusResponseSchema,
  CVTailoredStatusResponse: cvTailoredStatusResponseSchema,
  CVTailoringRequest: cvTailoringRequestSchema,
  ErrorResponse: flatErrorEnvelopeSchema,
  ExportResponse: exportResponseSchema,
  InterviewPrepPatchResponse: interviewPrepPatchResponseSchema,
  InterviewPrepStatusResponse: interviewPrepStatusResponseSchema,
  VPRStatusResponse: vprStatusResponseSchema,
} as const;

const _hubArtifactSchema: z.ZodType<HubArtifact> = hubArtifactSchema;
const _asyncTaskSchema: z.ZodType<AsyncTaskResponse> = asyncTaskResponseSchema;
const _applicationHubSchema: z.ZodType<ApplicationHubData> = applicationHubDataSchema;
const _vprStatusSchema: z.ZodType<VPRStatusResponse> = vprStatusResponseSchema;
const _interviewPrepStatusSchema: z.ZodType<InterviewPrepStatusResponse> = interviewPrepStatusResponseSchema;
const _interviewPrepPatchSchema: z.ZodType<InterviewPrepPatchResponse> = interviewPrepPatchResponseSchema;
const _coverLetterStatusSchema: z.ZodType<CoverLetterStatusResponse> = coverLetterStatusResponseSchema;
const _cvTailoredStatusSchema: z.ZodType<CVTailoredStatusResponse> = cvTailoredStatusResponseSchema;
const _cvTailoringRequestSchema: z.ZodType<CVTailoringRequest> = cvTailoringRequestSchema;
const _companyResearchSchema: z.ZodType<CompanyResearchResult> = companyResearchResultSchema;
const _exportResponseSchema: z.ZodType<ExportResponse> = exportResponseSchema;
const _flatErrorSchema: z.ZodType<ApiErrorEnvelope> = flatErrorEnvelopeSchema;

void [
  _hubArtifactSchema,
  _asyncTaskSchema,
  _applicationHubSchema,
  _vprStatusSchema,
  _interviewPrepStatusSchema,
  _interviewPrepPatchSchema,
  _coverLetterStatusSchema,
  _cvTailoredStatusSchema,
  _cvTailoringRequestSchema,
  _companyResearchSchema,
  _exportResponseSchema,
  _flatErrorSchema,
];
