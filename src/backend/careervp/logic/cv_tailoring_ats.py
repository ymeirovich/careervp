"""Deterministic ATS scoring rules engine — 5-component 100-point scale.

Spec: CVT-P7 / careervp_cv_tailoring_schemas.json#ATSResult
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from careervp.models.cv_tailoring_models import ATSComponents, ATSIssue, ATSResult

if TYPE_CHECKING:
    from careervp.models.cv_tailoring_models import CVSections

_REQUIRED_SECTIONS = ('summary', 'skills', 'experience', 'education')
_SECTION_PT = 15.0 / len(_REQUIRED_SECTIONS)  # 3.75 per required section


def compute_ats_result(
    cv_sections: CVSections,
    primary_keywords: list[str],
) -> ATSResult:
    """Run all 5 scoring components and return a structured ATSResult.

    Components (100pt total):
      keyword_match         40pt  — primary keyword coverage
      quantified_bullets    20pt  — bullets containing a numeric metric
      section_headers       15pt  — required sections present
      formatting_safety     15pt  — no tables/columns, standard date format
      summary_keyword_density 10pt — keywords in professional summary
    """
    cv_text = _cv_to_text(cv_sections).lower()

    # ── Component 1: keyword_match (0-40) ────────────────────────────────────
    matched = [kw for kw in primary_keywords if kw.lower() in cv_text]
    missing = [kw for kw in primary_keywords if kw.lower() not in cv_text]
    keyword_match = round((len(matched) / max(len(primary_keywords), 1)) * 40, 1)

    # ── Component 2: quantified_bullets (0-20) ────────────────────────────────
    all_bullets = [b.text if hasattr(b, 'text') else str(b) for exp in cv_sections.experience for b in exp.bullets]
    quant_count = sum(1 for b in all_bullets if re.search(r'\d+|%|\$', b))
    quantified_bullets = round((quant_count / max(len(all_bullets), 1)) * 20, 1)

    # ── Component 3: section_headers (0-15) ──────────────────────────────────
    present = sum(
        [
            bool(cv_sections.summary),
            bool(cv_sections.skills.technical or cv_sections.skills.soft),
            bool(cv_sections.experience),
            bool(cv_sections.education),
        ]
    )
    section_headers = round(present * _SECTION_PT, 1)

    # ── Component 4: formatting_safety (0-15) ────────────────────────────────
    # Content is structured JSON — tables/columns impossible by design (10pt free).
    # Date format: experience start_date must match MM/YYYY or be empty (5pt).
    dates_ok = all((not exp.start_date) or bool(re.match(r'^\d{2}/\d{4}$', exp.start_date)) for exp in cv_sections.experience)
    formatting_safety = 10.0 + (5.0 if dates_ok else 0.0)

    # ── Component 5: summary_keyword_density (0-10) ───────────────────────────
    summary_lower = cv_sections.summary.lower()
    kw_in_summary = sum(1 for kw in matched if kw.lower() in summary_lower)
    summary_keyword_density = min(10.0, round(kw_in_summary * 2.5, 1))

    # ── Totals ────────────────────────────────────────────────────────────────
    total = int(keyword_match + quantified_bullets + section_headers + formatting_safety + summary_keyword_density)
    grade = 'green' if total >= 90 else ('yellow' if total >= 70 else 'red')
    issues = _build_issues(keyword_match, quantified_bullets, section_headers, missing)
    kw_score_10 = max(1, min(10, round(total / 10)))

    return ATSResult(
        total_score=total,
        grade=grade,
        components=ATSComponents(
            keyword_match=keyword_match,
            quantified_bullets=quantified_bullets,
            section_headers=section_headers,
            formatting_safety=formatting_safety,
            summary_keyword_density=summary_keyword_density,
        ),
        issues=issues,
        keywords_matched=matched,
        keywords_missing=missing,
        keyword_match_score_1_10=kw_score_10,
    )


def _cv_to_text(cv_sections: CVSections) -> str:
    """Flatten all CV text into a single string for keyword matching."""
    parts: list[str] = [cv_sections.summary]
    parts.extend(cv_sections.skills.technical)
    parts.extend(cv_sections.skills.soft)
    for exp in cv_sections.experience:
        parts.append(exp.title)
        for b in exp.bullets:
            parts.append(b.text if hasattr(b, 'text') else str(b))
    for edu in cv_sections.education:
        parts.append(edu.degree)
        parts.append(edu.field)
    return ' '.join(parts)


def _build_issues(
    keyword_match: float,
    quantified_bullets: float,
    section_headers: float,
    missing_keywords: list[str],
) -> list[ATSIssue]:
    """Generate actionable ATS issues for scores below threshold."""
    issues: list[ATSIssue] = []
    if keyword_match < 24:  # < 60% of 40pt
        issues.append(
            ATSIssue(
                code='LOW_KEYWORD_MATCH',
                severity='critical',
                message=f'Only {round(keyword_match / 40 * 100)}% of primary keywords matched.',
                suggestion=f'Add these keywords naturally: {", ".join(missing_keywords[:5])}',
            )
        )
    if quantified_bullets < 10:  # < 50% of 20pt
        issues.append(
            ATSIssue(
                code='FEW_QUANTIFIED_BULLETS',
                severity='warning',
                message='Fewer than half of experience bullets contain a numeric metric.',
                suggestion='Add specific numbers, percentages, or dollar amounts to bullets.',
            )
        )
    if section_headers < 11.25:  # fewer than 3 of 4 required sections
        issues.append(
            ATSIssue(
                code='MISSING_SECTIONS',
                severity='critical',
                message='One or more required CV sections are absent.',
                suggestion='Ensure summary, skills, experience, and education sections are present.',
            )
        )
    return issues
