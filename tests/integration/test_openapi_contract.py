"""OpenAPI contract checks used by Phase 10 verification."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = ROOT / "docs" / "swagger" / "careervp-api-v1.yaml"
RUNBOOK_PATH = ROOT / "docs" / "refactor" / "EXECUTION_RUNBOOK.md"


ASYNC_ENDPOINTS = {
    ("POST", "/vpr/generate"),
    ("POST", "/cv-tailoring/generate"),
    ("POST", "/cover-letter/generate"),
    ("POST", "/interview-prep/generate"),
    ("POST", "/company-research/fetch"),
}


def test_async_endpoints_declared() -> None:
    openapi = yaml.safe_load(OPENAPI_PATH.read_text())

    for method, path in ASYNC_ENDPOINTS:
        assert path in openapi["paths"]
        assert method.lower() in openapi["paths"][path]


def test_async_endpoints_return_202() -> None:
    openapi = yaml.safe_load(OPENAPI_PATH.read_text())

    for method, path in ASYNC_ENDPOINTS:
        operation = openapi["paths"][path][method.lower()]
        assert "202" in operation["responses"]


def test_protected_endpoints_enforce_bearer_auth() -> None:
    openapi = yaml.safe_load(OPENAPI_PATH.read_text())

    for path, methods in openapi["paths"].items():
        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                continue
            if path.startswith("/auth/") and path in {"/auth/register", "/auth/login"}:
                continue
            if path == "/health":
                continue
            assert operation.get("security") == [{"BearerAuth": []}]


def test_runbook_phase_10_verification_references_contract_tests() -> None:
    content = RUNBOOK_PATH.read_text()

    assert "test_openapi_contract.py" in content
    assert "test_api_contract_spec_sync.py" in content
