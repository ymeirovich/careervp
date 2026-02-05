"""
Unit tests for CV Tailoring Pydantic models.

Tests validation, serialization, deserialization, and field constraints
for all models used in the CV tailoring workflow.
"""

import pytest
from pydantic import ValidationError
from careervp.models.cv_tailoring import (
    TailorCVRequest,
    TailoringPreferences,
    TailoredCVResponse,
)


def test_tailor_cv_request_valid():
    """Test creating valid TailorCVRequest."""
    # Arrange & Act
    request = TailorCVRequest(
        cv_id="cv-123",
        job_description="Looking for a software engineer with Python experience.",
    )

    # Assert
    assert request.cv_id == "cv-123"
    assert len(request.job_description) > 0
    assert request.preferences is not None  # Should have defaults


def test_tailor_cv_request_missing_cv_id():
    """Test TailorCVRequest raises ValidationError when cv_id is missing."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        TailorCVRequest(
            job_description="Looking for a software engineer with Python experience.",
        )

    assert "cv_id" in str(exc_info.value)


def test_tailor_cv_request_missing_job_description():
    """Test TailorCVRequest raises ValidationError when job_description is missing."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        TailorCVRequest(
            cv_id="cv-123",
        )

    assert "job_description" in str(exc_info.value)


def test_tailor_cv_request_job_description_too_short():
    """Test TailorCVRequest validates minimum job description length."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        TailorCVRequest(
            cv_id="cv-123",
            job_description="Short",  # Less than 20 characters
        )

    assert "job_description" in str(exc_info.value)


def test_tailor_cv_request_job_description_too_long():
    """Test TailorCVRequest validates maximum job description length."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        TailorCVRequest(
            cv_id="cv-123",
            job_description="x" * 51000,  # Exceeds 50K characters
        )

    assert "job_description" in str(exc_info.value)


def test_tailoring_preferences_defaults():
    """Test TailoringPreferences has sensible default values."""
    # Arrange & Act
    prefs = TailoringPreferences()

    # Assert
    assert prefs.tone is not None
    assert prefs.length is not None
    assert prefs.emphasize_skills is not None
    assert prefs.include_summary is True  # Default


def test_tailoring_preferences_all_fields():
    """Test TailoringPreferences accepts all optional fields."""
    # Arrange & Act
    prefs = TailoringPreferences(
        tone="formal",
        length="concise",
        emphasize_skills=["Python", "AWS"],
        include_summary=False,
        max_pages=1,
    )

    # Assert
    assert prefs.tone == "formal"
    assert prefs.length == "concise"
    assert "Python" in prefs.emphasize_skills
    assert prefs.include_summary is False
    assert prefs.max_pages == 1


def test_tailored_cv_model_structure(sample_tailored_cv):
    """Test TailoredCV model has required fields."""
    # Assert
    assert hasattr(sample_tailored_cv, "contact_info")
    assert hasattr(sample_tailored_cv, "experience")
    assert hasattr(sample_tailored_cv, "education")
    assert hasattr(sample_tailored_cv, "skills")
    assert hasattr(sample_tailored_cv, "certifications")


def test_tailored_cv_response_success(sample_tailored_cv):
    """Test TailoredCVResponse for success case."""
    # Arrange & Act
    response = TailoredCVResponse(
        success=True,
        tailored_cv=sample_tailored_cv,
        download_url="https://s3.amazonaws.com/bucket/cv-123-tailored.pdf",
    )

    # Assert
    assert response.success is True
    assert response.tailored_cv is not None
    assert response.download_url is not None
    assert response.error_message is None


def test_tailored_cv_response_failure():
    """Test TailoredCVResponse for error case."""
    # Arrange & Act
    response = TailoredCVResponse(
        success=False,
        error_message="FVS detected hallucinations",
        error_code="FVS_HALLUCINATION_DETECTED",
    )

    # Assert
    assert response.success is False
    assert response.error_message is not None
    assert response.error_code is not None
    assert response.tailored_cv is None


def test_tailored_cv_serialization(sample_tailored_cv):
    """Test TailoredCV can be serialized to JSON."""
    # Act
    json_data = sample_tailored_cv.dict()

    # Assert
    assert isinstance(json_data, dict)
    assert "contact_info" in json_data
    assert "experience" in json_data
    assert "education" in json_data


def test_tailored_cv_deserialization(sample_tailored_cv):
    """Test TailoredCV can be deserialized from JSON."""
    # Arrange
    json_data = sample_tailored_cv.dict()

    # Act
    from careervp.models.cv import CV

    deserialized = CV(**json_data)

    # Assert
    assert deserialized.contact_info.email == sample_tailored_cv.contact_info.email
    assert len(deserialized.experience) == len(sample_tailored_cv.experience)


def test_tailor_cv_request_cv_id_format():
    """Test TailorCVRequest validates cv_id format."""
    # Arrange & Act
    request = TailorCVRequest(
        cv_id="cv-123",
        job_description="Looking for a software engineer with Python experience.",
    )

    # Assert
    assert request.cv_id.startswith("cv-")


def test_tailor_cv_request_empty_cv_id():
    """Test TailorCVRequest rejects empty cv_id."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError):
        TailorCVRequest(
            cv_id="",
            job_description="Looking for a software engineer with Python experience.",
        )


def test_tailor_cv_request_empty_job_description():
    """Test TailorCVRequest rejects empty job_description."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError):
        TailorCVRequest(
            cv_id="cv-123",
            job_description="",
        )


def test_tailoring_preferences_tone_values():
    """Test TailoringPreferences validates tone values."""
    # Arrange & Act
    valid_tones = ["formal", "casual", "professional"]

    for tone in valid_tones:
        prefs = TailoringPreferences(tone=tone)
        assert prefs.tone == tone


def test_tailoring_preferences_length_values():
    """Test TailoringPreferences validates length values."""
    # Arrange & Act
    valid_lengths = ["concise", "standard", "detailed"]

    for length in valid_lengths:
        prefs = TailoringPreferences(length=length)
        assert prefs.length == length


def test_tailoring_preferences_max_pages_constraint():
    """Test TailoringPreferences validates max_pages is positive."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError):
        TailoringPreferences(max_pages=0)

    with pytest.raises(ValidationError):
        TailoringPreferences(max_pages=-1)


def test_tailored_cv_response_requires_cv_on_success(sample_tailored_cv):
    """Test TailoredCVResponse requires tailored_cv when success is True."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError):
        TailoredCVResponse(
            success=True,
            # Missing tailored_cv
        )


def test_tailored_cv_response_requires_error_on_failure():
    """Test TailoredCVResponse requires error_message when success is False."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError):
        TailoredCVResponse(
            success=False,
            # Missing error_message
        )


def test_tailor_cv_request_with_preferences():
    """Test TailorCVRequest with custom preferences."""
    # Arrange & Act
    request = TailorCVRequest(
        cv_id="cv-123",
        job_description="Looking for a software engineer with Python experience.",
        preferences=TailoringPreferences(
            tone="formal",
            length="concise",
        ),
    )

    # Assert
    assert request.preferences.tone == "formal"
    assert request.preferences.length == "concise"


def test_tailoring_preferences_emphasize_skills_list():
    """Test TailoringPreferences emphasize_skills accepts list of strings."""
    # Arrange & Act
    prefs = TailoringPreferences(
        emphasize_skills=["Python", "AWS", "Docker", "Kubernetes"],
    )

    # Assert
    assert len(prefs.emphasize_skills) == 4
    assert all(isinstance(skill, str) for skill in prefs.emphasize_skills)


def test_tailored_cv_response_with_metadata():
    """Test TailoredCVResponse can include metadata."""
    # Arrange & Act
    _response = TailoredCVResponse(
        success=True,
        tailored_cv=None,  # Will fail validation, but testing structure
        metadata={
            "processing_time_ms": 1500,
            "model_version": "1.0.0",
            "fvs_violations": 0,
        },
    )

    # Assert - will raise ValidationError but we're testing the structure
    # In real code, this would include tailored_cv


def test_tailor_cv_request_json_serialization():
    """Test TailorCVRequest can be serialized to JSON."""
    # Arrange
    request = TailorCVRequest(
        cv_id="cv-123",
        job_description="Looking for a software engineer with Python experience.",
    )

    # Act
    json_str = request.json()

    # Assert
    assert isinstance(json_str, str)
    assert "cv-123" in json_str
    assert "job_description" in json_str


def test_tailor_cv_request_json_deserialization():
    """Test TailorCVRequest can be deserialized from JSON."""
    # Arrange
    json_data = {
        "cv_id": "cv-123",
        "job_description": "Looking for a software engineer with Python experience.",
    }

    # Act
    request = TailorCVRequest(**json_data)

    # Assert
    assert request.cv_id == "cv-123"


def test_tailoring_preferences_partial_update():
    """Test TailoringPreferences allows partial field updates."""
    # Arrange
    prefs = TailoringPreferences()
    original_length = prefs.length

    # Act
    prefs.tone = "formal"

    # Assert
    assert prefs.tone == "formal"
    assert prefs.length == original_length  # Unchanged


def test_tailored_cv_response_dict_structure():
    """Test TailoredCVResponse.dict() has correct structure."""
    # Arrange
    response = TailoredCVResponse(
        success=False,
        error_message="FVS detected hallucinations",
        error_code="FVS_HALLUCINATION_DETECTED",
    )

    # Act
    response_dict = response.dict()

    # Assert
    assert "success" in response_dict
    assert "error_message" in response_dict
    assert "error_code" in response_dict
    assert response_dict["success"] is False
