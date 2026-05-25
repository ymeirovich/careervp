# Phase 5 Prompts — Batching Guide

## Token optimization rationale

Batching 2–3 same-tier components per conversation saves ~300–500 tokens per extra component by
amortizing fixed overhead: ROLE block, PROHIBITED rules, format instructions, contract JSON preamble.
Beyond 4 components Opus attention dilutes — split into a new conversation.

## Batching rules

1. **Same tier only** — never mix ui-primitive with layout or feature in one batch
2. **Same route data** — paste only the JSON files for that route (or shared-components.json for shared)
3. **Shared components (Badge, ProgressBar, AppSidebar, AppHeader)** — write the spec once using the
   route where their changes are most complete (usually applications-hub), then reference it in other routes
4. **Max 3 components per batch** — or 4 if they are all cosmetic with minimal gap answers

## Complete batch list — all 11 batches

| File | Batch | Components | Source route(s) |
| ---- | ----- | ---------- | --------------- |
| `applications-hub-A-ui-primitives.md` | A | Badge, ProgressBar | /applications/[id] |
| `applications-hub-B-layout.md` | B | AppSidebar, AppHeader, HubLayout | /applications/[id] |
| `applications-hub-C-feature.md` | C | ModuleCard, JobDetailHeader (new) | /applications/[id] |
| `shared-D-errorspinner.md` | D | ErrorBoundary, Spinner | shared |
| `dashboard-E-tables.md` | E | JobsTable (both modes), StatsRow | /dashboard + /applications |
| `dashboard-F-new-app-flow.md` | F | NewApplicationPage (new), ChooseBaseCVModal (new) | /dashboard |
| `list-pages-G.md` | G | CoverLettersPage (new), CoverLettersListTable (new), TailoredCVsPage (new), TailoredCVsListTable (new) | /cover-letters + /tailored-cvs |
| `cv-center-H.md` | H | CVCenterContent (replace), BaseCVsTable (new) | /cv-center |
| `gap-analysis-I.md` | I | GapAnalysisContent, GapQuestionCard (new), RichTextEditor (new) | /gap-analysis |
| `billing-J-main.md` | J | BillingContent, SubscriptionCard (new), UsageCard (new), BillingInfoCard (new) | /billing |
| `billing-K-plans.md` | K | PlansSection (new), PlanCard (new) | /billing |

Run K after J — PlansSection is part of BillingContent and the specs must be consistent.

## Not specced (intentional)

| Route | Reason |
| ----- | ------ |
| /settings (SettingsContent) | BLOCKED — requires 2fa_enabled, notification_preferences, DELETE /users/me — none present in current API |
| /dashboard AppSidebar, AppHeader, Badge | Already specced in A + B using applications-hub data — global scope, no re-spec needed |
| tokens.css | Token changes embedded in each component spec's Design Notes — write a separate tokens spec only if a dedicated tokens.css diff file is produced |
