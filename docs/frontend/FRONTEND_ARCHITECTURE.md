# CareerVP Frontend Architecture

**Status:** Design — Pre-Implementation
**Last Updated:** 2026-03-08
**Covers:** Stack selection, API integration, client-side orchestrator, error UX, mobile, hosting

---

## Table of Contents

1. [Technology Stack](#1-technology-stack)
2. [Project Structure](#2-project-structure)
3. [Authentication — AWS Amplify](#3-authentication--aws-amplify)
4. [API Client Layer](#4-api-client-layer)
5. [Response Schema Development](#5-response-schema-development)
6. [CV Upload Flow](#6-cv-upload-flow)
7. [TanStack Query — Server State](#8-tanstack-query--server-state)
8. [Client-Side Orchestrator](#8-client-side-orchestrator)
9. [Error UX — AI Failure Handling](#9-error-ux--ai-failure-handling)
10. [Trial / Quota Enforcement UI](#10-trial--quota-enforcement-ui)
11. [Styling Strategy — HTML Template Integration](#11-styling-strategy--html-template-integration)
12. [Mobile Responsiveness](#12-mobile-responsiveness)
13. [CORS Hardening](#13-cors-hardening)
14. [Hosting Decision](#14-hosting-decision)
15. [Feature Scope Map](#15-feature-scope-map)
16. [API Domain Model](#16-api-domain-model)
17. [Open Questions](#17-open-questions)
18. [Billing & Stripe Integration](#18-billing--stripe-integration)
19. [Admin Portal](#19-admin-portal)

---

## 1. Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Framework | **Next.js 15 (App Router)** | SSR support required for Cognito auth in Server Components; aligns with AWS Amplify adapter |
| Auth | **AWS Amplify v6 (full session management)** | Cognito User Pool `us-east-1_WiHMRqLpe`; auto token refresh; SSR cookie adapter |
| Server State | **TanStack Query v5** | Fire-and-poll pattern for all 4 async AI features; built-in `refetchInterval` with adaptive control |
| Client State | **Zustand + persist middleware** | Orchestrator state that survives page reload (gap draft, job IDs, application stage) |
| Styling | **Tailwind CSS v4 + shadcn/ui** | CSS variable theming bridges HTML template → production components |
| Forms | **React Hook Form + Zod** | Zod is also the runtime API schema validator — single source of truth |
| HTTP | **Custom typed fetch wrapper** | Attaches Cognito JWT from Amplify `fetchAuthSession()` per request |
| Type Gen | **openapi-typescript** | Generate types from `careervp-api-v1.yaml` once schemas stabilize |
| Hosting | **AWS Amplify Hosting (MVP)** | Git push deploy, preview URLs per PR, SSR supported; migrate to CloudFront+ECS at scale |

---

## 2. Project Structure

```
careervp-web/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   └── (dashboard)/
│       ├── layout.tsx              ← auth guard, Amplify config, QueryProvider
│       ├── dashboard/page.tsx      ← jobs list + usage indicator
│       ├── profile/page.tsx        ← CV management, user settings
│       ├── settings/
│       │   └── billing/page.tsx    ← subscription status + Customer Portal button
│       ├── billing/
│       │   ├── checkout/page.tsx   ← Stripe Checkout redirect (server action)
│       │   └── success/page.tsx    ← post-payment confirmation + refresh usage
│       └── jobs/
│           └── [jobId]/
│               ├── layout.tsx      ← load application state, ApplicationProvider
│               ├── page.tsx        ← redirect to reload_route from /applications/{id}
│               ├── gap-questions/
│               │   └── page.tsx    ← Q&A form, auto-save, validation
│               └── artifacts/
│                   ├── page.tsx    ← 4-panel progress + results hub
│                   ├── vpr/        ← Value Proposition Report viewer
│                   ├── cv/         ← side-by-side diff + edit form
│                   ├── cover-letter/
│                   └── interview-prep/
│   └── (admin)/                    ← Cognito group "Admins" required; separate layout
│       ├── layout.tsx              ← admin auth check (group claim), AdminSidebar
│       ├── admin/
│       │   ├── page.tsx            ← admin dashboard: KPI cards + charts
│       │   ├── users/
│       │   │   ├── page.tsx        ← user list with search/filter/sort
│       │   │   └── [userId]/page.tsx ← user detail: profile + usage + apps
│       │   ├── subscriptions/page.tsx ← subscription states table
│       │   ├── jobs/page.tsx       ← all jobs across all users
│       │   └── analytics/page.tsx  ← conversion funnel, cohort charts
├── components/
│   ├── ui/                         ← shadcn/ui components (owned source)
│   ├── auth/                       ← LoginForm, RegisterForm, PasswordReset
│   ├── cv/                         ← CVUpload, CVCard, CVEditForm
│   ├── jobs/                       ← JobCreateForm, JobCard, JobList
│   ├── gap/                        ← GapQuestionCard, GapResponseForm
│   ├── artifacts/                  ← ArtifactCard, ArtifactProgress, DownloadButton
│   ├── billing/                    ← CheckoutButton, BillingPortalButton, PlanCard
│   ├── trial/                      ← TrialGuard, UpgradeBanner, UpgradeModal, CreditIndicator
│   ├── admin/                      ← AdminUserTable, AdminKPICard, AdminChart
│   └── layout/                     ← Header, Sidebar, MobileNav, ErrorBoundary
├── lib/
│   ├── amplify-config.ts           ← Amplify.configure(), cookie storage setup
│   ├── api-client.ts               ← typed fetch wrapper with Cognito JWT
│   ├── schemas/                    ← Zod schemas by domain
│   │   ├── auth.ts
│   │   ├── jobs.ts
│   │   ├── applications.ts
│   │   ├── cv.ts
│   │   ├── artifacts.ts
│   │   ├── billing.ts              ← SubscriptionSchema, CheckoutSessionSchema
│   │   └── admin.ts                ← AdminUserSchema, AdminMetricsSchema
│   ├── api/                        ← API call functions (schema-validated)
│   │   ├── jobs.ts
│   │   ├── applications.ts
│   │   ├── cv.ts
│   │   ├── gap.ts
│   │   ├── artifacts.ts
│   │   ├── billing.ts              ← createCheckoutSession, createPortalSession
│   │   └── admin.ts                ← listUsers, getUser, listSubscriptions
│   └── hooks/                      ← reusable query/mutation hooks
│       ├── useApplication.ts
│       ├── useJobStatus.ts
│       ├── useAsyncFeature.ts
│       └── useSubscription.ts      ← subscription context + gating helpers
├── stores/
│   └── applicationStore.ts         ← Zustand orchestrator state
├── middleware.ts                   ← Amplify SSR auth guard (dashboard + admin)
└── types/
    └── api.d.ts                    ← generated by openapi-typescript
```

---

## 3. Authentication — AWS Amplify

**Decision:** Full Amplify session management with cookie-based storage for SSR compatibility.

### Configuration

```typescript
// lib/amplify-config.ts
import { Amplify } from 'aws-amplify'
import { cognitoUserPoolsTokenProvider } from 'aws-amplify/auth/cognito'
import { CookieStorage } from 'aws-amplify/utils'

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID!,   // us-east-1_WiHMRqLpe
      userPoolClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID!,
    },
  },
})

// Cookie storage required for Next.js App Router SSR
cognitoUserPoolsTokenProvider.setKeyValueStorage(
  new CookieStorage({
    domain: process.env.NEXT_PUBLIC_DOMAIN!,  // 'careervp.com'
    secure: true,
    sameSite: 'strict',
    path: '/',
  })
)
```

### SSR Route Protection

```typescript
// middleware.ts
import { fetchAuthSession } from 'aws-amplify/auth/server'
import { createServerRunner } from '@aws-amplify/adapter-nextjs'
import { NextRequest, NextResponse } from 'next/server'

export const { runWithAmplifyServerContext } = createServerRunner({ config: { Auth: { Cognito: { ... } } } })

export async function middleware(request: NextRequest) {
  const isAuthenticated = await runWithAmplifyServerContext({
    nextServerContext: { request, response: NextResponse.next() },
    operation: async (contextSpec) => {
      try {
        const session = await fetchAuthSession(contextSpec)
        return !!session.tokens
      } catch { return false }
    },
  })

  if (!isAuthenticated && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
}

export const config = { matcher: ['/dashboard/:path*'] }
```

### What Amplify Provides vs. What You Build

| Capability | Amplify Provides | You Build |
|---|---|---|
| Sign in / sign up / sign out | `signIn()`, `signUp()`, `signOut()` | — |
| Token storage | Cookies (via adapter) | — |
| Auto token refresh | `fetchAuthSession()` auto-refreshes | — |
| Authorization header | Via `fetchAuthSession()` call | Attach in api-client.ts |
| Route protection | — | `middleware.ts` |
| Auth UI | Amplify UI (optional, opinionated) | Custom login/register forms |
| RBAC | — | Component-level checks |

---

## 4. API Client Layer

All API calls go through a single wrapper that attaches the Cognito JWT automatically.

```typescript
// lib/api-client.ts
import { fetchAuthSession } from 'aws-amplify/auth'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL!  // https://dev-api.careervp.com

export class ApiError extends Error {
  constructor(public status: number, public body: Record<string, unknown>) {
    super(String(body.error ?? `HTTP ${status}`))
  }
  get isTrialExpired()   { return this.status === 403 && this.body.error === 'trial_expired' }
  get isTrialExhausted() { return this.status === 403 && this.body.error === 'trial_exhausted' }
  get isRateLimited()    { return this.status === 429 }
  get isTimeout()        { return this.status === 504 }
  get isAuthError()      { return this.status === 401 }
}

export async function apiClient<T>(path: string, options: RequestInit = {}): Promise<T> {
  const session = await fetchAuthSession()
  const token = session.tokens?.idToken?.toString()
  if (!token) throw new ApiError(401, { error: 'Not authenticated' })

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: token,
      ...options.headers,
    },
  })

  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(res.status, body)
  return body as T
}
```

### Environment Variables

```bash
# .env.local
NEXT_PUBLIC_API_BASE_URL=https://dev-api.careervp.com
NEXT_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_WiHMRqLpe
NEXT_PUBLIC_COGNITO_CLIENT_ID=<from CDK output>
NEXT_PUBLIC_DOMAIN=localhost   # 'careervp.com' in production
```

---

## 5. Response Schema Development

Schemas below are derived from **observed live API responses** (`live-test-results34.log`), not from the Swagger spec (which lacks body schemas). Use these as the ground truth.

**Workflow:**

1. **Schemas here** → Zod definitions (runtime validation + TypeScript inference)
2. **Wrap each call** with `safeParse` to catch drift early
3. **Phase 4** (future): `npx openapi-typescript docs/swagger/careervp-api-v1.yaml -o src/types/api.d.ts`

---

### Auth Schemas (`lib/schemas/auth.ts`)

```typescript
import { z } from 'zod'

// POST /auth/register → 201
// POST /auth/login    → 200
// POST /auth/refresh  → 200
export const AuthTokenSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  id_token: z.string(),
  expires_in: z.number(),          // 3600
  token_type: z.literal('Bearer'),
})
export type AuthToken = z.infer<typeof AuthTokenSchema>
```

---

### User Schemas (`lib/schemas/user.ts`)

```typescript
// GET /users/me → 200
// PUT /users/me → 200
export const UserSchema = z.object({
  id: z.string(),
  user_id: z.string(),             // same value as id
  email: z.string().email(),
  name: z.string(),
  preferences: z.object({
    timezone: z.string().optional(),
  }).optional(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type User = z.infer<typeof UserSchema>

// GET /users/me/usage → 200
// ⚠ Field is "applications.remaining" not "credits_remaining"
export const UsageSchema = z.object({
  trial: z.object({
    active: z.boolean(),
    days_elapsed: z.number(),
    days_remaining: z.number(),
    ends_at: z.string(),           // ISO 8601 with timezone
  }),
  applications: z.object({
    used: z.number(),
    remaining: z.number(),         // 0–3 on free tier
  }),
})
export type Usage = z.infer<typeof UsageSchema>
```

---

### CV Schemas (`lib/schemas/cv.ts`)

```typescript
// Nested shape inside POST /users/me/cv response
export const CVExperienceSchema = z.object({
  company: z.string(),
  role: z.string(),
  dates: z.string().nullable().optional(),
  start_date: z.string().nullable().optional(),
  end_date: z.string().nullable().optional(),
  current: z.boolean().optional(),
  description: z.string().nullable().optional(),
  achievements: z.array(z.string()),
  technologies: z.array(z.string()).optional(),
})

export const CVEducationSchema = z.object({
  institution: z.string(),
  degree: z.string(),
  field_of_study: z.string().nullable().optional(),
  graduation_date: z.string().nullable().optional(),
  start_date: z.string().nullable().optional(),
  end_date: z.string().nullable().optional(),
  gpa: z.number().nullable().optional(),
  honors: z.array(z.string()).optional(),
  dates: z.string().nullable().optional(),
})

export const CVCertificationSchema = z.object({
  name: z.string(),
  issuer: z.string().nullable().optional(),
  issuing_organization: z.string().nullable().optional(),
  date: z.string().nullable().optional(),
  issue_date: z.string().nullable().optional(),
  expiry_date: z.string().nullable().optional(),
  credential_id: z.string().nullable().optional(),
})

export const UserCVSchema = z.object({
  cv_id: z.string(),
  user_id: z.string(),
  full_name: z.string(),
  language: z.string().optional(),
  contact_info: z.object({
    name: z.string().optional(),
    phone: z.string().nullable().optional(),
    email: z.string().nullable().optional(),
    location: z.string().nullable().optional(),
    linkedin: z.string().nullable().optional(),
  }).optional(),
  email: z.string().nullable().optional(),
  phone: z.string().nullable().optional(),
  location: z.string().nullable().optional(),
  linkedin: z.string().nullable().optional(),
  experience: z.array(CVExperienceSchema),
  education: z.array(CVEducationSchema),
  certifications: z.array(CVCertificationSchema).optional(),
  skills: z.array(z.string()),
  top_achievements: z.array(z.string()).optional(),
  professional_summary: z.string().optional(),
  languages: z.array(z.string()).optional(),
  created_at: z.string().nullable().optional(),
  updated_at: z.string().nullable().optional(),
  is_parsed: z.boolean().optional(),
  source_file_key: z.string().nullable().optional(),
})
export type UserCV = z.infer<typeof UserCVSchema>

// POST /users/me/cv → 201
// ⚠ Response has TWO shapes: full user_cv object AND simplified parsed_data
export const CVUploadResponseSchema = z.object({
  success: z.boolean(),
  user_cv: UserCVSchema.nullable().optional(),
  language_detected: z.string().nullable().optional(),
  parse_time_ms: z.number().optional(),
  error: z.string().nullable().optional(),
  cv_id: z.string(),
  status: z.literal('parsed'),
  parsed_data: z.object({          // simplified view for quick display
    name: z.string(),
    title: z.string(),             // first experience role
    experience: z.array(z.object({
      company: z.string(),
      role: z.string(),
      duration: z.string(),        // ← field is "duration" not "dates" here
      achievements: z.array(z.string()),
    })),
    skills: z.array(z.string()),
    education: z.array(z.object({
      degree: z.string(),
      institution: z.string(),
      year: z.string(),            // may be empty string
    })),
  }),
})
export type CVUploadResponse = z.infer<typeof CVUploadResponseSchema>

// GET /users/me/cv → 200
export const CVListResponseSchema = z.object({
  cvs: z.array(UserCVSchema),
})
```

---

### Job Schemas (`lib/schemas/jobs.ts`)

```typescript
// POST /jobs → 201
// GET /jobs/{jobId} → 200
// ⚠ API returns BOTH "id" and "job_id" (same value); uses "company_name" not "company"
export const JobSchema = z.object({
  id: z.string(),
  job_id: z.string(),              // same as id
  user_id: z.string(),
  title: z.string(),
  company_name: z.string(),        // ← NOT "company"
  description: z.string(),
  status: z.enum(['active', 'archived']),
  created_at: z.string(),
  url: z.string().nullable().optional(),
  requirements: z.array(z.string()),
})
export type Job = z.infer<typeof JobSchema>

// GET /jobs → 200
export const JobListResponseSchema = z.object({
  jobs: z.array(JobSchema),
})
```

---

### Company Research Schema (`lib/schemas/company-research.ts`)

```typescript
// GET /company-research/{jobId} → 200
export const CompanyResearchSchema = z.object({
  company_research_id: z.string(),
  company_name: z.string(),
  mission: z.string().optional(),
  values: z.array(z.string()).optional(),
  recent_news: z.array(z.object({
    title: z.string(),
    date: z.string(),
  })).optional(),
  culture: z.string().optional(),
  products: z.array(z.string()).optional(),
  funding_status: z.string().optional(),
  size_range: z.string().optional(),
  industry: z.string().optional(),
})
export type CompanyResearch = z.infer<typeof CompanyResearchSchema>
```

---

### Gap Analysis Schemas (`lib/schemas/gap.ts`)

```typescript
// ⚠ Each question has BOTH "id"/"question_id" AND "text"/"question" (duplicate fields)
// ⚠ "destination" uses space-separated strings like "CV IMPACT" or "INTERVIEW/MVP ONLY"
export const GapQuestionSchema = z.object({
  id: z.string(),                       // e.g. "Q001"
  question_id: z.string(),              // same as id
  text: z.string(),
  question: z.string(),                 // same as text
  impact: z.enum(['HIGH', 'MEDIUM', 'LOW']),
  probability: z.enum(['HIGH', 'MEDIUM', 'LOW']),
  gap_score: z.number(),                // 0.0–1.0
  tags: z.array(z.string()),            // e.g. ["[CV IMPACT]"]
  destination: z.string(),              // "CV IMPACT" | "INTERVIEW/MVP ONLY"
  requirement: z.string(),
  strategic_intent: z.string(),
  evidence_gap: z.string(),
  priority: z.enum(['CRITICAL', 'IMPORTANT', 'OPTIONAL']),
})
export type GapQuestion = z.infer<typeof GapQuestionSchema>

// POST /jobs/{jobId}/gap-questions → 200
// GET  /jobs/{jobId}/gap-questions → 200
export const GapQuestionsResponseSchema = z.object({
  job_id: z.string(),
  cv_id: z.string(),
  questions: z.array(GapQuestionSchema),
  missing_qualifications: z.array(z.object({
    skill: z.string(),
    priority: z.string(),
  })).optional(),
})

// POST /jobs/{jobId}/gap-responses → 200
// ⚠ Does NOT return impact statements; just confirms save
export const GapResponsesSubmitSchema = z.object({
  status: z.literal('saved'),
  job_id: z.string(),
  responses_saved: z.number(),
})
```

---

### Artifact Schemas (`lib/schemas/artifacts.ts`)

```typescript
// ── VPR ──────────────────────────────────────────────────────────────────────
// POST /vpr/generate → 202
// ⚠ Returns "request_id" AND "job_id" (same value); also has "webhook_url"
export const VPRGenerateResponseSchema = z.object({
  request_id: z.string(),
  job_id: z.string(),                   // same as request_id — use this for polling
  status: z.literal('processing'),
  estimated_time_seconds: z.number(),   // typically 120
  webhook_url: z.string().optional(),
})

// GET /vpr/{id}/status → 200 (pending/processing)
export const VPRStatusPendingSchema = z.object({
  id: z.string(),
  job_id: z.string(),
  status: z.enum(['pending', 'processing']),
  created_at: z.string(),
  started_at: z.string().optional(),    // added once processing begins
})

// GET /vpr/{id}/status → 200 (completed)
export const VPRStatusCompletedSchema = z.object({
  id: z.string(),
  job_id: z.string(),
  status: z.literal('completed'),
  result: z.object({
    uvp: z.string(),
    differentiators: z.array(z.object({
      text: z.string(),
      source: z.string(),               // e.g. "cv"
    })),
    strategic_narrative: z.string(),
    company_job_fit_score: z.number(),  // 0–10
    meta_evaluation: z.object({
      persuasion_score: z.number(),
      completeness_score: z.number(),
    }),
    download_url: z.string(),           // presigned S3 URL (expires ~1h)
  }),
  created_at: z.string(),
  completed_at: z.string(),
})

export const VPRStatusSchema = z.discriminatedUnion('status', [
  VPRStatusPendingSchema.extend({ status: z.enum(['pending', 'processing']) }),
  VPRStatusCompletedSchema,
  z.object({ id: z.string(), status: z.literal('failed') }),
])

// GET /vprs → 200
export const VPRListResponseSchema = z.object({
  vprs: z.array(z.object({
    id: z.string(),
    job_title: z.string(),
    company_name: z.string(),
    created_at: z.string(),
  })),
})

// ── CV TAILORING ──────────────────────────────────────────────────────────────
// POST /cv-tailoring/generate → 202
// ⚠ Only "request_id" here — no "artifact_id" field (unlike cover letter/interview-prep)
export const CVTailoringGenerateResponseSchema = z.object({
  request_id: z.string(),
  status: z.literal('processing'),
  estimated_time_seconds: z.number(),  // typically 30
})

// GET /cv-tailoring/{id}/status → 200 (completed)
export const CVTailoringStatusSchema = z.object({
  id: z.string(),
  status: z.enum(['pending', 'processing', 'completed', 'failed']),
  result: z.object({
    tailored_cv: z.string(),            // full text of tailored CV
    ats_score: z.number(),              // 0–10
    keyword_matches: z.object({
      missing: z.array(z.string()),
      matched: z.array(z.string()),
    }),
    suggestions: z.array(z.string()),
    fvs_validation: z.object({
      is_valid: z.boolean(),
      violations: z.array(z.string()),
    }),
  }).optional(),
})

// GET /cv-tailorings → 200
export const CVTailoringListResponseSchema = z.object({
  tailored_cvs: z.array(z.object({
    id: z.string(),
    status: z.enum(['pending', 'processing', 'completed', 'failed']),
    cv_id: z.string(),
    created_at: z.string(),
    updated_at: z.string(),
  })),
})

// ── COVER LETTER ──────────────────────────────────────────────────────────────
// POST /cover-letter/generate → 202
// ⚠ Returns BOTH "request_id" AND "artifact_id" (same value)
export const CoverLetterGenerateResponseSchema = z.object({
  request_id: z.string(),
  artifact_id: z.string(),             // same as request_id — use either for polling
  status: z.literal('processing'),
  estimated_time_seconds: z.number(),  // typically 60
})

// GET /cover-letter/{id}/status → 200 (processing)
export const CoverLetterStatusProcessingSchema = z.object({
  id: z.string(),
  status: z.enum(['pending', 'processing']),
})

// GET /cover-letter/{id}/status → 200 (completed)
export const CoverLetterStatusCompletedSchema = z.object({
  id: z.string(),
  status: z.literal('completed'),
  result: z.object({
    cover_letter: z.string(),          // full prose cover letter text
  }),
})

// GET /cover-letters → 200
export const CoverLetterListResponseSchema = z.object({
  cover_letters: z.array(z.object({
    id: z.string(),
    status: z.enum(['pending', 'processing', 'completed', 'failed']),
    cv_id: z.string().nullable().optional(),
    job_id: z.string().nullable().optional(),
    created_at: z.string(),
    updated_at: z.string(),
  })),
})

// ── INTERVIEW PREP ────────────────────────────────────────────────────────────
// POST /interview-prep/generate → 202
// Same shape as cover letter — returns both "request_id" AND "artifact_id"
export const InterviewPrepGenerateResponseSchema = z.object({
  request_id: z.string(),
  artifact_id: z.string(),
  status: z.literal('processing'),
  estimated_time_seconds: z.number(),
})

// GET /interview-prep/{id}/status → 200 (completed)
export const InterviewPrepStatusSchema = z.object({
  id: z.string(),
  status: z.enum(['pending', 'processing', 'completed', 'failed']),
  result: z.object({
    questions: z.array(z.object({
      id: z.string(),                  // "q1", "q2", etc.
      text: z.string(),
      question_type: z.enum(['behavioral', 'technical', 'situational']),
      suggested_answer: z.object({
        format: z.literal('STAR'),
        situation: z.string(),
        task: z.string(),
        action: z.string(),
        result: z.string(),
      }),
    })),
  }).optional(),
})
```

---

### Schema Usage Pattern

```typescript
// lib/api/jobs.ts — wrap calls with safeParse
import { JobSchema, JobListResponseSchema } from '@/lib/schemas/jobs'

export async function listJobs(): Promise<Job[]> {
  const raw = await apiClient('/jobs')
  const parsed = JobListResponseSchema.safeParse(raw)
  if (!parsed.success) {
    console.warn('[schema drift] GET /jobs:', parsed.error.issues)
    return (raw as any).jobs ?? []
  }
  return parsed.data.jobs
}
```

### Key Schema Gotchas (confirmed from live data)

| Field | Wrong assumption | Actual value |
|---|---|---|
| Job company field | `company` | `company_name` |
| Job ID | only `job_id` | BOTH `id` AND `job_id` (same value) |
| Usage credits | `credits_remaining` | `applications.remaining` |
| VPR polling ID | `artifact_id` | `job_id` (from generate response) |
| Gap question text | only `text` | BOTH `text` AND `question` (duplicates) |
| Gap question ID | only `question_id` | BOTH `id` AND `question_id` (same value) |
| CV tailoring ID field | `artifact_id` | `request_id` only |
| Cover letter/interview-prep | `request_id` only | BOTH `request_id` AND `artifact_id` |
| Gap submit response | returns impact statements | only `{ status: "saved", responses_saved: N }` |

---

## 6. CV Upload Flow

**Important:** There is NO presigned URL. The backend accepts base64-encoded file content directly in the request body (confirmed in `cv_upload_handler.py`).

```
Browser → FileReader.readAsDataURL() → strip "data:..." prefix
       → POST /users/me/cv { cv_content: base64string, file_name: "resume.pdf" }
       → Lambda decodes base64 → s3.put_object() server-side → parse
       → Response: { cv_id, status: 'parsed', parsed_data: {name, title, experience, skills, education} }
```

**Supported formats:** `pdf`, `docx`, `txt`
**Size limit:** 5MB raw (≈ 6.7MB base64 — within API Gateway's 10MB body limit)

```typescript
// lib/api/cv.ts
export async function uploadCV(file: File) {
  // Client-side validation BEFORE network call
  const MAX_SIZE = 5 * 1024 * 1024
  if (file.size > MAX_SIZE) throw new Error('File exceeds 5MB limit')

  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!['pdf', 'docx', 'txt'].includes(ext ?? '')) {
    throw new Error('Only PDF, DOCX, and TXT files are supported')
  }

  const base64 = await fileToBase64(file)

  return apiClient('/users/me/cv', {
    method: 'POST',
    body: JSON.stringify({ cv_content: base64, file_name: file.name }),
  })
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve((reader.result as string).split(',')[1])
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}
```

---

## 7. TanStack Query — Server State

TanStack Query handles all remote data. Client state (modal open, selected tab) stays in React `useState` or Zustand.

**Provider setup:**
```tsx
// app/(dashboard)/layout.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 2, staleTime: 30_000 } }
})

export default function DashboardLayout({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}
```

**Adaptive polling hook (used by all 4 AI features):**
```typescript
// lib/hooks/useJobStatus.ts
export function useJobStatus(jobId: string | null, statusEndpoint: string) {
  return useQuery({
    queryKey: ['job-status', jobId],
    queryFn: () => apiClient<{ status: string; result_url?: string }>(`${statusEndpoint}/${jobId}/status`),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const s = query.state.data?.status
      if (!s || s === 'pending') return 2000          // fast: just submitted
      if (s === 'processing') return 5000              // normal polling
      if (query.state.errorUpdateCount > 2) return 15000  // back off on errors
      return false                                     // completed or failed — stop
    },
    refetchIntervalInBackground: true,
  })
}
```

---

## 8. Client-Side Orchestrator

### Overview

The orchestrator manages the CareerVP 7-stage AI pipeline with a human-in-the-loop pause after gap analysis.

```
POST /jobs                      ← create job (checks trial)
  ↓
poll GET /applications/{id}     ← wait for gap_questions_ready
  ↓
[USER FILLS GAP RESPONSES]      ← auto-save every 30s, CRITICAL required
  ↓
POST /jobs/{jobId}/gap-responses ← pipeline resumes
  ↓
poll 4 independent job_ids      ← VPR + CV + CoverLetter + InterviewPrep
  ↓
artifacts_completed             ← show results
```

**On every page load**, call `GET /applications/{id}` and use the `reload_route` field to navigate:
```typescript
// app/dashboard/jobs/[jobId]/page.tsx
const { data: application } = useQuery({ queryKey: ['application', applicationId], ... })
useEffect(() => {
  if (application?.reload_route) router.replace(`/dashboard/jobs/${jobId}${application.reload_route}`)
}, [application?.reload_route])
```

### Application State Machine

```
BACKEND STATE          FRONTEND ACTION
───────────────────────────────────────────────────────────
created              → Show job form, CV selector
cv_selected          → Show "Start processing" CTA
gap_questions_pending→ Show loading spinner "Analyzing job..."
gap_questions_ready  → Show Q&A form (BLOCK other navigation)
gap_responses_sub.   → Show "Generating your package..." spinner
artifacts_generating → Show 4 artifact progress cards (polling)
artifacts_completed  → Show full results panel
FAILED               → Show error card + retry button
NEEDS_REVIEW         → Show yellow "Under review" badge (wait, don't show failure)
```

### Zustand Orchestrator Store

Persists across page reloads via `localStorage`:

```typescript
// stores/applicationStore.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ApplicationStore {
  applicationId: string | null
  jobId: string | null
  applicationState: string | null
  // Gap Q&A draft — persisted so user can return mid-form
  gapDraft: Record<string, string>
  gapLastSaved: number | null
  // Async job IDs for the 4 parallel artifact generations
  vprJobId: string | null
  cvJobId: string | null
  coverLetterJobId: string | null
  interviewPrepJobId: string | null

  setApplication: (id: string, jobId: string) => void
  setApplicationState: (state: string) => void
  updateGapDraft: (questionId: string, text: string) => void
  setArtifactJobIds: (ids: Partial<Record<'vprJobId' | 'cvJobId' | 'coverLetterJobId' | 'interviewPrepJobId', string>>) => void
  clearSession: () => void
}

export const useApplicationStore = create<ApplicationStore>()(
  persist(
    (set) => ({
      applicationId: null, jobId: null, applicationState: null,
      gapDraft: {}, gapLastSaved: null,
      vprJobId: null, cvJobId: null, coverLetterJobId: null, interviewPrepJobId: null,

      setApplication: (id, jobId) => set({ applicationId: id, jobId }),
      setApplicationState: (state) => set({ applicationState: state }),
      updateGapDraft: (qId, text) =>
        set(s => ({ gapDraft: { ...s.gapDraft, [qId]: text }, gapLastSaved: Date.now() })),
      setArtifactJobIds: (ids) => set(ids),
      clearSession: () => set({
        applicationId: null, jobId: null, gapDraft: {},
        vprJobId: null, cvJobId: null, coverLetterJobId: null, interviewPrepJobId: null,
      }),
    }),
    { name: 'careervp-session' }
  )
)
```

### Gap Questions UX

```typescript
// app/dashboard/jobs/[jobId]/gap-questions/page.tsx
export function GapQuestionsPage() {
  const { gapDraft, updateGapDraft, jobId } = useApplicationStore()
  const { data: application } = useApplication()
  const questions = application?.gap_analysis.questions ?? []

  // Auto-save every 30 seconds
  const { mutate: saveDraft } = useMutation({
    mutationFn: () => apiClient(`/jobs/${jobId}/gap-questions/draft`, {
      method: 'POST',
      body: JSON.stringify({
        responses: Object.entries(gapDraft).map(([id, text]) => ({ question_id: id, response_text: text }))
      })
    })
  })
  useEffect(() => {
    const timer = setInterval(() => { if (Object.keys(gapDraft).length) saveDraft() }, 30_000)
    return () => clearInterval(timer)
  }, [gapDraft])

  // Validate: CRITICAL required, IMPORTANT warned, OPTIONAL skippable
  const critical = questions.filter(q => q.priority === 'CRITICAL')
  const important = questions.filter(q => q.priority === 'IMPORTANT')
  const canSubmit = critical.every(q => gapDraft[q.question_id]?.trim())
  const hasSkippedImportant = important.some(q => !gapDraft[q.question_id]?.trim())

  const { mutate: submit, isPending } = useMutation({
    mutationFn: () => apiClient(`/jobs/${jobId}/gap-responses`, {
      method: 'POST',
      body: JSON.stringify({
        responses: Object.entries(gapDraft).map(([id, text]) => ({ question_id: id, response_text: text }))
      })
    }),
    onSuccess: () => router.push(`/dashboard/jobs/${jobId}/artifacts`)
  })

  return (
    <form onSubmit={(e) => { e.preventDefault(); submit() }}>
      {questions.map(q => (
        <GapQuestionCard key={q.question_id} question={q}
          value={gapDraft[q.question_id] ?? ''}
          onChange={text => updateGapDraft(q.question_id, text)} />
      ))}
      {hasSkippedImportant && (
        <Alert variant="warning">Some important questions are unanswered — your results may be less personalized.</Alert>
      )}
      <Button type="submit" disabled={!canSubmit || isPending}>
        {isPending ? 'Generating your package…' : 'Generate Application Package'}
      </Button>
    </form>
  )
}
```

### Parallel Artifact Polling (Stage 4)

After gap responses submitted, 4 async jobs run simultaneously:

```typescript
// app/dashboard/jobs/[jobId]/artifacts/page.tsx
export function ArtifactsPage() {
  const { vprJobId, cvJobId, coverLetterJobId, interviewPrepJobId } = useApplicationStore()

  const vpr = useJobStatus(vprJobId, '/vpr')
  const cv = useJobStatus(cvJobId, '/cv-tailoring')
  const coverLetter = useJobStatus(coverLetterJobId, '/cover-letter')
  const interviewPrep = useJobStatus(interviewPrepJobId, '/interview-prep')

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <ArtifactCard title="Value Proposition Report" icon="📊" query={vpr} href="./vpr" />
      <ArtifactCard title="Tailored CV" icon="📄" query={cv} href="./cv" />
      <ArtifactCard title="Cover Letter" icon="✉️" query={coverLetter} href="./cover-letter" />
      <ArtifactCard title="Interview Prep" icon="🎯" query={interviewPrep} href="./interview-prep" />
    </div>
  )
}
```

### /jobs vs /applications — The Distinction

These are two separate domain objects:

| Concept | `/jobs` endpoints | `/applications/{id}` endpoint |
|---|---|---|
| What it is | Job posting data | AI workflow session |
| CRUD | POST, GET list, GET by ID | **GET only** |
| State | `status: active/archived` | 7-state machine |
| Contains | title, company, description, url | state + CV ref + gap Q&A + artifact statuses + `reload_route` |
| Created by | User action (POST /jobs) | Implicitly when pipeline starts |
| Frontend use | Data entry / job library | Recovery / navigation source of truth |

**Workflow:** Create Job → start Application (pipeline run) against that Job → Application tracks all state.

---

## 9. Error UX — AI Failure Handling

### Backend Error Codes (confirmed from source)

| Condition | HTTP | Error Value | Source File |
|---|---|---|---|
| Trial expired | 403 | `trial_expired` | `job_handler.py:138` |
| Trial exhausted | 403 | `trial_exhausted` | `job_handler.py:140` |
| LLM rate limited | 429 | `LLM_RATE_LIMITED` | `cv_upload_handler.py:283` |
| LLM timeout | 504 | `LLM_TIMEOUT` | `cv_upload_handler.py:285` |
| Artifact failed | 200 (status field) | `status: 'failed'` | `application_handler.py:85` |
| Quality < 80 | 200 | `status: 'needs_review'` | Architecture docs |
| SQS DLQ (3x) | 200 | `status: 'failed'` | VPR async design |

### UX Response Per Error

| Error | UX | Auto-Retry? |
|---|---|---|
| `trial_expired` | Full-screen upgrade modal, block all actions | No |
| `trial_exhausted` | Persistent banner + upgrade CTA | No |
| Rate limited (429) | Toast "AI is busy, retrying…" → auto-retry with exponential backoff | Yes (automatic) |
| Timeout (504) | "This took longer than expected." + Retry button | Yes (user-initiated) |
| Artifact `failed` | Per-artifact error card with message + "Regenerate" button | Yes (user-initiated) |
| `needs_review` | Yellow "Under Review" badge — do NOT show as failure | No (wait) |
| Network offline | Offline toast, queue retry on reconnect | Yes (automatic) |
| 500 | "Something went wrong" + support link | No |

### Global Error Handler

```typescript
// components/GlobalErrorHandler.tsx
export function GlobalErrorHandler() {
  const queryClient = useQueryClient()

  queryClient.setMutationDefaults(['*'], {
    onError: (error: ApiError) => {
      if (error.isTrialExpired)   openUpgradeModal('trial_expired')
      else if (error.isTrialExhausted) openUpgradeModal('trial_exhausted')
      else if (error.isAuthError) router.push('/login')
      else if (error.isRateLimited) toast.warning('AI rate limit — retrying automatically…')
      else if (error.isTimeout)   toast.error('Request timed out. Try again.')
      else toast.error(error.message)
    },
  })
  return null
}
```

---

## 10. Trial / Quota Enforcement UI

The job creation endpoint (`POST /jobs`) checks trial status and returns 403 on failure. The frontend must gate before and handle on failure.

```typescript
// components/trial/TrialGuard.tsx
// ⚠ Use usage.applications.remaining — NOT usage.credits_remaining (that field doesn't exist)
function TrialGuard({ children }: { children: React.ReactNode }) {
  const { data: usage } = useQuery({
    queryKey: ['usage'],
    queryFn: () => apiClient<Usage>('/users/me/usage'),
  })

  const remaining = usage?.applications?.remaining ?? null

  if (remaining === 0) {
    return (
      <div className="space-y-3">
        <Button disabled className="w-full">Start New Application</Button>
        <UpgradeBanner reason="exhausted" />
      </div>
    )
  }

  return (
    <>
      {remaining === 1 && (
        <Alert variant="warning" className="mb-3">Last free application — upgrade to continue.</Alert>
      )}
      {children}
    </>
  )
}

// components/layout/Header.tsx — persistent credit indicator
function CreditIndicator() {
  const { data: usage } = useQuery({ queryKey: ['usage'], queryFn: () => apiClient<Usage>('/users/me/usage'), staleTime: 60_000 })
  if (!usage) return null
  const remaining = usage.applications.remaining
  const variant = remaining === 0 ? 'destructive' : remaining === 1 ? 'warning' : 'outline'
  return (
    <Badge variant={variant}>
      {remaining} / 3 free applications
    </Badge>
  )
}
```

---

## 11. Styling Strategy — HTML Template Integration

Use this migration path when incorporating an HTML template:

### Recommended Order

```
1. TODAY: Global CSS import (fastest, enables mockup validation)
   app/layout.tsx → import './globals.css' (your template CSS here)
   ⚠ Warning: sticky across routes — avoid page-specific styles globally

2. PER COMPONENT: CSS Modules (scoped, zero collisions)
   Component.module.css → import styles from './Component.module.css'
   Direct translation of your HTML template's class structure

3. NEW COMPONENTS: shadcn/ui (accessible, owned source)
   npx shadcn@latest add button card dialog
   Override via CSS variables → matches your brand instantly

4. PROGRESSIVE: Tailwind migration
   @layer components { .btn-primary { @apply ... } }
   Replace custom classes component by component
```

### Theming (map your brand colors once)

```css
/* globals.css */
:root {
  --primary: 220 90% 56%;        /* your brand blue */
  --primary-foreground: 0 0% 100%;
  --secondary: 210 40% 96%;
  --accent: 262 83% 58%;
  --background: 0 0% 100%;
  --foreground: 222 84% 5%;
  --destructive: 0 72% 51%;
  --border: 214 32% 91%;
  --radius: 0.5rem;
}
```

All shadcn/ui components use these variables — one change updates everything.

---

## 12. Mobile Responsiveness

CareerVP's workflow is used on mobile (gap Q&A on-the-go, reviewing artifacts, downloading files).

### Layout Strategy (mobile-first)

```tsx
// Dashboard: bottom nav on mobile, sidebar on desktop
<div className="flex flex-col md:flex-row min-h-screen">
  <Sidebar className="hidden md:flex md:w-64 flex-col" />
  <main className="flex-1 pb-20 md:pb-0">{children}</main>
  <BottomNav className="md:hidden fixed bottom-0 w-full" />
</div>

// Artifacts: tabs on mobile, grid on desktop
<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
  {artifacts.map(a => <ArtifactCard key={a.type} {...a} />)}
</div>

// CV diff: stacked on mobile, side-by-side on desktop
<div className="flex flex-col md:flex-row gap-4">
  <div className="flex-1"><h3>Original</h3><CVPanel cv={original} /></div>
  <div className="flex-1"><h3>Tailored</h3><CVPanel cv={tailored} /></div>
</div>
```

### Mobile-Specific Decisions

| Feature | Desktop | Mobile |
|---|---|---|
| Gap Q&A layout | All questions, scroll | One question per screen (swipe/next) |
| Artifact tabs | Sidebar | Bottom tab strip (`CV`, `Letter`, `Prep`, `VPR`) |
| Progress indicator | Horizontal stepper | Compact dot indicator |
| CV diff | Side-by-side | Stacked with toggle |
| File upload | Drag-and-drop + click | `<input capture>` for camera |
| File download | Browser download | `target="_blank"` (iOS opens in browser) |

### File Upload (mobile-aware)

```tsx
<input
  type="file"
  accept=".pdf,.docx,.txt"
  className="hidden"
  onChange={handleFileChange}
/>
```

For iOS: use `target="_blank"` on presigned download URLs — Safari opens instead of downloads.

---

## 13. CORS Hardening

### Current State (confirmed from source)

- **Lambda-level CORS** (`cors_utils.py`): Already allowlist-based via `ALLOWED_ORIGINS` env var. Logic is correct — only needs the env var set to the actual domain.
- **API Gateway gateway responses** (`api_construct.py`): Still returns `'*'` for 4xx/5xx errors that bypass Lambda.

### Two Changes Required

**1. Set `ALLOWED_ORIGINS` env var on all Lambda functions:**
```python
# infra/careervp/api_construct.py — add to Lambda environment
environment={
  'ALLOWED_ORIGINS': 'https://app.careervp.com,https://careervp.com',
  ...
}
```

**2. Fix CDK gateway responses** (currently hardcoded to `'*'`):
```python
# In _add_gateway_error_responses() — replace '*' with actual domain
'gatewayresponse.header.Access-Control-Allow-Origin': f"'https://app.careervp.com'"
```

Effort: **2 hours**. Must complete before production launch.

---

## 14. Hosting Decision

### Decision Framework

```
Does the app use SSR / Server Components?
  YES (App Router default) → S3 alone won't work
    ├── MVP / prototype → Amplify Hosting  ← RECOMMENDED NOW
    └── Production with WAF / fine-grained CloudFront → CloudFront + ECS Fargate
  NO (static export) → CloudFront + S3  (cheapest at scale)
```

### MVP: Amplify Hosting

- Git push → auto-deploy (branch-based: `dev`, `staging`, `main`)
- Preview URL per PR
- SSR supported (managed Lambda compute + CloudFront)
- Setup: ~30 minutes

**Amplify Hosting limitations** (plan for V2 migration):
- Cannot tune CloudFront cache behaviors
- Cannot add Lambda@Edge or WAF rules
- Cannot control underlying compute memory/timeout
- Limited IaC control (fights CDK abstractions)

### V2: CloudFront + ECS Fargate

Migrate when you need: custom WAF rules, fine-grained caching, full CDK ownership, or compute control.

---

## 15. Feature Scope Map

### P0 — Build First (Sprint 1–8)

| Feature ID | Feature | Frontend Components |
|---|---|---|
| F-AUTH-001/002/003 | Auth (register, login, password reset) | LoginForm, RegisterForm, PasswordResetForm |
| F-CV-001/002/003 | CV upload, parse, manage | CVUpload, CVCard, CVEditForm |
| F-JOB-001 | Job posting input + validation popup | JobCreateForm, RequirementsConfirmModal |
| F-JOB-002 | Company research (cached, background) | CompanyResearchCard (display only) |
| F-JOB-003/004 | Gap analysis Q&A | GapQuestionCard, GapResponseForm, auto-save |
| F-JOB-005 | VPR generation + display | VPRViewer, VPRDownloadButton |
| F-JOB-006 | CV tailoring + edit | CVDiffView, CVEditForm, regenerate |
| F-JOB-007 | Cover letter generation + edit | CoverLetterViewer, EditModal |
| F-JOB-008 | Interview prep generation | InterviewPrepViewer, STARQuestionCard |
| F-REVIEW-001/002 | Artifact review + regenerate | ArtifactCard, RegenerateModal, VersionHistory |
| F-EXPORT-001/002 | DOCX + PDF download | DownloadButton (presigned S3 URL) |
| F-SUBSCRIPTION-001/002 | Stripe Checkout + subscription management | CheckoutButton, BillingPortalButton, SubscriptionBadge |
| F-BILLING-001 | Trial → paid upgrade flow | UpgradeModal → Stripe Checkout → success page |
| F-BILLING-002 | Billing portal (manage/cancel) | BillingPortalButton → Stripe Customer Portal |
| F-BILLING-003 | Subscription gating (post-trial) | useSubscription() hook, TrialGuard upgrade |
| F-NOTIFY-001 | Email notifications (server-side) | Frontend: show completion state on poll |

### P1 — Post-Launch

| Feature ID | Feature | Frontend Notes |
|---|---|---|
| F-LANG-001 | Multi-language (EN + HE) | Detect mismatch → show both artifact variants; RTL support for Hebrew |
| F-ATS-001 | ATS compatibility checker | ATS score badge (0–100, color-coded), issue list |
| F-ANALYTICS-001 | User analytics dashboard | Charts (Recharts/Nivo), trend lines |
| F-EDIT-001 | Collaborative editing | Shareable links, permission modal (V1.1) |

### P2 / V2 — Future

- Google Drive integration
- LinkedIn import
- Job tracking board
- French language support

---

## 16. API Domain Model

Complete endpoint map with frontend usage:

| Endpoint | Method | Auth | Frontend Use |
|---|---|---|---|
| `/auth/login` | POST | No | Login form |
| `/auth/register` | POST | No | Registration form |
| `/auth/refresh` | POST | No | Managed by Amplify automatically |
| `/users/me` | GET/PUT | Yes | Profile page |
| `/users/me/cv` | GET/POST | Yes | CV management; POST = base64 upload |
| `/users/me/usage` | GET | Yes | CreditIndicator, TrialGuard |
| `/users/me/trial/reset` | POST | Yes | Dev/testing only |
| `/jobs` | GET/POST | Yes | Job list; POST checks trial |
| `/jobs/{jobId}` | GET | Yes | Job detail page |
| `/jobs/{jobId}/gap-questions` | GET/POST | Yes | Gap Q&A fetch and generate |
| `/jobs/{jobId}/gap-responses` | POST | Yes | Submit answers → resume pipeline |
| `/applications/{application_id}` | GET | Yes | **Recovery endpoint** — `reload_route` drives navigation |
| `/vpr/generate` | POST | Yes | Trigger VPR generation → returns job_id |
| `/vpr/{vprId}/status` | GET | Yes | Poll every 5s → `result_url` on complete |
| `/vprs` | GET | Yes | VPR history list |
| `/cv-tailoring/generate` | POST | Yes | Trigger CV tailoring |
| `/cv-tailoring/{id}/status` | GET | Yes | Poll for completion |
| `/cv-tailoring/{id}` | DELETE | Yes | Remove a tailored CV |
| `/cv-tailorings` | GET | Yes | CV tailoring history |
| `/cover-letter/generate` | POST | Yes | Trigger cover letter |
| `/cover-letter/{id}/status` | GET | Yes | Poll for completion |
| `/cover-letters` | GET | Yes | Cover letter history |
| `/interview-prep/generate` | POST | Yes | Trigger interview prep |
| `/interview-prep/{id}/status` | GET | Yes | Poll for completion |
| `/interview-preps` | GET | Yes | Interview prep history |
| `/company-research/fetch` | POST | Yes | Trigger research (background) |
| `/company-research/{jobId}` | GET | Yes | Fetch cached research |
| `/knowledge-base` | GET | Yes | Cross-application learnings |

---

## 17. Open Questions

Questions marked ✅ are resolved from `live-test-results34.log`.

| # | Question | Status | Answer / Resolution |
|---|---|---|---|
| 1 | What does `GET /applications/{id}` return as `artifact_statuses` before any artifacts exist? | ⏳ Open | First integration test needed |
| 2 | How are artifact `job_id`s surfaced to the client? Via application state or separate webhook? | ✅ Resolved | Each generate endpoint returns the ID directly: VPR → `job_id`, CV tailoring → `request_id`, cover letter/interview-prep → both `request_id` and `artifact_id`. Store in Zustand on the generate call. |
| 3 | Does `POST /jobs/{jobId}/gap-responses` return a `job_id` for VPR or does VPR poll against the application? | ✅ Resolved | Gap-responses returns only `{ status: "saved", job_id, responses_saved }`. Each artifact must be triggered separately with its own `POST /vpr/generate`, etc. |
| 4 | What is the exact request body for `POST /jobs`? | ✅ Resolved | `{ title, company_name, description, url?, requirements[] }` — field is `company_name` not `company`. |
| 5 | Is there a draft save endpoint for gap responses? | ✅ Resolved | No draft endpoint exists. Auto-save should go to Zustand persist only; full submit via `POST /jobs/{jobId}/gap-responses`. |
| 6 | What Cognito App Client ID should the frontend use? | ✅ Resolved | `7blipbarsisbctqh6hlsj46sqa` (from token claims in log). Set as `NEXT_PUBLIC_COGNITO_CLIENT_ID`. |
| 7 | For multi-language (F-LANG-001): separate artifact IDs for EN/HE or single with language field? | ⏳ Open | P1 — not yet observable from log |
| 8 | Is `POST /gap-analysis/questions` (legacy route) still active? | ✅ Resolved | Only `/jobs/{jobId}/gap-questions` (canonical) is active. Legacy route was an alias, now removed per RECOVERY_007. |
| 9 | What fields trigger VPR polling? | ✅ Resolved | `POST /vpr/generate` → use returned `job_id` for `GET /vpr/{job_id}/status`. The status response also contains `job_id`. |
| 10 | What does a `failed` cover-letter look like in the list? | ✅ Resolved | `{ id, status: "failed", cv_id: null, job_id, created_at, updated_at }` — `cv_id` is null when failed. |

---

## 18. Billing & Stripe Integration

**Architecture decision:** Use hosted Stripe Checkout and Customer Portal. No client-side card handling — zero PCI scope on the frontend.

### Subscription State Machine

```
trialing  ─── upgrade ──────────────────────────► active
   │                                                  │
   │ trial ends + no payment                   invoice.payment_failed (3x)
   ▼                                                  ▼
expired ◄── customer.subscription.deleted ──── past_due
```

States stored in DynamoDB `subscriptions` table, mirrored to `UsageSchema` response.

### Zod Schemas (`lib/schemas/billing.ts`)

```typescript
import { z } from 'zod'

export const SubscriptionStatusSchema = z.enum([
  'trialing',
  'active',
  'past_due',
  'canceled',
  'incomplete',
])

export const SubscriptionSchema = z.object({
  subscription_id: z.string(),             // Stripe subscription ID (sub_xxx)
  customer_id: z.string(),                 // Stripe customer ID (cus_xxx)
  status: SubscriptionStatusSchema,
  plan: z.enum(['trial', 'monthly', 'annual']),
  current_period_end: z.string(),          // ISO 8601 — when billing cycle ends
  cancel_at_period_end: z.boolean(),
  trial_end: z.string().nullable().optional(),
})
export type Subscription = z.infer<typeof SubscriptionSchema>

// POST /billing/checkout → 200
export const CheckoutSessionSchema = z.object({
  checkout_url: z.string().url(),          // Redirect user here
})

// POST /billing/portal → 200
export const PortalSessionSchema = z.object({
  portal_url: z.string().url(),            // Redirect user here
})

// GET /users/me/subscription → 200
export const UserSubscriptionResponseSchema = z.object({
  subscription: SubscriptionSchema.nullable(),
  has_active_subscription: z.boolean(),
})
```

### `useSubscription` Hook (`lib/hooks/useSubscription.ts`)

```typescript
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api-client'
import { UserSubscriptionResponseSchema, type Subscription } from '@/lib/schemas/billing'

export function useSubscription() {
  const query = useQuery({
    queryKey: ['subscription'],
    queryFn: async () => {
      const raw = await apiClient('/users/me/subscription')
      return UserSubscriptionResponseSchema.parse(raw)
    },
    staleTime: 60_000,
  })

  const sub = query.data?.subscription
  const status = sub?.status ?? null

  return {
    ...query,
    subscription: sub,
    isActive:    status === 'active',
    isTrialing:  status === 'trialing',
    isPastDue:   status === 'past_due',
    isCanceled:  status === 'canceled',
    canUseApp:   status === 'trialing' || status === 'active',
    cancelAtPeriodEnd: sub?.cancel_at_period_end ?? false,
  }
}
```

### Billing API Functions (`lib/api/billing.ts`)

```typescript
import { apiClient } from '@/lib/api-client'

// Triggers Stripe Checkout for the selected plan.
// Backend creates/retrieves Stripe customer, creates checkout session,
// returns the hosted URL. Frontend simply redirects.
export async function createCheckoutSession(plan: 'monthly' | 'annual') {
  const data = await apiClient<{ checkout_url: string }>('/billing/checkout', {
    method: 'POST',
    body: JSON.stringify({
      plan,
      success_url: `${window.location.origin}/billing/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${window.location.origin}/settings/billing`,
    }),
  })
  return data.checkout_url
}

// Opens Stripe Customer Portal — user can update card, view invoices, cancel.
export async function createPortalSession() {
  const data = await apiClient<{ portal_url: string }>('/billing/portal', {
    method: 'POST',
    body: JSON.stringify({
      return_url: `${window.location.origin}/settings/billing`,
    }),
  })
  return data.portal_url
}
```

### Components

#### `CheckoutButton` (`components/billing/CheckoutButton.tsx`)

```tsx
'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { createCheckoutSession } from '@/lib/api/billing'

export function CheckoutButton({ plan }: { plan: 'monthly' | 'annual' }) {
  const [loading, setLoading] = useState(false)

  async function handleClick() {
    setLoading(true)
    try {
      const url = await createCheckoutSession(plan)
      window.location.href = url   // full redirect to Stripe Checkout
    } catch {
      setLoading(false)
    }
  }

  return (
    <Button onClick={handleClick} disabled={loading} className="w-full">
      {loading ? 'Redirecting to checkout…' : `Upgrade — ${plan === 'annual' ? 'Annual' : 'Monthly'}`}
    </Button>
  )
}
```

#### `BillingPortalButton` (`components/billing/BillingPortalButton.tsx`)

```tsx
'use client'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { createPortalSession } from '@/lib/api/billing'

export function BillingPortalButton() {
  const [loading, setLoading] = useState(false)

  async function handleClick() {
    setLoading(true)
    try {
      const url = await createPortalSession()
      window.location.href = url
    } catch {
      setLoading(false)
    }
  }

  return (
    <Button variant="outline" onClick={handleClick} disabled={loading}>
      {loading ? 'Opening portal…' : 'Manage Subscription'}
    </Button>
  )
}
```

#### `UpgradeModal` (`components/trial/UpgradeModal.tsx`)

Triggered when `useSubscription().canUseApp === false` or on 403 `trial_expired`:

```tsx
export function UpgradeModal({ open, reason }: { open: boolean; reason: 'trial_expired' | 'trial_exhausted' }) {
  return (
    <Dialog open={open}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {reason === 'trial_expired' ? 'Your trial has ended' : 'You\'ve used all free applications'}
          </DialogTitle>
        </DialogHeader>
        <p className="text-muted-foreground text-sm">
          Upgrade to continue generating unlimited application packages.
        </p>
        <div className="grid grid-cols-2 gap-3 mt-4">
          <PlanCard plan="monthly" price="$19/mo" />
          <PlanCard plan="annual" price="$149/yr" badge="Best value" />
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

### Feature Gating Strategy

| Subscription State | `canUseApp` | UI Behavior |
|---|---|---|
| `trialing` | ✅ | Show trial countdown badge |
| `active` | ✅ | No restrictions |
| `past_due` | ❌ | Banner: "Payment failed — update card" + BillingPortalButton |
| `canceled` | ❌ | UpgradeModal — re-subscribe to continue |
| `null` (no record) | ❌ | Same as canceled — force upgrade |

### Success Page (`app/(dashboard)/billing/success/page.tsx`)

After Stripe Checkout completes, Stripe redirects to `/billing/success?session_id=cs_xxx`.
The backend webhook (`checkout.session.completed`) fires simultaneously and updates the subscription record.

```tsx
'use client'
import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'

export default function BillingSuccessPage() {
  const queryClient = useQueryClient()
  const router = useRouter()

  useEffect(() => {
    // Invalidate subscription + usage so fresh state loads
    queryClient.invalidateQueries({ queryKey: ['subscription'] })
    queryClient.invalidateQueries({ queryKey: ['usage'] })
    // Redirect to dashboard after 3s
    const t = setTimeout(() => router.replace('/dashboard'), 3000)
    return () => clearTimeout(t)
  }, [])

  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4">
      <h1 className="text-2xl font-bold">You're all set!</h1>
      <p className="text-muted-foreground">Your subscription is now active. Redirecting…</p>
    </div>
  )
}
```

### Webhook Note (Backend Concern)

Stripe webhooks hit the backend directly. Frontend only needs to:

1. Redirect to Checkout URL
2. On success page, invalidate `subscription` and `usage` queries
3. Poll `GET /users/me/subscription` if needed (webhook usually faster than user return)

No frontend webhook handling required.

---

## 19. Admin Portal

**Decision:** Admin portal is a separate Next.js route group `(admin)` protected by Cognito group membership (`"Admins"`). It uses the same API client and JWT, but the backend validates the `cognito:groups` claim in the token for admin endpoints.

### Auth Guard — Admin Routes

```typescript
// middleware.ts — extend to protect /admin routes
export async function middleware(request: NextRequest) {
  const response = NextResponse.next()

  const { isAuthenticated, groups } = await runWithAmplifyServerContext({
    nextServerContext: { request, response },
    operation: async (contextSpec) => {
      try {
        const session = await fetchAuthSession(contextSpec)
        const payload = session.tokens?.idToken?.payload
        const groups = (payload?.['cognito:groups'] as string[]) ?? []
        return { isAuthenticated: !!session.tokens, groups }
      } catch { return { isAuthenticated: false, groups: [] } }
    },
  })

  const isAdmin = groups.includes('Admins')
  const pathname = request.nextUrl.pathname

  if (pathname.startsWith('/admin') && !isAdmin) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  if (pathname.startsWith('/dashboard') && !isAuthenticated) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
}

export const config = { matcher: ['/dashboard/:path*', '/admin/:path*'] }
```

### Admin Zod Schemas (`lib/schemas/admin.ts`)

```typescript
import { z } from 'zod'
import { SubscriptionStatusSchema } from './billing'

// GET /admin/users → 200
export const AdminUserSchema = z.object({
  user_id: z.string(),
  email: z.string().email(),
  name: z.string(),
  created_at: z.string(),
  subscription_status: SubscriptionStatusSchema.nullable(),
  applications_used: z.number(),
  applications_remaining: z.number(),
  trial_active: z.boolean(),
  last_active_at: z.string().nullable().optional(),
})
export type AdminUser = z.infer<typeof AdminUserSchema>

export const AdminUserListSchema = z.object({
  users: z.array(AdminUserSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
})

// GET /admin/metrics → 200
export const AdminMetricsSchema = z.object({
  total_users: z.number(),
  active_subscriptions: z.number(),
  trialing_users: z.number(),
  churned_users: z.number(),
  trial_to_paid_rate: z.number(),          // 0.0–1.0
  mrr: z.number(),                         // monthly recurring revenue in cents
  applications_created_today: z.number(),
  applications_created_this_week: z.number(),
})

// GET /admin/users/{userId} → 200
export const AdminUserDetailSchema = AdminUserSchema.extend({
  cv_count: z.number(),
  jobs: z.array(z.object({
    job_id: z.string(),
    title: z.string(),
    company_name: z.string(),
    status: z.enum(['active', 'archived']),
    created_at: z.string(),
    application_state: z.string().nullable().optional(),
  })),
  subscription: z.object({
    subscription_id: z.string().nullable(),
    customer_id: z.string().nullable(),
    status: SubscriptionStatusSchema.nullable(),
    plan: z.string().nullable(),
    current_period_end: z.string().nullable(),
  }).nullable(),
})
```

### Admin API Functions (`lib/api/admin.ts`)

```typescript
import { apiClient } from '@/lib/api-client'
import type { AdminUser, AdminUserDetail } from '@/lib/schemas/admin'

export async function listAdminUsers(params?: {
  page?: number
  page_size?: number
  search?: string
  subscription_status?: string
}) {
  const qs = new URLSearchParams()
  if (params?.page) qs.set('page', String(params.page))
  if (params?.page_size) qs.set('page_size', String(params.page_size))
  if (params?.search) qs.set('search', params.search)
  if (params?.subscription_status) qs.set('subscription_status', params.subscription_status)
  return apiClient<{ users: AdminUser[]; total: number }>(`/admin/users?${qs}`)
}

export async function getAdminUser(userId: string) {
  return apiClient<AdminUserDetail>(`/admin/users/${userId}`)
}

export async function getAdminMetrics() {
  return apiClient('/admin/metrics')
}

// Admin action: manually extend trial
export async function extendUserTrial(userId: string, days: number) {
  return apiClient(`/admin/users/${userId}/trial`, {
    method: 'POST',
    body: JSON.stringify({ extend_days: days }),
  })
}

// Admin action: cancel subscription immediately
export async function cancelUserSubscription(userId: string) {
  return apiClient(`/admin/users/${userId}/subscription/cancel`, {
    method: 'POST',
  })
}
```

### Admin Pages — Component Stack

| Page | URL | Key Components | Data Source |
|---|---|---|---|
| Dashboard | `/admin` | KPI cards, conversion chart, daily activity chart | `GET /admin/metrics` |
| Users | `/admin/users` | TanStack Table, search input, status filter, export CSV | `GET /admin/users?page=N` |
| User Detail | `/admin/users/[userId]` | Profile card, usage meter, jobs accordion, subscription status | `GET /admin/users/{userId}` |
| Subscriptions | `/admin/subscriptions` | Subscription status table, MRR indicator | `GET /admin/subscriptions` |
| Analytics | `/admin/analytics` | Recharts: cohort retention, funnel, revenue trend | `GET /admin/analytics` |

### Admin Dashboard KPI Cards (`app/(admin)/admin/page.tsx`)

```tsx
export default async function AdminDashboard() {
  // Server component — fetch directly (token from server context)
  const metrics = await getAdminMetrics()

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <KPICard label="Total Users" value={metrics.total_users} />
      <KPICard label="Active Subscriptions" value={metrics.active_subscriptions} />
      <KPICard label="Trial → Paid" value={`${(metrics.trial_to_paid_rate * 100).toFixed(1)}%`} />
      <KPICard label="MRR" value={`$${(metrics.mrr / 100).toFixed(0)}`} />
    </div>
  )
}
```

### Admin User Table (`app/(admin)/admin/users/page.tsx`)

Uses **TanStack Table v8** for sorting, filtering, and pagination:

```tsx
'use client'
import { useQuery } from '@tanstack/react-query'
import { useReactTable, getCoreRowModel, flexRender } from '@tanstack/react-table'
import { listAdminUsers } from '@/lib/api/admin'
import { AdminUser } from '@/lib/schemas/admin'

const columns = [
  { accessorKey: 'email', header: 'Email' },
  { accessorKey: 'name', header: 'Name' },
  { accessorKey: 'subscription_status', header: 'Status',
    cell: ({ getValue }) => <SubscriptionBadge status={getValue()} /> },
  { accessorKey: 'applications_used', header: 'Apps Used' },
  { accessorKey: 'last_active_at', header: 'Last Active',
    cell: ({ getValue }) => getValue() ? new Date(getValue()).toLocaleDateString() : '—' },
  { id: 'actions', cell: ({ row }) => <AdminUserActions user={row.original} /> },
]

export default function AdminUsersPage() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')

  const { data } = useQuery({
    queryKey: ['admin-users', page, search],
    queryFn: () => listAdminUsers({ page, page_size: 20, search }),
  })

  const table = useReactTable({
    data: data?.users ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualPagination: true,
    pageCount: Math.ceil((data?.total ?? 0) / 20),
  })

  return (
    <div className="space-y-4">
      <Input placeholder="Search by email or name…" value={search} onChange={e => setSearch(e.target.value)} />
      <Table>
        <TableHeader>{/* render headers */}</TableHeader>
        <TableBody>{/* render rows */}</TableBody>
      </Table>
      <Pagination page={page} total={data?.total ?? 0} pageSize={20} onChange={setPage} />
    </div>
  )
}
```

### Library Decisions for Admin

| Need | Library | Rationale |
|---|---|---|
| Data table | `@tanstack/react-table` v8 | Already using TanStack ecosystem; server-side pagination |
| Charts | `recharts` | Lightweight, composable, works with shadcn/ui themes |
| Date formatting | `date-fns` | Consistent with backend ISO 8601 strings |
| CSV export | `papaparse` | Client-side CSV from admin user table |

### Admin-Only Env Var

```bash
# Not NEXT_PUBLIC — server-only, never sent to browser
ADMIN_COGNITO_GROUP=Admins
```

The middleware reads `cognito:groups` from the Cognito ID token claim — no extra backend call needed for access control.
