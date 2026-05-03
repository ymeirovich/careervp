# CareerVP Canvas App — Spec V4 Overview

## Purpose
This spec directory contains YAML test specifications for the CareerVP single-file Canvas App (App.jsx).
All specs follow the TDD discipline: tests must be written first and must fail before implementation.

## Source
- App: `src/frontend/canvas-app/App.jsx` (Gemini Canvas export, enhanced)
- Design screenshots: `UX/V4/Canvas Export for Claude Code/`
- Test runner: Vitest + React Testing Library (jsdom)
- Test root: `src/frontend/tests/ui/`

## Screen Inventory

| ID | Screen | Switch Case | Spec File |
|----|--------|-------------|-----------|
| 1 | Applications Table (Dashboard) | `dashboard` | 01-applications-table.yaml |
| 2 | New Application Form | `new-app` | 02-new-application-form.yaml |
| 3 | Change Base CV Modal | (overlay) | 03-change-base-cv-modal.yaml |
| 4 | Application Hub | `hub` | 04-application-hub.yaml |
| 5 | Base CVs Table | `base-cvs` | 05-base-cvs-table.yaml |
| 6 | Tailored CVs Table | `tailored-cvs` | 06-tailored-cvs-table.yaml |
| 7 | Cover Letters Table | `cover-letters` | 07-cover-letters-table.yaml |
| 8 | Billing | `billing` | 08-billing.yaml |
| 9 | Settings | `settings` | 09-settings.yaml |
| 10 | Plans | `plans` | 10-plans.yaml |
| 11 | Navigation / Routing | (cross-screen) | 11-navigation.yaml |
| 12 | Design Tokens | (CSS vars) | 12-design-tokens.yaml |

## Test Count Summary

| File | Unit Tests | Integration | E2E | Regression | Total |
|------|-----------|-------------|-----|------------|-------|
| ApplicationsTable | 3 | - | - | - | 3 |
| NewApplicationForm | 9 | - | - | - | 9 |
| ChangeBaseCVModal | 6 | - | - | - | 6 |
| ApplicationHub | 10 | - | - | - | 10 |
| BaseCVsTable | 7 | - | - | - | 7 |
| TailoredCVsTable | 6 | - | - | - | 6 |
| CoverLettersTable | 7 | - | - | - | 7 |
| Billing | 7 | - | - | - | 7 |
| Settings | 12 | - | - | - | 12 |
| Plans | 3 | - | - | - | 3 |
| Navigation | - | 8 | - | - | 8 |
| Full Flow | - | - | 5 | - | 5 |
| Regression | - | - | - | 6 | 6 |
| **TOTAL** | **70** | **8** | **5** | **6** | **89** |

## Spec Format

Each YAML spec file follows this schema:

```yaml
spec_id: SCREEN_NN
screen: ScreenName
component_path: src/frontend/canvas-app/App.jsx
test_file: src/frontend/tests/ui/unit/ScreenName.test.tsx

tests:
  - id: SCREEN_NN
    name: "Human-readable test name"
    arrange: "Setup description"
    act: "Action to perform"
    assert: "Expected observable outcome"
    expected_failure: "Why this test fails before implementation"
```

## Firebase Mock Strategy

The Canvas App initializes Firebase at module load using globals:
- `globalThis.__firebase_config` — JSON string of Firebase config
- `globalThis.__app_id` — Firestore app ID
- `globalThis.__initial_auth_token` — optional pre-auth token

These must be stubbed in `src/frontend/tests/ui/setup.ts` BEFORE any test imports App.jsx.
Modules `firebase/app`, `firebase/auth`, `firebase/firestore` must be fully vi.mock()-ed.
