"""Gap Analysis runbook tests for 10-question generation and response persistence."""

from __future__ import annotations

from collections import Counter
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from careervp.handlers import gap_handler
from careervp.logic.gap_analysis import (
    TAG_BEHAVIORAL,
    TAG_CV_IMPACT,
    TAG_INTERVIEW_MVP,
    TAG_TECHNICAL,
    generate_gap_questions,
)
from careervp.models.result import Result, ResultCode


def _build_llm_questions(count: int = 12) -> list[dict[str, Any]]:
    return [
        {
            "question_id": f"q{i + 1}",
            "question": f"Question {i + 1}",
            "impact": "HIGH" if i < 4 else "MEDIUM",
            "probability": "HIGH" if i % 2 == 0 else "MEDIUM",
            "gap_score": round(max(0.05, 1 - (i * 0.07)), 2),
        }
        for i in range(count)
    ]


@pytest.mark.asyncio
async def test_generate_10_questions() -> None:
    mock_dal = MagicMock()
    llm_questions = _build_llm_questions()

    with patch("careervp.logic.gap_analysis.LLMClient") as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = Result(
            success=True,
            data=json.dumps(llm_questions),
            code=ResultCode.SUCCESS,
        )
        mock_llm_class.return_value = mock_llm

        result = await generate_gap_questions(
            user_cv={"personal_info": {"full_name": "Test User"}},
            job_posting={
                "company_name": "ACME",
                "role_title": "Engineer",
                "requirements": [],
            },
            dal=mock_dal,
            language="en",
        )

    assert result.success is True
    assert result.code == ResultCode.GAP_QUESTIONS_GENERATED
    assert result.data is not None
    assert len(result.data) == 10
    assert all(
        isinstance(question.get("tags"), list) and len(question["tags"]) >= 1
        for question in result.data
    )


@pytest.mark.asyncio
async def test_question_tagging_all_categories_present() -> None:
    mock_dal = MagicMock()

    with patch("careervp.logic.gap_analysis.LLMClient") as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = Result(
            success=True,
            data=json.dumps(_build_llm_questions()),
            code=ResultCode.SUCCESS,
        )
        mock_llm_class.return_value = mock_llm

        result = await generate_gap_questions(
            user_cv={"personal_info": {"full_name": "Test User"}},
            job_posting={
                "company_name": "ACME",
                "role_title": "Engineer",
                "requirements": [],
            },
            dal=mock_dal,
            language="en",
        )

    assert result.success is True
    assert result.data is not None
    present_tags = {question["tags"][0] for question in result.data}
    assert TAG_CV_IMPACT in present_tags
    assert TAG_TECHNICAL in present_tags
    assert TAG_BEHAVIORAL in present_tags
    assert TAG_INTERVIEW_MVP in present_tags


@pytest.mark.asyncio
async def test_question_distribution_meets_targets() -> None:
    mock_dal = MagicMock()

    with patch("careervp.logic.gap_analysis.LLMClient") as mock_llm_class:
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = Result(
            success=True,
            data=json.dumps(_build_llm_questions()),
            code=ResultCode.SUCCESS,
        )
        mock_llm_class.return_value = mock_llm

        result = await generate_gap_questions(
            user_cv={"personal_info": {"full_name": "Test User"}},
            job_posting={
                "company_name": "ACME",
                "role_title": "Engineer",
                "requirements": [],
            },
            dal=mock_dal,
            language="en",
        )

    assert result.success is True
    assert result.data is not None

    distribution = Counter(question["tags"][0] for question in result.data)
    assert distribution[TAG_CV_IMPACT] == 4
    assert distribution[TAG_TECHNICAL] == 2
    assert distribution[TAG_BEHAVIORAL] == 2
    assert distribution[TAG_INTERVIEW_MVP] == 2


class _InMemoryGapTable:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], dict[str, Any]] = {}

    def put_item(self, Item: dict[str, Any]) -> None:  # noqa: N803
        key = (str(Item["pk"]), str(Item["sk"]))
        self._items[key] = Item

    def get_item(self, Key: dict[str, Any]) -> dict[str, Any]:  # noqa: N803
        key = (str(Key["pk"]), str(Key["sk"]))
        item = self._items.get(key)
        if item is None:
            return {}
        return {"Item": item}

    def query(
        self,
        KeyConditionExpression: Any,
        ExclusiveStartKey: dict[str, Any] | None = None,
    ) -> dict[str, Any]:  # noqa: N803
        _ = KeyConditionExpression
        _ = ExclusiveStartKey
        return {"Items": []}


def test_response_storage_persists_correctly(monkeypatch: pytest.MonkeyPatch) -> None:
    table = _InMemoryGapTable()
    monkeypatch.setattr(gap_handler, "_get_table", lambda: table)

    submit_event = {
        "headers": {"x-user-id": "user-123"},
        "body": json.dumps(
            {
                "job_id": "job-456",
                "cv_id": "cv-789",
                "responses": [
                    {"question_id": "q1", "response": "I improved latency by 40%."},
                    {
                        "question_id": "q2",
                        "response": "I led a migration for 12 engineers.",
                    },
                ],
            }
        ),
    }

    submit_result = gap_handler.submit_response(submit_event)
    assert submit_result["statusCode"] == 200
    submit_body = json.loads(submit_result["body"])
    assert submit_body["status"] == "saved"
    assert submit_body["responses_saved"] == 2

    get_responses_event = {
        "headers": {"x-user-id": "user-123"},
        "pathParameters": {"jobId": "job-456"},
        "path": "/gap-analysis/responses/job-456",
    }
    get_result = gap_handler.get_responses(get_responses_event)
    assert get_result["statusCode"] == 200
    get_body = json.loads(get_result["body"])
    assert get_body["job_id"] == "job-456"
    assert len(get_body["responses"]) == 2
    assert get_body["responses"][0]["question_id"] == "q1"

    get_missing_questions_event = {
        "headers": {"x-user-id": "user-123"},
        "pathParameters": {"jobId": "job-456"},
        "path": "/gap-analysis/questions/job-456",
    }
    missing_questions_result = gap_handler.get_questions(get_missing_questions_event)
    assert missing_questions_result["statusCode"] == 404
