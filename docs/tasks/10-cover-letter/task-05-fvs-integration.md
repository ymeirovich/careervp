# Task 10.5: FVS Integration for Cover Letters

**Status:** Pending
**Spec Reference:** [docs/specs/cover-letter/COVER_LETTER_SPEC.md](../../specs/cover-letter/COVER_LETTER_SPEC.md)
**Depends On:** Task 10.8 (Models)
**Blocking:** Task 10.6 (Handler)
**Complexity:** Medium
**Duration:** 2 hours
**Test File:** `tests/cover-letter/unit/test_fvs_integration.py` (20-25 tests)

## Overview

Implement FVS (Fact Verification System) integration for cover letters. Cover letters have VERIFIABLE tier for company name and job title (must match exactly), and FLEXIBLE tier for all narrative content.

## Todo

### FVS Implementation

- [ ] Create or extend `src/backend/careervp/logic/fvs_cover_letter.py`
- [ ] Implement `create_fvs_baseline()` from job description
- [ ] Implement `validate_cover_letter()` with company/title matching
- [ ] Implement fuzzy matching for company name variations
- [ ] Add FVS violation classification (CRITICAL vs WARNING)

### Test Implementation

- [ ] Create `tests/cover-letter/unit/test_fvs_integration.py`
- [ ] Test company name exact match
- [ ] Test company name mismatch (CRITICAL violation)
- [ ] Test job title exact match
- [ ] Test job title mismatch (WARNING violation)
- [ ] Test fuzzy matching edge cases

---

## Codex Implementation Guide

### File Path

`src/backend/careervp/logic/fvs_cover_letter.py`

### FVS Tiers for Cover Letters

```python
"""
FVS tiers for cover letter validation:

IMMUTABLE (CRITICAL): None - cover letters are creative content
VERIFIABLE (WARNING): Company name, job title - must match job description
FLEXIBLE (ALLOWED): All narrative content, accomplishments, tone
"""

from enum import Enum

class FVSViolationSeverity(Enum):
    CRITICAL = "critical"  # Blocks generation
    WARNING = "warning"    # Logs but allows
    INFO = "info"          # Informational only
```

### Key Implementation

```python
"""
FVS validation for cover letters.

Validates:
- Company name (VERIFIABLE - must match)
- Job title (VERIFIABLE - must match)
"""

from dataclasses import dataclass
from typing import Optional
from difflib import SequenceMatcher

from aws_lambda_powertools import Logger

logger = Logger()


@dataclass
class FVSViolation:
    """Represents a single FVS violation."""
    field: str
    expected: str
    actual: str
    severity: str
    message: str


@dataclass
class FVSValidationResult:
    """Result of FVS validation."""
    is_valid: bool
    violations: list[FVSViolation]
    warnings: list[FVSViolation]

    @property
    def has_critical_violations(self) -> bool:
        return any(v.severity == "critical" for v in self.violations)


@dataclass
class FVSBaseline:
    """Baseline facts for FVS validation."""
    company_name: str
    job_title: str
    company_variations: list[str]  # Acceptable variations


def create_fvs_baseline(
    company_name: str,
    job_title: str,
) -> FVSBaseline:
    """Create FVS baseline from job details.

    Args:
        company_name: Official company name
        job_title: Official job title

    Returns:
        FVSBaseline with acceptable variations
    """
    # Generate acceptable company name variations
    variations = generate_company_variations(company_name)

    return FVSBaseline(
        company_name=company_name,
        job_title=job_title,
        company_variations=variations,
    )


def generate_company_variations(company_name: str) -> list[str]:
    """Generate acceptable variations of company name.

    Args:
        company_name: Original company name

    Returns:
        List of acceptable variations
    """
    variations = [company_name]

    # Add common variations
    name = company_name.lower()

    # Remove common suffixes
    suffixes = [" inc.", " inc", " llc", " ltd", " corp", " corporation", " co."]
    for suffix in suffixes:
        if name.endswith(suffix):
            base = company_name[:-len(suffix)]
            variations.append(base)
            break

    # Add "The" prefix variation
    if not name.startswith("the "):
        variations.append(f"The {company_name}")

    return variations


def validate_cover_letter(
    content: str,
    baseline: FVSBaseline,
    strict_mode: bool = False,
) -> FVSValidationResult:
    """Validate cover letter against FVS baseline.

    Args:
        content: Generated cover letter text
        baseline: FVS baseline with expected facts
        strict_mode: If True, warnings become critical

    Returns:
        FVSValidationResult with violations
    """
    violations = []
    warnings = []

    # Validate company name
    company_result = _validate_company_name(content, baseline)
    if company_result:
        if company_result.severity == "critical":
            violations.append(company_result)
        else:
            warnings.append(company_result)

    # Validate job title
    title_result = _validate_job_title(content, baseline)
    if title_result:
        if title_result.severity == "critical" or strict_mode:
            violations.append(title_result)
        else:
            warnings.append(title_result)

    is_valid = len(violations) == 0

    logger.info(
        "FVS validation complete",
        is_valid=is_valid,
        violations=len(violations),
        warnings=len(warnings),
    )

    return FVSValidationResult(
        is_valid=is_valid,
        violations=violations,
        warnings=warnings,
    )


def _validate_company_name(
    content: str,
    baseline: FVSBaseline,
) -> Optional[FVSViolation]:
    """Validate company name appears correctly in content."""
    content_lower = content.lower()

    # Check exact match first
    if baseline.company_name.lower() in content_lower:
        return None

    # Check variations
    for variation in baseline.company_variations:
        if variation.lower() in content_lower:
            return None

    # Check fuzzy match (>85% similarity)
    words = content.split()
    for i in range(len(words)):
        for j in range(i + 1, min(i + 5, len(words) + 1)):
            phrase = " ".join(words[i:j])
            similarity = SequenceMatcher(
                None,
                baseline.company_name.lower(),
                phrase.lower(),
            ).ratio()
            if similarity > 0.85:
                # Close match found - warning only
                return FVSViolation(
                    field="company_name",
                    expected=baseline.company_name,
                    actual=phrase,
                    severity="warning",
                    message=f"Company name similar but not exact: '{phrase}' vs '{baseline.company_name}'",
                )

    # No match found - critical violation
    return FVSViolation(
        field="company_name",
        expected=baseline.company_name,
        actual="[not found]",
        severity="critical",
        message=f"Company name '{baseline.company_name}' not found in cover letter",
    )


def _validate_job_title(
    content: str,
    baseline: FVSBaseline,
) -> Optional[FVSViolation]:
    """Validate job title appears correctly in content."""
    content_lower = content.lower()

    # Check exact match
    if baseline.job_title.lower() in content_lower:
        return None

    # Check without "Senior", "Junior", etc.
    title_core = _extract_title_core(baseline.job_title)
    if title_core.lower() in content_lower:
        return FVSViolation(
            field="job_title",
            expected=baseline.job_title,
            actual=title_core,
            severity="warning",
            message=f"Job title partially matched: '{title_core}' (expected '{baseline.job_title}')",
        )

    # No match found
    return FVSViolation(
        field="job_title",
        expected=baseline.job_title,
        actual="[not found]",
        severity="warning",  # Job title is WARNING, not CRITICAL
        message=f"Job title '{baseline.job_title}' not found in cover letter",
    )


def _extract_title_core(title: str) -> str:
    """Extract core job title without level prefixes."""
    prefixes = ["senior ", "junior ", "lead ", "principal ", "staff "]
    title_lower = title.lower()

    for prefix in prefixes:
        if title_lower.startswith(prefix):
            return title[len(prefix):]

    return title
```

---

## Test Implementation

### test_fvs_integration.py

```python
"""Unit tests for FVS cover letter validation."""

import pytest
from careervp.logic.fvs_cover_letter import (
    create_fvs_baseline,
    validate_cover_letter,
    generate_company_variations,
    FVSBaseline,
    FVSValidationResult,
)


class TestCreateFVSBaseline:
    """Tests for FVS baseline creation."""

    def test_create_baseline_basic(self):
        """Test basic baseline creation."""
        baseline = create_fvs_baseline(
            company_name="TechCorp",
            job_title="Senior Engineer",
        )

        assert baseline.company_name == "TechCorp"
        assert baseline.job_title == "Senior Engineer"

    def test_create_baseline_includes_variations(self):
        """Test baseline includes company name variations."""
        baseline = create_fvs_baseline(
            company_name="TechCorp Inc.",
            job_title="Engineer",
        )

        assert "TechCorp Inc." in baseline.company_variations
        assert "TechCorp" in baseline.company_variations

    def test_create_baseline_adds_the_prefix(self):
        """Test baseline adds 'The' prefix variation."""
        baseline = create_fvs_baseline(
            company_name="Company",
            job_title="Engineer",
        )

        assert "The Company" in baseline.company_variations


class TestGenerateCompanyVariations:
    """Tests for company name variation generation."""

    def test_variations_include_original(self):
        """Test variations include original name."""
        variations = generate_company_variations("TechCorp")
        assert "TechCorp" in variations

    def test_variations_remove_inc(self):
        """Test variations remove 'Inc.' suffix."""
        variations = generate_company_variations("TechCorp Inc.")
        assert "TechCorp" in variations

    def test_variations_remove_llc(self):
        """Test variations remove 'LLC' suffix."""
        variations = generate_company_variations("TechCorp LLC")
        assert "TechCorp" in variations

    def test_variations_remove_corp(self):
        """Test variations remove 'Corp' suffix."""
        variations = generate_company_variations("TechCorp Corp")
        assert "TechCorp" in variations


class TestValidateCoverLetter:
    """Tests for cover letter validation."""

    @pytest.fixture
    def baseline(self):
        """Create test baseline."""
        return create_fvs_baseline(
            company_name="TechCorp",
            job_title="Senior Engineer",
        )

    def test_validate_success_exact_match(self, baseline):
        """Test validation passes with exact matches."""
        content = "I am applying for the Senior Engineer position at TechCorp."

        result = validate_cover_letter(content, baseline)

        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_validate_company_name_mismatch(self, baseline):
        """Test validation fails when company name missing."""
        content = "I am applying for the Senior Engineer position at OtherCompany."

        result = validate_cover_letter(content, baseline)

        assert result.is_valid is False
        assert any(v.field == "company_name" for v in result.violations)

    def test_validate_company_name_variation(self, baseline):
        """Test validation accepts company name variations."""
        baseline = create_fvs_baseline("TechCorp Inc.", "Engineer")
        content = "I am applying for the Engineer position at TechCorp."

        result = validate_cover_letter(content, baseline)

        assert result.is_valid is True

    def test_validate_job_title_mismatch_is_warning(self, baseline):
        """Test job title mismatch is warning, not critical."""
        content = "I am applying for the Engineer position at TechCorp."

        result = validate_cover_letter(content, baseline)

        # Should pass (job title mismatch is warning)
        assert result.is_valid is True
        assert len(result.warnings) > 0

    def test_validate_job_title_partial_match(self, baseline):
        """Test partial job title match triggers warning."""
        content = "I am applying for the Engineer role at TechCorp."

        result = validate_cover_letter(content, baseline)

        assert result.is_valid is True
        assert any(v.field == "job_title" for v in result.warnings)

    def test_validate_strict_mode(self, baseline):
        """Test strict mode converts warnings to critical."""
        content = "I am applying for the Engineer position at TechCorp."

        result = validate_cover_letter(content, baseline, strict_mode=True)

        assert result.is_valid is False

    def test_validate_fuzzy_match_company(self, baseline):
        """Test fuzzy matching for similar company names."""
        content = "I am applying for the Senior Engineer position at Techcorp."

        result = validate_cover_letter(content, baseline)

        # Should pass with fuzzy match
        assert result.is_valid is True

    def test_validate_case_insensitive(self, baseline):
        """Test validation is case insensitive."""
        content = "I am applying for the SENIOR ENGINEER position at TECHCORP."

        result = validate_cover_letter(content, baseline)

        assert result.is_valid is True

    def test_validate_has_critical_violations_property(self, baseline):
        """Test has_critical_violations property."""
        content = "Generic cover letter without company."

        result = validate_cover_letter(content, baseline)

        assert result.has_critical_violations is True


class TestFVSValidationResult:
    """Tests for FVSValidationResult class."""

    def test_result_valid_no_violations(self):
        """Test result is valid when no violations."""
        result = FVSValidationResult(
            is_valid=True,
            violations=[],
            warnings=[],
        )

        assert result.is_valid is True
        assert result.has_critical_violations is False

    def test_result_invalid_with_violations(self):
        """Test result is invalid with violations."""
        from careervp.logic.fvs_cover_letter import FVSViolation

        result = FVSValidationResult(
            is_valid=False,
            violations=[
                FVSViolation(
                    field="company_name",
                    expected="TechCorp",
                    actual="Other",
                    severity="critical",
                    message="Mismatch",
                )
            ],
            warnings=[],
        )

        assert result.is_valid is False
        assert result.has_critical_violations is True
```

---

## Verification Commands

```bash
cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Format
uv run ruff format careervp/logic/fvs_cover_letter.py

# Lint
uv run ruff check --fix careervp/logic/fvs_cover_letter.py

# Type check
uv run mypy careervp/logic/fvs_cover_letter.py --strict

# Run tests
uv run pytest tests/cover-letter/unit/test_fvs_integration.py -v

# Expected: 24 tests PASSED
```

---

## Completion Criteria

- [ ] `create_fvs_baseline()` implemented
- [ ] `validate_cover_letter()` implemented
- [ ] Company name validation working (CRITICAL)
- [ ] Job title validation working (WARNING)
- [ ] Fuzzy matching working
- [ ] All 24 tests passing
- [ ] ruff format passes
- [ ] mypy --strict passes

---

## Common Pitfalls

### Pitfall 1: Case Sensitivity
**Problem:** Exact match fails due to case differences.
**Solution:** Always compare lowercase versions.

### Pitfall 2: Company Suffix Handling
**Problem:** "TechCorp Inc." doesn't match "TechCorp".
**Solution:** Generate variations without common suffixes.

---

## References

- [COVER_LETTER_DESIGN.md](../../architecture/COVER_LETTER_DESIGN.md) - FVS integration design
- [fvs_validator.py](../../../src/backend/careervp/logic/fvs_validator.py) - Pattern reference
