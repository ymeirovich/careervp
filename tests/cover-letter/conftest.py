"""
Pytest fixtures for cover letter generation tests.

Provides reusable fixtures for unit, integration, and E2E tests.
"""

import pytest
from datetime import datetime
from typing import Dict, List
from unittest.mock import Mock, AsyncMock

# Note: These imports will fail until implementation exists (RED phase)
# from careervp.models.cover_letter_models import (
#     GenerateCoverLetterRequest,
#     CoverLetterPreferences,
#     TailoredCoverLetter,
#     TailoredCoverLetterResponse,
# )
# from careervp.models.result import Result, ResultCode


# ==================== REQUEST FIXTURES ====================


@pytest.fixture
def sample_cover_letter_request() -> Dict:
    """Valid cover letter generation request."""
    return {
        "cv_id": "cv_test_123",
        "job_id": "job_test_456",
        "company_name": "TechCorp",
        "job_title": "Senior Software Engineer",
        "preferences": {
            "tone": "professional",
            "word_count_target": 300,
            "emphasis_areas": ["leadership", "python", "aws"],
            "include_salary_expectations": False,
        },
    }


@pytest.fixture
def sample_cover_letter_preferences() -> Dict:
    """Sample cover letter preferences."""
    return {
        "tone": "professional",
        "word_count_target": 300,
        "emphasis_areas": ["leadership", "python"],
        "include_salary_expectations": False,
    }


@pytest.fixture
def sample_preferences_enthusiastic() -> Dict:
    """Enthusiastic tone preferences."""
    return {
        "tone": "enthusiastic",
        "word_count_target": 350,
        "emphasis_areas": ["passion", "innovation"],
        "include_salary_expectations": False,
    }


@pytest.fixture
def sample_preferences_technical() -> Dict:
    """Technical tone preferences."""
    return {
        "tone": "technical",
        "word_count_target": 400,
        "emphasis_areas": ["architecture", "systems", "scalability"],
        "include_salary_expectations": False,
    }


# ==================== CV FIXTURES ====================


@pytest.fixture
def sample_master_cv() -> Mock:
    """Complete UserCV mock with experience, skills, education."""
    cv = Mock()
    cv.cv_id = "cv_test_123"
    cv.user_id = "user_test_789"
    cv.skills = ["Python", "AWS", "Kubernetes", "PostgreSQL", "React"]
    cv.experience = [
        Mock(
            title="Senior Software Engineer",
            company="Previous Corp",
            start_date="2020-01",
            end_date="2024-01",
            highlights=[
                "Led team of 10 engineers to deliver critical project",
                "Reduced system latency by 50% through optimization",
                "Implemented CI/CD pipeline reducing deployment time by 80%",
            ],
        ),
        Mock(
            title="Software Engineer",
            company="Startup Inc",
            start_date="2018-01",
            end_date="2020-01",
            highlights=[
                "Built microservices architecture serving 1M+ users",
                "Designed and implemented RESTful APIs",
            ],
        ),
    ]
    cv.education = [
        Mock(
            degree="M.S. Computer Science",
            institution="Tech University",
            graduation_year=2018,
        ),
    ]
    cv.summary = "Experienced software engineer with 6+ years of experience in building scalable systems."
    return cv


@pytest.fixture
def sample_vpr() -> Mock:
    """Sample VPR (Value Proposition Report) with accomplishments."""
    vpr = Mock()
    vpr.cv_id = "cv_test_123"
    vpr.job_id = "job_test_456"
    vpr.accomplishments = [
        Mock(
            text="Led team of 10 engineers to deliver critical project on time",
            keywords=["led", "team", "engineers", "project"],
            relevance_score=0.95,
        ),
        Mock(
            text="Reduced system latency by 50% through optimization",
            keywords=["latency", "performance", "optimization"],
            relevance_score=0.88,
        ),
        Mock(
            text="Implemented CI/CD pipeline reducing deployment time by 80%",
            keywords=["ci/cd", "pipeline", "deployment", "automation"],
            relevance_score=0.82,
        ),
    ]
    vpr.job_requirements = [
        "Python expertise",
        "AWS experience",
        "Team leadership",
        "System design",
        "Agile methodology",
    ]
    vpr.skill_gaps = []
    vpr.recommendations = [
        "Emphasize leadership experience",
        "Highlight cloud expertise",
    ]
    return vpr


@pytest.fixture
def sample_tailored_cv() -> Mock:
    """Sample tailored CV."""
    cv = Mock()
    cv.cv_id = "cv_test_123"
    cv.job_id = "job_test_456"
    cv.tailored_summary = "Results-driven engineer with proven leadership experience..."
    cv.relevance_score = 0.85
    return cv


@pytest.fixture
def sample_gap_responses() -> List[Mock]:
    """Sample gap analysis responses."""
    return [
        Mock(
            question="Why are you interested in this role?",
            response="I am passionate about building scalable systems and leading engineering teams.",
        ),
        Mock(
            question="What experience do you have with cloud infrastructure?",
            response="I have 4+ years of AWS experience including EC2, Lambda, and EKS.",
        ),
    ]


# ==================== JOB FIXTURES ====================


@pytest.fixture
def sample_job_description() -> str:
    """Sample job posting text (500+ words)."""
    return """
    Senior Software Engineer - TechCorp

    About the Role:
    We are looking for a Senior Software Engineer to join our Platform team.
    You will be responsible for designing and implementing scalable backend services
    that power our core product offerings.

    Responsibilities:
    - Design and implement scalable microservices using Python and AWS
    - Lead technical initiatives and mentor junior engineers
    - Collaborate with product and design teams to deliver features
    - Participate in code reviews and maintain high code quality standards
    - Contribute to architectural decisions and technical roadmap

    Requirements:
    - 5+ years of software engineering experience
    - Strong Python programming skills
    - Experience with AWS services (EC2, Lambda, EKS, RDS)
    - Experience leading technical projects and mentoring others
    - Strong communication and collaboration skills
    - BS/MS in Computer Science or equivalent

    Nice to Have:
    - Experience with Kubernetes and container orchestration
    - Familiarity with CI/CD pipelines and DevOps practices
    - Experience with distributed systems at scale

    About TechCorp:
    TechCorp is a leading technology company building innovative solutions
    for enterprise customers. We value collaboration, innovation, and
    continuous learning. Join us to work on challenging problems and
    make a real impact.

    Benefits:
    - Competitive salary and equity
    - Health, dental, and vision insurance
    - Flexible work arrangements
    - Professional development budget
    - Generous PTO policy
    """


@pytest.fixture
def sample_company_name() -> str:
    """Sample company name."""
    return "TechCorp"


@pytest.fixture
def sample_job_title() -> str:
    """Sample job title."""
    return "Senior Software Engineer"


# ==================== COVER LETTER FIXTURES ====================


@pytest.fixture
def sample_generated_cover_letter_content() -> str:
    """Expected cover letter text from LLM."""
    return """I am excited to apply for the Senior Software Engineer position at TechCorp. With my proven experience leading engineering teams and delivering high-performance systems, I am confident I can contribute significantly to your Platform team.

In my current role at Previous Corp, I led a team of 10 engineers to deliver a critical project that reduced system latency by 50%. This experience has honed my leadership skills and deepened my expertise in Python and AWS—core technologies for this role.

Beyond technical execution, I am passionate about mentoring junior engineers and driving technical excellence. I implemented CI/CD pipelines that reduced deployment time by 80%, demonstrating my commitment to engineering best practices and continuous improvement.

I am particularly drawn to TechCorp's focus on building innovative solutions for enterprise customers. The opportunity to work on scalable microservices and contribute to architectural decisions aligns perfectly with my career goals and expertise.

I would welcome the opportunity to discuss how my background in system design, team leadership, and cloud infrastructure can benefit TechCorp. Thank you for considering my application."""


@pytest.fixture
def sample_tailored_cover_letter(sample_generated_cover_letter_content: str) -> Mock:
    """Sample TailoredCoverLetter object."""
    letter = Mock()
    letter.cover_letter_id = "cl_test_123_456_1704067200"
    letter.cv_id = "cv_test_123"
    letter.job_id = "job_test_456"
    letter.user_id = "user_test_789"
    letter.company_name = "TechCorp"
    letter.job_title = "Senior Software Engineer"
    letter.content = sample_generated_cover_letter_content
    letter.word_count = 285
    letter.personalization_score = 0.85
    letter.relevance_score = 0.82
    letter.tone_score = 0.88
    letter.generated_at = datetime(2024, 1, 1, 12, 0, 0)
    return letter


@pytest.fixture
def sample_quality_scores() -> Dict[str, float]:
    """Quality scoring breakdown."""
    return {
        "personalization": 0.85,
        "relevance": 0.82,
        "tone": 0.88,
        "overall": 0.85,  # 0.40*0.85 + 0.35*0.82 + 0.25*0.88
    }


# ==================== FVS FIXTURES ====================


@pytest.fixture
def sample_fvs_baseline() -> Mock:
    """Sample FVS baseline for validation."""
    baseline = Mock()
    baseline.company_name = "TechCorp"
    baseline.job_title = "Senior Software Engineer"
    baseline.company_variations = ["TechCorp", "TechCorp Inc.", "The TechCorp"]
    return baseline


@pytest.fixture
def sample_fvs_result_valid() -> Mock:
    """Valid FVS validation result."""
    result = Mock()
    result.is_valid = True
    result.has_critical_violations = False
    result.violations = []
    result.warnings = []
    return result


@pytest.fixture
def sample_fvs_result_invalid() -> Mock:
    """Invalid FVS validation result with violations."""
    violation = Mock()
    violation.field = "company_name"
    violation.expected = "TechCorp"
    violation.actual = "OtherCompany"
    violation.severity = "critical"
    violation.message = "Company name 'TechCorp' not found in cover letter"

    result = Mock()
    result.is_valid = False
    result.has_critical_violations = True
    result.violations = [violation]
    result.warnings = []
    return result


# ==================== MOCK FIXTURES ====================


@pytest.fixture
def mock_llm_client() -> Mock:
    """Mock LLMClient with generate() method."""
    client = Mock()
    client.generate = AsyncMock(
        return_value=Mock(
            content="I am excited to apply for the Senior Software Engineer position at TechCorp...",
            usage=Mock(input_tokens=5000, output_tokens=300),
        )
    )
    return client


@pytest.fixture
def mock_dal_handler() -> Mock:
    """Mock DynamoDalHandler with all methods."""
    dal = Mock()

    # CV retrieval
    dal.get_cv_by_id = AsyncMock(
        return_value=Mock(
            success=True,
            data=Mock(cv_id="cv_test_123", user_id="user_test_789"),
            code="SUCCESS",
        )
    )

    # VPR retrieval
    dal.get_vpr_artifact = AsyncMock(
        return_value=Mock(
            success=True,
            data=Mock(accomplishments=[], job_requirements=[]),
            code="SUCCESS",
        )
    )

    # Tailored CV retrieval
    dal.get_tailored_cv_artifact = AsyncMock(
        return_value=Mock(success=True, data=Mock(), code="SUCCESS")
    )

    # Gap responses
    dal.get_gap_responses = AsyncMock(
        return_value=Mock(success=True, data=[], code="SUCCESS")
    )

    # Save artifact
    dal.save_cover_letter_artifact = AsyncMock(
        return_value=Mock(success=True, data="cl_123", code="SUCCESS")
    )

    # Get artifact
    dal.get_cover_letter_artifact = AsyncMock(
        return_value=Mock(success=True, data=Mock(), code="SUCCESS")
    )

    return dal


@pytest.fixture
def mock_lambda_context() -> Mock:
    """Mock Lambda context."""
    context = Mock()
    context.function_name = "cover-letter-handler"
    context.memory_limit_in_mb = 2048
    context.invoked_function_arn = (
        "arn:aws:lambda:us-east-1:123456789:function:cover-letter"
    )
    context.aws_request_id = "test-request-id-12345"
    context.get_remaining_time_in_millis = Mock(return_value=290000)
    return context


# ==================== API GATEWAY FIXTURES ====================


@pytest.fixture
def sample_api_gateway_event(sample_cover_letter_request: Dict) -> Dict:
    """Sample API Gateway event."""
    import json

    return {
        "body": json.dumps(sample_cover_letter_request),
        "headers": {
            "Authorization": "Bearer mock_jwt_token",
            "Content-Type": "application/json",
        },
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "user_test_789",
                    "email": "test@example.com",
                }
            },
            "requestId": "test-request-id",
            "httpMethod": "POST",
            "path": "/api/cover-letter",
        },
        "httpMethod": "POST",
        "path": "/api/cover-letter",
    }


@pytest.fixture
def sample_api_gateway_event_no_auth(sample_cover_letter_request: Dict) -> Dict:
    """API Gateway event without authentication."""
    import json

    return {
        "body": json.dumps(sample_cover_letter_request),
        "headers": {"Content-Type": "application/json"},
        "requestContext": {},
        "httpMethod": "POST",
        "path": "/api/cover-letter",
    }


# ==================== VALIDATION FIXTURES ====================


@pytest.fixture
def valid_company_names() -> List[str]:
    """Valid company name examples."""
    return [
        "TechCorp",
        "Google",
        "Amazon Web Services",
        "Meta Platforms, Inc.",
        "StartUp.io",
    ]


@pytest.fixture
def invalid_company_names() -> List[str]:
    """Invalid company name examples."""
    return [
        "",  # Empty
        " ",  # Whitespace only
        "A" * 256,  # Too long
        "<script>alert('xss')</script>",  # XSS attempt
    ]


@pytest.fixture
def valid_job_titles() -> List[str]:
    """Valid job title examples."""
    return [
        "Software Engineer",
        "Senior Software Engineer",
        "Principal Engineer",
        "Engineering Manager",
        "VP of Engineering",
    ]


@pytest.fixture
def invalid_job_titles() -> List[str]:
    """Invalid job title examples."""
    return [
        "",  # Empty
        " ",  # Whitespace only
        "T" * 256,  # Too long
        "<script>alert('xss')</script>",  # XSS attempt
    ]


# ==================== PROMPT FIXTURES ====================


@pytest.fixture
def sample_personalization_context() -> Dict:
    """Sample personalization context for prompts."""
    return {
        "accomplishments": [
            {
                "text": "Led team of 10 engineers",
                "keywords": ["led", "team", "engineers"],
            },
            {
                "text": "Reduced latency by 50%",
                "keywords": ["latency", "performance"],
            },
        ],
        "job_requirements": ["Python", "AWS", "Leadership"],
        "skills": ["Python", "AWS", "Kubernetes"],
        "experience_highlights": [
            ["Led team of 10 engineers"],
            ["Built microservices architecture"],
        ],
        "gap_responses": [
            {
                "question": "Why this role?",
                "response": "Passion for building scalable systems",
            }
        ],
    }


# ==================== ERROR FIXTURES ====================


@pytest.fixture
def sample_cv_not_found_result() -> Mock:
    """CV not found result."""
    result = Mock()
    result.success = False
    result.error = "CV not found: cv_nonexistent"
    result.code = "CV_NOT_FOUND"
    result.data = None
    return result


@pytest.fixture
def sample_vpr_not_found_result() -> Mock:
    """VPR not found result."""
    result = Mock()
    result.success = False
    result.error = "VPR not found - generate VPR first"
    result.code = "VPR_NOT_FOUND"
    result.data = None
    return result


@pytest.fixture
def sample_timeout_result() -> Mock:
    """Timeout result."""
    result = Mock()
    result.success = False
    result.error = "Cover letter generation timed out after 300s"
    result.code = "CV_LETTER_GENERATION_TIMEOUT"
    result.data = None
    return result
