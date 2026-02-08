"""Lambda handler for CV tailoring requests."""

from __future__ import annotations

import json
import os
from datetime import datetime
from http import HTTPStatus
from typing import Any, cast

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.logic.cv_tailoring import tailor_cv
from careervp.logic.fvs_validator import create_fvs_baseline
from careervp.logic.utils.llm_client import LLMRouter, TaskMode
from careervp.models.cv import UserCV as DynamoUserCV
from careervp.models.cv_models import UserCV, Skill, SkillLevel
from careervp.models.cv_tailoring_models import TailorCVRequest, TailoringPreferences
from careervp.models.result import Result, ResultCode
from careervp.validation.cv_tailoring_validation import validate_job_description


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime and Pydantic objects."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, 'model_dump'):
            return obj.model_dump(mode='json')
        return super().default(obj)


logger: Any
try:
    from careervp.handlers.utils.observability import logger as powertools_logger

    logger = powertools_logger
except Exception:  # pragma: no cover - fallback for tests
    import logging

    logger = logging.getLogger(__name__)


class TailoringLLMClient:
    """Wrapper to adapt LLMRouter to the simple generate interface expected by cv_tailoring."""

    def __init__(self, router: LLMRouter | None = None) -> None:
        self._router = router or LLMRouter()

    def generate(self, prompt: str, timeout: int = 300) -> dict[str, Any]:
        """Call LLMRouter with TEMPLATE mode (Haiku) for CV tailoring."""
        result = self._router.invoke(
            mode=TaskMode.TEMPLATE,
            system_prompt='You are an expert CV writer. Output valid JSON only.',
            user_prompt=prompt,
            max_tokens=4096,
            temperature=0.3,
        )
        if not result.success or result.data is None:
            raise Exception(result.error or 'LLM invocation failed')
        return result.data


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: C901
    """Handle CV tailoring request."""
    headers = _cors_headers()

    try:
        body = json.loads(event.get('body') or '{}')
    except json.JSONDecodeError:
        return _response(
            HTTPStatus.BAD_REQUEST,
            {
                'success': False,
                'code': ResultCode.INVALID_JSON,
                'message': 'Request body contains invalid JSON',
            },
            headers,
        )

    user_id = _get_user_id(event)
    if not user_id:
        return _response(
            HTTPStatus.UNAUTHORIZED,
            {
                'success': False,
                'code': ResultCode.UNAUTHORIZED,
                'message': 'Missing or invalid authentication token',
            },
            headers,
        )

    if 'preferences' in body and not isinstance(body['preferences'], dict):
        return _response(
            HTTPStatus.BAD_REQUEST,
            {
                'success': False,
                'code': ResultCode.VALIDATION_ERROR,
                'message': 'preferences must be an object',
            },
            headers,
        )

    cv_id = body.get('cv_id')
    job_description = body.get('job_description')

    validation_errors = []
    if not cv_id:
        validation_errors.append({'field': 'cv_id', 'message': 'cv_id is required'})
    if job_description is None:
        validation_errors.append({'field': 'job_description', 'message': 'job_description is required'})

    if job_description is not None:
        job_result = validate_job_description(job_description)
        if not job_result.success:
            validation_errors.append(
                {
                    'field': 'job_description',
                    'message': f'job_description: {job_result.message}',
                }
            )

    if validation_errors:
        message = ', '.join(err['message'] for err in validation_errors)
        return _response(
            HTTPStatus.BAD_REQUEST,
            {
                'success': False,
                'code': ResultCode.VALIDATION_ERROR,
                'message': message,
                'errors': validation_errors,
            },
            headers,
        )

    preferences = None
    if isinstance(body.get('preferences'), dict):
        preferences = TailoringPreferences(**body['preferences'])

    request = TailorCVRequest(
        cv_id=cv_id,
        job_description=job_description,
        user_id=user_id,
        preferences=preferences,
    )

    try:
        result = _fetch_and_tailor_cv(request)
    except Exception as exc:  # noqa: BLE001
        logger.info('CV tailoring failed', request_id=context.aws_request_id)
        return _response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {
                'success': False,
                'code': ResultCode.INTERNAL_ERROR,
                'message': str(exc),
            },
            headers,
        )

    status_code = _status_from_code(result.code)
    if result.success:
        data = _build_success_data(result.data)
        body = {
            'success': True,
            'code': result.code,
            'message': None,
            'data': data,
        }
    else:
        body = {
            'success': False,
            'code': result.code,
            'message': result.message,
            'data': _serialize_result_data(result.data) if result.data is not None else None,
        }

    logger.info('CV tailoring handled', request_id=context.aws_request_id)
    return _response(status_code, body, headers)


def _convert_cv(dynamo_cv: DynamoUserCV) -> UserCV:
    """Convert from DynamoDB UserCV to tailoring UserCV model."""
    # Convert skills from strings to Skill objects if needed
    skills = []
    for skill in dynamo_cv.skills:
        if isinstance(skill, str):
            # Assume basic proficiency for converted skills
            skills.append(Skill(name=skill, level=SkillLevel.INTERMEDIATE))
        else:
            skills.append(skill)

    # Convert experience - build description from achievements
    experience = []
    for exp in dynamo_cv.experience:
        dates = exp.dates.split(' – ') if ' – ' in exp.dates else [exp.dates, None]
        achievements = exp.achievements or []
        # Build description from role and achievements
        description = f'{exp.role} at {exp.company}'
        if achievements:
            description += '. ' + '; '.join(achievements[:3])
        experience.append(
            {
                'company': exp.company,
                'role': exp.role,
                'start_date': dates[0] or '',
                'end_date': dates[1],
                'current': 'Present' in (dates[1] or ''),
                'description': description,
                'achievements': achievements,
            }
        )

    return UserCV(
        cv_id=dynamo_cv.user_id,
        user_id=dynamo_cv.user_id,
        full_name=dynamo_cv.full_name,
        email=dynamo_cv.contact_info.email or '',
        phone=dynamo_cv.contact_info.phone,
        location=dynamo_cv.contact_info.location,
        professional_summary=dynamo_cv.professional_summary,
        work_experience=experience,  # type: ignore
        education=[
            {
                'institution': edu.institution,
                'degree': edu.degree,
                'field_of_study': edu.field_of_study,
                'start_date': edu.graduation_date or '',
                'end_date': edu.graduation_date,
                'description': f'{edu.degree} at {edu.institution}',
            }
            for edu in dynamo_cv.education
        ],
        skills=skills,
        certifications=[
            {
                'name': cert.name,
                'issuer': cert.issuer,
                'date': cert.date,
            }
            for cert in dynamo_cv.certifications
        ],
    )


def _fetch_and_tailor_cv(request: TailorCVRequest) -> Result[Any]:
    """Fetch CV from DAL and invoke tailoring logic."""
    # Use TABLE_NAME environment variable (passed by CDK) or fallback to cv-table
    table_name = os.environ.get('TABLE_NAME', 'cv-table')
    dal = DynamoDalHandler(table_name=table_name)
    llm_client = TailoringLLMClient()

    # Get CV by user_id using the correct DynamoDB key schema (pk=user_id, sk='CV')
    dynamo_cv = dal.get_cv(request.user_id)
    if not dynamo_cv:
        return Result(
            success=False,
            error=f"CV for user '{request.user_id}' not found",
            code=ResultCode.CV_NOT_FOUND,
        )

    # Convert to tailoring UserCV model
    master_cv = _convert_cv(dynamo_cv)
    baseline = create_fvs_baseline(master_cv)

    return tailor_cv(
        master_cv=master_cv,
        job_description=request.job_description,
        preferences=request.preferences,
        fvs_baseline=baseline,
        dal=dal,
        llm_client=llm_client,
    )


def _get_user_id(event: dict[str, Any]) -> str | None:
    # Try to get user_id from Cognito authorizer claims first
    user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub')
    if user_id:
        return cast(str | None, user_id)

    # For testing: allow user_id in request body if no authorizer
    # This bypass is only active when AUTHORIZER_DISABLED env var is set
    if os.environ.get('AUTHORIZER_DISABLED') == 'true':
        body = event.get('body') or '{}'
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                pass
        if isinstance(body, dict):
            return body.get('user_id')

    return cast(str | None, user_id)


def _status_from_code(code: str) -> int:
    mapping = {
        ResultCode.SUCCESS: HTTPStatus.OK,
        ResultCode.CV_TAILORED_SUCCESS: HTTPStatus.OK,
        ResultCode.CV_NOT_FOUND: HTTPStatus.NOT_FOUND,
        ResultCode.FVS_HALLUCINATION_DETECTED: HTTPStatus.BAD_REQUEST,
        ResultCode.FVS_VIOLATION_DETECTED: HTTPStatus.BAD_REQUEST,
        ResultCode.LLM_TIMEOUT: HTTPStatus.GATEWAY_TIMEOUT,
        ResultCode.RATE_LIMIT_EXCEEDED: HTTPStatus.TOO_MANY_REQUESTS,
        ResultCode.FORBIDDEN: HTTPStatus.FORBIDDEN,
        ResultCode.UNAUTHORIZED: HTTPStatus.UNAUTHORIZED,
        ResultCode.VALIDATION_ERROR: HTTPStatus.BAD_REQUEST,
    }
    return int(mapping.get(code, HTTPStatus.INTERNAL_SERVER_ERROR).value)


def _serialize_result_data(data: Any) -> Any:
    """Serialize result data, handling datetime objects."""
    if data is None:
        return None
    if hasattr(data, 'model_dump'):
        # Use json serialization mode to handle datetime
        try:
            return data.model_dump(mode='json')
        except (TypeError, ValueError):
            # Fallback to default serialization
            return data.model_dump()
    return data


def _build_success_data(data: Any) -> dict[str, Any]:
    """Build success response data, handling datetime serialization."""
    if data is None:
        return {'tailored_cv': None}
    if isinstance(data, dict):
        if 'tailored_cv' in data:
            serialized = _serialize_result_data(data)
            return dict(serialized) if isinstance(serialized, dict) else {'tailored_cv': serialized}
        return {'tailored_cv': _serialize_result_data(data)}
    if hasattr(data, 'tailored_cv'):
        # TailoredCVResponse object
        serialized = _serialize_result_data(data)
        if isinstance(serialized, dict) and 'tailored_cv' in serialized:
            return serialized
        return {'tailored_cv': serialized}
    if hasattr(data, 'model_dump'):
        # TailoredCV or similar Pydantic model
        return {'tailored_cv': _serialize_result_data(data)}
    return {'tailored_cv': data}


def _cors_headers() -> dict[str, str]:
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    }


def _response(status: int | HTTPStatus, body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    status_code = int(status.value) if isinstance(status, HTTPStatus) else int(status)
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body, cls=CustomJSONEncoder),
    }
