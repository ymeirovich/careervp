"""Unit tests for FVS quality validation checks."""

from careervp.logic.fvs_validator import (
    check_anti_ai_patterns,
    check_cross_document_consistency,
    score_ats_content,
    validate_grammar,
    validate_tone,
)


def test_grammar_validation_scores_above_threshold() -> None:
    content = (
        "I led platform modernization across three product lines. "
        "The program reduced release incidents by 32% while improving cycle time. "
        "I partnered with engineering and product leaders to align priorities and execution."
    )
    result = validate_grammar(content)

    assert result.score >= 9.0
    assert result.passed is True


def test_tone_validation_detects_robotic_language() -> None:
    robotic_content = (
        "I think we can maybe leverage robust synergy across the organization! "
        "I think we can maybe leverage robust synergy across the organization! "
        "I think we can maybe leverage robust synergy across the organization!"
    )
    result = validate_tone(robotic_content)

    assert result.score < 8.0
    assert result.passed is False
    assert result.issues


def test_anti_ai_patterns_detected() -> None:
    robotic_content = (
        "We leverage robust best practices to facilitate paradigm shift outcomes. "
        "We leverage robust best practices to facilitate paradigm shift outcomes. "
        "We leverage robust best practices to facilitate paradigm shift outcomes."
    )
    result = check_anti_ai_patterns(robotic_content)

    assert result.score < 9.0
    assert any("Pattern 1" in issue for issue in result.issues)


def test_ats_scoring_returns_numeric_score() -> None:
    cv_content = (
        "Experience: Led migration to AWS and improved Python service reliability by 40%. "
        "Skills: Python, AWS, leadership, collaboration, delivery."
    )
    score = score_ats_content(
        cv_content, keywords=["python", "aws", "leadership"], document_type="cv"
    )

    assert isinstance(score, float)
    assert 0.0 <= score <= 10.0


def test_cross_document_consistency_check() -> None:
    cv_content = (
        "I worked as Senior Software Engineer at Acme Corp in 2022. "
        "I worked as Staff Engineer at Blue Rocket in 2024."
    )
    vpr_content = "I served as Senior Software Engineer at Acme Corp in 2022 with measurable impact."
    cover_letter_content = "I worked as Staff Engineer at Blue Rocket in 2024 and delivered critical platform upgrades."

    result = check_cross_document_consistency(
        vpr_content, cv_content, cover_letter_content
    )

    assert result.passed is True
    assert result.contradictions == []
    assert result.score >= 9.0
