# Phase 1 — Screenshot Manifest

Upload all 24 screenshots alongside this prompt, then send the following:

---

ROLE: UI inventory analyst cataloguing redesign screenshots for a Next.js application.
OUTPUT: JSON array saved as `docs/upgrade/screenshot-manifest.json`. No prose.
TASK: Produce one manifest entry per UNIQUE ROUTE (not per file). Group multi-screenshot pages into a single entry.

## Grouping Rules

Multi-file pages — treat as ONE entry:
- `Dashboard View page.png` + `Dashboard page-Account dropdown.png` → route: /dashboard
- `New Application Form.png` + `New Application-Job Description textbox edit.png` + `New Application Form-Choose Base CV Modal.png` → route: /dashboard (modal group)
- `Job Application Hub page-top.png` + `Job Application Hub page-middle.png` + `Job Application Hub page-bottom.png` → route: /applications/[id]
- `gap analysis questionnaire form.png` + all 4 variants → route: /applications/[id]/gap-analysis
- `Billing page.png` + `Billing page continued.png` + `subscription plans page.png` + `Subscription plan page 2.png` → route: /billing (all four are sections of one long billing page)
- `Settings page-Account Settings.png` + `Settings page.png` → route: /settings

Single-file pages — one entry each:
- `Applications View page.png` → route: /applications
- `Base CVs View page.png` + `Base CV New Upload modal.png` → route: /cv-center
- `Cover Letters View page.png` → route: /cover-letters (NEW — no current route)
- `Tailored CVs View page.png` → route: /tailored-cvs (NEW — no current route)

## Entry Format

```json
{
  "route": "/route-path",
  "page_title": "human-readable name",
  "screenshot_files": ["filename1.png", "filename2.png"],
  "screenshot_count": 2,
  "is_new_route": false,
  "visible_states": ["default", "interactive", "modal", "edit", "scroll-continuation"],
  "sidebar_change_required": false,
  "components_visually_present": ["list any recognisable component names"],
  "notes": "anything ambiguous or route-TBD"
}
```

## Known New Routes (flag these)
- `/applications` — replacing current redirect-only page; backend: `GET /jobs`
- `/cover-letters` — no existing page file, new sidebar item required; backend: `GET /cover-letters` (exists)
- `/tailored-cvs` — no existing page file, new sidebar item required; backend: `GET /cv-tailorings` (exists)
- Subscription plans screenshots belong to `/billing` — not a separate route

## PROHIBITED
- Do not open or analyse image content
- Do not infer component details from the screenshots in this phase
- Do not write prose explanations
- Do not create one entry per screenshot file — group by route

STOP: Output only the JSON array.
