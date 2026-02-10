# Task 13-KB-08: CV Tailoring Knowledge Base Integration

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P1 (High)
**Estimated Effort:** 1 hour
**Parent:** 13-knowledge-base/PLAN.md
**Depends On:** task-03-logic-layer.md, JSA-CVT-001

---

## Objective

Integrate Knowledge Base with CV Tailoring to use gap responses marked as [CV IMPACT].

## Requirements

1. [ ] Import KnowledgeBaseService in cv_tailoring_handler.py
2. [ ] Retrieve gap responses for current job
3. [ ] Filter for [CV IMPACT] tagged responses
4. [ ] Pass CV-relevant gap responses to tailoring prompt
5. [ ] Add `{cv_impact_responses}` placeholder to prompt
6. [ ] Track which responses were used in CV

## Files Modified

- `src/backend/careervp/handlers/cv_tailoring_handler.py`
- `src/backend/careervp/logic/cv_tailoring_logic.py`
- `src/backend/careervp/logic/cv_tailoring_prompt.py`

## Integration Flow

```
┌──────────────┐     ┌──────────────┐     ┌─────────────────┐
│ CV Handler   │────▶│ KB Service   │────▶│ Get Gap         │
│              │     │              │     │ Responses       │
└──────────────┘     └──────────────┘     └─────────────────┘
       │                                          │
       │                                          ▼
       │                                 ┌─────────────────┐
       │                                 │ Filter          │
       │                                 │ [CV IMPACT]     │
       │                                 └────────┬────────┘
       │                                          │
       ▼                                          ▼
┌──────────────┐     ┌──────────────┐     ┌─────────────────┐
│ CV Prompt    │◀────│ Include      │◀────│ CV-Relevant     │
│ STEP 1       │     │ Responses    │     │ Gap Answers     │
└──────────────┘     └──────────────┘     └─────────────────┘
```

## Gap Response Usage

Gap responses tagged [CV IMPACT] should inform:
- Bullet point content
- Achievement quantification
- Skill emphasis

```python
# Filter for CV-relevant responses
cv_responses = [
    r for r in gap_responses
    if r.tag == "CV_IMPACT"
]
```

## Prompt Template Changes

```python
# Add to cv_tailoring_prompt.py

CV_IMPACT_SECTION = """
### Gap Analysis Insights for CV

The candidate provided the following relevant context:

{cv_impact_responses}

Use these insights to:
1. Strengthen bullet points with specific examples
2. Quantify achievements where data is provided
3. Emphasize skills aligned with identified gaps
"""
```

## Validation Checklist

- [ ] CV handler retrieves gap responses
- [ ] Only [CV IMPACT] responses included
- [ ] Responses formatted for prompt
- [ ] Integration tested end-to-end
- [ ] Response usage tracked in KB

## Tests

- `tests/knowledge_base/integration/test_cv_integration.py`
