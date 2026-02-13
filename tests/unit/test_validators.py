"""
Tests for validators module - SEC-002 Input Validation.

Per docs/refactor/specs/security_spec.yaml (SEC-002).
"""

from pydantic import BaseModel, Field

from careervp.handlers.validators import (
    validate_request,
    validate_cv_upload,
    _get_file_extension,
    ALLOWED_CV_EXTENSIONS,
    MAX_CV_FILE_SIZE,
    MIN_CV_FILE_SIZE,
    CV_CONTENT_MIN_LENGTH,
    CV_CONTENT_MAX_LENGTH,
)
from careervp.models.result import ResultCode


# Test schemas
class SimpleRequest(BaseModel):
    """Simple test request model."""

    name: str = Field(min_length=1)
    email: str
    age: int = Field(ge=0, le=150)


class ComplexRequest(BaseModel):
    """Complex test request model with optional fields."""

    title: str = Field(min_length=1, max_length=100)
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    count: int = Field(default=0, ge=0)


# ============================================================================
# Tests for validate_request
# ============================================================================


class TestValidateRequest:
    """Tests for validate_request function."""

    def test_valid_simple_request(self):
        """Test validation of a valid simple request."""
        body = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
        }
        result = validate_request(body, SimpleRequest)

        assert result.success is True
        assert result.code == ResultCode.VALIDATION_SUCCESS
        assert result.data is not None
        assert result.data["name"] == "John Doe"

    def test_valid_complex_request_with_defaults(self):
        """Test validation of complex request using default values."""
        body = {
            "title": "Test Title",
        }
        result = validate_request(body, ComplexRequest)

        assert result.success is True
        assert result.code == ResultCode.VALIDATION_SUCCESS
        assert result.data["count"] == 0
        assert result.data["tags"] == []

    def test_valid_complex_request_with_all_fields(self):
        """Test validation of complex request with all fields."""
        body = {
            "title": "Test",
            "description": "A test description",
            "tags": ["tag1", "tag2"],
            "count": 5,
        }
        result = validate_request(body, ComplexRequest)

        assert result.success is True
        assert result.data["description"] == "A test description"
        assert result.data["tags"] == ["tag1", "tag2"]

    def test_invalid_missing_required_field(self):
        """Test validation fails when required field is missing."""
        body = {"name": "John Doe"}  # Missing email and age
        result = validate_request(body, SimpleRequest)

        assert result.success is False
        assert result.error is not None
        assert result.code == ResultCode.VALIDATION_ERROR

    def test_invalid_field_type(self):
        """Test validation fails with wrong field type."""
        body = {
            "name": "John",
            "email": "john@example.com",
            "age": "thirty",  # Should be int
        }
        result = validate_request(body, SimpleRequest)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_ERROR

    def test_invalid_field_constraint(self):
        """Test validation fails when field violates constraints."""
        body = {
            "name": "",  # Violates min_length=1
            "email": "john@example.com",
            "age": 30,
        }
        result = validate_request(body, SimpleRequest)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_ERROR

    def test_invalid_out_of_range_value(self):
        """Test validation fails for out-of-range values."""
        body = {
            "name": "John",
            "email": "john@example.com",
            "age": 200,  # Exceeds max of 150
        }
        result = validate_request(body, SimpleRequest)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_ERROR

    def test_empty_body(self):
        """Test validation fails with empty body."""
        result = validate_request({}, SimpleRequest)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_ERROR
        assert "empty" in result.error.lower()

    def test_none_body(self):
        """Test validation fails with None body."""
        result = validate_request(None, SimpleRequest)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_ERROR

    def test_extra_fields_accepted(self):
        """Test that extra fields are accepted (forbid not enforced in validate_request)."""
        body = {
            "name": "John",
            "email": "john@example.com",
            "age": 30,
            "extra_field": "extra value",
        }
        result = validate_request(body, SimpleRequest)

        # Pydantic by default ignores extra fields unless strict validation is enabled
        assert result.success is True
        assert result.code == ResultCode.VALIDATION_SUCCESS


# ============================================================================
# Tests for validate_cv_upload
# ============================================================================


class TestValidateCVUpload:
    """Tests for validate_cv_upload function."""

    def test_valid_pdf_cv(self):
        """Test validation of valid PDF CV."""
        filename = "resume.pdf"
        content = b"PDF content" * 100  # Ensure sufficient content length
        result = validate_cv_upload(filename, content)

        assert result.success is True
        assert result.code == ResultCode.VALIDATION_SUCCESS

    def test_valid_docx_cv(self):
        """Test validation of valid DOCX CV."""
        filename = "resume.docx"
        content = b"DOCX content" * 100
        result = validate_cv_upload(filename, content)

        assert result.success is True

    def test_valid_doc_cv(self):
        """Test validation of valid DOC CV."""
        filename = "resume.doc"
        content = b"DOC content" * 100
        result = validate_cv_upload(filename, content)

        assert result.success is True

    def test_valid_txt_cv(self):
        """Test validation of valid TXT CV."""
        filename = "resume.txt"
        content = b"Text content" * 100
        result = validate_cv_upload(filename, content)

        assert result.success is True

    def test_invalid_extension(self):
        """Test validation fails for unsupported file type."""
        filename = "resume.exe"
        content = b"executable content" * 100
        result = validate_cv_upload(filename, content)

        assert result.success is False
        assert result.code == ResultCode.UNSUPPORTED_FILE_FORMAT

    def test_invalid_extension_html(self):
        """Test validation fails for HTML files."""
        filename = "resume.html"
        content = b"<html>" * 100
        result = validate_cv_upload(filename, content)

        assert result.success is False
        assert result.code == ResultCode.UNSUPPORTED_FILE_FORMAT

    def test_invalid_extension_image(self):
        """Test validation fails for image files."""
        filename = "resume.png"
        content = b"PNG binary" * 100
        result = validate_cv_upload(filename, content)

        assert result.success is False
        assert result.code == ResultCode.UNSUPPORTED_FILE_FORMAT

    def test_file_too_small(self):
        """Test validation fails for files smaller than minimum."""
        filename = "resume.pdf"
        content = b"too small"  # Less than MIN_CV_FILE_SIZE
        result = validate_cv_upload(filename, content)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_FILE_SIZE_EXCEEDED

    def test_file_too_large(self):
        """Test validation fails for files larger than maximum."""
        filename = "resume.pdf"
        # Create content larger than MAX_CV_FILE_SIZE
        content = b"x" * (MAX_CV_FILE_SIZE + 1)
        result = validate_cv_upload(filename, content)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_FILE_SIZE_EXCEEDED

    def test_file_at_min_size_boundary(self):
        """Test validation passes at minimum size boundary."""
        filename = "resume.pdf"
        content = b"x" * MIN_CV_FILE_SIZE
        result = validate_cv_upload(filename, content)

        assert result.success is True

    def test_file_at_max_size_boundary(self):
        """Test validation at boundary between file size and content limits."""
        filename = "resume.pdf"
        # Use content within both limits: < CV_CONTENT_MAX_LENGTH and < MAX_CV_FILE_SIZE
        content = b"x" * (CV_CONTENT_MAX_LENGTH - 1)
        result = validate_cv_upload(filename, content)

        assert result.success is True

    def test_empty_file_content(self):
        """Test validation fails for empty file content."""
        filename = "resume.pdf"
        content = b""
        result = validate_cv_upload(filename, content)

        # Empty content fails on size check first (0 bytes < 1KB minimum)
        assert result.success is False
        assert result.code == ResultCode.VALIDATION_FILE_SIZE_EXCEEDED

    def test_invalid_filename_none(self):
        """Test validation fails with None filename."""
        content = b"x" * 10000
        result = validate_cv_upload(None, content)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_ERROR

    def test_invalid_filename_empty_string(self):
        """Test validation fails with empty filename."""
        content = b"x" * 10000
        result = validate_cv_upload("", content)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_ERROR

    def test_case_insensitive_extension(self):
        """Test that file extension validation is case-insensitive."""
        filename = "resume.PDF"  # Uppercase
        content = b"PDF content" * 100
        result = validate_cv_upload(filename, content)

        assert result.success is True

    def test_explicit_file_size_parameter(self):
        """Test validation using explicit file_size parameter for size checks."""
        filename = "resume.pdf"
        # Content needs to meet CV_CONTENT_MIN_LENGTH requirement
        content = b"x" * CV_CONTENT_MIN_LENGTH
        explicit_size = 1000000  # 1MB - used for file size validation
        result = validate_cv_upload(filename, content, file_size=explicit_size)

        # Should validate file_size against limits (passes at 1MB)
        assert result.success is True

    def test_explicit_file_size_too_large(self):
        """Test validation fails when explicit file_size exceeds limit."""
        filename = "resume.pdf"
        content = b"actual content"
        explicit_size = MAX_CV_FILE_SIZE + 1
        result = validate_cv_upload(filename, content, file_size=explicit_size)

        assert result.success is False
        assert result.code == ResultCode.VALIDATION_FILE_SIZE_EXCEEDED

    def test_filename_with_spaces(self):
        """Test validation of filename with spaces."""
        filename = "my resume.pdf"
        content = b"PDF content" * 100
        result = validate_cv_upload(filename, content)

        assert result.success is True

    def test_filename_with_multiple_dots(self):
        """Test validation of filename with multiple dots."""
        filename = "my.resume.final.pdf"
        content = b"PDF content" * 100
        result = validate_cv_upload(filename, content)

        # Should validate based on last extension
        assert result.success is True

    def test_filename_no_extension(self):
        """Test validation fails for filename without extension."""
        filename = "resume"
        content = b"PDF content" * 100
        result = validate_cv_upload(filename, content)

        assert result.success is False
        assert result.code == ResultCode.UNSUPPORTED_FILE_FORMAT


# ============================================================================
# Tests for _get_file_extension
# ============================================================================


class TestGetFileExtension:
    """Tests for _get_file_extension helper function."""

    def test_simple_extension(self):
        """Test extraction of simple file extension."""
        ext = _get_file_extension("resume.pdf")
        assert ext == ".pdf"

    def test_uppercase_extension(self):
        """Test extraction of uppercase extension."""
        ext = _get_file_extension("resume.PDF")
        assert ext == ".PDF"

    def test_multiple_dots(self):
        """Test extraction with multiple dots in filename."""
        ext = _get_file_extension("my.resume.pdf")
        assert ext == ".pdf"

    def test_no_extension(self):
        """Test with filename having no extension."""
        ext = _get_file_extension("resume")
        assert ext == ""

    def test_hidden_file_with_extension(self):
        """Test extraction from hidden file with extension."""
        ext = _get_file_extension(".resume.pdf")
        assert ext == ".pdf"

    def test_hidden_file_with_dot(self):
        """Test extraction from hidden file returns the extension after last dot."""
        ext = _get_file_extension(".resume")
        # '.resume' has no extension in the traditional sense, 'resume' is the name
        # but our implementation returns the part after the last dot
        assert ext == ".resume"


# ============================================================================
# Integration Tests
# ============================================================================


class TestValidatorIntegration:
    """Integration tests combining multiple validators."""

    def test_request_and_file_validation_flow(self):
        """Test typical request + file upload validation flow."""
        # Validate request
        request_body = {
            "title": "Resume Upload",
            "description": "My professional resume",
        }
        request_result = validate_request(request_body, ComplexRequest)
        assert request_result.success is True

        # Validate file
        file_result = validate_cv_upload("resume.pdf", b"Content" * 500)
        assert file_result.success is True

    def test_all_allowed_extensions(self):
        """Test validation of all allowed CV extensions."""
        content = b"x" * 10000

        for ext in ALLOWED_CV_EXTENSIONS:
            filename = f"resume{ext}"
            result = validate_cv_upload(filename, content)
            assert result.success is True, f"Extension {ext} should be valid"
