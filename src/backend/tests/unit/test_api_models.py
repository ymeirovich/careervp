"""Unit tests for OpenAPI-aligned API Pydantic models."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from careervp.models import api_models
from careervp.models.api_models import (
    GapResponseRequest,
    HealthResponse,
    RegisterRequest,
    VPRGenerateRequest,
)

HTTP_METHODS = {'get', 'post', 'put', 'patch', 'delete', 'options', 'head', 'trace'}


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / 'docs' / 'swagger' / 'careervp-api-v1.yaml').exists():
            return parent
    raise RuntimeError('Could not locate repository root containing docs/swagger/careervp-api-v1.yaml')


def _extract_schema_name(ref: str) -> str:
    return ref.rsplit('/', 1)[-1]


def _iter_schema_refs_from_schema(schema: object) -> set[str]:
    refs: set[str] = set()
    if isinstance(schema, dict):
        ref_value = schema.get('$ref')
        if isinstance(ref_value, str) and ref_value.startswith('#/components/schemas/'):
            refs.add(_extract_schema_name(ref_value))
        for value in schema.values():
            refs.update(_iter_schema_refs_from_schema(value))
    elif isinstance(schema, list):
        for value in schema:
            refs.update(_iter_schema_refs_from_schema(value))
    return refs


def _iter_endpoint_schema_refs(openapi_doc: dict[str, object]) -> set[str]:
    refs: set[str] = set()
    paths = openapi_doc.get('paths')
    if not isinstance(paths, dict):
        return refs

    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue

        for method, operation in path_item.items():
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue

            request_body = operation.get('requestBody')
            refs.update(_iter_schema_refs_from_schema(request_body))

            responses = operation.get('responses')
            refs.update(_iter_schema_refs_from_schema(responses))

    return refs


def _count_operations(openapi_doc: dict[str, object]) -> int:
    count = 0
    paths = openapi_doc.get('paths')
    if not isinstance(paths, dict):
        return count

    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method in HTTP_METHODS and isinstance(operation, dict):
                count += 1
    return count


def _load_openapi() -> dict[str, object]:
    openapi_path = _repo_root() / 'docs' / 'swagger' / 'careervp-api-v1.yaml'
    with openapi_path.open('r', encoding='utf-8') as file_obj:
        loaded = yaml.safe_load(file_obj)
    if not isinstance(loaded, dict):
        raise AssertionError('OpenAPI file did not parse into a dictionary')
    return loaded


def test_openapi_contains_27_operations() -> None:
    openapi = _load_openapi()
    assert _count_operations(openapi) == 27


def test_all_endpoint_schema_refs_have_api_model_class() -> None:
    openapi = _load_openapi()
    schema_refs = _iter_endpoint_schema_refs(openapi)

    missing_model_classes = sorted(schema_name for schema_name in schema_refs if not hasattr(api_models, schema_name))
    assert missing_model_classes == []


def test_register_request_requires_email_password_name() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest.model_validate({'email': 'person@example.com', 'password': 'password123'})

    valid = RegisterRequest.model_validate(
        {
            'email': 'person@example.com',
            'password': 'password123',
            'name': 'Person Example',
        }
    )
    assert valid.email == 'person@example.com'


def test_vpr_generate_request_allows_empty_gap_ids() -> None:
    # Empty gap_response_ids is intentionally allowed — the frontend previously
    # sent [] by default and the backend was updated to accept it (see commit 16a2993).
    request = VPRGenerateRequest.model_validate(
        {
            'cv_id': 'cv-123',
            'job_id': 'job-123',
            'gap_response_ids': [],
        }
    )
    assert request.gap_response_ids == []


def test_gap_response_request_requires_responses() -> None:
    with pytest.raises(ValidationError):
        GapResponseRequest.model_validate({'responses': []})


def test_cover_letter_request_omitting_company_research_id_succeeds() -> None:
    from careervp.models.api_models import CoverLetterRequest

    req = CoverLetterRequest.model_validate(
        {
            'cv_id': 'cv-1',
            'job_id': 'job-1',
            'vpr_id': 'vpr-1',
            'gap_response_ids': ['r1'],
        }
    )
    assert req.company_research_id is None


def test_cover_letter_request_with_company_research_id_string_succeeds() -> None:
    from careervp.models.api_models import CoverLetterRequest

    req = CoverLetterRequest.model_validate(
        {
            'cv_id': 'cv-1',
            'job_id': 'job-1',
            'vpr_id': 'vpr-1',
            'gap_response_ids': ['r1'],
            'company_research_id': 'cr-abc',
        }
    )
    assert req.company_research_id == 'cr-abc'


def test_cover_letter_request_company_research_id_null_succeeds() -> None:
    from careervp.models.api_models import CoverLetterRequest

    req = CoverLetterRequest.model_validate(
        {
            'cv_id': 'cv-1',
            'job_id': 'job-1',
            'vpr_id': 'vpr-1',
            'gap_response_ids': ['r1'],
            'company_research_id': None,
        }
    )
    assert req.company_research_id is None


def test_cover_letter_request_company_research_id_empty_string_is_now_allowed() -> None:
    """Empty string was previously rejected (min_length=1). The field is now
    `str | None = None` with no length constraint, so "" is accepted as-is."""
    from careervp.models.api_models import CoverLetterRequest

    req = CoverLetterRequest.model_validate(
        {
            'cv_id': 'cv-1',
            'job_id': 'job-1',
            'vpr_id': 'vpr-1',
            'gap_response_ids': ['r1'],
            'company_research_id': '',
        }
    )
    assert req.company_research_id == ''


def test_api_model_json_round_trip_for_health_response() -> None:
    health = HealthResponse(
        status='healthy',
        timestamp=datetime(2026, 2, 18, 0, 0, 0, tzinfo=UTC),
        version='1.0.0',
    )
    serialized = health.to_json()
    restored = HealthResponse.from_json(serialized)

    assert restored.status == 'healthy'
    assert restored.version == '1.0.0'
    assert restored.timestamp == datetime(2026, 2, 18, 0, 0, 0, tzinfo=UTC)
