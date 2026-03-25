# Frontend Implementation Spec — CareerVP CRUD UI

**Date**: March 24, 2026 (revised)
**Status**: Active design reference
**Source API**: `docs/swagger/careervp-core-api-dev-prod-swagger-apigateway (1).json`

---

## Table of Contents

### This file
1. [Overview & Architecture](#overview--architecture)
2. [Shared Layout & Navigation](#shared-layout--navigation)
3. [Dashboard Page](#dashboard-page-dashboarddashboard)

### [IMPLEMENTATION-PAGES.md](./IMPLEMENTATION-PAGES.md)
4. Application Hub (`/dashboard/jobs/[jobId]`)
5. Gap Analysis (`/dashboard/jobs/[jobId]/gap-analysis`)
6. VPR Display (`/dashboard/jobs/[jobId]/vpr`)
7. Cover Letter Display (`/dashboard/jobs/[jobId]/cover-letter`)
8. Interview Prep Display (`/dashboard/jobs/[jobId]/interview-prep`)
9. CV Center (`/dashboard/cv`)
10. CV Detail / Edit (`/dashboard/cv/edit` and `/dashboard/cv/new`)

### [IMPLEMENTATION-REFERENCE.md](./IMPLEMENTATION-REFERENCE.md)
11. Shared Components (ResourceCard, Badge, FormField)
12. API Client Methods
13. TypeScript Types
14. Design Tokens
15. Testing Checklist

---

## Overview & Architecture

CareerVP is a multi-page Next.js 15 (App Router) application. All authenticated pages live under `/dashboard` and share a common shell (Sidebar + Topbar) via `dashboard/layout.tsx`.

### Page Routing Table

| Route | File | Description |
|-------|------|-------------|
| `/login` | `app/login/page.tsx` | Login form (existing) |
| `/dashboard` | `app/dashboard/page.tsx` | Jobs table + StatusStrip (existing, updated) |
| `/dashboard/jobs/[jobId]` | `app/dashboard/jobs/[jobId]/page.tsx` | **NEW** Application Hub |
| `/dashboard/jobs/[jobId]/gap-analysis` | `app/dashboard/jobs/[jobId]/gap-analysis/page.tsx` | **NEW** Gap Analysis Q&A form |
| `/dashboard/jobs/[jobId]/vpr` | `app/dashboard/jobs/[jobId]/vpr/page.tsx` | **NEW** VPR display |
| `/dashboard/jobs/[jobId]/cover-letter` | `app/dashboard/jobs/[jobId]/cover-letter/page.tsx` | **NEW** Cover Letter display |
| `/dashboard/jobs/[jobId]/interview-prep` | `app/dashboard/jobs/[jobId]/interview-prep/page.tsx` | **NEW** Interview Prep display |
| `/dashboard/cv` | `app/dashboard/cv/page.tsx` | **NEW** CV Center (single CV summary) |
| `/dashboard/cv/edit` | `app/dashboard/cv/edit/page.tsx` | **NEW** CV edit form |
| `/dashboard/cv/new` | `app/dashboard/cv/new/page.tsx` | **NEW** CV upload form (first time) |

### ID Glossary (Read This First)

There are three distinct IDs in this system that are easy to confuse:

| Name | Meaning | Source |
|------|---------|--------|
| `job_id` | Saved job posting ID | `POST /jobs` response |
| `application_id` | Workflow state key — **same UUID as `job_id`** | `GET /applications/{id}` |
| VPR `job_id` (async task) | ID for a specific async generation run | `POST /vpr/generate` response |

**`application_id` = `job_id`** — the backend assigns the same UUID to both. When the frontend generates a VPR, it sends `job_id` in the request body; the backend stores it internally as `application_id`. They refer to the same entity.

**Field name normalization:** `GET /jobs/{jobId}` returns `company` and `role_title`. `GET /jobs` (list) returns `company_name` and `title`. The `api.ts` client normalizes both to `company_name` / `title` before returning.

### Resource Dependency Chain

Resources must be generated in dependency order. The Application Hub enforces this with disabled states.

```
Job Created (POST /jobs) → job_id = application_id
├── Company Research  (optional, no deps)
├── CV Selection      (required for all downstream — stored per-application in local state)
└── Gap Analysis      (requires CV selected)
    └── VPR           (requires CV + Gap Analysis complete)
        ├── Cover Letter    (requires VPR ready)
        └── Interview Prep  (requires VPR ready)
```

### Directory Structure

```
frontend/
├── app/
│   ├── auth-context.tsx
│   ├── dashboard/
│   │   ├── layout.tsx                    ← NEW: shared shell
│   │   ├── page.tsx                      ← UPDATED: StatusStrip + JobsCard only
│   │   ├── jobs/
│   │   │   └── [jobId]/
│   │   │       ├── page.tsx              ← NEW: Application Hub
│   │   │       ├── gap-analysis/
│   │   │       │   └── page.tsx          ← NEW
│   │   │       ├── vpr/
│   │   │       │   └── page.tsx          ← NEW
│   │   │       ├── cover-letter/
│   │   │       │   └── page.tsx          ← NEW
│   │   │       └── interview-prep/
│   │   │           └── page.tsx          ← NEW
│   │   └── cv/
│   │       ├── page.tsx                  ← NEW: CV Center (summary)
│   │       ├── edit/
│   │       │   └── page.tsx              ← NEW: CV Edit form
│   │       └── new/
│   │           └── page.tsx              ← NEW: CV Upload (first time)
│   ├── login/
│   │   └── page.tsx
│   └── api/proxy/[...path]/route.ts
│
├── components/
│   ├── dashboard/
│   │   ├── Sidebar.tsx                   ← EXTRACTED + updated
│   │   ├── Topbar.tsx                    ← EXTRACTED + updated
│   │   ├── StatusStrip.tsx               ← EXTRACTED
│   │   └── ResourceCard.tsx              ← NEW
│   ├── ui/
│   │   ├── button.tsx                    ← existing
│   │   ├── Badge.tsx                     ← NEW
│   │   └── FormField.tsx                 ← NEW
│   └── NewApplicationModal.tsx           ← existing
│
└── lib/
    ├── api.ts                            ← UPDATED: new methods
    ├── auth.ts
    ├── types.ts                          ← UPDATED: new interfaces
    └── utils.ts
```

---

## Shared Layout & Navigation

### `app/dashboard/layout.tsx`

Wraps every `/dashboard/**` route. Must be `"use client"` because it uses `useAuth()` (Cognito) and `usePathname()` (for Sidebar active state).

Fetches `usage` and `subscription` once and exposes them via `DashboardContext` so every page's Topbar can read `userName` and `usage` without re-fetching.

**Context:**
```typescript
// app/dashboard/dashboard-context.tsx
interface DashboardContextValue {
  userName: string
  usage: Usage | null
  subscription: SubscriptionResponse | null
}
export const DashboardContext = createContext<DashboardContextValue>(...)
```

**Component Hierarchy:**
```
DashboardLayout  ("use client")
├── Auth guard: if !user → redirect("/login")
├── DashboardContext.Provider (userName, usage, subscription)
│   └── Shell wrapper (div.min-h-screen, bg-[#fcf7f5])
│       └── App Shell (1239px, border, bg-[#fafafa])
│           ├── Sidebar (240px)  ← reads usePathname() for active state
│           └── Content Area (flex-1)
│               └── {children}  ← page content goes here
```

**Data fetched once in layout:**
```typescript
Promise.all([api.getUsage(), api.getSubscription()])
```

**Key point:** Individual pages render their own `Topbar` as the first child with a `title` prop. Topbar reads `userName`/`usage` from `DashboardContext` — no prop drilling needed.

### `components/dashboard/Sidebar.tsx`

Extracted from `dashboard/page.tsx` and made route-aware.

**Props:** None (reads current path via `usePathname()`)

**Active state logic:** Item is active when `pathname.startsWith(item.href)` (except `/dashboard` which requires exact match to avoid matching all sub-routes).

**Updated `NAV_ITEMS`:**
```typescript
const NAV_ITEMS = [
  { label: "CareerVP", isSection: true },
  { label: "Dashboard", href: "/dashboard", exact: true },
  { label: "Applications", href: "/dashboard/jobs" },
  { label: "CV Center", href: "/dashboard/cv" },
  { label: "Billing", href: "#" },        // placeholder
  { label: "Settings", href: "#" },       // placeholder
];
```

**Styling:** Unchanged — `w-60`, white BG, `border-r border-[#cbd5e1]`, active item `bg-[rgba(217,217,217,0.61)]`.

### `components/dashboard/Topbar.tsx`

Extracted from `dashboard/page.tsx` with a `title` prop and optional breadcrumb.

**Props:**
```typescript
interface TopbarProps {
  title: string
  breadcrumb?: { label: string; href: string }[]
  // userName and usage read from DashboardContext — not passed as props
}
```

**Breadcrumb** renders as `Dashboard > Applications > [Job Title]` above the title when provided. Uses `>` separator, each segment is a link except the last.

**Styling:** Unchanged — `h-20`, white BG, `border-b border-[#cbd5e1]`, `px-6`.

---

## Dashboard Page (`/dashboard`)

**File:** `app/dashboard/page.tsx`

**Changes from current:** Sidebar and Topbar moved to layout. Page now renders only `StatusStrip` + `JobsCard`. "View Application" link updated from `href="#"` to `href={`/dashboard/jobs/${job.job_id}`}`.

**Component Hierarchy:**
```
DashboardPage
├── Topbar (title="Dashboard")
└── main (flex column, gap-6, p-6)
    ├── StatusStrip (plan, credits, status)
    └── JobsCard
        ├── Header: "My Jobs" + "+ New Application" button
        └── Table
            └── Row: Title | Company | Status | Created | "View Application" → /dashboard/jobs/{id}
```

**Data fetched on mount:**
```typescript
api.getJobs()
// usage and subscription come from DashboardContext (fetched once in layout)
```

**"View Application" link** (updated):
```typescript
<a href={`/dashboard/jobs/${job.job_id}`} className="text-[#1e2229] hover:underline">
  View Application
</a>
```

---
