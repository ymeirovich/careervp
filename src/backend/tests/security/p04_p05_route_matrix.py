"""Live route x handler ownership matrix for P-04/P-05 (spec: specs/P-04-P-05-auth-idor-spec.md).

This module is intentionally NOT a test file. It parses the *live* CDK ``route_map`` out of
``infra/careervp/api_construct.py`` at import time so the P-05 coverage ratchet reads the source of
truth instead of a frozen snapshot. If a new route is added to ``route_map`` and no owner-check case
is registered for it, the ratchet test (``test_p05_route_matrix_has_owner_assertion_for_every_authenticated_route``)
fails — that is the entire point.

Public-route exceptions come from the same file's ``public_paths`` set (the only place that decides
which methods are attached with ``authorizer=None``), so this stays in lock-step with the deploy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


def _repo_root() -> Path:
    # this file: <repo>/src/backend/tests/security/p04_p05_route_matrix.py
    return Path(__file__).resolve().parents[4]


def api_construct_source() -> str:
    path = _repo_root() / 'infra' / 'careervp' / 'api_construct.py'
    return path.read_text(encoding='utf-8')


def _extract_public_paths(source: str) -> set[str]:
    """Pull the literal ``public_paths = { ... }`` set that ``_add_route_method_with_integration`` uses."""
    match = re.search(r'public_paths\s*=\s*\{(.*?)\}', source, re.DOTALL)
    if not match:
        raise AssertionError(
            'Could not locate the public_paths set in api_construct.py — the citation has drifted; re-locate it before trusting this ratchet.'
        )
    return set(re.findall(r'"([^"]+)"', match.group(1)))


def _extract_route_map(source: str) -> list[tuple[str, str, str]]:
    """Return [(path, method, handler_attr)] from the canonical ``route_map`` list literal."""
    start = source.find('route_map: list[tuple[str, str, _lambda.Function]] = [')
    if start == -1:
        raise AssertionError(
            'Could not locate the route_map literal in api_construct.py — the citation has drifted; re-locate it before trusting this ratchet.'
        )
    # The list ends at the first line that iterates it.
    end = source.find('for path, method, handler in route_map', start)
    if end == -1:
        raise AssertionError('Could not find the end of the route_map literal.')
    block = source[start:end]

    # Each entry looks like: ("/path", "METHOD", self.some_func),  (whitespace/newlines vary).
    entries = re.findall(
        r'\(\s*"([^"]+)"\s*,\s*"([A-Z]+)"\s*,\s*self\.([A-Za-z0-9_]+)\s*,?\s*\)',
        block,
    )
    if not entries:
        raise AssertionError('Parsed zero route_map entries — the literal shape changed; re-check the regex.')
    return [(path, method, handler) for path, method, handler in entries]


@dataclass(frozen=True)
class Route:
    path: str
    method: str
    handler_attr: str

    @property
    def is_public(self) -> bool:
        return self.path in _PUBLIC_PATHS

    @property
    def has_foreign_id_param(self) -> bool:
        """True if the path carries a resource identifier owned by *some* user (an IDOR surface).

        Every ``{...}`` path parameter in this API names a foreign resource id (job/vpr/artifact/...);
        the caller's own identity never appears in the path (it is ``/users/me``, from the JWT).
        """
        return bool(re.search(r'\{[^}]+\}', self.path))

    @property
    def family(self) -> str:
        """First non-empty path segment, e.g. '/jobs/{jobId}' -> 'jobs'. Used to group owner-check coverage."""
        segments = [seg for seg in self.path.split('/') if seg]
        return segments[0] if segments else ''


_SOURCE = api_construct_source()
_PUBLIC_PATHS = _extract_public_paths(_SOURCE)
ALL_ROUTES: list[Route] = [Route(p, m, h) for (p, m, h) in _extract_route_map(_SOURCE)]
PUBLIC_PATHS: set[str] = set(_PUBLIC_PATHS)


def authenticated_routes() -> list[Route]:
    return [r for r in ALL_ROUTES if not r.is_public]


def resource_by_id_routes() -> list[Route]:
    return [r for r in authenticated_routes() if r.has_foreign_id_param]


def self_or_collection_routes() -> list[Route]:
    return [r for r in authenticated_routes() if not r.has_foreign_id_param]
