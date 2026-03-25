# Frontend Reference — CareerVP (Components, API, Types, Tokens, Checklist)

> **Read first:** `IMPLEMENTATION.md` — architecture overview, ID glossary, routing table, dependency chain, shared layout, and Dashboard page.
> **Page specs:** `IMPLEMENTATION-PAGES.md` — component hierarchies and data flows for all 7 feature pages.

---

## Table of Contents

11. [Shared Components](#shared-components)
12. [API Client Methods](#api-client-methods)
13. [TypeScript Types](#typescript-types)
14. [Design Tokens](#design-tokens)
15. [Testing Checklist](#testing-checklist)

---

## Shared Components

### `components/dashboard/ResourceCard.tsx`

Reusable card for the Application Hub grid.

```typescript
interface ResourceCardProps {
  title: string
  description: string                                          // subtitle / hint
  status: 'not_started' | 'processing' | 'ready' | 'partial' // drives visual state
  statusLabel?: string                                        // e.g. "5 of 8 answered"
  preview?: string                                            // short text when ready
  primaryAction: {
    label: string
    href?: string
    onClick?: () => void
    disabled?: boolean
    loading?: boolean
  }
  secondaryAction?: {
    label: string
    onClick?: () => void
  }
  dependency?: string   // shown when disabled: "Requires VPR"
}
```

**Status indicator dot colors:**
- `not_started` → gray `#6b7280`
- `processing` → amber `#f59e0b` (spinning)
- `partial` → amber `#f59e0b`
- `ready` → green `#16b44b`

**Card height:** `min-h-[140px]` to keep grid uniform.

### `components/ui/Badge.tsx`

```typescript
interface BadgeProps {
  variant: 'green' | 'amber' | 'gray' | 'orange' | 'blue' | 'purple' | 'red'
  size?: 'sm' | 'md'
  children: React.ReactNode
}
```

**Base styling:** `inline-flex items-center rounded-[4px] px-2 py-0.5 text-xs font-medium`

**Variant map:**
| Variant | BG | Text |
|---------|-----|------|
| green | `#dcfce7` | `#16b44b` |
| amber | `#fffbeb` | `#f59e0b` |
| gray | `#f1f5f9` | `#6b7280` |
| orange | `#fff7ed` | `#f97316` |
| blue | `#eff6ff` | `#3b82f6` |
| purple | `#f5f3ff` | `#8b5cf6` |
| red | `#fef2f2` | `#ef4444` |

### `components/ui/FormField.tsx`

```typescript
interface FormFieldProps {
  label: string
  required?: boolean
  hint?: string
  error?: string
  children: React.ReactNode
}
```

**Renders:**
```
<div className="flex flex-col gap-1">
  <label className="text-sm font-medium text-[#1e2229]">
    {label} {required && <span className="text-[#ef4444]">*</span>}
  </label>
  {hint && <p className="text-xs text-[#6b7280]">{hint}</p>}
  {children}  ← input or textarea
  {error && <p className="text-xs text-[#ef4444]">{error}</p>}
</div>
```

**Input styling (shared):**
```typescript
className="rounded-[4px] border border-[#cbd5e1] px-3 py-2 text-sm text-[#1e2229]
           focus:outline-none focus:border-[#f97316] focus:ring-1 focus:ring-[#f97316]"
```

---

## API Client Methods

Add to `lib/api.ts`.

**New helper needed** — graceful 404 handling for optional resources:
```typescript
async function apiFetchOrNull<T>(path: string, init?: RequestInit): Promise<T | null> {
  try {
    return await apiFetch<T>(path, init)
  } catch (err) {
    if (err instanceof Error && err.message.startsWith("API 404")) return null
    throw err
  }
}
```

**New methods:**
```typescript
// Jobs
getJob(jobId: string): Promise<JobDetail>
  // GET /jobs/{jobId}
  // Normalize: map response.company → company_name, response.role_title → title

// Application Hub (single call replaces 7 parallel calls)
getApplication(jobId: string): Promise<ApplicationHubData | null>
  // GET /applications/{jobId}  (application_id = job_id)
  // Use apiFetchOrNull — fresh jobs return 404 until first artifact is generated

// Company Research
fetchCompanyResearch(data: CompanyResearchRequest): Promise<CompanyResearchResult>
  // POST /company-research/fetch

// CV
getCV(): Promise<UserCV | null>
  // GET /users/me/cv — returns single CV or null (apiFetchOrNull)
saveCV(data: Partial<UserCV>): Promise<UserCV>
  // POST /users/me/cv — upsert (create and replace use same endpoint)

// Gap Analysis
getGapQuestions(jobId: string): Promise<GapQuestion[]>
  // GET /jobs/{jobId}/gap-questions — apiFetchOrNull → []
generateGapQuestions(data: GapAnalysisRequest): Promise<GapAnalysisResponse>
  // POST /gap-analysis/questions
saveGapResponses(jobId: string, responses: GapResponse[]): Promise<void>
  // POST /jobs/{jobId}/gap-responses

// VPR — async generation
generateVPR(data: VPRGenerateRequest): Promise<AsyncTaskResponse>
  // POST /vpr/generate → { job_id: asyncTaskId, status, estimated_time_seconds }
pollVPRStatus(asyncTaskId: string): Promise<VPRStatusResponse>
  // GET /vpr/{asyncTaskId}/status → { status: PENDING|PROCESSING|COMPLETED|FAILED, vpr? }

// Cover Letter — async generation
generateCoverLetter(data: CoverLetterRequest): Promise<AsyncTaskResponse>
  // POST /cover-letter/generate → { job_id: asyncTaskId, status, estimated_time_seconds }
pollCoverLetterStatus(asyncTaskId: string): Promise<CoverLetterStatusResponse>
  // GET /cover-letter/{asyncTaskId}/status

// Interview Prep — async generation
generateInterviewPrep(data: InterviewPrepRequest): Promise<AsyncTaskResponse>
  // POST /interview-prep/generate → { job_id: asyncTaskId, status, estimated_time_seconds }
pollInterviewPrepStatus(asyncTaskId: string): Promise<InterviewPrepStatusResponse>
  // GET /interview-prep/{asyncTaskId}/status
```

All methods use the existing `apiFetch` (calls `/api/proxy/{path}` with Bearer token).

---

## TypeScript Types

Add to `lib/types.ts` (derived from Swagger schemas):

```typescript
// ── Async task response (VPR / Cover Letter / Interview Prep generate) ──
interface AsyncTaskResponse {
  job_id: string              // async task ID — use to poll status (NOT the job posting ID)
  status: 'pending' | 'processing'
  estimated_time_seconds: number
}

// ── Application Hub (GET /applications/{application_id}) ──
interface ApplicationHubData {
  application: {
    application_id: string    // same value as job_id
    state: string
    created_at: string
    trial_credit_consumed: boolean
  }
  job: JobDetail
  cv: { cv_id: string } | null
  gap_analysis: {
    questions: GapQuestion[]
    responses: GapResponse[]
  }
  artifacts: {
    vpr: VPRArtifact | null
    cover_letter: CoverLetterArtifact | null
    interview_prep: InterviewPrepArtifact | null
    cv_tailored: object | null
  }
  reload_route?: string
}

// Artifact status wrappers (inside hub artifacts object)
interface VPRArtifact {
  job_id: string              // async task ID
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  vpr?: VPR                   // present when status = COMPLETED
}

interface CoverLetterArtifact {
  job_id: string
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  cover_letter?: CoverLetter
}

interface InterviewPrepArtifact {
  job_id: string
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'
  interview_prep?: InterviewPrep
}

// ── Job Detail ──
interface JobDetail {
  job_id: string
  user_id: string
  title: string               // normalized from role_title in single-job endpoint
  company_name: string        // normalized from company in single-job endpoint
  description?: string
  status: string
  created_at: string
  url?: string
  requirements: string[]
}

// ── VPR Generate Request ──
interface VPRGenerateRequest {
  job_id: string              // the job posting job_id (backend maps this to application_id internally)
  cv_id: string
  gap_response_ids: string[]
  options?: Record<string, unknown>
}

// ── Company Research ──
interface CompanyResearchResult {
  company_name: string
  overview: string
  values: string[]
  mission?: string
  strategic_priorities: string[]
  recent_news: string[]
  financial_summary?: string
  source: 'website_scrape' | 'web_search' | 'llm_fallback'
  source_urls: string[]
  confidence_score: number
  research_timestamp: string
}

// ── CV ──
interface UserCV {
  cv_id?: string
  user_id: string
  full_name: string
  language: 'en' | 'he'
  contact_info: ContactInfo
  professional_summary?: string
  experience: WorkExperience[]
  education: Education[]
  skills: string[]
  certifications: Certification[]
  top_achievements: string[]
  languages: string[]
  created_at?: string
  updated_at?: string
}

interface ContactInfo {
  name?: string; email?: string; phone?: string
  location?: string; linkedin?: string
}

interface WorkExperience {
  company: string; role: string; dates: string
  current: boolean; achievements: string[]; technologies: string[]
}

interface Education {
  institution: string; degree: string; graduation_date: string
  field_of_study?: string; honors: string[]
}

interface Certification {
  name: string; issuer?: string; date?: string; credential_id?: string
}

// ── Gap Analysis ──
interface GapQuestion {
  question_id: string; question: string
  impact: 'HIGH' | 'MEDIUM' | 'LOW'
  probability: 'HIGH' | 'MEDIUM' | 'LOW'
  gap_score: number; tags: string[]
}

interface GapResponse {
  question_id: string; question: string
  answer: string
  destination: 'CV_IMPACT' | 'INTERVIEW_MVP_ONLY'
}

// ── VPR ──
interface VPR {
  application_id: string; user_id: string
  executive_summary: string
  evidence_matrix: EvidenceItem[]
  differentiators: string[]
  gap_strategies: GapStrategy[]
  cultural_fit?: string
  talking_points: string[]
  keywords: string[]
  version: number; language: string
  created_at: string; word_count: number
}

interface EvidenceItem {
  requirement: string; evidence: string
  alignment_score: 'STRONG' | 'MODERATE' | 'DEVELOPING'
  impact_potential: string
}

interface GapStrategy {
  gap: string; mitigation_approach: string; transferable_skills: string[]
}

// ── Cover Letter ──
interface CoverLetter {
  cover_letter_id: string; user_id: string
  job_id: string; cv_id: string; vpr_id: string
  full_text: string
  paragraphs: CoverLetterParagraph[]
  word_count: number; tone: string
  created_at: string; version: number
}

interface CoverLetterParagraph {
  type: 'hook' | 'proof_points' | 'close'
  content: string; word_count: number
}

// ── Interview Prep ──
interface InterviewPrep {
  prep_id: string; user_id: string
  job_id?: string; vpr_id: string
  questions: InterviewQuestion[]
  questions_to_ask: InterviewerQuestion[]
  salary_guidance?: string
  pre_interview_checklist: string[]
  created_at: string; version: number
}

interface InterviewQuestion {
  question_id: string; question: string
  question_type: 'behavioral' | 'technical' | 'situational' | 'gap_focused'
  difficulty: 'easy' | 'medium' | 'hard'
  suggested_answer?: STARAnswer
  why_asked: string; tips: string[]
}

interface STARAnswer {
  situation: string; task: string; action: string; result: string
  full_text: string; word_count: number
}

interface InterviewerQuestion {
  question: string; purpose: string
}
```

---

## Design Tokens

### Colors

| Usage | Hex | Tailwind |
|-------|-----|----------|
| Page BG | `#fcf7f5` | inline style |
| Card / Sidebar BG | white | `bg-white` |
| App Shell BG | `#fafafa` | `bg-[#fafafa]` |
| Border | `#cbd5e1` | `border-[#cbd5e1]` |
| Text Primary | `#1e2229` | `text-[#1e2229]` |
| Text Muted | `#6b7280` | `text-[#6b7280]` |
| Active Green | `#16b44b` | `text-[#16b44b]` |
| Brand Orange (CTA) | `#f97316` | `bg-[#f97316]` |
| Active Nav BG | `rgba(217,217,217,0.61)` | `bg-[rgba(217,217,217,0.61)]` |
| Status Card BG | `rgba(245,245,245,0.61)` | `bg-[rgba(245,245,245,0.61)]` |
| **NEW** Amber / Warning | `#f59e0b` | `text-[#f59e0b]` |
| **NEW** Blue / Behavioral | `#3b82f6` | `text-[#3b82f6]` |
| **NEW** Purple / Technical | `#8b5cf6` | `text-[#8b5cf6]` |
| **NEW** Error | `#ef4444` | `text-[#ef4444]` |
| **NEW** IMMUTABLE Field BG | `rgba(245,245,245,0.8)` | `bg-[rgba(245,245,245,0.8)]` |

### Typography

| Element | Font | Size | Weight | Tailwind |
|---------|------|------|--------|----------|
| Page Title | DM Sans | 24px | semibold | `text-2xl font-semibold` |
| Card Title / Job Title | DM Sans | 18px | bold | `text-lg font-bold` |
| Section Title | DM Sans | 16px | bold | `text-base font-bold` |
| Nav Items | DM Sans | 14px | bold | `text-sm font-bold` |
| Body / Table | DM Sans | 14px | medium | `text-sm font-medium` |
| Hint / Meta | DM Sans | 12px | normal | `text-xs text-[#6b7280]` |

### Layout Dimensions (unchanged)

| Component | Size |
|-----------|------|
| Sidebar | 240px wide |
| Topbar | 80px tall |
| App Shell | 1239px × min 900px |
| Main Content Gap | 24px (`gap-6`) |
| Main Content Padding | 24px (`p-6`) |
| Card Border Radius | 8px |
| Input Border Radius | 4px |

### Figma Assets (7-day URLs — export to `/public/icons/` before production)

```typescript
const ASSET_CVP_LOGO = "https://www.figma.com/api/mcp/asset/661cfe6f-1041-4faa-8666-3d001bb92746"
const ASSET_STATUS_DOT = "https://www.figma.com/api/mcp/asset/62714d3b-6e61-40cf-917d-9ad5f45735ac"
const ASSET_DROPDOWN_ARROW = "https://www.figma.com/api/mcp/asset/29ba343a-ed50-4f60-ab33-814b014f47b8"
```

---

## Testing Checklist

### Design Fidelity
- [ ] All colors match tokens above (no undocumented hex values)
- [ ] Sidebar width 240px, Topbar 80px, app shell 1239px
- [ ] Fonts: DM Sans for all UI, DM Serif Display for display headings (if used)
- [ ] Orange `#f97316` CTAs across all pages

### Navigation
- [ ] "View Application" in Jobs table links to `/dashboard/jobs/{job_id}` (not `#`)
- [ ] Sidebar active state updates correctly by route (path prefix match)
- [ ] CV Center sidebar link → `/dashboard/cv`
- [ ] Breadcrumb links navigate correctly

### Dashboard Page
- [ ] StatusStrip shows real plan/credits/status data
- [ ] Jobs table loads from API
- [ ] "+ New Application" opens modal → new job appears in list

### Application Hub
- [ ] All 6 resource cards render with correct status
- [ ] Disabled cards show dependency hint text
- [ ] Generate buttons trigger API calls with loading states
- [ ] "View" links navigate to correct sub-pages
- [ ] Resource status reflects actual API data (not hardcoded)

### Gap Analysis Form (CRUD)
- [ ] Generate Questions creates question cards
- [ ] Edit mode enables textareas and radio inputs
- [ ] Cancel reverts state (no save to API)
- [ ] Save POSTs responses and shows success toast
- [ ] Save error shows error banner (not crash)
- [ ] Answered count updates as user fills in answers

### VPR / Cover Letter / Interview Prep (Display)
- [ ] All sections render with real API data
- [ ] No crashes on missing optional fields (cultural_fit, salary_guidance, etc.)
- [ ] Copy to Clipboard works (Cover Letter)
- [ ] Expandable question STAR answers toggle correctly (Interview Prep)
- [ ] Alignment score badge colors match spec (STRONG=green, MODERATE=amber, DEVELOPING=gray)

### CV Detail / Edit (CRUD)
- [ ] View mode shows all sections as read-only
- [ ] Edit mode activates inputs for FLEXIBLE fields
- [ ] IMMUTABLE fields (dates, company, role) remain non-editable in edit mode
- [ ] Lock icon visible on immutable headers
- [ ] Skills and languages tag input: add and remove chips
- [ ] Save POSTs to API, success → view mode
- [ ] Cancel → reverts to original data without API call
- [ ] New CV page (`/dashboard/cv/new`) starts in edit mode

### API Integration
- [ ] All new `api.*` methods use Bearer token via proxy
- [ ] `apiFetchOrNull` used for: `getApplication`, `getCV`, `getGapQuestions` — returns null on 404, not an error
- [ ] `getJob` normalizes `company` → `company_name` and `role_title` → `title` from single-job endpoint
- [ ] Loading states shown during all async API calls
- [ ] Error states shown when API calls fail

### Async Generation (VPR / Cover Letter / Interview Prep)
- [ ] Generate button calls POST endpoint → receives `{ job_id: asyncTaskId, status: "processing" }`
- [ ] Polling loop starts immediately after generate response (every 3 seconds)
- [ ] Polling stops when status = COMPLETED or FAILED
- [ ] Polling stops on component unmount (useEffect cleanup)
- [ ] COMPLETED → hub data refreshed via `api.getApplication(jobId)`
- [ ] FAILED → error banner shown on the resource card
- [ ] "Generating…" spinner visible during PENDING/PROCESSING states
- [ ] `estimated_time_seconds` optionally shown as countdown

### ID Mapping
- [ ] `application_id` = `job_id` — confirmed no separate application creation step needed
- [ ] VPR generate request sends `job_id` (job posting ID), NOT the async task ID
- [ ] Async task `job_id` (from generate response) stored separately and used only for polling
- [ ] Hub page URL uses `job.job_id` (not `job.id`)

---

**Last Updated**: March 24, 2026
