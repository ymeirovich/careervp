# Task 06: DAL Extensions (Optional for Phase 11)

## Overview

**NOTE:** Phase 11 returns results immediately (synchronous), so DAL extensions for gap storage are **optional**.

If you want to persist gap analysis results for historical tracking:
- Add methods to store gap analysis artifacts in DynamoDB
- Follow existing VPR artifact storage pattern

**Files to modify:**
- `src/backend/careervp/dal/dynamo_dal_handler.py` (optional extensions)

**Dependencies:** None
**Estimated time:** 1 hour (if implemented)
**Tests:** `tests/gap-analysis/integration/test_gap_dal.py`

---

## Decision Point

**Option A: Skip DAL storage (simpler)**
- Gap analysis results returned immediately, not stored
- No persistence overhead
- Simpler implementation
- **Recommended for Phase 11**

**Option B: Add DAL storage (future-proof)**
- Store gap analysis results in DynamoDB
- Enable historical tracking
- Pattern ready for async migration
- Requires additional code

---

## Implementation (Option B - If Chosen)

### Add to: `src/backend/careervp/dal/dynamo_dal_handler.py`

```python
def save_gap_analysis(
    self,
    user_id: str,
    cv_id: str,
    job_posting_id: str,
    questions: list[dict],
    version: int = 1
) -> Result[None]:
    """
    Save gap analysis artifact to DynamoDB.

    Storage pattern:
    pk = {application_id or user_id}
    sk = ARTIFACT#GAP#{cv_id}#{job_posting_id}#v{version}

    Args:
        user_id: User identifier
        cv_id: CV identifier
        job_posting_id: Job posting identifier
        questions: Generated gap questions
        version: Artifact version

    Returns:
        Result[None] indicating success or failure
    """
    try:
        item = {
            'pk': user_id,
            'sk': f'ARTIFACT#GAP#{cv_id}#{job_posting_id}#v{version}',
            'artifact_type': 'gap_analysis',
            'user_id': user_id,
            'cv_id': cv_id,
            'job_posting_id': job_posting_id,
            'questions': questions,
            'version': version,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'ttl': int((datetime.now(timezone.utc) + timedelta(days=90)).timestamp())
        }

        self.table.put_item(Item=item)

        return Result(
            success=True,
            code=ResultCode.GAP_RESPONSES_SAVED
        )

    except Exception as e:
        return Result(
            success=False,
            error=f"Failed to save gap analysis: {str(e)}",
            code=ResultCode.INTERNAL_ERROR
        )


def get_gap_analysis(
    self,
    user_id: str,
    cv_id: str,
    job_posting_id: str,
    version: int = 1
) -> Result[dict]:
    """
    Retrieve gap analysis artifact from DynamoDB.

    Args:
        user_id: User identifier
        cv_id: CV identifier
        job_posting_id: Job posting identifier
        version: Artifact version

    Returns:
        Result[dict] with gap analysis data
    """
    try:
        response = self.table.get_item(
            Key={
                'pk': user_id,
                'sk': f'ARTIFACT#GAP#{cv_id}#{job_posting_id}#v{version}'
            }
        )

        if 'Item' not in response:
            return Result(
                success=False,
                error="Gap analysis not found",
                code=ResultCode.NOT_FOUND
            )

        return Result(
            success=True,
            data=response['Item'],
            code=ResultCode.SUCCESS
        )

    except Exception as e:
        return Result(
            success=False,
            error=f"Failed to retrieve gap analysis: {str(e)}",
            code=ResultCode.INTERNAL_ERROR
        )
```

---

## If Implementing DAL Storage

### Update handler to save results

In `gap_handler.py`, after generating questions:

```python
# Optional: Save to DynamoDB for historical tracking
save_result = dal.save_gap_analysis(
    user_id=request.user_id,
    cv_id=request.cv_id,
    job_posting_id=request.job_posting.source_url or "manual",
    questions=[q.model_dump() for q in response.questions]
)

if not save_result.success:
    logger.warning(f"Failed to save gap analysis: {save_result.error}")
```

---

## Verification Commands (If Implemented)

```bash
cd src/backend

# Unit tests
uv run pytest tests/gap-analysis/integration/test_gap_dal.py -v

# Expected: All DAL tests pass
```

---

## Acceptance Criteria (If Implemented)

- [ ] `save_gap_analysis()` stores gap artifacts in DynamoDB
- [ ] `get_gap_analysis()` retrieves gap artifacts
- [ ] Storage pattern follows existing artifact conventions
- [ ] TTL set to 90 days
- [ ] Error handling for DynamoDB errors
- [ ] DAL tests pass

---

## Recommendation

**For Phase 11: Skip DAL storage (Option A)**
- Return results immediately without persistence
- Simpler, faster implementation
- Can add storage in future phases if needed

**If storage is needed later:**
- This task file provides the implementation pattern
- Easy to add without breaking existing functionality

---

## Commit Message (If Implemented)

```bash
git add src/backend/careervp/dal/dynamo_dal_handler.py
git commit -m "feat(gap-analysis): add DAL methods for gap storage

- Add save_gap_analysis() for artifact persistence
- Add get_gap_analysis() for retrieval
- Follow existing artifact storage pattern
- Set 90-day TTL for gap analysis artifacts
- All DAL tests pass (8/8)

Optional enhancement for historical tracking.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```
