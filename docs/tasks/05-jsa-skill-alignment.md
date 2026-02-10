# JSA Skill Alignment Implementation Tasks

**Parent Plan:** `docs/architecture/jsa-skill-alignment/JSA-Skill-Alignment-Plan.md`
**Spec:** `docs/specs/05-jsa-skill-alignment.md`
**Created:** 2026-02-09
**Status:** Pending

---

## Phase 1: Critical Fixes (Week 1-2)

### Task: JSA-VPR-001 - VPR 6-Stage Methodology Implementation

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P0 (Critical)
**Estimated Effort:** 4 hours
**Source:** JSA-Skill-Alignment-Plan.md Section 3

#### Description

Implement the 6-stage VPR methodology with staged thinking and self-correction.

#### Requirements

1. [ ] Add STAGE 1: Company & Role Research with strategic priorities extraction
2. [ ] Add STAGE 2: Candidate Analysis with career narrative and differentiators
3. [ ] Add STAGE 3: Alignment Mapping with explicit table creation
4. [ ] Add STAGE 4: Self-Correction with meta-review questions
5. [ ] Add STAGE 5: Generate Report (existing structure)
6. [ ] Add STAGE 6: Final Meta Evaluation with "20% more persuasive" improvement
7. [ ] Preserve existing anti-AI detection rules
8. [ ] Preserve existing fact verification checklist

#### Files Modified

- `src/backend/careervp/logic/prompts/vpr_prompt.py`

#### Tests Created

- `tests/jsa_skill_alignment/test_vpr_alignment.py::TestVPRAlignment::test_vpr_has_6_stages`
- `tests/jsa_skill_alignment/test_vpr_alignment.py::TestVPRAlignment::test_vpr_has_self_correction`
- `tests/jsa_skill_alignment/test_vpr_alignment.py::TestVPRAlignment::test_vpr_has_meta_evaluation`

#### Validation Checklist

- [ ] All 6 stages present in prompt template
- [ ] Meta-review questions include: unsupported claims, logic consistency, persuasion check
- [ ] "20% more persuasive" prompt included
- [ ] Internal output markers between stages
- [ ] Anti-AI detection rules preserved
- [ ] Fact verification checklist preserved

---

### Task: JSA-CVT-001 - CV Tailoring 3-Step Verification Implementation

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P0 (Critical)
**Estimated Effort:** 6 hours
**Source:** JSA-Skill-Alignment-Plan.md Section 4

#### Description

Implement 3-step verification methodology for CV tailoring with company keywords and VPR differentiators.

#### Requirements

1. [ ] Add `{company_keywords}` parameter to prompt builder
2. [ ] Add `{vpr_differentiators}` parameter to prompt builder
3. [ ] Implement STEP 1: Analysis & Keyword Mapping with 12-18 keyword extraction
4. [ ] Implement STEP 2: Self-Correction & Verification with ATS score (1-10)
5. [ ] Implement STEP 3: Final Output with ATS score >= 8 requirement
6. [ ] Add CAR/STAR format requirement for bullet points
7. [ ] Add explicit ATS formatting rules
8. [ ] Update `cv_tailoring_logic.py` to pass new parameters

#### Files Modified

- `src/backend/careervp/logic/cv_tailoring_prompt.py`
- `src/backend/careervp/logic/cv_tailoring_logic.py`

#### Tests Created

- `tests/jsa_skill_alignment/test_cv_tailoring_alignment.py::TestCVTailoringAlignment::test_cv_has_3_steps`
- `tests/jsa_skill_alignment/test_cv_tailoring_alignment.py::TestCVTailoringAlignment::test_cv_has_company_keywords`
- `tests/jsa_skill_alignment/test_cv_tailoring_alignment.py::TestCVTailoringAlignment::test_cv_has_vpr_differentiators`
- `tests/jsa_skill_alignment/test_cv_tailoring_alignment.py::TestCVTailoringAlignment::test_cv_has_ats_verification`

#### Validation Checklist

- [ ] STEP 1, 2, 3 markers present
- [ ] Verification Check 1 (ATS) present
- [ ] Verification Check 2 (Hiring Manager) present
- [ ] ATS score >= 8 requirement present
- [ ] CAR/STAR format required
- [ ] `{company_keywords}` placeholder present
- [ ] `{vpr_differentiators}` placeholder present

---

### Task: JSA-CL-001 - Cover Letter Handler & Scaffolded Prompt Implementation

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P0 (Critical)
**Estimated Effort:** 8 hours
**Source:** JSA-Skill-Alignment-Plan.md Section 5

#### Description

Create Lambda handler for cover letter and implement scaffolded prompt with reference class priming.

#### Requirements

1. [ ] Create `cover_letter_handler.py` with POST /api/cover-letter endpoint
2. [ ] Add Powertools decorators (@logger.inject_lambda_context, @tracer.capture_lambda_handler)
3. [ ] Add reference class priming step
4. [ ] Implement Paragraph 1 (Hook) - 80-100 words, UVP + company reference
5. [ ] Implement Paragraph 2 (Proof Points) - 120-140 words, 3 requirements × claim + proof
6. [ ] Implement Paragraph 3 (Close) - 60-80 words, CTA + time-saver positioning
7. [ ] Add anti-AI detection rules
8. [ ] Add word count enforcement (< 400 words)
9. [ ] Wire up API Gateway route in CDK

#### Files Created

- `src/backend/careervp/handlers/cover_letter_handler.py`

#### Files Modified

- `src/backend/careervp/logic/prompts/cover_letter_prompt.py`
- `infra/careervp/api_construct.py`

#### Tests Created

- `tests/jsa_skill_alignment/test_cover_letter_alignment.py::TestCoverLetterAlignment::test_cover_letter_handler_exists`
- `tests/jsa_skill_alignment/test_cover_letter_alignment.py::TestCoverLetterAlignment::test_cover_letter_has_reference_priming`
- `tests/jsa_skill_alignment/test_cover_letter_alignment.py::TestCoverLetterAlignment::test_cover_letter_has_proof_points`
- `tests/jsa_skill_alignment/test_cover_letter_alignment.py::TestCoverLetterAlignment::test_cover_letter_has_word_limits`

#### Validation Checklist

- [ ] Handler file exists with correct decorators
- [ ] POST /api/cover-letter route added to API Gateway
- [ ] REFERENCE CLASS PRIMING step present
- [ ] All paragraph word count constraints present
- [ ] Proof points structure with 3 requirements present
- [ ] Anti-AI detection rules present
- [ ] Word count enforcement present

---

### Task: JSA-GA-001 - Gap Analysis Handler & Contextual Tagging Implementation

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P0 (Critical)
**Estimated Effort:** 6 hours
**Source:** JSA-Skill-Alignment-Plan.md Section 6

#### Description

Complete Lambda handler for gap analysis and implement contextual tagging system.

#### Requirements

1. [ ] Complete `gap_handler.py` with full lambda_handler function
2. [ ] Add Powertools decorators
3. [ ] Add memory awareness (load recurring themes from knowledge base)
4. [ ] Add memory awareness (load previous gap responses)
5. [ ] Implement contextual tagging: [CV IMPACT] and [INTERVIEW/MVP ONLY]
6. [ ] Implement priority levels: CRITICAL, IMPORTANT, OPTIONAL
7. [ ] Add strategic intent for each question
8. [ ] Update prompt to generate MAX 10 questions
9. [ ] Wire up API Gateway route in CDK

#### Files Modified

- `src/backend/careervp/handlers/gap_handler.py`
- `src/backend/careervp/logic/prompts/gap_analysis_prompt.py`
- `infra/careervp/api_construct.py`

#### Tests Created

- `tests/jsa_skill_alignment/test_gap_analysis_alignment.py::TestGapAnalysisAlignment::test_gap_handler_complete`
- `tests/jsa_skill_alignment/test_gap_analysis_alignment.py::TestGapAnalysisAlignment::test_gap_has_contextual_tagging`
- `tests/jsa_skill_alignment/test_gap_analysis_alignment.py::TestGapAnalysisAlignment::test_gap_has_memory_awareness`
- `tests/jsa_skill_alignment/test_gap_analysis_alignment.py::TestGapAnalysisAlignment::test_gap_max_10_questions`

#### Validation Checklist

- [ ] lambda_handler function exists in gap_handler.py
- [ ] [CV IMPACT] tag present
- [ ] [INTERVIEW/MVP ONLY] tag present
- [ ] Max 10 questions constraint present
- [ ] recurring_themes parameter present
- [ ] Strategic Intent field present
- [ ] Priority levels present

---

## Phase 2: Missing Features (Week 3-4)

### Task: JSA-IP-001 - Interview Prep Full Implementation

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P1 (High)
**Estimated Effort:** 16 hours
**Source:** JSA-Skill-Alignment-Plan.md Section 7.1

#### Description

Implement complete Interview Prep Generator with STAR-formatted responses.

#### Requirements

1. [ ] Create `interview_prep_prompt.py` with 4-category question generation
2. [ ] Implement STAR format for responses
3. [ ] Create `interview_prep_logic.py` for orchestration
4. [ ] Create `interview_prep_handler.py` with POST /api/interview-prep endpoint
5. [ ] Add questions to ask interviewer section (5-7 questions)
6. [ ] Add salary negotiation guidance
7. [ ] Add pre-interview checklist
8. [ ] Add to CDK infrastructure

#### Files Created

- `src/backend/careervp/logic/prompts/interview_prep_prompt.py`
- `src/backend/careervp/logic/interview_prep.py`
- `src/backend/careervp/handlers/interview_prep_handler.py`

#### Files Modified

- `infra/careervp/api_construct.py`

#### Tests Created

- `tests/jsa_skill_alignment/test_interview_prep_alignment.py::TestInterviewPrepAlignment::test_interview_prep_handler_exists`
- `tests/jsa_skill_alignment/test_interview_prep_alignment.py::TestInterviewPrepAlignment::test_interview_prep_has_star_format`
- `tests/jsa_skill_alignment/test_interview_prep_alignment.py::TestInterviewPrepAlignment::test_interview_prep_has_4_categories`

#### Validation Checklist

- [ ] Handler file exists
- [ ] Logic module exists
- [ ] STAR format required in prompt
- [ ] 4 categories present
- [ ] 10-15 questions target present
- [ ] Questions to ask section present
- [ ] Pre-interview checklist present
- [ ] POST /api/interview-prep route added

---

### Task: JSA-QV-001 - Quality Validator Agent Implementation

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P1 (Medium)
**Estimated Effort:** 8 hours
**Source:** JSA-Skill-Alignment-Plan.md Section 7.2

#### Description

Implement multi-check validation agent for artifact quality assurance.

#### Requirements

1. [ ] Create `quality_validator.py` with 6 checks
2. [ ] Implement fact verification (cross-reference claims)
3. [ ] Implement ATS compatibility check (keyword score)
4. [ ] Implement anti-AI detection check
5. [ ] Implement cross-document consistency check
6. [ ] Implement completeness check (word/section counts)
7. [ ] Implement language quality check
8. [ ] Integrate as final step in VPR generation flow

#### Files Created

- `src/backend/careervp/logic/quality_validator.py`

#### Tests Created

- `tests/jsa_skill_alignment/test_quality_validator_alignment.py::TestQualityValidatorAlignment::test_quality_validator_exists`
- `tests/jsa_skill_alignment/test_quality_validator_alignment.py::TestQualityValidatorAlignment::test_fact_verification_present`
- `tests/jsa_skill_alignment/test_quality_validator_alignment.py::TestQualityValidatorAlignment::test_ats_check_present`
- `tests/jsa_skill_alignment/test_quality_validator_alignment.py::TestQualityValidatorAlignment::test_anti_ai_check_present`

#### Validation Checklist

- [ ] quality_validator.py exists
- [ ] All 6 checks implemented
- [ ] Fact verification method present
- [ ] ATS compatibility check present
- [ ] Anti-AI detection present
- [ ] Cross-document consistency present

---

### Task: JSA-KB-001 - Knowledge Base Implementation

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P1 (Medium)
**Estimated Effort:** 8 hours
**Source:** JSA-Skill-Alignment-Plan.md Section 7.3

#### Description

Implement DynamoDB-backed knowledge base for user memory awareness.

#### Requirements

1. [ ] Create DynamoDB table `careervp-knowledge-base` in CDK
2. [ ] Define schema: userEmail (PK), knowledgeType (SK), data, applications_count
3. [ ] Create `knowledge_base_repository.py` for CRUD operations
4. [ ] Implement recurring_themes storage/retrieval
5. [ ] Implement gap_responses storage/retrieval
6. [ ] Implement differentiators storage/retrieval
7. [ ] Integrate with Gap Analysis for memory-aware questioning

#### Files Created

- `src/backend/careervp/dal/knowledge_base_repository.py`
- `src/backend/careervp/logic/knowledge_base.py`

#### Files Modified

- `infra/careervp/api_db_construct.py`

#### Tests Created

- `tests/jsa_skill_alignment/test_knowledge_base_alignment.py::TestKnowledgeBaseAlignment::test_knowledge_base_table_in_cdk`
- `tests/jsa_skill_alignment/test_knowledge_base_alignment.py::TestKnowledgeBaseAlignment::test_repository_exists`

#### Validation Checklist

- [ ] Knowledge base table defined in CDK
- [ ] Repository module exists
- [ ] recurring_themes type supported
- [ ] gap_responses type supported
- [ ] Differentators type supported
- [ ] Integration with Gap Analysis works

---

## Phase 3: Enhancements (Week 5+)

### Task: JSA-CKW-001 - Company Keyword Extraction

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P2 (Low)
**Estimated Effort:** 4 hours
**Source:** JSA-Skill-Alignment-Plan.md Section 7 (Company Research enhancement)

#### Description

Enhance company research module to extract keywords for CV tailoring.

#### Requirements

1. [ ] Add keyword extraction function to company_research.py
2. [ ] Extract 12-18 ATS-friendly keywords from company research
3. [ ] Return keywords in structured format for CV tailoring
4. [ ] Add unit tests

#### Files Modified

- `src/backend/careervp/logic/company_research.py`

#### Validation Checklist

- [ ] Keyword extraction function exists
- [ ] Returns 12-18 keywords
- [ ] Keywords are ATS-friendly
- [ ] Integration with CV Tailoring works

---

## Phase 4: Test-Driven Completion

### Task: JSA-COMP-001 - Fix VPR Test Failures

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P0 (Critical)
**Estimated Effort:** 4 hours
**Source:** Test run 2026-02-09

#### Description

Fix the 7 VPR test failures identified during initial test run.

#### Requirements

1. [ ] Add STAGE 1 marker with Company & Role Research content
2. [ ] Add "3-5 strategic priorities" to Stage 1
3. [ ] Add STAGE 2 marker with Candidate Analysis content
4. [ ] Add "3-5 core differentiators" to Stage 2
5. [ ] Add STAGE 3 marker with Alignment Mapping content
6. [ ] Add STAGE 4 marker with Self-Correction meta-review
7. [ ] Add "unsupported claims" question in Stage 4
8. [ ] Add STAGE 5 marker for Report Generation
9. [ ] Add STAGE 6 marker with Final Meta Evaluation
10. [ ] Add "20% more persuasive" improvement prompt
11. [ ] Add "OUTPUT (Internal)" markers between stages

#### Files Modified

- `src/backend/careervp/logic/prompts/vpr_prompt.py`

#### Test Verification

Run: `uv run pytest tests/jsa_skill_alignment/test_vpr_alignment.py -v`
Expected: 12/12 passing

---

### Task: JSA-COMP-002 - Run Full Test Suite

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P0 (Critical)
**Estimated Effort:** 1 hour
**Source:** Test run 2026-02-09

#### Description

Execute full JSA alignment test suite and document results.

#### Requirements

1. [ ] Run VPR tests: `uv run pytest tests/jsa_skill_alignment/test_vpr_alignment.py -v`
2. [ ] Run CV Tailoring tests: `uv run pytest tests/jsa_skill_alignment/test_cv_tailoring_alignment.py -v`
3. [ ] Run Cover Letter tests: `uv run pytest tests/jsa_skill_alignment/test_cover_letter_alignment.py -v`
4. [ ] Run Gap Analysis tests: `uv run pytest tests/jsa_skill_alignment/test_gap_analysis_alignment.py -v`
5. [ ] Run Interview Prep tests: `uv run pytest tests/jsa_skill_alignment/test_interview_prep_alignment.py -v`
6. [ ] Run Quality Validator tests: `uv run pytest tests/jsa_skill_alignment/test_quality_validator_alignment.py -v`
7. [ ] Run Knowledge Base tests: `uv run pytest tests/jsa_skill_alignment/test_knowledge_base_alignment.py -v`
8. [ ] Run mapping validation: `python tests/jsa_skill_alignment/test_mapping.py`
9. [ ] Document all failures in task backlog

#### Output

| Component | Tests | Passing | Failing |
|-----------|-------|---------|---------|
| VPR | 12 | | |
| CV Tailoring | 15 | | |
| Cover Letter | 18 | | |
| Gap Analysis | 18 | | |
| Interview Prep | 11 | | |
| Quality Validator | 10 | | |
| Knowledge Base | 11 | | |
| **TOTAL** | **95+** | | |

---

### Task: JSA-COMP-003 - Code Quality Validation

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P0 (Critical)
**Estimated Effort:** 30 minutes
**Source:** Project standards

#### Requirements

1. [ ] Run linting: `uv run ruff check src/backend/careervp/`
2. [ ] Fix any linting errors
3. [ ] Run formatter: `uv run ruff format src/backend/careervp/`
4. [ ] Run type checking: `uv run mypy src/backend/careervp --strict`
5. [ ] Fix any type errors

#### Acceptance Criteria

- [ ] ruff check: No errors
- [ ] ruff format: All files formatted
- [ ] mypy: No errors (--strict mode)

---

### Task: JSA-COMP-004 - Gap Remediation

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P0 (Critical)
**Estimated Effort:** TBD based on Task JSA-COMP-002

#### Description

Fix all remaining test failures identified in Task JSA-COMP-002.

#### Requirements

1. [ ] Review test failure output
2. [ ] Prioritize failures by component
3. [ ] Fix CV Tailoring failures (if any)
4. [ ] Fix Cover Letter failures (if any)
5. [ ] Fix Gap Analysis failures (if any)
6. [ ] Create Interview Prep files (if tests fail due to missing files)
7. [ ] Create Quality Validator file (if tests fail due to missing files)
8. [ ] Create Knowledge Base files (if tests fail due to missing files)
9. [ ] Re-run all tests to verify fixes

---

### Task: JSA-COMP-005 - Final Validation & Merge

**Status:** [ ] Pending | [ ] In Progress | [ ] Complete
**Priority:** P0 (Critical)
**Estimated Effort:** 1 hour

#### Requirements

1. [ ] Run full test suite: `uv run pytest tests/jsa_skill_alignment/ -v`
2. [ ] Verify mapping validation passes
3. [ ] Verify linting passes
4. [ ] Verify type checking passes
5. [ ] Update JSA-ALIGNMENT-CHECKLIST.md with completion status
6. [ ] Create PR with all changes
7. [ ] Request code review

#### Definition of Done

- [ ] All 95+ tests passing
- [ ] No linting errors
- [ ] Type checking passes
- [ ] Code reviewed and approved
- [ ] PR merged

---

## Test Execution

### Run All JSA Alignment Tests

```bash
# Run all JSA alignment tests
cd src/backend
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/ -v

# Run specific test category
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_vpr_alignment.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_cv_tailoring_alignment.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_cover_letter_alignment.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_gap_analysis_alignment.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_interview_prep_alignment.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_quality_validator_alignment.py -v
PYTHONPATH=$(pwd) uv run pytest ../../tests/jsa_skill_alignment/test_knowledge_base_alignment.py -v

# Validate test mapping
python ../../tests/jsa_skill_alignment/test_mapping.py

# Code quality checks
uv run ruff check src/backend/careervp/
uv run ruff format src/backend/careervp/
uv run mypy src/backend/careervp --strict
```

### Initial Test Results (2026-02-09)

| Component | Tests | Passing | Failing |
|-----------|-------|---------|---------|
| VPR | 12 | 5 | 7 |
| CV Tailoring | 15 | TBD | TBD |
| Cover Letter | 18 | TBD | TBD |
| Gap Analysis | 18 | TBD | TBD |
| Interview Prep | 11 | 0 | 11 |
| Quality Validator | 10 | 0 | 10 |
| Knowledge Base | 11 | 0 | 11 |

**VPR Failures Detail:**
- test_vpr_has_6_stages: Missing "STAGE 1: COMPANY & ROLE RESEARCH"
- test_vpr_stage1_company_role_research: Missing "3-5 strategic priorities"
- test_vpr_stage2_candidate_analysis: Missing "3-5 core differentiators"
- test_vpr_stage3_alignment_mapping: Missing "ALIGNMENT MAPPING"
- test_vpr_has_self_correction: Missing "unsupported claims" check
- test_vpr_has_meta_evaluation: Missing "20% more persuasive"
- test_vpr_internal_output_markers: Missing "OUTPUT (Internal)"

---

### Validation Before Merge

All tasks must be complete before merge:
- [ ] All Phase 1 tasks complete
- [ ] All Phase 2 tasks complete
- [ ] All Phase 4 tasks complete
- [ ] All 95+ tests passing
- [ ] No linting errors
- [ ] Type checking passes (mypy)
- [ ] Code reviewed and approved
- [ ] PR merged

---

**END OF TASKS**
