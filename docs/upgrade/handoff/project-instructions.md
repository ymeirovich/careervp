# CareerVP UI Upgrade — Project Instructions

You are a UI spec engineer working on a full-app visual redesign of CareerVP, a Next.js 16 + TypeScript + Tailwind CSS v4 SaaS application.

## Your Role

Analyze design screenshots (modified versions of the current UI), map visual changes to existing components, produce functional specs, and design test stubs. You do NOT implement code — you produce specs and test stubs that a developer will implement.

## Stack

- **Framework:** Next.js 16, TypeScript strict mode, App Router
- **Styling:** Tailwind CSS v4, design tokens in `styles/tokens.css`
- **State:** Zustand + React Query (TanStack)
- **Testing:** Vitest + Testing Library (unit/UI), Jest (integration), Playwright (e2e)
- **Icons:** Lucide React
- **Auth:** AWS Cognito

## Non-Negotiable Constraints

1. **Backend is frozen.** No new API endpoints. Every UI change must use existing API responses.
2. **Token-first.** Changes to `styles/tokens.css` cascade to every component — always identify token changes before component changes.
3. **No silent completion.** Every spec requires a Verification Contract table and Traceability Matrix.
4. **Specs drive tests.** No test without a spec AC mapping to it.
5. **Directive-first output.** All prompts and outputs follow: OUTPUT CONTRACT → TASK → CONSTRAINTS → CONTEXT.

## Current App Structure

### Routes (Next.js App Router)
```
app/
├── (auth)/
│   ├── login/page.tsx
│   ├── register/page.tsx
│   ├── confirm-signup/page.tsx
│   ├── forgot-password/page.tsx
│   └── reset-password/page.tsx
├── dashboard/
│   ├── page.tsx
│   └── jobs/[jobId]/page.tsx
├── applications/
│   ├── page.tsx                    ← REDIRECT ONLY (no current UI)
│   └── [id]/
│       ├── page.tsx                ← Application Hub
│       ├── vpr/page.tsx
│       ├── cover-letter/page.tsx
│       ├── cv-tailored/page.tsx
│       ├── gap-analysis/page.tsx
│       ├── interview-prep/page.tsx
│       └── company-research/page.tsx
├── cv-center/page.tsx
├── billing/page.tsx
└── settings/page.tsx
```

### Current Sidebar Navigation (AppSidebar.tsx)
```
/dashboard    → Dashboard
/applications → Applications  (currently redirect, no UI)
/cv-center    → CV Center
/billing      → Billing
/settings     → Settings
```

### NEW Routes in Redesign (require new page files)
These pages appear in screenshots but have NO current page file. Backend endpoints already exist.

| Frontend Route | Page File (to create) | Backend Endpoint | Sidebar |
|---|---|---|---|
| `/applications` | `app/applications/page.tsx` (replace redirect) | `GET /jobs` | existing item |
| `/cover-letters` | `app/cover-letters/page.tsx` | `GET /cover-letters` | NEW item |
| `/tailored-cvs` | `app/tailored-cvs/page.tsx` | `GET /cv-tailorings` | NEW item |

All three new frontend routes consume **existing API endpoints** — no backend changes required.

### Shared Component Cascade Risk
| Component | File | Routes Affected | Test Coverage |
|-----------|------|----------------|---------------|
| ErrorBoundary | components/ErrorBoundary/ErrorBoundary.tsx | 10 | **none** |
| Spinner | components/ui/Spinner.tsx | 9 | **none** |
| Button | components/ui/Button.tsx | 6 | **none** |
| ExportDropdown | components/ExportDropdown/ExportDropdown.tsx | 4 | has unit test |
| ModuleCard | components/ModuleCard/ModuleCard.tsx | 2 | has unit tests |

**Upgrade order:** tokens.css → ErrorBoundary → Spinner → Button → ExportDropdown → layout → feature pages

### Module Pages API Pattern
All 6 module pages (vpr, cover-letter, cv-tailored, gap-analysis, interview-prep, company-research) call `api.*` directly in `useEffect` — **not** through React Query hooks. State is managed locally per page.

## API Route Map (from Swagger)

Source: `careervp-core-api-dev-prod-swagger-apigateway-2026-05-16.json`

| Frontend Route | API Endpoints Used |
|---|---|
| `/dashboard` | `GET /jobs`, `POST /jobs`, `GET /users/me/usage` |
| `/applications` | `GET /jobs` (same data — applications list IS jobs list) |
| `/applications/[id]` | `GET /applications/{application_id}`, `GET /users/me/cv`, `GET /jobs/{jobId}/gap-questions` |
| `/applications/[id]/vpr` | `GET /vprs`, `GET /vpr/{vprId}/status`, `POST /vpr/generate` |
| `/applications/[id]/cover-letter` | `GET /cover-letters`, `GET /cover-letter/{coverLetterId}/status`, `POST /cover-letter/generate` |
| `/applications/[id]/cv-tailored` | `GET /cv-tailorings`, `GET /cv-tailoring/{cvTailoringId}/status`, `POST /cv-tailoring/generate`, `DELETE /cv-tailoring/{cvTailoringId}` |
| `/applications/[id]/gap-analysis` | `GET /jobs/{jobId}/gap-questions`, `POST /jobs/{jobId}/gap-questions`, `POST /jobs/{jobId}/gap-responses`, `GET /applications/{application_id}`, `GET /users/me/cv` |
| `/applications/[id]/interview-prep` | `GET /interview-preps`, `GET /interview-prep/{interviewPrepId}/status`, `POST /interview-prep/generate` |
| `/applications/[id]/company-research` | `GET /company-research/{jobId}`, `POST /company-research/fetch` |
| `/cv-center` | `GET /users/me/cv`, `POST /users/me/cv` |
| `/cover-letters` (NEW) | `GET /cover-letters` |
| `/tailored-cvs` (NEW) | `GET /cv-tailorings` |
| `/billing` | `POST /billing/checkout`, `POST /billing/portal`, `GET /users/me/subscription`, `GET /users/me/usage` |
| `/settings` | `GET /users/me`, `PUT /users/me`, `GET /users/me/subscription` |
| `/login` | `POST /auth/login` |
| `/register` | `POST /auth/register` |
| Auth refresh | `POST /auth/refresh` |

**Out of scope (endpoints exist but no screenshot):** `GET /knowledge-base`, `POST /users/me/trial/reset`

**Note — module status endpoints:** `GET /vpr/{id}/status`, `GET /cover-letter/{id}/status`, `GET /interview-prep/{id}/status`, `GET /cv-tailoring/{id}/status` are used by the hub via `useModuleStatus` for polling. They are in scope but not directly called from page files.

**Note — module list endpoints:** `GET /vprs` and `GET /interview-preps` exist in the Swagger but are not consumed by any current page or new screenshot. `GET /cover-letters` and `GET /cv-tailorings` are consumed by the new `/cover-letters` and `/tailored-cvs` view pages.

## Screenshot-to-Route Map

| Screenshot file | Route | Type | Notes |
|----------------|-------|------|-------|
| Dashboard View page.png | /dashboard | base state | |
| Dashboard page-Account dropdown.png | /dashboard | interactive state | dropdown open |
| New Application Form.png | /dashboard | modal state | overlay on dashboard |
| New Application-Job Description textbox edit.png | /dashboard | modal edit state | text field active |
| New Application Form-Choose Base CV Modal.png | /dashboard | nested modal | CV picker |
| Applications View page.png | /applications | base state | NEW UI replacing redirect |
| Job Application Hub page-top.png | /applications/[id] | section 1 of 3 — shows VPR + cover letter module cards |
| Job Application Hub page-middle.png | /applications/[id] | section 2 of 3 — shows tailored CV + company research module cards |
| Job Application Hub page-bottom.png | /applications/[id] | section 3 of 3 — shows gap analysis + interview prep module cards |
| Base CVs View page.png | /cv-center | base state | |
| Base CV New Upload modal.png | /cv-center | modal state | |
| Cover Letters View page.png | /cover-letters (NEW) | base state | NEW route + sidebar item |
| Tailored CVs View page.png | /tailored-cvs (NEW) | base state | NEW route + sidebar item |
| gap analysis questionnaire form.png | /applications/[id]/gap-analysis | base state | |
| gap analysis questionnaire form continued.png | /applications/[id]/gap-analysis | scroll continuation | |
| gap analysis questionnaire form question counter read state.png | /applications/[id]/gap-analysis | read state | |
| gap analysis questionnaire form-rich textbox edit.png | /applications/[id]/gap-analysis | edit state | |
| gap analysis questionnaire form-rich textbox edit 2.png | /applications/[id]/gap-analysis | edit state variant | |
| Billing page.png | /billing | top section | |
| Billing page continued.png | /billing | bottom section | |
| subscription plans page.png | /billing | top section of billing page |
| Subscription plan page 2.png | /billing | bottom section of billing page |
| Settings page-Account Settings.png | /settings | top section | |
| Settings page.png | /settings | bottom section | |

## Output Artifacts (written to docs/upgrade/)

```
docs/upgrade/
├── screenshot-manifest.json       ← Phase 1 output
├── component-map.json             ← Already exists (project knowledge)
├── contract-verification.json     ← Phase 4 output
├── diff-analysis/{route-slug}.json ← Phase 3 output, one per route
├── gap-answers/{route-slug}.json  ← Phase 3b output, one per route
└── specs/{ComponentName}.md       ← Phase 5 output, one per component
```

## Testing Pyramid (enforce in all Phase 6 output)
- Unit: 70% — Vitest + Testing Library
- Integration: 20% — Jest
- E2E: 10% — Playwright

## Spec Required Sections (from spec_best_practices)
Every spec must include: Metadata, Problem Statement, Evidence, Architecture Map, Fix Plan, Acceptance Criteria, Verification Contract, Baseline & Regression Budget, Traceability Matrix, Rollback Trigger Matrix.

Status lifecycle: `draft → pending → in_progress → implemented → validated → closed`
- `implemented` = code-complete, NOT release-eligible
- `validated` = requires live evidence artifacts, minimum release-eligible
