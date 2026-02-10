# Task 13-KB-04: Gap Analysis Knowledge Base Integration

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P0 (Critical)
**Estimated Effort:** 1.5 hours
**Parent:** 13-knowledge-base/PLAN.md
**Depends On:** task-03-logic-layer.md

---

## Objective

Integrate Knowledge Base with Gap Analysis for memory-aware questioning.

## Requirements

1. [ ] Import KnowledgeBaseService in gap_handler.py
2. [ ] Retrieve recurring_themes before generating questions
3. [ ] Pass recurring_themes to gap analysis prompt
4. [ ] Update gap_analysis_prompt.py to use recurring themes
5. [ ] Skip questions already answered in previous applications
6. [ ] Save gap responses to Knowledge Base after submission
7. [ ] Add `{recurring_themes}` placeholder to prompt template

## Files Modified

- `src/backend/careervp/handlers/gap_handler.py`
- `src/backend/careervp/logic/prompts/gap_analysis_prompt.py`
- `src/backend/careervp/logic/gap_analysis.py`

## Integration Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ Gap Handler │────▶│ KB Service   │────▶│ Get Recurring   │
│             │     │              │     │ Themes          │
└─────────────┘     └──────────────┘     └─────────────────┘
       │                                          │
       │                                          ▼
       │                                 ┌─────────────────┐
       │                                 │ Memory Context  │
       │                                 │ {themes, diffs} │
       │                                 └────────┬────────┘
       │                                          │
       ▼                                          ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ Gap Prompt  │◀────│ Include      │◀────│ Filter Already  │
│ with Memory │     │ Themes       │     │ Answered        │
└─────────────┘     └──────────────┘     └─────────────────┘
```

## Prompt Template Changes

```python
# Add to gap_analysis_prompt.py

MEMORY_AWARENESS_SECTION = """
## User Memory Context

The user has previously provided responses to gap analysis questions.

### Recurring Themes (DO NOT ask again):
{recurring_themes}

### Previously Answered Questions to Skip:
{previous_question_topics}

Generate NEW questions that explore areas NOT covered by the above context.
"""
```

## Validation Checklist

- [ ] Gap handler retrieves memory context
- [ ] Prompt includes recurring themes
- [ ] Previously answered questions skipped
- [ ] Gap responses saved after submission
- [ ] Integration tests passing

## Tests

- `tests/jsa_skill_alignment/test_gap_analysis_alignment.py::test_gap_has_memory_awareness`
- `tests/knowledge_base/integration/test_gap_integration.py`
