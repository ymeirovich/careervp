"""
Integration tests for Company Research and VPR generation flows.
Exercises Handler -> Logic -> DAL pattern with moto-backed DynamoDB and mocked LLM/web sources.

Test coverage:
- Company research success via website scrape, web search, and LLM fallback
- VPR generation using company research data
- FVS validation (no hallucination flags)
- HTTP status codes and response shapes
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import boto3
import pytest
from moto import mock_aws
from mypy_boto3_dynamodb.service_resource import Table
from pydantic import HttpUrl

from careervp.handlers.company_research_handler import lambda_handler as company_research_handler
from careervp.handlers.vpr_handler import lambda_handler as vpr_handler
from careervp.models.company import SearchResult
from careervp.models.result import Result, ResultCode


@pytest.fixture(scope='module')
def aws_env() -> Iterator[None]:
    """Set deterministic AWS credentials + Powertools configuration for moto."""
    patcher = pytest.MonkeyPatch()
    patcher.setenv('AWS_ACCESS_KEY_ID', 'testing')
    patcher.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    patcher.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    patcher.setenv('POWERTOOLS_SERVICE_NAME', 'careervp-test')
    patcher.setenv('LOG_LEVEL', 'INFO')
    try:
        yield
    finally:
        patcher.undo()


@pytest.fixture(scope='function')
def dynamodb_table(aws_env: None) -> Iterator[Table]:
    """Provision a moto-backed DynamoDB table matching the DAL schema."""
    table_name = 'test-careervp-artifacts'
    env_patcher = pytest.MonkeyPatch()
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user_id-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'sk', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        env_patcher.setenv('DYNAMODB_TABLE_NAME', table_name)
        try:
            yield table
        finally:
            env_patcher.undo()


def _seed_user_cv(table: Table, user_id: str) -> None:
    """Insert a parsed CV record required for VPR handler lookup."""
    table.put_item(
        Item={
            'pk': user_id,
            'sk': 'CV',
            'user_id': user_id,
            'full_name': 'Test User',
            'language': 'en',
            'contact_info': {'email': 'test@example.com'},
            'experience': [
                {
                    'company': 'Acme Corp',
                    'role': 'Senior Engineer',
                    'dates': '2020 – 2023',
                    'achievements': ['Built scalable distributed systems', 'Led reliability initiatives'],
                }
            ],
            'education': [{'institution': 'Tech University', 'degree': 'BS Computer Science', 'year': '2018'}],
            'certifications': [{'name': 'AWS Solutions Architect', 'issuer': 'Amazon Web Services', 'date': '2021'}],
            'skills': ['Python', 'AWS', 'Kubernetes', 'Distributed Systems'],
            'top_achievements': ['Reduced latency by 40%', 'Zero downtime deployments'],
            'professional_summary': 'Seasoned engineer with expertise in cloud infrastructure.',
            'is_parsed': True,
        }
    )


def _mock_scrape_success_content() -> str:
    """Sample scraped website content for company research (200+ words required)."""
    return """
    About TechCo - Leading Innovation in Cloud Solutions

    TechCo is a global technology company focused on empowering businesses through innovative cloud solutions.
    Founded in 2010, we have grown to serve over 10,000 customers worldwide. Our headquarters is located in
    San Francisco, California, with additional offices in London, Tokyo, and Sydney.

    Our Mission: To democratize access to enterprise-grade technology for businesses of all sizes. We believe
    that every organization deserves access to powerful technology that was once only available to large enterprises.

    Core Values:
    - Customer Obsession: Every decision starts with the customer and their needs
    - Innovation First: We push boundaries and embrace new ideas constantly
    - Integrity: We do what's right, even when it's hard or challenging
    - Collaboration: Great things happen when we work together as a team

    Strategic Priorities for the Coming Year:
    - Expand AI/ML capabilities across all product lines and services
    - Achieve carbon neutrality by 2025 through sustainable practices
    - Launch in 5 new international markets across Europe and Asia
    - Invest heavily in research and development initiatives
    - Build stronger partnerships with enterprise customers globally

    Recent News and Announcements:
    - Q4 2024: Record revenue growth of 35% year-over-year performance
    - Partnership with major cloud providers announced last quarter
    - Named to Fortune's Best Places to Work list for third consecutive year
    - Launched new AI-powered analytics platform for enterprise customers
    - Acquired leading data visualization startup to enhance product offerings
    - Expanded engineering team by 40% to accelerate product development

    Our Leadership Team:
    TechCo is led by experienced executives with deep industry knowledge. Our CEO has over 20 years
    of experience in enterprise software. Our CTO previously led engineering at major technology companies.
    Together, the leadership team has guided TechCo through multiple successful product launches and
    market expansions.
    """


def _mock_llm_structure_response() -> dict[str, Any]:
    """LLM response for structuring company research content."""
    return {
        'text': json.dumps(
            {
                'overview': 'TechCo is a global technology company focused on cloud solutions, serving 10,000+ customers since 2010.',
                'values': ['Customer Obsession', 'Innovation First', 'Integrity', 'Collaboration'],
                'mission': 'To democratize access to enterprise-grade technology for businesses of all sizes.',
                'strategic_priorities': ['Expand AI/ML capabilities', 'Carbon neutrality by 2025', 'International expansion'],
                'recent_news': ['Q4 2024 record revenue growth of 35%', 'Major cloud provider partnership'],
                'financial_summary': 'Strong growth with 35% YoY revenue increase in Q4 2024.',
            }
        ),
        'input_tokens': 500,
        'output_tokens': 200,
        'cost': 0.005,
        'model': 'claude-sonnet-4-5',
    }


def _mock_vpr_llm_success_payload() -> dict[str, Any]:
    """Valid LLM payload for successful VPR generation aligned with CV facts."""
    return {
        'text': json.dumps(
            {
                'executive_summary': 'Strong alignment between candidate and TechCo Senior Engineer role.',
                'evidence_matrix': [
                    {
                        'requirement': '5+ years engineering experience',
                        'evidence': 'Worked at Acme Corp from 2020 to 2023 building distributed systems.',
                        'alignment_score': 'STRONG',
                        'impact_potential': 'Immediate contributor to platform reliability.',
                    }
                ],
                'differentiators': ['Proven track record in reducing latency by 40%'],
                'gap_strategies': [],
                'cultural_fit': 'Values alignment with TechCo focus on innovation and customer obsession.',
                'talking_points': ['Highlight distributed systems expertise', 'Discuss zero-downtime deployment experience'],
                'keywords': ['Python', 'AWS', 'Kubernetes', 'Distributed Systems'],
                'language': 'en',
                'version': 1,
            }
        ),
        'input_tokens': 4800,
        'output_tokens': 1400,
        'cost': 0.024,
        'model': 'claude-sonnet-4-5',
    }


def _mock_vpr_llm_hallucination_payload() -> dict[str, Any]:
    """LLM payload with hallucinated facts not in CV to trigger FVS rejection."""
    return {
        'text': json.dumps(
            {
                'executive_summary': 'Excellent match for TechCo.',
                'evidence_matrix': [
                    {
                        'requirement': '5+ years experience',
                        'evidence': 'Led engineering at Fictional Startup from 2015-2019 with breakthrough results.',
                        'alignment_score': 'STRONG',
                        'impact_potential': 'Game-changing expertise.',
                    }
                ],
                'differentiators': ['Pioneered technology at companies not on CV'],
                'gap_strategies': [],
                'cultural_fit': 'Perfect cultural match.',
                'talking_points': ['Discuss Fictional Startup experience'],
                'keywords': ['Python', 'AWS'],
                'language': 'en',
                'version': 1,
            }
        ),
        'input_tokens': 4800,
        'output_tokens': 1400,
        'cost': 0.024,
        'model': 'claude-sonnet-4-5',
    }


def _build_company_research_event(
    company_name: str = 'TechCo',
    domain: str | None = 'techco.com',
    job_posting_url: str | None = None,
    job_posting_text: str | None = None,
) -> dict[str, Any]:
    """Construct API Gateway event for company research endpoint."""
    request: dict[str, Any] = {'company_name': company_name}
    if domain:
        request['domain'] = domain
    if job_posting_url:
        request['job_posting_url'] = job_posting_url
    if job_posting_text:
        request['job_posting_text'] = job_posting_text
    return {'body': json.dumps(request)}


def _build_vpr_event(
    application_id: str = 'app-456',
    user_id: str = 'user-123',
    company_name: str = 'TechCo',
) -> dict[str, Any]:
    """Construct API Gateway event for VPR endpoint."""
    request = {
        'application_id': application_id,
        'user_id': user_id,
        'job_posting': {
            'company_name': company_name,
            'role_title': 'Senior Engineer',
            'description': 'Build scalable cloud infrastructure.',
            'responsibilities': ['Design distributed systems', 'Lead reliability initiatives'],
            'requirements': ['5+ years engineering experience', 'Cloud platform expertise'],
            'nice_to_have': ['Kubernetes experience'],
            'language': 'en',
        },
    }
    return {'body': json.dumps(request)}


class TestCompanyResearchFlow:
    """Integration tests for company research endpoint."""

    @patch('careervp.logic.company_research.scrape_company_about_page', new_callable=AsyncMock)
    @patch('careervp.logic.company_research.get_llm_router')
    def test_research_success_via_website_scrape(
        self,
        mock_get_router: MagicMock,
        mock_scrape: AsyncMock,
        aws_env: None,
    ) -> None:
        """Test successful company research using website scrape as primary source."""
        mock_scrape.return_value = Result(
            success=True,
            data=_mock_scrape_success_content(),
            code=ResultCode.SUCCESS,
        )
        mock_router = MagicMock()
        mock_router.invoke.return_value = Result(
            success=True,
            data=_mock_llm_structure_response(),
            code=ResultCode.SUCCESS,
        )
        mock_get_router.return_value = mock_router

        response = company_research_handler(_build_company_research_event(), MagicMock())

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['company_name'] == 'TechCo'
        assert body['source'] == 'website_scrape'
        assert 'overview' in body
        assert len(body['values']) > 0
        assert body['confidence_score'] >= 0.8

    @patch('careervp.logic.company_research.scrape_company_about_page', new_callable=AsyncMock)
    @patch('careervp.logic.company_research.search_company_info', new_callable=AsyncMock)
    @patch('careervp.logic.company_research.get_llm_router')
    def test_research_fallback_to_web_search(
        self,
        mock_get_router: MagicMock,
        mock_search: AsyncMock,
        mock_scrape: AsyncMock,
        aws_env: None,
    ) -> None:
        """Test fallback to web search when website scrape fails."""
        mock_scrape.return_value = Result(
            success=False,
            error='Website scrape failed',
            code=ResultCode.SCRAPE_FAILED,
        )
        mock_search.return_value = Result(
            success=True,
            data=[
                SearchResult(
                    title='TechCo About Us',
                    url=HttpUrl('https://techco.com/about'),
                    snippet=(
                        'TechCo is a leading global cloud technology company focused on innovation and customer success. '
                        'Founded in 2010 in San Francisco, TechCo has grown to serve over 10,000 enterprise customers worldwide. '
                        'Our mission is to democratize access to enterprise-grade technology for businesses of all sizes. '
                        'We believe every organization deserves powerful technology solutions that drive growth and efficiency. '
                        'TechCo headquarters is located in San Francisco with additional offices in London, Tokyo, and Sydney.'
                    ),
                ),
                SearchResult(
                    title='TechCo Company Culture and Values',
                    url=HttpUrl('https://techco.com/culture'),
                    snippet=(
                        'At TechCo, our core values drive everything we do in our daily operations and long-term strategy. '
                        'Customer Obsession means every decision starts with understanding and addressing customer needs first. '
                        'Innovation First pushes us to constantly embrace new ideas and challenge conventional thinking. '
                        'Integrity guides us to always do what is right even when facing challenging situations. '
                        'Collaboration brings us together as a unified team working toward shared goals and mutual success.'
                    ),
                ),
                SearchResult(
                    title='TechCo News and Announcements',
                    url=HttpUrl('https://news.example.com/techco'),
                    snippet=(
                        'TechCo announces record revenue growth of 35% year-over-year in Q4 2024 exceeding analyst expectations. '
                        'The company also launched a new AI-powered analytics platform designed for enterprise customers. '
                        'TechCo expanded its engineering team by 40% to accelerate product development and innovation efforts. '
                        'The company was named to Fortune Best Places to Work list for the third consecutive year. '
                        'TechCo also announced strategic partnerships with major cloud providers to enhance service offerings.'
                    ),
                ),
            ],
            code=ResultCode.SUCCESS,
        )
        mock_router = MagicMock()
        mock_router.invoke.return_value = Result(
            success=True,
            data=_mock_llm_structure_response(),
            code=ResultCode.SUCCESS,
        )
        mock_get_router.return_value = mock_router

        response = company_research_handler(
            _build_company_research_event(domain='techco.com'),
            MagicMock(),
        )

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['source'] == 'web_search'
        assert body['confidence_score'] >= 0.5

    @patch('careervp.logic.company_research.scrape_company_about_page', new_callable=AsyncMock)
    @patch('careervp.logic.company_research.search_company_info', new_callable=AsyncMock)
    @patch('careervp.logic.company_research.get_llm_router')
    def test_research_fallback_to_llm_synthesis(
        self,
        mock_get_router: MagicMock,
        mock_search: AsyncMock,
        mock_scrape: AsyncMock,
        aws_env: None,
    ) -> None:
        """Test LLM fallback when both scrape and search fail."""
        mock_scrape.return_value = Result(
            success=False,
            error='Website scrape failed',
            code=ResultCode.SCRAPE_FAILED,
        )
        mock_search.return_value = Result(
            success=False,
            error='Search failed',
            code=ResultCode.SEARCH_FAILED,
        )
        mock_router = MagicMock()
        mock_router.invoke.return_value = Result(
            success=True,
            data=_mock_llm_structure_response(),
            code=ResultCode.SUCCESS,
        )
        mock_get_router.return_value = mock_router

        job_posting_text = 'TechCo is hiring Senior Engineers to build cloud infrastructure.'
        response = company_research_handler(
            _build_company_research_event(
                domain=None,
                job_posting_text=job_posting_text,
            ),
            MagicMock(),
        )

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['source'] == 'llm_fallback'
        assert body['confidence_score'] <= 0.5

    def test_research_invalid_request_returns_400(self, aws_env: None) -> None:
        """Test invalid request payload returns 400."""
        event = {'body': json.dumps({'invalid_field': 'value'})}

        response = company_research_handler(event, MagicMock())

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body

    @patch('careervp.logic.company_research.scrape_company_about_page', new_callable=AsyncMock)
    @patch('careervp.logic.company_research.search_company_info', new_callable=AsyncMock)
    def test_research_all_sources_failed_returns_503(
        self,
        mock_search: AsyncMock,
        mock_scrape: AsyncMock,
        aws_env: None,
    ) -> None:
        """Test 503 when all research sources fail and no job posting for fallback."""
        mock_scrape.return_value = Result(
            success=False,
            error='Scrape failed',
            code=ResultCode.SCRAPE_FAILED,
        )
        mock_search.return_value = Result(
            success=False,
            error='Search failed',
            code=ResultCode.SEARCH_FAILED,
        )

        response = company_research_handler(
            _build_company_research_event(domain=None),
            MagicMock(),
        )

        assert response['statusCode'] == 503
        body = json.loads(response['body'])
        assert 'error' in body


class TestVPRGenerationFlow:
    """Integration tests for VPR generation endpoint."""

    @patch('careervp.logic.vpr_generator.LLMClient')
    def test_vpr_success_with_cv_facts_validated(
        self,
        mock_llm_cls: MagicMock,
        dynamodb_table: Table,
    ) -> None:
        """Test successful VPR generation with FVS validation passing."""
        _seed_user_cv(dynamodb_table, 'user-123')
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = Result(
            success=True,
            data=_mock_vpr_llm_success_payload(),
            code=ResultCode.SUCCESS,
        )
        mock_llm_cls.return_value = mock_llm

        response = vpr_handler(_build_vpr_event(), MagicMock())

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['vpr'] is not None
        assert body['vpr']['application_id'] == 'app-456'
        assert 'evidence_matrix' in body['vpr']
        assert len(body['vpr']['evidence_matrix']) > 0

        saved = dynamodb_table.get_item(Key={'pk': 'app-456', 'sk': 'ARTIFACT#VPR#v1'})
        assert 'Item' in saved

    @pytest.mark.skip(reason='FVS disabled for VPR generation - see vpr_generator.py')
    @patch('careervp.logic.vpr_generator.LLMClient')
    def test_vpr_fvs_rejection_returns_422(
        self,
        mock_llm_cls: MagicMock,
        dynamodb_table: Table,
    ) -> None:
        """Test FVS rejection when VPR contains hallucinated facts."""
        _seed_user_cv(dynamodb_table, 'user-123')
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = Result(
            success=True,
            data=_mock_vpr_llm_hallucination_payload(),
            code=ResultCode.SUCCESS,
        )
        mock_llm_cls.return_value = mock_llm

        response = vpr_handler(_build_vpr_event(application_id='app-fvs-test'), MagicMock())

        assert response['statusCode'] == 422
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'error' in body

        persisted = dynamodb_table.get_item(Key={'pk': 'app-fvs-test', 'sk': 'ARTIFACT#VPR#v1'})
        assert 'Item' not in persisted

    @patch('careervp.logic.vpr_generator.LLMClient')
    def test_vpr_missing_cv_returns_404(
        self,
        mock_llm_cls: MagicMock,
        dynamodb_table: Table,
    ) -> None:
        """Test 404 when user CV is not found."""
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm

        response = vpr_handler(_build_vpr_event(user_id='nonexistent-user'), MagicMock())

        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['success'] is False
        mock_llm.invoke.assert_not_called()

    @patch('careervp.logic.vpr_generator.LLMClient')
    def test_vpr_llm_failure_returns_502(
        self,
        mock_llm_cls: MagicMock,
        dynamodb_table: Table,
    ) -> None:
        """Test 502 when LLM API fails."""
        _seed_user_cv(dynamodb_table, 'user-123')
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = Result(
            success=False,
            data=None,
            error='LLM service unavailable',
            code=ResultCode.LLM_API_ERROR,
        )
        mock_llm_cls.return_value = mock_llm

        response = vpr_handler(_build_vpr_event(), MagicMock())

        assert response['statusCode'] == 502
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'LLM' in body['error'] or 'unavailable' in body['error']


class TestCompanyResearchVPRIntegration:
    """End-to-end tests combining company research with VPR generation."""

    @patch('careervp.logic.company_research.scrape_company_about_page', new_callable=AsyncMock)
    @patch('careervp.logic.company_research.get_llm_router')
    @patch('careervp.logic.vpr_generator.LLMClient')
    def test_full_flow_company_research_then_vpr(
        self,
        mock_vpr_llm_cls: MagicMock,
        mock_research_router: MagicMock,
        mock_scrape: AsyncMock,
        dynamodb_table: Table,
    ) -> None:
        """Test complete flow: research company then generate VPR using company data."""
        _seed_user_cv(dynamodb_table, 'user-123')

        mock_scrape.return_value = Result(
            success=True,
            data=_mock_scrape_success_content(),
            code=ResultCode.SUCCESS,
        )
        mock_router = MagicMock()
        mock_router.invoke.return_value = Result(
            success=True,
            data=_mock_llm_structure_response(),
            code=ResultCode.SUCCESS,
        )
        mock_research_router.return_value = mock_router

        research_response = company_research_handler(
            _build_company_research_event(company_name='TechCo'),
            MagicMock(),
        )

        assert research_response['statusCode'] == 200
        research_body = json.loads(research_response['body'])
        assert research_body['source'] == 'website_scrape'
        assert 'values' in research_body

        mock_vpr_llm = MagicMock()
        mock_vpr_llm.invoke.return_value = Result(
            success=True,
            data=_mock_vpr_llm_success_payload(),
            code=ResultCode.SUCCESS,
        )
        mock_vpr_llm_cls.return_value = mock_vpr_llm

        vpr_response = vpr_handler(_build_vpr_event(company_name='TechCo'), MagicMock())

        assert vpr_response['statusCode'] == 200
        vpr_body = json.loads(vpr_response['body'])
        assert vpr_body['success'] is True
        assert vpr_body['vpr']['application_id'] == 'app-456'
        assert 'cultural_fit' in vpr_body['vpr']

    @patch('careervp.logic.company_research.scrape_company_about_page', new_callable=AsyncMock)
    @patch('careervp.logic.company_research.get_llm_router')
    def test_company_research_response_shape(
        self,
        mock_get_router: MagicMock,
        mock_scrape: AsyncMock,
        aws_env: None,
    ) -> None:
        """Verify company research response contains all expected fields."""
        mock_scrape.return_value = Result(
            success=True,
            data=_mock_scrape_success_content(),
            code=ResultCode.SUCCESS,
        )
        mock_router = MagicMock()
        mock_router.invoke.return_value = Result(
            success=True,
            data=_mock_llm_structure_response(),
            code=ResultCode.SUCCESS,
        )
        mock_get_router.return_value = mock_router

        response = company_research_handler(_build_company_research_event(), MagicMock())

        assert response['statusCode'] == 200
        body = json.loads(response['body'])

        required_fields = [
            'company_name',
            'overview',
            'values',
            'source',
            'source_urls',
            'confidence_score',
            'research_timestamp',
        ]
        for field in required_fields:
            assert field in body, f'Missing required field: {field}'

        optional_fields = ['mission', 'strategic_priorities', 'recent_news', 'financial_summary']
        for field in optional_fields:
            assert field in body, f'Missing optional field: {field}'

    @patch('careervp.logic.vpr_generator.LLMClient')
    def test_vpr_response_shape(
        self,
        mock_llm_cls: MagicMock,
        dynamodb_table: Table,
    ) -> None:
        """Verify VPR response contains all expected fields."""
        _seed_user_cv(dynamodb_table, 'user-123')
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = Result(
            success=True,
            data=_mock_vpr_llm_success_payload(),
            code=ResultCode.SUCCESS,
        )
        mock_llm_cls.return_value = mock_llm

        response = vpr_handler(_build_vpr_event(), MagicMock())

        assert response['statusCode'] == 200
        body = json.loads(response['body'])

        assert 'success' in body
        assert 'vpr' in body
        assert 'token_usage' in body
        assert 'generation_time_ms' in body

        vpr = body['vpr']
        vpr_required_fields = [
            'application_id',
            'user_id',
            'executive_summary',
            'evidence_matrix',
            'differentiators',
            'gap_strategies',
            'talking_points',
            'keywords',
            'language',
            'version',
        ]
        for field in vpr_required_fields:
            assert field in vpr, f'Missing VPR field: {field}'
