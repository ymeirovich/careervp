"""L2.2 infrastructure tests for API Gateway Cognito authorizer wiring."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')

try:
    from aws_cdk import App, Environment
    from aws_cdk.assertions import Template

    CDK_AVAILABLE = True
except Exception:
    CDK_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CDK_AVAILABLE, reason='aws-cdk not available')

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')

PUBLIC_ROUTES = {
    ('GET', '/health'),
    ('POST', '/auth/register'),
    ('POST', '/auth/login'),
    ('POST', '/auth/refresh'),
    ('POST', '/billing/webhook'),
    ('POST', '/errors'),
}

PUBLIC_PROXY_ROUTES = {
    ('ANY', '/auth'),
    ('ANY', '/auth/{proxy+}'),
}


def _template() -> Template:
    if INFRA_SRC not in sys.path:
        sys.path.insert(0, INFRA_SRC)

    from careervp.naming_utils import NamingUtils  # type: ignore[import-not-found]
    from careervp.service_stack import ServiceStack  # type: ignore[import-not-found]

    app = App()
    naming = NamingUtils(environment='test', region='us-east-1', account_id='123456789012')
    stack = ServiceStack(
        scope=app,
        id=naming.stack_id('crud'),
        env=Environment(account='123456789012', region='us-east-1'),
        is_production_env=False,
        naming=naming,
        stack_feature='crud',
    )
    return Template.from_stack(stack)


def _resolve_paths(template: Template) -> dict[str, str]:
    resources = template.find_resources('AWS::ApiGateway::Resource')
    memo: dict[str, str] = {}

    def resolve(logical_id: str) -> str:
        if logical_id in memo:
            return memo[logical_id]
        props = resources[logical_id]['Properties']
        part = str(props.get('PathPart', '')).strip('/')
        parent = props.get('ParentId', {})
        parent_ref = parent.get('Ref') if isinstance(parent, dict) else None
        if isinstance(parent_ref, str) and parent_ref in resources:
            parent_path = resolve(parent_ref)
        else:
            parent_path = ''
        if parent_path and part:
            full = f'{parent_path}/{part}'
        elif part:
            full = f'/{part}'
        else:
            full = parent_path or '/'
        memo[logical_id] = full
        return full

    return {logical_id: resolve(logical_id) for logical_id in resources}


def _method_records(template: Template) -> list[dict[str, Any]]:
    methods = template.find_resources('AWS::ApiGateway::Method')
    resource_paths = _resolve_paths(template)
    records: list[dict[str, Any]] = []
    for method in methods.values():
        props = method['Properties']
        resource_ref = props.get('ResourceId', {}).get('Ref')
        path = resource_paths.get(resource_ref, '')
        records.append(
            {
                'http_method': props.get('HttpMethod'),
                'path': path,
                'authorization_type': props.get('AuthorizationType'),
                'authorizer_id': props.get('AuthorizerId'),
            }
        )
    return records


def _method_matches(record_method: object, target_method: str) -> bool:
    return record_method in {target_method, 'ANY'}


def _proxy_covers_path(proxy_path: str, target_path: str) -> bool:
    if not proxy_path.endswith('/{proxy+}'):
        return False
    prefix = proxy_path[: -len('/{proxy+}')]
    return target_path.startswith(f'{prefix}/')


def _matching_route_records(methods: list[dict[str, Any]], target_method: str, target_path: str) -> list[dict[str, Any]]:
    exact_matches = [m for m in methods if _method_matches(m['http_method'], target_method) and m['path'] == target_path]
    if exact_matches:
        return exact_matches
    return [
        m
        for m in methods
        if _method_matches(m['http_method'], target_method) and isinstance(m['path'], str) and _proxy_covers_path(m['path'], target_path)
    ]


def _is_public_route_record(method: dict[str, Any]) -> bool:
    method_key = (method['http_method'], method['path'])
    return method_key in PUBLIC_ROUTES or method_key in PUBLIC_PROXY_ROUTES


def test_cognito_authorizer_resource_created() -> None:
    template = _template()
    authorizers = template.find_resources('AWS::ApiGateway::Authorizer')
    assert authorizers
    assert any(a['Properties'].get('Type') == 'COGNITO_USER_POOLS' for a in authorizers.values())
    assert all(a['Properties'].get('Type') != 'TOKEN' for a in authorizers.values())


def test_cognito_authorizer_uses_authorization_header() -> None:
    template = _template()
    authorizers = template.find_resources('AWS::ApiGateway::Authorizer')
    cognito_authorizers = [a for a in authorizers.values() if a['Properties'].get('Type') == 'COGNITO_USER_POOLS']
    assert cognito_authorizers
    assert all(a['Properties'].get('IdentitySource') == 'method.request.header.Authorization' for a in cognito_authorizers)


def test_public_routes_are_unauthenticated() -> None:
    template = _template()
    methods = _method_records(template)
    for public_method, public_path in PUBLIC_ROUTES:
        matches = _matching_route_records(methods, public_method, public_path)
        assert matches, f'missing route {public_method} {public_path}'
        assert all(m['authorization_type'] == 'NONE' for m in matches)


def test_protected_routes_use_cognito_auth() -> None:
    template = _template()
    methods = _method_records(template)
    protected = [
        m for m in methods if m['http_method'] != 'OPTIONS' and m['path'] and not m['path'].startswith('/swagger') and not _is_public_route_record(m)
    ]
    assert protected
    assert all(m['authorization_type'] == 'COGNITO_USER_POOLS' for m in protected)
    assert all(m['authorizer_id'] is not None for m in protected)


def test_no_custom_authorization_type_remains() -> None:
    template = _template()
    methods = _method_records(template)
    assert all(m['authorization_type'] != 'CUSTOM' for m in methods)
