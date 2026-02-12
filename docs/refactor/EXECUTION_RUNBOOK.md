# CareerVP Refactoring Execution Runbook

**Document Version:** 2.4
**Date:** 2026-02-12
**Purpose:** Machine-readable execution guide for all refactoring phases

> **Status:** Phase -1 COMPLETE. All specs in `docs/refactor/specs/`
> **Infra Specs:** `infra/careervp/specs/`
> **Prompt Library:** `docs/refactor/specs/prompt_library_spec.yaml` (v2.0 - NOW WITH ACTUAL PROMPT TEXT)
> **Handler Status Matrix:** See `docs/refactor/specs/_registry.yaml` (handler_status_matrix section)

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

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Implement validators per security_spec.yaml:

1. Create: src/backend/careervp/handlers/validators.py
   - validate_request(body) -> bool
   - validate_cv_upload(file) -> bool

2. Create: tests/unit/test_validators.py

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
uv run pytest tests/unit/test_auth_handler.py tests/unit/test_validators.py tests/unit/test_circuit_breaker.py -v --tb=short
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

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `models_spec.yaml` | Model definitions |
| Reference | `architectural_findings_spec.yaml` | Layer rules |
| Reference | `test_strategy_spec.yaml` | Test patterns |

### Step 1.1: Implement CV Models

**READ FIRST:**
- `docs/refactor/specs/models_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Consolidate CV models per models_spec.yaml:

1. Create: src/backend/careervp/models/cv.py
   - CVData, CVSection, WorkExperience, Education, Skill

2. Create: tests/unit/test_cv_models.py

KNOWLEDGE: docs/refactor/specs/models_spec.yaml (categories.CV models)
"""
```

### Step 1.2: Implement VPR Models

**READ FIRST:**
- `docs/refactor/specs/models_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Sonnet
"""
Consolidate VPR models per models_spec.yaml:

1. Create: src/backend/careervp/models/vpr.py
   - VPRData, ValueProposition, Achievement, TargetRole

2. Create: tests/unit/test_vpr_models.py

KNOWLEDGE: docs/refactor/specs/models_spec.yaml (categories.VPR models)
"""
```

### Step 1.3: Implement FVS Models

**READ FIRST:**
- `docs/refactor/specs/models_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Consolidate FVS models per models_spec.yaml:

1. Create: src/backend/careervp/models/fvs.py
   - FVSResult, QualityScore, GrammarIssue, ToneIssue

2. Create: tests/unit/test_fvs_models.py

KNOWLEDGE: docs/refactor/specs/models_spec.yaml (categories.FVS models)
"""
```

### Verification
```bash
uv run pytest tests/unit/test_cv_models.py tests/unit/test_vpr_models.py tests/unit/test_fvs_models.py -v
uv run ruff check careervp/models/
uv run mypy careervp/models/ --strict
```

---

## Phase 2: DAL Consolidation + Cost Optimization

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
uv run pytest tests/unit/test_cv_summarizer.py tests/unit/test_llm_content_cache.py -v
uv run ruff check careervp/logic/
uv run mypy careervp/logic/ --strict
```

---

## Phase 3: VPR 6-Stage Generator

**Duration:** 1.5 days | **Effort:** 10 hours

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `vpr_6stage_spec.yaml` | VPR implementation |
| Reference | `test_strategy_spec.yaml` | Test patterns |
| Reference | `prompt_library_spec.yaml` | Prompt: vpr_generation (Sonnet 4.5, STRATEGIC) |

### Step 3.1: Implement VPR Generator

**READ FIRST:**
- `docs/refactor/specs/vpr_6stage_spec.yaml`
- `docs/refactor/specs/prompt_library_spec.yaml` (prompts.vpr_generation)

**CODE:**
```bash
# VSCode + Anthropic Opus (complex architecture)
"""
Implement VPR 6-Stage Generator per vpr_6stage_spec.yaml:

1. Create: src/backend/careervp/logic/vpr_generator.py
   - Stage 1: _analyze_input() -> AnalysisResult
   - Stage 2: _extract_evidence() -> EvidenceList
   - Stage 3: _synthesize() -> DraftProposition
   - Stage 4: _self_correct() -> CorrectedProposition
   - Stage 5: _generate_output() -> VPRData

2. Create: tests/unit/test_vpr_generator.py

KNOWLEDGE: docs/refactor/specs/vpr_6stage_spec.yaml (stages section)
PROMPTS: docs/refactor/specs/prompt_library_spec.yaml (prompts.vpr_generation)
  - Existing prompt: src/backend/careervp/logic/prompts/vpr_prompt.py (IMPLEMENTED)
  - Model: Claude Sonnet 4.5 (STRATEGIC mode), temp=0.7, max_tokens=8192
  - Output: JSON with executive_summary, evidence_matrix, differentiators, gap_strategies
  - Anti-AI: Apply banned_words list + check_anti_ai_patterns() post-generation
"""
```

### Verification
```bash
uv run pytest tests/unit/test_vpr_generator.py -v
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
Implement CV Tailoring Logic per cv_tailoring_spec.yaml:

1. Create: src/backend/careervp/logic/cv_tailoring_logic.py
   - Class: CVTailoringLogic
   - Step 1: _analyze() -> AnalysisResult
   - Step 2: _self_correct() -> CorrectedCV
   - Step 3: _generate() -> TailoredCV

2. Create: tests/unit/test_cv_tailoring_logic.py

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

### Step 4.2: Implement CV Tailoring Handler

**READ FIRST:**
- `docs/refactor/specs/cv_tailoring_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Implement CV Tailoring Handler per cv_tailoring_spec.yaml:

1. Create: src/backend/careervp/handlers/cv_tailoring_handler.py
   - Lambda handler with Powertools
   - Input validation
   - Calls CVTailoringLogic

2. Create: tests/unit/test_cv_tailoring_handler.py

KNOWLEDGE: docs/refactor/specs/cv_tailoring_spec.yaml (implementation)
"""
```

### Step 4.3: Create Gate Tests

**READ FIRST:**
- `docs/refactor/specs/cv_tailoring_spec.yaml` (gate_tests)
- `docs/refactor/specs/test_strategy_spec.yaml` (cv_tailoring_gates)

**CODE:**
```bash
# Claude Code CLI
/swarm 2:executor "Create tests/unit/test_cv_tailoring_gates.py:
KNOWLEDGE: docs/refactor/specs/cv_tailoring_spec.yaml (gate_tests section)

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
"
```

### Verification
```bash
uv run pytest tests/unit/test_cv_tailoring_*.py -v --tb=short
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

1. Create: src/backend/careervp/handlers/gap_handler.py
   - Lambda handler with Powertools
   - Handles: question generation, response submission, processing

2. Create: tests/unit/test_gap_handler.py

KNOWLEDGE: docs/refactor/specs/gap_analysis_spec.yaml (implementation)
"""
```

### Verification
```bash
uv run pytest tests/unit/test_gap_*.py -v --tb=short
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

1. Create: src/backend/careervp/logic/cover_letter_generator.py
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
uv run pytest tests/unit/test_cover_letter_*.py -v --tb=short
uv run ruff check careervp/logic/cover_letter_generator.py careervp/handlers/cover_letter_handler.py
uv run mypy careervp/logic/cover_letter_generator.py careervp/handlers/cover_letter_handler.py --strict
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

1. Create: src/backend/careervp/logic/quality_validator.py
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

### Step 7.2: Implement FVS Handler

**READ FIRST:**
- `docs/refactor/specs/fvs_spec.yaml`

**CODE:**
```bash
# VSCode + Anthropic Haiku
"""
Implement Quality Validator Handler per fvs_spec.yaml:

1. Create: src/backend/careervp/handlers/quality_validator_handler.py
   - Lambda handler with Powertools

2. Create: tests/unit/test_quality_validator_handler.py

KNOWLEDGE: docs/refactor/specs/fvs_spec.yaml (implementation)
"""
```

### Verification
```bash
uv run pytest tests/unit/test_quality_validator*.py -v --tb=short
uv run ruff check careervp/logic/quality_validator.py careervp/handlers/quality_validator_handler.py
uv run mypy careervp/logic/quality_validator.py careervp/handlers/quality_validator_handler.py --strict
```

---

## Phase 8: Knowledge Base

**Duration:** 1.5 days | **Effort:** 12 hours

### Specs
| Type | File | Purpose |
|------|------|---------|
| Mandatory | `knowledge_base_spec.yaml` | Repository |
| Reference | `deployment_spec.yaml` | DynamoDB/S3 |

### Step 8.1: Implement Knowledge Repository

**READ FIRST:**
- `docs/refactor/specs/knowledge_base_spec.yaml`

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
uv run pytest tests/unit/test_knowledge_*.py -v --tb=short
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
uv run pytest tests/unit/test_interview_prep*.py -v --tb=short
uv run ruff check careervp/logic/interview_prep.py careervp/handlers/interview_prep_handler.py
uv run mypy careervp/logic/interview_prep.py careervp/handlers/interview_prep_handler.py --strict
```

---

## All Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Run all unit tests
uv run pytest tests/unit/ -v --tb=short

# Run all integration tests
uv run pytest tests/integration/ -v --tb=short

# Lint all code
uv run ruff check careervp/

# Type check all
uv run mypy careervp/ --strict
```

---

**Document Version:** 2.4
**Created:** 2026-02-12
**Changes:**
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
