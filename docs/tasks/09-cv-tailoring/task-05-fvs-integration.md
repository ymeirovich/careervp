# Task 9.5: CV Tailoring - FVS Integration

**Status:** Pending
**Spec Reference:** [docs/specs/04-cv-tailoring.md](../../specs/04-cv-tailoring.md)
**Depends On:** Task 9.1 (Validation), Task 9.3 (Tailoring Logic)
**Blocking:** Task 9.6 (Handler)

## Overview

Integrate existing FVS (Fact-Value-Sentiment) validator from Phase 6 with CV tailoring logic to validate tailored CVs against IMMUTABLE, VERIFIABLE, and FLEXIBLE tier rules. This prevents hallucinations and ensures factual accuracy throughout the tailoring process.

## Todo

### FVS Integration Implementation

- [ ] Create `src/backend/careervp/logic/fvs_tailor_integration.py`
- [ ] Implement `create_fvs_baseline()` from source CV
- [ ] Implement `validate_tailored_cv()` against baseline
- [ ] Implement `compare_immutable_facts()` for preservation check
- [ ] Implement `verify_skills_exist()` for VERIFIABLE tier
- [ ] Implement `validate_flexible_content()` for reframing check
- [ ] Implement detailed error reporting with FVS violations

### Test Implementation

- [ ] Create `tests/logic/test_fvs_integration.py`
- [ ] Implement 20-25 test cases covering all validation scenarios
- [ ] Test baseline creation (3 tests)
- [ ] Test immutable fact comparison (5 tests)
- [ ] Test skill verification (4 tests)
- [ ] Test flexible content validation (4 tests)
- [ ] Test integrated validation flow (5 tests)
- [ ] Test error reporting (3 tests)

### Validation & Formatting

- [ ] Run `uv run ruff format src/backend/careervp/logic/`
- [ ] Run `uv run ruff check --fix src/backend/careervp/logic/`
- [ ] Run `uv run mypy src/backend/careervp/logic/ --strict`
- [ ] Run `uv run pytest tests/logic/test_fvs_integration.py -v`

### Commit

- [ ] Commit with message: `feat(fvs): integrate FVS validator with CV tailoring for hallucination prevention`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `src/backend/careervp/logic/fvs_tailor_integration.py` | FVS integration functions |
| `tests/logic/test_fvs_integration.py` | FVS integration tests |
| `src/backend/careervp/logic/fvs_validator.py` | Existing FVS validator (reference) |

### Key Implementation Details

```python
"""
FVS Integration for CV Tailoring.
Per docs/specs/04-cv-tailoring.md.

Validates tailored CVs against FVS (Fact-Value-Sentiment) rules:

FVS Tier Classification:
- IMMUTABLE: Facts that cannot be altered (dates, titles, names)
  Rule: Must be preserved exactly from source CV
  Validation: Byte-for-byte comparison
  
- VERIFIABLE: Facts that must exist in source (skills, certifications)
  Rule: Can be reordered or highlighted but must originate in source
  Validation: Existence check against source
  
- FLEXIBLE: Content that can be reframed (summaries, descriptions)
  Rule: Can be rewritten but must not introduce hallucinated facts
  Validation: Semantic similarity + no new skills/certs

Uses existing FVS validator from Phase 6 as foundation.
All functions return Result[T] for error handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from careervp.logic.fvs_validator import FVSValidator  # Existing Phase 6 validator
from careervp.handlers.utils.observability import logger, tracer
from careervp.models.result import Result, ResultCode

if TYPE_CHECKING:
    from careervp.models.cv import UserCV
    from careervp.models.tailor import TailoredCV


@dataclass
class FVSBaseline:
    """Baseline facts extracted from source CV for validation."""

    immutable_facts: dict  # Dates, titles, company names, etc.
    verifiable_facts: dict  # Skills, certifications, technologies
    flexible_sections: dict  # Summaries, descriptions that can be reframed
    cv_version: int
    extraction_timestamp: str


@dataclass
class FVSViolation:
    """Single FVS validation violation."""

    tier: str  # "IMMUTABLE", "VERIFIABLE", "FLEXIBLE"
    field: str  # Field name (e.g., "company_name", "skill")
    rule: str  # Rule violated (e.g., "must be preserved exactly")
    issue: str  # What went wrong
    source_value: str | None = None
    actual_value: str | None = None
    severity: str = "ERROR"  # "ERROR" or "WARNING"


@tracer.capture_method(capture_response=False)
def create_fvs_baseline(user_cv: UserCV) -> Result[FVSBaseline]:
    """
    Extract baseline facts from source CV for validation.

    Creates frozen snapshot of:
    - IMMUTABLE tier: Contact info, work dates/titles, education, certifications
    - VERIFIABLE tier: Skills, tools, technologies, certifications
    - FLEXIBLE tier: Summaries, bullet descriptions for semantic analysis

    Args:
        user_cv: Source CV (UserCV model)

    Returns:
        Result[FVSBaseline] with baseline facts or error details.

    Example:
        >>> result = create_fvs_baseline(cv)
        >>> assert result.success
        >>> baseline = result.data
        >>> assert baseline.immutable_facts['work_experiences']
    """
    # PSEUDO-CODE:
    # try:
    #     baseline = FVSBaseline(
    #         immutable_facts={
    #             'contact_info': {
    #                 'full_name': user_cv.contact_info.full_name,
    #                 'email': user_cv.contact_info.email,
    #             },
    #             'work_experiences': [
    #                 {
    #                     'company_name': exp.company_name,
    #                     'job_title': exp.job_title,
    #                     'start_date': exp.start_date,
    #                     'end_date': exp.end_date,
    #                     'location': exp.location,
    #                 }
    #                 for exp in (user_cv.work_experience or [])
    #             ],
    #             'education': [
    #                 {
    #                     'institution': edu.institution,
    #                     'degree': edu.degree,
    #                     'field': edu.field_of_study,
    #                     'graduation_date': edu.graduation_date,
    #                 }
    #                 for edu in (user_cv.education or [])
    #             ],
    #             'certifications': [
    #                 {
    #                     'name': cert.name,
    #                     'issuer': cert.issuer,
    #                     'date_obtained': cert.date_obtained,
    #                 }
    #                 for cert in (user_cv.certifications or [])
    #             ],
    #         },
    #         verifiable_facts={
    #             'skills': {s.lower() for s in (user_cv.skills or [])},
    #             'technologies': extract_technologies(user_cv),  # From work descriptions\n        #         },
    #         flexible_sections={
    #             'executive_summary': user_cv.executive_summary,\n        #             'work_experience_descriptions': [
    #                 exp.description for exp in (user_cv.work_experience or [])
    #             ],
    #         },
    #         cv_version=user_cv.version,\n        #         extraction_timestamp=datetime.utcnow().isoformat(),\n        #     )
    #     logger.info("FVS baseline created", immutable_count=len(baseline.immutable_facts))
    #     return Result(success=True, data=baseline, code=ResultCode.SUCCESS)\n    # except Exception as exc:
    #     logger.exception("failed to create FVS baseline")
    #     return Result(success=False, error=str(exc), code=ResultCode.FVS_BASELINE_FAILED)

    pass


@tracer.capture_method(capture_response=False)
def validate_tailored_cv(
    tailored_cv: TailoredCV,
    baseline: FVSBaseline,
    user_cv: UserCV,
) -> Result[list[FVSViolation]]:
    """
    Validate tailored CV against FVS baseline and rules.

    Performs three-tier validation:
    1. IMMUTABLE tier: Byte-for-byte comparison of dates, titles, names
    2. VERIFIABLE tier: Ensure skills/certs exist in source CV
    3. FLEXIBLE tier: Check for hallucinated facts in reframed content

    Args:
        tailored_cv: Tailored CV to validate (TailoredCV model)
        baseline: FVS baseline from source CV (FVSBaseline)
        user_cv: Original source CV for reference

    Returns:
        Result[list[FVSViolation]] with:
        - success=True, data=[] if validation passes (no violations)
        - success=False, data=[violations] if any violations found
        - error: Human-readable summary of violations

    Example:
        >>> baseline = create_fvs_baseline(cv).data
        >>> tailored = tailor_cv(...)
        >>> result = validate_tailored_cv(tailored, baseline, cv)
        >>> if not result.success:
        ...     for violation in result.data:
        ...         print(f"{violation.tier}: {violation.issue}")
    """
    # PSEUDO-CODE:
    # violations = []
    #
    # # Tier 1: IMMUTABLE validation
    # immutable_errors = _compare_immutable_facts(tailored_cv, baseline)
    # violations.extend(immutable_errors)
    #
    # # Tier 2: VERIFIABLE validation
    # verifiable_errors = _verify_skills_exist(tailored_cv, baseline, user_cv)
    # violations.extend(verifiable_errors)
    #
    # # Tier 3: FLEXIBLE validation
    # flexible_errors = _validate_flexible_content(tailored_cv, baseline)
    # violations.extend(flexible_errors)
    #
    # if violations:
    #     error_summary = "; ".join(
    #         [f"{v.tier}: {v.issue}" for v in violations[:5]]
    #     )
    #     logger.warning("FVS validation violations found", count=len(violations))
    #     return Result(
    #         success=False,
    #         data=violations,
    #         error=error_summary,
    #         code=ResultCode.FVS_VALIDATION_FAILED,
    #     )
    #
    # logger.info("FVS validation passed")
    # return Result(success=True, data=[], code=ResultCode.SUCCESS)

    pass


def _compare_immutable_facts(
    tailored_cv: TailoredCV,
    baseline: FVSBaseline,
) -> list[FVSViolation]:
    """
    Compare IMMUTABLE tier facts between source and tailored CV.

    Checks:
    - Company names match exactly
    - Job titles match exactly
    - Dates match exactly (no alterations)
    - Education preserved
    - Certifications preserved

    Args:
        tailored_cv: Tailored CV (TailoredCV model)
        baseline: FVS baseline (FVSBaseline)

    Returns:
        List of FVSViolation objects (empty if all match).

    Example:
        >>> violations = _compare_immutable_facts(tailored, baseline)
        >>> assert len(violations) == 0  # All immutable facts preserved
    """
    # PSEUDO-CODE:
    # violations = []
    #
    # # Check work experience IMMUTABLE facts
    # for i, tailored_exp in enumerate(tailored_cv.work_experience):
    #     if i >= len(baseline.immutable_facts['work_experiences']):
    #         violations.append(FVSViolation(
    #             tier="IMMUTABLE",
    #             field=f"work_experience_{i}",
    #             rule="must exist in source CV",
    #             issue=f"Hallucinated work experience at index {i}",
    #         ))
    #         continue
    #
    #     source_exp = baseline.immutable_facts['work_experiences'][i]
    #
    #     if tailored_exp.company_name != source_exp['company_name']:
    #         violations.append(FVSViolation(
    #             tier="IMMUTABLE",
    #             field="company_name",
    #             rule="must be preserved exactly",
    #             issue=f"Company name altered in work experience {i}",
    #             source_value=source_exp['company_name'],
    #             actual_value=tailored_exp.company_name,
    #         ))
    #
    #     if tailored_exp.job_title != source_exp['job_title']:
    #         violations.append(FVSViolation(
    #             tier="IMMUTABLE",
    #             field="job_title",
    #             rule="must be preserved exactly",
    #             issue=f"Job title altered in work experience {i}",
    #             source_value=source_exp['job_title'],
    #             actual_value=tailored_exp.job_title,
    #         ))
    #
    #     if tailored_exp.start_date != source_exp['start_date']:
    #         violations.append(FVSViolation(
    #             tier="IMMUTABLE",
    #             field="start_date",
    #             rule="must be preserved exactly",
    #             issue=f"Start date altered in work experience {i}",
    #             source_value=source_exp['start_date'],
    #             actual_value=tailored_exp.start_date,
    #         ))
    #
    # return violations

    pass


def _verify_skills_exist(
    tailored_cv: TailoredCV,
    baseline: FVSBaseline,
    user_cv: UserCV,
) -> list[FVSViolation]:
    """
    Verify VERIFIABLE tier facts (skills, certifications) exist in source.

    Checks:
    - All skills in tailored CV exist in source CV
    - No hallucinated skills added
    - All certifications in source

    Args:
        tailored_cv: Tailored CV (TailoredCV model)
        baseline: FVS baseline (FVSBaseline)
        user_cv: Source CV for reference

    Returns:
        List of FVSViolation objects for hallucinated skills/certs.

    Example:
        >>> violations = _verify_skills_exist(tailored, baseline, cv)
        >>> # Check no Kubernetes in violations if not in source
    """
    # PSEUDO-CODE:
    # violations = []
    #
    # # Verify skills
    # source_skills = baseline.verifiable_facts['skills']
    # for skill in tailored_cv.skills:
    #     if skill.skill_name.lower() not in source_skills:
    #         violations.append(FVSViolation(
    #             tier="VERIFIABLE",
    #             field="skill",
    #             rule="must exist in source CV",
    #             issue=f"Hallucinated skill: '{skill.skill_name}'",
    #             actual_value=skill.skill_name,
    #         ))
    #
    # # Verify certifications
    # source_certs = {c.name.lower() for c in (user_cv.certifications or [])}
    # for cert in tailored_cv.certifications:
    #     cert_name = cert.get('name', '').lower()
    #     if cert_name and cert_name not in source_certs:
    #         violations.append(FVSViolation(
    #             tier="VERIFIABLE",
    #             field="certification",
    #             rule="must exist in source CV",
    #             issue=f"Hallucinated certification: '{cert.get('name')}'",\n        #             actual_value=cert.get('name'),
    #         ))
    #
    # return violations

    pass


def _validate_flexible_content(
    tailored_cv: TailoredCV,
    baseline: FVSBaseline,
) -> list[FVSViolation]:
    """
    Validate FLEXIBLE tier content for semantic consistency.

    Checks:
    - Executive summary is substantially different (reframed)
    - Work experience bullets are reframed but preserve meaning
    - No new facts introduced in descriptions
    - No fabricated metrics or achievements

    Args:
        tailored_cv: Tailored CV (TailoredCV model)
        baseline: FVS baseline (FVSBaseline)

    Returns:
        List of FVSViolation objects (warnings for style, errors for new facts).

    Example:
        >>> violations = _validate_flexible_content(tailored, baseline)
        >>> # Reframing is OK, hallucinated facts are errors
    """
    # PSEUDO-CODE:
    # violations = []
    #
    # # Check work experience descriptions
    # for i, exp in enumerate(tailored_cv.work_experience):
    #     if i >= len(exp.original_bullets):
    #         continue
    #
    #     original_bullets = set(exp.original_bullets)
    #     new_bullets = set(exp.description_bullets)
    #
    #     # Check if completely replaced (good for reframing)
    #     if original_bullets == new_bullets:
    #         violations.append(FVSViolation(
    #             tier="FLEXIBLE",
    #             field=f"work_experience_{i}",
    #             rule="should be reframed for job relevance",
    #             issue=f"Bullets not reframed in work experience {i}",
    #             severity="WARNING",
    #         ))
    #
    #     # Check for hallucinated metrics
    #     for bullet in new_bullets:
    #         if _has_unsupported_metric(bullet, original_bullets):
    #             violations.append(FVSViolation(
    #                 tier="FLEXIBLE",
    #                 field=f"work_experience_{i}",
    #                 rule="metrics must be evidenced in source",
    #                 issue=f"Possible hallucinated metric: '{bullet}'",
    #                 actual_value=bullet,
    #             ))
    #
    # return violations


def _has_unsupported_metric(new_bullet: str, original_bullets: set[str]) -> bool:
    """
    Check if new bullet contains metrics not in original.

    Flags suspicious patterns:
    - Specific percentages not in original
    - Specific numbers (team size, budget) not in original
    - Claims of achievement without source evidence

    PSEUDO-CODE:
    # import re
    # metrics = re.findall(r'(\d+%|\$[\d.]+[MK]?|team of \d+)', new_bullet)
    # for metric in metrics:
    #     if metric not in " ".join(original_bullets):
    #         return True  # Suspicious metric
    # return False
    """
    pass


def generate_validation_report(violations: list[FVSViolation]) -> str:
    """
    Generate human-readable validation report.

    Groups violations by tier and severity for debugging.

    Args:
        violations: List of FVSViolation objects

    Returns:
        Formatted report string.

    Example:
        >>> violations = [...]
        >>> report = generate_validation_report(violations)
        >>> print(report)
    """
    # PSEUDO-CODE:
    # if not violations:
    #     return "FVS Validation Passed: No violations detected"
    #
    # report_lines = ["FVS Validation Report", "=" * 40]
    #
    # # Group by tier
    # by_tier = {}
    # for v in violations:
    #     if v.tier not in by_tier:
    #         by_tier[v.tier] = []
    #     by_tier[v.tier].append(v)
    #
    # for tier in ["IMMUTABLE", "VERIFIABLE", "FLEXIBLE"]:
    #     if tier in by_tier:
    #         report_lines.append(f"\n{tier} Tier ({len(by_tier[tier])} violations):")
    #         for v in by_tier[tier]:
    #             report_lines.append(f"  - {v.issue}")
    #             if v.source_value and v.actual_value:
    #                 report_lines.append(f"    Expected: {v.source_value}")
    #                 report_lines.append(f"    Actual: {v.actual_value}")
    #
    # return "\n".join(report_lines)

    pass
```

### Test Implementation Structure

```python
"""
Tests for FVS Integration.
Per tests/logic/test_fvs_integration.py.

Test categories:
- Baseline creation (3 tests)
- IMMUTABLE tier validation (5 tests)
- VERIFIABLE tier validation (4 tests)
- FLEXIBLE tier validation (4 tests)
- Integrated validation flow (5 tests)
- Error reporting (3 tests)

Total: 20-25 tests
"""

import pytest
from unittest.mock import Mock

from careervp.logic.fvs_tailor_integration import (
    create_fvs_baseline,
    validate_tailored_cv,
    _compare_immutable_facts,
    _verify_skills_exist,
    _validate_flexible_content,
    generate_validation_report,
    FVSBaseline,
    FVSViolation,
)


class TestBaselineCreation:
    """Test FVS baseline creation."""

    def test_create_baseline_includes_immutable_facts(self):
        """Baseline captures IMMUTABLE facts."""
        # PSEUDO-CODE:
        # cv = Mock(UserCV)
        # cv.contact_info = Mock(full_name="John", email="john@example.com")
        # cv.work_experience = [Mock(company_name="Acme")]
        # result = create_fvs_baseline(cv)
        # assert result.success
        # baseline = result.data
        # assert baseline.immutable_facts['contact_info']['full_name'] == "John"
        pass

    def test_create_baseline_includes_verifiable_facts(self):
        """Baseline captures VERIFIABLE facts."""
        # PSEUDO-CODE:
        # cv = Mock(UserCV)
        # cv.skills = ["Python", "AWS"]
        # cv.certifications = [Mock(name="AWS")]
        # result = create_fvs_baseline(cv)
        # baseline = result.data
        # assert "python" in baseline.verifiable_facts['skills']
        pass

    def test_create_baseline_includes_flexible_sections(self):
        """Baseline captures FLEXIBLE sections."""
        # PSEUDO-CODE:
        # cv = Mock(UserCV)
        # cv.executive_summary = "Experienced engineer"
        # result = create_fvs_baseline(cv)
        # baseline = result.data
        # assert baseline.flexible_sections['executive_summary']
        pass


class TestImmutableValidation:
    """Test IMMUTABLE tier validation."""

    def test_immutable_validation_preserves_company_names(self):
        """IMMUTABLE validation checks company names."""
        # PSEUDO-CODE:
        # baseline = FVSBaseline(
        #     immutable_facts={'work_experiences': [{'company_name': 'Acme'}]},
        #     ...
        # )
        # tailored = Mock(work_experience=[Mock(company_name='Acme')])
        # violations = _compare_immutable_facts(tailored, baseline)
        # assert len(violations) == 0
        pass

    def test_immutable_validation_rejects_altered_company_names(self):
        """IMMUTABLE validation detects altered company names."""
        # PSEUDO-CODE:
        # baseline = FVSBaseline(
        #     immutable_facts={'work_experiences': [{'company_name': 'Acme Corp'}]},
        # )
        # tailored = Mock(work_experience=[Mock(company_name='Acme')])
        # violations = _compare_immutable_facts(tailored, baseline)
        # assert len(violations) > 0
        # assert violations[0].tier == "IMMUTABLE"
        pass

    def test_immutable_validation_preserves_job_titles(self):
        """IMMUTABLE validation checks job titles."""
        # PSEUDO-CODE:
        # baseline = FVSBaseline(
        #     immutable_facts={'work_experiences': [{'job_title': 'Engineer'}]},
        # )
        # tailored = Mock(work_experience=[Mock(job_title='Engineer')])
        # violations = _compare_immutable_facts(tailored, baseline)
        # assert len(violations) == 0
        pass

    def test_immutable_validation_preserves_dates(self):
        """IMMUTABLE validation checks dates."""
        # PSEUDO-CODE:
        # baseline = FVSBaseline(
        #     immutable_facts={'work_experiences': [{'start_date': '2020-01-01'}]},
        # )
        # tailored = Mock(work_experience=[Mock(start_date='2020-01-01')])
        # violations = _compare_immutable_facts(tailored, baseline)
        # assert len(violations) == 0
        pass

    def test_immutable_validation_rejects_hallucinated_experiences(self):
        """IMMUTABLE validation detects hallucinated work experiences."""
        # PSEUDO-CODE:
        # baseline = FVSBaseline(
        #     immutable_facts={'work_experiences': []},
        # )
        # tailored = Mock(work_experience=[Mock(company_name='Fake')])
        # violations = _compare_immutable_facts(tailored, baseline)
        # assert len(violations) > 0
        # assert "hallucinated" in violations[0].issue.lower()
        pass


class TestVerifiableValidation:
    """Test VERIFIABLE tier validation."""

    def test_verifiable_validation_allows_existing_skills(self):
        """VERIFIABLE validation allows skills from source."""
        # PSEUDO-CODE:
        # baseline = FVSBaseline(
        #     verifiable_facts={'skills': {'python', 'aws'}},
        # )
        # cv = Mock(certifications=[])
        # tailored = Mock(skills=[Mock(skill_name='Python')], certifications=[])
        # violations = _verify_skills_exist(tailored, baseline, cv)
        # assert len(violations) == 0
        pass

    def test_verifiable_validation_rejects_hallucinated_skills(self):
        """VERIFIABLE validation detects hallucinated skills."""
        # PSEUDO-CODE:
        # baseline = FVSBaseline(
        #     verifiable_facts={'skills': {'python'}},
        # )
        # cv = Mock(certifications=[])
        # tailored = Mock(skills=[Mock(skill_name='Kubernetes')], certifications=[])
        # violations = _verify_skills_exist(tailored, baseline, cv)
        # assert len(violations) > 0
        # assert "hallucinated" in violations[0].issue.lower()
        pass

    def test_verifiable_validation_allows_existing_certifications(self):
        """VERIFIABLE validation allows certifications from source."""
        # PSEUDO-CODE:
        # baseline = FVSBaseline(verifiable_facts={...})
        # cv = Mock(certifications=[Mock(name='AWS Solutions')])
        # tailored = Mock(skills=[], certifications=[{'name': 'AWS Solutions'}])
        # violations = _verify_skills_exist(tailored, baseline, cv)
        # assert len(violations) == 0
        pass

    def test_verifiable_validation_rejects_hallucinated_certifications(self):
        """VERIFIABLE validation detects hallucinated certifications."""
        # PSEUDO-CODE:
        # cv = Mock(certifications=[Mock(name='AWS')])
        # tailored = Mock(skills=[], certifications=[{'name': 'PhD in CS'}])
        # violations = _verify_skills_exist(tailored, baseline, cv)
        # assert len(violations) > 0
        pass
```

### Verification Commands

```bash
# Format code
uv run ruff format src/backend/careervp/logic/

# Check for style issues
uv run ruff check --fix src/backend/careervp/logic/

# Type check with strict mode
uv run mypy src/backend/careervp/logic/ --strict

# Run FVS integration tests
uv run pytest tests/logic/test_fvs_integration.py -v

# Expected output:
# ===== test session starts =====
# tests/logic/test_fvs_integration.py::TestBaselineCreation PASSED (3 tests)
# tests/logic/test_fvs_integration.py::TestImmutableValidation PASSED (5 tests)
# ... [20-25 total tests]
# ===== 20-25 passed in X.XXs =====
```

### Expected Test Results

```
tests/logic/test_fvs_integration.py PASSED

Baseline Creation: 3 PASSED
- IMMUTABLE facts captured
- VERIFIABLE facts captured
- FLEXIBLE sections captured

IMMUTABLE Tier Validation: 5 PASSED
- Company names preserved
- Job titles preserved
- Dates preserved
- Altered facts detected
- Hallucinated experiences rejected

VERIFIABLE Tier Validation: 4 PASSED
- Existing skills allowed
- Hallucinated skills detected
- Existing certifications allowed
- Hallucinated certifications detected

FLEXIBLE Tier Validation: 4 PASSED
- Reframing detected
- Metrics validation
- Semantic consistency
- Warning for unchanged content

Integrated Validation Flow: 5 PASSED
- Complete validation passes
- Partial violations detected
- Error summary generated
- Report formatting correct
- All violation types handled

Total: 20-25 tests passing
Type checking: 0 errors, 0 warnings
```

### Zero-Hallucination Checklist

- [ ] FVS baseline extraction captures all IMMUTABLE tier fields
- [ ] IMMUTABLE tier validation uses byte-for-byte comparison
- [ ] VERIFIABLE tier validation checks skill/cert existence
- [ ] FLEXIBLE tier allows reframing but detects hallucinated facts
- [ ] No new facts allowed in tailored content
- [ ] Metrics checked for source evidence
- [ ] Work experience count validation
- [ ] All violations properly categorized by tier
- [ ] Error reporting includes source vs actual values
- [ ] Phase 6 FVS validator integration tested

### Acceptance Criteria

- [ ] `create_fvs_baseline()` returns FVSBaseline with all tiers
- [ ] `validate_tailored_cv()` returns Result[list[FVSViolation]]
- [ ] IMMUTABLE facts checked byte-for-byte
- [ ] VERIFIABLE facts checked for existence
- [ ] FLEXIBLE content validated for new facts
- [ ] FVSViolation objects include tier, field, issue, severity
- [ ] Validation report human-readable with grouped violations
- [ ] Integration with Phase 6 FVS validator working
- [ ] 20-25 tests all passing
- [ ] Type checking passes with `mypy --strict`

---

### Verification & Compliance

1. Run `python src/backend/scripts/validate_naming.py --path src/backend/careervp/logic --strict`
2. Run `uv run ruff format . && uv run ruff check --fix . && uv run mypy --strict .`
3. Run `uv run pytest tests/logic/test_fvs_integration.py -v --cov`
4. If any FVS validation fails, report a **BLOCKING ISSUE** and exit.
