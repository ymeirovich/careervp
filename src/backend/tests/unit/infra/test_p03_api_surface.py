"""RED-first tests for clause P-03 — map the /api/* surface (verify staging-only).

Spec: docs/db-redesign/code/code-analysis/project/specs/P-03-api-surface-spec.md

Oracle rule (scope-lock §0.2): the canonical route surface is the CDK `route_map` in
infra/careervp/api_construct.py plus the `_register_feature_proxy` prefixes registered
in `_add_openapi_contract_routes()` — the drifted swagger doc is NOT authoritative.

AC-P03-1 — no frontend call site issues a backend HTTP request against an /api/*-prefixed
path. A raw substring grep for "/api/" over src/frontend false-positives on two things
present in the real tree: relative import specifiers such as '../../api/methods' (the
substring "/api/" appears inside the path segment, not a route) and the Next.js-internal,
same-origin routes under src/frontend/app/api/** (e.g. /api/errors, and the
fetch('/api/proxy/auth/logout') call in AuthContext.tsx) — these are handled by the
Next.js/Amplify SSR runtime, not AWS API Gateway, exactly as called out for
service_stack.py:101 in the spec's Evidence section. This test instead scans for
`apiClient.<verb>(...)` call sites (the sole path backend requests are issued through,
per api/client.ts + api/methods.ts) whose literal path starts with "/api/".

AC-P03-2 — no synthesized CloudFormation template contains an AWS::ApiGateway::Resource
with PathPart == "api" at the root level.

AC-P03-3 — the canonical route_map in api_construct.py carries zero /api/-prefixed paths,
across both the explicit route_map tuples and the feature_proxies prefixes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# src/backend/tests/unit/infra/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[5]
API_CONSTRUCT_PATH = REPO_ROOT / 'infra' / 'careervp' / 'api_construct.py'
FRONTEND_ROOT = REPO_ROOT / 'src' / 'frontend'
CDK_OUT = REPO_ROOT / 'infra' / 'cdk.out'

# Source-only directories under src/frontend/ (excludes node_modules, dist, .next,
# playwright-report, and other vendored/generated trees, which are not call sites).
_FRONTEND_SOURCE_DIRS = (
    'app',
    'adapters',
    'api',
    'canvas-app',
    'components',
    'contexts',
    'hooks',
    'lib',
    'store',
    'types',
)

_APICLIENT_CALL_PATTERN = re.compile(r"apiClient\s*\.\s*(?:get|post|put|patch|delete)\s*(?:<[^>]*>)?\s*\(\s*['\"`](/[^'\"`]*)['\"`]")


def _frontend_source_files() -> list[Path]:
    files: list[Path] = []
    for name in _FRONTEND_SOURCE_DIRS:
        target = FRONTEND_ROOT / name
        if not target.is_dir():
            continue
        for ext in ('*.ts', '*.tsx', '*.js', '*.jsx'):
            files.extend(p for p in target.rglob(ext) if 'node_modules' not in p.parts)
    middleware = FRONTEND_ROOT / 'middleware.ts'
    if middleware.is_file():
        files.append(middleware)
    return files


def test_frontend_has_no_api_star_backend_calls() -> None:
    """AC-P03-1: no apiClient.<verb>() call site targets an /api/*-prefixed path."""
    violations: list[str] = []
    for path in _frontend_source_files():
        text = path.read_text(encoding='utf-8')
        for match in _APICLIENT_CALL_PATTERN.finditer(text):
            literal = match.group(1)
            if literal.startswith('/api/') or literal == '/api':
                violations.append(f'{path.relative_to(REPO_ROOT)}: {literal!r}')
    assert violations == [], 'P-03 (AC-P03-1): frontend calls the backend via /api/*-prefixed paths:\n' + '\n'.join(violations)


def test_cdk_route_map_has_no_api_prefix() -> None:
    """AC-P03-3: no explicit route_map entry carries an /api/ prefix."""
    source = API_CONSTRUCT_PATH.read_text(encoding='utf-8')
    match = re.search(
        r'route_map\s*:\s*list\[.*?\]\s*=\s*(\[.*?\n\s*\])\s*\n\s*for\s+path',
        source,
        re.DOTALL,
    )
    assert match, 'P-03: could not locate route_map list literal in api_construct.py'
    route_list_text = match.group(1)
    paths = re.findall(r'"(/[^"]+)"', route_list_text)
    assert paths, 'P-03: route_map parsed but yielded zero path entries — regex likely stale'
    api_paths = [p for p in paths if p.startswith('/api/')]
    assert api_paths == [], f'P-03 (AC-P03-3): route_map contains /api/-prefixed routes: {api_paths}'


def test_cdk_feature_proxies_have_no_api_prefix() -> None:
    """AC-P03-3: no feature_proxies prefix (registered ahead of route_map) is /api/-prefixed."""
    source = API_CONSTRUCT_PATH.read_text(encoding='utf-8')
    match = re.search(
        r'feature_proxies\s*:\s*list\[.*?\]\s*=\s*(\[.*?\n\s*\])\s*\n\s*for\s+path',
        source,
        re.DOTALL,
    )
    assert match, 'P-03: could not locate feature_proxies list literal in api_construct.py'
    prefixes = re.findall(r'"(/[^"]+)"', match.group(1))
    assert prefixes, 'P-03: feature_proxies parsed but yielded zero prefixes — regex likely stale'
    api_prefixes = [p for p in prefixes if p.startswith('/api/')]
    assert api_prefixes == [], f'P-03 (AC-P03-3): feature_proxies contains /api/-prefixed routes: {api_prefixes}'


def test_cdk_synth_has_no_api_gateway_resource_named_api() -> None:
    """AC-P03-2: no synthesized CloudFormation template has a root-level
    AWS::ApiGateway::Resource with PathPart == 'api'.

    Uses the CDK_OUT snapshot committed to infra/cdk.out — regenerate it first with
    `cd infra && cdk synth` (dev) / `ENVIRONMENT=prod cdk synth` (prod) for a fresh check.
    """
    assert CDK_OUT.exists(), f'P-03: infra/cdk.out not found at {CDK_OUT} — run `cd infra && cdk synth` first'
    template_files = list(CDK_OUT.glob('*.template.json'))
    assert template_files, f'P-03: no synthesized *.template.json files found under {CDK_OUT}'
    violating_resources: list[str] = []
    for template_file in template_files:
        template = json.loads(template_file.read_text(encoding='utf-8'))
        resources = template.get('Resources', {})
        for logical_id, resource in resources.items():
            if resource.get('Type') != 'AWS::ApiGateway::Resource':
                continue
            path_part = resource.get('Properties', {}).get('PathPart', '')
            if path_part == 'api':
                violating_resources.append(f'{template_file.name}::{logical_id} (PathPart={path_part!r})')
    assert violating_resources == [], 'P-03 (AC-P03-2): CDK synth contains /api/ API Gateway resources:\n' + '\n'.join(violating_resources)
