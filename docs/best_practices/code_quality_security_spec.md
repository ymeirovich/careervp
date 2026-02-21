# CareerVP Code Quality & Security Specification

**Version:** 1.0
**Date:** 2026-02-20
**Purpose:** Mandatory coding standards to prevent security vulnerabilities and logic bugs
**Enforcement:** All new code must pass these checks; existing code to be remediated

---

## 1. AUTHENTICATION & AUTHORIZATION

### 1.1 Never Trust User Input for Identity

**Rule:** Always derive user identity from authentication context, never from request payload.

```python
# ❌ FORBIDDEN - Never do this
user_id = payload.get('user_id')  # Untrusted input

# ❌ FORBIDDEN - Even with fallback
user_id = extract_user_id(event) or payload.get('user_id')

# ✅ REQUIRED - Always extract from auth
user_id = extract_user_id(event)
if not user_id:
    return 401 response
```

### 1.2 Authorization Pattern

**Rule:** Validate ownership of resources before access.

```python
# ❌ FORBIDDEN
def get_resource(event, resource_id):
    resource = dal.get(resource_id)  # No ownership check

# ✅ REQUIRED
def get_resource(event, resource_id):
    user_id = extract_user_id(event)
    resource = dal.get(resource_id)
    if resource.user_id != user_id:
        return 403 response
```

### 1.3 Remove Debug Authentication Bypass

**Rule:** Production code must never contain authentication bypass mechanisms.

```python
# ❌ FORBIDDEN - Never in production code
def _authorizer_disabled() -> bool:
    return os.getenv('AUTHORIZER_DISABLED', 'false').lower() == 'true'

# Remove entirely - no debug flags in handlers
```

### 1.4 Require Auth Decorator

**Rule:** Use standardized auth middleware on all protected endpoints.

```python
# ✅ REQUIRED - Use the auth middleware
from careervp.handlers.auth_middleware import require_auth

@require_auth
def handler(event, context, user_id: str) -> dict:
    # user_id guaranteed to be present
    ...

# Never manually extract user_id in handlers
```

---

## 2. INPUT VALIDATION

### 2.1 Validate Required Fields

**Rule:** Check both existence AND type/format of required fields.

```python
# ❌ FORBIDDEN - Only checks existence
required = ('user_id', 'job_id')
missing = [f for f in required if not payload.get(f)]  # Empty string passes!

# ✅ REQUIRED - Validate type and format
required_gap = {
    'user_id': str,
    'job_id': str,
    'cv_id': str,
}
for field, expected_type in required_gap.items():
    value = payload.get(field)
    if not isinstance(value, expected_type) or not value:
        return 400 response
```

### 2.2 Validate URL/URI Parameters

**Rule:** Validate external inputs before parsing.

```python
# ❌ FORBIDDEN - Blind str() conversion
if request.job_posting_url:
    parsed = urlparse(str(request.job_posting_url))

# ✅ REQUIRED - Validate type first
if request.job_posting_url:
    if not isinstance(request.job_posting_url, str):
        raise ValidationError("job_posting_url must be string")
    parsed = urlparse(request.job_posting_url)
```

---

## 3. NULL SAFETY

### 3.1 Defensive Access on Optional Values

**Rule:** Always check for None before attribute access on optional types.

```python
# ❌ FORBIDDEN - Direct access
result = request_result.data.job_id  # data could be None

# ✅ REQUIRED - Null check
if not request_result.success or request_result.data is None:
    return 500 response
job_id = request_result.data.job_id
```

### 3.2 Safe Collection Access

**Rule:** Handle empty collections explicitly.

```python
# ❌ FORBIDDEN - Crashes on empty list
latest_item = max(items, key=lambda r: int(r.get('version', 0)))

# ✅ REQUIRED - Handle empty
if not items:
    return Result(success=True, data=None, code=ResultCode.NOT_FOUND)
latest_item = max(items, key=lambda r: int(r.get('version', 0)))
```

### 3.3 Context Attribute Access

**Rule:** Never assume context has attributes.

```python
# ❌ FORBIDDEN
logger.info('Failed', request_id=context.aws_request_id)

# ✅ REQUIRED - Check or use getattr
logger.info('Failed', request_id=getattr(context, 'aws_request_id', 'unknown'))
```

---

## 4. ERROR HANDLING

### 4.1 No Bare Except

**Rule:** Never use bare `except:` - catch specific exceptions.

```python
# ❌ FORBIDDEN
try:
    do_something()
except:  # Catches everything including KeyboardInterrupt
    response = {}

# ✅ REQUIRED - Catch specific exceptions
try:
    do_something()
except ClientError as e:
    logger.exception("DynamoDB error: %s", e)
    return 500 response
```

### 4.2 Always Log Exceptions

**Rule:** Never swallow errors without logging.

```python
# ❌ FORBIDDEN - Silent failure
try:
    response = table.get_item(Key=key)
except Exception:
    response = {}  # Lost forever!

# ✅ REQUIRED - Log before handling
try:
    response = table.get_item(Key=key)
except ClientError as e:
    logger.exception("Failed to get item: %s", key)
    raise  # Or handle with specific error
```

### 4.3 Preserve Error Context

**Rule:** Don't mask the real error cause.

```python
# ❌ FORBIDDEN - Loses error cause
try:
    value = int(record.get('version'))
except ValueError:
    return generic_error  # What went wrong?

# ✅ REQUIRED - Include context
try:
    value = int(record.get('version'))
except ValueError as e:
    logger.warning("Invalid version format: %s", record.get('version'))
    return Result(success=False, error=f"Invalid version: {e}")
```

---

## 5. RACE CONDITIONS

### 5.1 Idempotent SQS Processing

**Rule:** Check job status before processing; implement idempotency.

```python
# ❌ FORBIDDEN - No status check
def process_job(job_id, input_data):
    # Start processing immediately
    ...

# ✅ REQUIRED - Check and update atomically
def process_job(job_id, input_data):
    # 1. Check current status
    job = get_job(job_id)
    if job.status in ('COMPLETED', 'FAILED'):
        logger.info("Job already terminal, skipping", job_id=job_id)
        return

    # 2. Atomically claim (use conditional update)
    if not update_job_status(job_id, 'PROCESSING', expected='PENDING'):
        logger.info("Job claimed by another worker", job_id=job_id)
        return

    # 3. Process...
```

### 5.2 Conditional Updates

**Rule:** Use DynamoDB conditional writes to prevent races.

```python
# ✅ REQUIRED - Conditional update
table.update_item(
    Key={'job_id': job_id},
    UpdateExpression='SET #status = :new_status',
    ConditionExpression='#status = :expected_status',
    ExpressionAttributeNames={'#status': 'status'},
    ExpressionAttributeValues={
        ':new_status': 'PROCESSING',
        ':expected_status': 'PENDING'
    }
)
```

---

## 6. SECURITY CONFIGURATION

### 6.1 CORS Restriction

**Rule:** Never use wildcard origin in production.

```python
# ❌ FORBIDDEN
headers = {
    'Access-Control-Allow-Origin': '*',  # Never in prod!
}

# ✅ REQUIRED - Use specific origins
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',')

def get_cors_headers(origin: str) -> dict:
    if origin in ALLOWED_ORIGINS:
        return {'Access-Control-Allow-Origin': origin}
    return {'Access-Control-Allow-Origin': ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else ''}
```

### 6.2 Disable Sensitive Event Logging

**Rule:** Never log full request/response in production.

```python
# ❌ FORBIDDEN - Logs JWT tokens!
@logger.inject_lambda_context(log_event=True)

# ✅ REQUIRED - Only log context
@logger.inject_lambda_context(log_event=False)  # Never log full event
```

### 6.3 Fail Fast on Missing Configuration

**Rule:** Validate required configuration at startup.

```python
# ❌ FORBIDDEN - Silent fallback
if not private_key:
    private_key, public_key = _generate_ephemeral_keys()  # Dangerous!

# ✅ REQUIRED - Fail in production
def get_jwt_keys():
    private_key = os.getenv('JWT_PRIVATE_KEY')
    public_key = os.getenv('JWT_PUBLIC_KEY')

    if not private_key or not public_key:
        if os.getenv('ENV') == 'production':
            raise ConfigurationError("JWT keys required in production")
        # Only in dev: generate temp keys
        private_key, public_key = _generate_ephemeral_keys()

    return private_key, public_key
```

---

## 7. TYPE SAFETY

### 7.1 Always Use Type Hints

**Rule:** All functions must have type hints.

```python
# ❌ FORBIDDEN
def handler(event, context):
    ...

# ✅ REQUIRED
def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    ...
```

### 7.2 Handle Optional Types

**Rule:** Use Optional and handle None explicitly.

```python
# ❌ FORBIDDEN
def get_version(item: dict) -> int:
    return int(item.get('version', 0))  # Could be None

# ✅ REQUIRED
def get_version(item: dict) -> int:
    version = item.get('version')
    if version is None:
        return 0
    try:
        return int(version)
    except (ValueError, TypeError):
        return 0
```

---

## 8. PAGINATION

### 8.1 Implement Proper Pagination

**Rule:** Never use scan without pagination.

```python
# ❌ FORBIDDEN - Missing pagination
def list_items(self, limit: int = 20):
    response = self.table.scan(Limit=limit)
    return response.get('Items', [])

# ✅ REQUIRED - Handle pagination
def list_items(self, limit: int = 20):
    items = []
    last_key = None

    while len(items) < limit:
        scan_kwargs = {'Limit': limit - len(items)}
        if last_key:
            scan_kwargs['ExclusiveStartKey'] = last_key

        response = self.table.scan(**scan_kwargs)
        items.extend(response.get('Items', []))

        last_key = response.get('LastEvaluatedKey')
        if not last_key:
            break

    return items
```

---

## 9. TESTING REQUIREMENTS

### 9.1 Required Test Coverage

| Category | Minimum Coverage |
|----------|-----------------|
| Authentication | 100% - All auth paths tested |
| Authorization | 100% - Ownership checks tested |
| Null handling | 100% - All optional paths tested |
| Error handling | 100% - All exception paths tested |

### 9.2 Required Test Cases Per Handler

```python
# Authentication tests (required)
def test_handler_returns_401_without_auth():
    ...

def test_handler_returns_401_with_invalid_token():
    ...

def test_handler_extracts_user_id_from_jwt():
    ...

# Authorization tests (required)
def test_handler_returns_403_for_other_user_resource():
    ...

# Null safety tests (required)
def test_handler_handles_none_result():
    ...

def test_handler_handles_empty_list():
    ...
```

---

## 10. LINTING & TYPE CHECKING

### 10.1 Mandatory Checks

| Tool | Command | Pass Required |
|------|---------|--------------|
| Ruff | `ruff check careervp/` | 0 errors |
| MyPy | `mypy careervp/ --strict` | 0 errors |
| Bandit | `bandit -r careervp/` | 0 High/Critical |

### 10.2 Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
        args: ['careervp/', '--strict', '--ignore-missing-imports']
```

---

## 11. CODE REVIEW CHECKLIST

Before any code merge, verify:

- [ ] **Auth:** `user_id` comes only from `extract_user_id()`, never from payload
- [ ] **Auth:** No `AUTHORIZER_DISABLED` or similar bypasses
- [ ] **Auth:** All handlers use `@require_auth` or equivalent
- [ ] **Ownership:** Resources checked for user ownership before access
- [ ] **Null:** All `result.data` access null-checked
- [ ] **Null:** All optional parameters handled
- [ ] **Errors:** No bare `except:`
- [ ] **Errors:** All exceptions logged
- [ ] **Security:** No `Access-Control-Allow-Origin: *`
- [ ] **Security:** `log_event=False` on Lambda decorators
- [ ] **Types:** All functions have type hints
- [ ] **Tests:** Auth/authorization paths tested

---

## 12. SEVERITY CLASSIFICATION

| Level | Definition | Response Time |
|-------|------------|---------------|
| **Critical** | Auth bypass, data breach, injection | Immediate hotfix |
| **High** | Access control flaw, race condition | 24 hours |
| **Medium** | Error swallowing, weak validation | 1 week |
| **Low** | Inconsistent patterns, style | Next sprint |

---

**Enforcement:** This spec is mandatory. Code not meeting these standards will not be merged.

---

*Generated from security & bug review findings - 2026-02-20*
