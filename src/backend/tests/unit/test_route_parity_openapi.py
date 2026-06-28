"""TEST-INFRA-048 Category B — OpenAPI route-parity at the Powertools resolver layer.

For every ``(path, method)`` declared in ``docs/architecture/api_spec.openapi.yml`` the
shared Powertools ``APIGatewayRestResolver`` must match a *registered* route — i.e. it
would not return 404 (no matching path) or 405 (path matched but wrong method).

This proves the FE-UI-048 ``{proxy+}`` collapse, which forwards the *full* request path to
each feature Lambda, preserves the documented contract: greedy proxy forwarding plus
full-path matching by Powertools still resolves every OpenAPI route to a handler.

Only the routing layer is under test. Handlers are never invoked, so no DAL/LLM/network is
touched — route resolution is checked by replaying Powertools' own compiled route regexes,
exactly as ``app.resolve`` would match them, without executing the route function.

AC-006

Source spec:  docs/upgrade/specs/FE-UI-048-apigw-proxy-collapse-headroom.yaml
Test prompts: docs/upgrade/specs/TEST-INFRA-048-test-prompts.yaml
Route oracle: docs/architecture/api_spec.openapi.yml
"""

from __future__ import annotations

import importlib
import pkgutil
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

# ---------------------------------------------------------------------------
# Route oracle loading
# ---------------------------------------------------------------------------

_HTTP_METHODS = frozenset({'get', 'post', 'put', 'patch', 'delete', 'head', 'options'})


def _repo_root() -> Path:
    """Resolve the repository root from this test file's location."""
    # src/backend/tests/unit/test_route_parity_openapi.py -> repo root is parents[4].
    return Path(__file__).resolve().parents[4]


def _load_openapi_routes() -> list[tuple[str, str]]:
    """Return ``(path, METHOD)`` pairs from the OpenAPI oracle."""
    oracle = _repo_root() / 'docs' / 'architecture' / 'api_spec.openapi.yml'
    spec = yaml.safe_load(oracle.read_text())
    routes: list[tuple[str, str]] = []
    for path, operations in (spec.get('paths') or {}).items():
        if not isinstance(operations, dict):
            continue
        for method in operations:
            if method.lower() in _HTTP_METHODS:
                routes.append((path, method.upper()))
    return routes


# ---------------------------------------------------------------------------
# Resolver route-table introspection
# ---------------------------------------------------------------------------


def _register_all_handler_routes() -> None:
    """Import every handler module so its decorators register on the shared resolver.

    All API-fronted handlers bind to the single shared ``APIGatewayRestResolver`` in
    ``careervp.handlers.utils.rest_api_resolver``. Importing the handler package's
    modules is what populates that resolver's route table. Import errors for non-route
    helper modules are tolerated — the route assertions below fail loudly if a route is
    genuinely unregistered.
    """
    import careervp.handlers as handlers_pkg

    for module_info in pkgutil.iter_modules(handlers_pkg.__path__):
        if not module_info.name.endswith('_handler'):
            continue
        try:
            importlib.import_module(f'careervp.handlers.{module_info.name}')
        except Exception:  # pragma: no cover - non-route import side effects
            # A handler that can't import cleanly in unit context still can't host a
            # route here; the parity assertion will surface any missing route.
            continue


def _registered_routes() -> list[tuple[str, Any]]:
    """Return ``(method, compiled_rule)`` for every route on the shared resolver."""
    _register_all_handler_routes()
    from careervp.handlers.utils.rest_api_resolver import app

    routes: list[tuple[str, Any]] = []
    for route in [*app._static_routes, *app._dynamic_routes]:
        routes.append((str(route.method).upper(), route.rule))
    return routes


def _concrete_path(openapi_path: str) -> str:
    """Turn an OpenAPI templated path into a concrete one Powertools regexes can match.

    Both OpenAPI ``{param}`` and Powertools ``<param>`` placeholders become a literal
    token so the compiled dynamic-route regex (which matches a single path segment) will
    bind it.
    """
    concrete = re.sub(r'\{[^/}]+\}', 'param', openapi_path)
    concrete = re.sub(r'<[^/>]+>', 'param', concrete)
    return concrete


def _resolution(path: str, method: str, routes: list[tuple[str, Any]]) -> str:
    """Replicate Powertools matching: return 'ok', '405' (path-only), or '404'."""
    concrete = _concrete_path(path)
    path_matched = False
    for route_method, rule in routes:
        if rule.match(concrete) is None:
            continue
        path_matched = True
        if route_method in (method, 'ANY'):
            return 'ok'
    return '405' if path_matched else '404'


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

_OPENAPI_ROUTES = _load_openapi_routes()


def test_openapi_oracle_is_non_empty() -> None:
    """Guard: the oracle must declare at least one route, else parity is vacuous."""
    assert _OPENAPI_ROUTES, (
        'docs/architecture/api_spec.openapi.yml declared no routes — the route-parity '
        'check would pass vacuously. Verify the OpenAPI oracle path/contents.'
    )


@pytest.mark.parametrize(('path', 'method'), _OPENAPI_ROUTES)
def test_every_openapi_route_resolves_to_a_handler(path: str, method: str) -> None:
    """Every OpenAPI ``(path, method)`` must resolve to a registered route (AC-006).

    A 404 means no path matched (route dropped by the collapse); a 405 means the path
    matched but the method did not (verb lost). Either is a contract regression.
    """
    routes = _registered_routes()
    outcome = _resolution(path, method, routes)
    assert outcome == 'ok', (
        f'OpenAPI route {method} {path} did not resolve to a handler: '
        f'the shared Powertools resolver returned {outcome} '
        f'({"no matching path — 404" if outcome == "404" else "method not allowed — 405"}). '
        'After the {proxy+} collapse every documented route must still bind to a '
        'registered handler route.'
    )
