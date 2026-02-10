# Task 13-KB-03: Knowledge Base Logic Layer

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P0 (Critical)
**Estimated Effort:** 2 hours
**Parent:** 13-knowledge-base/PLAN.md
**Depends On:** task-02-repository-layer.md

---

## Objective

Create the business logic layer for Knowledge Base operations with higher-level abstractions.

## Requirements

1. [ ] Create `knowledge_base.py` in logic folder
2. [ ] Implement `extract_recurring_themes(gap_responses)` - analyzes patterns
3. [ ] Implement `get_memory_context(user_email)` - returns combined context
4. [ ] Implement `update_after_application(user_email, job_id, artifacts)` - persists learnings
5. [ ] Implement `get_gap_history(user_email, limit)` - returns recent gap responses
6. [ ] Implement `merge_differentiators(existing, new)` - deduplicates and ranks
7. [ ] Add caching layer for frequently accessed data (optional)
8. [ ] Integrate with existing DAL patterns

## Files Created

- `src/backend/careervp/logic/knowledge_base.py`

## Interface Definition

```python
from dataclasses import dataclass
from typing import List, Optional
from careervp.models.knowledge_base import (
    RecurringTheme, GapResponse, Differentiator, MemoryContext
)
from careervp.utils.result import Result

@dataclass
class MemoryContext:
    recurring_themes: List[RecurringTheme]
    recent_differentiators: List[Differentiator]
    gap_response_count: int
    applications_analyzed: int

class KnowledgeBaseService:
    def __init__(self, repository: KnowledgeBaseRepository):
        self.repository = repository

    def get_memory_context(
        self, user_email: str
    ) -> Result[MemoryContext]:
        """Get combined memory context for memory-aware features"""
        ...

    def extract_recurring_themes(
        self, gap_responses: List[GapResponse]
    ) -> List[RecurringTheme]:
        """Analyze gap responses to identify patterns"""
        ...

    def update_after_application(
        self, user_email: str, job_id: str, artifacts: dict
    ) -> Result[None]:
        """Persist learnings after completing an application"""
        ...
```

## Business Logic

### Theme Extraction Rules

1. If same gap question answered 3+ times → recurring theme
2. If differentiator used in 5+ VPRs → core differentiator
3. Themes decay after 30 days without reinforcement

### Memory Context Priority

1. Themes used in last 7 days (highest weight)
2. Core differentiators (always included)
3. Recent gap responses (last 5 applications)

## Validation Checklist

- [ ] All methods implemented
- [ ] Theme extraction logic correct
- [ ] Memory context aggregation working
- [ ] Integration with repository layer
- [ ] Type hints complete

## Tests

- `tests/knowledge_base/unit/test_logic.py`
