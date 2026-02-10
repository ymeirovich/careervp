# Task 13-KB-02: Knowledge Base Repository Layer

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P0 (Critical)
**Estimated Effort:** 2 hours
**Parent:** 13-knowledge-base/PLAN.md
**Depends On:** task-01-dynamodb-table.md

---

## Objective

Create the repository layer for Knowledge Base CRUD operations.

## Requirements

1. [ ] Create `knowledge_base_repository.py`
2. [ ] Implement `save_recurring_theme(user_email, theme_data)` method
3. [ ] Implement `get_recurring_themes(user_email)` method
4. [ ] Implement `save_gap_responses(user_email, job_id, responses)` method
5. [ ] Implement `get_gap_responses(user_email, job_id)` method
6. [ ] Implement `save_differentiators(user_email, differentiators)` method
7. [ ] Implement `get_differentiators(user_email)` method
8. [ ] Implement `increment_usage_count(pk, sk)` method
9. [ ] Add proper error handling with Result[T] pattern
10. [ ] Add logging with AWS Powertools

## Files Created

- `src/backend/careervp/dal/knowledge_base_repository.py`

## Interface Definition

```python
from typing import Protocol, List, Optional
from careervp.models.knowledge_base import (
    RecurringTheme, GapResponse, Differentiator
)
from careervp.utils.result import Result

class KnowledgeBaseRepository(Protocol):
    def save_recurring_theme(
        self, user_email: str, theme: RecurringTheme
    ) -> Result[None]: ...

    def get_recurring_themes(
        self, user_email: str
    ) -> Result[List[RecurringTheme]]: ...

    def save_gap_responses(
        self, user_email: str, job_id: str, responses: List[GapResponse]
    ) -> Result[None]: ...

    def get_gap_responses(
        self, user_email: str, job_id: str
    ) -> Result[List[GapResponse]]: ...

    def save_differentiators(
        self, user_email: str, differentiators: List[Differentiator]
    ) -> Result[None]: ...

    def get_differentiators(
        self, user_email: str
    ) -> Result[List[Differentiator]]: ...
```

## Validation Checklist

- [ ] All 6 CRUD methods implemented
- [ ] Result[T] pattern used for error handling
- [ ] Powertools logging configured
- [ ] DynamoDB key patterns correct (pk/sk)
- [ ] Type hints complete

## Tests

- `tests/knowledge_base/unit/test_repository.py`
