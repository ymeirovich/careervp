"""
Unit tests for validators module.
Per Phase 0: Security Foundation validation.
"""

from pydantic import BaseModel

from careervp.handlers.validators import (
    ALLOWED_CV_EXTENSIONS,
    CV_CONTENT_MAX_LENGTH,
    CV_CONTENT_MIN_LENGTH,
    MAX_CV_FILE_SIZE,
    MIN_CV_FILE_SIZE,
    ResultCode,
    _get_file_extension,
    validate_cv_upload,
    validate_request,
)

# =============================================================================
# Test Fixtures
# =============================================================================


class SampleSchema(BaseModel):
    """Sample Pydantic schema for testing."""

    name: str
    age: int


# =============================================================================
# Test validate_request
# =============================================================================


class TestValidateRequest:
    """Tests for validate_request function."""

    def test_valid_request_returns_success(self):
        """Valid request should return success Result."""
        body = {'name': 'John', 'age': 30}

        result = validate_request(body, SampleSchema)

        assert result.success is True
        assert result.code == ResultCode.VALIDATION_SUCCESS
        assert result.data == body

    def test_empty_body_returns_error(self):
        """Empty body should return validation error."""
        result = validate_request({}, SampleSchema)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_ERROR
        assert 'empty' in result.error.lower()

    def test_none_body_returns_error(self):
        """None body should return validation error."""
        result = validate_request(None, SampleSchema)  # type: ignore

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_ERROR

    def test_invalid_fields_returns_error(self):
        """Invalid fields should return validation error."""
        body = {'name': 'John', 'age': 'not-an-int'}

        result = validate_request(body, SampleSchema)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_ERROR

    def test_missing_required_field_returns_error(self):
        """Missing required field should return validation error."""
        body = {'name': 'John'}  # missing age

        result = validate_request(body, SampleSchema)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_ERROR


# =============================================================================
# Test validate_cv_upload
# =============================================================================


class TestValidateCvUpload:
    """Tests for validate_cv_upload function."""

    def test_valid_pdf_returns_success(self):
        """Valid PDF file should pass validation."""
        content = b'PDF content' * 100  # Ensure > 100 bytes

        result = validate_cv_upload('resume.pdf', content)

        assert result.success is True
        assert result.code == ResultCode.VALIDATION_SUCCESS

    def test_valid_docx_returns_success(self):
        """Valid DOCX file should pass validation."""
        content = b'DOCX content' * 100

        result = validate_cv_upload('resume.docx', content)

        assert result.success is True

    def test_valid_txt_returns_success(self):
        """Valid TXT file should pass validation."""
        content = b'Text content' * 100

        result = validate_cv_upload('resume.txt', content)

        assert result.success is True

    def test_unsupported_extension_returns_error(self):
        """Unsupported file extension should return error."""
        content = b'content' * 100

        result = validate_cv_upload('resume.exe', content)

        assert result.success is False
        assert result.code == ResultCode.UNSUPPORTED_FILE_FORMAT

    def test_empty_filename_returns_error(self):
        """Empty filename should return error."""
        content = b'content' * 100

        result = validate_cv_upload('', content)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_ERROR

    def test_none_filename_returns_error(self):
        """None filename should return error."""
        content = b'content' * 100

        result = validate_cv_upload(None, content)  # type: ignore

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_ERROR

    def test_file_too_small_returns_error(self):
        """File smaller than minimum should return error."""
        content = b'small'

        result = validate_cv_upload('resume.pdf', content)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_FILE_SIZE_EXCEEDED

    def test_file_too_large_returns_error(self):
        """File larger than maximum should return error."""
        # This test verifies the size validation logic
        # Using a size that exceeds the limit
        result = validate_cv_upload('resume.pdf', b'test', file_size=MAX_CV_FILE_SIZE + 1)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_FILE_SIZE_EXCEEDED

    def test_content_above_minimum_passes(self):
        """Content above minimum length should pass."""
        # MIN_CV_FILE_SIZE = 1024, CV_CONTENT_MIN_LENGTH = 100
        content = b'x' * 2000

        result = validate_cv_upload('resume.pdf', content)

        assert result.success is True

    def test_pdf_extension(self):
        """PDF extension should be allowed."""
        content = b'x' * 2000

        result = validate_cv_upload('resume.pdf', content)
        assert result.success is True

    def test_explicit_file_size_validation(self):
        """Should use explicit file_size parameter when provided."""
        content = b'content' * 100

        # Pass explicit size that violates limits
        result = validate_cv_upload('resume.pdf', content, file_size=100)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_FILE_SIZE_EXCEEDED


# =============================================================================
# Test _get_file_extension
# =============================================================================


class TestGetFileExtension:
    """Tests for _get_file_extension function."""

    def test_pdf_extension(self):
        """Should extract .pdf extension."""
        assert _get_file_extension('document.pdf') == '.pdf'

    def test_docx_extension(self):
        """Should extract .docx extension."""
        assert _get_file_extension('document.docx') == '.docx'

    def test_no_extension(self):
        """Should return empty string for no extension."""
        assert _get_file_extension('document') == ''

    def test_multiple_dots(self):
        """Should extract last extension."""
        assert _get_file_extension('document.backup.pdf') == '.pdf'

    def test_extension_case_preserved(self):
        """Should preserve case of extension."""
        assert _get_file_extension('document.PDF') == '.PDF'


# =============================================================================
# Test Constants
# =============================================================================


class TestConstants:
    """Tests for validator constants."""

    def test_allowed_extensions(self):
        """Verify allowed extensions include expected formats."""
        assert '.pdf' in ALLOWED_CV_EXTENSIONS
        assert '.docx' in ALLOWED_CV_EXTENSIONS
        assert '.doc' in ALLOWED_CV_EXTENSIONS
        assert '.txt' in ALLOWED_CV_EXTENSIONS

    def test_file_size_limits(self):
        """Verify file size limits are reasonable."""
        assert MIN_CV_FILE_SIZE > 0
        assert MAX_CV_FILE_SIZE > MIN_CV_FILE_SIZE
        assert MAX_CV_FILE_SIZE <= 10 * 1024 * 1024  # Max 10MB

    def test_content_length_limits(self):
        """Verify content length limits are reasonable."""
        assert CV_CONTENT_MIN_LENGTH > 0
        assert CV_CONTENT_MAX_LENGTH > CV_CONTENT_MIN_LENGTH
