# CareerVP Refactoring Execution Runbook

**Document Version:** 4.1
**Date:** 2026-02-15
**Purpose:** Machine-readable execution guide for all refactoring phases
**Status:** API CONTRACT REMEDIATION + EXECUTION ORDER SYNC — NEW 2026-02-15

> **Status:** Phase -1 COMPLETE. All specs in `docs/refactor/specs/`
> **Infra Specs:** `infra/careervp/specs/`
> **Prompt Library:** `docs/refactor/specs/prompt_library_spec.yaml` (v2.0 - NOW WITH ACTUAL PROMPT TEXT)
> **Handler Status Matrix:** See `docs/refactor/specs/_registry.yaml` (handler_status_matrix section)

> **Test Directory Structure:**
> - `tests/unit/` - Generic tests (auth, validators, circuit breaker)
> - `tests/{feature}/unit/` - Feature-organized tests:
>   - `tests/cv-tailoring/unit/` (exists)
>   - `tests/gap_analysis/unit/` (exists)
>   - `tests/cover-letter/unit/` (exists)
>   - `tests/vpr-async/unit/` (exists)
>   - `tests/models/unit/` (create for Phase 1)
>   - `tests/cost_optimization/unit/` (create for Phase 2)
>   - `tests/quality_validator/unit/` (create for Phase 7)
>   - `tests/knowledge_base/unit/` (create for Phase 8)

> **Handler Patterns:**
> - Function-based Powertools (existing codebase pattern)
> - Pattern: `@app.post('/api/{feature}')` → function `handle_{feature}()`
> - Examples: `cv_upload_handler.py`, `cv_tailoring_handler.py`

> **File Creation Rules:**
> - ALWAYS check if file exists before creating
> - "Create" = new file, "Enhance/Consolidate" = existing file
> - Phase 1: models/cv.py, models/vpr.py, models/fvs.py already exist

---

## Quick Reference

### Backend Specs
```bash
cat docs/refactor/specs/_registry.yaml    # All specs with phase mapping
ls docs/refactor/specs/                  # All spec files
```

### Infrastructure Specs
```bash
cat infra/careervp/specs/_registry.yaml  # Infra specs with phase mapping
ls infra/careervp/specs/                # Infra spec files
```

### Verification
```bash
# Validate all YAML specs
python -c "
import yaml, os
for d in ['docs/refactor/specs', 'infra/careervp/specs']:
    for f in os.listdir(d):
        if f.endswith('.yaml'):
            yaml.safe_load(open(f'{d}/{f}'))
            print(f'{d}/{f}: ✅')
"
```

---

## Execution Sequence (Post-Phase-1) — NEW 2026-02-15

**Context:** Phase 0 and Phase 1 are already implemented.
This sequence identifies what to execute now to sync specs + API while preserving existing code and infrastructure.

### Required Order

1. **Phase 0 (Sub-step only):**
   - Step 0.4 (deployment spec handler pattern sync)
2. **Phase 1 (Sub-step only):**
   - Step 1.6.3 (spec sync gate)
3. **Phase 2**
4. **Phase 3**
5. **Phase 4**
6. **Phase 5**
7. **Phase 6**
8. **Phase 7**
9. **Phase 8**
10. **Phase X**
11. **Phase 9**
12. **Phase 10**
   - Start with Step 10.0a / 10.0b / 10.0c (infra-safe path migration)
   - Then Step 10.0 and Steps 10.1 – 10.12

**Why this order:** it preserves existing feature logic and infrastructure, then applies contract alignment after prerequisites are in place.

---

## Phase 0: Security Foundation

**Duration:** 1 day | **Effort:** 8 hours

> **⚠️ Handler Pattern Note:**
> `deployment_spec.yaml` specifies class-based handler patterns, but actual implementation uses function-based Powertools patterns. Follow existing patterns in `cv_upload_handler.py` and `cv_tailoring_handler.py` for consistency with the codebase.

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `security_spec.yaml` | Auth implementation |
| Reference | `vpc_spec.yaml` | VPC architecture |
| Reference | `circuit_breaker_spec.yaml` | Circuit breaker |
| Reference | `deployment_spec.yaml` | Lambda config |

### Step 0.1: Implement Auth Handler

**READ FIRST:**
- `docs/refactor/specs/security_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement API Authorizer per security_spec.yaml:

1. Create: src/backend/careervp/handlers/auth_handler.py
   - validate_token(token) -> bool
   - get_user_from_token(token) -> User

2. Create: tests/unit/test_auth_handler.py

KNOWLEDGE: docs/refactor/specs/security_spec.yaml (requirements section)
"""
```

### Step 0.2: Implement Validators

**READ FIRST:**
- `docs/refactor/specs/security_spec.yaml`

**HANDLER PATTERN:** Use function-based Powertools pattern (see cv_upload_handler.py)

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Implement validators per security_spec.yaml:

1. Create: src/backend/careervp/handlers/validators.py
   - validate_request(body) -> bool
   - validate_cv_upload(file) -> bool

2. Create: tests/unit/test_validators.py

NOTE: Alternative - Extend existing src/backend/careervp/validation/ package instead of handlers/validators.py if preferred

KNOWLEDGE: docs/refactor/specs/security_spec.yaml (requirements.SEC-002)
"""
```

### Step 0.3: Implement Circuit Breaker

**READ FIRST:**
- `docs/refactor/specs/circuit_breaker_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement CircuitBreaker per circuit_breaker_spec.yaml:

1. Create: src/backend/careervp/logic/circuit_breaker.py
   - Class: CircuitBreaker
   - States: CLOSED, OPEN, HALF_OPEN

2. Create: tests/unit/test_circuit_breaker.py

KNOWLEDGE: docs/refactor/specs/circuit_breaker_spec.yaml (implementation section)
"""
```

### Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Phase 0 tests
uv run pytest tests/unit/ -v --tb=short
# Files: test_auth_handler.py, test_validators.py, test_circuit_breaker.py

uv run ruff check careervp/handlers/ careervp/logic/circuit_breaker.py
uv run mypy careervp/handlers/ careervp/logic/circuit_breaker.py --strict
```

### Infrastructure (Optional - if infra needed)
```bash
# Run AFTER backend is implemented
cd infra/careervp

# Synthesize DynamoDB stacks
cdk synth

# Deploy (requires AWS credentials)
cdk deploy --all
```

### Step 0.4: Sync Deployment Spec Handler Pattern (Sub-step) — NEW 2026-02-15

**Context:** Phase 0 already implemented. This is a documentation/spec sync sub-step only.

**READ FIRST:**
- `docs/refactor/specs/deployment_spec.yaml`
- Existing handler implementations in `src/backend/careervp/handlers/`

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Update deployment_spec.yaml handler_patterns to match actual codebase:

1. Replace class-based pattern:
   - class: {Feature}Handler
   - methods: handle_{action}

2. With function-based Powertools pattern used in existing handlers:
   - lambda_handler(event, context) for API Gateway-routed handlers
   - optional @app.<method> route decorators for resolver-based handlers

3. Add note: API Gateway owns route mapping; handler routes omit /v1 stage prefix.
"""
```

**Validation:**
```bash
cd /Users/yitzchak/Documents/dev/careervp
python3 -c "import yaml; yaml.safe_load(open('docs/refactor/specs/deployment_spec.yaml')); print('DEPLOYMENT_SPEC: VALID')"
```

### Live Test (Phase 0 - Infrastructure)
```bash
# Run AFTER successful CDK deployment to AWS
# Payload: docs/refactor/payloads/phase0_infrastructure_test.json

cd /Users/yitzchak/Documents/dev/careervp

# Test DynamoDB Knowledge Base connectivity
curl -X PUT "https://api.careervp.com/v1/knowledge/test" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/refactor/payloads/phase0_infrastructure_test.json

# Expected: 200 OK with success=true
# Verify: Item retrievable via GET
```

---

## Phase 1: Model Unification

**Duration:** 3 days | **Effort:** 22 hours

### Existing Files (DO NOT OVERWRITE)
| File | Status | Contains |
|------|--------|----------|
| `models/cv.py` | EXISTS | SkillLevel, Skill, CVSection, WorkExperience, Education, UserCV, CVParseRequest, CVParseResponse |
| `models/vpr.py` | EXISTS | EvidenceItem, VPR (with executive_summary, evidence_matrix, differentiators, gap_strategies) |
| `models/fvs.py` | EXISTS | ViolationSeverity, FVSViolation, FVSValidationResult |
| `models/cv_models.py` | EXISTS | Duplicate of cv.py - consolidate into cv.py |
| `models/fvs_models.py` | EXISTS | Duplicate of fvs.py - consolidate into fvs.py |

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `models_spec.yaml` | Model definitions |
| Reference | `architectural_findings_spec.yaml` | Layer rules |
| Reference | `test_strategy_spec.yaml` | Test patterns |

### Step 1.1: Consolidate CV Models

**READ FIRST:**
- `docs/refactor/specs/models_spec.yaml` (model definitions)
- `docs/refactor/specs/architectural_findings_spec.yaml` (layer rules - LAYER-003)
- `docs/refactor/specs/test_strategy_spec.yaml` (TDD pattern, 80% unit coverage)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Consolidate CV models per models_spec.yaml + architectural_findings_spec.yaml:

1. ENHANCE: src/backend/careervp/models/cv.py
   - Keep existing: SkillLevel, Skill, CVSection, WorkExperience, Education, UserCV, CVParseRequest, CVParseResponse
   - Add from cv_models.py if missing
   - Per architectural_findings_spec.yaml LAYER-003: Move models from handlers/models/ and dal/models/ to /models
   - DO NOT DELETE cv_models.py - update imports in cv_tailoring_handler first

2. Create: tests/models/unit/test_cv_models.py (NEW FOLDER)
   - Per test_strategy_spec.yaml: TDD pattern (write test first)
   - Unit coverage target: 80%

MAPPING: spec "CVData" → existing "UserCV"
MAPPING: spec "CVSection" → existing "CVSection"
MAPPING: spec "WorkExperience" → existing "WorkExperience"
MAPPING: spec "Education" → existing "Education"
MAPPING: spec "Skill" → existing "Skill"

After consolidation: Update cv_tailoring_handler.py imports from cv_models.py to cv.py
"""

KNOWLEDGE: docs/refactor/specs/models_spec.yaml (categories.CV models)
KNOWLEDGE: docs/refactor/specs/architectural_findings_spec.yaml (consolidation_targets)
KNOWLEDGE: docs/refactor/specs/test_strategy_spec.yaml (tdd_pattern, test_pyramid)
KNOWLEDGE: cv_tailoring_handler.py imports from careervp.models.cv_models
```

**VALIDATION (Secondary Prompt - Run After Completion):**
```bash
# VSCode + Anthropic Haiku
"""
Validate Step 1.1 consolidation was successful:

1. Verify cv.py has all expected models:
   grep -E "class (UserCV|WorkExperience|Education|Skill|SkillLevel|CVSection|CVParseRequest|CVParseResponse)" careervp/models/cv.py

2. Verify cv_models.py still exists (not deleted):
   ls -la careervp/models/cv_models.py

3. Verify cv_tailoring_handler.py imports from cv.py (not cv_models.py):
   grep "from careervp.models" careervp/handlers/cv_tailoring_handler.py
   grep "import.*UserCV\|import.*WorkExperience" careervp/handlers/cv_tailoring_handler.py

4. Verify test file exists:
   ls -la tests/models/unit/test_cv_models.py

5. Run lint and type check:
   uv run ruff check careervp/models/cv.py careervp/models/cv_models.py
   uv run mypy careervp/models/cv.py careervp/models/cv_models.py --strict

DONE when:
- All 7 models in cv.py
- cv_models.py exists (not deleted)
- cv_tailoring_handler.py imports from cv.py
- test_cv_models.py exists
- ruff check passes (no errors)
- mypy --strict passes (no errors)
"""

KNOWLEDGE: src/backend/careervp/models/cv.py (consolidated file)
KNOWLEDGE: src/backend/careervp/models/cv_models.py (source file - still exists)
KNOWLEDGE: src/backend/careervp/handlers/cv_tailoring_handler.py (updated imports)
```

### Step 1.2: Consolidate VPR Models

**READ FIRST:**
- `docs/refactor/specs/models_spec.yaml` (VPR model definitions)
- `docs/refactor/specs/architectural_findings_spec.yaml` (layer rules - LAYER-003)
- `docs/refactor/specs/test_strategy_spec.yaml` (TDD pattern, 80% unit coverage)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Consolidate VPR models per models_spec.yaml + architectural_findings_spec.yaml:

1. ENHANCE: src/backend/careervp/models/vpr.py
   - Keep existing: EvidenceItem, VPR (with executive_summary, evidence_matrix, differentiators, gap_strategies)
   - Add new if missing: ValueProposition, Achievement, TargetRole
   - Per architectural_findings_spec.yaml LAYER-003: Move models from handlers/models/ and dal/models/ to /models

2. Create: tests/models/unit/test_vpr_models.py (NEW FOLDER)
   - Per test_strategy_spec.yaml: TDD pattern (write test first)
   - Unit coverage target: 80%

MAPPING: spec "VPRData" → existing "VPR"
MAPPING: spec "ValueProposition" → NEW (add to vpr.py)
MAPPING: spec "Achievement" → NEW (add to vpr.py)
MAPPING: spec "TargetRole" → NEW (add to vpr.py)
"""

KNOWLEDGE: docs/refactor/specs/models_spec.yaml (categories.VPR models)
KNOWLEDGE: docs/refactor/specs/architectural_findings_spec.yaml (consolidation_targets)
KNOWLEDGE: docs/refactor/specs/test_strategy_spec.yaml (tdd_pattern, test_pyramid)
```

**VALIDATION (Secondary Prompt - Run After Completion):**
```bash
# VSCode + Anthropic Haiku
"""
Validate Step 1.2 consolidation was successful:

1. Verify vpr.py has all expected models:
   grep -E "class (VPR|EvidenceItem|ValueProposition|Achievement|TargetRole)" careervp/models/vpr.py

2. Check for VPR-related handlers that may need import updates:
   grep -r "from.*vpr_models\|from.*handlers.models.vpr" careervp/handlers/ careervp/logic/ 2>/dev/null | grep -v ".pyc"

3. Verify test file exists:
   ls -la tests/models/unit/test_vpr_models.py

4. Run lint and type check:
   uv run ruff check careervp/models/vpr.py
   uv run mypy careervp/models/vpr.py --strict

DONE when:
- VPR, EvidenceItem, ValueProposition, Achievement, TargetRole all in vpr.py
- Any vpr_models imports in handlers/logic updated to vpr.py
- test_vpr_models.py exists
- ruff check passes (no errors)
- mypy --strict passes (no errors)
"""

KNOWLEDGE: src/backend/careervp/models/vpr.py (consolidated file)
KNOWLEDGE: src/backend/careervp/handlers/ (check for vpr_models imports)
```

### Step 1.3: Consolidate FVS Models

**READ FIRST:**
- `docs/refactor/specs/models_spec.yaml` (FVS model definitions)
- `docs/refactor/specs/architectural_findings_spec.yaml` (layer rules - LAYER-003)
- `docs/refactor/specs/test_strategy_spec.yaml` (TDD pattern, 80% unit coverage)

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Consolidate FVS models per models_spec.yaml + architectural_findings_spec.yaml:

1. ENHANCE: src/backend/careervp/models/fvs.py
   - Keep existing: ViolationSeverity, FVSViolation, FVSValidationResult
   - Add new if missing: FVSResult, QualityScore, GrammarIssue, ToneIssue
   - Per architectural_findings_spec.yaml LAYER-003: Move models from handlers/models/ and dal/models/ to /models
   - DO NOT DELETE fvs_models.py - consolidate into fvs.py

2. Create: tests/models/unit/test_fvs_models.py (NEW FOLDER)
   - Per test_strategy_spec.yaml: TDD pattern (write test first)
   - Unit coverage target: 80%

MAPPING: spec "FVSResult" → NEW (add to fvs.py)
MAPPING: spec "QualityScore" → NEW (add to fvs.py)
MAPPING: spec "GrammarIssue" → NEW (add to fvs.py)
MAPPING: spec "ToneIssue" → NEW (add to fvs.py)
MAPPING: spec "FVSValidationResult" → existing "FVSValidationResult"
"""

KNOWLEDGE: docs/refactor/specs/models_spec.yaml (categories.FVS models)
KNOWLEDGE: docs/refactor/specs/architectural_findings_spec.yaml (consolidation_targets)
KNOWLEDGE: docs/refactor/specs/test_strategy_spec.yaml (tdd_pattern, test_pyramid)
```

**VALIDATION (Secondary Prompt - Run After Completion):**
```bash
# VSCode + Anthropic Haiku
"""
Validate Step 1.3 consolidation was successful:

1. Verify fvs.py has all expected models:
   grep -E "class (FVSValidationResult|ViolationSeverity|FVSViolation|FVSResult|QualityScore|GrammarIssue|ToneIssue)" careervp/models/fvs.py

2. Verify fvs_models.py still exists (not deleted):
   ls -la careervp/models/fvs_models.py

3. Check for FVS-related handlers/logic that may need import updates:
   grep -r "from.*fvs_models\|from.*handlers.models.fvs" careervp/handlers/ careervp/logic/ 2>/dev/null | grep -v ".pyc"

4. Verify test file exists:
   ls -la tests/models/unit/test_fvs_models.py

5. Run lint and type check:
   uv run ruff check careervp/models/fvs.py careervp/models/fvs_models.py
   uv run mypy careervp/models/fvs.py careervp/models/fvs_models.py --strict

DONE when:
- ViolationSeverity, FVSViolation, FVSValidationResult, FVSResult, QualityScore, GrammarIssue, ToneIssue all in fvs.py
- fvs_models.py exists (not deleted)
- Any fvs_models imports in handlers/logic updated to fvs.py
- test_fvs_models.py exists
- ruff check passes (no errors)
- mypy --strict passes (no errors)
"""

KNOWLEDGE: src/backend/careervp/models/fvs.py (consolidated file)
KNOWLEDGE: src/backend/careervp/models/fvs_models.py (source file - still exists)
KNOWLEDGE: src/backend/careervp/handlers/ (check for fvs_models imports)
KNOWLEDGE: src/backend/careervp/logic/ (check for fvs_models imports)
```

### Phase 1 Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/models/unit/ -v  # NEW FOLDER
uv run ruff check careervp/models/
uv run mypy careervp/models/ --strict
```

### Live Test (Phase 1 - VPR Generator)
```bash
# Run AFTER Phase 1 model consolidation
# Payload: docs/refactor/payloads/phase1_vpr_generator_test.json

cd /Users/yitzchak/Documents/dev/careervp

# 1. Generate VPR (async)
curl -X POST "https://api.careervp.com/v1/vpr/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/refactor/payloads/phase1_vpr_generator_test.json


curl -X POST "https://4xe2tdq8z6.execute-api.us-east-1.amazonaws.com/prod/vpr" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/refactor/payloads/phase1_vpr_generator_test.json
# Expected: 202 Accepted with request_id

# 2. Poll for completion (timeout: 120s)
REQUEST_ID="<from_step_1>"
for i in {1..24}; do
  STATUS=$(curl -s "https://api.careervp.com/v1/vpr/$REQUEST_ID" \
    -H "Authorization: Bearer $TOKEN" | jq -r '.status')

  if [ "$STATUS" == "completed" ]; then
    echo "SUCCESS: VPR generated"
    curl -s "https://api.careervp.com/v1/vpr/$REQUEST_ID" \
      -H "Authorization: Bearer $TOKEN" | jq '.result'
    exit 0
  fi

  sleep 5
done

echo "TIMEOUT: VPR not completed in 120 seconds"
exit 1
```

**Expected Results:**
- `uvp`: Generated UVP statement
- `differentiators`: List with evidence sources
- `strategic_narrative`: Coherent career story
- `persuasion_score`: >= 7.0
- `completeness_score`: >= 7.0

---

## Phase 1.5: JSA Prompt Library Completion

**Duration:** 0.5 days | **Effort:** 4 hours

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `prompt_library_spec.yaml` (v3.0) | Complete prompt library |
| Reference | `CRITICAL_CORRECTIONS.md` | Original requirements |

### Step 1.5.1: Create Interview Prep Prompt

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Create interview_prep_prompt.py per prompt_library_spec.yaml v3.0:

1. Create: src/backend/careervp/logic/prompts/interview_prep_prompt.py
   - System prompt for STAR-formatted questions
   - User prompt template
   - Output schema with predicted_questions, star_response, key_points

2. Create: tests/unit/test_interview_prep_prompt.py

KNOWLEDGE: docs/refactor/specs/prompt_library_spec.yaml (interview_prep_complete section)
"""
```

### Step 1.5.2: Create FVS Prompt

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Create fvs_prompt.py per prompt_library_spec.yaml v3.0:

1. Create: src/backend/careervp/logic/prompts/fvs_prompt.py
   - Grammar validation prompt
   - Tone validation prompt
   - Anti-AI detection prompt
   - Output schema with scores (grammar, tone, anti_ai, formatting)

2. Create: tests/unit/test_fvs_prompt.py

KNOWLEDGE: docs/refactor/specs/prompt_library_spec.yaml (fvs_validation section)
"""
```

### Step 1.5.3: Create Knowledge Base Prompt

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Create knowledge_base_prompt.py per prompt_library_spec.yaml v3.0:

1. Create: src/backend/careervp/logic/prompts/knowledge_base_prompt.py
   - Knowledge storage prompt
   - Knowledge retrieval prompt
   - Output schema with entities, tags, priority, ttl_days

2. Create: tests/unit/test_knowledge_base_prompt.py

KNOWLEDGE: docs/refactor/specs/prompt_library_spec.yaml (knowledge_base section)
"""
```

### Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/unit/test_interview_prep_prompt.py tests/unit/test_fvs_prompt.py tests/unit/test_knowledge_base_prompt.py -v

uv run ruff check careervp/logic/prompts/
uv run mypy careervp/logic/prompts/ --strict
```

---

## Phase 1.6: API Contract Documentation

**Duration:** 0.5 days | **Effort:** 4 hours

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `api_contract_spec.yaml` | Quick reference (endpoints, tags, operationIds) |
| Authoritative | `../swagger/careervp-api-v1.yaml` | Full OpenAPI 3.0.3 spec with schemas |

### Step 1.6.1: Document API Endpoints

**AUTHORITATIVE SOURCE:** `docs/swagger/careervp-api-v1.yaml` (full schemas, examples)
**QUICK REFERENCE:** `docs/refactor/specs/api_contract_spec.yaml` (endpoints, tags, operationIds)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement API contract per api_contract_spec.yaml:

1. Create: src/backend/careervp/api_contract.py
   - Endpoint definitions with methods
   - Request schemas (Pydantic models)
   - Response schemas (standard format)
   - Error codes

2. Create: tests/integration/test_api_contract.py

KNOWLEDGE:
- docs/refactor/specs/api_contract_spec.yaml (quick reference)
- docs/swagger/careervp-api-v1.yaml (authoritative schemas)

Important: Use the OpenAPI spec for detailed schemas and examples.
The api_contract_spec.yaml provides a quick reference for
endpoints, tags, operationIds, and async patterns.
"""
```

### Step 1.6.2: Sync with OpenAPI Spec

The OpenAPI spec (`careervp-api-v1.yaml`) is the authoritative source.
When updating API contracts:

1. Update `docs/swagger/careervp-api-v1.yaml` for schema changes
2. Update `docs/refactor/specs/api_contract_spec.yaml` for quick reference

**KEY SECTIONS:**
- 10 tags (Auth, Users, Jobs, VPR, Gap Analysis, CV Tailoring, Cover Letter, Interview Prep, Company Research, Health)
- 27 endpoints total
- 5 async endpoints (202 responses) with polling patterns
- Pagination on list endpoints (/users/me/*, /jobs)

### Step 1.6.3: Spec Sync Gate (Sub-step) — NEW 2026-02-15

**Context:** Phase 1 already implemented. This sub-step aligns specs before continuing feature/contract implementation.

**Objective:** Sync specs with OpenAPI + Phase 10 matrix while retaining existing code and infrastructure.

**CHECKLIST:**
1. `_registry.yaml`:
   - Remove duplicate `interview_prep_spec.yaml` entries
   - Add `phase_10` mapping
   - Update handler_status_matrix for Phase 10 handlers
2. Feature specs:
   - Align `gap_analysis_spec.yaml` endpoints to OpenAPI
   - Align `cover_letter_spec.yaml` and `interview_prep_spec.yaml` to async + status/list patterns
   - Align `cv_tailoring_spec.yaml` to async + status/list patterns
   - Align `vpr_6stage_spec.yaml` handler references with async VPR submit/status handlers
3. Company research specs:
   - Use `GET /company-research/{jobId}` (not `{company_name}`)
4. Keep `docs/swagger/careervp-api-v1.yaml` as authoritative source.

**Validation:**
```bash
cd /Users/yitzchak/Documents/dev/careervp

python3 -c "import yaml; yaml.safe_load(open('docs/refactor/specs/_registry.yaml')); print('REGISTRY: VALID')"
python3 -c "import yaml; yaml.safe_load(open('docs/refactor/specs/api_contract_spec.yaml')); print('API_CONTRACT: VALID')"
python3 -c "import yaml; yaml.safe_load(open('docs/refactor/specs/gap_analysis_spec.yaml')); print('GAP_SPEC: VALID')"
python3 -c "import yaml; yaml.safe_load(open('docs/refactor/specs/cover_letter_spec.yaml')); print('COVER_SPEC: VALID')"
python3 -c "import yaml; yaml.safe_load(open('docs/refactor/specs/interview_prep_spec.yaml')); print('INTERVIEW_SPEC: VALID')"
python3 -c "import yaml; yaml.safe_load(open('docs/refactor/specs/cv_tailoring_spec.yaml')); print('CV_TAILORING_SPEC: VALID')"
python3 -c "import yaml; yaml.safe_load(open('docs/refactor/specs/vpr_6stage_spec.yaml')); print('VPR_SPEC: VALID')"

# Legacy endpoint patterns should be absent from specs after sync
rg -n "/gap-analysis/generate|/gap-analysis/\\{id\\}|/company-research/\\{company_name\\}" docs/refactor/specs/ || true
```

### Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Validate both YAML specs
python3 -c "import yaml; yaml.safe_load(open('../swagger/careervp-api-v1.yaml')); print('OPENAPI: VALID')"
python3 -c "import yaml; yaml.safe_load(open('../refactor/specs/api_contract_spec.yaml')); print('REF: VALID')"

uv run pytest tests/integration/test_api_contract.py -v

uv run ruff check careervp/api_contract.py
uv run mypy careervp/api_contract.py --strict
```

---

## Phase 1.7: Workflow Dependencies

**Duration:** 0.5 days | **Effort:** 4 hours

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `workflow_dependencies_spec.yaml` | Workflow documentation |

### Step 1.7.1: Implement Workflow Enforcer

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement workflow dependencies per workflow_dependencies_spec.yaml:

1. Create: src/backend/careervp/logic/workflow_enforcer.py
   - WorkflowContext class
   - WorkflowEnforcer class
   - validate_prerequisites() method
   - get_available_features() method

2. Create: tests/unit/test_workflow_enforcer.py

KNOWLEDGE: docs/refactor/specs/workflow_dependencies_spec.yaml
"""
```

### Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/unit/test_workflow_enforcer.py -v

uv run ruff check careervp/logic/workflow_enforcer.py
uv run mypy careervp/logic/workflow_enforcer.py --strict
```

---

## Phase 1.8: LLM Client Migration

**Duration:** 1 day | **Effort:** 8 hours

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `llm_client_migration_spec.yaml` | Migration documentation |

### Step 1.8.1: Create Anthropic Client

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Create Anthropic client per llm_client_migration_spec.yaml:

1. Create: src/backend/careervp/logic/anthropic_client.py
   - AnthropicClient class
   - Direct HTTP calls to Anthropic API
   - Cost calculation
   - Rate limiting

2. Create: src/backend/careervp/logic/llm_router.py
   - LLMRouter class
   - Model routing (Sonnet/Haiku)

3. Create: src/backend/careervp/logic/cost_estimator.py
   - CostEstimator class
   - Token usage tracking

4. Create: src/backend/careervp/logic/rate_limiter.py
   - RateLimiter class
   - Circuit breaker pattern

5. Create: tests/unit/test_anthropic_client.py
6. Create: tests/unit/test_llm_router.py
7. Create: tests/unit/test_cost_estimator.py

KNOWLEDGE: docs/refactor/specs/llm_client_migration_spec.yaml
"""
```

### Step 1.8.2: Migrate LLM Client

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Migrate llm_client.py per llm_client_migration_spec.yaml:

1. UPDATE: src/backend/careervp/logic/llm_client.py
   - Replace Bedrock with Anthropic
   - Add model routing
   - Add cost tracking

2. Run: tests/unit/test_llm_client.py

KNOWLEDGE: docs/refactor/specs/llm_client_migration_spec.yaml
"""
```

### Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/unit/test_anthropic_client.py tests/unit/test_llm_router.py tests/unit/test_cost_estimator.py -v

uv run ruff check careervp/logic/anthropic_client.py careervp/logic/llm_router.py
uv run mypy careervp/logic/anthropic_client.py careervp/logic/llm_router.py --strict
```

---

## Phase 1.9: Tasks Alignment

**Duration:** 0.5 days | **Effort:** 4 hours

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `tasks_alignment_spec.yaml` | Tasks mapping |

### Step 1.9.1: Create Alignment Matrix

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Create tasks alignment per tasks_alignment_spec.yaml:

1. Create: src/backend/careervp/tasks_alignment.py
   - TasksAlignment class
   - Phase-to-task mapping
   - get_alignment_report() method

2. Create: tests/unit/test_tasks_alignment.py

KNOWLEDGE: docs/refactor/specs/tasks_alignment_spec.yaml
"""
```

### Step 1.9.2: Consolidate Duplicate Tasks

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Consolidate duplicate task directories:

1. Merge 03-vpr-generator/ and 12-vpr-generator/
2. Merge 06-cv-tailoring/ and 09-cv-tailoring/
3. Merge 07-cover-letter/ and 10-cover-letter/
4. Merge 08-gap-analysis/ and 11-gap-analysis/

Update docs/tasks/README.md with consolidated structure.
"""
```

### Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/unit/test_tasks_alignment.py -v

uv run ruff check careervp/tasks_alignment.py
uv run mypy careervp/tasks_alignment.py --strict
```

---

## Phase 2: Cost Optimization + LLM Caching

**Duration:** 2.5 days | **Effort:** 20 hours

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `cost_optimization_spec.yaml` | CV Summarizer, Cache |
| Reference | `circuit_breaker_spec.yaml` | Resilience patterns |

### Step 2.1: Implement CV Summarizer

**READ FIRST:**
- `docs/refactor/specs/cost_optimization_spec.yaml` (Strategy 1)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement CV Summarizer per cost_optimization_spec.yaml Strategy 1:

1. Create: src/backend/careervp/logic/cv_summarizer.py
   - extract_highlights(cv) -> str (500 tokens)
   - Target: 500 tokens from ~5000 token CV

2. Create: tests/unit/test_cv_summarizer.py

KNOWLEDGE: docs/refactor/specs/cost_optimization_spec.yaml (strategies[0])
"""
```

### Step 2.2: Implement LLM Content Cache

**READ FIRST:**
- `docs/refactor/specs/cost_optimization_spec.yaml` (Strategy 2)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement LLM Content Cache per cost_optimization_spec.yaml Strategy 2:

1. Create: src/backend/careervp/logic/llm_content_cache.py
   - cache_cv_context(cv_id, context) - TTL: 24 hours
   - cache_job_requirements(job_id, reqs) - TTL: 1 hour
   - cache_company_research(company, research) - TTL: 30 days

2. Create: tests/unit/test_llm_content_cache.py

KNOWLEDGE: docs/refactor/specs/cost_optimization_spec.yaml (strategies[1])
"""
```

### Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/cost_optimization/unit/ -v  # NEW FOLDER
uv run ruff check careervp/logic/
uv run mypy careervp/logic/ --strict
```

### Live Test (Phase 2 - Gap Analysis)
```bash
# Run AFTER CV Summarizer and LLM Cache implementation
# Payload: docs/refactor/payloads/phase2_gap_analysis_test.json

cd /Users/yitzchak/Documents/dev/careervp

# 1. Generate gap questions
curl -X POST "https://api.careervp.com/v1/gap-analysis/questions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/refactor/payloads/phase2_gap_analysis_test.json

# Expected: 200 OK with questions array

# 2. Submit responses
curl -X POST "https://api.careervp.com/v1/gap-analysis/responses" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/refactor/payloads/phase2_gap_analysis_test.json

# Expected: 200 OK with impact statements
```

**Validation:**
- Questions: 3-10 generated
- Tags: [CV IMPACT], [INTERVIEW/MVP ONLY] enforced
- Missing qualifications identified

---

## Phase 3: VPR 6-Stage Generator

**Duration:** 1.5 days | **Effort:** 10 hours

### Existing Files (DO NOT OVERWRITE)
| File | Status | Contains |
|------|--------|----------|
| `logic/vpr_generator.py` | EXISTS | VPR generator logic |
| `logic/prompts/vpr_prompt.py` | EXISTS | VPR prompts |

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `vpr_6stage_spec.yaml` | VPR implementation (6 stages) |
| Reference | `test_strategy_spec.yaml` | Test patterns |
| Reference | `prompt_library_spec.yaml` | Prompt: vpr_generation (Sonnet 4.5, STRATEGIC) |

### Step 3.1: Enhance VPR Generator

**CODE:**
```bash
# VSCode + Anthropic Opus (complex architecture)
"""
Enhance VPR Generator per vpr_6stage_spec.yaml:

1. ENHANCE: src/backend/careervp/logic/vpr_generator.py
   - Add Stage 6: _final_meta_evaluation() -> FinalVPRData
   - Keep existing stages 1-5 implementation
   - Verify 6-stage process matches spec

2. Create: tests/vpr-async/unit/test_vpr_generator.py (use existing folder)

DO NOT CREATE NEW FILE - vpr_generator.py already exists
"""

KNOWLEDGE: docs/refactor/specs/vpr_6stage_spec.yaml (stages section - 6 stages total)
PROMPTS: docs/refactor/specs/prompt_library_spec.yaml (prompts.vpr_generation)
  - Existing prompt: src/backend/careervp/logic/prompts/vpr_prompt.py (IMPLEMENTED)
  - Model: Claude Sonnet 4.5 (STRATEGIC mode), temp=0.7, max_tokens=8192
  - Output: JSON with executive_summary, evidence_matrix, differentiators, gap_strategies
  - Anti-AI: Apply banned_words list + check_anti_ai_patterns() post-generation
"""
```

### Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/vpr-async/unit/ -v
uv run ruff check careervp/logic/vpr_generator.py
uv run mypy careervp/logic/vpr_generator.py --strict
```

### Live Test (Phase 3 - VPR 6-Stage)
```bash
# Run AFTER VPR 6-Stage enhancement
# Payload: docs/refactor/payloads/phase1_vpr_generator_test.json

cd /Users/yitzchak/Documents/dev/careervp

# 1. Submit VPR generation request
curl -X POST "https://api.careervp.com/v1/vpr/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/refactor/payloads/phase1_vpr_generator_test.json

# Expected: 202 Accepted

# 2. Poll and verify 6-stage completion
REQUEST_ID="<from_step_1>"
for i in {1..24}; do
  RESULT=$(curl -s "https://api.careervp.com/v1/vpr/$REQUEST_ID" \
    -H "Authorization: Bearer $TOKEN")

  STATUS=$(echo $RESULT | jq -r '.status')

  if [ "$STATUS" == "completed" ]; then
    echo "SUCCESS: 6-Stage VPR complete"
    echo $RESULT | jq '.result'
    exit 0
  fi
  sleep 5
done
echo "TIMEOUT"
exit 1
```

**Validation (6-Stage):**
- Stage 1: Company & Role Research → company_research included
- Stage 2: Candidate Analysis → achievements extracted
- Stage 3: Alignment Mapping → explicit table created
- Stage 4: Self-Correction → meta-review passed
- Stage 5: Report Generation → UVP + proof points
- Stage 6: Meta Evaluation → persuasion_score >= 7.0

---

## Phase 4: CV Tailoring 3-Step

**Duration:** 1.5 days | **Effort:** 11 hours

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `cv_tailoring_spec.yaml` | CV tailoring |
| Reference | `test_strategy_spec.yaml` | Gate tests |
| Reference | `prompt_library_spec.yaml` | Prompt: cv_tailoring (Haiku 4.5, TEMPLATE) |

### Step 4.1: Implement CV Tailoring Logic

**READ FIRST:**
- `docs/refactor/specs/cv_tailoring_spec.yaml`
- `docs/refactor/specs/prompt_library_spec.yaml` (prompts.cv_tailoring)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement CV Tailoring per cv_tailoring_spec.yaml:

File Structure (ALREADY EXISTS - ENHANCE ONLY):
1. src/backend/careervp/logic/cv_tailoring.py (CORE FUNCTION - canonical)
   - tailor_cv() - already exists, verify 3-step process

2. src/backend/careervp/logic/cv_tailoring_logic.py (ORCHESTRATION - already exists)
   - CVTailoringLogic class - handles DAL + orchestrates tailor_cv()
   - Verify dependency injection pattern

Handler imports from: cv_tailoring.tailor_cv

DO NOT CREATE NEW FILES - These files already exist.
ENHANCE: Verify 3-step process (_analyze, _self_correct, _generate)

2. Update: tests/unit/test_cv_tailoring_logic.py

KNOWLEDGE: docs/refactor/specs/cv_tailoring_spec.yaml (three_step_process)
PROMPTS: docs/refactor/specs/prompt_library_spec.yaml (prompts.cv_tailoring)
  - Existing prompts:
    * src/backend/careervp/logic/cv_tailoring_prompt.py (IMPLEMENTED - basic system/user)
    * docs/tasks/09-cv-tailoring/task-04-tailoring-prompt.md (PSEUDO_CODE - extended with few-shot)
  - Model: Claude Haiku 4.5 (TEMPLATE mode), temp=0.3, max_tokens=4096
  - Output: JSON TailoredCV with original_bullets, relevance_score, keyword_alignments
  - Anti-AI: Apply 8-pattern framework + FVS tier classification
  - Few-shot: 5 examples covering different career transitions
"""
```

### Step 4.2: Enhance CV Tailoring Handler

**READ FIRST:**
- `docs/refactor/specs/cv_tailoring_spec.yaml`
- `cv_tailoring_handler.py` (existing imports)

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Enhance CV Tailoring Handler per cv_tailoring_spec.yaml:

1. ENHANCE: src/backend/careervp/handlers/cv_tailoring_handler.py
   - Already exists with: CustomJSONEncoder, CVTable imports
   - Verify handler function-based pattern (@app.post)
   - Check imports: from careervp.logic.cv_tailoring import tailor_cv

2. Update: tests/cv-tailoring/unit/test_cv_tailoring_handler.py

DO NOT CREATE NEW FILE - cv_tailoring_handler.py already exists
"""

KNOWLEDGE: docs/refactor/specs/cv_tailoring_spec.yaml (implementation)
KNOWLEDGE: cv_tailoring_handler.py imports from careervp.logic.cv_tailoring
```
```

### Step 4.3: Create Gate Tests

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Create Gate Tests per cv_tailoring_spec.yaml:

1. Create: tests/cv-tailoring/unit/test_cv_tailoring_gates.py

Test all 10 gates per cv_tailoring_spec.yaml minimum_scores:
1. matching_experience >= 9.0
2. career_changer >= 7.5
3. leadership_role >= 8.0
4. senior_skills_gap >= 7.0
5. recent_graduate >= 7.5
6. remote_first >= 8.0
7. startup_culture >= 8.0
8. industry_transition >= 7.5
9. contract_to_perm >= 8.0
10. employment_gap >= 7.0

USE EXISTING FOLDER: tests/cv-tailoring/unit/
"""

KNOWLEDGE: docs/refactor/specs/cv_tailoring_spec.yaml (gate_tests section)
KNOWLEDGE: docs/refactor/specs/test_strategy_spec.yaml (cv_tailoring_gates section)
```

### Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Phase 4 tests
uv run pytest tests/cv-tailoring/unit/ -v --tb=short
# Files: test_cv_tailoring_handler.py, test_cv_tailoring_logic.py, test_cv_tailoring_gates.py,
#        test_tailoring_dal_unit.py, test_tailoring_models.py, test_tailoring_prompt.py,
#        test_fvs_integration.py, test_validation.py

uv run ruff check careervp/logic/cv_tailoring_logic.py careervp/handlers/cv_tailoring_handler.py
uv run mypy careervp/logic/cv_tailoring_logic.py careervp/handlers/cv_tailoring_handler.py --strict
```

### Live Test (Phase 4 - CV Tailoring)
```bash
# Run AFTER CV Tailoring 3-Step implementation
# Payload: docs/refactor/payloads/phase3_cv_tailoring_test.json

cd /Users/yitzchak/Documents/dev/careervp

# 1. Generate tailored CV
curl -X POST "https://api.careervp.com/v1/cv-tailoring/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/refactor/payloads/phase3_cv_tailoring_test.json

# Expected: 202 Accepted

# 2. Poll for completion
REQUEST_ID="<from_step_1>"
for i in {1..24}; do
  RESULT=$(curl -s "https://api.careervp.com/v1/cv-tailoring/$REQUEST_ID" \
    -H "Authorization: Bearer $TOKEN")

  STATUS=$(echo $RESULT | jq -r '.status')

  if [ "$STATUS" == "completed" ]; then
    echo "SUCCESS: CV Tailored"
    echo $RESULT | jq '.result'
    exit 0
  fi
  sleep 5
done
echo "TIMEOUT"
exit 1
```

**Validation (3-Step Process):**
- Step 1 (Analysis): Keywords extracted (12-18)
- Step 2 (Self-Correction): ATS score calculated
- Step 3 (Finalize): ATS >= 8.0, FVS validated

**Gate Tests:**
- matching_experience >= 9.0
- career_changer >= 7.5
- leadership_role >= 8.0
- senior_skills_gap >= 7.0
- recent_graduate >= 7.5
- remote_first >= 8.0
- startup_culture >= 8.0
- industry_transition >= 7.5
- contract_to_perm >= 8.0
- employment_gap >= 7.0

---

## Phase 5: Gap Analysis

**Duration:** 2 days | **Effort:** 13 hours

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `gap_analysis_spec.yaml` | Gap analysis |
| Reference | `cost_optimization_spec.yaml` | Cost targets |
| Reference | `prompt_library_spec.yaml` | Prompt: gap_analysis (Sonnet 4.5, STRATEGIC) |

### Step 5.1: Implement Gap Questions Generator

**READ FIRST:**
- `docs/refactor/specs/gap_analysis_spec.yaml`
- `docs/refactor/specs/prompt_library_spec.yaml` (prompts.gap_analysis)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement Gap Questions Generator per gap_analysis_spec.yaml:

1. Create: src/backend/careervp/logic/gap_questions.py
   - Class: GapQuestionsGenerator
   - generate_questions(job_requirements) -> List[GapQuestion]
   - identify_recurring_themes(gap_responses) -> List[str]
   - Max questions: 10

2. Create: tests/unit/test_gap_questions.py

KNOWLEDGE: docs/refactor/specs/gap_analysis_spec.yaml (components.GapQuestionsGenerator)
PROMPTS: docs/refactor/specs/prompt_library_spec.yaml (prompts.gap_analysis)
  - Existing prompt: src/backend/careervp/logic/prompts/gap_analysis_prompt.py (IMPLEMENTED)
  - Model: Claude Sonnet 4.5 (STRATEGIC mode), temp=0.3, max_tokens=4096
  - Output: JSON with questions (max 10), identified_gaps
"""
```

### Step 5.2: Implement Gap Responses Handler

**READ FIRST:**
- `docs/refactor/specs/gap_analysis_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement Gap Responses Handler per gap_analysis_spec.yaml:

1. Create: src/backend/careervp/logic/gap_responses.py
   - Class: GapResponsesHandler
   - save_response(user_email, application_id, response) -> Result
   - get_responses(application_id) -> List[GapResponse]

2. Create: tests/unit/test_gap_responses.py

KNOWLEDGE: docs/refactor/specs/gap_analysis_spec.yaml (components.GapResponsesHandler)
"""
```

### Step 5.3: Implement Gap Processor

**READ FIRST:**
- `docs/refactor/specs/gap_analysis_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement Gap Processor per gap_analysis_spec.yaml:

1. Create: src/backend/careervp/logic/gap_processor.py
   - Class: GapProcessor
   - process_gaps(cv_facts, job_requirements) -> GapAnalysisResult
   - generate_impact_statements(gap_responses) -> List[ImpactStatement]

2. Create: tests/unit/test_gap_processor.py

KNOWLEDGE: docs/refactor/specs/gap_analysis_spec.yaml (components.GapProcessor)
"""
```

### Step 5.4: Implement Gap Handler

**READ FIRST:**
- `docs/refactor/specs/gap_analysis_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Implement Gap Analysis Handler per gap_analysis_spec.yaml:

1. Enhance: src/backend/careervp/handlers/gap_handler.py
   - Lambda handler with Powertools
   - Handles: question generation, response submission, processing
   - Preserve existing CORS helpers and error response utilities

2. Create: tests/unit/test_gap_handler.py

KNOWLEDGE: docs/refactor/specs/gap_analysis_spec.yaml (implementation)
"""
```

### Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/gap_analysis/unit/ -v --tb=short
uv run ruff check careervp/logic/gap_*.py careervp/handlers/gap_handler.py
uv run mypy careervp/logic/gap_*.py careervp/handlers/gap_handler.py --strict
```

### Live Test (Phase 5 - Gap Analysis)
```bash
# Run AFTER Gap Analysis implementation
# Payload: docs/refactor/payloads/phase2_gap_analysis_test.json

cd /Users/yitzchak/Documents/dev/careervp

# 1. Generate questions
curl -X POST "https://api.careervp.com/v1/gap-analysis/questions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/refactor/payloads/phase2_gap_analysis_test.json

# Expected: 200 OK with questions array (3-10)

# 2. Submit responses
curl -X POST "https://api.careervp.com/v1/gap-analysis/responses" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/refactor/payloads/phase2_gap_analysis_test.json

# Expected: 200 OK with impact statements
```

**Validation:**
- Questions tagged with [CV IMPACT], [INTERVIEW/MVP ONLY]
- Strategic intent included for each question
- Missing qualifications identified
- Impact statements generated for CV enhancement

### Infrastructure
```bash
cd infra/careervp

# READ: infra/careervp/specs/dynamodb_spec.yaml
cat infra/careervp/specs/dynamodb_spec.yaml | grep -A5 "careervp-gap-responses"

# CDK: DynamoDB Table - careervp-gap-responses
# File: infra/careervp/dynamodb_stack.py (already created)
# Verify Table: gap_responses_table is defined

# Synthesize
cdk synth

# Deploy
cdk deploy --all
```

---

## Phase 6: Cover Letter

**Duration:** 2 days | **Effort:** 13 hours

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `cover_letter_spec.yaml` | Cover letter |
| Reference | `test_strategy_spec.yaml` | Quality tests |
| Reference | `prompt_library_spec.yaml` | Prompt: cover_letter (Haiku 4.5, TEMPLATE) |

### Step 6.1: Implement Cover Letter Generator

**READ FIRST:**
- `docs/refactor/specs/cover_letter_spec.yaml`
- `docs/refactor/specs/prompt_library_spec.yaml` (prompts.cover_letter)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement Cover Letter Generator per cover_letter_spec.yaml:

1. Create: src/backend/careervp/logic/cover_letter.py
   - Class: CoverLetterGenerator
   - generate(options) -> CoverLetterResult
   - Paragraph 1: Hook (80-100 words)
   - Paragraph 2: Proof Points
   - Paragraph 3: Close (60-80 words, CTA)

2. Create: tests/unit/test_cover_letter_generator.py

KNOWLEDGE: docs/refactor/specs/cover_letter_spec.yaml (structure section)
PROMPTS: docs/refactor/specs/prompt_library_spec.yaml (prompts.cover_letter)
  - Existing prompt: src/backend/careervp/logic/prompts/cover_letter_prompt.py (IMPLEMENTED)
  - Model: Claude Haiku 4.5 (TEMPLATE mode), temp=0.5, max_tokens=4096
  - System prompt params: tone (professional|conversational|technical), word_count_target
  - Output: Text with 3-paragraph structure
  - Anti-AI: Apply banned_words + natural transitions
"""
```

### Step 6.2: Implement Cover Letter Handler

**READ FIRST:**
- `docs/refactor/specs/cover_letter_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Implement Cover Letter Handler per cover_letter_spec.yaml:

1. Create: src/backend/careervp/handlers/cover_letter_handler.py
   - Lambda handler with Powertools
   - Input validation
   - Calls CoverLetterGenerator

2. Create: tests/unit/test_cover_letter_handler.py

KNOWLEDGE: docs/refactor/specs/cover_letter_spec.yaml (implementation)
"""
```

### Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/cover-letter/unit/ -v --tb=short
uv run ruff check careervp/logic/cover_letter.py careervp/handlers/cover_letter_handler.py
uv run mypy careervp/logic/cover_letter.py careervp/handlers/cover_letter_handler.py --strict
```

### Live Test (Phase 6 - Cover Letter)
```bash
# Run AFTER Cover Letter implementation
# Payload: docs/refactor/payloads/phase4_cover_letter_test.json

cd /Users/yitzchak/Documents/dev/careervp

# 1. Generate cover letter
curl -X POST "https://api.careervp.com/v1/cover-letter/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/refactor/payloads/phase4_cover_letter_test.json

# Expected: 202 Accepted

# 2. Poll for completion
LETTER_ID="<from_step_1>"
for i in {1..18}; do
  RESULT=$(curl -s "https://api.careervp.com/v1/cover-letter/$LETTER_ID" \
    -H "Authorization: Bearer $TOKEN")

  STATUS=$(echo $RESULT | jq -r '.status')

  if [ "$STATUS" == "completed" ]; then
    echo "SUCCESS: Cover Letter generated"
    echo $RESULT | jq '.result'
    exit 0
  fi
  sleep 5
done
echo "TIMEOUT"
exit 1
```

**Validation (3-Paragraph Structure):**
- Paragraph 1 (Hook): 80-100 words, includes UVP + company reference
- Paragraph 2 (Proof Points): 3 requirements mapped, quantified evidence
- Paragraph 3 (Close): 60-80 words, includes CTA
- FVS Validation: is_valid=true, violations=[]

---

## Phase 7: Quality Validator (FVS)

**Duration:** 1.5 days | **Effort:** 12 hours

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `fvs_spec.yaml` | Quality validation |
| Reference | `test_strategy_spec.yaml` | Quality tests |
| Reference | `prompt_library_spec.yaml` | Prompt: quality_validation (Sonnet 4.5, STRATEGIC) |

### Step 7.1: Implement Quality Validator

**READ FIRST:**
- `docs/refactor/specs/fvs_spec.yaml`
- `docs/refactor/specs/prompt_library_spec.yaml` (prompts.quality_validation)

**CODE:**
```bash
# VSCode + Anthropic Opus (complex validation)
"""
Implement Quality Validator per fvs_spec.yaml:

1. Enhance: src/backend/careervp/logic/fvs_validator.py
   - Class: QualityValidator
   - validate(content) -> FVSResult
   - Grammar >= 9.0
   - Tone >= 8.0
   - Anti-AI Patterns >= 9.0
   - Formatting >= 8.0

2. Create: tests/unit/test_quality_validator.py

KNOWLEDGE: docs/refactor/specs/fvs_spec.yaml (validation_checks section)
PROMPTS: docs/refactor/specs/prompt_library_spec.yaml (prompts.quality_validation)
  - TO_BE_CREATED: src/backend/careervp/logic/prompts/quality_validation_prompt.py
  - Model: Claude Sonnet 4.5 (STRATEGIC mode), temp=0.1, max_tokens=2048
  - Output: JSON with grammar_score, tone_score, anti_ai_score, formatting_score, issues[]
"""
```

### Step 7.2: FVS Handler Clarification

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
FVS is used inline by other features (cover letter, CV tailoring).
Per fvs_spec.yaml: handler_status: "N/A"

1. DO NOT create standalone handler unless explicitly required
2. FVS is called via: QualityValidator.validate() in other logic modules

USE EXISTING FOLDER: tests/cv-tailoring/unit/ or tests/cover-letter/unit/ for inline FVS tests
"""

KNOWLEDGE: docs/refactor/specs/fvs_spec.yaml (handler_status: N/A)
```
```

### Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# FVS tests - inline in feature folders + unit tests
uv run pytest tests/unit/test_quality_validator.py tests/cv-tailoring/unit/ tests/cover-letter/unit/ -v --tb=short
# Files: test_quality_validator.py (unit), test_fvs_integration.py (feature folders)

uv run ruff check careervp/logic/fvs_validator.py
uv run mypy careervp/logic/fvs_validator.py --strict
```

### Live Test (Phase 7 - Quality Validator)
```bash
# Run AFTER Quality Validator enhancement
# Payload: docs/refactor/payloads/phase5_quality_validator_test.json

cd /Users/yitzchak/Documents/dev/careervp

# Validate content
curl -X POST "https://api.careervp.com/v1/quality-validate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/refactor/payloads/phase5_quality_validator_test.json

# Expected: 200 OK with scores
```

**Validation Scores:**
- Grammar: >= 9.0
- Tone: >= 8.0
- Anti-AI: >= 9.0
- Formatting: >= 8.0
- Issues: 0

---

## Phase 8: Knowledge Base

**Duration:** 1.5 days | **Effort:** 12 hours

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `knowledge_base_spec.yaml` | Repository |
| Reference | `deployment_spec.yaml` | DynamoDB/S3 naming convention |
| Reference | `infra/careervp/specs/dynamodb_spec.yaml` | Table schemas (GAP_RESPONSES, KNOWLEDGE) |

### Step 8.1: Implement Knowledge Repository

**READ FIRST:**
- `docs/refactor/specs/knowledge_base_spec.yaml`
- `infra/careervp/specs/dynamodb_spec.yaml` (GAP_RESPONSES_TABLE_NAME, KNOWLEDGE_TABLE_NAME)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement Knowledge Repository per knowledge_base_spec.yaml:

1. Create: src/backend/careervp/dal/knowledge_repository.py
   - Class: KnowledgeRepository
   - save_gap_response(response) -> Result
   - get_gap_responses(user_email, application_id) -> List[GapResponse]
   - save_company_research(company, research) -> Result
   - get_company_research(company) -> CompanyResearch

2. Create: tests/unit/test_knowledge_repository.py

KNOWLEDGE: docs/refactor/specs/knowledge_base_spec.yaml (methods section)
KNOWLEDGE: infra/careervp/specs/dynamodb_spec.yaml (table schemas)
  - careervp-gap-responses-table-dev (PK: user_email, SK: application_id)
  - careervp-knowledge-table-dev (PK: user_email, SK: entity_type)
TTL: gap_responses(24mo), company_research(30d), cv_context(24h)
"""
```

### Step 8.2: Implement Knowledge Handler

**READ FIRST:**
- `docs/refactor/specs/knowledge_base_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Implement Knowledge Base Handler per knowledge_base_spec.yaml:

1. Create: src/backend/careervp/handlers/knowledge_base_handler.py
   - Lambda handler with Powertools

2. Create: tests/unit/test_knowledge_base_handler.py

KNOWLEDGE: docs/refactor/specs/knowledge_base_spec.yaml (implementation)
"""
```

### Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Phase 8 tests - PENDING SOURCE IMPLEMENTATION
# Files: test_knowledge_repository.py, test_knowledge_base_handler.py
uv run pytest tests/knowledge_base/unit/ -v --tb=short

uv run ruff check careervp/dal/knowledge_repository.py careervp/handlers/knowledge_base_handler.py
uv run mypy careervp/dal/knowledge_repository.py careervp/handlers/knowledge_base_handler.py --strict
```

### Infrastructure
```bash
cd infra/careervp

# DynamoDB Tables (Phase 8)
# READ: infra/careervp/specs/dynamodb_spec.yaml
cat infra/careervp/specs/dynamodb_spec.yaml | grep -A5 "careervp-knowledge"

# CDK: DynamoDB Table - careervp-knowledge
# File: infra/careervp/dynamodb_stack.py (already created)
# Verify Table: knowledge_table is defined

# S3 Buckets (Phase 4, Phase 6)
# READ: infra/careervp/specs/s3_spec.yaml
cat infra/careervp/specs/s3_spec.yaml

# CDK: S3 Buckets
# File: infra/careervp/s3_stack.py (already created)
# Verify Buckets: cvs_bucket, generated_bucket are defined

# Synthesize
cdk synth

# Deploy
cdk deploy --all
```

### Live Test (Phase 8 - Knowledge Base)
```bash
# Run AFTER Knowledge Base implementation
# Payload: docs/refactor/payloads/phase7_knowledge_base_test.json

cd /Users/yitzchak/Documents/dev/careervp

# Store knowledge entities
curl -X PUT "https://api.careervp.com/v1/knowledge" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/refactor/payloads/phase7_knowledge_base_test.json

# Expected: 200 OK with success=true, items_stored=4

# Verify retrieval
curl -X GET "https://api.careervp.com/v1/knowledge/jane@example.com" \
  -H "Authorization: Bearer $TOKEN"

# Expected: All 4 items retrievable
```

**Validation:**
- CRUD operations: All working
- TTL functionality: Applied correctly
- Skip recurring themes: Working
- Prioritize by job: Working

---

## Phase X: Company Research Transformation

**Duration:** 1 day | **Effort:** 8 hours

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `company_research_transform_spec.yaml` | Transformation layer spec |
| Reference | `knowledge_base_spec.yaml` | Storage requirements |
| Reference | `dynamodb_spec.yaml` | DynamoDB schema |
| Reference | `company_research_model_spec.yaml` | Model specification |
| Reference | `company_research_fvs_spec.yaml` | FVS validation spec |
| Reference | `company_research_payload_spec.yaml` | Test payload spec |
| Reference | `company_research_e2e_spec.yaml` | E2E test spec |

### Step X.0: Validate Prerequisites

**CODE:**
```bash
# Check existing state before starting
ls -la docs/refactor/specs/ | grep company
ls -la src/backend/careervp/models/ | grep company
ls -la src/backend/careervp/logic/ | grep company
ls -la tests/ | grep -r company

# Verify spec files exist
cat docs/refactor/specs/company_research_transform_spec.yaml | head -10
cat docs/refactor/specs/company_research_model_spec.yaml | head -10
cat docs/refactor/specs/company_research_fvs_spec.yaml | head -10
cat docs/refactor/specs/company_research_payload_spec.yaml | head -10
cat docs/refactor/specs/company_research_e2e_spec.yaml | head -10
```

**Validation:**
- All 5 spec files exist and are readable
- Source model file exists: `src/backend/careervp/models/company.py`
- Logic directory exists: `src/backend/careervp/logic/`
- DAL directory exists: `src/backend/careervp/dal/`

### Step X.1: Extend CompanyResearchResult Model

**READ FIRST:**
- `docs/refactor/specs/company_research_transform_spec.yaml` (section 4.2)
- `src/backend/careervp/models/company.py` (existing model)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Extend CompanyResearchResult per company_research_transform_spec.yaml section 4.2:

1. ENHANCE: src/backend/careervp/models/company.py
   - Add to_research_dict() method
   - Add from_research_dict() classmethod
   - Keep existing fields: company_name, overview, values, mission, strategic_priorities, recent_news, financial_summary

2. Create: tests/unit/test_company_research_model.py

DO NOT DELETE existing fields - extend only.

KNOWLEDGE: docs/refactor/specs/company_research_transform_spec.yaml (section 4.2)
"""
```

### Step X.2: Create CompanyResearchTransformer

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Create CompanyResearchTransformer per company_research_transform_spec.yaml section 4.1:

1. Create: src/backend/careervp/logic/company_research_transformer.py
   - DynamoDBItem dataclass (user_email, entity_type, entity_id, cached_at, ttl, research_data)
   - CompanyResearchTransformer class
   - to_dynamodb_item() method (LLM → DynamoDB)
   - from_dynamodb_item() method (DynamoDB → structured)
   - calculate_ttl() method (30 days)

2. Create: tests/unit/test_company_research_transformer.py

KNOWLEDGE: docs/refactor/specs/company_research_transform_spec.yaml (section 4.1)
"""
```

### Step X.3: Update KnowledgeRepository

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Update KnowledgeRepository per company_research_transform_spec.yaml section 5:

1. ENHANCE: src/backend/careervp/dal/knowledge_repository.py
   - Add save_company_research() method
   - Add get_company_research() method
   - Add cache check logic
   - Add TTL expiration check

2. Create: tests/integration/test_company_research_flow.py

KNOWLEDGE: docs/refactor/specs/company_research_transform_spec.yaml (section 5)
"""
```

### Step X.4: Create Company Research Prompt

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Extract company research prompt to separate file:

1. Create: src/backend/careervp/logic/prompts/company_research_prompt.py
   - Extract inline prompt from company.py
   - Include system prompt
   - Include user prompt template
   - Include output schema (CompanyResearchResult)

KNOWLEDGE: docs/refactor/specs/company_research_transform_spec.yaml (section 1)
"""
```

### Step X.5: Update Infrastructure (CDK)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Add GSI to DynamoDB stack per company_research_transform_spec.yaml section 7:

1. ENHANCE: infra/careervp/dynamodb_stack.py
   - Add GSI: entity-index (entity_type → entity_id)
   - Reference: dynamodb_spec.yaml

2. ADD to: infra/careervp/constants.py
   - KNOWLEDGE_TABLE_NAME = "knowledge"

KNOWLEDGE: docs/refactor/specs/company_research_transform_spec.yaml (section 7)
"""
```

### Step X.FVS: Integrate FVS Validation

**READ FIRST:**
- `docs/refactor/specs/company_research_fvs_spec.yaml`
- `src/backend/careervp/logic/fvs_validator.py` (existing validator)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Integrate FVS validation for company research:

1. ENHANCE: src/backend/careervp/logic/fvs_validator.py
   - Add validate_company_research() method
   - Grammar score >= 9.0
   - Anti-AI score >= 9.0
   - Block AI buzzwords per spec

2. Update: src/backend/careervp/dal/knowledge_repository.py
   - Add FVS validation call before save_company_research() DynamoDB write
   - Handle validation failure gracefully (return Result with error)

3. Create: tests/unit/test_company_research_fvs.py
   - test_valid_company_research_passes
   - test_low_grammar_score_fails
   - test_ai_buzzword_detection
   - test_missing_section_fails

KNOWLEDGE: docs/refactor/specs/company_research_fvs_spec.yaml
"""
```

**Verification:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/unit/test_company_research_fvs.py -v

uv run ruff check careervp/logic/fvs_validator.py

uv run mypy careervp/logic/fvs_validator.py --strict
```

### Step X.PAYLOAD: Create Test Payloads

**READ FIRST:**
- `docs/refactor/specs/company_research_payload_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Create test payload files:

1. Create: docs/refactor/payloads/phase8_company_research_live_test.json
   - Full live test payload per spec

2. Create: docs/refactor/payloads/phase8_company_research_unit_test.json
   - Unit test data with edge cases (4 test cases)

3. Create: docs/refactor/payloads/phase8_company_research_integration.json
   - Integration test scenarios (3 scenarios)

KNOWLEDGE: docs/refactor/specs/company_research_payload_spec.yaml
"""
```

**Validation:**
```bash
# Verify JSON syntax
python -m json.tool docs/refactor/payloads/phase8_company_research_live_test.json > /dev/null
python -m json.tool docs/refactor/payloads/phase8_company_research_unit_test.json > /dev/null
python -m json.tool docs/refactor/payloads/phase8_company_research_integration.json > /dev/null
```

### Step X.E2E: Create E2E Tests

**READ FIRST:**
- `docs/refactor/specs/company_research_e2e_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Create end-to-end tests:

1. Create: tests/e2e/test_company_research_e2e.py
   - Test E2E-COMP-001: User researches company and retrieves
   - Test E2E-COMP-002: Cache hit prevents duplicate generation
   - Test E2E-COMP-003: Expired TTL triggers regeneration
   - Test E2E-COMP-004: FVS validation failure rejects content

KNOWLEDGE: docs/refactor/specs/company_research_e2e_spec.yaml
"""
```

**Verification:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Dry run (no AWS calls)
uv run pytest tests/e2e/test_company_research_e2e.py -v --tb=short -k "not live"

# Full run with AWS profile
uv run pytest tests/e2e/test_company_research_e2e.py -v --aws-profile=careervp-dev
```

### Step X.LIVE: Create Live Test Script

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Create live test script:

1. Create: scripts/live_test_company_research.sh
   - Generate research (POST /v1/company-research/fetch)
   - Retrieve research (GET /v1/company-research/{jobId})
   - Verify DynamoDB storage (aws dynamodb get-item)
   - Verify TTL is set (30 days from now)
   - Test cache hit (second POST returns cached=true)
   - Cleanup (delete test item from DynamoDB)

KNOWLEDGE: docs/refactor/specs/company_research_transform_spec.yaml section 12
"""
```

**Execution:**
```bash
bash scripts/live_test_company_research.sh
```

### Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Run unit tests
uv run pytest tests/unit/test_company_research_transformer.py tests/unit/test_company_research_model.py -v

# Run integration tests
uv run pytest tests/integration/test_company_research_flow.py -v

# Run lint
uv run ruff check careervp/logic/company_research_transformer.py careervp/models/company.py

# Run type check
uv run mypy careervp/logic/company_research_transformer.py --strict
```

### Live Test (Phase X - Company Research)
```bash
# Run AFTER Company Research transformation implementation
# Payload: docs/refactor/payloads/phase8_company_research_live_test.json

cd /Users/yitzchak/Documents/dev/careervp

# 1. Generate company research
curl -X POST "https://api.careervp.com/v1/company-research/fetch" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/refactor/payloads/phase8_company_research_live_test.json

# Expected: 200 OK with research_id

# 2. Retrieve research
curl -X GET "https://api.careervp.com/v1/company-research/$JOB_ID" \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK with all fields

# 3. Run live test script
bash scripts/live_test_company_research.sh
```

**Validation:**
- Transformation: All 6 fields preserved
- Storage: DynamoDB item with JSON blob
- TTL: 30 days expiration
- Cache: Second request returns cached=true

---

## Phase 9: Interview Prep

**Duration:** 2 days | **Effort:** 16 hours

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `interview_prep_spec.yaml` | Interview prep |
| Reference | `test_strategy_spec.yaml` | Test patterns |
| Reference | `prompt_library_spec.yaml` | Prompt: interview_prep (Haiku 4.5, TEMPLATE) |

### Step 9.1: Implement Interview Prep Generator

**READ FIRST:**
- `docs/refactor/specs/interview_prep_spec.yaml`
- `docs/refactor/specs/prompt_library_spec.yaml` (prompts.interview_prep)

**NOTE:** Check docs/refactor/specs/_registry.yaml for duplicate interview_prep_spec.yaml entries and remove duplicate

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement Interview Prep Generator per interview_prep_spec.yaml:

1. Create: src/backend/careervp/logic/interview_prep.py
   - Class: InterviewPrepGenerator
   - generate_questions(gap_responses, vpr) -> List[InterviewQuestion]
   - generate_answers(question, cv_facts) -> InterviewAnswer
   - prioritize_questions(questions) -> List[InterviewQuestion]

2. Create: tests/unit/test_interview_prep.py

KNOWLEDGE: docs/refactor/specs/interview_prep_spec.yaml (components section)
PROMPTS: docs/refactor/specs/prompt_library_spec.yaml (prompts.interview_prep)
  - TO_BE_CREATED: src/backend/careervp/logic/prompts/interview_prep_prompt.py
  - Model: Claude Haiku 4.5 (TEMPLATE mode), temp=0.5, max_tokens=4096
  - Output: JSON with questions (max 10), model_answer, key_points, follow_up_questions
Constraints: max_questions = 10
"""
```

### Step 9.2: Implement Interview Handler

**READ FIRST:**
- `docs/refactor/specs/interview_prep_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Implement Interview Prep Handler per interview_prep_spec.yaml:

1. Create: src/backend/careervp/handlers/interview_prep_handler.py
   - Lambda handler with Powertools

2. Create: tests/unit/test_interview_prep_handler.py

KNOWLEDGE: docs/refactor/specs/interview_prep_spec.yaml (implementation)
"""
```

### Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Phase 9 tests - PENDING SOURCE IMPLEMENTATION
# Files: test_interview_prep_handler.py (pending), test_interview_prep_logic.py (pending),
#        test_interview_prep_prompt.py (CREATED)
uv run pytest tests/unit/test_interview_prep*.py tests/unit/test_interview_prep_prompt.py -v --tb=short

uv run ruff check careervp/logic/interview_prep.py careervp/handlers/interview_prep_handler.py
uv run mypy careervp/logic/interview_prep.py careervp/handlers/interview_prep_handler.py --strict
```

### Live Test (Phase 9 - Interview Prep)
```bash
# Run AFTER Interview Prep implementation
# Payload: docs/refactor/payloads/phase6_interview_prep_test.json

cd /Users/yitzchak/Documents/dev/careervp

# Generate interview questions
curl -X POST "https://api.careervp.com/v1/interview-prep/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/refactor/payloads/phase6_interview_prep_test.json

# Expected: 200 OK with questions array (8-10)
```

**Validation:**
- Questions generated: 8-10
- Categories: technical, behavioral, situational
- STAR format: enforced
- Model answers: included
- Follow-up questions: generated

### Live Test (Phase 9 - E2E Workflow Integration)
```bash
# Run AFTER all phases implemented
# Payload: docs/refactor/payloads/phase9_workflow_integration_test.json

cd /Users/yitzchak/Documents/dev/careervp

# Execute full workflow
bash scripts/test_workflow_e2e.sh \
  --payload @docs/refactor/payloads/phase9_workflow_integration_test.json

# Expected: All 9 steps complete successfully
```

**E2E Validation:**
- Order enforced: CV → Gap → VPR → Tailor → Cover → Interview
- Dependencies: Required
- Knowledge Base: Updated throughout
- Total time: < 15 minutes
- Success rate: 100%

---

## Phase 10: API Contract Remediation — NEW 2026-02-15

**Duration:** 5 days | **Effort:** 40 hours
**Depends on:** Phases 0–9 (feature logic implemented)
**Purpose:** Ensure 100% coverage of all 27 OpenAPI endpoints in `docs/swagger/careervp-api-v1.yaml`

> **Gap Summary:** Current codebase has 5 partially-implemented handlers with path/schema mismatches,
> 1 stub-only handler (gap_handler.py), and 19 completely missing endpoints.
> This phase closes every gap so the deployed API matches the OpenAPI contract exactly.

### Specs
| Type | File | Purpose |
|------|------|---------|
| Authoritative | `../swagger/careervp-api-v1.yaml` | Full OpenAPI 3.0.3 spec |
| Reference | `api_contract_spec.yaml` | Quick reference (endpoints, tags, operationIds) |
| Reference | `security_spec.yaml` | Auth requirements |
| Reference | `workflow_dependencies_spec.yaml` | Prerequisite enforcement |

### Endpoint Coverage Matrix

| # | OpenAPI Path | Method | operationId | Auth | Async | Current Handler | Gap Type |
|---|-------------|--------|-------------|------|-------|-----------------|----------|
| 1 | `/auth/register` | POST | registerUser | No | No | None | MISSING |
| 2 | `/auth/login` | POST | loginUser | No | No | None | MISSING |
| 3 | `/auth/refresh` | POST | refreshToken | Yes | No | None | MISSING |
| 4 | `/users/me` | GET | getCurrentUser | Yes | No | None | MISSING |
| 5 | `/users/me` | PUT | updateCurrentUser | Yes | No | None | MISSING |
| 6 | `/users/me/cv` | POST | uploadCV | Yes | No | cv_upload_handler.py (`/api/cv`) | PATH + SCHEMA MISMATCH |
| 7 | `/users/me/cvs` | GET | listUserCVs | Yes | No | None | MISSING |
| 8 | `/jobs` | POST | createJob | Yes | No | None | MISSING |
| 9 | `/jobs` | GET | listJobs | Yes | No | None | MISSING |
| 10 | `/jobs/{jobId}` | GET | getJob | Yes | No | None | MISSING |
| 11 | `/vpr/generate` | POST | generateVPR | Yes | Yes | vpr_submit_handler.py (`/api/vpr`) | PATH + SCHEMA MISMATCH |
| 12 | `/vpr/{vprId}` | GET | getVPR | Yes | No | vpr_status_handler.py (`/api/vpr/status/{job_id}`) | PATH MISMATCH |
| 13 | `/users/me/vprs` | GET | listUserVPRs | Yes | No | None | MISSING |
| 14 | `/gap-analysis/questions` | POST | generateGapQuestions | Yes | No | gap_handler.py (helpers only) | STUB ONLY |
| 15 | `/gap-analysis/responses` | POST | submitGapResponses | Yes | No | gap_handler.py (helpers only) | STUB ONLY |
| 16 | `/gap-analysis/{jobId}/questions` | GET | getGapQuestions | Yes | No | None | MISSING |
| 17 | `/cv-tailoring/generate` | POST | generateTailoredCV | Yes | Yes | cv_tailoring_handler.py | SCHEMA MISMATCH |
| 18 | `/cv-tailoring/{cvTailoringId}` | GET | getTailoredCV | Yes | No | None | MISSING |
| 19 | `/users/me/tailored-cvs` | GET | listTailoredCVs | Yes | No | None | MISSING |
| 20 | `/cover-letter/generate` | POST | generateCoverLetter | Yes | Yes | None (Phase 6 creates) | MISSING |
| 21 | `/cover-letter/{coverLetterId}` | GET | getCoverLetter | Yes | No | None | MISSING |
| 22 | `/users/me/cover-letters` | GET | listCoverLetters | Yes | No | None | MISSING |
| 23 | `/interview-prep/generate` | POST | generateInterviewPrep | Yes | Yes | None (Phase 9 creates) | MISSING |
| 24 | `/interview-prep/{interviewPrepId}` | GET | getInterviewPrep | Yes | No | None | MISSING |
| 25 | `/company-research/fetch` | POST | fetchCompanyResearch | Yes | Yes | company_research_handler.py | RESPONSE CODE MISMATCH |
| 26 | `/company-research/{jobId}` | GET | getCompanyResearch | Yes | No | None | MISSING |
| 27 | `/health` | GET | healthCheck | No | No | None | MISSING |

### Step 10.0: Path Normalization Strategy — NEW 2026-02-15

### Step 10.0a: API Gateway Additive Route Migration — NEW 2026-02-15

**Goal:** Add OpenAPI-compliant routes first, keep existing `/api/*` routes temporarily to avoid breaking existing clients.

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
ENHANCE infra/careervp/api_construct.py for additive migration:

1. Add OpenAPI paths as API Gateway resources/methods:
   /auth/*, /users/me*, /jobs*, /vpr*, /gap-analysis*, /cv-tailoring*,
   /cover-letter*, /interview-prep*, /company-research/*, /health

2. Keep existing /api/* resources during migration window
3. Reuse existing role/table/bucket/queue resources where possible
4. Do not rename or replace existing DynamoDB/S3/SQS resources
"""
```

### Step 10.0b: Infra Diff + Safety Gate — NEW 2026-02-15
```bash
cd /Users/yitzchak/Documents/dev/careervp/infra

cdk synth
cdk diff

# Expected:
# - Additive API Gateway resource changes
# - No destructive replacements of existing DynamoDB/S3/SQS resources
```

### Step 10.0c: Legacy Route Decommission Gate — NEW 2026-02-15

Remove legacy `/api/*` API Gateway routes only after:
1. Phase 10 DONE gate passes
2. Staging smoke tests pass for all 27 OpenAPI endpoints
3. Migration sign-off is complete

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (servers section: base URL `/v1`)
- Existing handler route patterns in `src/backend/careervp/handlers/`

**ISSUE:** Existing handlers use `/api/*` routes (e.g., `/api/cv`, `/api/vpr`) but the OpenAPI contract defines paths under `/v1` base URL with feature-specific prefixes (e.g., `/users/me/cv`, `/vpr/generate`).

**RESOLUTION:**
API Gateway resource paths must match OpenAPI paths. Lambda handlers are invoked by API Gateway based on the resource path configured in the gateway, not the handler's internal route. The normalization requires:

1. **API Gateway routes** must be configured to match OpenAPI paths exactly
2. **Handler route decorators** (where present, e.g., `@app.post('/api/cv')`) must be updated to match
3. **No `/v1` prefix in handler routes** — the `/v1` prefix is the API Gateway stage name

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Normalize all handler route decorators to match OpenAPI contract paths:

1. ENHANCE: src/backend/careervp/handlers/cv_upload_handler.py
   - Change: @app.post('/api/cv') → @app.post('/users/me/cv')

2. VERIFY: All other handlers use lambda_handler(event, context) pattern
   (no route decorators to change — routing is via API Gateway config)

3. Document: API Gateway resource-to-handler mapping table for deployment

NOTE: Do NOT add /v1 prefix — that is the API Gateway stage name.
"""
```

**VALIDATION:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Verify no /api/ routes remain
grep -r "@app\.\(get\|post\|put\|delete\).*'/api/" careervp/handlers/ | wc -l
# Expected: 0

# Verify new route
grep "@app.post" careervp/handlers/cv_upload_handler.py
# Expected: @app.post('/users/me/cv')
```

### Step 10.1: Auth Endpoints (register, login, refresh) — NEW 2026-02-15

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (Auth section: RegisterRequest, LoginRequest, AuthResponse schemas)
- `docs/refactor/specs/security_spec.yaml`
- `src/backend/careervp/handlers/auth_handler.py` (existing Lambda Authorizer — DO NOT modify)

**NOTE:** The existing `auth_handler.py` is a **Lambda Authorizer** (validates tokens). The endpoints below are **user-facing auth endpoints** (register, login, refresh) — these are separate Lambda functions.

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement user-facing Auth endpoints per careervp-api-v1.yaml:

1. Create: src/backend/careervp/handlers/auth_endpoints_handler.py
   - POST /auth/register → register_user()
     * Input: RegisterRequest (email, password, name)
     * Output: 201 AuthResponse (access_token, refresh_token, expires_in, token_type)
     * Validation: email format, password min 8 chars
   - POST /auth/login → login_user()
     * Input: LoginRequest (email, password)
     * Output: 200 AuthResponse
     * Error: 401 Invalid credentials
   - POST /auth/refresh → refresh_token()
     * Input: Bearer token in Authorization header
     * Output: 200 AuthResponse (new tokens)
     * Error: 401 Invalid refresh token
     * Security: BearerAuth required

2. Create: tests/unit/test_auth_endpoints_handler.py
   - test_register_success (201)
   - test_register_duplicate_email (400)
   - test_register_invalid_email (400)
   - test_register_weak_password (400)
   - test_login_success (200)
   - test_login_invalid_credentials (401)
   - test_refresh_success (200)
   - test_refresh_invalid_token (401)

DO NOT MODIFY existing auth_handler.py (Lambda Authorizer).

KNOWLEDGE: docs/swagger/careervp-api-v1.yaml (RegisterRequest, LoginRequest, AuthResponse schemas)
KNOWLEDGE: docs/refactor/specs/security_spec.yaml
"""
```

**Verification:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/unit/test_auth_endpoints_handler.py -v --tb=short
uv run ruff check careervp/handlers/auth_endpoints_handler.py
uv run mypy careervp/handlers/auth_endpoints_handler.py --strict
```

**Live Test:**
```bash
cd /Users/yitzchak/Documents/dev/careervp

# Register
curl -X POST "https://api.careervp.com/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecureP@ss1","name":"Test User"}'
# Expected: 201 Created with access_token, refresh_token

# Login
curl -X POST "https://api.careervp.com/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecureP@ss1"}'
# Expected: 200 OK with access_token, refresh_token

# Refresh
curl -X POST "https://api.careervp.com/v1/auth/refresh" \
  -H "Authorization: Bearer $REFRESH_TOKEN"
# Expected: 200 OK with new access_token
```

### Step 10.2: User Management Endpoints — NEW 2026-02-15

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (Users section: UserProfile, UpdateUserRequest, CVUploadRequest, CVListResponse)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement User Management endpoints per careervp-api-v1.yaml:

1. Create: src/backend/careervp/handlers/user_handler.py
   - GET /users/me → get_current_user()
     * Security: BearerAuth required
     * Output: 200 UserProfile (id, email, name, created_at)
   - PUT /users/me → update_current_user()
     * Security: BearerAuth required
     * Input: UpdateUserRequest (name?, timezone?)
     * Output: 200 UserProfile
     * Error: 400 ValidationError
   - GET /users/me/cvs → list_user_cvs()
     * Security: BearerAuth required
     * Params: limit (int, default 20), cursor (string)
     * Output: 200 CVListResponse (cvs[], cursor)

2. ENHANCE: src/backend/careervp/handlers/cv_upload_handler.py
   - Fix route: @app.post('/api/cv') → @app.post('/users/me/cv')
   - Fix response: Return 201 (not 200) per OpenAPI
   - Fix response schema: Return CVUploadResponse (cv_id, status, parsed_data)
     instead of current CVParseResponse

3. Create: tests/unit/test_user_handler.py
   - test_get_current_user_success (200)
   - test_get_current_user_unauthorized (401)
   - test_update_user_success (200)
   - test_update_user_invalid (400)
   - test_list_cvs_success (200)
   - test_list_cvs_pagination (cursor-based)

KNOWLEDGE: docs/swagger/careervp-api-v1.yaml (UserProfile, UpdateUserRequest, CVUploadRequest, CVUploadResponse, CVListResponse schemas)
"""
```

**Verification:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/unit/test_user_handler.py -v --tb=short
uv run ruff check careervp/handlers/user_handler.py careervp/handlers/cv_upload_handler.py
uv run mypy careervp/handlers/user_handler.py careervp/handlers/cv_upload_handler.py --strict
```

**Live Test:**
```bash
cd /Users/yitzchak/Documents/dev/careervp

# Get current user
curl -X GET "https://api.careervp.com/v1/users/me" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with UserProfile

# Update user
curl -X PUT "https://api.careervp.com/v1/users/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Name","timezone":"America/New_York"}'
# Expected: 200 OK with updated UserProfile

# Upload CV
curl -X POST "https://api.careervp.com/v1/users/me/cv" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cv_content":"base64encodedcontent","file_name":"resume.pdf"}'
# Expected: 201 Created with cv_id, status

# List CVs
curl -X GET "https://api.careervp.com/v1/users/me/cvs?limit=10" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with cvs[], cursor
```

### Step 10.3: Job CRUD Endpoints — NEW 2026-02-15

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (Jobs section: JobCreateRequest, JobResponse, JobListResponse)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Implement Job CRUD endpoints per careervp-api-v1.yaml:

1. Create: src/backend/careervp/handlers/job_handler.py
   - POST /jobs → create_job()
     * Security: BearerAuth required
     * Input: JobCreateRequest (title, company_name, description, url?)
     * Output: 201 JobResponse (id, title, company_name, description, url, requirements[], created_at)
     * Error: 400 ValidationError
   - GET /jobs → list_jobs()
     * Security: BearerAuth required
     * Params: limit (int, default 20)
     * Output: 200 JobListResponse (jobs[])
   - GET /jobs/{jobId} → get_job()
     * Security: BearerAuth required
     * Params: jobId (path)
     * Output: 200 JobResponse
     * Error: 404 Job not found

2. Create: src/backend/careervp/logic/job_service.py
   - create_job(user_email, request) -> JobResponse
   - list_jobs(user_email, limit) -> JobListResponse
   - get_job(user_email, job_id) -> JobResponse | None

3. Create: tests/unit/test_job_handler.py
   - test_create_job_success (201)
   - test_create_job_missing_fields (400)
   - test_list_jobs_success (200)
   - test_list_jobs_empty (200, empty array)
   - test_get_job_success (200)
   - test_get_job_not_found (404)

KNOWLEDGE: docs/swagger/careervp-api-v1.yaml (JobCreateRequest, JobResponse, JobListResponse schemas)
"""
```

**Verification:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/unit/test_job_handler.py -v --tb=short
uv run ruff check careervp/handlers/job_handler.py careervp/logic/job_service.py
uv run mypy careervp/handlers/job_handler.py careervp/logic/job_service.py --strict
```

**Live Test:**
```bash
cd /Users/yitzchak/Documents/dev/careervp

# Create job
curl -X POST "https://api.careervp.com/v1/jobs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Senior Engineer","company_name":"Acme Corp","description":"Build things"}'
# Expected: 201 Created with JobResponse

# List jobs
curl -X GET "https://api.careervp.com/v1/jobs?limit=10" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with jobs[]

# Get specific job
JOB_ID="<from_create>"
curl -X GET "https://api.careervp.com/v1/jobs/$JOB_ID" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with JobResponse
```

### Step 10.4: VPR Endpoint Alignment — NEW 2026-02-15

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (VPR section)
- `src/backend/careervp/handlers/vpr_submit_handler.py` (current: POST /api/vpr)
- `src/backend/careervp/handlers/vpr_status_handler.py` (current: GET /api/vpr/status/{job_id})

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Align VPR endpoints with OpenAPI contract:

1. ENHANCE: src/backend/careervp/handlers/vpr_submit_handler.py
   - Fix route: POST /api/vpr → POST /vpr/generate
   - Fix request schema: Accept VPRGenerateRequest (cv_id, job_id, gap_response_ids, options)
     instead of current VPRRequest (user_id, application_id)
   - Fix response schema: Return VPRGenerateResponse (request_id, status, estimated_time_seconds, webhook_url)
   - Verify: Returns 202 Accepted (already correct)

2. ENHANCE: src/backend/careervp/handlers/vpr_status_handler.py
   - Fix route: GET /api/vpr/status/{job_id} → GET /vpr/{vprId}
   - Fix response schema: Return VPRStatusResponse (id, status, result{uvp, differentiators, strategic_narrative, company_job_fit_score, meta_evaluation}, created_at, completed_at)
   - Status values: pending, processing, completed, failed

3. Create: GET /users/me/vprs endpoint
   - Add to user_handler.py OR create vpr_list_handler.py
   - Output: 200 VPRListResponse (vprs[])
   - Security: BearerAuth required

4. Update: tests/vpr-async/unit/ with schema-aligned tests

KNOWLEDGE: docs/swagger/careervp-api-v1.yaml (VPRGenerateRequest, VPRGenerateResponse, VPRStatusResponse, VPRListResponse schemas)
"""
```

**Verification:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/vpr-async/unit/ -v --tb=short
uv run ruff check careervp/handlers/vpr_submit_handler.py careervp/handlers/vpr_status_handler.py
uv run mypy careervp/handlers/vpr_submit_handler.py careervp/handlers/vpr_status_handler.py --strict
```

**Live Test:**
```bash
cd /Users/yitzchak/Documents/dev/careervp

# Generate VPR (async)
curl -X POST "https://api.careervp.com/v1/vpr/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cv_id":"cv-123","job_id":"job-456","gap_response_ids":["gr-1","gr-2"]}'
# Expected: 202 Accepted with request_id, status=processing

# Poll status
VPR_ID="<request_id>"
curl -X GET "https://api.careervp.com/v1/vpr/$VPR_ID" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with VPRStatusResponse

# List VPRs
curl -X GET "https://api.careervp.com/v1/users/me/vprs" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with vprs[]
```

### Step 10.5: Gap Analysis Handler Completion — NEW 2026-02-15

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (Gap Analysis section)
- `src/backend/careervp/handlers/gap_handler.py` (current: CORS helpers only, no routes)
- Phase 5 steps (gap logic already planned)

**NOTE:** Phase 5 creates logic layer (gap_questions.py, gap_responses.py, gap_processor.py) but Step 5.4 only says "Enhance gap_handler.py" without specifying the exact route-to-handler mappings for all 3 endpoints. This step completes that.

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Complete Gap Analysis handler with all 3 OpenAPI endpoints:

1. ENHANCE: src/backend/careervp/handlers/gap_handler.py
   - Currently: Only _cors_headers() and _error_response() helpers
   - Add lambda_handler(event, context) entry point
   - POST /gap-analysis/questions → handle_generate_questions()
     * Security: BearerAuth required
     * Input: GapQuestionRequest (cv_id, job_id, max_questions?, focus_areas?)
     * Output: 200 GapQuestionResponse (questions[], missing_qualifications[])
   - POST /gap-analysis/responses → handle_submit_responses()
     * Security: BearerAuth required
     * Input: GapResponseRequest (responses[{question_id, response, quantifiable_data?}])
     * Output: 200 GapResponseResponse (status, impact_statements[])
   - GET /gap-analysis/{jobId}/questions → handle_get_questions()
     * Security: BearerAuth required
     * Params: jobId (path)
     * Output: 200 GapQuestionHistoryResponse (questions[])

2. Route dispatching: Use Powertools REST resolver or event path matching

3. Update: tests/gap_analysis/unit/test_gap_handler.py
   - test_generate_questions_success (200)
   - test_generate_questions_missing_cv (400)
   - test_submit_responses_success (200)
   - test_submit_responses_empty (400)
   - test_get_questions_history (200)
   - test_get_questions_not_found (404)

KNOWLEDGE: docs/swagger/careervp-api-v1.yaml (GapQuestionRequest, GapQuestionResponse, GapResponseRequest, GapResponseResponse, GapQuestionHistoryResponse schemas)
"""
```

**Verification:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/gap_analysis/unit/ -v --tb=short
uv run ruff check careervp/handlers/gap_handler.py
uv run mypy careervp/handlers/gap_handler.py --strict
```

**Live Test:**
```bash
cd /Users/yitzchak/Documents/dev/careervp

# Generate gap questions
curl -X POST "https://api.careervp.com/v1/gap-analysis/questions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cv_id":"cv-123","job_id":"job-456","max_questions":5}'
# Expected: 200 OK with questions[]

# Submit responses
curl -X POST "https://api.careervp.com/v1/gap-analysis/responses" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"responses":[{"question_id":"q-1","response":"Led team of 8..."}]}'
# Expected: 200 OK with impact_statements[]

# Get question history
curl -X GET "https://api.careervp.com/v1/gap-analysis/job-456/questions" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with questions[]
```

### Step 10.6: CV Tailoring Status + List Endpoints — NEW 2026-02-15

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (CV Tailoring section)
- `src/backend/careervp/handlers/cv_tailoring_handler.py` (current: POST only)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Add CV Tailoring status polling and list endpoints:

1. ENHANCE: src/backend/careervp/handlers/cv_tailoring_handler.py
   - Fix request schema: Accept CVTailoringRequest (cv_id, job_id, vpr_id, options{preserve_length, highlight_keywords, target_ats})
     instead of current TailorCVRequest (cv_id, job_description, user_id, preferences)
   - Fix response: Return 202 Accepted with CVTailoringResponse (request_id, status, estimated_time_seconds)
     instead of current synchronous 200 response
   - Add async job creation pattern (create DynamoDB job record + SQS message)

2. Create: src/backend/careervp/handlers/cv_tailoring_status_handler.py
   - GET /cv-tailoring/{cvTailoringId} → get_tailored_cv_status()
     * Security: BearerAuth required
     * Output: 200 CVTailoringStatusResponse (id, status, result{tailored_cv, ats_score, keyword_matches, suggestions, fvs_validation})
     * Error: 404 Not found

3. Add list endpoint to user_handler.py or create cv_tailoring_list_handler.py:
   - GET /users/me/tailored-cvs → list_tailored_cvs()
     * Security: BearerAuth required
     * Output: 200 CVTailoringListResponse (tailored_cvs[])

4. Update: tests/cv-tailoring/unit/ with new endpoint tests

KNOWLEDGE: docs/swagger/careervp-api-v1.yaml (CVTailoringRequest, CVTailoringResponse, CVTailoringStatusResponse, CVTailoringListResponse schemas)
"""
```

**Verification:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/cv-tailoring/unit/ -v --tb=short
uv run ruff check careervp/handlers/cv_tailoring_handler.py careervp/handlers/cv_tailoring_status_handler.py
uv run mypy careervp/handlers/cv_tailoring_handler.py careervp/handlers/cv_tailoring_status_handler.py --strict
```

**Live Test:**
```bash
cd /Users/yitzchak/Documents/dev/careervp

# Generate tailored CV (async)
curl -X POST "https://api.careervp.com/v1/cv-tailoring/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cv_id":"cv-123","job_id":"job-456","vpr_id":"vpr-789"}'
# Expected: 202 Accepted with request_id

# Poll status
TAILORING_ID="<request_id>"
curl -X GET "https://api.careervp.com/v1/cv-tailoring/$TAILORING_ID" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with CVTailoringStatusResponse

# List tailored CVs
curl -X GET "https://api.careervp.com/v1/users/me/tailored-cvs" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with tailored_cvs[]
```

### Step 10.7: Cover Letter Status + List Endpoints — NEW 2026-02-15

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (Cover Letter section)
- Phase 6 creates cover_letter_handler.py (POST /cover-letter/generate)

**NOTE:** Phase 6 creates the generate handler. This step adds the status polling and list endpoints that Phase 6 does not cover, and ensures the generate endpoint returns 202 (async pattern).

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Add Cover Letter status polling and list endpoints:

1. ENHANCE: src/backend/careervp/handlers/cover_letter_handler.py (created in Phase 6)
   - Verify POST /cover-letter/generate returns 202 Accepted
   - Verify response schema: CoverLetterResponse (request_id, status, estimated_time_seconds)
   - Verify request schema: CoverLetterRequest (cv_id, job_id, vpr_id, gap_response_ids, company_research_id, options{tone, length, include_portfolio_link})

2. Create: src/backend/careervp/handlers/cover_letter_status_handler.py
   - GET /cover-letter/{coverLetterId} → get_cover_letter_status()
     * Security: BearerAuth required
     * Output: 200 CoverLetterStatusResponse (id, status, result{cover_letter, paragraphs{hook, proof_points, close}, fvs_validation})
     * Error: 404 Not found

3. Add list endpoint:
   - GET /users/me/cover-letters → list_cover_letters()
     * Security: BearerAuth required
     * Output: 200 CoverLetterListResponse (cover_letters[])

4. Update: tests/cover-letter/unit/ with new endpoint tests

KNOWLEDGE: docs/swagger/careervp-api-v1.yaml (CoverLetterRequest, CoverLetterResponse, CoverLetterStatusResponse, CoverLetterListResponse schemas)
"""
```

**Verification:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/cover-letter/unit/ -v --tb=short
uv run ruff check careervp/handlers/cover_letter_handler.py careervp/handlers/cover_letter_status_handler.py
uv run mypy careervp/handlers/cover_letter_handler.py careervp/handlers/cover_letter_status_handler.py --strict
```

**Live Test:**
```bash
cd /Users/yitzchak/Documents/dev/careervp

# Generate cover letter (async)
curl -X POST "https://api.careervp.com/v1/cover-letter/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cv_id":"cv-123","job_id":"job-456","vpr_id":"vpr-789","gap_response_ids":["gr-1"],"company_research_id":"cr-1"}'
# Expected: 202 Accepted with request_id

# Poll status
LETTER_ID="<request_id>"
curl -X GET "https://api.careervp.com/v1/cover-letter/$LETTER_ID" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with CoverLetterStatusResponse

# List cover letters
curl -X GET "https://api.careervp.com/v1/users/me/cover-letters" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with cover_letters[]
```

### Step 10.8: Interview Prep Status Endpoint — NEW 2026-02-15

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (Interview Prep section)
- Phase 9 creates interview_prep_handler.py (POST /interview-prep/generate)

**NOTE:** Phase 9 creates the generate handler. This step adds the status polling endpoint and ensures the generate endpoint returns 202 (async pattern).

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Add Interview Prep status polling endpoint:

1. ENHANCE: src/backend/careervp/handlers/interview_prep_handler.py (created in Phase 9)
   - Verify POST /interview-prep/generate returns 202 Accepted
   - Verify request schema: InterviewPrepRequest (vpr_id, gap_response_ids, focus_areas?, question_count?)
   - Verify response schema: InterviewPrepResponse (request_id, status)

2. Create: src/backend/careervp/handlers/interview_prep_status_handler.py
   - GET /interview-prep/{interviewPrepId} → get_interview_prep_status()
     * Security: BearerAuth required
     * Output: 200 InterviewPrepStatusResponse (id, status, result{questions[{id, text, suggested_answer{format, situation, task, action, result}}]})

3. Update tests

KNOWLEDGE: docs/swagger/careervp-api-v1.yaml (InterviewPrepRequest, InterviewPrepResponse, InterviewPrepStatusResponse schemas)
"""
```

**Verification:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/unit/test_interview_prep*.py -v --tb=short
uv run ruff check careervp/handlers/interview_prep_handler.py careervp/handlers/interview_prep_status_handler.py
uv run mypy careervp/handlers/interview_prep_handler.py careervp/handlers/interview_prep_status_handler.py --strict
```

**Live Test:**
```bash
cd /Users/yitzchak/Documents/dev/careervp

# Generate interview prep (async)
curl -X POST "https://api.careervp.com/v1/interview-prep/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"vpr_id":"vpr-789","gap_response_ids":["gr-1","gr-2"],"question_count":5}'
# Expected: 202 Accepted with request_id

# Poll status
PREP_ID="<request_id>"
curl -X GET "https://api.careervp.com/v1/interview-prep/$PREP_ID" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with InterviewPrepStatusResponse (STAR-formatted answers)
```

### Step 10.9: Company Research GET Endpoint — NEW 2026-02-15

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (Company Research section)
- `src/backend/careervp/handlers/company_research_handler.py` (current: POST only, returns 200 instead of 202)

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Add Company Research GET endpoint and fix POST response code:

1. ENHANCE: src/backend/careervp/handlers/company_research_handler.py
   - Fix POST /company-research/fetch response: Return 202 Accepted (not 200)
   - Fix response schema: Return CompanyResearchResponse (request_id, status)
   - Add async job pattern (SQS + DynamoDB job record)

2. Create: src/backend/careervp/handlers/company_research_status_handler.py
   - GET /company-research/{jobId} → get_company_research()
     * Security: BearerAuth required
     * Output: 200 CompanyResearchResultResponse (id, company_name, mission, values[], recent_news[], culture, products[], funding_status, size_range, industry)
     * Error: 404 Not found

3. Update: tests/unit/test_company_research_handler.py
   - test_fetch_returns_202
   - test_get_research_success (200)
   - test_get_research_not_found (404)

KNOWLEDGE: docs/swagger/careervp-api-v1.yaml (CompanyResearchRequest, CompanyResearchResponse, CompanyResearchResultResponse schemas)
"""
```

**Verification:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/unit/test_company_research*.py -v --tb=short
uv run ruff check careervp/handlers/company_research_handler.py careervp/handlers/company_research_status_handler.py
uv run mypy careervp/handlers/company_research_handler.py careervp/handlers/company_research_status_handler.py --strict
```

**Live Test:**
```bash
cd /Users/yitzchak/Documents/dev/careervp

# Fetch company research (async)
curl -X POST "https://api.careervp.com/v1/company-research/fetch" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job_id":"job-456","company_name":"Acme Corp"}'
# Expected: 202 Accepted with request_id, status

# Get company research
curl -X GET "https://api.careervp.com/v1/company-research/job-456" \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200 OK with CompanyResearchResultResponse
```

### Step 10.10: Health Check Endpoint — NEW 2026-02-15

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (Health section: HealthResponse)

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Implement Health Check endpoint per careervp-api-v1.yaml:

1. Create: src/backend/careervp/handlers/health_handler.py
   - GET /health → health_check()
     * Security: None (public endpoint)
     * Output: 200 HealthResponse (status, timestamp, version, services{dynamodb, lambda, bedrock})
     * status: healthy | degraded | unhealthy
     * services: Check DynamoDB connectivity, Lambda status, Bedrock availability

2. Create: tests/unit/test_health_handler.py
   - test_health_check_healthy (200)
   - test_health_check_degraded (200, one service down)
   - test_health_check_unhealthy (200, critical service down)

KNOWLEDGE: docs/swagger/careervp-api-v1.yaml (HealthResponse schema)
"""
```

**Verification:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/unit/test_health_handler.py -v --tb=short
uv run ruff check careervp/handlers/health_handler.py
uv run mypy careervp/handlers/health_handler.py --strict
```

**Live Test:**
```bash
cd /Users/yitzchak/Documents/dev/careervp

curl -X GET "https://api.careervp.com/v1/health"
# Expected: 200 OK
# {
#   "status": "healthy",
#   "timestamp": "2026-02-15T12:00:00Z",
#   "version": "1.0.0",
#   "services": {"dynamodb": "healthy", "lambda": "healthy", "bedrock": "healthy"}
# }
```

### Step 10.11: Request/Response Schema Conformance — NEW 2026-02-15

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml` (all schemas in components/schemas)
- Existing Pydantic models in `src/backend/careervp/models/`

**CODE:**
```bash
# VSCode + Anthropic Opus (complex schema alignment)
"""
Align all handler request/response Pydantic models with OpenAPI schemas:

SCHEMA MISMATCHES TO FIX:

1. CV Upload:
   - Current: CVParseRequest (user_id, file_content, text_content, file_type)
   - OpenAPI: CVUploadRequest (cv_content, file_name)
   - Action: Create OpenAPI-aligned model, adapter from old if needed

2. VPR Generate:
   - Current: VPRRequest (user_id, application_id)
   - OpenAPI: VPRGenerateRequest (cv_id, job_id, gap_response_ids, options{include_company_research, tone})
   - Action: Create OpenAPI-aligned request model

3. CV Tailoring:
   - Current: TailorCVRequest (cv_id, job_description, user_id, preferences)
   - OpenAPI: CVTailoringRequest (cv_id, job_id, vpr_id, options{preserve_length, highlight_keywords, target_ats})
   - Action: Create OpenAPI-aligned request model

4. Create missing response models:
   - VPRGenerateResponse, VPRStatusResponse, VPRListResponse
   - CVTailoringResponse, CVTailoringStatusResponse, CVTailoringListResponse
   - CoverLetterResponse, CoverLetterStatusResponse, CoverLetterListResponse
   - InterviewPrepResponse, InterviewPrepStatusResponse
   - CompanyResearchResponse, CompanyResearchResultResponse
   - HealthResponse

5. Create: src/backend/careervp/models/api_models.py
   - All OpenAPI-aligned request/response Pydantic models
   - ErrorResponse model (error{code, message, details[]})

6. Create: tests/unit/test_api_models.py
   - Validate all models serialize/deserialize correctly
   - Validate required fields enforcement
   - Validate enum constraints

KNOWLEDGE: docs/swagger/careervp-api-v1.yaml (all schemas in components/schemas)
"""
```

**Verification:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/unit/test_api_models.py -v --tb=short
uv run ruff check careervp/models/api_models.py
uv run mypy careervp/models/api_models.py --strict
```

### Step 10.12: OpenAPI Contract Validation Suite — NEW 2026-02-15

**READ FIRST:**
- `docs/swagger/careervp-api-v1.yaml`
- `docs/refactor/specs/api_contract_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Create comprehensive contract validation test suite:

1. Create: tests/integration/test_openapi_contract.py
   - test_all_openapi_paths_have_handler()
     * Parse careervp-api-v1.yaml
     * For each path+method, verify a handler function exists
     * Verify handler route matches OpenAPI path
   - test_all_openapi_schemas_have_models()
     * For each schema in components/schemas, verify Pydantic model exists
   - test_async_endpoints_return_202()
     * Verify all 5 async endpoints return 202, not 200
   - test_auth_requirements_enforced()
     * Verify all endpoints with security: BearerAuth enforce auth
   - test_error_response_format()
     * Verify error responses match ErrorResponse schema
   - test_pagination_endpoints()
     * Verify list endpoints accept limit/cursor params
   - test_status_polling_lifecycle()
     * For each async endpoint: submit → poll (pending/processing) → completed/failed

2. Create: tests/integration/test_api_contract_spec_sync.py
   - test_contract_spec_matches_openapi()
     * Parse both api_contract_spec.yaml and careervp-api-v1.yaml
     * Verify all endpoints in contract spec exist in OpenAPI
     * Verify all OpenAPI endpoints exist in contract spec
     * Verify operationIds match

3. Create: scripts/validate_api_coverage.py
   - Parse OpenAPI spec
   - Scan handler files for route definitions
   - Output coverage report: matched, missing, mismatched

KNOWLEDGE: docs/swagger/careervp-api-v1.yaml
KNOWLEDGE: docs/refactor/specs/api_contract_spec.yaml
"""
```

**Verification:**
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# YAML validity
python3 -c "import yaml; yaml.safe_load(open('../../docs/swagger/careervp-api-v1.yaml')); print('OPENAPI: VALID')"
python3 -c "import yaml; yaml.safe_load(open('../../docs/refactor/specs/api_contract_spec.yaml')); print('CONTRACT: VALID')"

# Contract tests
uv run pytest tests/integration/test_openapi_contract.py tests/integration/test_api_contract_spec_sync.py -v --tb=short

# Coverage script
python3 ../../scripts/validate_api_coverage.py
# Expected: 27/27 endpoints covered (100%)
```

### Phase 10 Verification — NEW 2026-02-15

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# All Phase 10 unit tests
uv run pytest tests/unit/test_auth_endpoints_handler.py \
  tests/unit/test_user_handler.py \
  tests/unit/test_job_handler.py \
  tests/unit/test_health_handler.py \
  tests/unit/test_api_models.py \
  -v --tb=short

# All Phase 10 integration tests
uv run pytest tests/integration/test_openapi_contract.py \
  tests/integration/test_api_contract_spec_sync.py \
  -v --tb=short

# Feature-specific tests updated for schema alignment
uv run pytest tests/vpr-async/unit/ \
  tests/cv-tailoring/unit/ \
  tests/gap_analysis/unit/ \
  tests/cover-letter/unit/ \
  -v --tb=short

# Lint all handlers
uv run ruff check careervp/handlers/

# Type check all handlers
uv run mypy careervp/handlers/ --strict

# Coverage validation
python3 ../../scripts/validate_api_coverage.py
```

### Phase 10 DONE Gate — NEW 2026-02-15

**DONE when ALL of:**

| # | Criterion | Validation Command | Expected |
|---|-----------|-------------------|----------|
| 1 | 100% OpenAPI path+method coverage | `python3 scripts/validate_api_coverage.py` | 27/27 endpoints covered |
| 2 | All request/response schemas aligned | `uv run pytest tests/unit/test_api_models.py -v` | All pass |
| 3 | All async endpoints return 202 | `uv run pytest tests/integration/test_openapi_contract.py -k async -v` | All pass |
| 4 | Auth enforced on protected endpoints | `uv run pytest tests/integration/test_openapi_contract.py -k auth -v` | All pass |
| 5 | Contract spec matches OpenAPI | `uv run pytest tests/integration/test_api_contract_spec_sync.py -v` | All pass |
| 6 | No /api/ route prefixes remain | `grep -r "/api/" careervp/handlers/ \| grep -v __pycache__` | 0 matches |
| 7 | All handler lint passes | `uv run ruff check careervp/handlers/` | 0 errors |
| 8 | All handler type checks pass | `uv run mypy careervp/handlers/ --strict` | 0 errors |
| 9 | All unit tests pass | `uv run pytest tests/ -v --tb=short` | 100% pass |
| 10 | Pagination on list endpoints | curl tests with limit/cursor params | Returns paginated results |

---

## All Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Run all unit tests (EXISTING + CREATED)
uv run pytest tests/unit/ -v --tb=short
# Files:
# - test_auth_handler.py (11 tests - EXISTS)
# - test_validators.py (43 tests - EXISTS)
# - test_circuit_breaker.py (20 tests - CREATED)
# - test_quality_validator.py (62 tests - CREATED, fixtures pending fix)
# - test_interview_prep_prompt.py (50 tests - CREATED)
# - test_cv_upload_handler.py (pending)
# - test_company_research_handler.py (pending)
# - test_interview_prep_handler.py (pending - source not implemented)
# - test_interview_prep_logic.py (pending - source not implemented)
# - test_knowledge_repository.py (pending - source not implemented)
# - test_knowledge_base_handler.py (pending - source not implemented)

# Run feature unit tests
uv run pytest tests/cv-tailoring/unit/ tests/gap_analysis/unit/ tests/vpr-async/unit/ tests/cover-letter/unit/ -v --tb=short

# Run all integration tests
uv run pytest tests/integration/ -v --tb=short

# Run alignment tests
uv run pytest tests/jsa_skill_alignment/ -v --tb=short

# Lint all code
uv run ruff check careervp/

# Type check all
uv run mypy careervp/ --strict

# --- Phase 10: API Contract Remediation (NEW 2026-02-15) ---

# Phase 10 unit tests
uv run pytest tests/unit/test_auth_endpoints_handler.py \
  tests/unit/test_user_handler.py \
  tests/unit/test_job_handler.py \
  tests/unit/test_health_handler.py \
  tests/unit/test_api_models.py \
  -v --tb=short

# Phase 10 integration tests (OpenAPI contract validation)
uv run pytest tests/integration/test_openapi_contract.py \
  tests/integration/test_api_contract_spec_sync.py \
  -v --tb=short

# API coverage validation
python3 ../../scripts/validate_api_coverage.py
# Expected: 27/27 endpoints covered (100%)

# Verify no legacy /api/ routes remain
grep -r "@app\.\(get\|post\|put\|delete\).*'/api/" careervp/handlers/ | grep -v __pycache__ | wc -l
# Expected: 0
```

---

**Document Version:** 4.1
**Created:** 2026-02-15

**Changes:**

- v4.1 - Sync Specs + API, Preserve Existing Code/Infra (NEW 2026-02-15):
  - Added "Execution Sequence (Post-Phase-1)" section with explicit phase/step order
  - Added Step 0.4 sub-step for deployment_spec handler-pattern sync (Phase 0 already complete)
  - Added Step 1.6.3 sub-step for spec sync gate (Phase 1 already complete)
  - Corrected Phase 1.6 endpoint count from 34 to 27
  - Added Step 10.0a / 10.0b / 10.0c for additive API Gateway migration and safe legacy route decommission
  - Clarified execution flow: perform infra-safe route migration before full Phase 10 endpoint remediation

- v4.0 - API Contract Remediation (NEW 2026-02-15):
  - Added Phase 10: API Contract Remediation with 13 steps (10.0 – 10.12)
  - Full endpoint coverage matrix: 27 OpenAPI endpoints mapped to handler status
  - Gap analysis: 19 missing endpoints, 5 path/schema mismatches, 1 stub-only handler
  - Step 10.0: Path normalization (/api/* → OpenAPI contract paths)
  - Step 10.1: Auth endpoints (register, login, refresh) — NEW handlers
  - Step 10.2: User management endpoints (GET/PUT /users/me, GET /users/me/cvs) — NEW handler
  - Step 10.3: Job CRUD endpoints (POST/GET /jobs, GET /jobs/{jobId}) — NEW handler + logic
  - Step 10.4: VPR route alignment + list endpoint — ENHANCE existing handlers
  - Step 10.5: Gap analysis handler completion — ENHANCE stub handler
  - Step 10.6: CV Tailoring status + list endpoints — NEW status handler
  - Step 10.7: Cover Letter status + list endpoints — NEW status handler
  - Step 10.8: Interview Prep status endpoint — NEW status handler
  - Step 10.9: Company Research GET endpoint + response code fix — NEW status handler
  - Step 10.10: Health check endpoint — NEW handler
  - Step 10.11: Request/response schema conformance — NEW api_models.py
  - Step 10.12: OpenAPI contract validation suite — NEW integration tests + coverage script
  - Added Phase 10 DONE Gate with 10 measurable completion criteria
  - Updated All Verification Commands section with Phase 10 tests

- v3.0 - Fixed INC-01 through INC-09 (Remaining Inconsistencies):
  - INC-01: Changed Phase 1.1-1.3 from "Create" to "Enhance/Consolidate" with existing files table
  - INC-02: Added handler pattern note (function-based Powertools) at document beginning
  - INC-04: Added MODEL MAPPING tables showing spec class names → existing class names
  - INC-05: Added cv_models.py → cv.py consolidation notes
  - INC-06: Changed Step 6.1 file from cover_letter_logic.py to cover_letter.py (per spec)
  - INC-07: Changed Step 7.1 file from fvs_validator_logic.py to fvs_validator.py (per spec)
  - INC-08: Clarified fvs_spec.yaml says handler_status: "N/A" (FVS is inline, no handler)
  - INC-09: Verified Step 5.1-5.4 already use "Enhance" not "Create"
  - INC-10: Added test directory structure note, updated verification sections:
    * Phase 2: tests/cost_optimization/unit/
    * Phase 3: tests/vpr-async/unit/
    * Phase 4: tests/cv-tailoring/unit/
    * Phase 5: tests/gap_analysis/unit/
    * Phase 6: tests/cover-letter/unit/
    * Phase 7: inline tests (cv-tailoring, cover-letter)
    * Phase 8: tests/knowledge_base/unit/
  - Step 4.1: Changed from "Create" to "ENHANCE ONLY" (files already exist)
  - Clarified file structure:
    * `cv_tailoring.py` - CORE FUNCTION (canonical, contains tailor_cv())
    * `cv_tailoring_logic.py` - ORCHESTRATION (contains CVTailoringLogic class)
  - Handler imports from cv_tailoring.tailor_cv
  - Added DO NOT CREATE NEW FILES directive

- v2.11 - Fixed INC-14: DynamoDB Table Name Standardization:
  - deployment_spec.yaml (v1.1): Added naming_convention section with NamingUtils pattern
  - Updated all table names to `careervp-{feature}-table-dev` format
  - Updated S3 bucket names to match infra naming
  - knowledge_base_spec.yaml (v1.1): Updated storage references to use full table names
  - Added `infra/careervp/specs/dynamodb_spec.yaml` reference for table schemas
  - _registry.yaml: Added naming_convention section for clarity

- v2.10 - Fixed VPR stage count inconsistency:
  - Updated vpr_6stage_spec.yaml from 5 stages to 6 stages (spec v2.0)
  - Changed Phase 3 title from "VPR 5-Stage Generator" back to "VPR 6-Stage Generator"
  - Added Stage 6: `_final_meta_evaluation()` to Step 3.1
  - Now matches CareerVP_Agentic_Architecture.md (6-stage VPR)

- v2.9 - Fixed remaining CRITICAL and LOW inconsistencies:
  - CRITICAL-01: ✅ Phase 1.1-1.3 "Create" → "Enhance/Consolidate"
  - CRITICAL-02: ✅ Added handler pattern note at Phase 0 beginning
  - CRITICAL-03: ✅ Added `cd /Users/yitzchak/Documents/dev/careervp/src/backend` to all 10 verification sections
  - INC-04: ✅ Added existing model notes to Phase 1 steps
  - INC-05, INC-06, INC-07, INC-08, INC-09: ✅ Fixed file naming and enhancement status
  - INC-19: ✅ Converted Step 4.3 from CLI-specific syntax to standard format
  - All 21 inconsistencies now addressed

- v2.8 - Fixed MEDIUM inconsistencies (INC-10 through INC-16):
  - INC-11: Changed Phase 3 title from "VPR 6-Stage Generator" to "VPR 5-Stage Generator" (matches spec at v1.x)
  - INC-12: Added consolidation note for cv_tailoring.py vs cv_tailoring_logic.py in Step 4.1
  - INC-13: Added guidance about existing validation/ package as alternative to handlers/validators.py in Step 0.2
  - INC-15: Added note to check for duplicate interview_prep_spec.yaml entries in _registry.yaml (Step 9.1)
  - INC-16: Changed Phase 2 title from "DAL Consolidation + Cost Optimization" to "Cost Optimization + LLM Caching"
  - INC-14 & INC-20: Added table naming verification note in Step 8.1

- v2.4 - Updated all specs with handler implementation patterns:
  - _registry.yaml: Added reference specs from docs/specs/ (vpr-async-architecture.md, company-research.md, vpr-generator.md)
  - _registry.yaml: Added handler_status_matrix (implemented/needs_enhancement/to_be_created/not_started)
  - _registry.yaml: Added infrastructure_status section (DynamoDB, S3, SQS, Lambda)
  - cover_letter_spec.yaml: Added full handler implementation pattern (TO_BE_CREATED)
  - interview_prep_spec.yaml: Added full handler implementation pattern (TO_BE_CREATED)
  - gap_analysis_spec.yaml: Added handler enhancement details (NEEDS_ENHANCEMENT)
  - cv_tailoring_spec.yaml: Handler status IMPLEMENTED
  - vpr_6stage_spec.yaml: Handler status NEEDS_REFACTOR

- v2.3 - Updated prompt_library_spec.yaml (v2.0) with ACTUAL prompt text from:
  - CareerVP_Agentic_Architecture.md
  - PROMPT_GAP_ANALYSIS_REPORT.md
  - CareerVP Prompt Library.md
- Added prompts: cv_parsing, perplexity_research, interview_tier1, interview_tier2
- Added verification sub-agents: verification_2a_fact_audit, verification_2b_strategy, verification_2c_tone
- Added: ats_compatibility checker
- Each prompt now includes: system_prompt, user_prompt, output_schema, anti_ai_detection, fvs_tier

**Previous Changes:**
- v2.2 - Added prompt_library_spec.yaml references to phases 3-9
