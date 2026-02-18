# EXECUTION RUNBOOK VALIDATION & IMPLEMENTATION PROMPT

**Version:** 1.0
**Generated:** 2026-02-16
**Purpose:** Complete Phase 0-10 implementation with validated tests and working workflows
**Model:** Claude Opus 4.6 (complex reasoning required)

---
**Purpose:** Complete Phase 0-10 implementation with validated tests and working workflows

## CONTEXT

This is a handoff from MiniMax validation. The following has been completed:

- ✅ Phase 0: Implementation verified, 59 unit tests created and passing
- ✅ Phase 1: Model consolidation verified (cv_models.py, fvs_models.py converted to shims)
- ✅ Infrastructure: Lambda layer enabled in api_construct.py
- ✅ Infrastructure: GitHub workflow caching enabled (enable-cache: true)

**What remains:**
- ❌ Phases 6, 8, 9: Missing handlers and logic
- ❌ Phases 3-7: Need quality assessment
- ❌ Execution Runbook: Needs detailed specifications from tasks/
- ❌ Tests: Need verification at each phase
- ❌ Workflows: Need to pass on deployment

---

## PART 1: VERIFICATION RESULTS (JSON)

```json
{
  "validation_version": "1.0",
  "completed_tasks": {
    "phase_0": {
      "status": "IMPLEMENTED_VERIFIED",
      "handlers": ["auth_handler.py", "validators.py"],
      "logic": ["circuit_breaker.py"],
      "tests": {
        "test_auth_handler.py": "CREATED - 18 tests passing",
        "test_validators.py": "CREATED - 23 tests passing",
        "test_circuit_breaker.py": "CREATED - 18 tests passing"
      },
      "total_tests": 59,
      "all_passing": true
    },
    "phase_1": {
      "status": "CONSOLIDATED",
      "models": {
        "cv.py": "EXISTS - 10 classes",
        "vpr.py": "EXISTS - 9 classes",
        "fvs.py": "EXISTS - 9 classes",
        "cv_models.py": "SHIM - imports from cv.py for backward compat",
        "fvs_models.py": "SHIM - imports from fvs.py for backward compat"
      },
      "tests": {
        "test_cv_models.py": "EXISTS",
        "test_vpr_models.py": "EXISTS",
        "test_fvs_models.py": "EXISTS"
      }
    },
    "infrastructure": {
      "lambda_layer": "FIXED - layers=[self.common_layer] uncommented",
      "github_workflows": "FIXED - enable-cache: true (4 places)"
    }
  },
  "missing_features": {
    "phase_6_cover_letter": {
      "handler": "MISSING",
      "logic": "MISSING"
    },
    "phase_8_knowledge_base": {
      "repository": "MISSING",
      "dynamodb_table": "VERIFY_NEEDED"
    },
    "phase_9_interview_prep": {
      "handler": "MISSING",
      "logic": "MISSING"
    }
  },
  "gaps_to_fill": {
    "execution_runbook": "Needs detailed specs from docs/tasks/",
    "test_alignment": "Need contract validation at each phase",
    "workflow_success": "Need to verify on merge/deploy"
  }
}
```

---

## PART 2: STEP-BY-STEP EXECUTION INSTRUCTIONS (YAML)

```yaml
execution_sequence:
  phase_0_completed:
    status: DONE
    verification: "uv run pytest tests/unit/test_auth_handler.py tests/unit/test_validators.py tests/unit/test_circuit_breaker.py -v"
    result: "59 tests passing"

  phase_1_completed:
    status: DONE
    verification: "ls src/backend/careervp/models/"
    result: "Models exist with shims for backward compatibility"

  # ============================================================================
  # PHASE 2: COST OPTIMIZATION
  # ============================================================================
  phase_2:
    task: "Verify/implement Cost Optimization (CV Summarizer, LLM Cache)"
    verification_command: |
      grep -r "cv_summarizer\|llm_cache\|CircuitBreaker" src/backend/careervp/logic/
    expected: "Implementation exists or create per cost_optimization_spec.yaml"
    test_command: "uv run pytest tests/unit/ -k 'cost or cache' -v"
    success_criteria: "Tests pass"

  # ============================================================================
  # PHASE 3: VPR 6-STAGE GENERATOR
  # ============================================================================
  phase_3:
    task: "Verify VPR 6-stage implementation quality"
    verification_commands:
      - command: "grep -n 'STAGE\|stage_\|meta\|persuasion' src/backend/careervp/logic/vpr_generator.py | head -30"
        expected: "All 6 stages present"
      - command: "cat docs/tasks/03-vpr-generator/task-04-sonnet-prompt.md | grep -A5 'STAGE'"
        expected: "Compare with actual implementation"
    requirements_from_tasks:
      - "STAGE 1: Company & Role Research"
      - "STAGE 2: Candidate Analysis with career narrative"
      - "STAGE 3: Alignment Mapping with explicit table"
      - "STAGE 4: Self-Correction with meta-review"
      - "STAGE 5: Generate Report"
      - "STAGE 6: Final Meta Evaluation (20% more persuasive)"
      - "Anti-AI detection: check_anti_ai_patterns()"
      - "Fact verification against source CV"
    test_command: "uv run pytest tests/unit/test_vpr_generator.py -v"
    success_criteria: "All VPR tests pass"
    runbook_update_needed: |
      Add to Phase 3 Validation:
      - Anti-AI: check_anti_ai_patterns() post-generation
      - Fact verification: Verify claims against source CV data

  # ============================================================================
  # PHASE 4: CV TAILORING 3-STEP
  # ============================================================================
  phase_4:
    task: "Verify CV Tailoring 3-step implementation quality"
    verification_commands:
      - command: "grep -n 'STEP\|step_\|ats\|keyword' src/backend/careervp/logic/cv_tailoring.py | head -30"
        expected: "All 3 steps present"
      - command: "ls src/backend/tests/cv-tailoring/unit/"
        expected: "Test files exist"
    requirements_from_tasks:
      - "{company_keywords}: 12-18 ATS-friendly keywords"
      - "{vpr_differentiators}: from VPR"
      - "STEP 1: Analysis & Keyword Mapping (12-18 keywords)"
      - "STEP 2: Self-Correction (ATS score 1-10)"
      - "STEP 3: Finalize (ATS >= 8.0)"
      - "CAR/STAR format for bullet points"
      - "ATS formatting rules"
    test_command: "uv run pytest tests/cv-tailoring/unit/ -v"
    success_criteria: "All CV Tailoring tests pass"
    runbook_update_needed: |
      Add to Phase 4 Validation:
      - Input Parameters: {company_keywords}, {vpr_differentiators}
      - CAR/STAR format requirement
      - ATS formatting rules

  # ============================================================================
  # PHASE 5: GAP ANALYSIS
  # ============================================================================
  phase_5:
    task: "Verify Gap Analysis implementation quality"
    verification_commands:
      - command: "grep -n 'cv impact\|interview\|tag\|priority' src/backend/careervp/handlers/gap_handler.py"
        expected: "Tagging system present"
      - command: "grep -n 'cv impact\|interview\|tag\|priority' src/backend/careervp/logic/gap_analysis.py"
        expected: "Tagging in logic"
    requirements_from_tasks:
      - "[CV IMPACT] tag for quantifiable evidence"
      - "[INTERVIEW/MVP ONLY] tag for qualitative answers"
      - "Priority levels: CRITICAL, IMPORTANT, OPTIONAL"
      - "Strategic intent per question"
      - "Max 10 questions"
      - "Memory awareness: recurring themes"
    test_command: "uv run pytest tests/gap_analysis/unit/ -v"
    success_criteria: "All Gap Analysis tests pass"
    runbook_update_needed: |
      Add to Phase 5 Validation:
      - Priority levels: CRITICAL, IMPORTANT, OPTIONAL
      - Memory awareness details

  # ============================================================================
  # PHASE 6: COVER LETTER (MISSING - FULL IMPLEMENTATION)
  # ============================================================================
  phase_6:
    task: "IMPLEMENT Cover Letter (MISSING)"
    implementation_required: true
    requirements_from_tasks:
      - "Handler: src/backend/careervp/handlers/cover_letter_handler.py"
      - "Logic: src/backend/careervp/logic/cover_letter.py"
      - "Reference class priming step"
      - "Paragraph 1 (Hook): 80-100 words, UVP + company reference"
      - "Paragraph 2 (Proof Points): 120-140 words, 3 requirements × claim + proof"
      - "Paragraph 3 (Close): 60-80 words, CTA + time-saver"
      - "Total: < 400 words"
      - "Anti-AI detection rules"
    create_tests:
      - "tests/unit/test_cover_letter_handler.py"
      - "tests/unit/test_cover_letter_generator.py"
    test_command: "uv run pytest tests/cover-letter/unit/ -v"
    success_criteria: "All Cover Letter tests pass"
    spec_reference: "docs/refactor/specs/cover_letter_spec.yaml"

  # ============================================================================
  # PHASE 7: QUALITY VALIDATOR (FVS)
  # ============================================================================
  phase_7:
    task: "Verify/enhance Quality Validator"
    verification_commands:
      - command: "grep -n 'grammar\|tone\|anti.*ai\|ats\|score' src/backend/careervp/logic/fvs_validator.py"
        expected: "All scoring present"
    requirements_from_tasks:
      - "1. Fact verification: cross-reference claims"
      - "2. ATS compatibility: keyword score >= 7.0"
      - "3. Anti-AI detection: score >= 9.0"
      - "4. Cross-document consistency"
      - "5. Completeness: word/section counts"
      - "6. Language quality: Grammar >= 9.0, Tone >= 8.0, Formatting >= 8.0"
    test_command: "uv run pytest tests/unit/test_fvs_validator.py -v"
    success_criteria: "All FVS tests pass"
    runbook_update_needed: |
      Add to Phase 7 Validation:
      - All 6 validation checks explicitly listed

  # ============================================================================
  # PHASE 8: KNOWLEDGE BASE (MISSING - FULL IMPLEMENTATION)
  # ============================================================================
  phase_8:
    task: "IMPLEMENT Knowledge Base (MISSING)"
    implementation_required: true
    requirements_from_tasks:
      - "Repository: src/backend/careervp/dal/knowledge_repository.py"
      - "DynamoDB table: careervp-knowledge-{env}"
      - "PK: USER#{user_email}, SK: entity patterns"
      - "Item types: COMPANY_RESEARCH, GAP_QUESTION, GAP_RESPONSE, THEME, DIFFERENTIATOR, APPLICATION"
      - "TTL: gap_responses(24mo), company_research(30d)"
      - "CRUD for gap_responses and company_research"
      - "Recurring themes handling"
    infrastructure_check: |
      cd infra/careervp
      grep -A10 "knowledge" specs/dynamodb_spec.yaml
    create_tests:
      - "tests/unit/test_knowledge_repository.py"
    test_command: "uv run pytest tests/knowledge_base/unit/ -v"
    success_criteria: "All Knowledge Base tests pass"
    spec_reference: "docs/refactor/specs/knowledge_base_spec.yaml"

  # ============================================================================
  # PHASE 9: INTERVIEW PREP (MISSING - FULL IMPLEMENTATION)
  # ============================================================================
  phase_9:
    task: "IMPLEMENT Interview Prep (MISSING)"
    implementation_required: true
    conflict_resolution: |
      CONFLICT: Runbook says 8-10 questions, 3 categories
      CONFLICT: tasks/ says 10-15 questions, 4 categories
      DECISION REQUIRED: Use tasks/ (10-15, 4 categories) for more comprehensive coverage
    requirements_from_tasks:
      - "Handler: src/backend/careervp/handlers/interview_prep_handler.py"
      - "Logic: src/backend/careervp/logic/interview_prep.py"
      - "Questions target: 10-15 (NOT 8-10)"
      - "4 categories: technical, behavioral, situational, company-specific"
      - "STAR format for responses"
      - "Questions to ask interviewer: 5-7"
      - "Salary negotiation guidance"
      - "Pre-interview checklist"
    create_tests:
      - "tests/unit/test_interview_prep_handler.py"
      - "tests/unit/test_interview_prep_generator.py"
    test_command: "uv run pytest tests/unit/test_interview_prep*.py -v"
    success_criteria: "All Interview Prep tests pass"
    spec_reference: "docs/refactor/specs/interview_prep_spec.yaml"
    runbook_update_needed: |
      Update Phase 9 Validation:
      - Questions: 10-15 (not 8-10)
      - Categories: 4 (technical, behavioral, situational, company-specific)
      - Add: STAR format, questions to ask, salary guidance, checklist

  # ============================================================================
  # PHASE 10: API CONTRACT REMEDIATION
  # ============================================================================
  phase_10:
    task: "Verify all 27 OpenAPI endpoints have handlers"
    verification_command: |
      # Extract all paths from OpenAPI
      grep -E "^  /" docs/swagger/careervp-api-v1.yaml | head -30

      # List existing handlers
      ls src/backend/careervp/handlers/
    expected: "Every OpenAPI path has corresponding handler"
    contract_test_command: "python scripts/validate_alignment.py"
    success_criteria: "All endpoints mapped to handlers"
```

---

## PART 3: INFRASTRUCTURE VALIDATION

```yaml
infrastructure_checks:
  lambda_layer:
    command: "grep 'layers=' infra/careervp/api_construct.py"
    expected: "layers=[self.common_layer],"
    status: FIXED

  github_workflows:
    command: "grep 'enable-cache:' .github/workflows/pr-validation.yml"
    expected: "enable-cache: true"
    status: FIXED

  cdk_synth:
    command: "cd infra && npx cdk synth"
    expected: "No errors"
    required_before_deploy: true

  naming_validation:
    command: "cd src/backend && uv run python scripts/validate_naming.py --path ../infra --strict"
    expected: "No naming violations"
    required_before_deploy: true
```

---

## PART 4: TEST TIER SYSTEM

Add to each phase in Execution Runbook:

```yaml
test_tiers:
  tier_1_unit:
    symbol: "✅"
    description: "Unit test (always runnable)"
    command: "uv run pytest tests/unit/ -v"
    required: true

  tier_2_integration:
    symbol: "🔄"
    description: "Integration test (localstack/moto)"
    command: "uv run pytest tests/integration/ -v --mock-aws"
    required: false

  tier_3_contract:
    symbol: "📋"
    description: "Contract test (API-Application alignment)"
    command: "python scripts/validate_alignment.py"
    required: true

  tier_4_e2e:
    symbol: "🌐"
    description: "E2E test (requires deployment)"
    command: "curl https://api.careervp.com/v1/..."
    required: false
    conditional: "if DEPLOYED=true"
```

---

## PART 5: EXECUTION RULES (FROM CLAUDE.MD & AGENTS.MD)

```yaml
execution_rules:
  delegation:
    - "Delegate substantive work to specialized agents"
    - "Use Task tool with appropriate subagent_type"
    - "Model selection: haiku (simple), sonnet (standard), opus (complex)"

  verification:
    - "NEVER claim completion without fresh verification"
    - "Run tests BEFORE claiming success"
    - "Use exact command from runbook for verification"

  code_quality:
    - "Run ruff check before commits"
    - "Run mypy --strict before commits"
    - "No type: ignore comments unless absolutely necessary"
    - "Follow existing patterns in codebase"

  documentation:
    - "Update runbook with any deviations"
    - "Document decisions in notepad if significant"
    - "Keep SPECS aligned with IMPLEMENTATION"
```

---

## PART 6: OUTPUT FORMAT

After completing each phase, output:

```yaml
phase_X_completion:
  phase: X
  status: COMPLETE | PARTIAL | BLOCKED
  implemented: [list of files created/modified]
  tests_created: [list of test files]
  tests_passed: [number]
  verification_command: "command run"
  verification_output: "summary of output"
  issues: [list of issues if any]
  blockers: [list of blockers if any]
  runbook_updates: [what was added to runbook]
  next_phase_ready: true | false
```

---

## PART 7: FINAL VALIDATION CHECKLIST

Before declaring completion:

```yaml
final_validation:
  - task: "All unit tests pass"
    command: "cd src/backend && uv run pytest tests/unit/ -v"
    expected: "100% passing"

  - task: "Lint passes"
    command: "cd src/backend && uv run ruff check careervp/"
    expected: "No errors"

  - task: "Type check passes"
    command: "cd src/backend && uv run mypy careervp --strict"
    expected: "No errors"

  - task: "CDK synth succeeds"
    command: "cd infra && npx cdk synth"
    expected: "No errors, CloudFormation template generated"

  - task: "Naming validation passes"
    command: "cd src/backend && uv run python scripts/validate_naming.py --path ../infra --strict"
    expected: "No violations"

  - task: "GitHub workflow file valid"
    command: "cat .github/workflows/pr-validation.yml | head -20"
    expected: "Valid YAML, enable-cache: true"

  - task: "Execution runbook updated"
    command: "grep -c 'phase' docs/refactor/EXECUTION_RUNBOOK.md"
    expected: "All phases documented with test tiers"
```

---

## START EXECUTION

Begin with Phase 2 and proceed through Phase 10 in order. After each phase:
1. Run verification commands
2. Run tests
3. Fix any issues
4. Update execution runbook with details
5. Output completion status in YAML format

**Current state:** Phase 0 and 1 complete. Start at Phase 2.
