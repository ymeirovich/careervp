# CareerVP Comprehensive Refactoring Plan

**Document Version:** 1.2
**Date:** 2026-02-10
**Changes:** Added Phase 2 Cost Optimization (CV Summarizer, LLM Content Cache)
**Purpose:** Master refactoring roadmap to align CareerVP with JSA Skill architecture and fix critical architectural issues

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architectural Class Analysis](#2-architectural-class-analysis)
3. [Security Requirements](#3-security-requirements)
4. [Gap Analysis Integration](#4-gap-analysis-integration)
5. [TDD Enforcement](#5-tdd-enforcement)
6. [GitHub Actions Workflows](#6-github-actions-workflows)
7. [CLAUDE Rules Enforcement](#7-claude-rules-enforcement)
8. [Class Coding Guidelines](#8-class-coding-guidelines)
9. [Implementation Phases](#9-implementation-phases)
10. [Dependencies and Sequencing](#10-dependencies-and-sequencing)
11. [Effort Estimates](#11-effort-estimates)
12. [Risk Analysis](#12-risk-analysis)
13. [Validation Strategy](#13-validation-strategy)
14. [Appendix: File Change Matrix](#14-appendix-file-change-matrix)

---

## 1. Executive Summary

### Refactoring Goal
Align CareerVP codebase with the original Job Search Assistant (JSA) Skill architecture, fix critical architectural debt, and achieve feature parity with the target design.

### Key Metrics

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Architecture Score | 2.7/5.0 | 4.0/5.0 | -1.3 |
| JSA Alignment | 62.5% | 100% | -37.5% |
| Model Duplication | 4 models | 1 model | -3 |
| Missing Components | 5 | 0 | -5 |
| P0 Blocking Issues | 4 | 0 | -4 |

### Phased Approach

| Phase | Focus | Duration | Effort |
|-------|-------|----------|--------|
| Phase 0 | Security Foundation | Week 1 | 8 hours |
| Phase 1 | Model Unification | Week 1-2 | 22 hours |
| Phase 2 | DAL Consolidation + Cost Optimization | Week 2 | 20 hours |
| Phase 3 | VPR 6-Stage | Week 2-3 | 10 hours |
| Phase 4 | CV Tailoring 3-Step | Week 3 | 11 hours |
| Phase 5 | Gap Analysis | Week 3-4 | 13 hours |
| Phase 6 | Cover Letter | Week 4 | 13 hours |
| Phase 7 | Quality Validator | Week 5 | 12 hours |
| Phase 8 | Knowledge Base | Week 5 | 12 hours |
| Phase 9 | Interview Prep | Week 6 | 16 hours |
| **Total** | | **6 Weeks** | **137 hours** |

---

## 2. Architectural Class Analysis

### 2.1 VPR Design Pattern (TARGET)

All features MUST follow the VPR architecture pattern:

```
┌─────────────────────────────────────────────────────────────────┐
│                        HANDLER LAYER                            │
│              (API Gateway → Lambda → Input Validation)           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        LOGIC LAYER                               │
│         (Business Rules → Orchestration → Prompt Building)       │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  STAGED THINKING PATTERN (per JSA Skill):                  │  │
│  │  1. Input Analysis & Context Building                      │  │
│  │  2. Evidence Extraction & Validation                       │  │
│  │  3. Strategic Synthesis & Alignment                       │  │
│  │  4. Self-Correction & Meta-Review                         │  │
│  │  5. Output Generation                                      │  │
│  │  6. Final Verification                                    │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          DAL LAYER                               │
│              (DynamoDalHandler → Repository Pattern)            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Feature-by-Feature Architectural Requirements

| Feature | Handler | Logic | DAL | Pattern Adherence |
|---------|---------|-------|-----|------------------|
| **VPR** | `vpr_submit_handler.py` | `vpr_generator.py` | `dynamo_dal_handler.py` | ✅ 6-Stage (target) |
| **CV Tailoring** | `cv_tailoring_handler.py` | `cv_tailoring_logic.py` | `dynamo_dal_handler.py` | ❌ Must refactor |
| **Gap Analysis** | `gap_handler.py` | `gap_analysis.py` | `dynamo_dal_handler.py` | ⚠️ Incomplete |
| **Cover Letter** | ❌ Missing | ❌ Missing | ❌ Missing | ❌ Must create |
| **Interview Prep** | ❌ Missing | ❌ Missing | ❌ Missing | ❌ Must create |
| **Quality Validator** | ❌ Missing | ❌ Missing | ❌ Missing | ❌ Must create |

### 2.3 Class Hierarchy Standards

All features MUST follow these class patterns:

```python
# REQUIRED PATTERN FOR ALL NEW FEATURES

# 1. Handler (entry point)
class FeatureHandler:
    """API Gateway entry point with Powertools decorators."""
    def __init__(self, logic: FeatureLogic, dal: DynamoDalHandler):
        self.logic = logic
        self.dal = dal

    @logger.inject_lambda_context
    @tracer.capture_lambda_handler
    def lambda_handler(self, event: dict, context: Any) -> dict:
        """Handle API request with full validation."""
        pass

# 2. Logic (business rules)
class FeatureLogic:
    """Business orchestration following staged thinking."""
    def __init__(self, llm: LLMClient, repository: FeatureRepository):
        self.llm = llm
        self.repository = repository

    def execute(self, input: FeatureInput) -> Result[FeatureOutput]:
        """Execute staged thinking process."""
        pass

    # Required internal methods (staged thinking)
    def _analyze_input(self, input: FeatureInput) -> AnalysisContext:
        """Stage 1: Analyze and build context."""
        pass

    def _extract_evidence(self, context: AnalysisContext) -> Evidence:
        """Stage 2: Extract and validate evidence."""
        pass

    def _synthesize(self, context: Evidence) -> Synthesis:
        """Stage 3: Strategic synthesis."""
        pass

    def _self_correct(self, synthesis: Synthesis) -> VerifiedSynthesis:
        """Stage 4: Meta-review and correction."""
        pass

    def _generate_output(self, verified: VerifiedSynthesis) -> FeatureOutput:
        """Stage 5: Generate final output."""
        pass

# 3. Repository (data access)
class FeatureRepository:
    """DAL wrapper with caching and TTL."""
    def __init__(self, dal: DynamoDalHandler):
        self.dal = dal

    def save(self, item: FeatureOutput) -> Result[str]:
        pass

    def get(self, id: str) -> Result[FeatureOutput]:
        pass
```

### 2.4 SOLID Principles Compliance

| Principle | Requirement | Validation |
|-----------|-------------|------------|
| **Single Responsibility** | One class = One purpose | Review per feature |
| **Open/Closed** | Extend via inheritance, not modification | Use ABC/Protocol |
| **Liskov Substitution** | Subclasses can replace parent | Interface contracts |
| **Interface Segregation** | Small, focused interfaces | No God interfaces |
| **Dependency Inversion** | Depend on abstractions | Use DI container |

### 2.5 Architectural Review Checklist

Before completing each phase, verify:

- [ ] Handler → Logic → DAL separation maintained
- [ ] No direct DAL access from handlers
- [ ] No business logic in handlers
- [ ] All dependencies injected, not constructed
- [ ] Staged thinking pattern followed
- [ ] SOLID principles applied
- [ ] No God classes (>300 lines without decomposition)
- [ ] No circular dependencies

---

## 3. Security Requirements

### 3.1 Infrastructure Security

| Check | Current | Required | Priority |
|-------|---------|----------|----------|
| API Authorizer | ❌ Missing | JWT/Cognito | P0 |
| WAF Configuration | ⚠️ Partial | Full | P1 |
| Encryption at Rest | ⚠️ Default | Explicit SSE-KMS | P1 |
| Encryption in Transit | ✅ TLS | TLS 1.2+ | P0 |
| VPC Configuration | ❌ Missing | Private subnets | P2 |
| Secrets Management | ❌ Plain env | AWS Secrets Manager | P1 |

### 3.2 Application Security

| Check | Current | Required | Priority |
|-------|---------|----------|----------|
| Input Validation | ⚠️ Partial | Pydantic models | P0 |
| Output Sanitization | ❌ Missing | No PII in logs | P0 |
| Exception Handling | ❌ Raw exceptions | Generic errors | P0 |
| SQL/NoSQL Injection | ❌ Direct queries | Parameterized | P0 |
| Rate Limiting | ❌ Missing | Per-user | P1 |
| Audit Logging | ⚠️ Partial | Full request/response | P1 |

### 3.3 AI/LLM Security

| Check | Current | Required | Priority |
|-------|---------|----------|----------|
| Prompt Injection | ⚠️ Basic | Delimiters + validation | P0 |
| FVS Enabled | ❌ Partial | All prompts | P1 |
| Output Validation | ❌ Missing | Schema validation | P1 |
| Content Filtering | ❌ Missing | Output scan | P2 |

### 3.4 Security Implementation Tasks

```python
# Task: Add API Authorizer
# File: infra/careervp/api_construct.py

from aws_cdk import (
    Duration,
    Stack,
    aws_apigateway as apigw,
    aws_cognito as cognito,
)
from constructs import Construct

class APIConstruct(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Create Cognito User Pool
        user_pool = cognito.UserPool(
            self, "CareerVPUserPool",
            user_pool_name="careervp-user-pool",
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            mfa=cognito.Mfa.REQUIRED,
            mfa_second_factor=cognito.MfaSecondFactor(sms=True, otp=True),
        )

        # Create authorizer
        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, "CareerVPApiAuthorizer",
            cognito_user_pools=[user_pool],
            authorizer_result_ttl=Duration.minutes(5),
        )

# Task: Add input validation
# File: handlers/cv_tailoring_handler.py

from pydantic import BaseModel, validator
from typing import Literal
import re

class CVTailoringRequest(BaseModel):
    cv_id: str
    job_description: str
    language: Literal["en", "he", "fr"] = "en"

    @validator("cv_id")
    def validate_cv_id(cls, v):
        if not re.match(r"^[a-zA-Z0-9-]{8,64}$", v):
            raise ValueError("Invalid cv_id format")
        return v

    @validator("job_description")
    def validate_job_description(cls, v):
        if len(v) > 20000:
            raise ValueError("Job description too long")
        # Check for potential prompt injection
        dangerous_patterns = [
            r"ignore previous instructions",
            r"system prompt",
            r"you are now",
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError("Invalid job description content")
        return v
```

---

## 4. Gap Analysis Integration

### 4.1 Continuous Gap Analysis Flow

All artifacts MUST consume and produce gap responses:

```
┌─────────────────────────────────────────────────────────────────┐
│                    GAP ANALYSIS ECOSYSTEM                        │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │   VPR INPUT    │ │ CV TAILOR INPUT │ │COVER LETTER INPUT│
    │                │ │                 │ │                 │
    │ gap_responses  │ │ gap_responses   │ │ gap_responses   │
    │ + cv_facts     │ │ + vpr_output    │ │ + vpr_output    │
    │ + job_req      │ │ + company_kw    │ │ + requirements  │
    └─────────────────┘ └─────────────────┘ └─────────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
    ┌─────────────────────────────────────────────────────────┐
    │              GAP RESPONSE CONSUMPTION PATTERN            │
    │                                                         │
    │  1. LOAD: Fetch user's gap_responses from Knowledge Base│
    │  2. FILTER: Select responses relevant to current artifact│
    │  3. INJECT: Include in LLM prompt as EVIDENCE          │
    │  4. VERIFY: Ensure facts are IMMUTABLE (dates, titles)  │
    │  5. OUTPUT: Reference gap responses in artifact content   │
    └─────────────────────────────────────────────────────────┘
```

### 4.2 Gap Response Schema

```python
# models/gap_analysis.py

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

class GapQuestionType(str, Enum):
    CV_IMPACT = "CV_IMPACT"  # Quantifiable evidence for CV
    INTERVIEW_MVP = "INTERVIEW_MVP_ONLY"  # Qualitative for interview

class GapQuestionPriority(str, Enum):
    CRITICAL = "CRITICAL"
    IMPORTANT = "IMPORTANT"
    OPTIONAL = "OPTIONAL"

class GapQuestion(BaseModel):
    question_id: str
    requirement: str  # Exact quote from job posting
    question_text: str
    question_type: GapQuestionType
    strategic_intent: str  # Why this matters
    evidence_gap: str  # What's missing from CV
    priority: GapQuestionPriority
    recurring_theme_check: bool = False

class GapResponse(BaseModel):
    response_id: str
    question_id: str
    user_email: str
    application_id: str
    response_text: str
    evidence_type: GapQuestionType  # How response can be used
    created_at: datetime

    # For VPR consumption
    quantifiable_data: Optional[Dict[str, Any]] = None  # { "percentage": 40, "team_size": 8 }

    # For artifact tracking
    used_in_artifacts: List[str] = []  # ["vpr", "cv", "cover_letter"]
    last_verified: Optional[datetime] = None
```

### 4.3 VPR Gap Integration

```python
# logic/vpr_generator.py

class VPRGenerator:
    """VPR with continuous gap analysis integration."""

    def _load_gap_responses(self, application_id: str) -> List[GapResponse]:
        """Load and filter gap responses for this application."""
        kb_repo = KnowledgeBaseRepository(self.dal)
        responses = kb_repo.get_gap_responses(application_id)

        # Filter to CV_IMPACT responses only (for VPR)
        cv_impact_responses = [
            r for r in responses
            if r.evidence_type == GapQuestionType.CV_IMPACT
        ]

        return cv_impact_responses

    def _build_evidence_context(
        self,
        cv_facts: UserCV,
        gap_responses: List[GapResponse]
    ) -> Dict[str, Any]:
        """Build evidence context from CV facts + gap responses."""
        evidence = {
            "cv_achievements": self._extract_achievements(cv_facts),
            "gap_quantified": self._quantify_gap_responses(gap_responses),
            "combined_impact": self._combine_evidence(
                cv_facts.achievements,
                gap_responses
            ),
        }
        return evidence

    def _quantify_gap_responses(
        self,
        responses: List[GapResponse]
    ) -> List[Dict[str, Any]]:
        """Extract quantifiable data from gap responses."""
        quantified = []
        for response in responses:
            if response.quantifiable_data:
                quantified.append({
                    "metric": response.quantifiable_data,
                    "context": response.response_text[:200],
                    "source": f"gap:{response.question_id}",
                })
        return quantified
```

### 4.4 CV Tailoring Gap Integration

```python
# logic/cv_tailoring_logic.py

class CVTailoringLogic:
    """CV Tailoring with gap response injection."""

    def _inject_gap_evidence(
        self,
        draft_cv: TailoredCV,
        gap_responses: List[GapResponse],
        vpr_differentiators: List[Differentiator]
    ) -> TailoredCV:
        """Inject quantified gap evidence into CV bullets."""
        # Get CV_IMPACT responses
        cv_impact = [
            r for r in gap_responses
            if r.evidence_type == GapQuestionType.CV_IMPACT
        ]

        # Enhance work experience bullets
        for exp in draft_cv.work_experience:
            enhanced_bullets = []
            for bullet in exp.bullets:
                # Check if bullet can be enhanced with gap response
                if gap_data := self._find_matching_gap(
                    bullet, cv_impact
                ):
                    enhanced = self._enhance_bullet(
                        bullet, gap_data
                    )
                    enhanced_bullets.append(enhanced)
                else:
                    enhanced_bullets.append(bullet)

            exp.bullets = enhanced_bullets

        # Mark artifacts as using gap responses
        for response in cv_impact:
            response.used_in_artifacts.append("cv_tailoring")

        return draft_cv
```

### 4.5 Gap Response Flow Validation

After each artifact generation:

```python
def track_gap_usage(
    application_id: str,
    artifact_type: str,
    used_responses: List[str]
) -> None:
    """Track which gap responses were used in each artifact."""
    kb_repo = KnowledgeBaseRepository()

    for response_id in used_responses:
        response = kb_repo.get_response(response_id)
        if artifact_type not in response.used_in_artifacts:
            response.used_in_artifacts.append(artifact_type)
            response.last_verified = datetime.utcnow()
            kb_repo.update(response)
```

---

## 5. TDD Enforcement

### 5.1 TDD Workflow

**BEFORE any implementation code:**
1. Write failing unit test
2. Run test (verify it fails)
3. Write minimal implementation code
4. Run test (verify it passes)
5. Refactor implementation
6. Run test (verify still passes)

**AFTER each phase:**
1. Run all unit tests
2. Run all integration tests
3. Run all E2E tests
4. All must pass before proceeding

### 5.2 Test Requirements by Phase

| Phase | Unit Tests | Integration Tests | E2E Tests | Pass Required |
|-------|------------|-------------------|-----------|---------------|
| 0 | 5 | 0 | 0 | 100% |
| 1 | 20 | 5 | 0 | 100% |
| 2 | 15 | 5 | 0 | 100% |
| 3 | 15 | 3 | 2 | 100% |
| 4 | 15 | 3 | 2 | 100% |
| 5 | 15 | 3 | 2 | 100% |
| 6 | 15 | 3 | 2 | 100% |
| 7 | 10 | 2 | 1 | 100% |
| 8 | 10 | 2 | 1 | 100% |
| 9 | 15 | 3 | 2 | 100% |
| **Total** | **135** | **29** | **12** | **100%** |

### 5.3 Test Directory Structure

```
tests/
├── unit/
│   ├── test_vpr_generator.py
│   ├── test_cv_tailoring.py
│   ├── test_gap_analysis.py
│   ├── test_cover_letter.py
│   ├── test_interview_prep.py
│   ├── test_quality_validator.py
│   └── test_knowledge_base.py
│
├── integration/
│   ├── test_vpr_flow.py
│   ├── test_cv_tailoring_flow.py
│   ├── test_gap_flow.py
│   └── test_full_application_flow.py
│
├── e2e/
│   ├── test_vpr_e2e.py
│   ├── test_cv_tailoring_e2e.py
│   └── test_full_application_e2e.py
│
├── conftest.py          # Shared fixtures
├── mocks.py             # AWS mocks
└── factories.py          # Test data factories
```

### 5.4 Required Test Pattern

```python
# tests/unit/test_vpr_generator.py

import pytest
from unittest.mock import Mock, patch
from careervp.logic.vpr_generator import VPRGenerator
from careervp.models.vpr import VPRResponse, Differentiator

class TestVPRGenerator:
    """VPR Generator unit tests - TDD pattern."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM client."""
        mock = Mock()
        mock.generate.return_value = '{"uvp": "test", "differentiators": []}'
        return mock

    @pytest.fixture
    def mock_dal(self):
        """Create mock DynamoDalHandler."""
        return Mock()

    @pytest.fixture
    def generator(self, mock_llm, mock_dal):
        """Create VPR Generator with dependencies."""
        return VPRGenerator(llm=mock_llm, dal=mock_dal)

    def test_generate_fails_without_cv_facts(self, generator):
        """Stage 1: Test that missing CV facts causes failure."""
        # ARRANGE
        input_data = VPRInput(
            application_id="test-123",
            cv_facts=None,  # Missing required input
            job_requirements={"requirements": []},
            company_research={},
            gap_responses=[],
        )

        # ACT & ASSERT
        with pytest.raises(ValueError):
            generator.execute(input_data)

    def test_generate_produces_valid_vpr(self, generator):
        """Stage 5: Test that execution produces valid VPR."""
        # ARRANGE
        input_data = VPRInput(
            application_id="test-123",
            cv_facts=UserCV(...),
            job_requirements=JobRequirements(...),
            company_research=CompanyResearch(...),
            gap_responses=[GapResponse(...)],
        )

        # ACT
        result = generator.execute(input_data)

        # ASSERT
        assert result.is_ok()
        assert result.value.uvp is not None
        assert len(result.value.differentiators) >= 3
        assert result.value.quality_score >= 0.7

    def test_gap_responses_included_in_prompt(self, generator, mock_llm):
        """Test that gap responses are injected into LLM prompt."""
        # ARRANGE
        gap_response = GapResponse(
            response_id="gap-1",
            question_id="q-1",
            quantifiable_data={"percentage": 40},
        )
        input_data = VPRInput(
            application_id="test-123",
            cv_facts=UserCV(...),
            job_requirements=JobRequirements(...),
            company_research={},
            gap_responses=[gap_response],
        )

        # ACT
        generator.execute(input_data)

        # ASSERT
        call_args = mock_llm.generate.call_args
        prompt = call_args[0][0]  # First positional argument
        assert "40%" in prompt or "quantified" in prompt.lower()
```

### 5.5 Test Validation Before Proceeding

```bash
# BEFORE CONTINUING TO NEXT TASK:
echo "Running unit tests for current task..."
uv run pytest tests/unit/test_<current_feature>.py -v

if [ $? -eq 0 ]; then
    echo "✅ Unit tests PASSED - Proceeding to next task"
else
    echo "❌ Unit tests FAILED - Fix before proceeding"
    exit 1
fi

# AFTER COMPLETING PHASE:
echo "Running all phase tests..."
uv run pytest tests/unit/ tests/integration/ tests/e2e/ -v --tb=short

if [ $? -eq 0 ]; then
    echo "✅ ALL PHASE TESTS PASSED - Phase complete"
else
    echo "❌ TESTS FAILED - Fix before proceeding"
    exit 1
fi
```

---

## 6. GitHub Actions Workflows

### 6.1 Workflow Structure

```
.github/workflows/
├── pr-lint.yml           # Lint and format check on PR
├── pr-test.yml           # Unit + integration tests on PR
├── phase-0-security.yml  # Security scan for Phase 0
├── phase-1-models.yml    # Model consolidation tests
├── phase-2-dal.yml       # DAL refactoring tests
├── phase-3-vpr.yml       # VPR 6-Stage tests
├── phase-4-cv.yml        # CV Tailoring tests
├── phase-5-gap.yml       # Gap Analysis tests
├── phase-6-cover.yml     # Cover Letter tests
├── phase-7-quality.yml   # Quality Validator tests
├── phase-8-kb.yml        # Knowledge Base tests
├── phase-9-interview.yml # Interview Prep tests
└── full-validation.yml    # Full E2E validation
```

### 6.2 PR Lint Workflow

```yaml
# .github/workflows/pr-lint.yml

name: Lint & Format

on:
  pull_request:
    paths:
      - 'src/**/*.py'
      - 'infra/**/*.py'

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd src/backend
          uv pip install -e .

      - name: Run Ruff Format
        run: uv run ruff format .

      - name: Check for Changes
        id: changed-files
        uses: tj-actions/changed-files@v44

      - name: Run Ruff Check
        run: uv run ruff check ${{ steps.changed-files.all_changed_files }}

      - name: Run Type Check
        run: uv run mypy ${{ steps.changed-files.all_changed_files }} --strict

      - name: Upload Lint Report
        uses: actions/upload-artifact@v4
        with:
          name: lint-report
          path: lint_output/
```

### 6.3 Phase Validation Workflow

```yaml
# .github/workflows/phase-1-models.yml

name: Phase 1 - Model Unification

on:
  pull_request:
    paths:
      - 'src/backend/careervp/models/**'

jobs:
  validate-phase-1:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd src/backend
          uv pip install -e .

      - name: Run Model Unit Tests
        run: |
          uv run pytest tests/unit/test_models.py -v --tb=short

      - name: Verify No Duplicate Models
        run: |
          echo "Checking for duplicate model imports..."
          DUPLICATES=$(grep -r "cv_models\|fvs_models" careervp/ --include="*.py" | grep -v __pycache__ | wc -l)
          if [ $DUPLICATES -gt 0 ]; then
            echo "❌ Found $DUPLICATES duplicate model references"
            exit 1
          fi
          echo "✅ No duplicate models found"

      - name: Verify Model Consolidation
        run: |
          python -c "
          from careervp.models import UserCV, FVSResult, Result
          print('✅ All models import successfully from single source')
          "

      - name: Upload Test Report
        uses: actions/upload-artifact@v4
        with:
          name: phase-1-test-report
          path: pytest_output/
```

### 6.4 Full E2E Validation

```yaml
# .github/workflows/full-validation.yml

name: Full E2E Validation

run-name: Running full validation after phase completion

on:
  workflow_dispatch:
    inputs:
      phase:
        description: 'Phase to validate'
        required: true
        type: choice
        options:
          - all
          - phase-0
          - phase-1
          - phase-2
          - phase-3
          - phase-4
          - phase-5
          - phase-6
          - phase-7
          - phase-8
          - phase-9

jobs:
  full-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd src/backend
          uv pip install -e .

      - name: Run Unit Tests
        run: uv run pytest tests/unit/ -v --tb=short

      - name: Run Integration Tests
        run: uv run pytest tests/integration/ -v --tb=short

      - name: Run E2E Tests
        run: uv run pytest tests/e2e/ -v --tb=short

      - name: Run Code Quality
        run: |
          uv run ruff check src/backend/careervp/
          uv run ruff format --check src/backend/careervp/
          uv run mypy src/backend/careervp --strict

      - name: Generate Coverage Report
        run: uv run pytest tests/ --cov=careervp --cov-report=xml

      - name: Upload Coverage
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage.xml

      - name: Publish Result
        run: |
          if [ $? -eq 0 ]; then
            echo "✅ ALL VALIDATION PASSED"
          else
            echo "❌ VALIDATION FAILED"
            exit 1
          fi
```

---

## 7. CLAUDE Rules Enforcement

### 7.1 Required Rule Adherence

All work MUST follow these documents (in order of precedence):

1. **`~/.claude/CLAUDE.md`** - System-level Claude Code instructions
2. **`/Users/yitzchak/Documents/dev/.claude/CLAUDE.md`** - Project-level instructions
3. **`CLAUDE.md`** - CareerVP context manifest
4. **`AGENTS.md`** - Codex/Developer rules (THIS DOCUMENT)
5. **`.claude-rules.md`** - Runtime rules

### 7.2 Rule Enforcement Checklist

Before submitting any code, verify:

- [ ] **Naming Conventions** (from AGENTS.md):
  - [ ] Python classes: PascalCase
  - [ ] Python functions/variables: snake_case
  - [ ] Constants: UPPER_SNAKE_CASE
  - [ ] AWS resources: kebab-case with `careervp-` prefix
  - [ ] Files: snake_case

- [ ] **Architecture Pattern** (from CLAUDE.md):
  - [ ] Handler → Logic → DAL separation
  - [ ] No business logic in handlers
  - [ ] No direct DAL construction in handlers
  - [ ] Powertools decorators on all handlers

- [ ] **Testing Requirements** (from AGENTS.md):
  - [ ] Test-first development
  - [ ] Mock AWS services with `moto`
  - [ ] Mock LLM calls
  - [ ] 80% code coverage target

- [ ] **Code Quality**:
  - [ ] Ruff format applied
  - [ ] Ruff check passes
  - [ ] Mypy strict passes
  - [ ] No type errors

- [ ] **Security**:
  - [ ] Input validation with Pydantic
  - [ ] No raw exceptions in responses
  - [ ] No PII in logs
  - [ ] API authorizer configured

### 7.3 Naming Validator Integration

```bash
# MANDATORY: Run after ANY change to infra/ or src/backend/

cd /Users/yitzchak/Documents/dev/careervp

# Validate naming conventions
python src/backend/scripts/validate_naming.py --path infra --verbose

# If strict mode required
python src/backend/scripts/validate_naming.py --path infra --strict
```

### 7.4 Pre-Commit Hook

```yaml
# .pre-commit-config.yaml

repos:
  - repo: local
    hooks:
      - id: ruff-format
        name: Ruff Format
        entry: uv run ruff format
        language: system
        types: [python]

      - id: ruff-check
        name: Ruff Check
        entry: uv run ruff check --fix
        language: system
        types: [python]

      - id: mypy-check
        name: Type Check
        entry: uv run mypy
        language: system
        types: [python]

      - id: naming-validator
        name: Naming Validator
        entry: python src/backend/scripts/validate_naming.py --path infra --strict
        language: system
        files: ^infra/
```

---

## 8. Class Coding Guidelines

### 8.1 Class Structure

```python
# FILE: feature_name.py

"""
Feature Name - Brief description.

Longer description if needed.
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Optional,
    Any,
)
from dataclasses import dataclass

if TYPE_CHECKING:
    from careervp.models.result import Result

# =============================================================================
# EXCEPTIONS
# =============================================================================

class FeatureError(Exception):
    """Base exception for feature errors."""
    pass

class ValidationError(FeatureError):
    """Raised when input validation fails."""
    pass

class ProcessingError(FeatureError):
    """Raised when processing fails."""
    pass


# =============================================================================
# MODELS
# =============================================================================

@dataclass
class FeatureInput:
    """Input data for feature execution."""
    application_id: str
    user_email: str
    # Add fields here

    def validate(self) -> None:
        """Validate input data."""
        if not self.application_id:
            raise ValidationError("application_id is required")


@dataclass
class FeatureOutput:
    """Output data from feature execution."""
    result_id: str
    content: Dict[str, Any]
    quality_score: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FeatureOutput:
        """Create from dictionary."""
        return cls(
            result_id=data["id"],
            content=data["content"],
            quality_score=data.get("score", 0.0),
        )


# =============================================================================
# LOGIC
# =============================================================================

class FeatureLogic:
    """
    Feature logic following staged thinking pattern.

    Attributes:
        llm: LLM client for AI operations
        repository: Data access layer
    """

    def __init__(
        self,
        llm: "LLMClient",
        repository: "FeatureRepository",
    ) -> None:
        """Initialize with dependencies."""
        self._llm = llm
        self._repository = repository

    def execute(self, input_data: FeatureInput) -> Result[FeatureOutput]:
        """
        Execute feature following staged thinking.

        Args:
            input_data: Validated input

        Returns:
            Result containing FeatureOutput or error
        """
        input_data.validate()

        # Stage 1: Analyze input
        context = self._analyze_input(input_data)

        # Stage 2: Extract evidence
        evidence = self._extract_evidence(context)

        # Stage 3: Synthesize
        synthesis = self._synthesize(evidence)

        # Stage 4: Self-correct
        verified = self._self_correct(synthesis)

        # Stage 5: Generate output
        output = self._generate_output(verified)

        return Result.ok(output)

    # -------------------------------------------------------------------------
    # Staged Thinking Methods (protected)
    # -------------------------------------------------------------------------

    def _analyze_input(self, input_data: FeatureInput) -> Dict[str, Any]:
        """Stage 1: Analyze input and build context."""
        return {"input": input_data}

    def _extract_evidence(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 2: Extract evidence from sources."""
        return context

    def _synthesize(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 3: Strategic synthesis."""
        return evidence

    def _self_correct(self, synthesis: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 4: Meta-review and correction."""
        return synthesis

    def _generate_output(
        self, verified: Dict[str, Any]
    ) -> FeatureOutput:
        """Stage 5: Generate final output."""
        return FeatureOutput(
            result_id="generated-id",
            content=verified,
            quality_score=0.0,
        )


# =============================================================================
# REPOSITORY
# =============================================================================

class FeatureRepository:
    """Data access layer for feature."""

    def __init__(self, dal: "DynamoDalHandler") -> None:
        """Initialize with data access layer."""
        self._dal = dal
        self._table_name = "careervp-feature-table"

    def save(
        self,
        user_email: str,
        item_id: str,
        data: Dict[str, Any],
        ttl_hours: int = 720,
    ) -> Result[str]:
        """Save feature output."""
        item = {
            "pk": f"USER#{user_email}",
            "sk": f"FEATURE#{item_id}",
            "data": data,
            "created_at": "ISO_TIMESTAMP",
            "expires_at": "ISO_TIMESTAMP_plus_TTL",
        }
        return self._dal.put_item(self._table_name, item)

    def get(
        self,
        user_email: str,
        item_id: str,
    ) -> Result[Optional[Dict[str, Any]]]:
        """Retrieve feature output."""
        key = {
            "pk": f"USER#{user_email}",
            "sk": f"FEATURE#{item_id}",
        }
        return self._dal.get_item(self._table_name, key)
```

### 8.2 Handler Template

```python
# FILE: feature_handler.py

"""
Feature Handler - AWS Lambda entry point.

Provides API endpoint for feature operations.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

from careervp.models.result import Result

logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Import after logger initialized
from careervp.logic.feature_logic import FeatureLogic
from careervp.logic.llm_client import LLMClient
from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.models.feature import FeatureInput


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle feature API request.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    try:
        # Parse request
        body = json.loads(event["body"])
        input_data = FeatureInput(**body)

        # Initialize dependencies
        llm = LLMClient()
        dal = DynamoDalHandler()
        logic = FeatureLogic(llm=llm, repository=FeatureRepository(dal))

        # Execute
        result = logic.execute(input_data)

        if result.is_ok():
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "status": "success",
                    "data": result.value.to_dict(),
                }),
            }
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "status": "error",
                    "message": str(result.error),
                }),
            }

    except Exception as exc:
        logger.exception("Feature handler failed")
        metrics.add_metric(name="Errors", unit=MetricUnit.Count, value=1)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "message": "Internal server error",
            }),
        }
```

### 8.3 File Organization Rules

| Layer | Directory | File Pattern | Examples |
|-------|-----------|--------------|----------|
| **Models** | `models/` | `feature_name.py` | `cv.py`, `vpr.py`, `gap_analysis.py` |
| **Logic** | `logic/` | `feature_name.py` | `vpr_generator.py`, `cv_tailoring.py` |
| **Handlers** | `handlers/` | `feature_handler.py` | `vpr_handler.py`, `cv_handler.py` |
| **DAL** | `dal/` | `feature_repository.py` | `jobs_repository.py` |
| **Prompts** | `logic/prompts/` | `feature_prompt.py` | `vpr_prompt.py` |

### 8.4 Import Order

```python
# 1. Python standard library
from __future__ import annotations
import json
import logging
from typing import TYPE_CHECKING, Dict, List

# 2. Third-party packages
from pydantic import BaseModel, validator
from aws_lambda_powertools import Logger, Tracer

# 3. AWS SDK (if needed)
import boto3

# 4. Project local - models
from careervp.models.result import Result
from careervp.models.feature import FeatureInput

# 5. Project local - logic
from careervp.logic.llm_client import LLMClient

# 6. Project local - DAL
from careervp.dal.dynamo_dal_handler import DynamoDalHandler

if TYPE_CHECKING:
    from careervp.logic.feature_logic import FeatureLogic
```

### 8.5 Error Handling Pattern

```python
from result import Result, Ok, Err

class FeatureError(Exception):
    """Base error."""
    pass

class ValidationError(FeatureError):
    """Input validation failed."""
    pass

class ProcessingError(FeatureError):
    """Processing failed."""
    pass

def process_feature(input_data: Input) -> Result[Output]:
    """
    Process with error handling.

    Returns:
        Ok(Output) on success
        Err(Error) on failure
    """
    try:
        # Validate
        if not input_data.is_valid():
            return Err(ValidationError("Invalid input"))

        # Process
        result = _do_processing(input_data)

        return Ok(result)

    except Exception as exc:
        logger.error(f"Processing failed: {exc}")
        return Err(ProcessingError(str(exc)))
```

---

## 9. Implementation Phases

*(Sections 9-14 continue with detailed phase breakdowns - see PHASE_*_TASKS.md files)*

---

## 10. Dependencies and Sequencing

### 10.1 Dependency Graph

```
Phase 0 (Security)
    │
    ▼
Phase 1 (Models) ──────► Phase 2 (DAL)
    │                       │
    │                       ▼
    │               Phase 3 (VPR 6-Stage)
    │                       │
    │                       ▼
    │               Phase 4 (CV 3-Step)
    │                       │
    │                       ▼
    │               Phase 5 (Gap Analysis)
    │                       │
    │                       ▼
    │               Phase 6 (Cover Letter)
    │                       │
    └───────────────────────┴──► Phase 7 (Quality Validator)
                                    │
                                    ├──► Phase 8 (Knowledge Base)
                                    │
                                    └──► Phase 9 (Interview Prep)
```

### 10.2 Cost Optimization Implementation

**From COST_OPTIMIZATION_VALIDATION.md (2026-02-10)**

| Strategy | Status | Cost Impact | Implementation |
|----------|--------|-------------|----------------|
| Response truncation | ✅ IMPLEMENTED | ~20% savings | `max_tokens` in llm_client.py |
| Haiku template | ✅ IMPLEMENTED | ~49% savings | `TaskMode.TEMPLATE` enum |
| Prompt compression | ❌ NOT IMPLEMENTED | $0.0005/letter | Add to Phase 2 |
| Caching | ⚠️ PARTIAL | $0.002/cached op | Add to Phase 2 |

#### 10.2.1 CV Summarizer (Prompt Compression)

**File:** `src/backend/careervp/logic/cv_summarizer.py`

**Purpose:** Reduce CV text from ~5000 tokens to ~500 token highlights

```python
class CVSummarizer:
    """Extract highlights from CV for cost optimization."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    def extract_highlights(self, cv_text: str) -> SummarizedCV:
        """Extract key skills, achievements, and experience."""
        pass
```

#### 10.2.2 LLM Content Cache

**File:** `src/backend/careervp/logic/llm_content_cache.py`

**TTL Configuration:**
- CV Context: 24 hours
- Job Requirements: 1 hour
- Company Research: 30 days

```python
class LLMContentCache:
    """Cache LLM input content to avoid redundant token costs."""

    def __init__(self, dal: DynamoDalHandler) -> None:
        self._dal = dal

    def cache_cv_context(self, user_email: str, cv_id: str, context: dict) -> Result[None]:
        """Cache CV context (24-hour TTL)."""
        pass

    def cache_job_requirements(self, job_id: str, requirements: dict) -> Result[None]:
        """Cache job requirements (1-hour TTL)."""
        pass

    def cache_company_research(self, company_domain: str, research: dict) -> Result[None]:
        """Cache company research (30-day TTL)."""
        pass
```

### 10.3 Critical Path

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 5 → Phase 6
          (22h)    (20h)     (10h)     (13h)     (13h)

Total Critical Path: 78 hours (10 days)
```

---

## 11. Effort Estimates

| Phase | Hours | Days | Tests Required |
|-------|-------|------|----------------|
| Phase 0 | 8h | 1d | 5 unit |
| Phase 1 | 22h | 3d | 20 unit, 5 integration |
| Phase 2 | 20h | 2.5d | 15 unit, 5 integration |
| Phase 3 | 10h | 1.5d | 15 unit, 3 integration, 2 E2E |
| Phase 4 | 11h | 1.5d | 15 unit, 3 integration, 2 E2E |
| Phase 5 | 13h | 2d | 15 unit, 3 integration, 2 E2E |
| Phase 6 | 13h | 2d | 15 unit, 3 integration, 2 E2E |
| Phase 7 | 12h | 1.5d | 10 unit, 2 integration, 1 E2E |
| Phase 8 | 12h | 1.5d | 10 unit, 2 integration, 1 E2E |
| Phase 9 | 16h | 2d | 15 unit, 3 integration, 2 E2E |
| **Total** | **137h** | **18d** | **135 unit, 29 integration, 12 E2E** |

---

## 12. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Model consolidation breaks VPR ↔ CV | Medium | Critical | Feature flags; extensive testing |
| 6-stage prompts unreliable | Medium | High | Output validation; prompt tuning |
| Scope creep | High | Medium | Strict scope control |
| Knowledge Base insufficient | Low | High | Design review before Phase 8 |

---

## 13. Validation Strategy

### 13.1 Validation Gates

| Phase | Gate | Pass Required |
|-------|------|---------------|
| All | Unit tests | 100% |
| All | Integration tests | 100% |
| Phase 0 | Security scan | Pass |
| Phase 1 | No duplicate models | Pass |
| All | Linting | 0 errors |
| All | Type checking | 0 errors |
| Phase 9 | E2E tests | 100% |

### 13.2 Validation Commands

```bash
# Full validation
uv run pytest tests/unit/ tests/integration/ tests/e2e/ -v --tb=short
uv run ruff check src/backend/careervp/
uv run ruff format --check src/backend/careervp/
uv run mypy src/backend/careervp --strict
```

---

## 14. Appendix: File Change Matrix

### 14.1 Files to CREATE

| File | Phase | Purpose |
|------|-------|---------|
| `.github/workflows/phase-*.yml` | All | CI/CD workflows |
| `handlers/cover_letter_handler.py` | 6 | Cover Letter endpoint |
| `handlers/quality_validator_handler.py` | 7 | Quality validation |
| `handlers/interview_prep_handler.py` | 9 | Interview Prep |
| `dal/knowledge_repository.py` | 8 | Knowledge Base CRUD |

### 14.2 Files to MODIFY

| File | Phase | Change |
|------|-------|--------|
| `infra/careervp/api_construct.py` | 0 | Add authorizer |
| `models/cv.py` | 1 | Consolidate UserCV |
| `logic/prompts/vpr_prompt.py` | 3 | 6-stage methodology |
| `logic/cv_tailoring_logic.py` | 4 | 3-step verification |

### 14.3 Files to REMOVE

| File | Reason | Phase |
|------|--------|-------|
| `models/cv_models.py` | Merged | 1 |
| `models/fvs_models.py` | Merged | 1 |

---

**Document Status:** DRAFT - FOR REVIEW
**Version:** 1.2
**Last Updated:** 2026-02-10 (Added Phase 2 Cost Optimization)

---

**END OF REFACTORING PLAN**
