"""Sync checks between OpenAPI and api_contract_spec.yaml."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_PATH = ROOT / "docs" / "swagger" / "careervp-api-v1.yaml"
CONTRACT_PATH = ROOT / "docs" / "refactor" / "specs" / "api_contract_spec.yaml"


def _openapi_endpoints(openapi: dict) -> set[tuple[str, str, str]]:
    endpoints: set[tuple[str, str, str]] = set()
    for path, methods in openapi["paths"].items():
        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "delete", "patch"}:
                continue
            endpoints.add((method.upper(), path, operation.get("operationId", "")))
    return endpoints


def _contract_endpoints(contract: dict) -> set[tuple[str, str, str]]:
    endpoints: set[tuple[str, str, str]] = set()
    for entries in contract["endpoints"].values():
        for entry in entries:
            endpoints.add(
                (entry["method"].upper(), entry["path"], entry["operationId"])
            )
    return endpoints


def test_contract_spec_matches_openapi() -> None:
    openapi = yaml.safe_load(OPENAPI_PATH.read_text())
    contract = yaml.safe_load(CONTRACT_PATH.read_text())

    openapi_set = _openapi_endpoints(openapi)
    contract_set = _contract_endpoints(contract)

    assert len(openapi_set) == 27
    assert contract["endpoint_count"] == 27
    assert contract_set == openapi_set
