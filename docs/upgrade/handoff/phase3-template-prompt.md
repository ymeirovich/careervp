# Phase 3 — Visual Diff Analysis (Per-Page Template)

Use this template for each page analysis conversation. Upload only the screenshots for the current page.
Replace ALL `{placeholders}` before sending.

---

## How to Use This Template

1. Open a new conversation in this project
2. Upload only the screenshot(s) for the current page (see "screenshots to upload" below)
3. Copy the prompt below, fill in the placeholders, and send

---

## Page Analysis Prompt

```
ROLE: UI spec engineer comparing redesign screenshots to an existing React component tree.
OUTPUT: Two JSON files — diff analysis and gap interview questions. No prose.

TASK: Analyse the attached screenshot(s) for route {ROUTE} and produce:
1. A diff analysis JSON (what changed visually)
2. A gap interview JSON (questions needed to complete the spec)

---

## PART 1 — Diff Analysis

Output format:
{
  "route": "{ROUTE}",
  "page_title": "{PAGE_TITLE}",
  "screenshot_files": ["{SCREENSHOT_FILE(S)}"],
  "is_new_route": {true|false},
  "token_changes": [
    {
      "token": "--token-name",
      "current": "#value-or-description",
      "desired": "#value-or-unknown",
      "confidence": "high | medium | low"
    }
  ],
  "layout_changes": [
    {
      "description": "plain English description of layout difference",
      "affects_component": "ComponentName or 'unknown'",
      "change_type": "spacing | structure | order | removal | addition | new-component"
    }
  ],
  "component_changes": [
    {
      "component": "ComponentName",
      "file": "components/.../Component.tsx or 'NEW'",
      "tier": "ui-primitive | layout | feature | shared | new",
      "change_type": "modify | replace | remove | new",
      "visual_description": "what it looks like in the screenshot vs. current",
      "interaction_states_visible": ["default", "hover", "active", "edit", "open"],
      "interaction_states_needed_but_not_shown": ["loading", "error", "empty", "disabled"],
      "backend_data_required": "describe or 'none'",
      "backend_available": "yes | no | unknown"
    }
  ],
  "new_components_needed": ["ComponentName — brief description"],
  "sidebar_change": {
    "required": false,
    "description": ""
  },
  "ambiguities": [
    "anything unclear that requires a decision"
  ]
}

Save as: docs/upgrade/diff-analysis/{ROUTE_SLUG}.json

---

## PART 2 — Gap Interview Questions

Generate questions ONLY for states not visible in the screenshots.
Deduplicate: if a shared component (ErrorBoundary, Spinner, Button) was already questioned on a prior page, reference the prior answer instead of re-asking.

Question format:
{
  "question_id": "q{N}",
  "component": "ComponentName",
  "topic": "loading_state | error_state | empty_state | hover_state | responsive | animation | accessibility | edge_case | i18n",
  "question": "plain English question",
  "options": ["Option A", "Option B", "Option C", "I'll decide later"],
  "default": "Option A"
}

Standard questions to always include (unless already answered for this component):
- Loading: skeleton, spinner, or nothing while data loads?
- Error: inline message, toast, or full-page error on API failure?
- Empty: blank, placeholder message, CTA, or illustration when no data?
- Responsive: same structure on mobile, or different layout?
- Long content: truncate, wrap, or expand container?
- Disabled: can this component appear disabled? What does it look like?
- Accessibility: any ARIA label or keyboard nav change needed?
- i18n: any new strings that need Hebrew translation? (V1 supports English + Hebrew)

Maximum 12 questions per page. Prioritise shared components over page-specific ones.

Save as: docs/upgrade/gap-answers/{ROUTE_SLUG}.json

---

## CONTEXT

Route: {ROUTE}
Route slug: {ROUTE_SLUG}
Is new route: {true|false}
Screenshot files attached: {SCREENSHOT_FILE(S)}

API endpoints available to this page (backend contract — changes requiring data outside this list are BLOCKED):
{PASTE API ENDPOINTS FROM EXECUTION GUIDE ROW FOR THIS PAGE}

Current components on this page (from component-map.json):
- If component-map.json is in project knowledge: write "see component-map.json in project knowledge, route: {ROUTE}"
- If using Claude Code: paste the single JSON object where "route" == "{ROUTE}"
- For /cover-letters and /tailored-cvs: write "new route — no current entry. New page file required."

Current design tokens (tokens.css — paste the entire file, all 61 lines):
{PASTE FULL tokens.css}

Prior gap answers for shared components (paste if available):
{PASTE OR WRITE "none yet"}

---

## PROHIBITED
- Never assume a color hex — mark as "unknown" if not pixel-determinable from the PNG
- Never invent API fields — only flag if the UI clearly shows data absent from current API responses
- Never omit the "ambiguities" array even if empty
- Never combine multiple routes in one analysis
- Never answer the gap interview questions yourself
- Never write prose outside the two JSON objects

STOP: Output only the two JSON objects, labelled PART 1 and PART 2.
```

---

## Page-by-Page Execution Guide

Run in this order. Upload only the listed screenshots per conversation.

| # | Route | Route Slug | API Endpoints | Screenshots to Upload | New Route |
|---|-------|------------|--------------|----------------------|-----------|
| 1 | /dashboard | dashboard | `GET /jobs` `POST /jobs` `GET /users/me/usage` | `Dashboard View page.png` `Dashboard page-Account dropdown.png` `New Application Form.png` `New Application-Job Description textbox edit.png` `New Application Form-Choose Base CV Modal.png` | No |
| 2 | /applications | applications | `GET /jobs` | `Applications View page.png` | Yes — replaces redirect |
| 3 | /applications/[id] | application-hub | `GET /applications/{id}` (bundles all module artifact status) `GET /users/me/cv` `GET /jobs/{jobId}/gap-questions` `GET /vpr/{id}/status` (polling) `GET /cover-letter/{id}/status` (polling) `GET /interview-prep/{id}/status` (polling) `GET /cv-tailoring/{id}/status` (polling) | `Job Application Hub page-top.png` (VPR + cover letter sections) `Job Application Hub page-middle.png` (tailored CV + company research sections) `Job Application Hub page-bottom.png` (gap analysis + interview prep sections) | No |
| 4 | /applications/[id]/gap-analysis | gap-analysis | `GET /jobs/{jobId}/gap-questions` `POST /jobs/{jobId}/gap-questions` `POST /jobs/{jobId}/gap-responses` `GET /applications/{id}` `GET /users/me/cv` | `gap analysis questionnaire form.png` `gap analysis questionnaire form continued.png` `gap analysis questionnaire form question counter read state.png` `gap analysis questionnaire form-rich textbox edit.png` `gap analysis questionnaire form-rich textbox edit 2.png` | No |
| 5 | /cv-center | cv-center | `GET /users/me/cv` `POST /users/me/cv` | `Base CVs View page.png` `Base CV New Upload modal.png` | No |
| 6 | /cover-letters | cover-letters | `GET /cover-letters` | `Cover Letters View page.png` | Yes — new page + sidebar item |
| 7 | /tailored-cvs | tailored-cvs | `GET /cv-tailorings` | `Tailored CVs View page.png` | Yes — new page + sidebar item |
| 8 | /billing | billing | `POST /billing/checkout` `POST /billing/portal` `GET /users/me/subscription` `GET /users/me/usage` | `Billing page.png` `Billing page continued.png` `subscription plans page.png` `Subscription plan page 2.png` | No |
| 9 | /settings | settings | `GET /users/me` `PUT /users/me` `GET /users/me/subscription` | `Settings page-Account Settings.png` `Settings page.png` | No |

**Notes:**
- Start with #1 (dashboard) — most shared component changes, token changes, modal patterns
- Carry gap answers for shared components (ErrorBoundary, Spinner, Button) forward into each subsequent page — paste in "Prior gap answers" slot
- #6 and #7 (new routes) — AppSidebar.tsx will need new nav items; flag this in both specs
- #3 (application hub) — the three screenshots are divided by module section, not arbitrary scroll positions. Each section is the primary visual reference for how that module type's card renders within the hub. ModuleCard likely has per-module-type visual variants. Treat the diff analysis as covering: VPR card design, cover letter card design, tailored CV card design, company research card design, gap analysis card design, and interview prep card design — all within the same `/applications/[id]` page. Module status data comes from a single `GET /applications/{id}` response; the hub does NOT call `/vprs`, `/cover-letters`, etc. directly.
- #8 (billing) includes all 4 subscription plan screenshots — they are sections of the same `/billing` page, not a separate route
- API endpoints column = the backend contract for that page; any UI change requiring data outside this list is BLOCKED

---

## After Each Page

After receiving the diff analysis and gap questions:
1. Answer the gap interview questions (in the same conversation or a follow-up message)
2. Save the answers to `docs/upgrade/gap-answers/{route-slug}.json`
3. Note any shared-component answers to paste into subsequent pages
4. Move to the next page in the execution guide
