# Task 9.5: CV Tailoring - Unit Tests

**Status:** Pending
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** Task 9.1 (Models), Task 9.2 (Logic), Task 9.3 (Handler)

## Overview

Implement comprehensive unit tests for the CV tailoring feature with 80%+ code coverage. Tests cover models validation, logic layer functions, handler endpoints, and FVS validation rules.

## Todo

### Test File Setup

- [ ] Create `tests/unit/test_cv_tailor.py`
- [ ] Create test fixtures for UserCV, JobPosting, CompanyResearch
- [ ] Create mock DAL handler
- [ ] Create mock LLM client responses

### Model Tests

- [ ] Test `TailorCVRequest` validation (valid and invalid inputs)
- [ ] Test `TailoredCV` serialization/deserialization
- [ ] Test `StylePreferences` defaults
- [ ] Test FVS tier field descriptions

### Logic Tests

- [ ] Test `tailor_cv()` happy path
- [ ] Test `tailor_cv()` with FVS validation failure and retry
- [ ] Test `_extract_immutable_facts()` extracts all tiers correctly
- [ ] Test `_validate_tailored_output()` catches hallucinations
- [ ] Test `_aggregate_inputs()` with and without gap analysis
- [ ] Test retry logic with exponential backoff

### Handler Tests

- [ ] Test `lambda_handler()` returns 200 on success
- [ ] Test `lambda_handler()` returns 400 on invalid request
- [ ] Test `lambda_handler()` returns 404 when CV not found
- [ ] Test `lambda_handler()` returns 422 on FVS failure
- [ ] Test `_map_result_code_to_http_status()` mapping
- [ ] Test metrics emission on success

### Coverage & Validation

- [ ] Run `uv run pytest tests/unit/test_cv_tailor.py -v --cov=careervp.logic.cv_tailor --cov=careervp.handlers.cv_tailor_handler --cov-report=term-missing`
- [ ] Verify coverage ≥80%
- [ ] Run `uv run ruff format tests/`
- [ ] Run `uv run ruff check --fix tests/`
- [ ] Run `uv run mypy tests/ --strict`

### Commit

- [ ] Commit with message: `test(cv-tailor): add unit tests with 80%+ coverage`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `tests/unit/test_cv_tailor.py` | All CV tailoring unit tests |
| `tests/conftest.py` | Shared fixtures (may need updates) |

### Key Implementation Details

```python
"""
Unit tests for CV Tailoring feature.
Per docs/specs/04-cv-tailoring.md.

Coverage target: 80%+
"""

from __future__ import annotations

import json
from datetime import datetime
from http import HTTPStatus
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from careervp.handlers.cv_tailor_handler import (
    _map_result_code_to_http_status,
    _parse_body,
    lambda_handler,
)
from careervp.logic.cv_tailor import (
    _aggregate_inputs,
    _extract_immutable_facts,
    _validate_tailored_output,
    tailor_cv,
)
from careervp.models.cv import ContactInfo, Education, UserCV, WorkExperience
from careervp.models.job import CompanyContext, JobPosting
from careervp.models.result import Result, ResultCode
from careervp.models.tailor import (
    StylePreferences,
    TailoredCV,
    TailoredCVData,
    TailoredSkill,
    TailoredWorkExperience,
    TailoringMetadata,
    TailorCVRequest,
    TailorCVResponse,
    TokenUsage,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_user_cv() -> UserCV:
    """Create a sample UserCV for testing."""
    return UserCV(
        user_id="user-123",
        contact_info=ContactInfo(
            full_name="John Doe",
            email="john@example.com",
            phone="+1-555-0100",
            location="New York, NY",
        ),
        work_experience=[
            WorkExperience(
                company_name="Acme Corp",
                job_title="Software Engineer",
                start_date="2020-01",
                end_date="2023-06",
                location="New York, NY",
                description_bullets=[
                    "Built REST APIs using Python and Flask",
                    "Improved database query performance by 40%",
                    "Mentored 3 junior developers",
                ],
            ),
        ],
        education=[
            Education(
                institution="State University",
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                graduation_date="2020",
            ),
        ],
        skills=["Python", "Flask", "PostgreSQL", "AWS"],
        certifications=[],
    )


@pytest.fixture
def sample_job_posting() -> JobPosting:
    """Create a sample JobPosting for testing."""
    return JobPosting(
        job_id="job-456",
        title="Senior Backend Engineer",
        company_name="TechStartup Inc",
        description="We are looking for a senior backend engineer...",
        requirements=[
            "5+ years Python experience",
            "Experience with microservices architecture",
            "Strong SQL skills",
        ],
        location="Remote",
    )


@pytest.fixture
def sample_company_research() -> CompanyContext:
    """Create sample CompanyResearch for testing."""
    return CompanyContext(
        company_name="TechStartup Inc",
        industry="Technology",
        company_size="50-200",
        culture_keywords=["innovative", "fast-paced", "collaborative"],
        recent_news=["Series B funding announced"],
    )


@pytest.fixture
def sample_tailor_request() -> TailorCVRequest:
    """Create a sample TailorCVRequest for testing."""
    return TailorCVRequest(
        user_id="user-123",
        application_id="app-789",
        job_id="job-456",
        cv_version=1,
        include_gap_analysis=False,
        output_format="json",
        style_preferences=StylePreferences(
            tone="professional",
            formality_level="high",
            include_summary=True,
        ),
    )


@pytest.fixture
def sample_tailored_cv(sample_user_cv: UserCV) -> TailoredCV:
    """Create a sample TailoredCV for testing."""
    return TailoredCV(
        contact_info={
            "full_name": "John Doe",
            "email": "john@example.com",
            "phone": "+1-555-0100",
            "location": "New York, NY",
        },
        executive_summary="Experienced backend engineer with expertise in Python...",
        work_experience=[
            TailoredWorkExperience(
                company_name="Acme Corp",
                job_title="Software Engineer",
                start_date="2020-01",
                end_date="2023-06",
                location="New York, NY",
                description_bullets=[
                    "Developed RESTful microservices in Python/Flask supporting internal tooling",
                    "Optimized database queries, achieving 40% performance improvement",
                    "Mentored junior developers on best practices",
                ],
                keyword_alignments=["Python", "microservices"],
                original_bullets=[
                    "Built REST APIs using Python and Flask",
                    "Improved database query performance by 40%",
                    "Mentored 3 junior developers",
                ],
            ),
        ],
        skills=[
            TailoredSkill(
                skill_name="Python",
                proficiency_level="Expert",
                relevance_score=0.95,
                matched_requirements=["5+ years Python experience"],
            ),
            TailoredSkill(
                skill_name="Flask",
                proficiency_level="Advanced",
                relevance_score=0.7,
                matched_requirements=[],
            ),
        ],
        education=[
            {
                "institution": "State University",
                "degree": "Bachelor of Science",
                "field_of_study": "Computer Science",
                "graduation_date": "2020",
            }
        ],
        certifications=[],
        source_cv_version=1,
        target_job_id="job-456",
        tailoring_version=1,
    )


@pytest.fixture
def mock_dal() -> MagicMock:
    """Create a mock DAL handler."""
    dal = MagicMock()
    dal.get_user_cv.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)
    dal.get_job_posting.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)
    dal.get_company_research.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)
    dal.save_tailored_cv.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)
    dal.get_gap_analysis.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)
    return dal


# =============================================================================
# MODEL TESTS
# =============================================================================


class TestTailorCVRequest:
    """Tests for TailorCVRequest model."""

    def test_valid_request(self) -> None:
        """Test valid request creation."""
        request = TailorCVRequest(
            user_id="user-123",
            application_id="app-456",
            job_id="job-789",
        )
        assert request.user_id == "user-123"
        assert request.cv_version == 1  # default
        assert request.include_gap_analysis is False  # default
        assert request.output_format == "json"  # default

    def test_invalid_cv_version(self) -> None:
        """Test that cv_version must be >= 1."""
        with pytest.raises(ValidationError):
            TailorCVRequest(
                user_id="user-123",
                application_id="app-456",
                job_id="job-789",
                cv_version=0,  # invalid
            )

    def test_style_preferences_defaults(self) -> None:
        """Test StylePreferences default values."""
        prefs = StylePreferences()
        assert prefs.tone == "professional"
        assert prefs.formality_level == "high"
        assert prefs.include_summary is True


class TestTailoredCV:
    """Tests for TailoredCV model."""

    def test_serialization(self, sample_tailored_cv: TailoredCV) -> None:
        """Test TailoredCV serializes to JSON correctly."""
        json_str = sample_tailored_cv.model_dump_json()
        data = json.loads(json_str)
        assert data["contact_info"]["full_name"] == "John Doe"
        assert len(data["work_experience"]) == 1
        assert data["work_experience"][0]["company_name"] == "Acme Corp"

    def test_deserialization(self, sample_tailored_cv: TailoredCV) -> None:
        """Test TailoredCV deserializes from dict correctly."""
        data = sample_tailored_cv.model_dump()
        restored = TailoredCV.model_validate(data)
        assert restored.contact_info == sample_tailored_cv.contact_info
        assert len(restored.work_experience) == 1


class TestTailoredWorkExperience:
    """Tests for TailoredWorkExperience model."""

    def test_immutable_fields_preserved(self) -> None:
        """Test that IMMUTABLE fields are present."""
        exp = TailoredWorkExperience(
            company_name="Acme Corp",
            job_title="Engineer",
            start_date="2020-01",
            end_date="2023-01",
            location="NYC",
            description_bullets=["Did work"],
            original_bullets=["Did work"],
        )
        # Verify IMMUTABLE fields are documented
        assert "IMMUTABLE" in exp.model_fields["company_name"].description
        assert "IMMUTABLE" in exp.model_fields["job_title"].description
        assert "IMMUTABLE" in exp.model_fields["start_date"].description


# =============================================================================
# LOGIC TESTS
# =============================================================================


class TestExtractImmutableFacts:
    """Tests for _extract_immutable_facts function."""

    def test_extracts_work_experience(self, sample_user_cv: UserCV) -> None:
        """Test work experience facts are extracted."""
        facts = _extract_immutable_facts(sample_user_cv)
        assert len(facts["work_experiences"]) == 1
        assert facts["work_experiences"][0]["company_name"] == "Acme Corp"
        assert facts["work_experiences"][0]["job_title"] == "Software Engineer"
        assert facts["work_experiences"][0]["start_date"] == "2020-01"

    def test_extracts_education(self, sample_user_cv: UserCV) -> None:
        """Test education facts are extracted."""
        facts = _extract_immutable_facts(sample_user_cv)
        assert len(facts["education"]) == 1
        assert facts["education"][0]["institution"] == "State University"
        assert facts["education"][0]["degree"] == "Bachelor of Science"

    def test_extracts_contact_info(self, sample_user_cv: UserCV) -> None:
        """Test contact info is extracted."""
        facts = _extract_immutable_facts(sample_user_cv)
        assert facts["contact_info"]["full_name"] == "John Doe"
        assert facts["contact_info"]["email"] == "john@example.com"


class TestValidateTailoredOutput:
    """Tests for _validate_tailored_output function."""

    def test_valid_output_passes(
        self,
        sample_tailored_cv: TailoredCV,
        sample_user_cv: UserCV,
    ) -> None:
        """Test that valid tailored CV passes validation."""
        facts = _extract_immutable_facts(sample_user_cv)
        result = _validate_tailored_output(sample_tailored_cv, facts, sample_user_cv)
        assert result.success is True

    def test_hallucinated_company_fails(
        self,
        sample_tailored_cv: TailoredCV,
        sample_user_cv: UserCV,
    ) -> None:
        """Test that hallucinated company name fails validation."""
        # Modify company name to something not in source
        sample_tailored_cv.work_experience[0].company_name = "Fake Corp"
        facts = _extract_immutable_facts(sample_user_cv)
        result = _validate_tailored_output(sample_tailored_cv, facts, sample_user_cv)
        assert result.success is False
        assert "Company name mismatch" in result.error

    def test_hallucinated_skill_fails(
        self,
        sample_tailored_cv: TailoredCV,
        sample_user_cv: UserCV,
    ) -> None:
        """Test that hallucinated skill fails validation."""
        # Add a skill not in source CV
        sample_tailored_cv.skills.append(
            TailoredSkill(
                skill_name="Kubernetes",  # Not in source CV
                relevance_score=0.8,
            )
        )
        facts = _extract_immutable_facts(sample_user_cv)
        result = _validate_tailored_output(sample_tailored_cv, facts, sample_user_cv)
        assert result.success is False
        assert "Hallucinated skill" in result.error

    def test_hallucinated_date_fails(
        self,
        sample_tailored_cv: TailoredCV,
        sample_user_cv: UserCV,
    ) -> None:
        """Test that modified date fails validation."""
        sample_tailored_cv.work_experience[0].start_date = "2019-01"  # Changed
        facts = _extract_immutable_facts(sample_user_cv)
        result = _validate_tailored_output(sample_tailored_cv, facts, sample_user_cv)
        assert result.success is False
        assert "Start date mismatch" in result.error


class TestAggregateInputs:
    """Tests for _aggregate_inputs function."""

    def test_aggregates_without_gap_analysis(
        self,
        sample_user_cv: UserCV,
        sample_job_posting: JobPosting,
        sample_company_research: CompanyContext,
    ) -> None:
        """Test aggregation without gap analysis."""
        result = _aggregate_inputs(
            sample_user_cv,
            sample_job_posting,
            sample_company_research,
            gap_analysis=None,
        )
        assert "user_cv" in result
        assert "job_posting" in result
        assert "company_research" in result
        assert "gap_analysis" not in result

    def test_aggregates_with_gap_analysis(
        self,
        sample_user_cv: UserCV,
        sample_job_posting: JobPosting,
        sample_company_research: CompanyContext,
    ) -> None:
        """Test aggregation with gap analysis."""
        gap = {"missing_skills": ["Kubernetes"]}
        result = _aggregate_inputs(
            sample_user_cv,
            sample_job_posting,
            sample_company_research,
            gap_analysis=gap,
        )
        assert "gap_analysis" in result
        assert result["gap_analysis"]["missing_skills"] == ["Kubernetes"]


class TestTailorCVLogic:
    """Tests for tailor_cv main function."""

    @patch("careervp.logic.cv_tailor.LLMClient")
    def test_happy_path(
        self,
        mock_llm_class: MagicMock,
        sample_tailor_request: TailorCVRequest,
        sample_user_cv: UserCV,
        sample_job_posting: JobPosting,
        sample_company_research: CompanyContext,
        sample_tailored_cv: TailoredCV,
        mock_dal: MagicMock,
    ) -> None:
        """Test successful CV tailoring."""
        # Setup mock LLM response
        mock_llm = mock_llm_class.return_value
        mock_llm.generate.return_value = Result(
            success=True,
            data=sample_tailored_cv,
            code=ResultCode.SUCCESS,
            metadata={"input_tokens": 1000, "output_tokens": 800},
        )

        result = tailor_cv(
            request=sample_tailor_request,
            user_cv=sample_user_cv,
            job_posting=sample_job_posting,
            company_research=sample_company_research,
            dal=mock_dal,
        )

        assert result.success is True
        assert result.code == ResultCode.CV_TAILORED
        assert result.data is not None
        assert result.data.tailored_cv is not None

    @patch("careervp.logic.cv_tailor.LLMClient")
    @patch("careervp.logic.cv_tailor.time.sleep")
    def test_retry_on_validation_failure(
        self,
        mock_sleep: MagicMock,
        mock_llm_class: MagicMock,
        sample_tailor_request: TailorCVRequest,
        sample_user_cv: UserCV,
        sample_job_posting: JobPosting,
        sample_company_research: CompanyContext,
        sample_tailored_cv: TailoredCV,
        mock_dal: MagicMock,
    ) -> None:
        """Test retry logic when FVS validation fails."""
        # First response has hallucinated skill
        bad_cv = sample_tailored_cv.model_copy(deep=True)
        bad_cv.skills.append(
            TailoredSkill(skill_name="Hallucinated", relevance_score=0.5)
        )

        mock_llm = mock_llm_class.return_value
        mock_llm.generate.side_effect = [
            # First call fails validation
            Result(success=True, data=bad_cv, code=ResultCode.SUCCESS, metadata={}),
            # Second call succeeds
            Result(
                success=True,
                data=sample_tailored_cv,
                code=ResultCode.SUCCESS,
                metadata={"input_tokens": 1000, "output_tokens": 800},
            ),
        ]

        result = tailor_cv(
            request=sample_tailor_request,
            user_cv=sample_user_cv,
            job_posting=sample_job_posting,
            company_research=sample_company_research,
            dal=mock_dal,
        )

        assert result.success is True
        assert mock_llm.generate.call_count == 2
        mock_sleep.assert_called_once()  # Retry delay


# =============================================================================
# HANDLER TESTS
# =============================================================================


class TestParseBody:
    """Tests for _parse_body function."""

    def test_parses_json_string(self) -> None:
        """Test parsing JSON string body."""
        event = {"body": '{"user_id": "123"}'}
        result = _parse_body(event)
        assert result["user_id"] == "123"

    def test_parses_dict_body(self) -> None:
        """Test parsing dict body (already parsed)."""
        event = {"body": {"user_id": "123"}}
        result = _parse_body(event)
        assert result["user_id"] == "123"

    def test_raises_on_missing_body(self) -> None:
        """Test raises ValueError when body is missing."""
        event = {}
        with pytest.raises(ValueError, match="Request body is required"):
            _parse_body(event)

    def test_raises_on_invalid_json(self) -> None:
        """Test raises JSONDecodeError on invalid JSON."""
        event = {"body": "not valid json"}
        with pytest.raises(json.JSONDecodeError):
            _parse_body(event)


class TestMapResultCodeToHttpStatus:
    """Tests for _map_result_code_to_http_status function."""

    @pytest.mark.parametrize(
        "code,expected_status",
        [
            (ResultCode.CV_TAILORED, HTTPStatus.OK),
            (ResultCode.INVALID_INPUT, HTTPStatus.BAD_REQUEST),
            (ResultCode.CV_NOT_FOUND, HTTPStatus.NOT_FOUND),
            (ResultCode.JOB_NOT_FOUND, HTTPStatus.NOT_FOUND),
            (ResultCode.FVS_HALLUCINATION_DETECTED, HTTPStatus.UNPROCESSABLE_ENTITY),
            (ResultCode.LLM_API_ERROR, HTTPStatus.BAD_GATEWAY),
            (ResultCode.LLM_TIMEOUT, HTTPStatus.GATEWAY_TIMEOUT),
            (ResultCode.INTERNAL_ERROR, HTTPStatus.INTERNAL_SERVER_ERROR),
        ],
    )
    def test_mapping(self, code: str, expected_status: HTTPStatus) -> None:
        """Test result code to HTTP status mapping."""
        assert _map_result_code_to_http_status(code) == expected_status

    def test_unknown_code_returns_500(self) -> None:
        """Test unknown code returns 500."""
        assert _map_result_code_to_http_status("UNKNOWN") == HTTPStatus.INTERNAL_SERVER_ERROR


class TestLambdaHandler:
    """Tests for lambda_handler function."""

    @patch("careervp.logic.cv_tailor.tailor_cv")
    @patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler")
    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "test-table"})
    def test_returns_200_on_success(
        self,
        mock_dal_class: MagicMock,
        mock_tailor_cv: MagicMock,
        sample_tailor_request: TailorCVRequest,
        sample_tailored_cv: TailoredCV,
        sample_user_cv: UserCV,
        sample_job_posting: JobPosting,
        sample_company_research: CompanyContext,
    ) -> None:
        """Test handler returns 200 on successful tailoring."""
        # Setup mocks
        mock_dal = mock_dal_class.return_value
        mock_dal.get_user_cv.return_value = Result(
            success=True, data=sample_user_cv, code=ResultCode.SUCCESS
        )
        mock_dal.get_job_posting.return_value = Result(
            success=True, data=sample_job_posting, code=ResultCode.SUCCESS
        )
        mock_dal.get_company_research.return_value = Result(
            success=True, data=sample_company_research, code=ResultCode.SUCCESS
        )

        tailored_data = TailoredCVData(
            tailored_cv=sample_tailored_cv,
            metadata=TailoringMetadata(
                application_id="app-789",
                version=1,
                created_at=datetime.utcnow(),
                keyword_matches=10,
                sections_modified=["executive_summary"],
                fvs_validation_passed=True,
            ),
            token_usage=TokenUsage(
                input_tokens=1000,
                output_tokens=800,
                model="claude-haiku-4-5-20250315",
            ),
        )
        mock_tailor_cv.return_value = Result(
            success=True, data=tailored_data, code=ResultCode.CV_TAILORED
        )

        event = {"body": sample_tailor_request.model_dump_json()}
        context = MagicMock()

        response = lambda_handler(event, context)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["success"] is True
        assert body["code"] == ResultCode.CV_TAILORED

    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "test-table"})
    def test_returns_400_on_invalid_request(self) -> None:
        """Test handler returns 400 for invalid request."""
        event = {"body": '{"invalid": "request"}'}
        context = MagicMock()

        response = lambda_handler(event, context)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["success"] is False
        assert body["code"] == ResultCode.INVALID_INPUT

    @patch("careervp.dal.dynamo_dal_handler.DynamoDalHandler")
    @patch.dict("os.environ", {"DYNAMODB_TABLE_NAME": "test-table"})
    def test_returns_404_when_cv_not_found(
        self,
        mock_dal_class: MagicMock,
        sample_tailor_request: TailorCVRequest,
    ) -> None:
        """Test handler returns 404 when CV not found."""
        mock_dal = mock_dal_class.return_value
        mock_dal.get_user_cv.return_value = Result(
            success=True, data=None, code=ResultCode.SUCCESS
        )

        event = {"body": sample_tailor_request.model_dump_json()}
        context = MagicMock()

        response = lambda_handler(event, context)

        assert response["statusCode"] == 404
        body = json.loads(response["body"])
        assert body["code"] == ResultCode.CV_NOT_FOUND


# =============================================================================
# PROMPT TESTS
# =============================================================================


class TestBuildTailorPrompt:
    """Tests for build_tailor_prompt function."""

    def test_includes_anti_detection_rules(
        self,
        sample_user_cv: UserCV,
        sample_job_posting: JobPosting,
        sample_company_research: CompanyContext,
    ) -> None:
        """Test that prompt includes anti-detection rules."""
        from careervp.logic.prompts.cv_tailor_prompt import build_tailor_prompt

        context = _aggregate_inputs(
            sample_user_cv, sample_job_posting, sample_company_research
        )
        prompt = build_tailor_prompt(context)

        assert "ANTI-DETECTION REQUIREMENTS" in prompt
        assert "AVOID AI CLICHÉS" in prompt
        assert "leverage" in prompt.lower()  # Listed as word to avoid

    def test_includes_few_shot_examples(
        self,
        sample_user_cv: UserCV,
        sample_job_posting: JobPosting,
        sample_company_research: CompanyContext,
    ) -> None:
        """Test that prompt includes few-shot examples."""
        from careervp.logic.prompts.cv_tailor_prompt import build_tailor_prompt

        context = _aggregate_inputs(
            sample_user_cv, sample_job_posting, sample_company_research
        )
        prompt = build_tailor_prompt(context)

        assert "EXAMPLE 1:" in prompt
        assert "WHY THIS WORKS:" in prompt

    def test_includes_gap_analysis_when_provided(
        self,
        sample_user_cv: UserCV,
        sample_job_posting: JobPosting,
        sample_company_research: CompanyContext,
    ) -> None:
        """Test that prompt includes gap analysis when provided."""
        from careervp.logic.prompts.cv_tailor_prompt import build_tailor_prompt

        gap = {"missing_skills": ["Kubernetes"]}
        context = _aggregate_inputs(
            sample_user_cv, sample_job_posting, sample_company_research, gap
        )
        prompt = build_tailor_prompt(context, include_gap_analysis=True)

        assert "GAP ANALYSIS CONTEXT" in prompt
        assert "Kubernetes" in prompt
```

### Pytest Configuration

Ensure `pyproject.toml` or `pytest.ini` has:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

### Coverage Commands

```bash
# Run tests with coverage
uv run pytest tests/unit/test_cv_tailor.py -v \
    --cov=careervp.logic.cv_tailor \
    --cov=careervp.handlers.cv_tailor_handler \
    --cov=careervp.models.tailor \
    --cov-report=term-missing \
    --cov-fail-under=80

# Generate HTML coverage report
uv run pytest tests/unit/test_cv_tailor.py -v \
    --cov=careervp \
    --cov-report=html
```

### Test Categories

| Category | Test Count | Description |
| -------- | ---------- | ----------- |
| Models | 5 | Request/response validation, serialization |
| Logic | 8 | FVS validation, aggregation, tailoring flow |
| Handler | 5 | API endpoint behavior, error handling |
| Prompts | 3 | Prompt construction, anti-detection rules |

### Zero-Hallucination Checklist

- [ ] All fixtures use realistic but distinct test data
- [ ] FVS validation tests cover all three tiers (IMMUTABLE, VERIFIABLE, FLEXIBLE)
- [ ] Handler tests verify all HTTP status code mappings
- [ ] Mock LLM responses include metadata for token tracking
- [ ] Retry logic tests verify exponential backoff behavior

### Acceptance Criteria

- [ ] All tests pass: `uv run pytest tests/unit/test_cv_tailor.py -v`
- [ ] Coverage ≥80% for logic, handler, and models
- [ ] No flaky tests (deterministic mocking)
- [ ] Tests run in <30 seconds total
- [ ] All edge cases documented with test comments

---

### Verification & Compliance

1. Run `python src/backend/scripts/validate_naming.py --path infra --strict`
2. Run `uv run ruff format . && uv run ruff check --fix . && uv run mypy --strict .`
3. If any path or class signature is missing, report a **BLOCKING ISSUE** and exit.
