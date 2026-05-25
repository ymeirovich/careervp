# Phase 4 — Backend Contract Verification
**Model:** Sonnet
**When:** One conversation, after ALL Phase 3 diff analyses are complete
**Input files:** All `docs/upgrade/diff-analysis/*.json` + Swagger spec

---

## How to Use

1. Open a new conversation
2. Paste the prompt below
3. Paste the content of every `diff-analysis/*.json` file
4. Paste the Swagger path list (see bottom of this file)

---

## Prompt

```
ROLE: Backend contract enforcement agent.
OUTPUT: JSON object saved as docs/upgrade/contract-verification.json. No prose.

TASK: Review all diff analysis files and classify every component_change entry
by whether it can be satisfied with existing API endpoints.

For each component_change where backend_available is "no" or "unknown":
1. Check if the required data exists in a different field of the listed endpoint response
2. Check if it can be derived or computed from existing response data
3. If neither — mark as BLOCKED

Classification rules:
- "yes"     → data is in the existing endpoint response for that route
- "derived" → data can be computed from existing fields (specify how)
- "blocked" → requires new API endpoint (OUT OF SCOPE for this upgrade)
- "cosmetic" → change is visual only (color, spacing, typography) — always "yes"

Output format:
{
  "verified_at": "{date}",
  "summary": {
    "total_component_changes": 0,
    "yes": 0,
    "derived": 0,
    "blocked": 0,
    "cosmetic": 0
  },
  "results": [
    {
      "route": "/route",
      "component": "ComponentName",
      "change_type": "modify | replace | remove | new",
      "backend_classification": "yes | derived | blocked | cosmetic",
      "resolution": "plain English — which field, or how derived, or why blocked",
      "in_scope": true
    }
  ],
  "blocked_items": [
    {
      "route": "/route",
      "component": "ComponentName",
      "reason": "requires endpoint that does not exist in Swagger"
    }
  ]
}

## API CONTRACT (Swagger endpoints — treat as the complete backend surface)

GET      /applications/{application_id}
POST     /auth/login
POST     /auth/refresh
POST     /auth/register
POST     /billing/checkout
POST     /billing/portal
POST     /billing/webhook
POST     /company-research/fetch
GET      /company-research/{jobId}
POST     /cover-letter/generate
GET      /cover-letter/{coverLetterId}/status
GET      /cover-letters
POST     /cv-tailoring/generate
DELETE   /cv-tailoring/{cvTailoringId}
GET      /cv-tailoring/{cvTailoringId}/status
GET      /cv-tailorings
POST     /gap-analysis/questions
GET      /health
POST     /interview-prep/generate
GET      /interview-prep/{interviewPrepId}/status
GET      /interview-preps
GET      /jobs
POST     /jobs
GET      /jobs/{jobId}
GET      /jobs/{jobId}/gap-questions
POST     /jobs/{jobId}/gap-questions
POST     /jobs/{jobId}/gap-responses
GET      /knowledge-base
GET      /users/me
PUT      /users/me
GET      /users/me/cv
POST     /users/me/cv
GET      /users/me/subscription
POST     /users/me/trial/reset
GET      /users/me/usage
POST     /vpr/generate
GET      /vpr/{vprId}/status
GET      /vprs

Any UI change requiring an endpoint NOT in this list is BLOCKED.

## DIFF ANALYSIS INPUT

{PASTE ALL diff-analysis/*.json FILES HERE}

## PROHIBITED
- Do not suggest adding new API endpoints
- Do not mark "derived" without specifying exactly which field and the derivation logic
- Do not mark cosmetic changes as anything other than "yes"
- Do not leave backend_classification as "unknown"
- Do not write prose outside the JSON object

STOP: Output only the JSON object.
```
