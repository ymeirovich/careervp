export interface User {
  id: string;
  user_id: string;
  email: string;
  name?: string;
  preferences?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Usage {
  trial: {
    active: boolean;
    days_elapsed: number;
    days_remaining: number;
    ends_at: string;
  };
  applications: {
    used: number;
    remaining: number;
  };
}

export interface SubscriptionDetails {
  plan_type: "monthly" | "annual";
  status: "active" | "expired" | "canceled";
  current_period_end?: string;
}

export interface SubscriptionResponse {
  subscription: SubscriptionDetails | null;
  has_active_subscription: boolean;
}

export interface Job {
  id: string;
  job_id: string;
  title: string;
  company_name: string;
  status: string;
  created_at: string;
  url?: string;
  description?: string;
}

export interface CreateJobInput {
  title: string;
  company_name: string;
  description: string;
  url?: string;
  requirements?: string[];
}

// ── Async task response (VPR / Cover Letter / Interview Prep generate) ──
export interface AsyncTaskResponse {
  request_id: string; // async task ID — use to poll status (NOT the job posting ID)
  job_id?: string;    // alias for request_id returned by some endpoints
  status: "processing" | "completed"; // "completed" returned for idempotent duplicate requests
  estimated_time_seconds?: number;
}

// ── Artifact status (hub artifacts) ──
export type ArtifactStatus = "pending" | "processing" | "completed" | "failed";

export interface HubArtifact {
  status: ArtifactStatus;
  artifact_id: string | null;
}

// ── Job Detail ──
export interface JobDetail {
  job_id: string;
  user_id: string;
  title: string; // normalized from role_title in single-job endpoint
  company_name: string; // normalized from company in single-job endpoint
  description?: string;
  status: string;
  created_at: string;
  url?: string;
  requirements: string[];
}

// ── CV ──
export interface ContactInfo {
  name?: string;
  email?: string;
  phone?: string;
  location?: string;
  linkedin?: string;
}

export interface WorkExperience {
  company: string;
  role: string;
  dates: string;
  current: boolean;
  achievements: string[];
  technologies: string[];
}

export interface Education {
  institution: string;
  degree: string;
  graduation_date: string;
  field_of_study?: string;
  honors: string[];
}

export interface Certification {
  name: string;
  issuer?: string;
  date?: string;
  credential_id?: string;
}

export interface UserCV {
  cv_id?: string;
  user_id: string;
  full_name: string;
  language: "en" | "he";
  contact_info: ContactInfo;
  professional_summary?: string;
  experience: WorkExperience[];
  education: Education[];
  skills: string[];
  certifications: Certification[];
  top_achievements: string[];
  languages: string[];
  created_at?: string;
  updated_at?: string;
}

// ── Gap Analysis ──
export interface GapQuestion {
  question_id: string;
  question: string;
  impact: "HIGH" | "MEDIUM" | "LOW";
  probability: "HIGH" | "MEDIUM" | "LOW";
  gap_score: number;
  tags: string[];
}

export interface GapResponse {
  question_id: string;
  response: string;
}

export interface GapAnalysisRequest {
  job_id: string;
  cv_id: string;
}

export interface GapAnalysisResponse {
  questions: GapQuestion[];
}

// ── VPR ──
export interface EvidenceItem {
  requirement: string;
  evidence: string;
  alignment_score: "STRONG" | "MODERATE" | "DEVELOPING";
  impact_potential: string;
}

export interface GapStrategy {
  gap: string;
  mitigation_approach: string;
  transferable_skills: string[];
}

export interface VPR {
  application_id: string;
  user_id: string;
  executive_summary: string;
  evidence_matrix: EvidenceItem[];
  differentiators: string[];
  gap_strategies: GapStrategy[];
  cultural_fit?: string;
  talking_points: string[];
  keywords: string[];
  version: number;
  language: string;
  created_at: string;
  word_count: number;
}

export interface VPRGenerateRequest {
  job_id: string; // the job posting job_id
  cv_id: string;
  gap_response_ids: string[];
  options?: Record<string, unknown>;
}

export interface VPRDifferentiator {
  text: string;
  source: string;
}

export interface VPRStatusResult {
  uvp?: string;
  strategic_narrative?: string;
  company_job_fit_score?: number;
  differentiators?: VPRDifferentiator[];
  meta_evaluation?: { persuasion_score: number; completeness_score: number };
  download_url?: string;
}

export interface VPRStatusResponse {
  id?: string;
  status: ArtifactStatus;
  result?: VPRStatusResult;
  created_at?: string;
  completed_at?: string;
}

// ── VPR Full Data (fetched from S3 download_url) ──
export interface VPRFullStrength {
  strength: string;
  evidence: string;
  relevanceToRole: string;
}
export interface VPRFullConcern {
  concern: string;
  severity: string;
  mitigation: string;
}
export interface VPRCoreResponsibility {
  responsibility: string;
  alignmentScore: number;
  candidateEvidence: string[];
  evidenceQuality: string;
}
export interface VPRMustHave {
  requirement: string;
  candidateMeetsRequirement: boolean;
  evidence: string;
  strengthOfEvidence: string;
}
export interface VPRRelevantExperience {
  role: string;
  organization: string;
  duration: string;
  keyAchievements: Array<{ achievement: string; metric: string; impact: string }>;
  relevanceToTargetRole: string;
  relevanceScore: number;
}
export interface VPRObjection {
  objection: string;
  likelihood: string;
  mitigation: { strategy: string; messaging: string };
  whereToAddress: string[];
}
export interface VPRFullData {
  applicationId: string;
  metadata: {
    reportDate: string;
    candidateName: string;
    targetRole: string;
    targetCompany: string;
  };
  executiveSummary: {
    overallFitScore: number;
    fitRationale: string;
    topThreeStrengths: VPRFullStrength[];
    topThreeConcerns: VPRFullConcern[];
    recommendedApproach: string;
  };
  roleAlignment: {
    coreResponsibilities: VPRCoreResponsibility[];
    requirementBreakdown: {
      mustHave: VPRMustHave[];
      niceToHave: Array<{ preference: string; candidateHasThis: boolean; evidence: string }>;
    };
  };
  experienceMapping: {
    relevantExperiences: VPRRelevantExperience[];
    experienceGaps: Array<{
      missingExperience: string;
      impactOnCandidacy: string;
      compensatingFactors: string[];
      mitigationStrategy: string;
    }>;
  };
  skillsAnalysis: {
    technicalSkills: Array<{
      skill: string;
      requiredLevel: string;
      candidateLevel: string;
      evidence: string;
      gap: boolean;
    }>;
    softSkills: Array<{
      skill: string;
      candidateDemonstrates: boolean;
      evidence: string;
      strengthLevel: string;
    }>;
  };
  evidenceGaps: {
    priorityGapsToAddress: Array<{
      gap: string;
      priority: number;
      actionItem: string;
      deadline: string;
    }>;
  };
  differentiators: {
    uniqueStrengths: Array<{ strength: string; rarity: string; relevance: string; proof: string }>;
    positioningStatement: string;
  };
  concernsAndMitigations: {
    likelyObjections: VPRObjection[];
    preemptiveResponses: Array<{ concern: string; preemptiveAction: string }>;
  };
  valueProposition: {
    primaryValue: { statement: string; evidence: string; outcomeForCompany: string };
    elevatorPitch: string;
  };
  applicationStrategy: {
    messagingApproach: string;
    atsKeywords: { primary: string[]; secondary: string[] };
    cvLeadDifferentiator: string;
    sectionsToCompress: string[];
  };
  companyInsights?: {
    missionAndPosition: string;
    recentInitiatives: string[];
    currentChallenges: string[];
  };
}

// ── Cover Letter ──
export interface CoverLetterParagraph {
  type: "hook" | "proof_points" | "close";
  content: string;
  word_count: number;
}

export interface CoverLetter {
  cover_letter_id: string;
  user_id: string;
  job_id: string;
  cv_id: string;
  vpr_id: string;
  full_text: string;
  paragraphs: CoverLetterParagraph[];
  word_count: number;
  tone: string;
  created_at: string;
  version: number;
}

export interface CoverLetterRequest {
  job_id: string;
  cv_id: string;
  vpr_id: string;
  gap_response_ids: string[];
  company_research_id: string;
  options?: Record<string, unknown>;
}

export interface CoverLetterStatusResponse {
  id?: string;
  status: string;
  result?: { cover_letter?: string };
}

// ── Interview Prep ──
export interface STARAnswer {
  situation: string;
  task: string;
  action: string;
  result: string;
  full_text: string;
  word_count: number;
}

export interface InterviewQuestion {
  question_id: string;
  question: string;
  question_type: "behavioral" | "technical" | "situational" | "gap_focused";
  difficulty: "easy" | "medium" | "hard";
  suggested_answer?: STARAnswer;
  why_asked: string;
  tips: string[];
}

export interface InterviewerQuestion {
  question: string;
  purpose: string;
}

export interface InterviewPrep {
  prep_id: string;
  user_id: string;
  job_id?: string;
  vpr_id: string;
  questions: InterviewQuestion[];
  questions_to_ask: InterviewerQuestion[];
  salary_guidance?: string;
  pre_interview_checklist: string[];
  created_at: string;
  version: number;
}

export interface InterviewPrepRequest {
  vpr_id: string;
  gap_response_ids: string[];
  application_id?: string;
  job_id?: string;
  language?: string;
}

export interface PrepQuestion {
  id: string;
  text: string;
  question_type: string;
  suggested_answer?: {
    format: string;
    situation?: string;
    task?: string;
    action?: string;
    result?: string;
  };
}

export interface InterviewPrepStatusResponse {
  id?: string;
  status: string;
  result?: {
    questions?: PrepQuestion[];
    questions_to_ask?: Array<{ question: string; purpose: string }>;
    pre_interview_checklist?: string[];
    salary_guidance?: string | null;
    interview_report?: { readiness_summary: string };
  };
}

// ── Company Research ──
export interface CompanyResearchRequest {
  job_id: string;
  url?: string;
  company_name?: string;
}

export interface CompanyResearchResult {
  id: string;
  company_name?: string | null;
  mission?: string | null;
  values: string[];
  culture?: string | null;
  recent_news: Array<{ title?: string; date?: string }>;
  products: string[];
  funding_status?: string | null;
  size_range?: string | null;
  industry?: string | null;
}

// ── CV Tailoring ──
export interface CVTailoringRequest {
  cv_id: string;
  job_id: string;
  vpr_id: string | null; // must be present (even as null) so backend detects new-API flow
}

export interface CVTailoredStatusResponse {
  id?: string;
  status: ArtifactStatus;
  result?: {
    tailored_cv?: string;
    ats_score?: number;
    keyword_matches?: { matched: string[]; missing: string[] };
    suggestions?: string[];
  };
}

// ── Application Hub (GET /applications/{application_id}) ──
export interface ApplicationHubData {
  application: {
    application_id: string; // same value as job_id
    state: string;
    created_at: string;
    trial_credit_consumed: boolean;
  };
  job: JobDetail;
  cv: { cv_id: string } | null;
  gap_analysis: {
    questions: Array<{ question_id?: string; id?: string; [key: string]: unknown }>;
    responses: Array<{ question_id: string; [key: string]: unknown }>;
  };
  artifacts: {
    vpr: HubArtifact;
    cover_letter: HubArtifact;
    interview_prep: HubArtifact;
    cv_tailored: HubArtifact;
    gap_analysis: HubArtifact;
  };
  reload_route?: string;
}
