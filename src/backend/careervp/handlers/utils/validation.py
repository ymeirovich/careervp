"""Shared validation utilities for handlers."""

from __future__ import annotations

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_TEXT_LENGTH = 1_000_000


def validate_file_size(content: bytes) -> None:
    """Validate file size is within limit."""
    size = len(content)
    if size > MAX_FILE_SIZE:
        raise ValueError(f"File size {size} exceeds maximum {MAX_FILE_SIZE} bytes (10MB)")


def validate_text_length(text: str) -> None:
    """Validate text length is within limit."""
    length = len(text)
    if length > MAX_TEXT_LENGTH:
        raise ValueError(f"Text length {length} exceeds maximum {MAX_TEXT_LENGTH} characters")
