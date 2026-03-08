# REFACTOR2 End-to-End Test Designs

**Date:** 2026-02-20
**Purpose:** E2E test specifications for complete job application workflows against deployed API
**Location:** `docs/refactor2/live_tests/` (curl-based) + `src/backend/tests/e2e/` (pytest-based)
**Environment:** Deployed API (staging or production)

---

## E2E Test 1: Happy Path - Full Job Application

**Description:** Complete job application workflow from user registration to interview preparation.
**Timeout:** 600 seconds (10 minutes)
**Prerequisites:** API deployed, Anthropic API key configured in SSM

```
API_BASE="${API_BASE:-https://dev-api.careervp.com}"
```

### Step Sequence

| Step | Method | Endpoint | Payload File | Expected Code | Key Assertions |
|------|--------|----------|-------------|---------------|----------------|
| 1 | POST | /auth/register | `payloads/auth_register.json` | 201 | `access_token` present, `token_type == "Bearer"` |
| 2 | POST | /auth/login | `payloads/auth_login.json` | 200 | `access_token` present |
| 3 | GET | /users/me | - | 200 | `email` matches registration |
| 4 | POST | /users/me/cv | `payloads/cv_upload.json` | 201 | `cv_id` returned, `status == "parsed"` |
| 5 | GET | /users/me/cvs | - | 200 | Array contains uploaded CV |
| 6 | POST | /jobs | `payloads/job_create.json` | 201 | `job_id` returned |
| 7 | GET | /jobs | - | 200 | Array contains created job |
| 8 | POST | /company-research/fetch | `payloads/company_research_fetch.json` | 202 | `request_id` returned |
| 9 | POST | /gap-analysis/questions | `payloads/gap_questions_generate.json` (use cv_id, job_id from steps 4,6) | 200 | 10 questions, each has `tags`, `strategic_intent` |
| 10 | POST | /gap-analysis/responses | `payloads/gap_responses_submit.json` | 200 | `impact_statements` with `evidence_type` |
| 11 | GET | /gap-analysis/{jobId}/questions | - | 200 | Previous questions returned |
| 12 | POST | /vpr/generate | `payloads/vpr_generate.json` (use cv_id, job_id, gap_response_ids) | 202 | `request_id`, `status == "processing"` |
| 13 | POLL | GET /vpr/{vprId} every 5s, max 120s | - | 200 | Wait until `status == "completed"` |
| 14 | VERIFY | VPR result | - | - | `uvp` non-empty, `differentiators` array len >= 3, `company_job_fit_score` > 0 |
| 15 | POST | /cv-tailoring/generate | `payloads/cv_tailoring_generate.json` (use cv_id, job_id, vpr_id) | 202 | `request_id` returned |
| 16 | POLL | GET /cv-tailoring/{id} every 5s, max 120s | - | 200 | Wait until `status == "completed"` |
| 17 | VERIFY | CV Tailoring result | - | - | `ats_score >= 8.0`, `keyword_matches.matched` len > 5, `fvs_validation.is_valid == true` |
| 18 | POST | /cover-letter/generate | `payloads/cover_letter_generate.json` (use all IDs) | 202 | `request_id` returned |
| 19 | POLL | GET /cover-letter/{id} every 5s, max 90s | - | 200 | Wait until `status == "completed"` |
| 20 | VERIFY | Cover Letter result | - | - | `paragraphs.hook.word_count` 80-100, `paragraphs.proof_points.requirements_matched >= 3`, `paragraphs.close.includes_cta == true` |
| 21 | POST | /interview-prep/generate | `payloads/interview_prep_generate.json` (use vpr_id, gap_response_ids) | 202 | `request_id` returned |
| 22 | POLL | GET /interview-prep/{id} every 5s, max 90s | - | 200 | Wait until `status == "completed"` |
| 23 | VERIFY | Interview Prep result | - | - | `questions` len >= 10, each has `suggested_answer.format == "STAR"` |

### Quality Gate Assertions (Post-Pipeline)

| Check | Threshold | Source |
|-------|-----------|--------|
| ATS Score | >= 8.0 | CV Tailoring result |
| Anti-AI Score | >= 9.0 | FVS validation |
| Grammar Score | >= 9.0 | FVS validation |
| Tone Score | >= 8.0 | FVS validation |
| Hook word count | 80-100 | Cover Letter paragraphs |
| Close word count | 60-80 | Cover Letter paragraphs |
| VPR differentiators | >= 3 | VPR result |
| Interview questions | >= 10 | Interview Prep result |
| STAR format | All questions | Interview Prep suggested_answer |

### Cleanup

```bash
# Delete test user and all artifacts (DynamoDB + S3)
aws dynamodb delete-item --table-name careervp-users-table-dev --key '{"pk": {"S": "<user_id>"}}'
# Delete S3 VPR results
aws s3 rm s3://careervp-dev-vpr-results-*/results/<vpr_job_id>.json
```

---

## E2E Test 2: Error Handling

**Description:** Validates proper error responses for unauthorized, invalid, and missing resource requests.
**Timeout:** 60 seconds

### 2a: Unauthorized Access (401)

| Step | Method | Endpoint | Auth | Expected Code | Expected Body |
|------|--------|----------|------|---------------|---------------|
| 1 | GET | /users/me | None | 401 | `{"error": {"code": "UNAUTHORIZED"}}` |
| 2 | POST | /vpr/generate | None | 401 | Error response |
| 3 | GET | /vpr/{vprId} | None | 401 | Error response |
| 4 | POST | /cv-tailoring/generate | None | 401 | Error response |
| 5 | POST | /cover-letter/generate | None | 401 | Error response |
| 6 | POST | /interview-prep/generate | None | 401 | Error response |
| 7 | GET | /company-research/{jobId} | None | 401 | Error response |
| 8 | GET | /jobs/{jobId} | None | 401 | Error response |

**Assertion:** All protected endpoints return 401 without auth. Unprotected endpoints (/auth/register, /auth/login, /health) return non-401.

### 2b: Invalid Input (400)

| Step | Method | Endpoint | Payload | Expected Code | Expected Error |
|------|--------|----------|---------|---------------|----------------|
| 1 | POST | /auth/register | `{"email": "invalid"}` | 400 | Validation error: email format |
| 2 | POST | /auth/register | `{"email": "a@b.com"}` (missing password) | 400 | Validation error: password required |
| 3 | POST | /jobs | `{}` (empty) | 400 | Validation error: title, company_name, description required |
| 4 | POST | /vpr/generate | `{"cv_id": "x"}` (missing job_id) | 400 | Validation error: job_id required |
| 5 | POST | /cv-tailoring/generate | `{"cv_id": "x"}` (neither pattern) | 400 | Validation error: must provide workflow or legacy pattern |
| 6 | POST | /gap-analysis/questions | `{}` | 400 | Validation error: cv_id, job_id required |

**Assertion:** Each 400 response includes `error.details` with field-level messages.

### 2c: Not Found (404)

| Step | Method | Endpoint | Expected Code |
|------|--------|----------|---------------|
| 1 | GET | /vpr/nonexistent-id | 404 |
| 2 | GET | /cv-tailoring/nonexistent-id | 404 |
| 3 | GET | /cover-letter/nonexistent-id | 404 |
| 4 | GET | /interview-prep/nonexistent-id | 404 |
| 5 | GET | /jobs/nonexistent-id | 404 |
| 6 | GET | /company-research/nonexistent-id | 404 |

### 2d: Prerequisites Not Met (422)

| Step | Method | Endpoint | Condition | Expected Code | Expected Error |
|------|--------|----------|-----------|---------------|----------------|
| 1 | POST | /vpr/generate | gap_response_ids pointing to non-existent responses | 422 | Prerequisites not met |
| 2 | POST | /cover-letter/generate | company_research_id that doesn't exist | 422 | Prerequisites not met |

---

## E2E Test 3: Async Failure and Recovery

**Description:** Validates async job failure handling, DLQ delivery, and manual retry.
**Timeout:** 300 seconds

### Step Sequence

| Step | Action | Expected | Assertion |
|------|--------|----------|-----------|
| 1 | POST /vpr/generate with valid payload | 202 | `request_id` returned |
| 2 | Simulate worker failure (e.g., by submitting with a cv_id that has corrupted data) | Worker throws exception | Job status transitions to PROCESSING then FAILED |
| 3 | Poll GET /vpr/{id} | 200 | `status == "failed"`, `error` message describes failure |
| 4 | Check DLQ message count | > 0 | `aws sqs get-queue-attributes --queue-url <dlq-url> --attribute-names ApproximateNumberOfMessages` |
| 5 | Fix underlying data issue | Data corrected | - |
| 6 | POST /vpr/generate with same cv_id + job_id | 202 | New `request_id` (idempotency key differs due to timestamp) |
| 7 | Poll until COMPLETED | 200 | `status == "completed"`, valid VPR result |

### DLQ Verification

```bash
# Check DLQ for failed messages
aws sqs get-queue-attributes \
  --queue-url "https://sqs.us-east-1.amazonaws.com/<account>/careervp-vpr-jobs-dlq-dev" \
  --attribute-names ApproximateNumberOfMessages \
  --region us-east-1

# Expected: ApproximateNumberOfMessages > 0 after worker failure

# Purge DLQ after test
aws sqs purge-queue --queue-url "https://sqs.us-east-1.amazonaws.com/<account>/careervp-vpr-jobs-dlq-dev"
```

---

## E2E Test 4: Quality Gates

**Description:** Validates FVS quality gates catch violations and trigger regeneration.
**Timeout:** 300 seconds

### Step Sequence

| Step | Action | Expected | Assertion |
|------|--------|----------|-----------|
| 1 | Complete full pipeline (steps 1-14 from E2E Test 1) | VPR generated | Baseline data ready |
| 2 | POST /cv-tailoring/generate | 202 | Processing starts |
| 3 | Poll until COMPLETED | 200 | Result available |
| 4 | Check FVS validation in response | `fvs_validation` object present | `is_valid` field exists |
| 5 | Verify anti-AI compliance | No banned words | Response text does not contain: leverage, delve, landscape, robust, streamline, utilize, facilitate, cutting-edge |
| 6 | Verify ATS score gate | >= 8.0 | `ats_score >= 8.0` |
| 7 | POST /cover-letter/generate | 202 | Processing starts |
| 8 | Poll until COMPLETED | 200 | Result available |
| 9 | Verify paragraph structure | 3 paragraphs | Hook (80-100 words), Proof (3 requirements), Close (60-80 words, CTA) |
| 10 | Verify anti-AI compliance | No banned words | Same check as step 5 |

### Anti-AI Detection Validation

```bash
# Banned words list (from prompt_library_spec.yaml)
BANNED_WORDS=("leverage" "delve" "landscape" "robust" "streamline" "utilize" "facilitate" "cutting-edge" "harness" "spearhead" "synergy" "paradigm" "holistic" "ecosystem" "empower" "revolutionize")

# Check VPR output
VPR_TEXT=$(echo "$VPR_RESULT" | jq -r '.result.strategic_narrative')
for word in "${BANNED_WORDS[@]}"; do
  if echo "$VPR_TEXT" | grep -qi "$word"; then
    echo "FAILED: Anti-AI violation - found '$word' in VPR output"
    exit 1
  fi
done

# Check Cover Letter output
CL_TEXT=$(echo "$CL_RESULT" | jq -r '.result.cover_letter')
for word in "${BANNED_WORDS[@]}"; do
  if echo "$CL_TEXT" | grep -qi "$word"; then
    echo "FAILED: Anti-AI violation - found '$word' in Cover Letter output"
    exit 1
  fi
done
```

---

## E2E Test 5: Contract Gate Validation

**Description:** Validates all 27 API operations are reachable and return expected status codes.
**Timeout:** 120 seconds

### All 27 Operations

| # | Method | Path | Auth | Expected Code | Category |
|---|--------|------|------|---------------|----------|
| 1 | POST | /auth/register | No | 201 or 400 | Auth |
| 2 | POST | /auth/login | No | 200 or 401 | Auth |
| 3 | POST | /auth/refresh | Yes | 200 or 401 | Auth |
| 4 | GET | /users/me | Yes | 200 or 401 | Users |
| 5 | PUT | /users/me | Yes | 200 or 401 | Users |
| 6 | POST | /users/me/cv | Yes | 201 or 400 | Users |
| 7 | GET | /users/me/cvs | Yes | 200 | Users |
| 8 | POST | /jobs | Yes | 201 or 400 | Jobs |
| 9 | GET | /jobs | Yes | 200 | Jobs |
| 10 | GET | /jobs/{jobId} | Yes | 200 or 404 | Jobs |
| 11 | POST | /vpr/generate | Yes | 202 or 400 | VPR |
| 12 | GET | /vpr/{vprId} | Yes | 200 or 404 | VPR |
| 13 | GET | /users/me/vprs | Yes | 200 | VPR |
| 14 | POST | /gap-analysis/questions | Yes | 200 or 400 | Gap Analysis |
| 15 | POST | /gap-analysis/responses | Yes | 200 or 400 | Gap Analysis |
| 16 | GET | /gap-analysis/{jobId}/questions | Yes | 200 | Gap Analysis |
| 17 | POST | /cv-tailoring/generate | Yes | 202 or 400 | CV Tailoring |
| 18 | GET | /cv-tailoring/{cvTailoringId} | Yes | 200 or 404 | CV Tailoring |
| 19 | GET | /users/me/tailored-cvs | Yes | 200 | CV Tailoring |
| 20 | POST | /cover-letter/generate | Yes | 202 or 400 | Cover Letter |
| 21 | GET | /cover-letter/{coverLetterId} | Yes | 200 or 404 | Cover Letter |
| 22 | GET | /users/me/cover-letters | Yes | 200 | Cover Letter |
| 23 | POST | /interview-prep/generate | Yes | 202 or 400 | Interview Prep |
| 24 | GET | /interview-prep/{interviewPrepId} | Yes | 200 or 404 | Interview Prep |
| 25 | POST | /company-research/fetch | Yes | 202 or 400 | Company Research |
| 26 | GET | /company-research/{jobId} | Yes | 200 or 404 | Company Research |
| 27 | GET | /health | No | 200 | Health |

**Pass Criteria:**
- No 404 "Missing Authentication Token" (indicates undeployed route)
- No 500 errors
- All authenticated endpoints return 401 when called without auth (not 403 or 404)

### Contract Gate Script

```bash
PASS=0
FAIL=0
TOTAL=27

for endpoint in "${ALL_ENDPOINTS[@]}"; do
  METHOD=$(echo "$endpoint" | cut -d'|' -f1)
  PATH=$(echo "$endpoint" | cut -d'|' -f2)
  AUTH=$(echo "$endpoint" | cut -d'|' -f3)

  HEADERS=(-H "Content-Type: application/json")
  [[ "$AUTH" == "yes" ]] && HEADERS+=(-H "Authorization: Bearer $TOKEN")

  CODE=$(curl -sS -o /dev/null -w "%{http_code}" -X "$METHOD" "$API_BASE$PATH" "${HEADERS[@]}")

  if [[ "$CODE" == "500" ]] || (echo "$BODY" | grep -q "Missing Authentication Token"); then
    echo "FAIL: $METHOD $PATH -> $CODE"
    ((FAIL++))
  else
    echo "PASS: $METHOD $PATH -> $CODE"
    ((PASS++))
  fi
done

echo "Contract Gate: $PASS/$TOTAL passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]] && echo "CONTRACT GATE PASSED" || echo "CONTRACT GATE FAILED"
```

---

## Test Execution Summary

| E2E Test | Duration | Steps | Key Validations |
|----------|----------|-------|-----------------|
| Test 1: Happy Path | ~10 min | 23 | Full pipeline, quality gates, STAR format |
| Test 2: Error Handling | ~1 min | 22 | 401, 400, 404, 422 error codes |
| Test 3: Async Failure | ~5 min | 7 | DLQ delivery, failure status, retry |
| Test 4: Quality Gates | ~5 min | 10 | Anti-AI, ATS >= 8.0, FVS validation |
| Test 5: Contract Gate | ~2 min | 27 | All 27 operations reachable |
| **Total** | **~23 min** | **89** | **All REFACTOR2 requirements** |

---

## Environment Configuration

```bash
# Required environment variables for E2E tests
export API_BASE="https://dev-api.careervp.com"
export TEST_USER_EMAIL="e2e-test@careervp.com"
export TEST_USER_PASSWORD="SecureP@ss123!"
export AWS_REGION="us-east-1"

# Stage environment option
# export API_BASE="https://stage-api.careervp.com"
```
