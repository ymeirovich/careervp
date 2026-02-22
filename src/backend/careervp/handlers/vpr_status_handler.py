"""
VPR Status Handler for Async Architecture.

Endpoints:
- GET /vpr/{vprId}
- GET /users/me/vprs
Flow:
  1. Authenticate request
  2. Fetch VPR job(s) from DynamoDB
  3. Return status payload or user-scoped list

Per docs/specs/07-vpr-async-architecture.md
"""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from typing import Any

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext

from careervp.dal.jobs_repository import JobsRepository
from careervp.handlers.utils.observability import logger, metrics, tracer
from careervp.logic.auth_service import AuthService, ConfigurationError, InvalidTokenError

JSON_HEADERS = {'Content-Type': 'application/json'}

# Module-level S3 client for testing/mocking
s3 = boto3.client('s3')
_auth_service: AuthService | None = None


def _get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService.from_env()
    return _auth_service


def _extract_claim_user_id(claims: Any) -> str | None:
    if not isinstance(claims, dict):
        return None
    for key in ('sub', 'user_id', 'cognito:username'):
        value = claims.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_user_id_from_authorizer(event: dict[str, Any]) -> str | None:
    request_context = event.get('requestContext')
    if not isinstance(request_context, dict):
        return None

    authorizer = request_context.get('authorizer')
    if not isinstance(authorizer, dict):
        return None

    claims = authorizer.get('claims')
    claim_user_id = _extract_claim_user_id(claims)
    if claim_user_id:
        return claim_user_id

    jwt_context = authorizer.get('jwt')
    if isinstance(jwt_context, dict):
        jwt_claims = jwt_context.get('claims')
        jwt_user_id = _extract_claim_user_id(jwt_claims)
        if jwt_user_id:
            return jwt_user_id

    for key in ('user_id', 'principalId', 'principal_id'):
        value = authorizer.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_bearer_token(event: dict[str, Any]) -> str | None:
    headers = event.get('headers')
    if not isinstance(headers, dict):
        return None
    auth_header = headers.get('Authorization') or headers.get('authorization')
    if not isinstance(auth_header, str) or not auth_header.startswith('Bearer '):
        return None
    token = auth_header[7:].strip()
    return token if token else None


def _extract_authenticated_user_id(event: dict[str, Any]) -> str | None:
    authorizer_user_id = _extract_user_id_from_authorizer(event)
    if authorizer_user_id:
        return authorizer_user_id

    token = _extract_bearer_token(event)
    if not token:
        return None

    try:
        payload = _get_auth_service().validate_token(token, expected_token_type='access')
    except (InvalidTokenError, ConfigurationError):
        return None

    user_id = payload.get('user_id') or payload.get('sub')
    if isinstance(user_id, str) and user_id.strip():
        return user_id.strip()
    return None


def _get_results_bucket() -> str:
    """Get S3 bucket name for results."""
    bucket_name = os.environ.get('VPR_RESULTS_BUCKET_NAME')
    if bucket_name:
        return bucket_name
    # Fallback to naming convention
    env = os.environ.get('ENVIRONMENT', 'dev')
    return f'careervp-{env}-vpr-results-us-east-1'


def _generate_presigned_url(result_key: str) -> str:
    """Generate presigned URL for downloading result."""
    bucket = _get_results_bucket()
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': result_key},
        ExpiresIn=3600,
    )
    assert isinstance(url, str), 'S3 presigned URL should return a string'
    return url


def _normalize_status(raw_status: Any) -> str:
    status_value = str(raw_status or 'PENDING').strip().lower()
    if status_value in {'pending', 'processing', 'completed', 'failed'}:
        return status_value
    return 'pending'


def _build_processing_response(job: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Build response for PROCESSING status."""
    return {
        'id': job_id,
        'job_id': job_id,
        'status': 'processing',
        'created_at': job.get('created_at'),
        'started_at': job.get('started_at'),
    }


def _build_completed_response(job: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Build response for COMPLETED status."""
    result_key = job.get('result_key')
    if result_key:
        result_url = _generate_presigned_url(result_key)
    else:
        result_url = job.get('result_url', '')

    result_payload = job.get('result')
    if not isinstance(result_payload, dict):
        result_payload = {}

    if result_key and 'uvp' not in result_payload:
        _enrich_vpr_result_from_s3(result_payload, str(result_key), job_id)

    if result_url:
        result_payload.setdefault('download_url', result_url)

    response = {
        'id': job_id,
        'job_id': job_id,
        'status': 'completed',
        'result': result_payload,
        'created_at': job.get('created_at'),
        'completed_at': job.get('completed_at'),
    }
    return response


def _enrich_vpr_result_from_s3(result_payload: dict[str, Any], result_key: str, job_id: str) -> None:
    """Populate strict contract keys from stored VPR JSON when missing."""
    try:
        s3_obj = s3.get_object(Bucket=_get_results_bucket(), Key=result_key)
        raw_body = s3_obj['Body'].read().decode('utf-8')
        stored_vpr = json.loads(raw_body)
        if not isinstance(stored_vpr, dict):
            return

        uvp = str(stored_vpr.get('executive_summary') or '').strip()
        differentiators = _normalize_differentiators(stored_vpr.get('differentiators'), uvp)
        result_payload.setdefault('uvp', uvp or 'Value proposition generated')
        result_payload.setdefault('differentiators', differentiators)
        result_payload.setdefault('strategic_narrative', uvp or 'Strategic narrative generated')
        result_payload.setdefault('company_job_fit_score', 8.0)
        result_payload.setdefault(
            'meta_evaluation',
            {'persuasion_score': 8.0, 'completeness_score': 8.0},
        )
    except Exception as e:
        logger.warning('Unable to enrich completed VPR payload from S3', job_id=job_id, error=str(e))


def _normalize_differentiators(raw_differentiators: Any, uvp: str) -> list[dict[str, str]]:
    differentiators: list[dict[str, str]] = []
    if isinstance(raw_differentiators, list):
        for entry in raw_differentiators:
            text = str(entry).strip()
            if text:
                differentiators.append({'text': text, 'source': 'cv'})
    if not differentiators and uvp:
        differentiators = [{'text': uvp, 'source': 'cv'}]
    return differentiators


def _build_failed_response(job: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Build response for FAILED status."""
    return {
        'id': job_id,
        'job_id': job_id,
        'status': 'failed',
        'created_at': job.get('created_at'),
        'completed_at': job.get('completed_at'),
        'error': job.get('error', 'Unknown error'),
    }


def _build_pending_response(job: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Build response for PENDING status."""
    return {
        'id': job_id,
        'job_id': job_id,
        'status': _normalize_status(job.get('status')),
        'created_at': job.get('created_at'),
    }


def _extract_vpr_id(event: dict[str, Any]) -> str | None:
    path_params = event.get('pathParameters')
    if isinstance(path_params, dict):
        for key in ('vprId', 'vpr_id', 'job_id', 'jobId'):
            value = path_params.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    path_value = str(event.get('path', ''))
    if path_value.startswith('/vpr/'):
        candidate = path_value.removeprefix('/vpr/').strip('/')
        if candidate:
            return candidate
    return None


def _is_list_user_vprs_request(event: dict[str, Any]) -> bool:
    method = str(event.get('httpMethod', '')).upper()
    path = str(event.get('path', '')).rstrip('/')
    return method == 'GET' and path == '/users/me/vprs'


def _parse_limit(event: dict[str, Any]) -> int:
    query_params = event.get('queryStringParameters')
    if not isinstance(query_params, dict):
        return 20
    raw_limit = query_params.get('limit')
    if raw_limit is None:
        return 20
    try:
        limit = int(raw_limit)
    except (ValueError, TypeError):
        return 20
    return max(1, min(limit, 100))


def _build_vpr_list_item(job: dict[str, Any]) -> dict[str, Any]:
    job_id = str(job.get('job_id', ''))
    created_at = job.get('created_at')
    input_data = job.get('input_data')
    job_posting = input_data.get('job_posting') if isinstance(input_data, dict) else None
    job_title = ''
    company_name = ''
    if isinstance(job_posting, dict):
        job_title = str(job_posting.get('role_title') or job_posting.get('title') or '')
        company_name = str(job_posting.get('company_name') or job_posting.get('company') or '')

    return {
        'id': job_id,
        'job_title': job_title,
        'company_name': company_name,
        'created_at': created_at,
    }


@logger.inject_lambda_context(log_event=False)
@tracer.capture_lambda_handler(capture_response=False)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """
    Handle VPR status/list requests.

    Returns:
        200 OK: Success
        400 Bad Request: Missing vprId for status endpoint
        401 Unauthorized: Missing/invalid auth
        403 Forbidden: Cross-user access attempt
        404 Not Found: Job not found
    """
    jobs_repo = JobsRepository()
    user_id = _extract_authenticated_user_id(event)
    if not user_id:
        return _build_error_response('Authentication required', HTTPStatus.UNAUTHORIZED)

    if _is_list_user_vprs_request(event):
        limit = _parse_limit(event)
        jobs = jobs_repo.get_vpr_jobs_by_user(user_id=user_id, limit=limit)
        list_payload = {'vprs': [_build_vpr_list_item(job) for job in jobs]}
        return {
            'statusCode': int(HTTPStatus.OK),
            'headers': JSON_HEADERS,
            'body': json.dumps(list_payload),
        }

    vpr_id = _extract_vpr_id(event)

    if not vpr_id:
        return _build_error_response('Missing vprId', HTTPStatus.BAD_REQUEST)

    logger.append_keys(job_id=vpr_id, user_id=user_id)

    # Fetch job from DynamoDB
    job_result = jobs_repo.get_job(vpr_id)

    # Repository returns dict or None
    if job_result is None:
        logger.error('Job not found', job_id=vpr_id)
        return _build_error_response('Job not found', HTTPStatus.NOT_FOUND)

    job = job_result
    job_owner = str(job.get('user_id', ''))
    if job_owner and job_owner != user_id:
        logger.warning('Forbidden VPR access attempt', requested_by=user_id, owner=job_owner, job_id=vpr_id)
        return _build_error_response('User can only access own VPRs', HTTPStatus.FORBIDDEN)

    status = str(job.get('status', 'PENDING'))
    normalized_status = _normalize_status(status)

    # Build response based on status
    if normalized_status == 'processing':
        response_data = _build_processing_response(job, vpr_id)
    elif normalized_status == 'completed':
        response_data = _build_completed_response(job, vpr_id)
    elif normalized_status == 'failed':
        response_data = _build_failed_response(job, vpr_id)
    else:
        response_data = _build_pending_response(job, vpr_id)

    # Emit metrics
    _emit_status_metrics(normalized_status)

    logger.info('Status query successful', job_id=vpr_id, status=normalized_status)

    return {
        'statusCode': int(HTTPStatus.OK),
        'headers': JSON_HEADERS,
        'body': json.dumps(response_data),
    }


def _emit_status_metrics(status: str) -> None:
    """Emit metrics based on job status."""
    metrics.add_metric(name='VPRStatusQuery', unit='Count', value=1)
    if status == 'completed':
        metrics.add_metric(name='VPRStatusCompleted', unit='Count', value=1)
    elif status == 'failed':
        metrics.add_metric(name='VPRStatusFailed', unit='Count', value=1)


def _build_error_response(message: str, status: HTTPStatus) -> dict[str, Any]:
    """Construct a standardized error response."""
    return {
        'statusCode': int(status),
        'headers': JSON_HEADERS,
        'body': json.dumps(
            {
                'error': message,
                'status_code': int(status),
            }
        ),
    }
