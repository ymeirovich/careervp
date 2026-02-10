# Task 13-KB-06: Knowledge Base Unit Tests

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P0 (Critical)
**Estimated Effort:** 1.5 hours
**Parent:** 13-knowledge-base/PLAN.md
**Depends On:** task-02, task-03, task-05

---

## Objective

Create comprehensive unit tests for Knowledge Base components.

## Requirements

1. [ ] Create test directory structure
2. [ ] Test all repository methods
3. [ ] Test all logic layer methods
4. [ ] Test model validation
5. [ ] Test error handling paths
6. [ ] Add fixtures for common test data
7. [ ] Mock DynamoDB for repository tests

## Directory Structure

```
tests/knowledge_base/
├── __init__.py
├── conftest.py
├── unit/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_repository.py
│   └── test_logic.py
└── integration/
    ├── __init__.py
    └── test_gap_integration.py
```

## Test Cases

### test_models.py

```python
def test_recurring_theme_validation():
    """Theme requires theme_text and theme_id"""

def test_recurring_theme_serialization():
    """Theme serializes datetime correctly for DynamoDB"""

def test_memory_context_defaults():
    """MemoryContext has correct default values"""

def test_knowledge_entry_pk_format():
    """pk follows USER#{email} pattern"""
```

### test_repository.py

```python
def test_save_recurring_theme_success():
    """Theme saved with correct pk/sk"""

def test_get_recurring_themes_empty():
    """Returns empty list for new user"""

def test_get_recurring_themes_returns_all():
    """Returns all themes for user"""

def test_save_gap_responses_success():
    """Gap responses saved correctly"""

def test_get_gap_responses_by_job():
    """Returns responses for specific job"""

def test_increment_usage_count():
    """Usage count increments atomically"""
```

### test_logic.py

```python
def test_extract_recurring_themes_identifies_patterns():
    """3+ same questions = recurring theme"""

def test_extract_recurring_themes_weights_recency():
    """Recent themes weighted higher"""

def test_get_memory_context_aggregates_all():
    """Returns combined themes, diffs, counts"""

def test_merge_differentiators_deduplicates():
    """Similar differentiators merged"""

def test_update_after_application_persists():
    """All data persisted after application"""
```

## Fixtures (conftest.py)

```python
@pytest.fixture
def sample_recurring_theme():
    return RecurringTheme(
        theme_id="theme-001",
        theme_text="Experience with Python and AWS",
        occurrence_count=5,
        first_seen=datetime.now() - timedelta(days=30),
        last_seen=datetime.now(),
        related_questions=["What is your Python experience?"],
        weight=1.5
    )

@pytest.fixture
def mock_dynamodb():
    with mock_dynamodb():
        yield create_test_table()

@pytest.fixture
def kb_repository(mock_dynamodb):
    return KnowledgeBaseRepository(table_name="test-kb")
```

## Validation Checklist

- [ ] All test files created
- [ ] Repository tests with mocked DynamoDB
- [ ] Logic tests with mocked repository
- [ ] Model validation tests
- [ ] Error handling tests
- [ ] All 11+ tests passing

## Tests to Create

| Test File | Test Count | Coverage |
|-----------|------------|----------|
| test_models.py | 4 | Models |
| test_repository.py | 6 | DAL |
| test_logic.py | 5 | Business logic |
| **Total** | **15+** | |
