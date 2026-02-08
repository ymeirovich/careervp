"""
Integration tests for CV Tailoring Handler.

Tests the full Handler -> Logic -> DAL flow with mocked external dependencies
(DynamoDB, Bedrock) but real internal integration between layers.
"""

import json
from unittest.mock import MagicMock, patch

from careervp.handlers.cv_tailoring_handler import handler


def test_full_flow_success(
    sample_master_cv,
    sample_tailored_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test complete happy path from handler to DAL with all layers."""
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with (
        patch("careervp.handlers.cv_tailoring_handler.CVTable") as mock_cv_table_class,
        patch("careervp.handlers.cv_tailoring_handler.LLMClient") as mock_llm_class,
    ):
        mock_cv_table_instance = MagicMock()
        mock_cv_table_instance.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.model_dump(),
            }
        }
        mock_cv_table_class.return_value = mock_cv_table_instance

        mock_llm_instance = MagicMock()
        mock_llm_instance.generate.return_value = sample_tailored_cv.model_dump()
        mock_llm_class.return_value = mock_llm_instance

        response = handler(event, lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["success"] is True
    assert "tailored_cv" in body["data"]


def test_full_flow_with_preferences(
    sample_master_cv,
    sample_tailored_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test full flow with custom tailoring preferences."""
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
                "preferences": {
                    "tone": "formal",
                    "target_length": "concise",
                    "emphasis_areas": ["Python", "AWS"],
                },
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with (
        patch("careervp.handlers.cv_tailoring_handler.CVTable") as mock_cv_table_class,
        patch("careervp.handlers.cv_tailoring_handler.LLMClient") as mock_llm_class,
    ):
        mock_cv_table_instance = MagicMock()
        mock_cv_table_instance.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.model_dump(),
            }
        }
        mock_cv_table_class.return_value = mock_cv_table_instance

        mock_llm_instance = MagicMock()
        mock_llm_instance.generate.return_value = sample_tailored_cv.model_dump()
        mock_llm_class.return_value = mock_llm_instance

        response = handler(event, lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["success"] is True


def test_full_flow_fvs_rejection(
    sample_master_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test full flow where FVS blocks hallucinated output."""
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    hallucinated_cv = sample_master_cv.model_dump()
    hallucinated_cv["work_experience"][0]["start_date"] = "2020-01-15"
    hallucinated_cv["email"] = "fake@example.com"

    with (
        patch("careervp.handlers.cv_tailoring_handler.CVTable") as mock_cv_table_class,
        patch("careervp.handlers.cv_tailoring_handler.LLMClient") as mock_llm_class,
    ):
        mock_cv_table_instance = MagicMock()
        mock_cv_table_instance.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.model_dump(),
            }
        }
        mock_cv_table_class.return_value = mock_cv_table_instance

        mock_llm_instance = MagicMock()
        mock_llm_instance.generate.return_value = hallucinated_cv
        mock_llm_class.return_value = mock_llm_instance

        response = handler(event, lambda_context)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False
    assert body["code"] == "FVS_VIOLATION_DETECTED"


def test_full_flow_cv_not_found(lambda_context):
    """Test full flow returns 404 when CV doesn't exist."""
    event = {
        "body": json.dumps(
            {
                "cv_id": "non-existent-cv",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with patch("careervp.handlers.cv_tailoring_handler.CVTable") as mock_cv_table_class:
        mock_cv_table_instance = MagicMock()
        mock_cv_table_instance.get_item.return_value = {}
        mock_cv_table_class.return_value = mock_cv_table_instance

        response = handler(event, lambda_context)

    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert body["success"] is False


def test_full_flow_invalid_job_description(lambda_context):
    """Test full flow returns 400 for invalid job description."""
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Short",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    response = handler(event, lambda_context)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False


def test_full_flow_error_propagation(
    sample_master_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test errors from lower layers propagate correctly to handler."""
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with (
        patch("careervp.handlers.cv_tailoring_handler.CVTable") as mock_cv_table_class,
        patch("careervp.handlers.cv_tailoring_handler.LLMClient") as mock_llm_class,
    ):
        mock_cv_table_instance = MagicMock()
        mock_cv_table_instance.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.model_dump(),
            }
        }
        mock_cv_table_class.return_value = mock_cv_table_instance

        mock_llm_instance = MagicMock()
        mock_llm_instance.generate.side_effect = Exception("Bedrock API error")
        mock_llm_class.return_value = mock_llm_instance

        response = handler(event, lambda_context)

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert body["success"] is False


def test_full_flow_unauthorized_user(
    sample_master_cv,
    lambda_context,
):
    """Test full flow rejects user accessing another user's CV."""
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-456"}}},
    }

    with patch("careervp.handlers.cv_tailoring_handler.CVTable") as mock_cv_table_class:
        mock_cv_table_instance = MagicMock()
        mock_cv_table_instance.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.model_dump(),
            }
        }
        mock_cv_table_class.return_value = mock_cv_table_instance

        response = handler(event, lambda_context)

    assert response["statusCode"] == 403
    body = json.loads(response["body"])
    assert body["success"] is False


def test_full_flow_validation_before_fvs(
    lambda_context,
):
    """Test input validation happens before FVS check."""
    event = {
        "body": json.dumps(
            {
                "cv_id": "",
                "job_description": "x" * 51000,
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with patch("careervp.handlers.cv_tailoring_handler.CVTable") as mock_cv_table_class:
        mock_cv_table_instance = MagicMock()
        mock_cv_table_class.return_value = mock_cv_table_instance

        response = handler(event, lambda_context)

    assert response["statusCode"] == 400
    mock_cv_table_instance.get_item.assert_not_called()


def test_full_flow_llm_json_parsing_error(
    sample_master_cv,
    lambda_context,
):
    """Test full flow handles LLM returning invalid JSON."""
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with (
        patch("careervp.handlers.cv_tailoring_handler.CVTable") as mock_cv_table_class,
        patch("careervp.handlers.cv_tailoring_handler.LLMClient") as mock_llm_class,
    ):
        mock_cv_table_instance = MagicMock()
        mock_cv_table_instance.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.model_dump(),
            }
        }
        mock_cv_table_class.return_value = mock_cv_table_instance

        mock_llm_instance = MagicMock()
        mock_llm_instance.generate.side_effect = json.JSONDecodeError(
            "Invalid JSON", doc="invalid json{", pos=0
        )
        mock_llm_class.return_value = mock_llm_instance

        response = handler(event, lambda_context)

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert body["success"] is False


def test_full_flow_missing_cv_id(lambda_context):
    """Test full flow returns 400 when cv_id is missing."""
    event = {
        "body": json.dumps(
            {
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    response = handler(event, lambda_context)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False


def test_full_flow_missing_job_description(lambda_context):
    """Test full flow returns 400 when job_description is missing."""
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    response = handler(event, lambda_context)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False


def test_full_flow_invalid_preferences(lambda_context):
    """Test full flow returns 400 for invalid preferences."""
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
                "preferences": "invalid",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    response = handler(event, lambda_context)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False
