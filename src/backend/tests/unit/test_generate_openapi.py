"""Unit tests for OpenAPI generation from API Gateway resources."""

from __future__ import annotations

from generate_openapi import build_openapi_from_apigw_resources, parse_api_id_from_swagger_url


def test_parse_api_id_from_swagger_url_extracts_execute_api_id() -> None:
    api_id = parse_api_id_from_swagger_url('https://1aj6084o45.execute-api.us-east-1.amazonaws.com/prod/swagger')
    assert api_id == '1aj6084o45'


def test_build_openapi_from_apigw_resources_excludes_docs_endpoints_only() -> None:
    resources = [
        {'path': '/swagger', 'resourceMethods': {'GET': {}}},
        {'path': '/swagger.css', 'resourceMethods': {'GET': {}}},
        {'path': '/swagger.js', 'resourceMethods': {'GET': {}}},
        {'path': '/jobs', 'resourceMethods': {'GET': {}, 'POST': {}}},
        {'path': '/api/cv', 'resourceMethods': {'POST': {}}},
    ]

    openapi = build_openapi_from_apigw_resources(resources)
    assert '/swagger' not in openapi['paths']
    assert '/swagger.css' not in openapi['paths']
    assert '/swagger.js' not in openapi['paths']
    assert '/jobs' in openapi['paths']
    assert '/api/cv' in openapi['paths']
    assert 'get' in openapi['paths']['/jobs']
    assert 'post' in openapi['paths']['/jobs']
    assert 'post' in openapi['paths']['/api/cv']


def test_build_openapi_from_apigw_resources_ignores_options_methods() -> None:
    resources = [
        {'path': '/health', 'resourceMethods': {'GET': {}, 'OPTIONS': {}}},
    ]
    openapi = build_openapi_from_apigw_resources(resources)
    assert '/health' in openapi['paths']
    assert 'get' in openapi['paths']['/health']
    assert 'options' not in openapi['paths']['/health']


def test_build_openapi_from_apigw_resources_normalizes_legacy_path_param_names() -> None:
    resources = [
        {'path': '/jobs/{jobId}', 'resourceMethods': {'GET': {}}},
        {'path': '/jobs/{jobId}/gap-questions', 'resourceMethods': {'POST': {}}},
        {'path': '/vpr/{vprId}/status', 'resourceMethods': {'GET': {}}},
        {'path': '/company-research/{jobId}', 'resourceMethods': {'GET': {}}},
    ]

    openapi = build_openapi_from_apigw_resources(resources)
    assert '/jobs/{job_id}' in openapi['paths']
    assert '/jobs/{job_id}/gap-questions' in openapi['paths']
    assert '/vpr/{job_id}/status' in openapi['paths']
    assert '/company-research/{company_name}' in openapi['paths']
    assert '/jobs/{jobId}' not in openapi['paths']
    assert '/vpr/{vprId}/status' not in openapi['paths']
    assert '/company-research/{jobId}' not in openapi['paths']
