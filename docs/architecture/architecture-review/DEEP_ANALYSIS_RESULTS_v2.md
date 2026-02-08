# Deep Architecture Analysis Results (v2)

**Date:** 2026-02-09
**Reviewer:** Codex (GPT-5)
**Features Reviewed:** VPR, CV Tailoring
**Pending Features:** Cover Letter, Gap Analysis
**Prereq Status:** NOT MET (only 1 successful CV Tailoring run in dev; requirement is ≥ 10)
**Scope Note:** This is a provisional report produced per request despite unmet prerequisite. Update once the 10-run threshold is satisfied.

## Executive Summary

Overall Architecture Score: **3/5 (Adequate)**

| Category | Score | Status |
|---|---|---|
| Class Architecture | 3/5 | FAIL |
| Interoperability | 3/5 | FAIL |
| Extensibility | 3/5 | FAIL |
| Scalability | 3/5 | FAIL |
| Security | 3/5 | FAIL |
| Stability | 3/5 | FAIL |

**Critical Issues:** 1 blocking issue found
**Technical Debt:** 8 non-blocking improvements identified

## 0. Prerequisite Gate Findings

- The deep analysis gate requires ≥ 10 successful CV tailoring runs in dev. Current count: 1. This violates the Phase 2 prerequisite and blocks the official signoff.

## 1. Class Architecture Analysis

### SOLID Principles Assessment

#### Single Responsibility Principle
- **VPR**: **4/5**. `logic/vpr_generator.py` is a focused module with 4 top-level functions and 9 imports. Responsibilities are mostly cohesive.
- **CV Tailoring**: **3/5**. `logic/cv_tailoring_logic.py` is focused (2 methods, 10 imports), but `dal/dynamo_dal_handler.py` has 25 methods and 16 imports, making it a high-responsibility hub. `logic/fvs_validator.py` is a large procedural module (16 top-level functions) with mixed responsibilities (VPR + CV tailoring + utilities).

#### Open/Closed Principle
- **VPR**: **3/5**. Uses `logic/utils/llm_client.py` with `LLMRouter`, but still instantiates a concrete `LLMClient` inside `generate_vpr`.
- **CV Tailoring**: **2/5**. `logic/llm_client.py` is a direct Bedrock client without provider abstraction. Adding a new provider requires editing this module and call sites.

#### Liskov Substitution Principle
- **Overall**: **3/5**. There are few inheritance hierarchies. `DalHandler` is an ABC, but concrete usage often depends on `DynamoDalHandler` directly instead of the interface.

#### Interface Segregation Principle
- **Overall**: **3/5**. `DalHandler` aggregates many responsibilities (VPR, CV Tailoring, Cover Letter, Gap Analysis). This is a “fat interface” that forces clients to depend on methods they do not use.

#### Dependency Inversion Principle
- **VPR**: **3/5**. Logic depends on concrete `LLMClient` inside `generate_vpr` rather than injecting an abstraction.
- **CV Tailoring**: **4/5**. `CVTailoringLogic` accepts DAL and LLM client via constructor, but the handler constructs concrete implementations directly.

### Class Hierarchy Summary

- **Total classes:** 62
- **Pydantic models:** 39
- **Abstract/ABC classes:** 2 (`DalHandler`, `_SingletonMeta`)

### Key Abstractions

- `DalHandler` (ABC) as the DAL contract.
- `Result[T]` for cross-layer error handling.
- Pydantic models in `models/cv.py`, `models/fvs.py`, `models/cv_tailoring_models.py`, and `models/vpr.py`.

## 2. Interoperability Analysis

### Shared Models

- **UserCV** in `models/cv.py` is now shared across features.
- **Result[T]** in `models/result.py` is shared.
- CV tailoring-specific data lives in `models/cv_tailoring_models.py` and does not conflict with VPR.

### Shared Interfaces

- All features use `DynamoDalHandler`, but VPR and CV Tailoring use different LLM clients (`logic/utils/llm_client.py` vs `logic/llm_client.py`). This is inconsistent and increases maintenance cost.

### Cross-Feature Data Flow

- **VPR** persists artifacts and uses S3 download via `handlers/vpr_worker_handler.py` and `handlers/vpr_status_handler.py`.
- **CV Tailoring** persists artifacts to DynamoDB only and does not provide a download URL, even though `TailoredCVResponse.download_url` exists and `CV_TAILORING_DESIGN.md` expects S3 output.

**Interoperability Score:** 3/5. Shared models are consolidated, but storage and LLM interfaces diverge from the VPR reference pattern.

## 3. Extensibility Assessment

### A. Adding French Language Support

- **Estimated effort:** 12-20 hours.
- **Findings:** Prompts are English-only and do not accept a language parameter (`logic/cv_tailoring_prompt.py`). FVS validation logic is language-agnostic but not designed for multilingual field formats. No central language configuration exists.

### B. New Artifact Type (LinkedIn Summary)

- **Estimated effort:** 16-24 hours.
- **Findings:** Pattern exists (Handler → Logic → DAL), but requires new DAL methods, prompt builders, and model definitions. Some reusable logic exists (relevance scoring), but extraction is not centralized.

### C. Hook Points for Customization

- **CV Tailoring:** DAL and LLM are injectable in `CVTailoringLogic`; FVS is not an injectable strategy.
- **VPR:** LLM client is created inside `generate_vpr`; no injection point for alternate providers or validators.

**Extensibility Score:** 3/5.

## 4. Scalability Analysis

### DynamoDB Access Patterns

- **CV Tailoring:** Uses `PK=user_id`, `SK=ARTIFACT#CV_TAILORED#...`. This can create hot keys for power users; list queries are paginated in `list_tailored_cvs`, but latest-fetch (`get_tailored_cv` version None) does not paginate.
- **VPR:** Uses `PK=application_id` and GSI `user_id-index`. This is a more distributed pattern but increases GSI cost.

### Lambda Concurrency

- Reserved concurrency settings are not visible in code. Infra was not reviewed here, so this is **unknown**.

### Async vs Sync

- **VPR:** Async (SQS + polling) with retry patterns.
- **CV Tailoring:** Sync with retries at the LLM call level only. Risk if Haiku latency exceeds 30s or if request volume spikes.

**Scalability Score:** 3/5.

## 5. Security Review

### Critical Vulnerabilities

- **None identified in code**, but the prerequisite gate is not met (see Section 0).

### Medium Risks

- **FVS for VPR is disabled**, removing hallucination protection in production (`logic/vpr_generator.py`).
- **PII logging risk**: `cv_tailoring_handler.py` logs full event payload (includes job description). FVS violation logs can include emails/phones in clear text.
- **Prompt injection controls are minimal**: job descriptions are length-validated but not strongly delimited or sanitized.

### Compliance Checks (Code-Level)

- **PII Encryption:** Not verified here (infra not inspected).
- **Input Validation:** PASS for CV Tailoring (`validation/cv_tailoring_validation.py`).
- **Authentication/Authorization:** PASS for CV Tailoring (user_id extracted, ownership check in `CVTailoringLogic`).

**Security Score:** 3/5.

## 6. Stability Assessment

### Error Handling

- Both VPR and CV Tailoring use `Result[T]` consistently.
- DAL exceptions are caught and surfaced as 500s; no global error normalization beyond handler.

### Idempotency

- CV Tailoring uses job hash or `idempotency_key` but does not use conditional writes to prevent duplicates in concurrent scenarios.

### Retry Logic

- VPR uses retry decorator in `logic/utils/llm_client.py`.
- CV Tailoring uses `RetryingLLMClient` in `logic/cv_tailoring_logic.py`.

**Stability Score:** 3/5.

## Critical Issues (Blocking)

1. **Deep Analysis prerequisite not met** (10 successful dev runs required; only 1 confirmed).
   - Impact: High
   - Fix Effort: 1-2 hours (run 9 additional dev tailors + capture evidence)
   - Priority: P0

## Technical Debt (Non-Blocking)

1. **LLM client fragmentation**: VPR uses `logic/utils/llm_client.py`, CV Tailoring uses `logic/llm_client.py`.
   - Impact: Medium
   - Fix Effort: 6-10 hours
   - Priority: P1

2. **DynamoDalHandler is a “god class”** with 25 methods and multi-feature responsibilities.
   - Impact: Medium
   - Fix Effort: 8-16 hours
   - Priority: P1

3. **FVS module is large and mixed-use** (VPR + CV Tailoring + utilities).
   - Impact: Medium
   - Fix Effort: 6-12 hours
   - Priority: P2

4. **CV Tailoring output not stored in S3** despite design expectations.
   - Impact: Medium
   - Fix Effort: 8-12 hours
   - Priority: P1

5. **No strong prompt injection delimiters** in CV tailoring prompts.
   - Impact: Medium
   - Fix Effort: 2-4 hours
   - Priority: P2

6. **No rate limiting in CV tailoring** (stub exists but DAL does not implement).
   - Impact: Medium
   - Fix Effort: 4-8 hours
   - Priority: P2

7. **Idempotency is best-effort only** (no conditional writes).
   - Impact: Medium
   - Fix Effort: 4-6 hours
   - Priority: P2

8. **Coverage target not verified** (≥ 90% per module). Current pytest run is green, but no coverage report is attached.
   - Impact: Low
   - Fix Effort: 1-2 hours
   - Priority: P3

## Recommendations

### Immediate Actions (Before Cover Letter Implementation)
1. Complete 9 more dev CV tailoring runs and document evidence to satisfy the deep analysis prerequisite.
2. Align CV tailoring storage with design: generate and persist S3 artifacts + presigned download URLs.
3. Consolidate LLM clients to a single router-based interface and inject into logic layers.

### Short-Term Improvements (Within 1 Month)
1. Split `DynamoDalHandler` into feature-scoped DALs behind a shared interface to reduce coupling.
2. Modularize `fvs_validator.py` into feature-specific validators and a shared core.
3. Add prompt injection delimiters and metadata boundaries in CV tailoring prompts.

### Long-Term Refactoring (Within 3 Months)
1. Introduce a provider-agnostic LLM abstraction across all features with explicit strategy injection.
2. Add conditional writes for idempotency and race safety in artifact persistence.
3. Add structured PII redaction at logger boundaries.

## Appendix: Analysis Artifacts

### Mapping to Actual Files

- `cv_tailor_handler.py` → `src/backend/careervp/handlers/cv_tailoring_handler.py`
- `cv_tailoring_logic.py` → `src/backend/careervp/logic/cv_tailoring_logic.py`
- `models/cv_tailoring.py` → `src/backend/careervp/models/cv_tailoring_models.py`
- `tests/unit/test_cv_tailoring_logic.py` → `tests/cv-tailoring/unit/test_tailoring_logic.py`
- `tests/integration/test_cv_tailoring_flow.py` → `tests/cv-tailoring/integration/test_tailoring_handler_integration.py`

### Class Inventory (AST Scan)

- Total classes: 62
- Pydantic models: 39
- ABC classes: 2

### SRP Proxy Metrics (AST Scan)

- `logic/vpr_generator.py`: 9 imports, 4 functions
- `logic/cv_tailoring_logic.py`: 10 imports, 2 methods
- `logic/fvs_validator.py`: 10 imports, 16 functions
- `dal/dynamo_dal_handler.py`: 16 imports, 25 methods

### LSP Analysis

- LSP tools were not available in this environment. AST-based scans and ripgrep were used as a substitute.
