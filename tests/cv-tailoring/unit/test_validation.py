"""Tests for CV tailoring validation logic."""

from careervp.validation.cv_tailoring_validation import (
    validate_file_size,
    validate_text_length,
    validate_job_description,
    validate_cv_id,
    validate_tone,
    validate_target_length,
    validate_emphasis_areas,
)
from careervp.models.result import ResultCode


def test_validate_file_size_valid():
    """Test file size validation passes with 5MB file."""
    # Arrange
    file_size_bytes = 5 * 1024 * 1024  # 5MB

    # Act
    result = validate_file_size(file_size_bytes)

    # Assert
    assert result.success is True
    assert result.code == ResultCode.VALIDATION_SUCCESS


def test_validate_file_size_exceeds_limit():
    """Test file size validation fails with 15MB file."""
    # Arrange
    file_size_bytes = 15 * 1024 * 1024  # 15MB
    max_size = 10 * 1024 * 1024  # 10MB limit

    # Act
    result = validate_file_size(file_size_bytes, max_size=max_size)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.VALIDATION_FILE_SIZE_EXCEEDED
    assert "exceeds maximum" in result.message.lower()


def test_validate_file_size_exactly_at_limit():
    """Test file size validation at exact limit."""
    # Arrange
    file_size_bytes = 10 * 1024 * 1024  # Exactly 10MB
    max_size = 10 * 1024 * 1024

    # Act
    result = validate_file_size(file_size_bytes, max_size=max_size)

    # Assert
    assert result.success is True


def test_validate_text_length_valid():
    """Test text length validation passes with 5000 chars."""
    # Arrange
    text = "a" * 5000

    # Act
    result = validate_text_length(text, max_length=10000)

    # Assert
    assert result.success is True
    assert result.code == ResultCode.VALIDATION_SUCCESS


def test_validate_text_length_exceeds_limit():
    """Test text length validation fails with 2M chars."""
    # Arrange
    text = "a" * 2_000_000
    max_length = 1_000_000

    # Act
    result = validate_text_length(text, max_length=max_length)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.VALIDATION_TEXT_TOO_LONG


def test_validate_text_length_empty_string():
    """Test text length validation with empty string."""
    # Arrange
    text = ""

    # Act
    result = validate_text_length(text, min_length=1)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.VALIDATION_TEXT_TOO_SHORT


def test_validate_job_description_valid():
    """Test job description validation passes with 500 chars."""
    # Arrange
    job_description = "a" * 500

    # Act
    result = validate_job_description(job_description)

    # Assert
    assert result.success is True
    assert result.code == ResultCode.VALIDATION_SUCCESS


def test_validate_job_description_too_short():
    """Test job description validation fails with 30 chars."""
    # Arrange
    job_description = "Looking for a developer."  # ~24 chars

    # Act
    result = validate_job_description(job_description, min_length=100)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.VALIDATION_JOB_DESCRIPTION_TOO_SHORT


def test_validate_job_description_too_long():
    """Test job description validation fails with 60K chars."""
    # Arrange
    job_description = "a" * 60_000

    # Act
    result = validate_job_description(job_description, max_length=50_000)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.VALIDATION_JOB_DESCRIPTION_TOO_LONG


def test_validate_job_description_whitespace_only():
    """Test job description validation with only whitespace."""
    # Arrange
    job_description = "   \n\t   "

    # Act
    result = validate_job_description(job_description)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.VALIDATION_JOB_DESCRIPTION_EMPTY


def test_validate_cv_id_valid():
    """Test CV ID validation with valid format."""
    # Arrange
    cv_id = "cv_abc123def456"

    # Act
    result = validate_cv_id(cv_id)

    # Assert
    assert result.success is True
    assert result.code == ResultCode.VALIDATION_SUCCESS


def test_validate_cv_id_invalid_format():
    """Test CV ID validation with invalid format."""
    # Arrange
    cv_id = "invalid-format"

    # Act
    result = validate_cv_id(cv_id)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.VALIDATION_INVALID_CV_ID


def test_validate_cv_id_empty():
    """Test CV ID validation with empty string."""
    # Arrange
    cv_id = ""

    # Act
    result = validate_cv_id(cv_id)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.VALIDATION_INVALID_CV_ID


def test_validate_tone_valid():
    """Test tone validation with valid values."""
    # Arrange
    valid_tones = ["professional", "casual", "technical"]

    # Act & Assert
    for tone in valid_tones:
        result = validate_tone(tone)
        assert result.success is True


def test_validate_tone_invalid():
    """Test tone validation with invalid value."""
    # Arrange
    tone = "super_informal"

    # Act
    result = validate_tone(tone)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.VALIDATION_INVALID_TONE


def test_validate_target_length_valid():
    """Test target length validation with valid values."""
    # Arrange
    valid_lengths = ["one_page", "two_pages", "detailed"]

    # Act & Assert
    for length in valid_lengths:
        result = validate_target_length(length)
        assert result.success is True


def test_validate_target_length_invalid():
    """Test target length validation with invalid value."""
    # Arrange
    target_length = "three_pages"

    # Act
    result = validate_target_length(target_length)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.VALIDATION_INVALID_TARGET_LENGTH


def test_validate_emphasis_areas_valid():
    """Test emphasis areas validation with valid list."""
    # Arrange
    emphasis_areas = ["cloud", "python", "leadership"]

    # Act
    result = validate_emphasis_areas(emphasis_areas)

    # Assert
    assert result.success is True
    assert result.code == ResultCode.VALIDATION_SUCCESS


def test_validate_emphasis_areas_too_many():
    """Test emphasis areas validation with too many items."""
    # Arrange
    emphasis_areas = ["area1", "area2", "area3", "area4", "area5", "area6"]

    # Act
    result = validate_emphasis_areas(emphasis_areas, max_count=5)

    # Assert
    assert result.success is False
    assert result.code == ResultCode.VALIDATION_TOO_MANY_EMPHASIS_AREAS
