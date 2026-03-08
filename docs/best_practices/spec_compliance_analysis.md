# CareerVP Best Practices Compliance Analysis

Generated: 2026-02-25

This document analyzes the codebase against the best practices specifications in `docs/best_practices/yaml/`.

---

## Summary

| Area | Compliant | Non-Compliant | Notes |
|------|-----------|---------------|-------|
| Lambda Handlers | 4 | 11 | Various patterns missing |
| DynamoDB | Partial | 4 tables | Query vs Scan violations |
| Testing | N/A | Not analyzed | Future work |
| Frontend | N/A | Not analyzed | Future work |
| CI/CD | N/A | Not analyzed | Future work |

---

## Lambda Handler Compliance

### Powertools Usage

#### Missing ALL Decorators (3 handlers)

| File | Issue |
|------|-------|
| `handlers/health_handler.py` | No Powertools decorators |
| `handlers/gap_handler.py` | No Powertools decorators |
| `handlers/cv_tailoring_handler.py` | No Powertools decorators |

#### Missing @metrics.log_metrics (4 handlers)

| File | Current |
|------|---------|
| `handlers/auth_handler.py` | Only logger + tracer |
| `handlers/user_handler.py` | Only logger + tracer |
| `handlers/job_handler.py` | Only logger + tracer |
| `handlers/cv_upload_handler.py` | Only logger + tracer |

#### Missing capture_cold_start_metric=True (4 handlers)

| File | Current |
|------|---------|
| `handlers/cover_letter_handler.py` | Has metrics, no cold start metric |
| `handlers/interview_prep_handler.py` | Has metrics, no cold start metric |
| `handlers/knowledge_base_handler.py` | Has metrics, no cold start metric |
| `handlers/company_research_handler.py` | Has metrics, no cold start metric |

#### Fully Compliant (4 handlers)

| File |
|------|
| `handlers/vpr_handler.py` |
| `handlers/vpr_submit_handler.py` |
| `handlers/vpr_status_handler.py` |
| `handlers/vpr_worker_handler.py` |

---

### Authentication Issues

#### Reading user_id from Payload (3 handlers - CRITICAL)

| File | Line | Issue |
|------|------|-------|
| `handlers/gap_handler.py` | 88 | Falls back to `payload.get('user_id')` |
| `handlers/cv_upload_handler.py` | 302 | Reads from payload directly |
| `handlers/knowledge_base_handler.py` | 173 | Reads from payload directly |

---

### Idempotency

#### Missing Idempotency (7 handlers)

| File | Endpoint Type |
|------|---------------|
| `handlers/cv_upload_handler.py` | POST - creates resource |
| `handlers/cover_letter_handler.py` | POST - creates async job |
| `handlers/cv_tailoring_handler.py` | POST - creates async job |
| `handlers/interview_prep_handler.py` | POST - creates async job |
| `handlers/gap_handler.py` | POST - creates resource |
| `handlers/job_handler.py` | POST - creates resource |
| `handlers/company_research_handler.py` | POST - creates async job |

#### Has Idempotency (1 handler)

| File | Implementation |
|------|----------------|
| `handlers/vpr_submit_handler.py` | `idempotency_key` check |

---

### Error Handling

#### Generic Exception Catching (2 handlers)

| File | Lines | Issue |
|------|-------|-------|
| `handlers/gap_handler.py` | 15 | Module-level blanket catch |
| `handlers/cv_tailoring_handler.py` | 44, 62, 149, 196 | Multiple blanket catches |

---

## DynamoDB Compliance

### Query vs Scan Violations (CRITICAL)

**Rule:** Prefer Query over Scan

| File | Line | Method | Fix |
|------|------|--------|-----|
| `dal/jobs_repository.py` | 112 | `list_jobs()` | Add GSI on user_id |
| `dal/jobs_repository.py` | 126 | `get_jobs_by_user()` | Add GSI on user_id |
| `dal/jobs_repository.py` | 140 | `get_vpr_jobs_by_user()` | Add GSI on user_id |
| `dal/cv_dal.py` | 85 | `get_cv_item()` | Legacy fallback - lower priority |

### GSI Projections Using ALL

**Rule:** Use KEYS_ONLY or INCLUDE to reduce costs

| File | Line | GSI Name |
|------|------|-----------|
| `infra/careervp/api_db_construct.py` | 106 | `email-index` |
| `infra/careervp/api_db_construct.py` | 116 | `user_id-index` |
| `infra/careervp/api_db_construct.py` | 226 | `idempotency-key-index` |
| `infra/careervp/api_db_construct.py` | 289 | `status-index` |
| `infra/careervp/api_db_construct.py` | 353 | `entity-index` |
| `infra/careervp/api_db_construct.py` | 393 | `type-index` |

### Point-in-Time Recovery (PITR)

**Rule:** Enable PITR for production tables

| File | Table | Status |
|------|-------|--------|
| `infra/careervp/dynamodb_stack.py` | `cvs_table` | NOT CONFIGURED |
| `infra/careervp/dynamodb_stack.py` | `applications_table` | NOT CONFIGURED |
| `infra/careervp/dynamodb_stack.py` | `gap_responses_table` | NOT CONFIGURED |
| `infra/careervp/dynamodb_stack.py` | `knowledge_table` | NOT CONFIGURED |

**Note:** Tables in `api_db_construct.py` DO have PITR enabled.

---

## Remediation Priority

### High Priority (Security/Critical)

1. **Fix auth bypass in gap_handler.py, cv_upload_handler.py, knowledge_base_handler.py**
   - These handlers read user_id from payload, allowing identity spoofing

2. **Add idempotency to all POST handlers**
   - Prevents duplicate operations on retry

3. **Fix Query vs Scan in jobs_repository.py**
   - Performance and cost impact

### Medium Priority

4. **Add Powertools decorators to all handlers**
   - health_handler.py, gap_handler.py, cv_tailoring_handler.py

5. **Add @metrics.log_metrics to handlers missing it**
   - auth_handler.py, user_handler.py, job_handler.py, cv_upload_handler.py

6. **Enable PITR on dynamodb_stack.py tables**
   - Production reliability

### Low Priority

7. **Optimize GSI projections**
   - Cost optimization

8. **Add capture_cold_start_metric=True**
   - Observability improvement

---

## Notes

- Specs location: `docs/best_practices/yaml/`
- This analysis is based on spec version 1.0
- Some spec rules are marked as "production only" and don't apply to dev/staging
