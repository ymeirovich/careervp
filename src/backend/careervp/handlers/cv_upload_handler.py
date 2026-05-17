"""
CV Upload Handler.
Per CLAUDE.md: Handler -> Logic -> DAL pattern.

Handles CV upload requests, orchestrates parsing and storage.
"""

import base64
import json
import os
import time
import uuid
from http import HTTPStatus
from typing import Any

import boto3
from aws_lambda_env_modeler import get_environment_variables
from aws_lambda_powertools.event_handler import (
    Response,
    content_types,
)
from aws_lambda_powertools.logging.correlation_paths import API_GATEWAY_REST
from aws_lambda_powertools.utilities.parser import ValidationError, parse
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from pydantic import ValidationError as PydanticValidationError

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.handlers.auth_utils import extract_user_id
from careervp.handlers.cors_utils import get_cors_headers, set_request_origin
from careervp.handlers.models.env_vars import CVUploadEnvVars
from careervp.handlers.utils.observability import logger, tracer
from careervp.handlers.utils.rest_api_resolver import app
from careervp.logic.cv_parser import create_cv_parse_response, parse_cv
from careervp.models.api_models import CVUploadRequest
from careervp.models.cv import CVParseRequest, CVParseResponse
from careervp.models.result import ResultCode


def _get_s3_client() -> BaseClient:
    """Get S3 client (separated for testability)."""
    return boto3.client('s3')


@app.post('/users/me/cv')
@tracer.capture_method(capture_response=False)
def upload_cv() -> Response[str]:  # noqa: C901
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
        body = _normalize_request_payload(app.current_event.json_body)
        request = parse(event=body, model=CVParseRequest)
    except (ValidationError, PydanticValidationError, ValueError, TypeError, json.JSONDecodeError) as e:
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

    if not parse_result.success or parse_result.data is None:
        error_message = parse_result.error or 'Failed to parse CV contents'
        logger.warning('CV parsing failed', error=error_message, code=parse_result.code)
        response = CVParseResponse(
            success=False,
            error=error_message,
            parse_time_ms=int((time.time() - start_time) * 1000),
        )
        status_code = _get_status_code_for_result_code(parse_result.code) if not parse_result.success else HTTPStatus.INTERNAL_SERVER_ERROR.value
        return Response(
            status_code=status_code,
            content_type=content_types.APPLICATION_JSON,
            body=response.model_dump_json(),
        )

    # Set S3 key and label on parsed CV
    user_cv = parse_result.data
    if s3_key:
        user_cv.source_file_key = s3_key

    raw_file_name = body.get('_file_name') or body.get('file_name') or ''
    if raw_file_name:
        user_cv.label = os.path.splitext(os.path.basename(raw_file_name))[0]

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

    parsed_data = _build_openapi_parsed_data(response)
    cv_id = None
    if response.user_cv is not None and isinstance(response.user_cv.cv_id, str):
        cv_id = response.user_cv.cv_id
    if not cv_id:
        cv_id = str(uuid.uuid4())

    return Response(
        status_code=HTTPStatus.CREATED.value,
        content_type=content_types.APPLICATION_JSON,
        body=json.dumps(
            {
                **response.model_dump(mode='json'),
                'cv_id': cv_id,
                'status': 'parsed',
                'parsed_data': parsed_data,
            },
            default=str,
        ),
    )


def _get_content_type(file_type: str | None) -> str:
    """Get MIME content type for file type."""
    content_types_map = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'txt': 'text/plain',
    }
    if file_type is None:
        return 'application/octet-stream'
    return content_types_map.get(file_type, 'application/octet-stream')


def _normalize_request_payload(body: Any) -> dict[str, Any]:
    """
    Normalize request payload to legacy CVParseRequest shape.

    Supports both:
    - Legacy request: {request_user, file_content|text_content, file_type}
    - OpenAPI request: {cv_content, file_name}
    """
    if not isinstance(body, dict):
        raise TypeError('Request body must be a JSON object')

    # OpenAPI request shape
    if {'cv_content', 'file_name'}.issubset(body):
        openapi_request = CVUploadRequest.model_validate(body)
        user_id = _extract_user_id()
        if not user_id:
            raise ValueError('Authenticated user_id is required for /users/me/cv')
        return {
            'user_id': user_id,
            'text_content': openapi_request.cv_content,
            '_file_name': openapi_request.file_name,
        }

    return body


def _extract_user_id() -> str | None:
    # Try raw_event first (contains original event dict)
    raw_event = getattr(app.current_event, 'raw_event', None)
    if isinstance(raw_event, dict):
        user_id = extract_user_id(raw_event)
        if user_id:
            return user_id

    # Fallback: try request_context (Powertools object)
    request_context = app.current_event.request_context
    if isinstance(request_context, dict):
        return extract_user_id({'requestContext': request_context})

    # Convert Powertools object to dict
    rc_dict = dict(request_context)
    return extract_user_id({'requestContext': rc_dict})


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


def _build_openapi_parsed_data(response: CVParseResponse) -> dict[str, Any]:
    user_cv = response.user_cv
    if user_cv is None:
        return {
            'name': '',
            'title': '',
            'experience': [],
            'skills': [],
            'education': [],
        }

    name = user_cv.full_name
    title = ''
    experience: list[dict[str, Any]] = []
    for idx, item in enumerate(user_cv.experience):
        if idx == 0 and isinstance(item.role, str):
            title = item.role
        experience.append(
            {
                'company': item.company,
                'role': item.role,
                'duration': item.dates or '',
                'achievements': item.achievements or [],
            }
        )

    skills = []
    for skill in user_cv.skills:
        if isinstance(skill, str):
            skills.append(skill)
        elif hasattr(skill, 'name'):
            skill_name = getattr(skill, 'name', '')
            if isinstance(skill_name, str) and skill_name:
                skills.append(skill_name)

    education: list[dict[str, Any]] = []
    for education_item in user_cv.education:
        year = education_item.graduation_date or education_item.end_date or education_item.dates or ''
        education.append(
            {
                'degree': education_item.degree,
                'institution': education_item.institution,
                'year': year,
            }
        )

    return {
        'name': name,
        'title': title,
        'experience': experience,
        'skills': skills,
        'education': education,
    }


@logger.inject_lambda_context(correlation_id_path=API_GATEWAY_REST)
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Lambda entry point for CV upload."""
    set_request_origin(event)
    response: dict[str, Any] = app.resolve(event, context)
    cors = get_cors_headers(None)
    if cors:
        headers: dict[str, str] = response.get('headers') or {}
        headers.update(cors)
        response['headers'] = headers
    return response
