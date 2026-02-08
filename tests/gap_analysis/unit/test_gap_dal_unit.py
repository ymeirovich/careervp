"""
Unit tests for gap analysis DAL methods on DynamoDalHandler.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.models.job import GapResponse
from careervp.models.result import ResultCode


@pytest.fixture
def dal_with_table():
    table = MagicMock()
    dal = DynamoDalHandler(table_name="test-table")
    dal._get_db_handler = MagicMock(return_value=table)
    return dal, table


@pytest.fixture
def mock_gap_questions():
    return [
        {"question_id": "q1", "question": "What is your experience?", "category": "experience"},
        {"question_id": "q2", "question": "Describe a project.", "category": "projects"},
    ]


def test_save_gap_questions_success(dal_with_table, mock_gap_questions):
    dal, table = dal_with_table

    result = dal.save_gap_questions(
        user_id="user-123",
        cv_id="cv-456",
        job_id="job-789",
        questions=mock_gap_questions,
    )

    assert result.success is True
    assert result.code == ResultCode.SUCCESS
    table.put_item.assert_called_once()
    item = table.put_item.call_args[1]["Item"]
    assert item["pk"] == "user-123"
    assert item["sk"] == "ARTIFACT#GAP_ANALYSIS#cv-456#job-789"
    assert item["questions"] == mock_gap_questions
    assert "ttl" in item


def test_get_gap_questions_success(dal_with_table, mock_gap_questions):
    dal, table = dal_with_table
    table.get_item.return_value = {
        "Item": {
            "pk": "user-123",
            "sk": "ARTIFACT#GAP_ANALYSIS#cv-456#job-789",
            "questions": mock_gap_questions,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    }

    result = dal.get_gap_questions(user_id="user-123", cv_id="cv-456", job_id="job-789")

    assert result.success is True
    assert result.data == mock_gap_questions


def test_get_gap_questions_not_found(dal_with_table):
    dal, table = dal_with_table
    table.get_item.return_value = {}

    result = dal.get_gap_questions(user_id="user-123", cv_id="cv-456", job_id="job-789")

    assert result.success is True
    assert result.data is None


def test_save_gap_questions_handles_dynamodb_error(dal_with_table, mock_gap_questions):
    dal, table = dal_with_table
    table.put_item.side_effect = ClientError(
        {"Error": {"Code": "ProvisionedThroughputExceededException", "Message": "Throttled"}},
        "PutItem",
    )

    result = dal.save_gap_questions(
        user_id="user-123",
        cv_id="cv-456",
        job_id="job-789",
        questions=mock_gap_questions,
    )

    assert result.success is False
    assert result.code == ResultCode.DYNAMODB_ERROR


def test_save_and_get_gap_responses(dal_with_table):
    dal, table = dal_with_table
    responses = [
        GapResponse(question_id="q1", question="Question 1", answer="Answer 1", destination="CV_IMPACT"),
        GapResponse(question_id="q2", question="Question 2", answer="Answer 2", destination="CV_IMPACT"),
    ]

    save_result = dal.save_gap_responses(user_id="user-123", responses=responses, version=1)
    assert save_result.success is True
    assert save_result.code == ResultCode.GAP_RESPONSES_SAVED

    table.get_item.return_value = {
        "Item": {
            "pk": "user-123",
            "sk": "ARTIFACT#GAP_RESPONSES#v1",
            "responses": [response.model_dump(mode="json") for response in responses],
        }
    }

    get_result = dal.get_gap_responses(user_id="user-123", version=1)
    assert get_result.success is True
    assert len(get_result.data) == 2
    assert get_result.data[0].question_id == "q1"
