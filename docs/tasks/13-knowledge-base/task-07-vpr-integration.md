# Task 13-KB-07: VPR Knowledge Base Integration

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P1 (High)
**Estimated Effort:** 1 hour
**Parent:** 13-knowledge-base/PLAN.md
**Depends On:** task-03-logic-layer.md, JSA-VPR-001

---

## Objective

Integrate Knowledge Base with VPR Generator to persist and reuse differentiators.

## Requirements

1. [ ] Import KnowledgeBaseService in vpr_handler.py
2. [ ] Retrieve existing differentiators before VPR generation
3. [ ] Pass differentiators to VPR prompt for consistency
4. [ ] Extract new differentiators from generated VPR
5. [ ] Save/merge differentiators to Knowledge Base after generation
6. [ ] Add `{existing_differentiators}` placeholder to prompt

## Files Modified

- `src/backend/careervp/handlers/vpr_handler.py`
- `src/backend/careervp/logic/vpr_generator.py`
- `src/backend/careervp/logic/prompts/vpr_prompt.py`

## Integration Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ VPR Handler │────▶│ KB Service   │────▶│ Get Existing    │
│             │     │              │     │ Differentiators │
└─────────────┘     └──────────────┘     └─────────────────┘
       │                                          │
       ▼                                          ▼
┌─────────────┐                          ┌─────────────────┐
│ VPR Prompt  │◀─────────────────────────│ Include in      │
│ Stage 2     │                          │ Candidate       │
│             │                          │ Analysis        │
└─────────────┘                          └─────────────────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ VPR Output  │────▶│ Extract New  │────▶│ Merge & Save    │
│             │     │ Differentiators│   │ to KB           │
└─────────────┘     └──────────────┘     └─────────────────┘
```

## Prompt Template Changes

```python
# Add to vpr_prompt.py Stage 2

EXISTING_DIFFERENTIATORS_SECTION = """
### Candidate's Established Differentiators

The candidate has previously identified these core differentiators:
{existing_differentiators}

Consider incorporating these into your analysis where relevant.
Identify any NEW differentiators specific to this role.
"""
```

## Differentiator Extraction

After VPR generation, extract differentiators from Stage 2 output:

```python
def extract_differentiators(vpr_output: str) -> List[Differentiator]:
    """
    Parse VPR Stage 2 to extract:
    - "3-5 core differentiators" section
    - Any unique value propositions mentioned
    """
    ...
```

## Validation Checklist

- [ ] VPR handler retrieves existing differentiators
- [ ] Differentiators included in Stage 2 prompt
- [ ] New differentiators extracted from output
- [ ] Differentiators merged and saved
- [ ] Usage count incremented for reused differentiators

## Tests

- `tests/knowledge_base/integration/test_vpr_integration.py`
