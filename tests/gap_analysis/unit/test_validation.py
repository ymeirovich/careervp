"""
Unit tests for validation utilities.
Tests for handlers/utils/validation.py (10MB file size limit, text length validation).

RED PHASE: These tests will FAIL until validation.py is implemented.
"""

import pytest

# This import will fail until the module is created
from careervp.handlers.utils.validation import (
    MAX_FILE_SIZE,
    MAX_TEXT_LENGTH,
    validate_file_size,
    validate_text_length,
)


class TestFileSizeValidation:
    """Test file size validation (10MB limit)."""

    def test_validate_file_size_under_limit(self):
        """Test that files under 10MB pass validation."""
        content = b"a" * (5 * 1024 * 1024)  # 5MB
        validate_file_size(content)  # Should not raise

    def test_validate_file_size_at_limit(self):
        """Test that files exactly at 10MB pass validation."""
        content = b"a" * MAX_FILE_SIZE  # Exactly 10MB
        validate_file_size(content)  # Should not raise

    def test_validate_file_size_over_limit(self):
        """Test that files over 10MB raise ValueError."""
        content = b"a" * (MAX_FILE_SIZE + 1)  # 10MB + 1 byte
        with pytest.raises(ValueError, match=r"exceeds maximum .* bytes \(10MB\)"):
            validate_file_size(content)

    def test_validate_file_size_significantly_over_limit(self):
        """Test that significantly large files raise ValueError."""
        content = b"a" * (50 * 1024 * 1024)  # 50MB
        with pytest.raises(ValueError, match=r"exceeds maximum"):
            validate_file_size(content)

    def test_validate_file_size_empty_file(self):
        """Test that empty files pass validation."""
        content = b""
        validate_file_size(content)  # Should not raise

    def test_max_file_size_constant(self):
        """Test that MAX_FILE_SIZE is exactly 10MB."""
        assert MAX_FILE_SIZE == 10 * 1024 * 1024
        assert MAX_FILE_SIZE == 10485760


class TestTextLengthValidation:
    """Test text length validation (1M characters limit)."""

    def test_validate_text_length_under_limit(self):
        """Test that text under 1M characters passes validation."""
        text = "a" * 500000  # 500k characters
        validate_text_length(text)  # Should not raise

    def test_validate_text_length_at_limit(self):
        """Test that text exactly at 1M characters passes validation."""
        text = "a" * MAX_TEXT_LENGTH
        validate_text_length(text)  # Should not raise

    def test_validate_text_length_over_limit(self):
        """Test that text over 1M characters raises ValueError."""
        text = "a" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError, match=r"exceeds maximum .* characters"):
            validate_text_length(text)

    def test_validate_text_length_empty_string(self):
        """Test that empty strings pass validation."""
        text = ""
        validate_text_length(text)  # Should not raise

    def test_validate_text_length_unicode(self):
        """Test validation with unicode characters."""
        text = "🎯" * 500000  # 500k emoji characters
        validate_text_length(text)  # Should not raise

    def test_max_text_length_constant(self):
        """Test that MAX_TEXT_LENGTH is exactly 1M."""
        assert MAX_TEXT_LENGTH == 1_000_000


class TestValidationErrorMessages:
    """Test that validation error messages are clear and actionable."""

    def test_file_size_error_includes_actual_size(self):
        """Test that file size errors include the actual size."""
        size = MAX_FILE_SIZE + 1000
        content = b"a" * size
        with pytest.raises(ValueError) as exc_info:
            validate_file_size(content)
        error_msg = str(exc_info.value)
        assert str(size) in error_msg or f"{size:,}" in error_msg

    def test_file_size_error_includes_limit(self):
        """Test that file size errors include the limit."""
        content = b"a" * (MAX_FILE_SIZE + 1)
        with pytest.raises(ValueError) as exc_info:
            validate_file_size(content)
        error_msg = str(exc_info.value)
        assert str(MAX_FILE_SIZE) in error_msg or "10MB" in error_msg

    def test_text_length_error_includes_actual_length(self):
        """Test that text length errors include the actual length."""
        length = MAX_TEXT_LENGTH + 1000
        text = "a" * length
        with pytest.raises(ValueError) as exc_info:
            validate_text_length(text)
        error_msg = str(exc_info.value)
        assert str(length) in error_msg or f"{length:,}" in error_msg

    def test_text_length_error_includes_limit(self):
        """Test that text length errors include the limit."""
        text = "a" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValueError) as exc_info:
            validate_text_length(text)
        error_msg = str(exc_info.value)
        assert str(MAX_TEXT_LENGTH) in error_msg or "1000000" in error_msg
