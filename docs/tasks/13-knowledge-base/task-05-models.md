# Task 13-KB-05: Knowledge Base Models

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P0 (Critical)
**Estimated Effort:** 1 hour
**Parent:** 13-knowledge-base/PLAN.md
**Depends On:** None (can start immediately)

---

## Objective

Define Pydantic models for Knowledge Base data structures.

## Requirements

1. [ ] Create `knowledge_base.py` in models folder
2. [ ] Define `RecurringTheme` model
3. [ ] Define `GapResponseRecord` model (for KB storage)
4. [ ] Define `Differentiator` model
5. [ ] Define `MemoryContext` model
6. [ ] Define `KnowledgeEntry` base model
7. [ ] Add validation rules
8. [ ] Add serialization helpers for DynamoDB

## Files Created

- `src/backend/careervp/models/knowledge_base.py`

## Model Definitions

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class KnowledgeType(str, Enum):
    RECURRING_THEME = "THEME"
    GAP_RESPONSE = "GAP"
    DIFFERENTIATOR = "DIFF"
    COMPANY_INSIGHT = "COMPANY"

class RecurringTheme(BaseModel):
    theme_id: str
    theme_text: str
    occurrence_count: int = 1
    first_seen: datetime
    last_seen: datetime
    related_questions: List[str] = Field(default_factory=list)
    weight: float = 1.0  # Higher = more important

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class GapResponseRecord(BaseModel):
    job_id: str
    question_id: str
    question_text: str
    response_text: str
    tag: str  # CV_IMPACT or INTERVIEW_ONLY
    priority: str  # CRITICAL, IMPORTANT, OPTIONAL
    created_at: datetime
    used_in_artifacts: List[str] = Field(default_factory=list)

class Differentiator(BaseModel):
    diff_id: str
    text: str
    category: str  # e.g., "technical", "leadership", "domain"
    usage_count: int = 0
    effectiveness_score: float = 0.0  # 0-1 based on success
    first_used: datetime
    last_used: datetime

class MemoryContext(BaseModel):
    recurring_themes: List[RecurringTheme] = Field(default_factory=list)
    recent_differentiators: List[Differentiator] = Field(default_factory=list)
    gap_response_count: int = 0
    applications_analyzed: int = 0
    last_updated: Optional[datetime] = None

class KnowledgeEntry(BaseModel):
    """Base model for DynamoDB storage"""
    pk: str  # USER#{email}
    sk: str  # KB#{type}#{id}
    data: dict
    applications_count: int = 0
    created_at: datetime
    updated_at: datetime
    ttl: Optional[int] = None
```

## Validation Checklist

- [ ] All models defined with Pydantic
- [ ] Type hints complete
- [ ] Serialization working for DynamoDB
- [ ] Validation rules in place
- [ ] JSON encoders for datetime

## Tests

- `tests/knowledge_base/unit/test_models.py`
