"""Pytest fixtures for CV Tailoring tests."""

from datetime import datetime, UTC
from typing import Any, Dict, List
from unittest.mock import Mock, AsyncMock
import pytest

from careervp.models.cv_models import (
    UserCV,
    WorkExperience,
    Education,
    Skill,
    SkillLevel,
    Certification,
)
from careervp.models.cv_tailoring_models import (
    TailorCVRequest,
    TailoringPreferences,
    TailoredCVResponse,
    TailoredCV,
    ChangeLog,
)
from careervp.models.fvs_models import FVSBaseline, ImmutableFact


@pytest.fixture
def sample_master_cv() -> UserCV:
    """Complete UserCV with experience, skills, education."""
    return UserCV(
        cv_id="cv_123",
        user_id="user_456",
        full_name="John Doe",
        email="john.doe@example.com",
        phone="+1234567890",
        location="San Francisco, CA",
        professional_summary="Senior Software Engineer with 8 years of experience in full-stack development.",
        work_experience=[
            WorkExperience(
                company="TechCorp Inc",
                role="Senior Software Engineer",
                start_date="2020-01-15",
                end_date=None,
                current=True,
                description="Leading development of cloud-native microservices.",
                achievements=[
                    "Reduced API latency by 40%",
                    "Mentored 5 junior engineers",
                    "Implemented CI/CD pipeline",
                ],
                technologies=["Python", "AWS", "Docker", "Kubernetes"],
            ),
            WorkExperience(
                company="StartupXYZ",
                role="Software Engineer",
                start_date="2016-06-01",
                end_date="2019-12-31",
                current=False,
                description="Developed RESTful APIs and frontend features.",
                achievements=[
                    "Built payment processing system",
                    "Improved test coverage to 85%",
                ],
                technologies=["JavaScript", "React", "Node.js", "PostgreSQL"],
            ),
        ],
        education=[
            Education(
                institution="University of California",
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                start_date="2012-09-01",
                end_date="2016-05-31",
                gpa=3.8,
                honors=["Dean's List", "Summa Cum Laude"],
            )
        ],
        skills=[
            Skill(name="Python", level=SkillLevel.EXPERT, years_of_experience=8),
            Skill(name="AWS", level=SkillLevel.ADVANCED, years_of_experience=5),
            Skill(name="Docker", level=SkillLevel.ADVANCED, years_of_experience=4),
            Skill(name="React", level=SkillLevel.INTERMEDIATE, years_of_experience=3),
            Skill(
                name="PostgreSQL", level=SkillLevel.INTERMEDIATE, years_of_experience=4
            ),
        ],
        certifications=[
            Certification(
                name="AWS Certified Solutions Architect",
                issuing_organization="Amazon Web Services",
                issue_date="2021-03-15",
                expiry_date="2024-03-15",
                credential_id="AWS-SA-12345",
            )
        ],
        languages=["English (Native)", "Spanish (Professional)"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_job_description() -> str:
    """500-word job posting text."""
    return """
Senior Python Developer - Cloud Infrastructure

We are seeking an experienced Senior Python Developer to join our cloud infrastructure team.
The ideal candidate will have strong expertise in Python development, AWS cloud services,
and containerization technologies.

Key Responsibilities:
- Design and implement scalable microservices using Python and FastAPI
- Manage AWS infrastructure using Infrastructure as Code (Terraform, CDK)
- Build and maintain CI/CD pipelines for automated deployment
- Optimize application performance and reduce latency
- Mentor junior developers and conduct code reviews
- Collaborate with cross-functional teams to deliver features

Required Skills:
- 5+ years of professional Python development experience
- Strong knowledge of AWS services (Lambda, ECS, S3, DynamoDB)
- Experience with Docker and Kubernetes
- Proficiency in SQL and NoSQL databases (PostgreSQL, DynamoDB)
- Understanding of microservices architecture and RESTful APIs
- Experience with version control systems (Git)

Preferred Qualifications:
- AWS certifications (Solutions Architect, Developer)
- Experience with FastAPI or Flask frameworks
- Knowledge of monitoring tools (CloudWatch, DataDog)
- Familiarity with event-driven architectures
- Experience mentoring junior engineers

What We Offer:
- Competitive salary and equity package
- Remote-first work environment
- Professional development budget
- Health, dental, and vision insurance
- 401(k) matching

About Us:
We're a fast-growing startup building the next generation of cloud infrastructure tools.
Our team values innovation, collaboration, and continuous learning.
    """


@pytest.fixture
def sample_tailoring_preferences() -> TailoringPreferences:
    """TailoringPreferences with tone/length/emphasis."""
    return TailoringPreferences(
        tone="professional",
        target_length="one_page",
        emphasis_areas=["cloud_infrastructure", "python", "aws"],
        include_all_experience=False,
        keyword_density="medium",
    )


@pytest.fixture
def sample_fvs_baseline(sample_master_cv: UserCV) -> FVSBaseline:
    """FVS baseline dict with immutable_facts."""
    return FVSBaseline(
        cv_id=sample_master_cv.cv_id,
        user_id=sample_master_cv.user_id,
        immutable_facts=[
            ImmutableFact(
                fact_type="employment_date",
                value="2020-01-15",
                context="TechCorp Inc - Senior Software Engineer - start_date",
            ),
            ImmutableFact(
                fact_type="employment_date",
                value="2016-06-01",
                context="StartupXYZ - Software Engineer - start_date",
            ),
            ImmutableFact(
                fact_type="employment_date",
                value="2019-12-31",
                context="StartupXYZ - Software Engineer - end_date",
            ),
            ImmutableFact(
                fact_type="company_name",
                value="TechCorp Inc",
                context="Work experience",
            ),
            ImmutableFact(
                fact_type="company_name",
                value="StartupXYZ",
                context="Work experience",
            ),
            ImmutableFact(
                fact_type="job_title",
                value="Senior Software Engineer",
                context="TechCorp Inc",
            ),
            ImmutableFact(
                fact_type="job_title",
                value="Software Engineer",
                context="StartupXYZ",
            ),
            ImmutableFact(
                fact_type="email",
                value="john.doe@example.com",
                context="Contact information",
            ),
            ImmutableFact(
                fact_type="phone",
                value="+1234567890",
                context="Contact information",
            ),
            ImmutableFact(
                fact_type="degree",
                value="Bachelor of Science",
                context="University of California",
            ),
            ImmutableFact(
                fact_type="institution",
                value="University of California",
                context="Education",
            ),
        ],
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_llm_client() -> Mock:
    """Mock LLMClient with generate() method."""
    client = Mock()
    client.generate = AsyncMock(
        return_value={
            "professional_summary": "Senior Python Developer with 8 years of experience specializing in cloud infrastructure and AWS services.",
            "work_experience": [
                {
                    "company": "TechCorp Inc",
                    "role": "Senior Software Engineer",
                    "start_date": "2020-01-15",
                    "end_date": None,
                    "current": True,
                    "description": "Leading cloud-native microservices development with Python and AWS.",
                    "achievements": [
                        "Reduced API latency by 40% through optimization",
                        "Implemented comprehensive CI/CD pipeline",
                    ],
                    "technologies": ["Python", "AWS", "Docker", "Kubernetes"],
                }
            ],
            "skills": [
                {"name": "Python", "level": "EXPERT", "years_of_experience": 8},
                {"name": "AWS", "level": "ADVANCED", "years_of_experience": 5},
                {"name": "Docker", "level": "ADVANCED", "years_of_experience": 4},
            ],
            "changes_made": [
                "Reworded professional summary to emphasize cloud infrastructure",
                "Filtered work experience to most relevant role",
                "Prioritized Python, AWS, and Docker skills",
            ],
        }
    )
    return client


@pytest.fixture
def mock_dal_handler() -> Mock:
    """Mock DynamoDalHandler."""
    dal = Mock()
    dal.save_tailored_cv_artifact = AsyncMock(return_value=True)
    dal.get_tailored_cv_artifact = AsyncMock(return_value=None)
    dal.query_tailored_cvs_by_user = AsyncMock(return_value=[])
    dal.increment_tailoring_counter = AsyncMock(return_value=1)
    dal.check_rate_limit = AsyncMock(return_value=False)
    return dal


@pytest.fixture
def sample_tailored_cv_response(sample_master_cv: UserCV) -> TailoredCVResponse:
    """Expected tailored CV from LLM."""
    return TailoredCVResponse(
        tailored_cv=TailoredCV(
            cv_id=sample_master_cv.cv_id,
            user_id=sample_master_cv.user_id,
            job_description_hash="abc123def456",
            full_name=sample_master_cv.full_name,
            email=sample_master_cv.email,
            phone=sample_master_cv.phone,
            location=sample_master_cv.location,
            professional_summary="Senior Python Developer with 8 years of experience specializing in cloud infrastructure and AWS services.",
            work_experience=sample_master_cv.work_experience[:1],  # Filtered
            education=sample_master_cv.education,
            skills=sample_master_cv.skills[:3],  # Top 3 skills
            certifications=sample_master_cv.certifications,
            languages=sample_master_cv.languages,
            created_at=datetime.now(UTC),
        ),
        changes_made=[
            ChangeLog(
                section="professional_summary",
                change_type="reword",
                description="Emphasized cloud infrastructure and AWS expertise",
            ),
            ChangeLog(
                section="work_experience",
                change_type="filter",
                description="Included only most relevant role",
            ),
            ChangeLog(
                section="skills",
                change_type="prioritize",
                description="Moved Python, AWS, Docker to top",
            ),
        ],
        relevance_scores={
            "professional_summary": 0.95,
            "work_experience": 0.88,
            "skills": 0.92,
            "education": 0.70,
            "certifications": 0.85,
        },
        average_relevance_score=0.86,
        keyword_matches=["Python", "AWS", "Docker", "Kubernetes", "microservices"],
        estimated_ats_score=82,
    )


@pytest.fixture
def sample_relevance_scores() -> Dict[str, float]:
    """Dict of section relevance scores."""
    return {
        "professional_summary": 0.95,
        "work_experience": 0.88,
        "skills": 0.92,
        "education": 0.70,
        "certifications": 0.85,
        "languages": 0.60,
    }


@pytest.fixture
def sample_tailor_cv_request(
    sample_master_cv: UserCV,
    sample_job_description: str,
    sample_tailoring_preferences: TailoringPreferences,
) -> TailorCVRequest:
    """Valid TailorCVRequest for testing."""
    return TailorCVRequest(
        cv_id=sample_master_cv.cv_id,
        user_id=sample_master_cv.user_id,
        job_description=sample_job_description,
        preferences=sample_tailoring_preferences,
    )


@pytest.fixture
def sample_invalid_tailored_cv(sample_master_cv: UserCV) -> Dict[str, Any]:
    """Tailored CV with FVS violations."""
    return {
        "full_name": sample_master_cv.full_name,
        "email": "wrong.email@example.com",  # CRITICAL: Email changed
        "phone": sample_master_cv.phone,
        "location": sample_master_cv.location,
        "professional_summary": "Updated summary",
        "work_experience": [
            {
                "company": "TechCorp Inc",
                "role": "Senior Software Engineer",
                "start_date": "2021-01-15",  # CRITICAL: Date changed
                "end_date": None,
                "current": True,
                "description": "Updated description",
                "achievements": ["New achievement"],
                "technologies": ["Python", "Go"],  # WARNING: Added Go
            }
        ],
        "skills": [
            {"name": "Python", "level": "EXPERT", "years_of_experience": 8},
            {
                "name": "Rust",
                "level": "ADVANCED",
                "years_of_experience": 5,
            },  # WARNING: Not in source
        ],
    }


@pytest.fixture
def sample_job_description_short() -> str:
    """Job description that's too short (<100 chars)."""
    return "Looking for a Python developer."


@pytest.fixture
def sample_job_description_long() -> str:
    """Job description that's too long (>50000 chars)."""
    return "Job description. " * 3000  # ~51000 chars


@pytest.fixture
def mock_llm_timeout() -> Mock:
    """Mock LLM client that times out."""
    client = Mock()
    client.generate = AsyncMock(
        side_effect=TimeoutError("LLM request timed out after 300s")
    )
    return client


@pytest.fixture
def mock_llm_rate_limit() -> Mock:
    """Mock LLM client that hits rate limit."""
    client = Mock()
    client.generate = AsyncMock(side_effect=Exception("Rate limit exceeded"))
    return client


@pytest.fixture
def sample_keyword_list() -> List[str]:
    """Extracted keywords from job description."""
    return [
        "Python",
        "AWS",
        "Docker",
        "Kubernetes",
        "microservices",
        "FastAPI",
        "CI/CD",
        "PostgreSQL",
        "DynamoDB",
        "mentoring",
    ]


@pytest.fixture
def sample_empty_cv() -> UserCV:
    """Minimal UserCV with no experience."""
    return UserCV(
        cv_id="cv_empty",
        user_id="user_empty",
        full_name="Jane Smith",
        email="jane@example.com",
        phone="+9876543210",
        location="New York, NY",
        professional_summary="Entry-level developer seeking opportunities.",
        work_experience=[],
        education=[],
        skills=[],
        certifications=[],
        languages=["English"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
