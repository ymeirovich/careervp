# CareerVP Master Task List

**Last Updated:** 2026-03-08
**Status Legend:** ⬜ Not started | 🔄 In progress | ✅ Done | ⏸ Blocked

---

## Phase 0 — Documentation & Planning

All pre-coding documents. Complete before writing backend or frontend code for each feature.

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| D-001 | FRONTEND_ARCHITECTURE.md — core stack + schema decisions | Backend/Full | ✅ Done | Updated with Stripe + admin sections |
| D-002 | PRE_CODING_DOCS_GUIDE.md — guide for non-technical partner | Product | ✅ Done | Explains all 5 doc types |
| D-003 | ADMIN_PORTAL_SPEC.md — full backend spec | Backend | ✅ Done | Endpoints, Lambda, DAL, DynamoDB |
| D-004 | SUBSCRIPTION_STRIPE_SPEC.md — full backend spec | Backend | ✅ Done | Stripe setup, webhook, state machine |
| D-005 | MASTER_TASK_LIST.md (this file) | Product | ✅ Done | — |
| D-006 | API contract stabilization — update careervp-api-v1.yaml with billing + admin routes | Backend | ⬜ | Needed before openapi-typescript codegen |
| D-007 | Feature spec for Admin Portal UI | Product | ⬜ | Use PRE_CODING_DOCS_GUIDE.md template |
| D-008 | Feature spec for Subscription Upgrade UX | Product | ⬜ | Use PRE_CODING_DOCS_GUIDE.md template |

---

## Phase 1 — Backend Prerequisites (Build Before Frontend)

Backend must be deployed and testable before the frontend can integrate.

### 1A — Stripe & Subscriptions

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| S-001 | Create Stripe account (test mode) | Product | ⬜ | |
| S-002 | Create Product + 2 Prices in Stripe Dashboard (monthly $19, annual $149) | Product | ⬜ | Store price IDs |
| S-003 | Register webhook endpoint in Stripe (test mode URL) | Backend | ⬜ | 5 events listed in SUBSCRIPTION_STRIPE_SPEC.md |
| S-004 | Store Stripe keys in AWS SSM Parameter Store | Backend | ⬜ | `STRIPE_SECRET_KEY`, `STRIPE_PRICE_MONTHLY`, `STRIPE_PRICE_ANNUAL`, `STRIPE_WEBHOOK_SECRET` |
| S-005 | Create DynamoDB `careervp-subscriptions-dev` table + 3 GSIs | Backend | ⬜ | See SUBSCRIPTION_STRIPE_SPEC.md §4 |
| S-006 | Implement `billing_handler.py` — POST /billing/checkout | Backend | ⬜ | Returns Stripe Checkout URL |
| S-007 | Implement `billing_handler.py` — POST /billing/portal | Backend | ⬜ | Returns Customer Portal URL |
| S-008 | Implement `billing_handler.py` — GET /users/me/subscription | Backend | ⬜ | Returns subscription status |
| S-009 | Implement `webhook_handler.py` — all 5 Stripe events | Backend | ⬜ | See SUBSCRIPTION_STRIPE_SPEC.md §7 |
| S-010 | Implement `subscription_dal.py` — all DAL functions | Backend | ⬜ | See SUBSCRIPTION_STRIPE_SPEC.md §8 |
| S-011 | Update `job_handler.py` `_check_trial_and_quota()` to enforce subscription status | Backend | ⬜ | See SUBSCRIPTION_STRIPE_SPEC.md §9 |
| S-012 | Add API Gateway routes: POST /billing/checkout, POST /billing/portal, GET /users/me/subscription, POST /billing/webhook | Backend | ⬜ | Webhook has NO Cognito authorizer |
| S-013 | CDK deploy subscription infrastructure | Backend | ⬜ | |
| S-014 | Unit tests: billing_handler + webhook_handler (11 test cases) | Backend | ⬜ | See SUBSCRIPTION_STRIPE_SPEC.md §11 |
| S-015 | Live E2E test: full checkout flow with Stripe test card | Backend | ⬜ | Use Stripe CLI for webhook replay |

### 1B — Admin Portal Backend

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| A-001 | Create Cognito `Admins` group in User Pool | Backend | ⬜ | Add admin users via Console |
| A-002 | Add GSIs to users table: `AllUsersIndex` | Backend | ⬜ | See ADMIN_PORTAL_SPEC.md §3 |
| A-003 | Add GSIs to subscriptions table: `StatusIndex` (if not done in S-005) | Backend | ⬜ | |
| A-004 | Implement `shared/auth_utils.py` — `require_admin()` function | Backend | ⬜ | See ADMIN_PORTAL_SPEC.md §2 |
| A-005 | Implement `admin_handler.py` — GET /admin/users | Backend | ⬜ | Pagination + search + status filter |
| A-006 | Implement `admin_handler.py` — GET /admin/users/{userId} | Backend | ⬜ | Full user detail with jobs |
| A-007 | Implement `admin_handler.py` — GET /admin/metrics | Backend | ⬜ | Platform KPIs |
| A-008 | Implement `admin_handler.py` — POST /admin/users/{userId}/trial | Backend | ⬜ | Extend trial |
| A-009 | Implement `admin_handler.py` — POST /admin/users/{userId}/subscription/cancel | Backend | ⬜ | Cancel via Stripe API |
| A-010 | Implement `admin_handler.py` — GET /admin/subscriptions | Backend | ⬜ | List by status |
| A-011 | Implement `admin_dal.py` — all DAL functions | Backend | ⬜ | See ADMIN_PORTAL_SPEC.md §6 |
| A-012 | Add API Gateway routes under /admin with Lambda integration | Backend | ⬜ | See ADMIN_PORTAL_SPEC.md §8 |
| A-013 | CDK deploy admin infrastructure | Backend | ⬜ | |
| A-014 | Test admin auth rejection: regular user → 403 | Backend | ⬜ | |
| A-015 | Test all admin endpoints with Postman/pytest | Backend | ⬜ | |

### 1C — CORS Hardening (Required Before Production)

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| C-001 | Set `ALLOWED_ORIGINS` env var on all Lambda functions | Backend | ⬜ | `https://app.careervp.com` |
| C-002 | Fix CDK `_add_gateway_error_responses()` — replace `'*'` with actual domain | Backend | ⬜ | See FRONTEND_ARCHITECTURE.md §13 |

---

## Phase 2 — Frontend Core (P0 User Flows)

Build in this order: Auth → CV → Jobs → Gap → Artifacts

### 2A — Project Scaffolding

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| F-001 | `npx create-next-app@latest careervp-web --typescript --tailwind --app` | Frontend | ⬜ | |
| F-002 | Install deps: `aws-amplify @aws-amplify/adapter-nextjs @tanstack/react-query zustand zod react-hook-form` | Frontend | ⬜ | |
| F-003 | Install shadcn/ui: `npx shadcn@latest init` then add Button, Card, Dialog, Input, Badge, Alert, Table | Frontend | ⬜ | |
| F-004 | `lib/amplify-config.ts` — configure Cognito + cookie storage | Frontend | ⬜ | See FRONTEND_ARCHITECTURE.md §3 |
| F-005 | `lib/api-client.ts` — typed fetch wrapper with JWT | Frontend | ⬜ | See FRONTEND_ARCHITECTURE.md §4 |
| F-006 | `middleware.ts` — SSR route guard for /dashboard and /admin | Frontend | ⬜ | See FRONTEND_ARCHITECTURE.md §19 |
| F-007 | `.env.local` — all env vars | Frontend | ⬜ | See FRONTEND_ARCHITECTURE.md §4 |
| F-008 | `lib/schemas/` — all Zod schemas | Frontend | ⬜ | See FRONTEND_ARCHITECTURE.md §5 — copy schemas directly |
| F-009 | `app/(dashboard)/layout.tsx` — QueryProvider + AuthGuard | Frontend | ⬜ | |
| F-010 | Global CSS / theme variables | Frontend | ⬜ | See FRONTEND_ARCHITECTURE.md §11 |

### 2B — Authentication

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| F-011 | `app/(auth)/login/page.tsx` — login form | Frontend | ⬜ | Amplify `signIn()` |
| F-012 | `app/(auth)/register/page.tsx` — register form | Frontend | ⬜ | Amplify `signUp()` + confirm email |
| F-013 | `components/auth/LoginForm.tsx` — RHF + Zod validation | Frontend | ⬜ | |
| F-014 | `components/auth/RegisterForm.tsx` | Frontend | ⬜ | |
| F-015 | Sign out button in Header | Frontend | ⬜ | Amplify `signOut()` |
| F-016 | Test: login → dashboard redirect; invalid credentials → error | Frontend | ⬜ | |

### 2C — CV Management

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| F-017 | `lib/api/cv.ts` — `uploadCV()`, `listCVs()` | Frontend | ⬜ | See FRONTEND_ARCHITECTURE.md §6 — base64 upload |
| F-018 | `components/cv/CVUpload.tsx` — drag-drop + file input | Frontend | ⬜ | 5MB limit, pdf/docx/txt |
| F-019 | `components/cv/CVCard.tsx` — display parsed CV summary | Frontend | ⬜ | |
| F-020 | `app/(dashboard)/profile/page.tsx` — CV management | Frontend | ⬜ | |
| F-021 | Test: upload PDF → see parsed skills/experience | Frontend | ⬜ | |

### 2D — Job Creation & Dashboard

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| F-022 | `lib/api/jobs.ts` — `createJob()`, `listJobs()`, `getJob()` | Frontend | ⬜ | Note: `company_name` not `company` |
| F-023 | `stores/applicationStore.ts` — Zustand persist | Frontend | ⬜ | See FRONTEND_ARCHITECTURE.md §8 |
| F-024 | `components/jobs/JobCreateForm.tsx` — RHF + Zod | Frontend | ⬜ | |
| F-025 | `app/(dashboard)/dashboard/page.tsx` — job list + usage indicator | Frontend | ⬜ | |
| F-026 | `components/trial/CreditIndicator.tsx` — badge in Header | Frontend | ⬜ | Use `usage.applications.remaining` |
| F-027 | `components/trial/TrialGuard.tsx` — gate job creation | Frontend | ⬜ | See FRONTEND_ARCHITECTURE.md §10 |
| F-028 | Test: create job → redirects to gap questions on ready | Frontend | ⬜ | |

### 2E — Gap Analysis Q&A

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| F-029 | `lib/api/gap.ts` — `getGapQuestions()`, `submitGapResponses()` | Frontend | ⬜ | |
| F-030 | `components/gap/GapQuestionCard.tsx` — single Q with priority indicator | Frontend | ⬜ | |
| F-031 | `app/(dashboard)/jobs/[jobId]/gap-questions/page.tsx` — Q&A form | Frontend | ⬜ | Auto-save to Zustand every 30s; CRITICAL gating |
| F-032 | Submit gap responses → navigate to artifacts | Frontend | ⬜ | |
| F-033 | Test: CRITICAL unanswered → submit blocked; IMPORTANT skipped → warning shown | Frontend | ⬜ | |

### 2F — Artifact Generation & Display

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| F-034 | `lib/hooks/useJobStatus.ts` — adaptive polling hook | Frontend | ⬜ | See FRONTEND_ARCHITECTURE.md §7 |
| F-035 | `lib/api/artifacts.ts` — generate + status for all 4 artifacts | Frontend | ⬜ | Note ID field differences per artifact |
| F-036 | `components/artifacts/ArtifactCard.tsx` — status/progress/result | Frontend | ⬜ | |
| F-037 | `app/(dashboard)/jobs/[jobId]/artifacts/page.tsx` — 4-panel hub | Frontend | ⬜ | Parallel polling |
| F-038 | `app/(dashboard)/jobs/[jobId]/artifacts/vpr/page.tsx` — VPR viewer | Frontend | ⬜ | UVP + differentiators + score + download |
| F-039 | `app/(dashboard)/jobs/[jobId]/artifacts/cv/page.tsx` — CV diff + edit | Frontend | ⬜ | Side-by-side original vs tailored |
| F-040 | `app/(dashboard)/jobs/[jobId]/artifacts/cover-letter/page.tsx` | Frontend | ⬜ | |
| F-041 | `app/(dashboard)/jobs/[jobId]/artifacts/interview-prep/page.tsx` | Frontend | ⬜ | STAR format questions |
| F-042 | Application recovery via `reload_route` | Frontend | ⬜ | See FRONTEND_ARCHITECTURE.md §8 |
| F-043 | Test: full pipeline from job creation to 4 artifacts complete | Frontend | ⬜ | |

### 2G — Error Handling

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| F-044 | `components/GlobalErrorHandler.tsx` — TanStack Query global error handler | Frontend | ⬜ | See FRONTEND_ARCHITECTURE.md §9 |
| F-045 | `components/trial/UpgradeModal.tsx` — trial_expired + trial_exhausted | Frontend | ⬜ | Integrates with CheckoutButton |
| F-046 | Per-artifact error card + Regenerate button | Frontend | ⬜ | |
| F-047 | Rate limit (429) → auto-retry toast | Frontend | ⬜ | |

---

## Phase 3 — Billing Frontend

Requires Phase 1A (Stripe backend) to be deployed first.

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| B-001 | `lib/schemas/billing.ts` — SubscriptionSchema, CheckoutSessionSchema | Frontend | ⬜ | See FRONTEND_ARCHITECTURE.md §18 |
| B-002 | `lib/api/billing.ts` — `createCheckoutSession()`, `createPortalSession()` | Frontend | ⬜ | |
| B-003 | `lib/hooks/useSubscription.ts` — subscription context hook | Frontend | ⬜ | `isActive`, `isTrialing`, `canUseApp` |
| B-004 | `components/billing/CheckoutButton.tsx` | Frontend | ⬜ | Redirect to Stripe Checkout |
| B-005 | `components/billing/BillingPortalButton.tsx` | Frontend | ⬜ | Redirect to Stripe Customer Portal |
| B-006 | `components/billing/PlanCard.tsx` — monthly vs annual comparison | Frontend | ⬜ | |
| B-007 | Update `UpgradeModal.tsx` to use CheckoutButton + PlanCard | Frontend | ⬜ | |
| B-008 | `app/(dashboard)/settings/billing/page.tsx` — subscription status + manage | Frontend | ⬜ | |
| B-009 | `app/(dashboard)/billing/success/page.tsx` — post-checkout confirmation | Frontend | ⬜ | Invalidate subscription + usage queries |
| B-010 | Update `TrialGuard.tsx` to use `useSubscription().canUseApp` | Frontend | ⬜ | |
| B-011 | Update middleware to block `past_due` / `canceled` users at route level | Frontend | ⬜ | |
| B-012 | Test: full upgrade flow with Stripe test card `4242 4242 4242 4242` | Frontend | ⬜ | |
| B-013 | Test: payment failure → past_due banner shown | Frontend | ⬜ | Use card `4000 0000 0000 0002` |
| B-014 | Test: cancel subscription → blocked on next app creation | Frontend | ⬜ | |

---

## Phase 4 — Admin Portal Frontend

Requires Phase 1B (admin backend) to be deployed first.

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| AD-001 | `lib/schemas/admin.ts` — AdminUserSchema, AdminMetricsSchema | Frontend | ⬜ | See FRONTEND_ARCHITECTURE.md §19 |
| AD-002 | `lib/api/admin.ts` — all admin API functions | Frontend | ⬜ | |
| AD-003 | `app/(admin)/layout.tsx` — admin sidebar + admin group guard | Frontend | ⬜ | Redirect non-admins to /dashboard |
| AD-004 | Install TanStack Table: `npm i @tanstack/react-table` | Frontend | ⬜ | |
| AD-005 | Install Recharts: `npm i recharts` | Frontend | ⬜ | |
| AD-006 | `app/(admin)/admin/page.tsx` — KPI dashboard | Frontend | ⬜ | 4 metric cards + activity chart |
| AD-007 | `components/admin/AdminKPICard.tsx` | Frontend | ⬜ | |
| AD-008 | `app/(admin)/admin/users/page.tsx` — user table with search/filter | Frontend | ⬜ | TanStack Table, server-side pagination |
| AD-009 | `components/admin/AdminUserTable.tsx` | Frontend | ⬜ | Columns: email, name, status, apps used, last active, actions |
| AD-010 | `app/(admin)/admin/users/[userId]/page.tsx` — user detail | Frontend | ⬜ | Profile + subscription + jobs accordion |
| AD-011 | Admin action: extend trial — modal + POST /admin/users/{id}/trial | Frontend | ⬜ | |
| AD-012 | Admin action: cancel subscription — confirm modal + API call | Frontend | ⬜ | |
| AD-013 | `app/(admin)/admin/subscriptions/page.tsx` — subscription table | Frontend | ⬜ | Filter by status |
| AD-014 | `app/(admin)/admin/analytics/page.tsx` — conversion funnel chart | Frontend | ⬜ | Recharts BarChart + LineChart |
| AD-015 | CSV export from users table | Frontend | ⬜ | Install papaparse |
| AD-016 | Test: non-admin user → redirected to /dashboard | Frontend | ⬜ | |
| AD-017 | Test: admin can search, view, extend trial, cancel subscription | Frontend | ⬜ | |

---

## Phase 5 — QA & Pre-Launch

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| Q-001 | Mobile responsiveness — test all P0 flows on iPhone/Android viewport | Frontend | ⬜ | See FRONTEND_ARCHITECTURE.md §12 |
| Q-002 | CORS fix: Set `ALLOWED_ORIGINS` env var + fix gateway responses | Backend | ⬜ | See C-001, C-002 |
| Q-003 | Full E2E: register → upload CV → create job → gap Q&A → 4 artifacts | QA | ⬜ | |
| Q-004 | Full E2E: trial exhausted → upgrade → unlimited access | QA | ⬜ | |
| Q-005 | Full E2E: payment failed → past_due → update card → active | QA | ⬜ | |
| Q-006 | Stripe live mode setup: replace test keys with live keys | Product | ⬜ | |
| Q-007 | Switch Amplify Hosting to `main` branch | DevOps | ⬜ | |
| Q-008 | Custom domain: `app.careervp.com` → Amplify Hosting | DevOps | ⬜ | |
| Q-009 | Update CORS to `https://app.careervp.com` | Backend | ⬜ | |
| Q-010 | Final smoke test on production domain | QA | ⬜ | |

---

## Phase 6 — Post-Launch (P1)

| # | Task | Owner | Status | Notes |
|---|---|---|---|---|
| P1-001 | Multi-language support (EN + HE) — F-LANG-001 | Backend + Frontend | ⬜ | Detect mismatch, RTL for Hebrew |
| P1-002 | ATS compatibility checker badge — F-ATS-001 | Frontend | ⬜ | `ats_score` already in CV tailoring response |
| P1-003 | Knowledge base viewer — GET /knowledge-base | Frontend | ⬜ | Cross-application insights |
| P1-004 | Pre-computed metrics table for admin (EventBridge-driven) | Backend | ⬜ | Replace Scan-based metrics |
| P1-005 | Webhook idempotency: store processed event IDs to prevent double-processing | Backend | ⬜ | Use `stripe_event_id` as DynamoDB key |
| P1-006 | WAF + rate limiting on API Gateway | Backend | ⬜ | Migrate to CloudFront + WAF |
| P1-007 | Annual billing reconciliation job (EventBridge) | Backend | ⬜ | Sync Stripe state → DynamoDB nightly |

---

## Quick Reference — Critical Path to MVP Launch

```
D-001→D-005 (docs) ──► S-001→S-015 (Stripe backend)
                    ──► A-001→A-015 (admin backend)
                    ──► C-001→C-002 (CORS)
                              │
                              ▼
                   F-001→F-043 (frontend core)
                              │
                              ▼
                   B-001→B-014 (billing frontend)
                   AD-001→AD-017 (admin frontend)
                              │
                              ▼
                   Q-001→Q-010 (QA + launch)
```

**Minimum viable for first paying user:**
D-001–D-005 ✅ → S-001–S-015 → F-001–F-047 → B-001–B-014 → Q-001–Q-010
