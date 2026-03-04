# Codex Prompt: CV Tailoring - Fix ID Format and Add Delete Endpoint

## Context

Two issues with CV Tailoring:

1. **ID Format Bug**: List endpoint returns full DynamoDB sort key as ID
2. **Missing Delete Endpoint**: No way to delete CV tailorings

## Issue 1: ID Format Bug

### Current Behavior

```
GET /cv-tailorings
Response:
{
  "tailored_cvs": [
    {
      "id": "ARTIFACT#CV_TAILORED#cv-tail-8d5a9e29-01ea-4618-933c-518a4d6dbb64",  # Full SK
      "status": "completed",
      "cv_id": "...",
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

### Expected Behavior

```
{
  "tailored_cvs": [
    {
      "id": "cv-tail-8d5a9e29-01ea-4618-933c-518a4d6dbb64",  # Just the UUID
      ...
    }
  ]
}
```

## Issue 2: Missing Delete Endpoint

### Current Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/cv-tailoring/generate` | Create new CV tailoring |
| GET | `/cv-tailoring/{id}/status` | Get tailoring status |
| GET | `/cv-tailorings` | List all tailorings |

### Needed

| Method | Endpoint | Description |
|--------|----------|-------------|
| DELETE | `/cv-tailoring/{id}` | Delete a CV tailoring |

## Your Task

### 1. Fix the ID Format Bug

Read `src/backend/careervp/handlers/cv_tailoring_handler.py` and find `_build_tailored_cv_list_item` function (around line 532).

Current code:
```python
def _build_tailored_cv_list_item(item: dict[str, Any]):
    sk = item.get('sk', '')
    return {
        'id': str(sk or ''),  # Returns full SK
```

Fix to extract just the UUID:
```python
def _build_tailored_cv_list_item(item: dict[str, Any]):
    sk = item.get('sk', '')
    # Extract just the UUID after the prefix
    cv_tailoring_id = sk.replace('ARTIFACT#CV_TAILORED#', '') if sk else ''
    return {
        'id': cv_tailoring_id,
```

### 2. Add Delete Endpoint

Implement a new handler function and wire it up to API Gateway.

**Handler function:**
```python
def delete_tailored_cv(event: dict[str, Any]) -> dict[str, Any]:
    """Handle DELETE /cv-tailoring/{cvTailoringId} requests."""
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _error_response(HTTPStatus.UNAUTHORIZED, 'Missing authentication')

    cv_tailoring_id = _extract_cv_tailoring_id(event)
    if not cv_tailoring_id:
        return _error_response(HTTPStatus.BAD_REQUEST, 'Missing cvTailoringId')

    # Delete from DynamoDB
    dal = _get_dal()
    result = dal.delete_tailored_cv(user_id, cv_tailoring_id)
    if not result.success:
        return _error_response(HTTPStatus.INTERNAL_SERVER_ERROR, 'Failed to delete')

    return _response(HTTPStatus.OK, {'message': 'Deleted successfully'})
```

**Add to routing:**
In the lambda_handler, add:
```python
if method == 'DELETE' and _is_tailoring_status_path(path):
    return delete_tailored_cv(event)
```

### 3. Add Delete to DAL

Add a method to DynamoDalHandler:

```python
def delete_tailored_cv(self, user_id: str, cv_tailoring_id: str) -> Result[None]:
    """Delete a CV tailoring artifact."""
    table = self._get_db_handler(self.table_name)
    sk = f'ARTIFACT#CV_TAILORED#{cv_tailoring_id}'
    table.delete_item(Key={'pk': user_id, 'sk': sk})
    return Result(success=True, data=None, code=ResultCode.SUCCESS)
```

### 4. Add Tests

**Unit Test:**
- Test that `_build_tail` extractsored_cv_list_item correct ID
- Test delete handler returns 200 on success
- Test delete returns 404 if not found

**Integration Test:**
- Create a CV tailoring
- Delete it
- Verify it's gone (GET returns 404)

### 5. Verify

- Run the tests
- Verify ID format is correct in list response
- Verify delete endpoint works

## Test File Reference

- `docs/refactor/live_tests/test_06_cv_tailoring.py` - CV tailoring tests
- `src/backend/careervp/handlers/cv_tailoring_handler.py` - handler code
- `src/backend/careervp/dal/dynamo_dal_handler.py` - DAL code

## Hints

- Check other handlers (cover letter, interview prep) for delete implementation patterns
- The ID extraction should handle both cases: with prefix and without prefix
- Make sure to verify the item exists before deleting, or handle the case gracefully
