"""Deployed parity contract assertions for route/method/auth gate.

Validates that routes defined in infra/careervp/api_construct.py are
consistent with the expected method/path set. Intended to be run as part
of the pre_merge and pre_deploy blocking gates.

Usage:
    pytest src/backend/tests/integration/test_deployed_parity_contract.py -v
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ROUTE_TUPLE_RE = re.compile(r'\(\s*"(?P<path>/[^"]+)"\s*,\s*"(?P<method>[A-Z]+)"\s*,\s*self\.[^)]+\)')
# Proxy mounts forward every sub-path to a single Lambda, e.g.
# ("/auth", self.auth_api_func, False) or ("/billing", self.billing_lambda, True).
# Individual routes under such a prefix (e.g. POST /auth/login) are served by the
# proxy and never appear as explicit (path, method, func) tuples.
_PROXY_MOUNT_RE = re.compile(r'\(\s*"(?P<prefix>/[^"]+)"\s*,\s*self\.[^,]+,\s*(?:True|False)\s*\)')

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SOURCE = REPO_ROOT / 'infra' / 'careervp' / 'api_construct.py'


def _load_infra_routes() -> set[tuple[str, str]]:
    """Extract explicit (METHOD, /path) tuples from api_construct.py."""
    text = INFRA_SOURCE.read_text(encoding='utf-8')
    return {(match.group('method'), match.group('path')) for match in _ROUTE_TUPLE_RE.finditer(text)}


def _load_infra_proxy_prefixes() -> set[str]:
    """Extract proxy mount prefixes (e.g. /auth, /billing, /gap-analysis)."""
    text = INFRA_SOURCE.read_text(encoding='utf-8')
    return {match.group('prefix') for match in _PROXY_MOUNT_RE.finditer(text)}


def _is_covered_by_proxy(path: str, prefixes: set[str]) -> bool:
    """True if path falls under one of the proxy mount prefixes."""
    return any(path == prefix or path.startswith(prefix + '/') for prefix in prefixes)


# ---------------------------------------------------------------------------
# Expected route surface – must be kept in sync with api_construct.py
# ---------------------------------------------------------------------------

EXPECTED_ROUTES: set[tuple[str, str]] = {
    # Health
    ('GET', '/health'),
    # Auth
    ('POST', '/auth/register'),
    ('POST', '/auth/login'),
    ('POST', '/auth/refresh'),
    # Users
    ('GET', '/users/me'),
    ('PUT', '/users/me'),
    ('GET', '/users/me/usage'),
    ('POST', '/users/me/trial/reset'),
    # User CVs
    ('POST', '/users/me/cv'),
    ('GET', '/users/me/cv'),
    # Jobs
    ('POST', '/jobs'),
    ('GET', '/jobs'),
    ('GET', '/jobs/{jobId}'),
    # Gap analysis
    ('POST', '/jobs/{jobId}/gap-questions'),
    ('GET', '/jobs/{jobId}/gap-questions'),
    ('POST', '/jobs/{jobId}/gap-responses'),
    # VPR
    ('POST', '/vpr/generate'),
    ('GET', '/vpr/{vprId}/status'),
    ('POST', '/vpr/{vprId}/cancel'),
    ('GET', '/vprs'),
    # CV Tailoring
    ('POST', '/cv-tailoring/generate'),
    ('GET', '/cv-tailoring/{cvTailoringId}/status'),
    ('POST', '/cv-tailoring/{cvTailoringId}/cancel'),
    ('PATCH', '/cv-tailoring/{cvTailoringId}'),
    ('GET', '/cv-tailorings'),
    ('DELETE', '/cv-tailoring/{cvTailoringId}'),
    # Cover Letter
    ('POST', '/cover-letter/generate'),
    ('GET', '/cover-letter/{coverLetterId}/status'),
    ('POST', '/cover-letter/{coverLetterId}/cancel'),
    ('PATCH', '/cover-letter/{coverLetterId}'),
    ('GET', '/cover-letters'),
    # Interview Prep
    ('POST', '/interview-prep/generate'),
    ('PATCH', '/interview-prep/{interviewPrepId}'),
    ('GET', '/interview-prep/{interviewPrepId}/status'),
    ('POST', '/interview-prep/{interviewPrepId}/cancel'),
    ('GET', '/interview-preps'),
    # AI Assist
    ('POST', '/ai/assist'),
    # Company Research
    ('POST', '/company-research/fetch'),
    ('GET', '/company-research/{jobId}'),
    ('POST', '/company-research/{jobId}/cancel'),
    # Additional API surface currently exposed by infra
    ('GET', '/applications/{application_id}'),
    ('GET', '/jobs/{jobId}/artifacts/{moduleType}/export'),
    ('GET', '/knowledge-base'),
    ('GET', '/users/me/subscription'),
    ('POST', '/gap-analysis/questions'),
    ('POST', '/billing/checkout'),
    ('POST', '/billing/portal'),
    ('POST', '/billing/webhook'),
}


class TestDeployedParityContract:
    """Route surface parity: infra definition vs. expected contract surface."""

    def test_infra_source_exists(self) -> None:
        """api_construct.py must exist and be readable."""
        assert INFRA_SOURCE.exists(), f'Infra source missing: {INFRA_SOURCE}. Cannot perform parity check without it.'

    def test_infra_routes_non_empty(self) -> None:
        """Infra source must define at least one route tuple."""
        routes = _load_infra_routes()
        assert routes, 'No route tuples found in api_construct.py. Regex may be stale or file structure changed.'

    def test_no_routes_missing_from_infra(self) -> None:
        """Every expected route must be present in the infra route map."""
        infra = _load_infra_routes()
        proxy_prefixes = _load_infra_proxy_prefixes()
        missing = {(method, path) for (method, path) in (EXPECTED_ROUTES - infra) if not _is_covered_by_proxy(path, proxy_prefixes)}
        assert not missing, f'{len(missing)} expected route(s) missing from infra:\n' + '\n'.join(f'  {m} {p}' for m, p in sorted(missing))

    def test_no_unexpected_routes_in_infra(self) -> None:
        """Routes in infra not in the expected set are flagged as drift.

        This is a *warning* gate – new routes should be added to EXPECTED_ROUTES
        rather than causing a hard failure. Fail if the delta exceeds threshold.
        """
        infra = _load_infra_routes()
        extra = infra - EXPECTED_ROUTES
        # Allow up to 5 untracked routes before treating as a blocker.
        max_untracked = int(os.environ.get('PARITY_MAX_UNTRACKED_ROUTES', '5'))
        assert len(extra) <= max_untracked, (
            f'{len(extra)} route(s) in infra not present in EXPECTED_ROUTES '
            f'(threshold={max_untracked}). Update EXPECTED_ROUTES in this file:\n' + '\n'.join(f'  {m} {p}' for m, p in sorted(extra))
        )

    def test_critical_regression_routes_present(self) -> None:
        """The five high-risk routes from RECOVERY_001 must be in the infra map."""
        infra = _load_infra_routes()
        critical: list[tuple[str, str]] = [
            ('POST', '/jobs/{jobId}/gap-questions'),
            ('DELETE', '/cv-tailoring/{cvTailoringId}'),
            ('GET', '/cover-letters'),
            ('GET', '/vprs'),
            ('GET', '/interview-prep/{interviewPrepId}/status'),
        ]
        missing = [route for route in critical if route not in infra]
        assert not missing, 'Critical regression routes missing from infra:\n' + '\n'.join(f'  {m} {p}' for m, p in missing)
