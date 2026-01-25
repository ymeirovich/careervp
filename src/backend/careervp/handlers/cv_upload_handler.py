"""
CV Upload Handler.
Per CLAUDE.md: Handler -> Logic -> DAL pattern.

Handles CV upload requests, orchestrates parsing and storage.
"""

import base64
import json
import time
import uuid
from http import HTTPStatus

import boto3
from aws_lambda_env_modeler import get_environment_variables
from aws_lambda_powertools.event_handler import (
    APIGatewayRestResolver,
    Response,
    content_types,
)
from aws_lambda_powertools.logging.correlation_paths import API_GATEWAY_REST
from aws_lambda_powertools.utilities.parser import ValidationError, parse
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.models.env_vars import CVUploadEnvVars
from careervp.handlers.utils.observability import logger, tracer
from careervp.logic.cv_parser import create_cv_parse_response, parse_cv
from careervp.models.cv import CVParseRequest, CVParseResponse
from careervp.models.result import ResultCode

app = APIGatewayRestResolver()


def _get_s3_client():
    """Get S3 client (separated for testability)."""
    return boto3.client('s3')


@app.post('/api/cv')
@tracer.capture_method(capture_response=False)
def upload_cv() -> Response:
    """
    Handle CV upload and parsing request.

    Flow per docs/specs/01-cv-parser.md:
    1. Validate request
    2. Store raw CV in S3
    3. Parse CV using cv_parser
    4. Store parsed CV in DynamoDB
    5. Return CVParseResponse
    """
    start_time = time.time()

    # Get environment variables
    env_vars = get_environment_variables(model=CVUploadEnvVars)

    # Parse and validate request
    try:
        body = app.current_event.json_body
        request = parse(event=body, model=CVParseRequest)
    except (ValidationError, TypeError, json.JSONDecodeError) as e:
        logger.warning('Invalid request body', error=str(e))
        response = CVParseResponse(
            success=False,
            error=f'Invalid request: {e}',
        )
        return Response(
            status_code=HTTPStatus.BAD_REQUEST.value,
            content_type=content_types.APPLICATION_JSON,
            body=response.model_dump_json(),
        )

    logger.append_keys(user_id=request.user_id)
    logger.info('Processing CV upload request', has_file=bool(request.file_content), has_text=bool(request.text_content))

    # Validate that content is provided
    if not request.file_content and not request.text_content:
        response = CVParseResponse(
            success=False,
            error='Either file_content or text_content must be provided',
        )
        return Response(
            status_code=HTTPStatus.BAD_REQUEST.value,
            content_type=content_types.APPLICATION_JSON,
            body=response.model_dump_json(),
        )

    # If file_content, validate file_type
    if request.file_content and not request.file_type:
        response = CVParseResponse(
            success=False,
            error='file_type is required when file_content is provided',
        )
        return Response(
            status_code=HTTPStatus.BAD_REQUEST.value,
            content_type=content_types.APPLICATION_JSON,
            body=response.model_dump_json(),
        )

    # Prepare content for parsing
    cv_content: bytes | None = None
    cv_text: str | None = None
    s3_key: str | None = None

    if request.file_content:
        # Decode base64 file content
        try:
            cv_content = base64.b64decode(request.file_content)
        except Exception as e:
            logger.warning('Failed to decode base64 content', error=str(e))
            response = CVParseResponse(
                success=False,
                error='Invalid base64 file content',
            )
            return Response(
                status_code=HTTPStatus.BAD_REQUEST.value,
                content_type=content_types.APPLICATION_JSON,
                body=response.model_dump_json(),
            )

        # Upload raw CV to S3
        s3_key = f'{request.user_id}/{uuid.uuid4()}.{request.file_type}'
        try:
            s3_client = _get_s3_client()
            s3_client.put_object(
                Bucket=env_vars.CV_BUCKET_NAME,
                Key=s3_key,
                Body=cv_content,
                ContentType=_get_content_type(request.file_type),
            )
            logger.info('CV uploaded to S3', s3_key=s3_key)
        except ClientError as e:
            logger.exception('Failed to upload CV to S3', error=str(e))
            response = CVParseResponse(
                success=False,
                error='Failed to store CV file',
            )
            return Response(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
                content_type=content_types.APPLICATION_JSON,
                body=response.model_dump_json(),
            )
    else:
        cv_text = request.text_content

    # Parse CV using logic layer
    parse_result = parse_cv(
        user_id=request.user_id,
        cv_text=cv_text,
        cv_content=cv_content,
        file_type=request.file_type,
    )

    if not parse_result.success:
        logger.warning('CV parsing failed', error=parse_result.error, code=parse_result.code)
        response = CVParseResponse(
            success=False,
            error=parse_result.error,
            parse_time_ms=int((time.time() - start_time) * 1000),
        )
        status_code = _get_status_code_for_result_code(parse_result.code)
        return Response(
            status_code=status_code,
            content_type=content_types.APPLICATION_JSON,
            body=response.model_dump_json(),
        )

    # Set S3 key on parsed CV
    user_cv = parse_result.data
    if s3_key and user_cv:
        user_cv.source_file_key = s3_key

    # Store parsed CV in DynamoDB
    try:
        dal = DynamoDalHandler(table_name=env_vars.TABLE_NAME)
        dal.save_cv(user_cv)
        logger.info('CV saved to DynamoDB')
    except Exception as e:
        logger.exception('Failed to save CV to DynamoDB', error=str(e))
        response = CVParseResponse(
            success=False,
            error='Failed to persist parsed CV',
        )
        return Response(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            content_type=content_types.APPLICATION_JSON,
            body=response.model_dump_json(),
        )

    # Build success response
    parse_time_ms = int((time.time() - start_time) * 1000)
    response = create_cv_parse_response(parse_result)
    response.parse_time_ms = parse_time_ms

    logger.info('CV upload completed successfully', parse_time_ms=parse_time_ms)

    return Response(
        status_code=HTTPStatus.OK.value,
        content_type=content_types.APPLICATION_JSON,
        body=response.model_dump_json(),
    )


def _get_content_type(file_type: str) -> str:
    """Get MIME content type for file type."""
    content_types_map = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'txt': 'text/plain',
    }
    return content_types_map.get(file_type, 'application/octet-stream')


def _get_status_code_for_result_code(code: str) -> int:
    """Map result codes to HTTP status codes."""
    error_mapping = {
        ResultCode.INVALID_INPUT: HTTPStatus.BAD_REQUEST.value,
        ResultCode.MISSING_REQUIRED_FIELD: HTTPStatus.BAD_REQUEST.value,
        ResultCode.UNSUPPORTED_FILE_FORMAT: HTTPStatus.BAD_REQUEST.value,
        ResultCode.LLM_RATE_LIMITED: HTTPStatus.TOO_MANY_REQUESTS.value,
        ResultCode.LLM_TIMEOUT: HTTPStatus.GATEWAY_TIMEOUT.value,
    }
    return error_mapping.get(code, HTTPStatus.INTERNAL_SERVER_ERROR.value)


@logger.inject_lambda_context(correlation_id_path=API_GATEWAY_REST)
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """Lambda entry point for CV upload."""
    return app.resolve(event, context)
