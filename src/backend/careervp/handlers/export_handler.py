"""
Lambda handler for the Export API endpoint.
Generates DOCX files from stored artifacts and returns presigned S3 download URLs.
Endpoint: GET /jobs/{jobId}/artifacts/{moduleType}/export?format=docx|pdf
"""

from __future__ import annotations

import io
import json
import os
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from typing import Any

import boto3
import botocore.exceptions
from docx import Document
from docx.document import Document as DocxDocument

from careervp.handlers.cors_utils import get_cors_headers, set_request_origin
from careervp.handlers.utils.observability import logger

INTERVIEW_PREP_SORT_KEY_PREFIX = 'ARTIFACT#INTERVIEW_PREP#'
VALID_MODULE_TYPES = frozenset({'vpr', 'cover_letter', 'interview_prep', 'cv_tailored'})
PRESIGNED_URL_TTL = 3600


class ArtifactNotFoundError(Exception):
    pass


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route export requests."""
    _ = context
    set_request_origin(event)
    method = str(event.get('httpMethod', 'GET')).upper()

    if method == 'OPTIONS':
        return _json_response(HTTPStatus.OK, {'status': 'ok'})

    if method == 'GET':
        return _handle_export(event)

    return _json_response(HTTPStatus.METHOD_NOT_ALLOWED, {'error': 'Method not allowed'})


def _handle_export(event: dict[str, Any]) -> dict[str, Any]:
    """Handle GET /jobs/{jobId}/artifacts/{moduleType}/export."""
    path_params = event.get('pathParameters') or {}
    job_id = str(path_params.get('jobId') or path_params.get('job_id') or '').strip()
    module_type = str(path_params.get('moduleType') or path_params.get('module_type') or '').strip()

    query_params = event.get('queryStringParameters') or {}
    export_format = str(query_params.get('format', '')).strip().lower()

    try:
        user_id = str(event['requestContext']['authorizer']['claims']['sub']).strip()
    except (KeyError, TypeError):
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Unauthorized'})

    if not user_id:
        return _json_response(HTTPStatus.UNAUTHORIZED, {'error': 'Unauthorized'})

    if export_format == 'pdf':
        return _json_response(
            HTTPStatus.NOT_IMPLEMENTED,
            {'message': 'PDF export is not yet available.'},
        )
    if export_format != 'docx':
        return _json_response(
            HTTPStatus.BAD_REQUEST,
            {'message': 'Unsupported format. Use docx.'},
        )

    if module_type not in VALID_MODULE_TYPES:
        return _json_response(
            HTTPStatus.BAD_REQUEST,
            {'message': 'Unsupported module type.'},
        )

    logger.info('Export requested', job_id=job_id, module_type=module_type, user_id=user_id)

    try:
        data = _read_artifact(module_type, job_id, user_id)
    except ArtifactNotFoundError:
        return _json_response(HTTPStatus.NOT_FOUND, {'message': 'Artifact not found.'})
    except Exception as exc:
        logger.error('Failed to read artifact', exc_info=exc)
        return _json_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {'message': 'Export failed. Please try again.'},
        )

    try:
        doc = _build_docx(module_type, data)
        artifacts_bucket = os.environ['ARTIFACTS_BUCKET_NAME']
        key = f'exports/{module_type}/{job_id}/{job_id}.docx'
        download_url, expires_at = _write_and_presign(artifacts_bucket, key, doc)
    except Exception as exc:
        logger.error('Failed to generate or upload export', exc_info=exc)
        return _json_response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {'message': 'Export failed. Please try again.'},
        )

    return _json_response(HTTPStatus.OK, {'download_url': download_url, 'expires_at': expires_at})


def _read_artifact(module_type: str, job_id: str, user_id: str) -> Any:
    if module_type == 'vpr':
        return _read_vpr(job_id)
    if module_type == 'cover_letter':
        return _read_cover_letter(job_id, user_id)
    if module_type == 'interview_prep':
        return _read_interview_prep(job_id, user_id)
    return _read_cv_tailored(job_id, user_id)


def _read_vpr(job_id: str) -> dict[str, Any]:
    s3 = boto3.client('s3')
    bucket = os.environ['VPR_RESULTS_BUCKET_NAME']
    key = f'results/{job_id}.json'
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        return dict(json.loads(response['Body'].read()))
    except botocore.exceptions.ClientError as exc:
        if exc.response['Error']['Code'] in ('NoSuchKey', '404'):
            raise ArtifactNotFoundError(f'VPR artifact not found: {job_id}') from exc
        raise


def _read_cover_letter(job_id: str, user_id: str) -> dict[str, Any]:
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['ARTIFACTS_TABLE_NAME'])
    response = table.get_item(Key={'applicationId': user_id, 'artifactId': job_id})
    item = response.get('Item')
    if not item:
        raise ArtifactNotFoundError(f'Cover letter artifact not found: {job_id}')
    return dict(item)


def _read_interview_prep(job_id: str, user_id: str) -> dict[str, Any]:
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['ARTIFACTS_TABLE_NAME'])
    artifact_id = f'{INTERVIEW_PREP_SORT_KEY_PREFIX}{job_id}'
    response = table.get_item(Key={'applicationId': user_id, 'artifactId': artifact_id})
    item = response.get('Item')
    if not item:
        raise ArtifactNotFoundError(f'Interview prep artifact not found: {job_id}')
    return dict(item)


def _read_cv_tailored(job_id: str, user_id: str) -> dict[str, Any]:
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['TABLE_NAME'])
    sk = f'ARTIFACT#CV_TAILORED#{job_id}'
    response = table.get_item(Key={'pk': user_id, 'sk': sk})
    item = response.get('Item')
    if not item:
        raise ArtifactNotFoundError(f'CV tailored artifact not found: {job_id}')
    return dict(item)


def _build_docx(module_type: str, data: Any) -> DocxDocument:
    doc = Document()
    builders = {
        'vpr': _fill_vpr,
        'cover_letter': _fill_cover_letter,
        'interview_prep': _fill_interview_prep,
        'cv_tailored': _fill_cv_tailored,
    }
    builders[module_type](doc, data)
    return doc


def _fill_vpr(doc: DocxDocument, data: Any) -> None:
    doc.add_heading('Value Proposition Report', 0)
    if not isinstance(data, dict):
        return
    for section_key, section_value in data.items():
        doc.add_heading(str(section_key).replace('_', ' ').title(), level=1)
        if isinstance(section_value, (dict, list)):
            doc.add_paragraph(json.dumps(section_value, indent=2, ensure_ascii=False))
        else:
            doc.add_paragraph(str(section_value))


def _fill_cover_letter(doc: DocxDocument, data: Any) -> None:
    doc.add_heading('Cover Letter', 0)
    cover_letter = data.get('cover_letter') or {} if isinstance(data, dict) else {}
    text = (cover_letter.get('full_text') or cover_letter.get('text') or '') if isinstance(cover_letter, dict) else ''
    doc.add_paragraph(str(text))


def _fill_interview_prep(doc: DocxDocument, data: Any) -> None:
    doc.add_heading('Interview Preparation', 0)
    prep = data.get('interview_prep') or {} if isinstance(data, dict) else {}
    questions = prep.get('questions') or [] if isinstance(prep, dict) else []
    for i, qa in enumerate(questions, start=1):
        if isinstance(qa, dict):
            doc.add_paragraph(f'{i}. Q: {qa.get("question", "")}')
            doc.add_paragraph(f'   A: {qa.get("answer", "")}')
        else:
            doc.add_paragraph(f'{i}. {qa}')


def _fill_cv_tailored(doc: DocxDocument, data: Any) -> None:
    doc.add_heading('Tailored CV', 0)
    cv_sections = data.get('cv_sections') or {} if isinstance(data, dict) else {}
    if isinstance(cv_sections, dict):
        for section_key, section_value in cv_sections.items():
            doc.add_heading(str(section_key).replace('_', ' ').title(), level=1)
            doc.add_paragraph('\n'.join(str(v) for v in section_value) if isinstance(section_value, list) else str(section_value))
    elif isinstance(cv_sections, list):
        for section in cv_sections:
            if isinstance(section, dict):
                title = section.get('title') or section.get('name') or ''
                content = section.get('content') or section.get('text') or ''
                if title:
                    doc.add_heading(str(title), level=1)
                doc.add_paragraph(str(content))
    tailored_cv = data.get('tailored_cv') or '' if isinstance(data, dict) else ''
    if tailored_cv:
        doc.add_heading('Summary', level=1)
        doc.add_paragraph(str(tailored_cv))


def _write_and_presign(bucket: str, key: str, doc: DocxDocument) -> tuple[str, str]:
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    s3 = boto3.client('s3')
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=buffer.getvalue(),
        ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    )

    download_url: str = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=PRESIGNED_URL_TTL,
    )

    expires_dt = datetime.now(timezone.utc) + timedelta(seconds=PRESIGNED_URL_TTL)
    expires_at = expires_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    return download_url, expires_at


def _json_response(status_code: HTTPStatus, body: dict[str, Any]) -> dict[str, Any]:
    headers = get_cors_headers(None)
    headers['Content-Type'] = 'application/json'
    return {
        'statusCode': status_code.value,
        'headers': headers,
        'body': json.dumps(body),
    }


__all__ = ['lambda_handler']
