"""Shared payload quality assertions for live API tests."""

from __future__ import annotations

from typing import Any


def _non_empty_text(value: Any) -> str:
    return str(value or "").strip()


def assert_vpr_quality(data: dict[str, Any]) -> None:
    result = data.get("result")
    assert isinstance(result, dict), "VPR response must include result object"

    uvp = _non_empty_text(result.get("uvp"))
    assert len(uvp) >= 20, "VPR UVP is too short"

    differentiators = result.get("differentiators")
    assert isinstance(differentiators, list) and len(differentiators) >= 3, (
        "VPR differentiators must include at least 3 items"
    )
    valid_count = 0
    for entry in differentiators:
        if isinstance(entry, dict):
            text = _non_empty_text(entry.get("text"))
        else:
            text = _non_empty_text(entry)
        if len(text) >= 12:
            valid_count += 1
    assert valid_count >= 3, "VPR differentiators are too weak"


def assert_cv_list_quality(data: dict[str, Any]) -> None:
    cvs = data.get("cvs")
    assert isinstance(cvs, list) and len(cvs) >= 1, "Expected at least one CV record"

    strongest = ""
    for item in cvs:
        if not isinstance(item, dict):
            continue
        candidate = " ".join(
            [
                _non_empty_text(item.get("full_name")),
                _non_empty_text(item.get("professional_summary")),
                _non_empty_text(item.get("cv_content")),
                _non_empty_text(item.get("parsed_text")),
            ]
        ).strip()
        if len(candidate) > len(strongest):
            strongest = candidate
    assert len(strongest) >= 40, "CV payload is missing meaningful textual content"


def assert_gap_questions_quality(data: dict[str, Any]) -> None:
    questions = data.get("questions")
    assert isinstance(questions, list) and len(questions) >= 3, (
        "Expected at least 3 gap questions"
    )

    for idx, question in enumerate(questions):
        assert isinstance(question, dict), f"Gap question #{idx + 1} must be an object"
        assert _non_empty_text(question.get("id")), (
            f"Gap question #{idx + 1} missing id"
        )
        text = _non_empty_text(question.get("text"))
        assert len(text) >= 12, f"Gap question #{idx + 1} text is too short"


def assert_tailored_cv_quality(data: dict[str, Any]) -> None:
    result = data.get("result")
    assert isinstance(result, dict), "Tailored CV status must include result object"

    tailored_cv = _non_empty_text(result.get("tailored_cv"))
    assert len(tailored_cv) >= 80, "Tailored CV text is too short"

    ats_score = result.get("ats_score")
    assert isinstance(ats_score, (int, float)), (
        "Tailored CV must include numeric ats_score"
    )


def assert_cover_letter_quality(data: dict[str, Any]) -> None:
    result = data.get("result")
    assert isinstance(result, dict), "Cover letter status must include result object"

    cover_letter = _non_empty_text(result.get("cover_letter"))
    assert len(cover_letter) >= 80, "Cover letter text is too short"
    assert cover_letter.lower() != "cover letter generation completed.", (
        "Cover letter payload is placeholder text"
    )


def assert_interview_prep_quality(data: dict[str, Any]) -> None:
    result = data.get("result")
    assert isinstance(result, dict), "Interview prep status must include result object"

    questions = result.get("questions")
    assert isinstance(questions, list) and len(questions) >= 3, (
        "Interview prep must include at least 3 questions"
    )

    rich_questions = 0
    for idx, question in enumerate(questions):
        assert isinstance(question, dict), (
            f"Interview question #{idx + 1} must be an object"
        )
        assert _non_empty_text(question.get("id")), (
            f"Interview question #{idx + 1} missing id"
        )
        text = _non_empty_text(question.get("text"))
        if len(text) >= 14:
            rich_questions += 1
    assert rich_questions >= 3, "Interview prep question content is too weak"

    report = result.get("interview_report")
    if isinstance(report, dict):
        summary = _non_empty_text(report.get("readiness_summary"))
        assert len(summary) >= 30, "Interview report summary is too short"
