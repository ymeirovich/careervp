# Frontend Page Specs — CareerVP

> **Read first:** `IMPLEMENTATION.md` — architecture overview, ID glossary, routing table, dependency chain, shared layout, and Dashboard page.
> **Reference:** `IMPLEMENTATION-REFERENCE.md` — shared components, API client methods, TypeScript types, design tokens, testing checklist.

---

## Table of Contents

4. [Application Hub](#application-hub-page-dashboardjobsjobid)
5. [Gap Analysis (CRUD form)](#gap-analysis-page-dashboardjobsjobidgap-analysis)
6. [VPR Display](#vpr-page-dashboardjobsjobidvpr)
7. [Cover Letter Display](#cover-letter-page-dashboardjobsjobidcover-letter)
8. [Interview Prep Display](#interview-prep-page-dashboardjobsjobidinterview-prep)
9. [CV Center](#cv-center-page-dashboardcv)
10. [CV Detail / Edit (CRUD form)](#cv-detail--edit-page-dashboardcvedit-and-dashboardcvnew)

---

## Application Hub Page (`/dashboard/jobs/[jobId]`)

**File:** `app/dashboard/jobs/[jobId]/page.tsx`

The central detail page for a single job application. Replaces the old dead `href="#"` link. Displays the job details and a grid of all associated AI resources with their generation status.

**Component Hierarchy:**
```
ApplicationHubPage
├── Topbar (title=job.title, breadcrumb=[{Dashboard, /dashboard}])
└── main (flex column, gap-6, p-6)
    ├── JobHeader
    │   ├── Title (text-2xl font-bold) + Company (text-lg text-muted)
    │   ├── Status badge (Active=green, Draft=gray)
    │   ├── Job URL (if present, external link)
    │   └── Description preview (3 lines, expandable)
    │
    └── ResourceGrid (grid grid-cols-2 gap-4)
        ├── CompanyResearchCard
        ├── CVSelectionCard
        ├── GapAnalysisCard
        ├── VPRCard
        ├── CoverLetterCard
        └── InterviewPrepCard
```

**Data fetched on mount — single call:**
```typescript
// application_id = job_id (same UUID)
const hub = await api.getApplication(jobId)
// Returns: { application, job, cv, gap_analysis: { questions, responses }, artifacts: { vpr, cover_letter, interview_prep, cv_tailored } }
```

`GET /applications/{application_id}` is the hub endpoint — it returns the full application state in one call. No need for 7 parallel requests. Use `apiFetchOrNull` since a freshly-created job has no application record yet (404 = empty state).

### ResourceCard Specs for Application Hub

Each card uses the `ResourceCard` component (see `IMPLEMENTATION-REFERENCE.md` → Shared Components).

#### Company Research Card
| Field | Value |
|-------|-------|
| Title | "Company Research" |
| Status: not started | "Generate company intelligence" |
| Status: ready | Confidence score + source label |
| Primary action (not started) | "Generate" → calls `api.fetchCompanyResearch()` inline |
| Primary action (ready) | No link needed — preview shown inline |
| Dependency | None |

#### CV Selection Card
| Field | Value |
|-------|-------|
| Title | "Base CV" |
| Status: no CV | "No CV uploaded" |
| Status: selected | CV full_name + language badge |
| Primary action (no CV) | "Upload CV" → `/dashboard/cv` |
| Primary action (selected) | "Change CV" → `/dashboard/cv` |
| Dependency | None |

**Note:** CV selection is stored in local component state for the session (no dedicated PUT endpoint); CV is linked to downstream generates via `cv_id`.

#### Gap Analysis Card
| Field | Value |
|-------|-------|
| Title | "Gap Analysis" |
| Status: not started | "Identify qualification gaps" |
| Status: in_progress | "N of Q questions answered" |
| Status: complete | "Q questions answered ✓" |
| Primary action (not started) | "Start Gap Analysis" → `/dashboard/jobs/{jobId}/gap-analysis` |
| Primary action (in_progress) | "Continue Answering" → same |
| Primary action (complete) | "View Responses" → same |
| Dependency | CV must be selected (show "Select a CV first" when disabled) |

#### VPR Card
| Field | Value |
|-------|-------|
| Title | "Value Proposition Report" |
| Status: not started | "Generate your positioning brief" |
| Status: pending/processing | Spinner + "Generating…" + `estimated_time_seconds` countdown |
| Status: ready | Word count + `version` label |
| Primary action (not started) | "Generate VPR" → `POST /vpr/generate` with `{ job_id, cv_id, gap_response_ids }` → store returned async `job_id` → begin polling |
| Primary action (ready) | "View VPR" → `/dashboard/jobs/{jobId}/vpr` |
| Secondary action (ready) | "Regenerate" → confirmation then re-generate |
| Dependency | CV selected + Gap Analysis complete |

**Async polling pattern (shared by VPR, Cover Letter, Interview Prep):**
```typescript
// 1. POST to generate → returns { job_id: asyncTaskId, status: "processing", estimated_time_seconds }
// 2. Store asyncTaskId in component state
// 3. Poll GET /vpr/{asyncTaskId}/status every 3 seconds
// 4. When status = "COMPLETED" → refresh hub data via api.getApplication(jobId)
// 5. When status = "FAILED" → show error banner
// 6. Stop polling on unmount (useEffect cleanup)
```

#### Cover Letter Card
| Field | Value |
|-------|-------|
| Title | "Cover Letter" |
| Status: not started | "Draft your application letter" |
| Status: pending/processing | Spinner + "Generating…" |
| Status: ready | word_count + tone label |
| Primary action (not started) | "Generate Cover Letter" → `POST /cover-letter/generate` → async polling |
| Primary action (ready) | "View Letter" → `/dashboard/jobs/{jobId}/cover-letter` |
| Dependency | VPR must be ready (status = COMPLETED) |

#### Interview Prep Card
| Field | Value |
|-------|-------|
| Title | "Interview Prep" |
| Status: not started | "Prepare for your interview" |
| Status: pending/processing | Spinner + "Generating…" |
| Status: ready | Question count preview |
| Primary action (not started) | "Generate Prep" → `POST /interview-prep/generate` → async polling |
| Primary action (ready) | "View Prep" → `/dashboard/jobs/{jobId}/interview-prep` |
| Dependency | VPR must be ready (status = COMPLETED) |

---

## Gap Analysis Page (`/dashboard/jobs/[jobId]/gap-analysis`)

**File:** `app/dashboard/jobs/[jobId]/gap-analysis/page.tsx`

The canonical **CRUD form page** example. Implements the full New / Edit / Cancel / Save flow.

**Component Hierarchy:**
```
GapAnalysisPage
├── Topbar (title="Gap Analysis", breadcrumb=[{Dashboard}, {jobTitle, /dashboard/jobs/jobId}])
└── main (flex column, gap-6, p-6)
    ├── PageHeader
    │   ├── "Gap Analysis" title
    │   ├── Subtitle: "Answer questions to identify gaps between your CV and this role"
    │   └── "Generate Questions" button (only if no questions yet)
    │
    ├── [If no questions] EmptyState
    │   └── "No questions generated yet. Click Generate Questions to start."
    │
    └── [If questions exist] QuestionForm
        ├── FormHeader
        │   ├── "{N} questions" label
        │   └── Edit / Save / Cancel button bar (sticky top)
        │
        └── QuestionList (flex column, gap-4)
            └── QuestionCard × N
                ├── QuestionHeader
                │   ├── Question text (font-medium)
                │   └── Badges: Impact (HIGH=green / MED=amber / LOW=gray) + Probability
                ├── DestinationRadio (view mode: badge only)
                │   ├── ● Include in CV (destination = CV_IMPACT)
                │   └── ○ Interview Only (destination = INTERVIEW_MVP_ONLY)
                └── AnswerField
                    ├── [View mode] Answer text (text-sm, text-muted if empty)
                    └── [Edit mode] <textarea rows=4> with orange focus ring
```

### CRUD State Machine

```
State: VIEW (default)
  ↓ "Edit" button clicked
State: EDIT
  ↓ "Cancel" button clicked → revert local state → State: VIEW
  ↓ "Save" button clicked → POST /jobs/{jobId}/gap-responses → State: SAVING
State: SAVING
  ↓ Success → toast "Saved successfully" → State: VIEW
  ↓ Error → show error banner → State: EDIT
```

**Generate Questions flow** (first time):
1. Click "Generate Questions" → `api.generateGapQuestions(data)` → loading spinner
2. API returns questions → store in page state
3. Immediately enter EDIT mode so user can start answering

**Data Flow:**
```typescript
// On mount
const questions = await api.getGapQuestions(jobId)  // GET /jobs/{jobId}/gap-questions

// On save
await api.saveGapResponses(jobId, responses)  // POST /jobs/{jobId}/gap-responses
// responses: Array<{ question_id, question, answer, destination }>
```

**Validation:** Each answered question requires both `answer` (non-empty) and `destination` selected. Unanswered questions are allowed (partial save). Show count: "5 of 8 answered".

**Button bar styling:**
```typescript
// Sticky at top of QuestionForm
<div className="sticky top-0 z-10 flex items-center justify-between bg-white border-b border-[#cbd5e1] px-6 py-3">
  <span className="text-sm text-[#6b7280]">5 of 8 answered</span>
  <div className="flex gap-2">
    <button onClick={cancel} className="px-4 py-2 text-sm border border-[#cbd5e1] rounded-[8px]">Cancel</button>
    <button onClick={save} className="px-4 py-2 text-sm bg-[#f97316] text-white rounded-[8px]">Save</button>
  </div>
</div>
```

---

## VPR Page (`/dashboard/jobs/[jobId]/vpr`)

**File:** `app/dashboard/jobs/[jobId]/vpr/page.tsx`

**Display page** — read-only, shows AI-generated VPR content.

**Component Hierarchy:**
```
VPRPage
├── Topbar (title="Value Proposition Report", breadcrumb=[{Dashboard}, {jobTitle}])
└── main (flex column, gap-8, p-6)
    ├── PageHeader
    │   ├── Title + Company subtitle
    │   ├── Meta: word_count + version + created_at
    │   └── "Regenerate" button (with confirmation modal)
    │
    ├── ExecutiveSummary (card)
    │   ├── Section title: "Executive Summary"
    │   └── prose text (text-sm leading-relaxed)
    │
    ├── EvidenceMatrix (card)
    │   ├── Section title: "Evidence Matrix"
    │   └── Table
    │       ├── Header: Requirement | Evidence | Alignment | Impact Potential
    │       └── Rows: alignment color coded
    │           ├── STRONG   → text-[#16b44b] badge
    │           ├── MODERATE → text-[#f59e0b] badge
    │           └── DEVELOPING → text-[#6b7280] badge
    │
    ├── Differentiators (card)
    │   ├── Section title: "Key Differentiators"
    │   └── ul.list-disc (3-5 items)
    │
    ├── GapStrategies (card, if any)
    │   ├── Section title: "Gap Strategies"
    │   └── GapStrategyItem × N
    │       ├── Gap label (text-sm font-medium)
    │       ├── Mitigation approach (text-sm)
    │       └── Transferable skills chips
    │
    ├── TalkingPoints (card)
    │   ├── Section title: "Talking Points"
    │   └── ol.list-decimal (5-7 items)
    │
    └── Keywords (card)
        ├── Section title: "ATS Keywords"
        └── Chip cloud (flex-wrap gap-2)
            └── KeywordChip: "px-2 py-1 text-xs bg-[#f0f2f5] rounded-[4px]"
```

**Data fetched on mount:**
```typescript
// Re-use the same hub endpoint — hub.artifacts.vpr.vpr is the VPR when COMPLETED
const hub = await api.getApplication(jobId)
const vpr = hub?.artifacts.vpr?.vpr ?? null
if (!vpr) redirect(`/dashboard/jobs/${jobId}`)  // not generated yet — back to hub
```

**Section card styling (reused across all display pages):**
```typescript
className="rounded-[8px] border border-[#cbd5e1] bg-white p-6 flex flex-col gap-4"
```

**Section title styling:**
```typescript
className="text-base font-bold text-[#1e2229]"
```

---

## Cover Letter Page (`/dashboard/jobs/[jobId]/cover-letter`)

**File:** `app/dashboard/jobs/[jobId]/cover-letter/page.tsx`

**Display page** — read-only, shows AI-generated cover letter with copy functionality.

**Component Hierarchy:**
```
CoverLetterPage
├── Topbar (title="Cover Letter", breadcrumb=[{Dashboard}, {jobTitle}])
└── main (flex column, gap-6, p-6)
    ├── PageHeader
    │   ├── Title + Company subtitle
    │   ├── Meta badges: tone | word_count words | version
    │   └── Action buttons
    │       ├── "Copy to Clipboard" button (icon + text)
    │       └── "Regenerate" button (gray outline)
    │
    ├── FullTextCard (card)
    │   ├── Section title: "Cover Letter"
    │   └── prose text (full_text, whitespace-pre-wrap, leading-relaxed)
    │
    └── ParagraphsCard (card, collapsible)
        ├── Section title: "Paragraph Breakdown" + toggle arrow
        └── [When expanded] ParagraphSection × N
            ├── Type label: "Hook" | "Proof Points" | "Close"
            │   (colored: Hook=orange, Proof=blue, Close=green)
            ├── word_count badge
            └── content text (text-sm)
```

**Copy to Clipboard:**
```typescript
navigator.clipboard.writeText(coverLetter.full_text)
// Show "Copied!" toast for 2 seconds
```

**Data fetched on mount:**
```typescript
const hub = await api.getApplication(jobId)
const letter = hub?.artifacts.cover_letter?.cover_letter ?? null
if (!letter) redirect(`/dashboard/jobs/${jobId}`)
```

---

## Interview Prep Page (`/dashboard/jobs/[jobId]/interview-prep`)

**File:** `app/dashboard/jobs/[jobId]/interview-prep/page.tsx`

**Display page** — read-only, shows AI-generated interview questions and guidance.

**Component Hierarchy:**
```
InterviewPrepPage
├── Topbar (title="Interview Prep", breadcrumb=[{Dashboard}, {jobTitle}])
└── main (flex column, gap-6, p-6)
    ├── PageHeader
    │   ├── Title + Company subtitle
    │   ├── Meta: "{N} questions" + created_at
    │   └── "Regenerate" button
    │
    ├── QuestionsSection
    │   ├── Section title: "Interview Questions"
    │   └── QuestionCard × N (flex column, gap-3)
    │       ├── QuestionHeader (flex, justify-between)
    │       │   ├── Question number + text (font-medium)
    │       │   └── Badges: type (Behavioral/Technical/Situational/Gap-Focused) + difficulty
    │       └── QuestionBody (collapsible, default collapsed)
    │           ├── [Expanded] STARAnswer
    │           │   ├── "Situation:" / "Task:" / "Action:" / "Result:" labels
    │           │   └── text per STAR field
    │           ├── [Expanded] "Why you'll be asked this:" italic text
    │           └── [Expanded] Tips (ul.list-disc text-sm)
    │
    ├── QuestionsToAskSection (card)
    │   ├── Section title: "Questions to Ask the Interviewer"
    │   └── QuestionToAskItem × N
    │       ├── Question text (font-medium)
    │       └── Purpose text (text-sm text-muted)
    │
    ├── ChecklistSection (card)
    │   ├── Section title: "Pre-Interview Checklist"
    │   └── ChecklistItem × N (client-side checkbox state only)
    │       └── <input type="checkbox"> + label
    │
    └── SalarySection (card, only if salary_guidance present)
        ├── Section title: "Salary Guidance"
        └── salary_guidance text (text-sm)
```

**Question type badge colors:**
| Type | Color |
|------|-------|
| Behavioral | blue `bg-[#eff6ff] text-[#3b82f6]` |
| Technical | purple `bg-[#f5f3ff] text-[#8b5cf6]` |
| Situational | amber `bg-[#fffbeb] text-[#f59e0b]` |
| Gap-Focused | orange `bg-[#fff7ed] text-[#f97316]` |

**Difficulty badge colors:**
| Difficulty | Color |
|-----------|-------|
| Easy | green `text-[#16b44b]` |
| Medium | amber `text-[#f59e0b]` |
| Hard | red `text-[#ef4444]` |

**Data fetched on mount:**
```typescript
const hub = await api.getApplication(jobId)
const prep = hub?.artifacts.interview_prep?.interview_prep ?? null
if (!prep) redirect(`/dashboard/jobs/${jobId}`)
```

---

## CV Center Page (`/dashboard/cv`)

**File:** `app/dashboard/cv/page.tsx`

**Single-CV page** — one CV per user. The user can upload multiple CV versions and select which one to use per application, but `GET /users/me/cv` returns the current/active CV object.

**Component Hierarchy:**
```
CVCenterPage
├── Topbar (title="CV Center")
└── main (flex column, gap-6, p-6)
    ├── PageHeader
    │   ├── "My CV" title
    │   └── [If CV exists] "Edit CV" button → /dashboard/cv/edit
    │       [If no CV]    "+ Upload CV" button → /dashboard/cv/new
    │
    ├── [If no CV] EmptyState
    │   ├── "No CV uploaded yet."
    │   └── "+ Upload CV" CTA → /dashboard/cv/new
    │
    └── [If CV exists] CVSummaryCard (card, read-only)
        ├── CVHeader
        │   ├── full_name (text-2xl font-bold)
        │   ├── language badge (EN / HE)
        │   └── "Last updated" meta
        ├── ContactInfoRow (email, phone, location, LinkedIn chips)
        ├── SkillsPreview (first 10 skills as chips + "…and N more")
        ├── ExperienceCount ("N positions")
        └── "View / Edit Full CV" button → /dashboard/cv/edit
```

**API:** `GET /users/me/cv` → single `UserCV` object (or 404 if none uploaded yet). Use `apiFetchOrNull`.

**CV selection per application** is handled on the Application Hub page, not here. The hub's CV Selection card shows the active CV name and a "Change" link back to this page.

---

## CV Detail / Edit Page (`/dashboard/cv/edit` and `/dashboard/cv/new`)

**Files:**
- `app/dashboard/cv/edit/page.tsx` — edit the existing CV (GET then POST upsert)
- `app/dashboard/cv/new/page.tsx` — upload first CV (blank form → POST)

> No `[cvId]` dynamic segment needed — there is one CV per user. Both pages share the same form component; the only difference is empty vs pre-filled initial state. Both save via `POST /users/me/cv` (upsert — no separate PUT endpoint).

The canonical **read/write form page**. Supports viewing and editing CV data.

**Component Hierarchy:**
```
CVDetailPage
├── Topbar (title="Edit CV" or "New CV", breadcrumb=[{CV Center, /dashboard/cv}])
└── main (flex column, gap-6, p-6)
    ├── StickyActionBar (sticky top-0 z-10, bg-white, border-b)
    │   ├── [View mode] "Edit" button (orange)
    │   ├── [Edit mode] "Cancel" button (gray outline) + "Save" button (orange)
    │   └── Unsaved changes indicator (text-sm text-amber if dirty)
    │
    ├── ContactInfoSection (card)
    │   ├── Section title: "Contact Info"
    │   └── FormFields: Full Name | Email | Phone | Location | LinkedIn
    │       └── [FLEXIBLE — all editable]
    │
    ├── ProfessionalSummarySection (card)
    │   ├── Section title: "Professional Summary"
    │   │   └── ⓘ "FLEXIBLE — can be tailored per application"
    │   └── [View] prose text | [Edit] <textarea rows=6>
    │
    ├── WorkExperienceSection (card)
    │   ├── Section title: "Work Experience"
    │   └── ExperienceEntry × N
    │       ├── ImmutableHeader (bg-[rgba(245,245,245,0.8)])
    │       │   ├── 🔒 Role + " at " + Company (font-medium)
    │       │   └── Dates (text-sm text-muted)
    │       └── AchievementsList
    │           ├── [View] ul.list-disc items
    │           └── [Edit] AchievementInput × N + "Add Achievement" link
    │               └── ⚠ "Must be verifiable — no fabrication"
    │
    ├── EducationSection (card)
    │   ├── Section title: "Education"
    │   └── EducationEntry × N
    │       └── ImmutableHeader: 🔒 Degree + Institution + Graduation Date
    │
    ├── SkillsSection (card)
    │   ├── Section title: "Skills" + count badge
    │   └── [View] chip cloud | [Edit] TagInput (add/remove chips, max 50)
    │
    ├── CertificationsSection (card)
    │   ├── Section title: "Certifications"
    │   └── CertificationItem × N: Name | Issuer | Date
    │
    ├── TopAchievementsSection (card)
    │   ├── Section title: "Top Achievements"
    │   │   └── ⓘ "Max 3 — must be verifiable"
    │   └── [View] ol.list-decimal | [Edit] <textarea rows=2> × 3
    │
    └── LanguagesSection (card)
        ├── Section title: "Languages"
        └── [View] chip cloud | [Edit] TagInput
```

### CRUD State Machine (CV Edit)

```
State: VIEW (default for /dashboard/cv/edit when CV exists)
State: EDIT (default for /dashboard/cv/new)
  ↓ "Cancel" → if new: navigate to /dashboard/cv | if existing: revert state → VIEW
  ↓ "Save" → POST /users/me/cv (new) or POST again (replace existing) → State: SAVING
State: SAVING
  ↓ Success → navigate to /dashboard/cv → State: VIEW (via CV Center)
  ↓ Error → show error banner → State: EDIT
```

**Note:** The API uses `POST /users/me/cv` for both create and replace (upsert). There is no separate PUT endpoint for CV updates.

### IMMUTABLE Field Treatment

Work experience dates, company names, role titles, and education entries are marked IMMUTABLE in the API spec. In the UI:
- Rendered with `🔒` icon and slightly dimmed background (`bg-[rgba(245,245,245,0.8)]`)
- In view mode: displayed as read-only text
- In edit mode: still non-editable (no input rendered), with tooltip "Cannot be modified — this field is locked to prevent misrepresentation"
- Achievements and skills ARE editable (VERIFIABLE tier)

**Data flow:**
```typescript
// Existing CV
const cv = await api.getCV()   // GET /users/me/cv

// Save
await api.saveCV(cvData)       // POST /users/me/cv
```

---

**Last Updated**: March 24, 2026
