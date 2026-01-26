# Task 02: VPR DAL Methods

**Status:** Pending
**Spec Reference:** [[docs/specs/03-vpr-generator.md]]
**Depends On:** Task 01 (Models)

## Overview

Add VPR persistence methods to `DynamoDalHandler` following the existing CV patterns. VPR uses Single Table Design with `PK=applicationId`, `SK=ARTIFACT#VPR#v{version}`.

## Todo

### DAL Method Implementation

- [ ] Add `save_vpr(vpr: VPR) -> None` method to `careervp/dal/dynamo_dal_handler.py`.
- [ ] Add `get_vpr(application_id: str, version: int | None = None) -> VPR | None` method.
- [ ] Add `get_latest_vpr(application_id: str) -> VPR | None` method.
- [ ] Add `list_vprs(user_id: str) -> list[VPR]` method (via GSI query).

### Abstract Base Class Update

- [ ] Add VPR method signatures to `careervp/dal/db_handler.py` (DalHandler ABC).

### Validation

- [ ] Run `uv run ruff format src/backend/careervp/dal/`.
- [ ] Run `uv run ruff check --fix src/backend/careervp/dal/`.
- [ ] Run `uv run mypy src/backend/careervp/dal/dynamo_dal_handler.py --strict`.

### Commit

- [ ] Commit with message: `feat(vpr): add VPR DAL methods to DynamoDalHandler`.

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/dal/dynamo_dal_handler.py` | Add VPR methods |
| `src/backend/careervp/dal/db_handler.py` | Add abstract signatures |
| `src/backend/tests/unit/test_dynamo_dal_handler.py` | Unit tests with moto |

### Key Implementation Details

```python
# DynamoDB Key Schema for VPR
# PK: application_id (e.g., "app-uuid-123")
# SK: "ARTIFACT#VPR#v{version}" (e.g., "ARTIFACT#VPR#v1")
# GSI: user_id (for list_vprs query)

# Import VPR model
from careervp.models.vpr import VPR

@tracer.capture_method(capture_response=False)
def save_vpr(self, vpr: VPR) -> None:
    """
    Save VPR to DynamoDB.
    PK=application_id, SK=ARTIFACT#VPR#v{version}
    """
    logger.append_keys(application_id=vpr.application_id)
    logger.info('saving VPR to DynamoDB')
    try:
        table: Table = self._get_db_handler(self.table_name)
        item = vpr.model_dump(mode='json')  # Serialize datetime
        item['pk'] = vpr.application_id
        item['sk'] = f'ARTIFACT#VPR#v{vpr.version}'
        item['user_id'] = vpr.user_id  # For GSI queries
        table.put_item(Item=item)
    except (ClientError, ValidationError) as exc:
        error_msg = 'failed to save VPR'
        logger.exception(error_msg, application_id=vpr.application_id)
        raise InternalServerException(error_msg) from exc

    logger.info('VPR saved successfully', application_id=vpr.application_id)
```

### Result Pattern Enforcement

This DAL layer raises `InternalServerException` on failure (following existing CV pattern). The logic layer wraps calls in try/except and returns `Result[VPR]`.

```python
# Logic layer usage example:
try:
    dal.save_vpr(vpr)
    return Result(success=True, data=vpr, code=ResultCode.VPR_GENERATED)
except InternalServerException as e:
    return Result(success=False, error=str(e), code=ResultCode.DYNAMODB_ERROR)
```

### Pytest Commands

```bash
# Run DAL unit tests
cd src/backend && uv run pytest tests/unit/test_dynamo_dal_handler.py -v

# Run with coverage
cd src/backend && uv run pytest tests/unit/test_dynamo_dal_handler.py -v --cov=careervp/dal
```

### Zero-Hallucination Checklist

- [ ] No FVS fields in DAL layer (DAL is pure persistence).
- [ ] VPR model fields are passed through unchanged.
- [ ] datetime serialization uses `model_dump(mode='json')`.

### Acceptance Criteria

- [ ] All 4 DAL methods implemented and pass mypy --strict.
- [ ] Unit tests with moto mock DynamoDB operations.
- [ ] Zero ruff/mypy errors.
