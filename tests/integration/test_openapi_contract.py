"""End-to-end OpenAPI contract validation for all 27 endpoints."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "scripts" / "validate_openapi_coverage.py"


def _load_validator_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "validate_openapi_coverage", VALIDATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load validator module from {VALIDATOR_PATH}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_all_27_endpoints_are_covered_by_handlers() -> None:
    validator = _load_validator_module()
    report = validator.build_validation_report()

    assert report.total_endpoints == 27
    assert report.covered_endpoints == 27
    assert report.missing_endpoint_mappings == []
    assert report.missing_handlers == []
    assert report.missing_route_markers == {}


def test_request_schemas_match_openapi_models() -> None:
    validator = _load_validator_module()
    report = validator.build_validation_report()

    assert report.missing_request_schemas == []


def test_response_schemas_match_openapi_models() -> None:
    validator = _load_validator_module()
    report = validator.build_validation_report()

    assert report.missing_response_schemas == []


def test_http_status_codes_match_openapi_contract() -> None:
    validator = _load_validator_module()
    report = validator.build_validation_report()

    assert report.status_mismatches == []


def test_authentication_requirements_match_openapi_contract() -> None:
    validator = _load_validator_module()
    report = validator.build_validation_report()

    assert report.auth_security_mismatches == []
    assert report.auth_handler_mismatches == {}
