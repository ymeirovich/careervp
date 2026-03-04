# Codex Prompt: CV Upload 529 Overloaded Error - Retry Logic Fix

## Context

The CV upload endpoint (`POST /users/me/cv`) is failing with a 529 error from Anthropic:

```
{
  "success": false,
  "user_cv": null,
  "error": "LLM extraction failed: Error code: 529 - {'type': 'error', 'error': {'type': 'overloaded_error', 'message': 'Overloaded'}}"
}
```

The error code 529 indicates Anthropic's server is overloaded. This is a transient error that should be retried.

## Current Implementation

The LLM client in `src/backend/careervp/logic/utils/llm_client.py` has retry logic:

```python
@retry_on_transient_error(max_retries=3)
def invoke(self, ...):
```

The retry decorator catches:
- `RateLimitError` - immediate retry
- `APIError` with `status_code >= 500` - retry with exponential backoff

## Problem

The 529 `overloaded_error` is NOT being retried properly. Possible reasons:

1. **Exception type mismatch** - The 529 error might not have `status_code` accessible
2. **SDK configuration missing** - Anthropic SDK might need configuration for timeout, max retries
3. **Cold start issues** - Retry logic might not execute properly on Lambda cold starts

## Your Task

### 1. Investigate the Exception Handling

Read the retry decorator and the `invoke` method in `src/backend/careervp/logic/utils/llm_client.py`:

- Check if `APIError` exception from Anthropic has `status_code` attribute
- Check if 529 errors are being caught properly
- Add logging to see what's happening during the error

### 2. Check Anthropic SDK Configuration

The Anthropic SDK may need configuration for:
- `max_retries` - How many times to retry on rate limit / overloaded
- `timeout` - Request timeout
- `connect_timeout` - Connection timeout

Example SDK configuration:
```python
from anthropic import Anthropic

client = Anthropic(
    max_retries=3,  # Default is 2, increase for better resilience
    timeout=60.0,   # Request timeout in seconds
)
```

Check if `LLMRouter` is properly configuring the Anthropic client.

### 3. Implement the Fix

**Option A: Fix SDK Configuration**
Add proper max_retries and timeout to the Anthropic client in `LLMRouter.__init__`:

```python
self._client = Anthropic(
    api_key=self._api_key,
    max_retries=3,
    timeout=60.0,
)
```

**Option B: Fix Exception Handling**
Improve the retry decorator to handle 529 errors:

```python
def retry_on_transient_error(max_retries: int = 3, base_delay: float = 1.0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except RateLimitError as e:
                    # Handle rate limit
                    delay = base_delay * (2 ** attempt)
                    sleep(delay)
                except APIError as e:
                    status_code = getattr(e, 'status_code', None)
                    # Also check for overloaded error in response
                    if status_code == 529 or 'overloaded' in str(e).lower():
                        delay = base_delay * (2 ** attempt)
                        sleep(delay)
                    elif isinstance(status_code, int) and status_code >= 500:
                        delay = base_delay * (2 ** attempt)
                        sleep(delay)
                    else:
                        raise
            raise RuntimeError('Max retries exceeded')
        return wrapper
    return decorator
```

**Option C: Both A and B (Recommended)**

### 4. Add Tests

**Unit Test:**
- Add test to verify retry logic handles 529 errors correctly
- Mock the Anthropic client to raise 529 errors and verify retry behavior

**Integration Test:**
- Add retry logic to the live test `test_upload_cv` as a quick fix:
  ```python
  max_retries = 3
  for attempt in range(max_retries):
      response = requests.post(...)
      if response.status_code == 200:
          break
      if 'overloaded' in response.text.lower():
          sleep(2 ** attempt)
      else:
          break
  ```

### 5. Verify the Fix

- Run the CV upload test multiple times
- Verify retry logic kicks in when 529 occurs
- Check CloudWatch logs for retry attempts

## Test File Reference
- `careervp/live-test-results25.log` - contains test evidence
- `docs/refactor/live_tests/test_02_users.py` - CV upload test
- `src/backend/careervp/logic/utils/llm_client.py` - LLM client with retry

## Hints
- The Anthropic SDK has built-in retry configuration - check if it's being used
- The 529 error might be raised as a different exception type than APIError
- Check the actual exception class and attributes when 529 occurs
- Consider using the SDK's built-in retry mechanism instead of custom decorator
