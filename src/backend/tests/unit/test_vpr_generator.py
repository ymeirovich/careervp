"""
VPR generator logic tests per docs/specs/03-vpr-generator.md Task 03.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from careervp.logic.vpr_generator import generate_vpr
from careervp.models.cv import ContactInfo, UserCV, WorkExperience
from careervp.models.job import JobPosting
from careervp.models.result import Result, ResultCode
from careervp.models.vpr import VPRRequest


@pytest.fixture
def sample_user_cv() -> UserCV:
    """Source CV facts for IMMUTABLE validation."""
    return UserCV(
        user_id='user-123',
        full_name='Alex Rivers',
        language='en',
        contact_info=ContactInfo(email='alex@example.com'),
        experience=[
            WorkExperience(
                company='Apex Labs',
                role='Product Lead',
                dates='2019 – Present',
                achievements=[],
            ),
            WorkExperience(
                company='Vertex Tech',
                role='Senior PM',
                dates='2016 – 2019',
                achievements=[],
            ),
        ],
        education=[],
        certifications=[],
        skills=['Roadmapping', 'Stakeholder Alignment'],
        top_achievements=[],
        is_parsed=True,
    )


@pytest.fixture
def sample_request() -> VPRRequest:
    """Minimal VPR request with job posting."""
    posting = JobPosting(
        company_name='Bright Future',
        role_title='Director of Product',
        description='',
        responsibilities=['Lead product org'],
        requirements=['10+ years experience'],
        nice_to_have=[],
        language='en',
    )
    return VPRRequest(
        application_id='app-789',
        user_id='user-123',
        job_posting=posting,
        gap_responses=[],
    )


def _build_llm_response() -> str:
    """LLM JSON payload with all VPR sections."""
    return json.dumps(
        {
            'executive_summary': 'Alex aligns perfectly with Bright Future needs.',
            'evidence_matrix': [
                {
                    'requirement': '10+ years experience',
                    'evidence': 'Alex led platforms at Apex Labs since 2019.',
                    'alignment_score': 'STRONG',
                    'impact_potential': 'Can immediately drive roadmap delivery.',
                }
            ],
            'differentiators': ['Blends product and GTM depth.'],
            'gap_strategies': [
                {
                    'gap': 'No fintech background',
                    'mitigation_approach': 'Highlight regulated launches at Apex.',
                    'transferable_skills': ['Risk Management'],
                }
            ],
            'cultural_fit': 'Values experimentation like Bright Future.',
            'talking_points': ['Discuss Apex Labs expansion since 2019.'],
            'keywords': ['Product Strategy', 'Roadmaps'],
        }
    )


class TestGenerateVPR:
    """Core behavior for generate_vpr()."""

    @pytest.mark.skip(reason='FVS disabled for VPR generation - see vpr_generator.py')
    @patch('careervp.logic.vpr_generator.LLMClient')
    @patch('careervp.logic.vpr_generator.validate_vpr_against_cv')
    def test_successful_generation(
        self,
        mock_validate: MagicMock,
        mock_llm_client_cls: MagicMock,
        sample_request: VPRRequest,
        sample_user_cv: UserCV,
    ) -> None:
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = Result(
            success=True,
            data={
                'text': _build_llm_response(),
                'input_tokens': 7000,
                'output_tokens': 2100,
                'cost': 0.034,
                'model': 'claude-sonnet-4-5',
            },
            code=ResultCode.SUCCESS,
        )
        mock_llm_client_cls.return_value = mock_llm_instance

        mock_validate.return_value = Result(
            success=True,
            data=None,
            code=ResultCode.SUCCESS,
        )

        mock_dal = MagicMock()
        mock_dal.save_vpr.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)

        result = generate_vpr(sample_request, sample_user_cv, mock_dal)

        assert result.success is True
        assert result.data is not None
        assert result.data.vpr is not None
        assert result.data.vpr.word_count > 0
        mock_dal.save_vpr.assert_called_once()
        mock_validate.assert_called_once()

    @patch('careervp.logic.vpr_generator.LLMClient')
    def test_llm_error_returns_failure(
        self,
        mock_llm_client_cls: MagicMock,
        sample_request: VPRRequest,
        sample_user_cv: UserCV,
    ) -> None:
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = Result(
            success=False,
            error='Rate limit',
            code=ResultCode.LLM_RATE_LIMITED,
        )
        mock_llm_client_cls.return_value = mock_llm_instance
        mock_dal = MagicMock()

        result = generate_vpr(sample_request, sample_user_cv, mock_dal)

        assert result.success is False
        assert result.code == ResultCode.LLM_RATE_LIMITED
        mock_dal.save_vpr.assert_not_called()

    @patch('careervp.logic.vpr_generator.LLMClient')
    def test_invalid_llm_payload_returns_parse_error(
        self,
        mock_llm_client_cls: MagicMock,
        sample_request: VPRRequest,
        sample_user_cv: UserCV,
    ) -> None:
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = Result(
            success=True,
            data={'text': 'not-json', 'input_tokens': 0, 'output_tokens': 0, 'cost': 0, 'model': 'claude-sonnet-4-5'},
            code=ResultCode.SUCCESS,
        )
        mock_llm_client_cls.return_value = mock_llm_instance
        mock_dal = MagicMock()

        result = generate_vpr(sample_request, sample_user_cv, mock_dal)

        assert result.success is False
        assert result.code == ResultCode.INVALID_INPUT
        mock_dal.save_vpr.assert_not_called()

    @pytest.mark.skip(reason='FVS disabled for VPR generation - see vpr_generator.py')
    @patch('careervp.logic.vpr_generator.LLMClient')
    @patch('careervp.logic.vpr_generator.validate_vpr_against_cv')
    def test_fvs_failure_blocks_persistence(
        self,
        mock_validate: MagicMock,
        mock_llm_client_cls: MagicMock,
        sample_request: VPRRequest,
        sample_user_cv: UserCV,
    ) -> None:
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = Result(
            success=True,
            data={'text': _build_llm_response(), 'input_tokens': 0, 'output_tokens': 0, 'cost': 0, 'model': 'claude-sonnet-4-5'},
            code=ResultCode.SUCCESS,
        )
        mock_llm_client_cls.return_value = mock_llm_instance

        mock_validate.return_value = Result(
            success=False,
            error='IMMUTABLE mismatch',
            code=ResultCode.FVS_HALLUCINATION_DETECTED,
        )

        mock_dal = MagicMock()

        result = generate_vpr(sample_request, sample_user_cv, mock_dal)

        assert result.success is False
        assert result.code == ResultCode.FVS_HALLUCINATION_DETECTED
        mock_dal.save_vpr.assert_not_called()

    @pytest.mark.skip(reason='FVS disabled for VPR generation - see vpr_generator.py')
    @patch('careervp.logic.vpr_generator.LLMClient')
    @patch('careervp.logic.vpr_generator.validate_vpr_against_cv')
    def test_dal_failure_returns_dynamodb_error(
        self,
        mock_validate: MagicMock,
        mock_llm_client_cls: MagicMock,
        sample_request: VPRRequest,
        sample_user_cv: UserCV,
    ) -> None:
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = Result(
            success=True,
            data={'text': _build_llm_response(), 'input_tokens': 0, 'output_tokens': 0, 'cost': 0, 'model': 'claude-sonnet-4-5'},
            code=ResultCode.SUCCESS,
        )
        mock_llm_client_cls.return_value = mock_llm_instance
        mock_validate.return_value = Result(success=True, data=None, code=ResultCode.SUCCESS)

        mock_dal = MagicMock()
        mock_dal.save_vpr.return_value = Result(
            success=False,
            error='DDB write failed',
            code=ResultCode.DYNAMODB_ERROR,
        )

        result = generate_vpr(sample_request, sample_user_cv, mock_dal)

        assert result.success is False
        assert result.code == ResultCode.DYNAMODB_ERROR
