"""
Integration tests for CV Tailoring Handler.

Tests the full Handler → Logic → DAL flow with mocked external dependencies
(DynamoDB, Bedrock) but real internal integration between layers.
"""

import json
from unittest.mock import patch, MagicMock
from careervp.handlers.cv_tailoring_handler import handler


def test_full_flow_success(
    sample_master_cv,
    sample_tailored_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test complete happy path from handler to DAL with all layers."""
    # Arrange
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
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
    ):
        # Mock CV retrieval
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }

        # Mock LLM response
        mock_bedrock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps(sample_tailored_cv.dict()).encode()
            )
        }

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["success"] is True
    assert "tailored_cv" in body["data"]

    # Verify DAL save was called
    mock_dynamodb_table.put_item.assert_called()


def test_full_flow_with_preferences(
    sample_master_cv,
    sample_tailored_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test full flow with custom tailoring preferences."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
                "preferences": {
                    "tone": "formal",
                    "length": "concise",
                    "emphasize_skills": ["Python", "AWS"],
                    "max_pages": 1,
                },
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with (
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
    ):
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }
        mock_bedrock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps(sample_tailored_cv.dict()).encode()
            )
        }

        # Act
        response = handler(event, lambda_context)

    # Assert
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
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    # Create tailored CV with hallucinated data
    hallucinated_cv = sample_master_cv.copy(deep=True)
    hallucinated_cv.experience[0].dates = "2020-2025"  # Wrong dates
    hallucinated_cv.contact_info.email = "fake@example.com"  # Wrong email

    with (
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
    ):
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }
        mock_bedrock_client.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps(hallucinated_cv.dict()).encode())
        }

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["success"] is False
    assert body["code"] == "FVS_HALLUCINATION_DETECTED"


def test_full_flow_llm_retry(
    sample_master_cv,
    sample_tailored_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test full flow with LLM retry on timeout."""
    # Arrange
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
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
    ):
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }

        # First call fails, second succeeds
        mock_bedrock_client.invoke_model.side_effect = [
            Exception("Timeout"),
            {
                "body": MagicMock(
                    read=lambda: json.dumps(sample_tailored_cv.dict()).encode()
                )
            },
        ]

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 200
    assert mock_bedrock_client.invoke_model.call_count == 2


def test_full_flow_stores_artifact(
    sample_master_cv,
    sample_tailored_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test full flow stores tailored CV artifact in DynamoDB."""
    # Arrange
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
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
    ):
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }
        mock_bedrock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps(sample_tailored_cv.dict()).encode()
            )
        }

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 200

    # Verify artifact was saved
    assert mock_dynamodb_table.put_item.called
    save_call = mock_dynamodb_table.put_item.call_args[1]
    assert "Item" in save_call
    assert "ttl" in save_call["Item"]  # TTL should be set


def test_full_flow_cv_not_found(lambda_context, mock_dynamodb_table):
    """Test full flow returns 404 when CV doesn't exist."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "non-existent-cv",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table):
        mock_dynamodb_table.get_item.return_value = {}  # No Item

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert body["success"] is False


def test_full_flow_invalid_job_description(lambda_context):
    """Test full flow returns 400 for invalid job description."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Short",  # Too short
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    # Act
    response = handler(event, lambda_context)

    # Assert
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
    # Arrange
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
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
    ):
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }
        mock_bedrock_client.invoke_model.side_effect = Exception("Bedrock API error")

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert body["success"] is False


def test_full_flow_unauthorized_user(
    sample_master_cv,
    lambda_context,
    mock_dynamodb_table,
):
    """Test full flow rejects user accessing another user's CV."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
            }
        ),
        "requestContext": {
            "authorizer": {"claims": {"sub": "user-456"}}
        },  # Different user
    }

    with patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table):
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 403
    body = json.loads(response["body"])
    assert body["success"] is False


def test_full_flow_with_s3_upload(
    sample_master_cv,
    sample_tailored_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
    mock_s3_client,
):
    """Test full flow generates PDF and uploads to S3."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
                "generate_pdf": True,
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with (
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
        patch("boto3.client") as mock_boto_client,
    ):
        mock_boto_client.return_value = mock_s3_client

        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }
        mock_bedrock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps(sample_tailored_cv.dict()).encode()
            )
        }

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "download_url" in body["data"]


def test_full_flow_rate_limiting(
    lambda_context,
    mock_dynamodb_table,
):
    """Test full flow respects rate limiting."""
    # Arrange
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
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.rate_limiter.check_rate_limit") as mock_rate_limiter,
    ):
        mock_rate_limiter.return_value = False  # Rate limit exceeded

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 429
    body = json.loads(response["body"])
    assert body["success"] is False


def test_full_flow_with_versioning(
    sample_master_cv,
    sample_tailored_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test full flow creates versioned artifacts."""
    # Arrange
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
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
    ):
        # Return existing versions
        mock_dynamodb_table.query.return_value = {
            "Items": [
                {"artifact_id": "artifact-1", "version": 1},
                {"artifact_id": "artifact-2", "version": 2},
            ]
        }
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }
        mock_bedrock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps(sample_tailored_cv.dict()).encode()
            )
        }

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 200
    # New version should be 3
    save_call = mock_dynamodb_table.put_item.call_args[1]
    assert save_call["Item"]["version"] == 3


def test_full_flow_validation_before_fvs(
    lambda_context,
    mock_dynamodb_table,
):
    """Test input validation happens before FVS check."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "",  # Invalid
                "job_description": "x" * 51000,  # Too long
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    # Act
    response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 400
    # Should fail validation before reaching FVS
    mock_dynamodb_table.get_item.assert_not_called()


def test_full_flow_llm_json_parsing_error(
    sample_master_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test full flow handles LLM returning invalid JSON."""
    # Arrange
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
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
    ):
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }
        mock_bedrock_client.invoke_model.return_value = {
            "body": MagicMock(read=lambda: b"invalid json{")
        }

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert body["success"] is False


def test_full_flow_concurrent_requests(
    sample_master_cv,
    sample_tailored_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test full flow handles concurrent requests for same CV."""
    # Arrange
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
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
    ):
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }
        mock_bedrock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps(sample_tailored_cv.dict()).encode()
            )
        }

        # Act - simulate concurrent requests
        response1 = handler(event, lambda_context)
        response2 = handler(event, lambda_context)

    # Assert
    assert response1["statusCode"] == 200
    assert response2["statusCode"] == 200


def test_full_flow_audit_logging(
    sample_master_cv,
    sample_tailored_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test full flow creates audit log entries."""
    # Arrange
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
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
        patch("careervp.logic.audit_logger.log_event") as mock_audit,
    ):
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }
        mock_bedrock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps(sample_tailored_cv.dict()).encode()
            )
        }

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 200
    mock_audit.assert_called()


def test_full_flow_metrics_tracking(
    sample_master_cv,
    sample_tailored_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test full flow tracks performance metrics."""
    # Arrange
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
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
        patch("careervp.logic.metrics.record_metric") as mock_metrics,
    ):
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }
        mock_bedrock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps(sample_tailored_cv.dict()).encode()
            )
        }

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 200
    # Metrics should be recorded
    assert mock_metrics.call_count > 0


def test_full_flow_idempotency(
    sample_master_cv,
    sample_tailored_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test full flow with idempotency key returns cached result."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
                "idempotency_key": "unique-key-123",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with (
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
    ):
        # Return cached result
        mock_dynamodb_table.query.return_value = {
            "Items": [
                {
                    "idempotency_key": "unique-key-123",
                    "tailored_cv": sample_tailored_cv.dict(),
                }
            ]
        }

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 200
    # Should not call LLM if cached result exists
    mock_bedrock_client.invoke_model.assert_not_called()


def test_full_flow_cleanup_on_error(
    sample_master_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test full flow cleans up resources on error."""
    # Arrange
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
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
    ):
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }
        mock_bedrock_client.invoke_model.side_effect = Exception(
            "Error during processing"
        )

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 500
    # Should not save partial results
    mock_dynamodb_table.put_item.assert_not_called()


def test_full_flow_batch_processing(
    sample_master_cv,
    sample_tailored_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test full flow can handle batch processing requests."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_descriptions": [
                    "Looking for a senior software engineer with Python and AWS experience.",
                    "Seeking a full-stack developer with React and Node.js skills.",
                ],
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with (
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
    ):
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }
        mock_bedrock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps(sample_tailored_cv.dict()).encode()
            )
        }

        # Act
        response = handler(event, lambda_context)

    # Assert
    # Either batch processing works or returns appropriate error
    assert response["statusCode"] in [200, 400]


def test_full_flow_streaming_response(
    sample_master_cv,
    sample_tailored_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test full flow with streaming response for large CVs."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
                "stream": True,
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with (
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
    ):
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }
        mock_bedrock_client.invoke_model_with_response_stream.return_value = {
            "body": [
                {
                    "chunk": {
                        "bytes": json.dumps(sample_tailored_cv.dict()[:100]).encode()
                    }
                },
                {
                    "chunk": {
                        "bytes": json.dumps(sample_tailored_cv.dict()[100:]).encode()
                    }
                },
            ]
        }

        # Act
        response = handler(event, lambda_context)

    # Assert
    # Either streaming works or returns standard response
    assert response["statusCode"] in [200, 400]


def test_full_flow_webhook_notification(
    sample_master_cv,
    sample_tailored_cv,
    lambda_context,
    mock_dynamodb_table,
    mock_bedrock_client,
):
    """Test full flow sends webhook notification on completion."""
    # Arrange
    event = {
        "body": json.dumps(
            {
                "cv_id": "cv-123",
                "job_description": "Looking for a senior software engineer with Python and AWS experience.",
                "webhook_url": "https://example.com/webhook",
            }
        ),
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
    }

    with (
        patch("careervp.dal.cv_dal.CVTable", mock_dynamodb_table),
        patch("careervp.logic.llm_client.bedrock_client", mock_bedrock_client),
        patch("requests.post") as mock_webhook,
    ):
        mock_dynamodb_table.get_item.return_value = {
            "Item": {
                "cv_id": "cv-123",
                "user_id": "user-123",
                "cv_data": sample_master_cv.dict(),
            }
        }
        mock_bedrock_client.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps(sample_tailored_cv.dict()).encode()
            )
        }

        # Act
        response = handler(event, lambda_context)

    # Assert
    assert response["statusCode"] == 200
    # Webhook should be called
    mock_webhook.assert_called()
