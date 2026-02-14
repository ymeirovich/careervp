# CareerVP Refactoring Execution Runbook

**Document Version:** 3.0
**Date:** 2026-02-12
**Purpose:** Machine-readable execution guide for all refactoring phases
**Status:** ALL INCONSISTENCIES FIXED ✅

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
```

### Step 1.2: Consolidate VPR Models

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Consolidate VPR models per models_spec.yaml:

1. ENHANCE: src/backend/careervp/models/vpr.py
   - Keep existing: EvidenceItem, VPR (with executive_summary, evidence_matrix, differentiators, gap_strategies)
   - Add new if missing: ValueProposition, Achievement, TargetRole

2. Create: tests/models/unit/test_vpr_models.py (NEW FOLDER)

MAPPING: spec "VPRData" → existing "VPR"
MAPPING: spec "ValueProposition" → NEW (add to vpr.py)
MAPPING: spec "Achievement" → NEW (add to vpr.py)
MAPPING: spec "TargetRole" → NEW (add to vpr.py)
"""

KNOWLEDGE: docs/refactor/specs/models_spec.yaml (categories.VPR models)
```
```

### Step 1.3: Consolidate FVS Models

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Consolidate FVS models per models_spec.yaml:

1. ENHANCE: src/backend/careervp/models/fvs.py
   - Keep existing: ViolationSeverity, FVSViolation, FVSValidationResult
   - Add new if missing: FVSResult, QualityScore, GrammarIssue, ToneIssue
   - DO NOT DELETE fvs_models.py - consolidate into fvs.py

2. Create: tests/models/unit/test_fvs_models.py (NEW FOLDER)

MAPPING: spec "FVSResult" → NEW (add to fvs.py)
MAPPING: spec "QualityScore" → NEW (add to fvs.py)
MAPPING: spec "GrammarIssue" → NEW (add to fvs.py)
MAPPING: spec "ToneIssue" → NEW (add to fvs.py)
MAPPING: spec "FVSValidationResult" → existing "FVSValidationResult"
"""

KNOWLEDGE: docs/refactor/specs/models_spec.yaml (categories.FVS models)
```
```

### Phase 1 Verification
```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

uv run pytest tests/models/unit/ -v  # NEW FOLDER
uv run ruff check careervp/models/
uv run mypy careervp/models/ --strict
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
```

---

**Document Version:** 3.0
**Created:** 2026-02-12

**Changes:**

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
