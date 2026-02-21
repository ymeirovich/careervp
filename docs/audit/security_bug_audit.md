# CareerVP Security & Bug Audit Report

**Date:** 2026-02-20
**Version:** 1.0
**Auditor:** Claude Code

---

## Executive Summary

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| **Security** | 1 | 5 | 3 | - | 9 |
| **Bugs** | 3 | 4 | 5 | 6 | 18 |
| **Grand Total** | 4 | 9 | 8 | 6 | **27** |

---

# PART 1: SECURITY VULNERABILITIES

## 1.1 Critical Severity

### Finding 1: Missing Authentication in Knowledge Base Handler

| Attribute | Value |
|-----------|-------|
| **Severity** | Critical |
| **File** | `src/backend/careervp/handlers/knowledge_base_handler.py` |
| **Line** | 40-42 |
| **Issue** | Takes `user_id` directly from query string parameters without any authentication verification |
| **Evidence** | ```python def _handle_get(event: dict[str, Any], repo: KnowledgeRepository) -> dict[str, Any]: params = event.get('queryStringParameters') or {} user_id = params.get('user_id', '') ``` |
| **Impact** | Any unauthenticated user can read or write knowledge base entries for ANY user by manipulating query parameters |
| **Remediation** | 1. Add `@require_auth` decorator to handler 2. Extract user_id from auth context using `extract_user_id(event)` 3. Remove user_id from query parameters 4. Add test: `test_handler_returns_401_without_auth` |

---

## 1.2 High Severity

### Finding 2: Broken Access Control in VPR Handler

| Attribute | Value |
|-----------|-------|
| **Severity** | High |
| **File** | `src/backend/careervp/handlers/vpr_handler.py` |
| **Line** | 51-56 |
| **Issue** | Accepts `user_id` directly from request body without validating that authenticated user owns that user_id |
| **Evidence** | ```python logger.append_keys(user_id=request.user_id, application_id=request.application_id) user_cv = dal.get_cv(request.user_id) ``` |
| **Impact** | Authenticated attacker can request VPR generation for ANY user by specifying their user_id in payload |
| **Remediation** | 1. Remove user_id from request parsing 2. Extract user_id from auth context only: `user_id = extract_user_id(event)` 3. Use authenticated user_id for all DAL calls 4. Add test: `test_handler_returns_403_for_other_user_resource` |

---

### Finding 3: Authorization Bypass in Gap Analysis Handler

| Attribute | Value |
|-----------|-------|
| **Severity** | High |
| **File** | `src/backend/careervp/handlers/gap_handler.py` |
| **Line** | 97-102 |
| **Issue** | Falls back to user_id from request body without proper authorization |
| **Evidence** | ```python user_id = _extract_user_id(event) or _coerce_str(payload.get('user_id')) ``` |
| **Impact** | Users can potentially access or modify other users' gap analysis data |
| **Remediation** | 1. Remove payload fallback: `user_id = extract_user_id(event)` 2. Return 401 if extraction fails 3. Verify user_id is not None before proceeding |

---

### Finding 4: Debug Authentication Bypass

| Attribute | Value |
|-----------|-------|
| **Severity** | High |
| **Files** | Multiple handlers (cv_tailoring_handler.py, interview_prep_handler.py, cover_letter_handler.py, company_research_handler.py) |
| **Issue** | Environment variable `AUTHORIZER_DISABLED` can completely disable authentication |
| **Evidence** | ```python def _authorizer_disabled() -> bool: return os.getenv('AUTHORIZER_DISABLED', 'false').strip().lower() == 'true' ``` |
| **Impact** | If accidentally set to true in production, entire API becomes unauthenticated |
| **Remediation** | 1. Remove all `_authorizer_disabled()` functions 2. Remove all `AUTHORIZER_DISABLED` checks 3. Search: `grep -r "DISABLED" src/backend/careervp/handlers/` 4. Verify 0 matches after removal |

---

### Finding 5: User ID Spoofing Vector

| Attribute | Value |
|-----------|-------|
| **Severity** | High |
| **Files** | Multiple handlers |
| **Issue** | Accept user_id from request body as fallback when authorizer is disabled |
| **Evidence** | Pattern: `user_id = extract_user_id(event) or payload.get('user_id')` |
| **Impact** | Creates vector for ID spoofing attacks |
| **Remediation** | 1. Never use payload user_id 2. Always extract from auth context 3. Add lint rule: `no-user-id-from-payload` |

---

### Finding 6: Race Condition in SQS Worker

| Attribute | Value |
|-----------|-------|
| **Severity** | High |
| **File** | `src/backend/careervp/handlers/vpr_worker_handler.py` |
| **Line** | 53-71 |
| **Issue** | No locking mechanism when processing jobs - SQS at-least-once delivery causes duplicate processing |
| **Evidence** | ```python job = job_result status = job.get('status') if status == 'COMPLETED': return # No atomic claim ``` |
| **Impact** | Duplicate VPR generation, wasted resources, potential data corruption |
| **Remediation** | 1. Check status before processing 2. Use conditional update: `ConditionExpression='#status = :expected'` 3. Add idempotency key check 4. See spec §5.1 for code example |

---

## 1.3 Medium Severity

### Finding 7: Permissive CORS (Wildcard Origin)

| Attribute | Value |
|-----------|-------|
| **Severity** | Medium |
| **Files** | All handlers |
| **Issue** | Returns `Access-Control-Allow-Origin: *` allowing cross-origin requests from any domain |
| **Evidence** | `'Access-Control-Allow-Origin': '*'` |
| **Impact** | Vulnerable to CSRF attacks and data exfiltration |
| **Remediation** | 1. Set `ALLOWED_ORIGINS` env var (comma-separated) 2. Validate origin against allowed list 3. Return specific origin, not wildcard 4. See spec §6.1 for code example |

---

### Finding 8: Fallback Ephemeral RSA Keys

| Attribute | Value |
|-----------|-------|
| **Severity** | Medium |
| **File** | `src/backend/careervp/logic/auth_service.py` |
| **Line** | 95-109 |
| **Issue** | If JWT_PRIVATE_KEY and JWT_PUBLIC_KEY not set, generates ephemeral 2048-bit RSA keys at runtime |
| **Evidence** | ```python if not private_key or not public_key: private_key, public_key = _generate_ephemeral_rsa_keys() ``` |
| **Impact** | Tokens invalid after Lambda restart, all users logged out |
| **Remediation** | 1. Fail fast if keys missing in production: `if ENV == 'prod' and not keys: raise ConfigurationError()` 2. Only use ephemeral keys in dev/test 3. Add startup validation 4. See spec §6.3 for code example |

---

### Finding 9: Sensitive Data Logging

| Attribute | Value |
|-----------|-------|
| **Severity** | Medium |
| **Files** | vpr_handler.py:27, vpr_submit_handler.py:150 |
| **Issue** | `log_event=True` logs entire API event which may contain JWT tokens |
| **Evidence** | ```python @logger.inject_lambda_context(log_event=True) ``` |
| **Impact** | JWT tokens could be logged to CloudWatch |
| **Remediation** | 1. Change to `log_event=False` 2. Manually log only necessary fields 3. Search: `grep -r "log_event.*True" src/backend/careervp/handlers/` |

---

# PART 2: BUGS & LOGIC ERRORS

## 2.1 Critical Severity

### Finding 10: Empty List Crash

| Attribute | Value |
|-----------|-------|
| **Severity** | Critical |
| **File** | `src/backend/careervp/dal/dynamo_dal_handler.py` |
| **Line** | 285 |
| **Issue** | `max(items, key=...)` on empty list raises `ValueError` |
| **Evidence** | ```python latest_item = max(items, key=lambda record: int(record.get('version', 0))) ``` |
| **Impact** | Lambda function crashes with 500 error when querying for non-existent tailored CV |
| **Remediation** | ```python if not items: return Result(success=True, data=None, code=ResultCode.NOT_FOUND) latest_item = max(items, key=...) ``` |

---

### Finding 11: AttributeError on Context

| Attribute | Value |
|-----------|-------|
| **Severity** | Critical |
| **File** | `src/backend/careervp/handlers/cv_tailoring_handler.py` |
| **Line** | 159 |
| **Issue** | `context.aws_request_id` accessed without null check |
| **Evidence** | ```python logger.info('CV tailoring failed', request_id=context.aws_request_id) ``` |
| **Impact** | Handler crashes instead of returning error response |
| **Remediation** | ```python logger.info('CV tailoring failed', request_id=getattr(context, 'aws_request_id', 'unknown')) ``` |

---

### Finding 12: Version Parse Failure

| Attribute | Value |
|-----------|-------|
| **Severity** | Critical |
| **File** | `src/backend/careervp/dal/dynamo_dal_handler.py` |
| **Line** | 175 |
| **Issue** | Non-numeric version field causes ValueError, caught by outer except, loses error cause |
| **Evidence** | ```python latest_item = max(items, key=lambda record: int(record.get('version', 0))) ``` |
| **Impact** | Hard to debug when version field contains invalid data |
| **Remediation** | ```python try: version = int(record.get('version', 0)) except (ValueError, TypeError) as e: logger.warning("Invalid version: %s", record.get('version')) raise InvalidVersionError(f"Invalid version: {e}") ``` |

---

## 2.2 High Severity

### Finding 13: None Access on Result Data

| Attribute | Value |
|-----------|-------|
| **Severity** | High |
| **File** | `src/backend/careervp/handlers/cover_letter_handler.py` |
| **Line** | 89 |
| **Issue** | `request_result.data.job_id` accessed when data could be None |
| **Evidence** | ```python request_id = request_result.data.job_id ``` |
| **Impact** | Unhandled exception when job_id is missing from successful response |
| **Remediation** | ```python if not request_result.success or request_result.data is None: return error_response job_id = request_result.data.job_id ``` |

---

### Finding 14: Type Coercion Issue

| Attribute | Value |
|-----------|-------|
| **Severity** | High |
| **File** | `src/backend/careervp/logic/company_research.py` |
| **Line** | 233 |
| **Issue** | Blind `str()` conversion on Pydantic model produces unexpected results |
| **Evidence** | ```python parsed = urlparse(str(request.job_posting_url)) ``` |
| **Impact** | Invalid URL parsing leads to incorrect domain resolution |
| **Remediation** | ```python if not isinstance(request.job_posting_url, str): raise ValidationError("job_posting_url must be string") parsed = urlparse(request.job_posting_url) ``` |

---

### Finding 15: Error Swallowing

| Attribute | Value |
|-----------|-------|
| **Severity** | High |
| **File** | `src/backend/careervp/handlers/company_research_handler.py` |
| **Line** | 195-200 |
| **Issue** | Bare `except Exception` silently swallows errors without logging |
| **Evidence** | ```python try: response = table.get_item(Key=key) except Exception: response = {} ``` |
| **Impact** | Database errors are hidden, making debugging impossible |
| **Remediation** | ```python try: response = table.get_item(Key=key) except ClientError as e: logger.exception("Failed to get item: %s", key) raise ``` |

---

### Finding 16: Inconsistent Return Types

| Attribute | Value |
|-----------|-------|
| **Severity** | High |
| **File** | `src/backend/careervp/handlers/vpr_submit_handler.py` |
| **Line** | 168-175 |
| **Issue** | Error responses use different structure than success responses |
| **Evidence** | Mixed patterns between `_build_error_response()` and success returns |
| **Impact** | Client parsing difficult, inconsistent API responses |
| **Remediation** | Standardize all responses to same structure: `{'statusCode': int, 'headers': dict, 'body': str}` |

---

## 2.3 Medium Severity

### Finding 17: Empty Keyword List Edge Case

| Attribute | Value |
|-----------|-------|
| **Severity** | Medium |
| **File** | `src/backend/careervp/logic/cv_tailoring.py` |
| **Line** | 102 |
| **Issue** | When keywords is empty, continues to calculate required_coverage which may fail |
| **Evidence** | ```python if keywords: matched_keywords = [...] else: coverage = 0.0 # Continues anyway ``` |
| **Impact** | Division by zero or incorrect scoring |
| **Remediation** | ```python if not keywords: return 0.0 # Early return ``` |

---

### Finding 18: Weak Input Validation

| Attribute | Value |
|-----------|-------|
| **Severity** | Medium |
| **File** | `src/backend/careervp/handlers/knowledge_base_handler.py` |
| **Line** | 66-78 |
| **Issue** | Only checks key existence, not value type or validity |
| **Evidence** | ```python missing = [f for f in required_gap if not payload.get(f)] # Empty string passes! ``` |
| **Impact** | Invalid data saved to database, causing downstream errors |
| **Remediation** | ```python required_gap = {'user_id': str, 'job_id': str} for field, expected_type in required_gap.items(): value = payload.get(field) if not isinstance(value, expected_type) or not value: return 400 ``` |

---

### Finding 19: Pagination Not Implemented

| Attribute | Value |
|-----------|-------|
| **Severity** | Medium |
| **File** | `src/backend/careervp/dal/jobs_repository.py` |
| **Line** | 71-85 |
| **Issue** | Uses `scan` operation without pagination handling |
| **Evidence** | ```python response = self.table.scan(FilterExpression=..., Limit=safe_limit) ``` |
| **Impact** | Users cannot retrieve all jobs - only first page returned |
| **Remediation** | Implement pagination loop with LastEvaluatedKey - see spec §8.1 |

---

### Finding 20: None Comparison Logic Error

| Attribute | Value |
|-----------|-------|
| **Severity** | Medium |
| **File** | `src/backend/careervp/handlers/user_handler.py` |
| **Line** | 152 |
| **Issue** | When both payload_user_id and user_id are None, allows unauthorized profile update |
| **Evidence** | ```python if isinstance(payload_user_id, str) and payload_user_id and payload_user_id != user_id: # Block # But if both None, passes through ``` |
| **Impact** | Logic error allows unauthorized profile updates |
| **Remediation** | ```python if not user_id: return 401 # Require auth user_id = extract_user_id(event) # Use ONLY auth context ``` |

---

### Finding 21: Inconsistent Timezone Handling

| Attribute | Value |
|-----------|-------|
| **Severity** | Low |
| **Files** | cv_tailoring_dal.py:25 vs dynamo_dal_handler.py:43 |
| **Issue** | `datetime.now()` vs `datetime.now(timezone.utc)` |
| **Impact** | Subtle bugs around DST transitions and TTL calculations |
| **Remediation** | Always use `datetime.now(timezone.utc)` |

---

### Finding 22: Hardcoded Magic Numbers

| Attribute | Value |
|-----------|-------|
| **Severity** | Low |
| **File** | `src/backend/careervp/logic/cv_parser.py:47` |
| **Issue** | Magic number 100 hardcoded without configuration |
| **Impact** | Cannot adjust validation threshold without code changes |
| **Remediation** | Move to constants/config file |

---

### Finding 23: Exception Handling Masks Real Error

| Attribute | Value |
|-----------|-------|
| **Severity** | Low |
| **File** | `src/backend/careervp/logic/vpr_generator.py:182` |
| **Issue** | Catches RuntimeError/ValueError silently, falls back without logging |
| **Impact** | Silent failures make LLM integration debugging difficult |
| **Remediation** | Add logging before fallback |

---

### Finding 24: Missing Null Check for Optional Field

| Attribute | Value |
|-----------|-------|
| **Severity** | Low |
| **File** | `src/backend/careervp/logic/gap_analysis.py:89` |
| **Issue** | question.get('impact') returns None if missing, passed to _normalize_level() |
| **Impact** | Invalid questions processed with defaults instead of failing fast |
| **Remediation** | Validate required fields explicitly |

---

### Finding 25: Inconsistent Error Message Format

| Attribute | Value |
|-----------|-------|
| **Severity** | Low |
| **File** | `src/backend/careervp/handlers/vpr_handler.py:61` |
| **Issue** | When result.success=False but result.data exists, returns data instead of error |
| **Impact** | Confusing API responses on failure |
| **Remediation** | Check success flag first |

---

### Finding 26: Default Value Override Issue

| Attribute | Value |
|-----------|-------|
| **Severity** | Low |
| **File** | `src/backend/careervp/handlers/vpr_status_handler.py:117` |
| **Issue** | If result key exists but contains None, overwritten to {} |
| **Impact** | Loses distinction between "no result" and "empty result" |
| **Remediation** | Check for None explicitly |

---

# PART 3: REMEDIATION PRIORITY MATRIX

| Priority | Finding | Severity | Effort | Owner |
|----------|---------|----------|--------|-------|
| 1 | Auth on knowledge_base_handler | Critical | Medium | TBD |
| 2 | Remove AUTHORIZER_DISABLED | High | Low | TBD |
| 3 | Fix user_id in all handlers | High | Medium | TBD |
| 4 | Fix empty list crash | Critical | Low | TBD |
| 5 | Add null checks on context | Critical | Low | TBD |
| 6 | Fix race condition in SQS | High | Medium | TBD |
| 7 | Fix error swallowing | High | Medium | TBD |
| 8 | Restrict CORS origins | Medium | Low | TBD |
| 9 | Disable log_event | Medium | Low | TBD |
| 10 | Implement pagination | Medium | Medium | TBD |

---

# PART 4: REMEDIATION VERIFICATION

After fixing each finding, verify with:

```bash
# Auth fixes
grep -r "payload.*user_id\|user_id.*payload" src/backend/careervp/handlers/
# Expected: 0 matches

grep -r "DISABLED" src/backend/careervp/handlers/
# Expected: 0 matches

# Null safety
python -c "from careervp.dal.dynamo_dal_handler import *; print('Import OK')"

# Run tests
pytest tests/unit/ -v --tb=short

# Lint
ruff check src/backend/careervp/

# Type check
mypy src/backend/careervp/ --strict
```

---

# PART 5: PREVENTION

See `docs/best_practices/code_quality_security_spec.yaml` for mandatory coding standards that prevent these issues.

---

*Report generated: 2026-02-20*
