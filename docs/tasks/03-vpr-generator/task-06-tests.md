# Task 06: VPR Unit Tests

**Status:** Complete
**Spec Reference:** [[docs/specs/03-vpr-generator.md]]
**Depends On:** Task 02-05 (All implementation tasks)

## Overview

Write comprehensive unit tests for VPR generator using moto for AWS mocking and unittest.mock for LLM mocking. Tests cover all Result paths and FVS validation scenarios.

## Todo

### Test File Structure

- [ ] Create `src/backend/tests/unit/test_vpr_generator.py` (logic tests).
- [ ] Create `src/backend/tests/unit/test_vpr_handler.py` (handler tests).
- [ ] Create `src/backend/tests/unit/test_vpr_prompt.py` (prompt builder tests).
- [ ] Add VPR DAL tests to existing `test_dynamo_dal_handler.py`.

### Test Fixtures

- [ ] Create `tests/fixtures/sample_vpr_request.json`.
- [ ] Create `tests/fixtures/sample_vpr_llm_response.json`.
- [ ] Create `tests/fixtures/sample_vpr_output.json`.

### VPR Generator Tests (test_vpr_generator.py)

- [ ] Test successful VPR generation (mocked LLM).
- [ ] Test FVS validation failure (hallucinated date).
- [ ] Test FVS validation failure (hallucinated company).
- [ ] Test LLM API error handling.
- [ ] Test LLM timeout handling.
- [ ] Test word count calculation.
- [ ] Test token usage tracking.

### VPR Handler Tests (test_vpr_handler.py)

- [ ] Test successful VPR generation (200 response).
- [ ] Test missing CV (404 response).
- [ ] Test invalid request body (400 response).
- [ ] Test FVS validation failure (422 response).
- [ ] Test LLM error (502 response).
- [ ] Test metrics emission.

### VPR Prompt Tests (test_vpr_prompt.py)

- [ ] Test prompt placeholder substitution.
- [ ] Test CV serialization excludes raw_text.
- [ ] Test banned words detection.
- [ ] Test empty gap_responses handling.

### Validation

- [ ] Run `uv run ruff format src/backend/tests/unit/test_vpr*.py`.
- [ ] Run `uv run ruff check --fix src/backend/tests/unit/test_vpr*.py`.
- [ ] Run `uv run pytest tests/unit/test_vpr*.py -v` (all pass).

### Commit

- [ ] Commit with message: `test(vpr): add comprehensive VPR unit tests`.

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/tests/unit/test_vpr_generator.py` | Logic layer tests |
| `src/backend/tests/unit/test_vpr_handler.py` | Handler tests with moto |
| `src/backend/tests/unit/test_vpr_prompt.py` | Prompt builder tests |
| `src/backend/tests/fixtures/` | JSON fixtures |

### Key Test Patterns

```python
"""
VPR Generator Unit Tests.
Per docs/specs/03-vpr-generator.md Success Criteria.

Uses moto for DynamoDB mocking and unittest.mock for LLM.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from moto import mock_aws

from careervp.logic.vpr_generator import generate_vpr
from careervp.models.cv import UserCV
from careervp.models.result import ResultCode
from careervp.models.vpr import VPRRequest


@pytest.fixture
def sample_user_cv() -> UserCV:
    """
    Sample CV with IMMUTABLE facts for FVS validation.

    FVS_COMMENT: These dates/titles/companies are the source of truth.
    """
    return UserCV(
        user_id='user-123',
        full_name='John Doe',
        email='john@example.com',
        experiences=[
            {
                'company_name': 'Acme Corp',  # FVS IMMUTABLE
                'job_title': 'Senior Developer',  # FVS IMMUTABLE
                'start_date': '2020-01',  # FVS IMMUTABLE
                'end_date': '2023-06',  # FVS IMMUTABLE
                'achievements': ['Led team of 5', 'Reduced costs by 30%'],
            }
        ],
        skills=['Python', 'AWS', 'Leadership'],
        language='en',
    )


@pytest.fixture
def sample_vpr_request() -> VPRRequest:
    """Sample VPR request with job posting."""
    return VPRRequest(
        application_id='app-456',
        user_id='user-123',
        job_posting={
            'company_name': 'TechStart Inc',
            'role_title': 'Engineering Manager',
            'requirements': ['5+ years experience', 'Team leadership'],
            'language': 'en',
        },
    )


@pytest.fixture
def mock_llm_response() -> str:
    """
    Mock LLM response with valid VPR structure.

    FVS_COMMENT: Evidence references CV facts by matching dates/companies.
    """
    return json.dumps({
        'executive_summary': 'John brings 3+ years at Acme Corp...',
        'evidence_matrix': [
            {
                'requirement': '5+ years experience',
                'evidence': 'Senior Developer at Acme Corp (2020-01 to 2023-06)',
                'alignment_score': 'MODERATE',
                'impact_potential': 'Proven technical leadership',
            }
        ],
        'differentiators': ['Cost reduction expertise', 'Team leadership'],
        'gap_strategies': [],
        'talking_points': ['Discuss 30% cost reduction achievement'],
        'keywords': ['Python', 'AWS', 'Leadership'],
    })


class TestVPRGenerator:
    """Tests for VPR generation logic."""

    @mock_aws
    @patch('careervp.logic.vpr_generator.LLMClient')
    def test_successful_vpr_generation(
        self,
        mock_llm_class: MagicMock,
        sample_user_cv: UserCV,
        sample_vpr_request: VPRRequest,
        mock_llm_response: str,
    ) -> None:
        """Test successful VPR generation with mocked LLM."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            success=True,
            data=MagicMock(
                content=mock_llm_response,
                input_tokens=7500,
                output_tokens=2200,
                cost_usd=0.035,
                model='claude-sonnet-4-5-20250929',
            ),
        )
        mock_llm_class.return_value = mock_llm

        mock_dal = MagicMock()
        mock_dal.get_cv.return_value = sample_user_cv

        # Act
        result = generate_vpr(sample_vpr_request, sample_user_cv, mock_dal)

        # Assert
        assert result.success is True
        assert result.code == ResultCode.VPR_GENERATED
        assert result.data is not None
        assert result.data.vpr is not None
        assert result.data.vpr.application_id == 'app-456'
        assert len(result.data.vpr.evidence_matrix) > 0
        mock_dal.save_vpr.assert_called_once()

    @mock_aws
    @patch('careervp.logic.vpr_generator.LLMClient')
    def test_fvs_validation_blocks_hallucinated_date(
        self,
        mock_llm_class: MagicMock,
        sample_user_cv: UserCV,
        sample_vpr_request: VPRRequest,
    ) -> None:
        """
        Test FVS blocks VPR with fabricated dates.

        FVS_COMMENT: Date 2019-01 does not exist in sample_user_cv.
        """
        # Arrange - LLM returns hallucinated date
        hallucinated_response = json.dumps({
            'executive_summary': 'John has been at Acme since 2019...',
            'evidence_matrix': [
                {
                    'requirement': '5+ years experience',
                    'evidence': 'Senior Developer at Acme Corp (2019-01 to 2023-06)',  # WRONG DATE
                    'alignment_score': 'STRONG',
                    'impact_potential': 'Extended tenure',
                }
            ],
            'differentiators': [],
            'gap_strategies': [],
            'talking_points': [],
            'keywords': [],
        })

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            success=True,
            data=MagicMock(content=hallucinated_response),
        )
        mock_llm_class.return_value = mock_llm

        mock_dal = MagicMock()

        # Act
        result = generate_vpr(sample_vpr_request, sample_user_cv, mock_dal)

        # Assert
        assert result.success is False
        assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
        mock_dal.save_vpr.assert_not_called()

    @mock_aws
    @patch('careervp.logic.vpr_generator.LLMClient')
    def test_llm_api_error_handling(
        self,
        mock_llm_class: MagicMock,
        sample_user_cv: UserCV,
        sample_vpr_request: VPRRequest,
    ) -> None:
        """Test graceful handling of LLM API errors."""
        # Arrange
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            success=False,
            error='Rate limit exceeded',
            code=ResultCode.LLM_RATE_LIMITED,
        )
        mock_llm_class.return_value = mock_llm

        mock_dal = MagicMock()

        # Act
        result = generate_vpr(sample_vpr_request, sample_user_cv, mock_dal)

        # Assert
        assert result.success is False
        assert result.code == ResultCode.LLM_API_ERROR
        assert 'Rate limit' in (result.error or '')
```

### Result Pattern Enforcement in Tests

All tests verify `Result` object fields:

```python
# Always check both success flag AND code
assert result.success is True
assert result.code == ResultCode.VPR_GENERATED

# For errors, verify error message is present
assert result.success is False
assert result.error is not None
assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
```

### Pytest Commands

```bash
# Run all VPR tests
cd src/backend && uv run pytest tests/unit/test_vpr*.py -v

# Run with coverage
cd src/backend && uv run pytest tests/unit/test_vpr*.py -v --cov=careervp --cov-report=term-missing

# Run specific test class
cd src/backend && uv run pytest tests/unit/test_vpr_generator.py::TestVPRGenerator -v

# Run FVS-related tests only
cd src/backend && uv run pytest tests/unit/ -k "fvs or hallucin" -v
```

### Zero-Hallucination Checklist for Tests

- [ ] Test fixtures include explicit `# FVS_COMMENT:` marking source of truth.
- [ ] Hallucination test cases use WRONG dates/companies to verify FVS catches them.
- [ ] Mock LLM responses that pass FVS use dates EXACTLY matching fixture CV.
- [ ] No test accidentally validates hallucinated data as correct.

### Coverage Requirements

| Module | Target Coverage |
| ------ | --------------- |
| `vpr_generator.py` | 90%+ |
| `vpr_handler.py` | 85%+ |
| `vpr_prompt.py` | 95%+ |

### Acceptance Criteria

- [ ] All tests pass: `uv run pytest tests/unit/test_vpr*.py -v`
- [ ] Coverage meets targets (checked via `--cov`).
- [ ] FVS validation tests explicitly verify hallucination detection.
- [ ] No real API calls in any test (all mocked).
- [ ] All mypy --strict checks pass on test files.
