# Phase 3b — Gap Interview Record
**Model:** Sonnet
**When:** Same conversation as Phase 3, after you have answered the gap questions from PART 2

---

## How to Use

1. After receiving Phase 3 PART 2 (gap questions JSON), answer each question in plain text
2. Paste your answers into this prompt and send in the same conversation

---

## Prompt

```
ROLE: Spec data recorder consolidating gap interview answers for {ROUTE}.
OUTPUT: Two JSON objects. No prose.
TASK: Record the gap interview answers and extract shared-component answers for reuse.

## PART 1 — Gap Answers Record

Format each answer as:
{
  "question_id": "q{N}",
  "component": "ComponentName",
  "topic": "loading_state | error_state | empty_state | hover_state | responsive | animation | accessibility | edge_case | i18n",
  "question": "(copy question text)",
  "answer": "(user's answer)",
  "applies_to_shared_component": true | false
}

Save as: docs/upgrade/gap-answers/{ROUTE_SLUG}.json

## PART 2 — Shared Component Answers (carry-forward)

Extract only answers where applies_to_shared_component is true.
These apply to ErrorBoundary, Spinner, Button, ExportDropdown across all pages.

Format:
{
  "component": "ComponentName",
  "topic": "loading_state | error_state | ...",
  "answer": "(the answer)",
  "source_route": "{ROUTE}",
  "do_not_re-ask_on": ["list all routes this answer now covers"]
}

Save as: docs/upgrade/gap-answers/shared-components.json
(Append to existing file if it already exists — do not overwrite prior entries)

## USER ANSWERS

$ROUTE=/dashboard
$ROUTE_SLUG=dashboard

Route: {ROUTE}
Route slug: {ROUTE_SLUG}

{PASTE YOUR ANSWERS HERE — plain text, question by question}

## PROHIBITED
- Do not invent answers the user did not provide
- Do not mark anything as shared unless it is ErrorBoundary, Spinner, Button, or ExportDropdown
- Do not re-ask any question
- Do not write prose outside the two JSON objects

STOP: Output only the two JSON objects labelled PART 1 and PART 2.
```

---

## After Each Page

- Save PART 1 output → `docs/upgrade/gap-answers/{route-slug}.json`
- Save/append PART 2 output → `docs/upgrade/gap-answers/shared-components.json`
- In subsequent Phase 3 conversations, paste `shared-components.json` content into the "Prior gap answers" slot of the Phase 3 template prompt
