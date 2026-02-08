"""Tests for CV tailoring logic."""

from unittest.mock import Mock, AsyncMock

from careervp.logic.cv_tailoring import (
    tailor_cv,
    extract_job_requirements,
    calculate_relevance_scores,
    filter_cv_sections_by_relevance,
    build_tailoring_prompt,
    parse_llm_response,
    validate_tailored_output,
)
from careervp.models.result import Result, ResultCode
from careervp.models.cv_models import UserCV


def test_tailor_cv_success(
    sample_master_cv, sample_job_description, mock_dal_handler, mock_llm_client
):
    """Test successful CV tailoring with valid inputs."""
    # Arrange - fixtures provide setup

    # Act
    result = tailor_cv(
        master_cv=sample_master_cv,
        job_description=sample_job_description,
        dal=mock_dal_handler,
        llm_client=mock_llm_client,
    )

    # Assert
    assert result.success is True
    assert result.code == ResultCode.CV_TAILORED_SUCCESS
    assert result.data is not None
    assert result.data.tailored_cv.full_name == sample_master_cv.full_name
    assert len(result.data.changes_made) > 0
    assert result.data.average_relevance_score >= 0.0
    assert result.data.average_relevance_score <= 1.0


def test_tailor_cv_calculates_relevance_scores(
    sample_master_cv, sample_job_description, mock_dal_handler, mock_llm_client
):
    """Test CV tailoring calculates relevance scores for all sections."""
    # Arrange

    # Act
    result = tailor_cv(
        master_cv=sample_master_cv,
        job_description=sample_job_description,
        dal=mock_dal_handler,
        llm_client=mock_llm_client,
    )

    # Assert
    assert result.success is True
    assert "professional_summary" in result.data.relevance_scores
    assert "work_experience" in result.data.relevance_scores
    assert "skills" in result.data.relevance_scores
    assert all(0.0 <= score <= 1.0 for score in result.data.relevance_scores.values())


def test_extract_job_requirements(sample_job_description):
    """Test extracting requirements from job description."""
    # Act
    requirements = extract_job_requirements(sample_job_description)

    # Assert
    assert isinstance(requirements, dict)
    assert "required_skills" in requirements
    assert "preferred_skills" in requirements
    assert "responsibilities" in requirements
    assert len(requirements["required_skills"]) > 0


def test_extract_job_requirements_empty_description():
    """Test extracting requirements from empty description."""
    # Arrange
    job_description = ""

    # Act
    requirements = extract_job_requirements(job_description)

    # Assert
    assert requirements["required_skills"] == []
    assert requirements["preferred_skills"] == []


def test_filter_cv_sections_by_relevance(sample_master_cv, sample_relevance_scores):
    """Test filtering CV sections by relevance threshold."""
    # Arrange
    threshold = 0.75

    # Act
    filtered_cv = filter_cv_sections_by_relevance(
        cv=sample_master_cv,
        relevance_scores=sample_relevance_scores,
        threshold=threshold,
    )

    # Assert
    assert isinstance(filtered_cv, UserCV)
    # High relevance sections should be included
    assert filtered_cv.professional_summary is not None
    assert len(filtered_cv.skills) > 0
    # Low relevance sections might be filtered
    assert len(filtered_cv.work_experience) <= len(sample_master_cv.work_experience)


def test_tailor_cv_llm_timeout(
    sample_master_cv, sample_job_description, mock_dal_handler, mock_llm_timeout
):
    """Test CV tailoring handles LLM timeout gracefully."""
    # Arrange

    # Act
    result = tailor_cv(
        master_cv=sample_master_cv,
        job_description=sample_job_description,
        dal=mock_dal_handler,
        llm_client=mock_llm_timeout,
        timeout=300,
    )

    # Assert
    assert result.success is False
    assert result.code == ResultCode.LLM_TIMEOUT
    assert "timed out" in result.message.lower()


def test_tailor_cv_fvs_violation(
    sample_master_cv, sample_job_description, sample_fvs_baseline, mock_dal_handler
):
    """Test CV tailoring rejects output with FVS violations."""
    # Arrange
    mock_llm = Mock()
    # Convert WorkExperience objects to dicts for the LLM response
    work_exp_dicts = [exp.model_dump() for exp in sample_master_cv.work_experience]
    mock_llm.generate = AsyncMock(
        return_value={
            "full_name": sample_master_cv.full_name,
            "email": "wrong.email@example.com",  # CRITICAL violation
            "work_experience": work_exp_dicts,
        }
    )

    # Act
    result = tailor_cv(
        master_cv=sample_master_cv,
        job_description=sample_job_description,
        fvs_baseline=sample_fvs_baseline,
        dal=mock_dal_handler,
        llm_client=mock_llm,
    )

    # Assert
    assert result.success is False
    assert result.code == ResultCode.FVS_VIOLATION_DETECTED
    assert len(result.data.violations) > 0


def test_tailor_cv_returns_result_object(
    sample_master_cv, sample_job_description, mock_dal_handler, mock_llm_client
):
    """Test CV tailoring returns Result[T] pattern."""
    # Act
    result = tailor_cv(
        master_cv=sample_master_cv,
        job_description=sample_job_description,
        dal=mock_dal_handler,
        llm_client=mock_llm_client,
    )

    # Assert
    assert isinstance(result, Result)
    assert hasattr(result, "success")
    assert hasattr(result, "code")
    assert hasattr(result, "message")
    assert hasattr(result, "data")


def test_tailor_cv_with_preferences(
    sample_master_cv,
    sample_job_description,
    sample_tailoring_preferences,
    mock_dal_handler,
    mock_llm_client,
):
    """Test CV tailoring respects user preferences."""
    # Act
    result = tailor_cv(
        master_cv=sample_master_cv,
        job_description=sample_job_description,
        preferences=sample_tailoring_preferences,
        dal=mock_dal_handler,
        llm_client=mock_llm_client,
    )

    # Assert
    assert result.success is True
    # Verify preferences were applied
    assert any(
        "professional" in change.description.lower()
        for change in result.data.changes_made
    )


def test_tailor_cv_stores_artifact(
    sample_master_cv, sample_job_description, mock_dal_handler, mock_llm_client
):
    """Test CV tailoring stores artifact in DynamoDB."""
    # Act
    result = tailor_cv(
        master_cv=sample_master_cv,
        job_description=sample_job_description,
        dal=mock_dal_handler,
        llm_client=mock_llm_client,
    )

    # Assert
    assert result.success is True
    mock_dal_handler.save_tailored_cv_artifact.assert_called_once()


def test_calculate_relevance_scores(sample_master_cv, sample_job_description):
    """Test relevance score calculation."""
    # Act
    scores = calculate_relevance_scores(
        cv=sample_master_cv,
        job_description=sample_job_description,
    )

    # Assert
    assert isinstance(scores, dict)
    assert all(isinstance(score, float) for score in scores.values())
    assert all(0.0 <= score <= 1.0 for score in scores.values())


def test_calculate_relevance_scores_no_match():
    """Test relevance scores when CV has no match to job."""
    # Arrange
    cv = Mock(spec=UserCV)
    cv.skills = []
    cv.work_experience = []
    cv.professional_summary = ""
    cv.education = []
    cv.certifications = []
    job_description = "Looking for Rust developer with blockchain experience"

    # Act
    scores = calculate_relevance_scores(cv, job_description)

    # Assert
    assert all(score < 0.5 for score in scores.values())


def test_build_tailoring_prompt(
    sample_master_cv, sample_job_description, sample_relevance_scores
):
    """Test building LLM prompt for tailoring."""
    # Act
    prompt = build_tailoring_prompt(
        cv=sample_master_cv,
        job_description=sample_job_description,
        relevance_scores=sample_relevance_scores,
    )

    # Assert
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "job description" in prompt.lower()
    assert sample_master_cv.full_name in prompt


def test_build_prompt_includes_relevance_scores(
    sample_master_cv, sample_job_description, sample_relevance_scores
):
    """Test prompt includes relevance score annotations."""
    # Act
    prompt = build_tailoring_prompt(
        cv=sample_master_cv,
        job_description=sample_job_description,
        relevance_scores=sample_relevance_scores,
    )

    # Assert
    assert "relevance" in prompt.lower()
    # Check that scores are included
    for section, score in sample_relevance_scores.items():
        if score > 0.8:
            assert section.replace("_", " ") in prompt.lower()


def test_build_prompt_includes_fvs_rules(
    sample_master_cv, sample_job_description, sample_fvs_baseline
):
    """Test prompt includes FVS immutable facts."""
    # Act
    prompt = build_tailoring_prompt(
        cv=sample_master_cv,
        job_description=sample_job_description,
        fvs_baseline=sample_fvs_baseline,
    )

    # Assert
    assert "immutable" in prompt.lower() or "do not change" in prompt.lower()
    # Check critical facts mentioned
    assert sample_master_cv.email in prompt


def test_build_prompt_includes_target_keywords(
    sample_master_cv, sample_job_description, sample_keyword_list
):
    """Test prompt includes target keywords from job."""
    # Act
    prompt = build_tailoring_prompt(
        cv=sample_master_cv,
        job_description=sample_job_description,
        target_keywords=sample_keyword_list,
    )

    # Assert
    assert "keywords" in prompt.lower()
    assert any(keyword in prompt for keyword in sample_keyword_list)


def test_build_prompt_with_tone_preferences(
    sample_master_cv, sample_job_description, sample_tailoring_preferences
):
    """Test prompt includes tone preferences."""
    # Act
    prompt = build_tailoring_prompt(
        cv=sample_master_cv,
        job_description=sample_job_description,
        preferences=sample_tailoring_preferences,
    )

    # Assert
    assert sample_tailoring_preferences.tone in prompt.lower()


def test_parse_llm_response_success(sample_tailored_cv_response):
    """Test parsing valid LLM response."""
    # Arrange
    raw_response = {
        "professional_summary": sample_tailored_cv_response.tailored_cv.professional_summary,
        "work_experience": [
            exp.dict()
            for exp in sample_tailored_cv_response.tailored_cv.work_experience
        ],
        "changes_made": [
            change.dict() for change in sample_tailored_cv_response.changes_made
        ],
    }

    # Act
    result = parse_llm_response(raw_response)

    # Assert
    assert result.success is True
    assert result.data is not None


def test_parse_llm_response_invalid_json():
    """Test parsing invalid JSON response."""
    # Arrange
    raw_response = "not valid json"

    # Act
    result = parse_llm_response(raw_response)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.PARSE_ERROR


def test_validate_tailored_output_success(
    sample_master_cv, sample_tailored_cv_response, sample_fvs_baseline
):
    """Test validating tailored CV output."""
    # Act
    result = validate_tailored_output(
        original_cv=sample_master_cv,
        tailored_cv=sample_tailored_cv_response.tailored_cv,
        fvs_baseline=sample_fvs_baseline,
    )

    # Assert
    assert result.success is True
    assert result.code == ResultCode.VALIDATION_SUCCESS


def test_validate_tailored_output_missing_required_field(
    sample_master_cv, sample_tailored_cv_response
):
    """Test validation fails when required fields missing."""
    # Arrange
    invalid_cv = sample_tailored_cv_response.tailored_cv
    invalid_cv.email = None  # Remove required field

    # Act
    result = validate_tailored_output(
        original_cv=sample_master_cv,
        tailored_cv=invalid_cv,
    )

    # Assert
    assert result.success is False
    assert result.code == ResultCode.VALIDATION_MISSING_REQUIRED_FIELD


def test_tailor_cv_increments_counter(
    sample_master_cv, sample_job_description, mock_dal_handler, mock_llm_client
):
    """Test CV tailoring increments usage counter."""
    # Act
    result = tailor_cv(
        master_cv=sample_master_cv,
        job_description=sample_job_description,
        dal=mock_dal_handler,
        llm_client=mock_llm_client,
    )

    # Assert
    assert result.success is True
    mock_dal_handler.increment_tailoring_counter.assert_called_once_with(
        sample_master_cv.user_id
    )


def test_tailor_cv_rate_limit_check(
    sample_master_cv, sample_job_description, mock_llm_client
):
    """Test CV tailoring checks rate limit."""
    # Arrange
    mock_dal = Mock()
    mock_dal.check_rate_limit = AsyncMock(return_value=True)  # Rate limited

    # Act
    result = tailor_cv(
        master_cv=sample_master_cv,
        job_description=sample_job_description,
        dal=mock_dal,
        llm_client=mock_llm_client,
    )

    # Assert
    assert result.success is False
    assert result.code == ResultCode.RATE_LIMIT_EXCEEDED


def test_tailor_cv_empty_cv(
    sample_empty_cv, sample_job_description, mock_dal_handler, mock_llm_client
):
    """Test CV tailoring with empty CV."""
    # Act
    result = tailor_cv(
        master_cv=sample_empty_cv,
        job_description=sample_job_description,
        dal=mock_dal_handler,
        llm_client=mock_llm_client,
    )

    # Assert
    assert result.success is False
    assert result.code == ResultCode.INSUFFICIENT_CV_DATA


def test_tailor_cv_generates_keyword_matches(
    sample_master_cv, sample_job_description, mock_dal_handler, mock_llm_client
):
    """Test CV tailoring identifies keyword matches."""
    # Act
    result = tailor_cv(
        master_cv=sample_master_cv,
        job_description=sample_job_description,
        dal=mock_dal_handler,
        llm_client=mock_llm_client,
    )

    # Assert
    assert result.success is True
    assert len(result.data.keyword_matches) > 0
    assert all(isinstance(keyword, str) for keyword in result.data.keyword_matches)


def test_tailor_cv_estimates_ats_score(
    sample_master_cv, sample_job_description, mock_dal_handler, mock_llm_client
):
    """Test CV tailoring estimates ATS score."""
    # Act
    result = tailor_cv(
        master_cv=sample_master_cv,
        job_description=sample_job_description,
        dal=mock_dal_handler,
        llm_client=mock_llm_client,
    )

    # Assert
    assert result.success is True
    assert result.data.estimated_ats_score >= 0
    assert result.data.estimated_ats_score <= 100


def test_tailor_cv_generates_change_log(
    sample_master_cv, sample_job_description, mock_dal_handler, mock_llm_client
):
    """Test CV tailoring generates detailed change log."""
    # Act
    result = tailor_cv(
        master_cv=sample_master_cv,
        job_description=sample_job_description,
        dal=mock_dal_handler,
        llm_client=mock_llm_client,
    )

    # Assert
    assert result.success is True
    assert len(result.data.changes_made) > 0
    for change in result.data.changes_made:
        assert hasattr(change, "section")
        assert hasattr(change, "change_type")
        assert hasattr(change, "description")
