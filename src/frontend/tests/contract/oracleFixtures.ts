import type { BackendSchemaName } from '../../lib/contractOracle';
import type { ApplicationHubData, VPRStatusResponse } from '../../lib/types';

export const applicationHubFixture: ApplicationHubData = {
  application: {
    application_id: 'job-1',
    state: 'active',
    created_at: '2026-07-01T00:00:00Z',
    trial_credit_consumed: true,
  },
  job: {
    job_id: 'job-1',
    user_id: 'user-1',
    title: 'Staff Engineer',
    company_name: 'Acme',
    description: 'Build systems',
    status: 'active',
    created_at: '2026-07-01T00:00:00Z',
    url: 'https://example.com/job',
    requirements: ['TypeScript', 'Python'],
  },
  cv: { cv_id: 'cv-1' },
  gap_analysis: {
    questions: [{ question_id: 'gq-1', question: 'Tell me about scale' }],
    responses: [{ question_id: 'gq-1', response: 'Scaled an API' }],
  },
  artifacts: {
    vpr: { status: 'completed', artifact_id: 'vpr-1' },
    cover_letter: { status: 'completed', artifact_id: 'cl-1' },
    interview_prep: { status: 'completed', artifact_id: 'ip-1' },
    cv_tailored: { status: 'edited', artifact_id: 'cv-tailored-1' },
    gap_analysis: { status: 'completed', artifact_id: null },
  },
  reload_route: '/applications/job-1',
};

export const asyncTaskFixtures = {
  requestOnly: { request_id: 'req-only', status: 'processing', estimated_time_seconds: 30 },
  jobOnly: { job_id: 'job-only', status: 'processing' },
  both: { request_id: 'req-wins', job_id: 'job-alias', status: 'completed' },
} as const;

export const vprStatusSuccessFixture: VPRStatusResponse = {
  id: 'vpr-1',
  status: 'completed',
  result: {
    uvp: 'Operational leader with systems depth',
    strategic_narrative: 'A concise narrative',
    company_job_fit_score: 9,
    differentiators: [{ text: 'Scaled revenue platform', source: 'cv' }],
    meta_evaluation: { persuasion_score: 9, completeness_score: 8 },
    download_url: 'https://signed.example.com/vpr.docx?sig=abc',
  },
  created_at: '2026-07-01T00:00:00Z',
  completed_at: '2026-07-01T00:02:00Z',
};

export const vprStatusMissingDownloadFixture = {
  id: 'vpr-1',
  status: 'completed',
  result: {
    uvp: 'Operational leader with systems depth',
  },
} as const;

export const cvTailoringRequestNullFixture = {
  cv_id: 'cv-1',
  job_id: 'job-1',
  vpr_id: null,
} as const;

export const cvTailoringRequestWithVprFixture = {
  cv_id: 'cv-1',
  job_id: 'job-1',
  vpr_id: 'vpr-1',
} as const;

export const cvTailoringRequestOmittedFixture = {
  cv_id: 'cv-1',
  job_id: 'job-1',
} as const;

export const interviewPrepPatchFixture = {
  status: 'completed',
  interview_prep_id: 'ip-1',
  question_id: 'q1',
  answer: 'Situation, task, action, result.',
  answer_version: 3,
  answer_updated_at: '2026-07-01T00:03:00Z',
} as const;

export const interviewPrepStatusFixture = {
  id: 'ip-1',
  status: 'completed',
  updated_at: '2026-07-01T00:03:00Z',
  version: 2,
  result: {
    questions: [
      {
        id: 'q1',
        text: 'Describe a complex delivery.',
        question_type: 'behavioral',
        answer: 'STAR answer',
        answer_version: 3,
        answer_updated_at: '2026-07-01T00:03:00Z',
        suggested_answer: {
          format: 'STAR',
          situation: 'A scaling challenge',
          task: 'Lead delivery',
          action: 'Aligned teams',
          result: 'Reduced latency',
          full_text: 'A full suggested answer',
        },
      },
    ],
    questions_to_ask: [{ question: 'How does the team measure impact?', purpose: 'Understand priorities' }],
    pre_interview_checklist: ['Review VPR'],
    salary_guidance: null,
    interview_report: { readiness_summary: 'Ready' },
  },
} as const;

export const coverLetterStatusFixture = {
  id: 'cl-1',
  status: 'completed',
  updated_at: '2026-07-01T00:03:00Z',
  version: 1,
  result: { cover_letter: 'Dear hiring team...' },
} as const;

export const cvTailoredStatusFixture = {
  id: 'cv-tailored-1',
  status: 'edited',
  version: 4,
  language: 'en',
  generated_at: '2026-07-01T00:02:00Z',
  updated_at: '2026-07-01T00:03:00Z',
  result: {
    tailored_cv: 'Tailored CV text',
    cv_sections: {
      contact: { name: 'Jane Candidate', email: 'jane@example.com', phone: null, linkedin: null, location: 'NYC' },
      summary: 'Product-minded engineering leader.',
      skills: { technical: ['Python'], soft: ['Leadership'] },
      experience: [
        {
          company: 'Acme',
          title: 'Staff Engineer',
          start_date: '2022',
          end_date: null,
          is_current: true,
          location: null,
          bullets: [{ text: 'Improved reliability by 20%', source: 'cv', user_edited: false, quantified: true }],
        },
      ],
      education: [{ degree: 'BS', field: 'CS', institution: 'Example University', graduation_date: '2016', gpa: null }],
      certifications: [{ name: 'AWS', issuer: 'Amazon', date: '2024' }],
      languages: ['English'],
    },
    ats_score: 92,
    ats_grade: 'A',
    ats_result: {
      total_score: 92,
      grade: 'A',
      components: {
        keyword_match: 20,
        quantified_bullets: 20,
        section_headers: 20,
        formatting_safety: 20,
        summary_keyword_density: 12,
      },
      keywords_matched: ['Python'],
      keywords_missing: ['Kubernetes'],
      keyword_match_score_1_10: 8,
    },
    keyword_match_score: 8,
    keywords_matched: ['Python'],
    keywords_missing: ['Kubernetes'],
    fact_verification_detail: { passed: true, items_corrected: 0, items_removed: 0 },
    suggestions: ['Add one more platform example'],
    keyword_matches: { matched: ['Python'], missing: ['Kubernetes'] },
  },
} as const;

export const companyResearchStringNewsFixture = {
  id: 'cr-1',
  company_name: 'Acme',
  mission: 'Build useful systems',
  values: ['Customer focus'],
  culture: null,
  recent_news: ['Acme launches a platform'],
  products: ['Platform'],
  funding_status: 'private',
  size_range: '100-500',
  industry: 'Software',
} as const;

export const companyResearchObjectNewsFixture = {
  ...companyResearchStringNewsFixture,
  recent_news: [{ title: 'Acme launches a platform', date: '2026-06-01' }],
} as const;

export const exportResponseFixture = {
  download_url: 'https://signed.example.com/export.docx?sig=abc',
  expires_at: '2026-07-01T01:00:00Z',
} as const;

export const flatErrorFixture = {
  error: 'Stale base_version; the answer was modified elsewhere',
  classification: 'conflict',
  error_code: 'DYNAMODB_CONDITION_CHECK_FAILED',
  field: 'base_version',
} as const;

export const nestedErrorFixture = {
  error: {
    code: 'DYNAMODB_CONDITION_CHECK_FAILED',
    message: 'Stale base_version',
    details: [{ field: 'base_version', message: 'stale' }],
  },
} as const;

export const statusEndpointFixtures = {
  vpr: vprStatusSuccessFixture,
  cover_letter: coverLetterStatusFixture,
  interview_prep: interviewPrepStatusFixture,
  cv_tailored: cvTailoredStatusFixture,
  gap_analysis: null,
} as const;

export const vprFullDataFixture = {
  applicationId: 'job-1',
  metadata: {
    reportDate: '2026-07-01',
    candidateName: 'Jane Candidate',
    targetRole: 'Staff Engineer',
    targetCompany: 'Acme',
  },
  executiveSummary: {
    overallFitScore: 9,
    fitRationale: 'Strong evidence',
    topThreeStrengths: [{ strength: 'Scale', evidence: 'Latency reduction', relevanceToRole: 'High' }],
    topThreeConcerns: [{ concern: 'Domain gap', severity: 'low', mitigation: 'Bridge with platform work' }],
    recommendedApproach: 'Lead with reliability outcomes',
  },
  roleAlignment: {
    coreResponsibilities: [{ responsibility: 'Build APIs', alignmentScore: 9, candidateEvidence: ['API work'], evidenceQuality: 'strong' }],
    requirementBreakdown: {
      mustHave: [{ requirement: 'Python', candidateMeetsRequirement: true, evidence: 'Backend work', strengthOfEvidence: 'strong' }],
      niceToHave: [{ preference: 'Kubernetes', candidateHasThis: false, evidence: 'Adjacent platform work' }],
    },
  },
  experienceMapping: {
    relevantExperiences: [
      {
        role: 'Staff Engineer',
        organization: 'Acme',
        duration: '2 years',
        keyAchievements: [{ achievement: 'Improved reliability', metric: '20%', impact: 'Fewer incidents' }],
        relevanceToTargetRole: 'Direct',
        relevanceScore: 9,
      },
    ],
    experienceGaps: [{ missingExperience: 'Domain', impactOnCandidacy: 'Low', compensatingFactors: ['Fast learner'], mitigationStrategy: 'Frame platform depth' }],
  },
  skillsAnalysis: {
    technicalSkills: [{ skill: 'Python', requiredLevel: 'high', candidateLevel: 'high', evidence: 'Projects', gap: false }],
    softSkills: [{ skill: 'Leadership', candidateDemonstrates: true, evidence: 'Led teams', strengthLevel: 'high' }],
  },
  evidenceGaps: {
    priorityGapsToAddress: [{ gap: 'Kubernetes', priority: 1, actionItem: 'Add project detail', deadline: 'Before submission' }],
  },
  differentiators: {
    uniqueStrengths: [{ strength: 'Systems thinking', rarity: 'high', relevance: 'high', proof: 'Architecture ownership' }],
    positioningStatement: 'Systems leader for reliable platforms',
  },
  concernsAndMitigations: {
    likelyObjections: [{ objection: 'Domain gap', likelihood: 'low', mitigation: { strategy: 'Bridge', messaging: 'Platform patterns transfer' }, whereToAddress: ['interview'] }],
    preemptiveResponses: [{ concern: 'Domain', preemptiveAction: 'Mention learning examples' }],
  },
  valueProposition: {
    primaryValue: { statement: 'Reliable delivery', evidence: 'Reduced incidents', outcomeForCompany: 'Faster execution' },
    elevatorPitch: 'I build reliable systems teams can move quickly on.',
  },
  applicationStrategy: {
    messagingApproach: 'Evidence first',
    atsKeywords: { primary: ['Python'], secondary: ['Reliability'] },
    cvLeadDifferentiator: 'Reliability leadership',
    sectionsToCompress: ['Education'],
  },
  companyInsights: {
    missionAndPosition: 'Build useful software',
    recentInitiatives: ['Platform expansion'],
    currentChallenges: ['Scale'],
  },
} as const;

export const contractFixtureCorpus: Record<BackendSchemaName, unknown> = {
  ApplicationHubData: applicationHubFixture,
  AsyncTaskResponse: asyncTaskFixtures.requestOnly,
  CompanyResearchResult: companyResearchObjectNewsFixture,
  CoverLetterStatusResponse: coverLetterStatusFixture,
  CVTailoredStatusResponse: cvTailoredStatusFixture,
  CVTailoringRequest: cvTailoringRequestNullFixture,
  ErrorResponse: flatErrorFixture,
  ExportResponse: exportResponseFixture,
  InterviewPrepPatchResponse: interviewPrepPatchFixture,
  InterviewPrepStatusResponse: interviewPrepStatusFixture,
  VPRStatusResponse: vprStatusSuccessFixture,
};
