# Codex Prompt: Health Check Returns "degraded" Status

## Context

The `/health` endpoint is returning "degraded" status because it performs live connectivity checks to external services (Anthropic API and DynamoDB) which are failing silently.

## Current Implementation

From `src/backend/careervp/handlers/health_handler.py`:

```python
def health_check() -> dict[str, Any]:
    services: dict[str, str] = {}

    # Check Anthropic API
    try:
        client = anthropic.Anthropic()
        client.models.list()
        services['anthropic'] = 'healthy'
    except Exception:
        services['anthropic'] = 'degraded'

    # Check DynamoDB
    try:
        ddb = boto3.client('dynamodb', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
        ddb.describe_table(TableName=table_name)
        services['dynamodb'] = 'healthy'
    except Exception:
        services['dynamodb'] = 'degraded'

    overall = 'healthy' if all(v == 'healthy' for v in services.values()) else 'degraded'
    return {...}
```

## Test Evidence

```
=== STRICT CONTRACT RESPONSE health_check.json ===
{
  "endpoint": "/health",
  "method": "GET",
  "status_code": 200,
  "response": {
    "status": "degraded",
    "timestamp": "2026-03-02T19:23:55.123014Z",
    "version": "1.0.0",
    "services": {
      "anthropic": "degraded",
      "dynamodb": "degraded"
    }
  }
}
```

## Problems with Current Approach

1. **Live API calls on every health check** - Expensive, slow, and unreliable
2. **Silent failures** - No logging of WHY services are degraded
3. **Catch-all exceptions** - Hides real issues
4. **No timeout handling** - Could hang the health endpoint
5. **No retry logic** - Single failure marks service as degraded
6. **Cold start issues** - Lambda might timeout before connection established

## Your Task

### 1. Analyze the Root Cause
- Determine why both Anthropic and DynamoDB checks are failing
- Check if it's a cold start, permissions, or network issue
- Add logging to capture the actual exception messages

### 2. Implement a Fix

**Option A (Recommended): Remove Live Checks**
Simply return "healthy" without making live API calls. Health checks should verify the Lambda is running, not check external service connectivity.

**Option B: Add Retry Logic with Exponential Backoff**
If live checks are required, add proper retry logic:

```python
import time
from functools import wraps

def retry_with_backoff(max_retries=3, initial_delay=1, backoff_factor=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay)
                    delay *= backoff_factor
            return None
        return wrapper
    return decorator

@retry_with_backoff(max_retries=3, initial_delay=1, backoff_factor=2)
def check_anthropic():
    client = anthropic.Anthropic(timeout=5.0)
    client.models.list(limit=1)
    return 'healthy'
```

### 3. Add Logging
- Log the actual exception messages when checks fail
- Include attempt numbers for retry logic

### 4. Update Tests
- Update `docs/refactor/live_tests/test_01_auth_health.py` to accept "healthy" status
- Update the contract test in `docs/refactor/live_tests/test_10_api_contract_success.py`

### 5. Verify the Fix
- Run health check and verify it returns "healthy"
- Ensure no regression

## Hints

- The health endpoint is called frequently - live checks are expensive
- Consider using a cached health status that updates periodically
- DynamoDB DescribeTable requires IAM permissions - check if Lambda role has them
- Anthropic API might be rate-limiting health check calls

## Test File Reference
- `careervp/live-test-results25.log` - contains test evidence
- `docs/refactor/live_tests/test_01_auth_health.py` - health test file
- `docs/refactor/live_tests/test_10_api_contract_success.py` - contract test file
- `docs/refactor/live_tests/test_data/strict_contracts/health_check.json` - contract definition
