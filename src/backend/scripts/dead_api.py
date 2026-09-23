"""dead_api.py — every API route, cross-checked against its handler and its caller.

Why this exists
----------------
Three things have to agree for a route to be real: CDK wired it, a handler
module exists to serve it, and the frontend (or some other real caller) knows
to call it. This tool reads all three independently and reports where they
disagree — a route with no caller, a route pointing at a handler function
that no longer exists, or (the more dangerous direction) a frontend call to a
path CDK never wired, which is a 404 waiting for a user to hit it.

Where each side comes from
----------------------------
    CDK routes       infra/careervp/api_construct.py — the `feature_proxies`
                      list (prefix routes: everything under `/auth/*` etc.
                      goes to one Lambda) and the `route_map` list (explicit
                      path+method+handler tuples), both inside
                      `_add_openapi_contract_routes`.
    Handler modules   resolved from each route's `self.<attr>` by tracing the
                      attribute back to the `_add_*_lambda*` method that built
                      it, then reading that method's own
                      `handler="careervp.handlers.X.func"` string — the same
                      resolution dead_code.py uses for entry-point seeding.
    Frontend callers  every `apiClient.<method>(...)` call anywhere under
                      src/frontend/ (not just api/methods.ts — three other
                      files call it directly), with template-literal
                      interpolations (`${jobId}`) normalised to `{param}` so
                      they compare against CDK's `{jobId}`-style path params.

Known, accepted exceptions (do not report these as defects)
--------------------------------------------------------------
    /jobs             excluded from the frontend-caller cross-check on
                      purpose — api_construct.py's own comment says several
                      Lambdas own sub-paths under it, by design.
    /billing/webhook  a webhook target, not something the frontend calls.

What this does NOT check
---------------------------
Whether a route wired to a *prefix* Lambda (auth/users/gap-analysis/billing)
is actually handled by that Lambda's *internal* dispatch (its own
`if method == ... and path == ...` branches) is not verified here — that
requires understanding each handler's private routing logic, which is
handler-specific and not mechanical. One instance of this class was found by
hand and is recorded in docs/DEAD-CODE.md instead: `/knowledge-base` is wired
to `company_research_func`, and that Lambda really does serve it
(`get_knowledge_base`) — but a wholly separate, never-wired
`handlers/knowledge_base_handler.py` also exists and implements the same
concept redundantly.

Usage
-----
    uv run python scripts/dead_api.py
    uv run python scripts/dead_api.py --json
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_stamp import REPO_ROOT, write_proof  # noqa: E402

API_CONSTRUCT: Final[Path] = REPO_ROOT / 'infra' / 'careervp' / 'api_construct.py'
HANDLERS_ROOT: Final[Path] = REPO_ROOT / 'src' / 'backend' / 'careervp' / 'handlers'
FRONTEND_ROOT: Final[Path] = REPO_ROOT / 'src' / 'frontend'

EXCLUDE_PARTS: Final[frozenset[str]] = frozenset({'node_modules', '.next', 'dist', 'cdk.out', '.build', '__pycache__'})

# Known-by-design exceptions — see module docstring.
NO_FRONTEND_CALLER_EXPECTED: Final[frozenset[str]] = frozenset({'/jobs', '/billing/webhook'})

HANDLER_ATTR_RE: Final[re.Pattern[str]] = re.compile(r'handler\s*=\s*"careervp\.handlers\.([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)"')
PARAM_SEGMENT_RE: Final[re.Pattern[str]] = re.compile(r'\{[^}/]+\}')
TEMPLATE_INTERP_RE: Final[re.Pattern[str]] = re.compile(r'\$\{[^}]+\}')
API_CALL_RE: Final[re.Pattern[str]] = re.compile(
    r"apiClient\s*\.\s*(get|post|put|patch|delete)(?:\s*<[\s\S]*?>)?\s*\(\s*(`([^`]*)`|'([^']*)'|\"([^\"]*)\")"
)


def _normalise(path: str) -> str:
    return PARAM_SEGMENT_RE.sub('{param}', path)


def _literal_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _self_attr(node: ast.AST) -> str | None:
    """`self.foo` -> 'foo'; anything else -> None (reported, not guessed)."""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'self':
        return node.attr
    return None


@dataclass
class CdkRoute:
    path: str
    method: str
    handler_attr: str
    kind: str  # 'explicit' or 'proxy'


def _find_method(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _extract_tuple_list(assign_value: ast.AST) -> list[tuple[Any, ...]]:
    """A `[(...), (...)]` list literal -> list of tuples of raw AST nodes."""
    out: list[tuple[Any, ...]] = []
    if not isinstance(assign_value, ast.List):
        return out
    for elt in assign_value.elts:
        if isinstance(elt, ast.Tuple):
            out.append(tuple(elt.elts))
    return out


def _assign_target_name(node: ast.Assign | ast.AnnAssign) -> str | None:
    if node.value is None:
        return None
    target = node.targets[0] if isinstance(node, ast.Assign) else node.target
    return target.id if isinstance(target, ast.Name) else None


def _feature_proxy_routes(list_node: ast.expr, unresolved: list[str]) -> list[CdkRoute]:
    routes: list[CdkRoute] = []
    for elts in _extract_tuple_list(list_node):
        if len(elts) != 3:
            continue
        path = _literal_str(elts[0])
        attr = _self_attr(elts[1])
        if path is None or attr is None:
            unresolved.append(f'feature_proxies entry: {ast.dump(elts[0])[:120]}')
            continue
        routes.append(CdkRoute(path=path, method='*', handler_attr=attr, kind='proxy'))
    return routes


def _route_map_routes(list_node: ast.expr, unresolved: list[str]) -> list[CdkRoute]:
    routes: list[CdkRoute] = []
    for elts in _extract_tuple_list(list_node):
        if len(elts) != 3:
            continue
        path = _literal_str(elts[0])
        http_method = _literal_str(elts[1])
        attr = _self_attr(elts[2])
        if path is None or http_method is None or attr is None:
            unresolved.append(f'route_map entry: {ast.dump(elts[0])[:120]}')
            continue
        routes.append(CdkRoute(path=path, method=http_method, handler_attr=attr, kind='explicit'))
    return routes


def discover_cdk_routes(source: str) -> tuple[list[CdkRoute], list[str]]:
    """Parse `_add_openapi_contract_routes` for feature_proxies + route_map."""
    tree = ast.parse(source)
    method = _find_method(tree, '_add_openapi_contract_routes')
    routes: list[CdkRoute] = []
    unresolved: list[str] = []
    if method is None:
        return routes, ['could not find _add_openapi_contract_routes']

    for node in ast.walk(method):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
            continue
        target_name = _assign_target_name(node)
        if target_name == 'feature_proxies':
            routes.extend(_feature_proxy_routes(node.value, unresolved))
        elif target_name == 'route_map':
            routes.extend(_route_map_routes(node.value, unresolved))

    routes.extend(_discover_direct_route_calls(tree))
    return routes, unresolved


def _discover_direct_route_calls(tree: ast.Module) -> list[CdkRoute]:
    """Routes registered outside `_add_openapi_contract_routes`.

    `register_ai_assist_routes` and `register_error_report_route` each call
    `self._add_route_method(...)` / `..._with_integration(...)` directly with
    literal (path, method) args, rather than looping a list — the same shape
    the naive-grep trap describes, just one level removed: read only the one
    method everyone expects and you miss routes wired from any other one.
    """
    routes: list[CdkRoute] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr not in ('_add_route_method', '_add_route_method_with_integration'):
            continue
        if isinstance(node.func.value, ast.Name) and node.func.value.id == 'self':
            pass  # top-level self.<call> — the only shape considered
        else:
            continue
        args = node.args
        if len(args) < 3:
            continue
        path = _literal_str(args[0])
        http_method = _literal_str(args[1])
        if path is None or http_method is None:
            continue
        attr = _self_attr(args[2])
        handler_desc = attr if attr is not None else f'<non-attr: {ast.dump(args[2])[:60]}>'
        routes.append(CdkRoute(path=path, method=http_method, handler_attr=handler_desc, kind='explicit'))
    return routes


def resolve_handler_modules(source: str) -> dict[str, str]:
    """`self.<attr> = self._add_x(...)` where `_add_x`'s body names a handler string -> {attr: 'module.func'}."""
    tree = ast.parse(source)

    attr_to_builder: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            attr = _self_attr(target)
            if attr and isinstance(node.value, ast.Call) and _self_attr_call_func(node.value):
                attr_to_builder[attr] = _self_attr_call_func(node.value)  # type: ignore[assignment]

    builder_to_handler: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            text = ast.get_source_segment(source, node) or ''
            match = HANDLER_ATTR_RE.search(text)
            if match:
                builder_to_handler[node.name] = f'{match.group(1)}.{match.group(2)}'

    return {attr: builder_to_handler[builder] for attr, builder in attr_to_builder.items() if builder in builder_to_handler}


def _self_attr_call_func(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id == 'self':
        return call.func.attr
    return None


def discover_frontend_calls(root: Path) -> set[tuple[str, str]]:
    calls: set[tuple[str, str]] = set()
    for path in root.rglob('*.ts*'):
        if any(part in EXCLUDE_PARTS for part in path.parts) or '/tests/' in path.as_posix():
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        for match in API_CALL_RE.finditer(text):
            method = match.group(1).upper()
            raw = match.group(3) or match.group(4) or match.group(5) or ''
            raw = raw.split('?', 1)[0]  # strip query strings
            normalised = _normalise(TEMPLATE_INTERP_RE.sub('{param}', raw))
            if normalised.startswith('/'):
                calls.add((method, normalised))
    return calls


def _handler_file_and_func(handler_module: str) -> tuple[Path, str]:
    module, func = handler_module.rsplit('.', 1)
    return HANDLERS_ROOT / f'{module}.py', func


def handler_exists(handler_module: str) -> bool:
    path, func = _handler_file_and_func(handler_module)
    if not path.exists():
        return False
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except (SyntaxError, UnicodeDecodeError):
        return False
    return any(isinstance(n, ast.FunctionDef) and n.name == func for n in ast.walk(tree))


@dataclass
class Report:
    explicit_routes: int
    proxy_routes: int
    missing_handlers: list[dict[str, str]]
    no_frontend_caller: list[dict[str, str]]
    frontend_calls_no_cdk_route: list[dict[str, str]]
    unresolved: list[str]


def _check_handlers(
    routes: list[CdkRoute], handler_by_attr: dict[str, str], unresolved: list[str]
) -> tuple[list[dict[str, str]], set[tuple[str, str]], list[str]]:
    """Returns (missing_handlers, cdk_normalised explicit-route keys, proxy prefixes)."""
    missing_handlers: list[dict[str, str]] = []
    cdk_normalised: set[tuple[str, str]] = set()
    proxy_prefixes: list[str] = []

    for route in routes:
        handler_module = handler_by_attr.get(route.handler_attr)
        if handler_module is None:
            unresolved.append(f'{route.method} {route.path} -> self.{route.handler_attr}: handler module not resolved')
        elif not handler_exists(handler_module):
            missing_handlers.append(
                {'path': route.path, 'method': route.method, 'handler_attr': route.handler_attr, 'handler_module': handler_module}
            )

        if route.kind == 'explicit':
            cdk_normalised.add((route.method, _normalise(route.path)))
        else:
            proxy_prefixes.append(route.path)

    return missing_handlers, cdk_normalised, proxy_prefixes


def _routes_without_frontend_callers(routes: list[CdkRoute], frontend_calls: set[tuple[str, str]]) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for route in routes:
        if route.kind != 'explicit' or route.path in NO_FRONTEND_CALLER_EXPECTED:
            continue
        target = (route.method, _normalise(route.path))
        if target not in frontend_calls:
            found.append({'method': route.method, 'path': route.path})
    return found


def _frontend_calls_without_cdk_route(
    frontend_calls: set[tuple[str, str]], cdk_normalised: set[tuple[str, str]], proxy_prefixes: list[str]
) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for method, path in sorted(frontend_calls):
        if any(path == p or path.startswith(p + '/') or path.startswith(p) for p in proxy_prefixes):
            continue
        if (method, path) in cdk_normalised:
            continue
        found.append({'method': method, 'path': path})
    return found


def build_report() -> Report:
    source = API_CONSTRUCT.read_text(encoding='utf-8')
    routes, unresolved = discover_cdk_routes(source)
    handler_by_attr = resolve_handler_modules(source)
    frontend_calls = discover_frontend_calls(FRONTEND_ROOT)

    missing_handlers, cdk_normalised, proxy_prefixes = _check_handlers(routes, handler_by_attr, unresolved)
    no_frontend_caller = _routes_without_frontend_callers(routes, frontend_calls)
    frontend_calls_no_cdk_route = _frontend_calls_without_cdk_route(frontend_calls, cdk_normalised, proxy_prefixes)

    return Report(
        explicit_routes=sum(1 for r in routes if r.kind == 'explicit'),
        proxy_routes=sum(1 for r in routes if r.kind == 'proxy'),
        missing_handlers=missing_handlers,
        no_frontend_caller=no_frontend_caller,
        frontend_calls_no_cdk_route=frontend_calls_no_cdk_route,
        unresolved=unresolved,
    )


def render(report: Report) -> str:
    lines = [
        'DEAD API — CDK routes vs. handler existence vs. frontend callers',
        '',
        f'{report.explicit_routes} explicit routes, {report.proxy_routes} proxy-prefix routes',
        '',
    ]
    lines.append(f'missing handler (route points at a function that does not exist): {len(report.missing_handlers)}')
    for m in report.missing_handlers:
        lines.append(f'  - {m["method"]} {m["path"]} -> {m["handler_module"]} (self.{m["handler_attr"]})')
    lines.append('')
    lines.append(f'no known frontend caller: {len(report.no_frontend_caller)}')
    for r in report.no_frontend_caller:
        lines.append(f'  - {r["method"]} {r["path"]}')
    lines.append('')
    lines.append(f'frontend calls a path with no matching CDK route (would 404 in prod): {len(report.frontend_calls_no_cdk_route)}')
    for r in report.frontend_calls_no_cdk_route:
        lines.append(f'  - {r["method"]} {r["path"]}')
    if report.unresolved:
        lines.append('')
        lines.append(f'unresolved (tool could not determine — needs a human, not a guess): {len(report.unresolved)}')
        for u in report.unresolved:
            lines.append(f'  - {u}')
    return '\n'.join(lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--no-write', action='store_true')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = build_report()

    if args.json:
        print(json.dumps(asdict(report), indent=2, sort_keys=True))
    else:
        print(render(report))

    if not args.no_write:
        path = write_proof('dead_api', asdict(report), read_deployed=False)
        if not args.json:
            print(f'\nproof: {path}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
