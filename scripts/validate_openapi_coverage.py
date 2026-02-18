#!/usr/bin/env python3
"""Validate OpenAPI endpoint coverage and contract checks against handler code."""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[1]
OPENAPI_PATH = ROOT / "docs" / "swagger" / "careervp-api-v1.yaml"
API_MODELS_PATH = ROOT / "src" / "backend" / "careervp" / "models" / "api_models.py"
HANDLERS_DIR = ROOT / "src" / "backend" / "careervp" / "handlers"

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
PUBLIC_ENDPOINTS = {
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("GET", "/health"),
}
ASYNC_ENDPOINTS = {
    ("POST", "/vpr/generate"),
    ("POST", "/cv-tailoring/generate"),
    ("POST", "/cover-letter/generate"),
    ("POST", "/interview-prep/generate"),
    ("POST", "/company-research/fetch"),
}

HTTP_STATUS_MARKERS: dict[str, tuple[str, ...]] = {
    "200": ("HTTPStatus.OK", "int(HTTPStatus.OK)"),
    "201": ("HTTPStatus.CREATED", "int(HTTPStatus.CREATED)"),
    "202": ("HTTPStatus.ACCEPTED", "int(HTTPStatus.ACCEPTED)"),
}


@dataclass(frozen=True)
class EndpointHandlerMapping:
    method: str
    path: str
    handler_file: str
    route_markers: tuple[str, ...]
    auth_markers: tuple[str, ...] = ()


ENDPOINT_HANDLER_MAP: tuple[EndpointHandlerMapping, ...] = (
    EndpointHandlerMapping(
        "POST", "/auth/register", "auth_handler.py", ("@app.post('/auth/register')",)
    ),
    EndpointHandlerMapping(
        "POST", "/auth/login", "auth_handler.py", ("@app.post('/auth/login')",)
    ),
    EndpointHandlerMapping(
        "POST",
        "/auth/refresh",
        "auth_handler.py",
        ("@app.post('/auth/refresh')",),
        auth_markers=("_extract_refresh_token()", "HTTPStatus.UNAUTHORIZED"),
    ),
    EndpointHandlerMapping(
        "GET",
        "/users/me",
        "user_handler.py",
        ("@app.get('/users/me')",),
        auth_markers=("_get_authenticated_user_id()", "HTTPStatus.UNAUTHORIZED"),
    ),
    EndpointHandlerMapping(
        "PUT",
        "/users/me",
        "user_handler.py",
        ("@app.put('/users/me')",),
        auth_markers=("_get_authenticated_user_id()", "HTTPStatus.UNAUTHORIZED"),
    ),
    EndpointHandlerMapping(
        "POST",
        "/users/me/cv",
        "cv_upload_handler.py",
        ("@app.post('/users/me/cv')",),
        auth_markers=(
            "_extract_user_id()",
            "Authenticated user_id is required for /users/me/cv",
        ),
    ),
    EndpointHandlerMapping(
        "GET",
        "/users/me/cvs",
        "user_handler.py",
        ("@app.get('/users/me/cvs')",),
        auth_markers=("_get_authenticated_user_id()", "HTTPStatus.UNAUTHORIZED"),
    ),
    EndpointHandlerMapping(
        "POST",
        "/jobs",
        "job_handler.py",
        ("@app.post('/jobs')",),
        auth_markers=("_get_authenticated_user_id()", "HTTPStatus.UNAUTHORIZED"),
    ),
    EndpointHandlerMapping(
        "GET",
        "/jobs",
        "job_handler.py",
        ("@app.get('/jobs')",),
        auth_markers=("_get_authenticated_user_id()", "HTTPStatus.UNAUTHORIZED"),
    ),
    EndpointHandlerMapping(
        "GET",
        "/jobs/{jobId}",
        "job_handler.py",
        ("@app.get('/jobs/<jobId>')",),
        auth_markers=("_get_authenticated_user_id()", "HTTPStatus.UNAUTHORIZED"),
    ),
    EndpointHandlerMapping(
        "POST",
        "/vpr/generate",
        "vpr_submit_handler.py",
        ("Endpoint: POST /vpr/generate",),
        auth_markers=(
            "_extract_authenticated_user_id(event)",
            "HTTPStatus.UNAUTHORIZED",
        ),
    ),
    EndpointHandlerMapping(
        "GET",
        "/vpr/{vprId}",
        "vpr_status_handler.py",
        ("path_value.startswith('/vpr/')",),
        auth_markers=(
            "_extract_authenticated_user_id(event)",
            "HTTPStatus.UNAUTHORIZED",
        ),
    ),
    EndpointHandlerMapping(
        "GET",
        "/users/me/vprs",
        "vpr_status_handler.py",
        ("path == '/users/me/vprs'",),
        auth_markers=(
            "_extract_authenticated_user_id(event)",
            "HTTPStatus.UNAUTHORIZED",
        ),
    ),
    EndpointHandlerMapping(
        "POST",
        "/gap-analysis/questions",
        "gap_handler.py",
        ("path == '/gap-analysis/questions'",),
        auth_markers=("_extract_user_id(event)", "HTTPStatus.UNAUTHORIZED"),
    ),
    EndpointHandlerMapping(
        "POST",
        "/gap-analysis/responses",
        "gap_handler.py",
        ("path == '/gap-analysis/responses'",),
        auth_markers=("_extract_user_id(event)", "HTTPStatus.UNAUTHORIZED"),
    ),
    EndpointHandlerMapping(
        "GET",
        "/gap-analysis/{jobId}/questions",
        "gap_handler.py",
        ("parts[0] == 'gap-analysis' and parts[2] == 'questions'",),
        auth_markers=("_extract_user_id(event)", "HTTPStatus.UNAUTHORIZED"),
    ),
    EndpointHandlerMapping(
        "POST",
        "/cv-tailoring/generate",
        "cv_tailoring_handler.py",
        ("/cv-tailoring/generate",),
        auth_markers=("_get_user_id(event, body)", "HTTPStatus.UNAUTHORIZED"),
    ),
    EndpointHandlerMapping(
        "GET",
        "/cv-tailoring/{cvTailoringId}",
        "cv_tailoring_handler.py",
        ("path.startswith('/cv-tailoring/') and path != '/cv-tailoring/generate'",),
        auth_markers=("_get_user_id(event)", "HTTPStatus.UNAUTHORIZED"),
    ),
    EndpointHandlerMapping(
        "GET",
        "/users/me/tailored-cvs",
        "cv_tailoring_handler.py",
        ("path == '/users/me/tailored-cvs'",),
        auth_markers=("_get_user_id(event)", "HTTPStatus.UNAUTHORIZED"),
    ),
    EndpointHandlerMapping(
        "POST",
        "/cover-letter/generate",
        "cover_letter_handler.py",
        ("path == '/cover-letter/generate'",),
        auth_markers=("_extract_authenticated_user_id(event)",),
    ),
    EndpointHandlerMapping(
        "GET",
        "/cover-letter/{coverLetterId}",
        "cover_letter_handler.py",
        ("path.startswith('/cover-letter/') and path != '/cover-letter/generate'",),
        auth_markers=(
            "_extract_authenticated_user_id(event)",
            "HTTPStatus.UNAUTHORIZED",
        ),
    ),
    EndpointHandlerMapping(
        "GET",
        "/users/me/cover-letters",
        "cover_letter_handler.py",
        ("path == '/users/me/cover-letters'",),
        auth_markers=(
            "_extract_authenticated_user_id(event)",
            "HTTPStatus.UNAUTHORIZED",
        ),
    ),
    EndpointHandlerMapping(
        "POST",
        "/interview-prep/generate",
        "interview_prep_handler.py",
        ("path == '/interview-prep/generate'",),
        auth_markers=("_extract_authenticated_user_id(event)",),
    ),
    EndpointHandlerMapping(
        "GET",
        "/interview-prep/{interviewPrepId}",
        "interview_prep_handler.py",
        ("path.startswith('/interview-prep/') and path != '/interview-prep/generate'",),
        auth_markers=(
            "_extract_authenticated_user_id(event)",
            "HTTPStatus.UNAUTHORIZED",
        ),
    ),
    EndpointHandlerMapping(
        "POST",
        "/company-research/fetch",
        "company_research_handler.py",
        ("Handle POST /company-research/fetch requests.",),
        auth_markers=("_extract_authenticated_user_id(event)",),
    ),
    EndpointHandlerMapping(
        "GET",
        "/company-research/{jobId}",
        "company_research_handler.py",
        (
            "path.startswith('/company-research/') and path != '/company-research/fetch'",
        ),
        auth_markers=(
            "_extract_authenticated_user_id(event)",
            "HTTPStatus.UNAUTHORIZED",
        ),
    ),
    EndpointHandlerMapping(
        "GET", "/health", "health_handler.py", ("path == '/health'",)
    ),
)


@dataclass
class ValidationReport:
    total_endpoints: int
    covered_endpoints: int
    missing_endpoint_mappings: list[str]
    extra_endpoint_mappings: list[str]
    missing_handlers: list[str]
    missing_route_markers: dict[str, list[str]]
    missing_request_schemas: list[str]
    missing_response_schemas: list[str]
    status_mismatches: list[str]
    auth_security_mismatches: list[str]
    auth_handler_mismatches: dict[str, list[str]]

    def is_success(self) -> bool:
        return not any(
            (
                self.missing_endpoint_mappings,
                self.extra_endpoint_mappings,
                self.missing_handlers,
                self.missing_route_markers,
                self.missing_request_schemas,
                self.missing_response_schemas,
                self.status_mismatches,
                self.auth_security_mismatches,
                self.auth_handler_mismatches,
            )
        )


def _load_openapi_spec() -> dict[str, Any]:
    with OPENAPI_PATH.open("r", encoding="utf-8") as file_obj:
        loaded = yaml.safe_load(file_obj)
    if not isinstance(loaded, dict):
        raise RuntimeError(f"Unable to parse OpenAPI spec at {OPENAPI_PATH}")
    return loaded


def _iter_operations(openapi: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    operations: dict[tuple[str, str], dict[str, Any]] = {}
    paths = openapi.get("paths", {})
    if not isinstance(paths, dict):
        return operations

    for path, methods in paths.items():
        if not isinstance(path, str) or not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            method_lower = str(method).lower()
            if method_lower not in HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            operations[(method_lower.upper(), path)] = operation
    return operations


def _iter_schema_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            refs.add(ref.rsplit("/", 1)[-1])
        for child in value.values():
            refs.update(_iter_schema_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.update(_iter_schema_refs(child))
    return refs


def _collect_request_schema_refs(
    operations: dict[tuple[str, str], dict[str, Any]],
) -> set[str]:
    refs: set[str] = set()
    for operation in operations.values():
        refs.update(_iter_schema_refs(operation.get("requestBody")))
    return refs


def _collect_response_schema_refs(
    operations: dict[tuple[str, str], dict[str, Any]],
) -> set[str]:
    refs: set[str] = set()
    for operation in operations.values():
        refs.update(_iter_schema_refs(operation.get("responses")))
    return refs


def _extract_api_model_class_names() -> set[str]:
    tree = ast.parse(API_MODELS_PATH.read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.ClassDef)}


def _success_status_codes(operation: dict[str, Any]) -> set[str]:
    responses = operation.get("responses")
    if not isinstance(responses, dict):
        return set()
    return {
        code
        for code in responses
        if isinstance(code, str)
        and len(code) == 3
        and code.isdigit()
        and code.startswith("2")
    }


def _status_markers_for_operation(method: str, success_codes: set[str]) -> set[str]:
    markers: set[str] = set()
    for code in success_codes:
        markers.update(HTTP_STATUS_MARKERS.get(code, ()))

    # POST handlers in this codebase can return 200/201/202 depending on workflow stage.
    if method == "POST":
        for code in ("200", "201", "202"):
            markers.update(HTTP_STATUS_MARKERS.get(code, ()))

    return markers


def _contains_any_marker(source: str, markers: set[str]) -> bool:
    return any(marker in source for marker in markers)


def build_validation_report() -> ValidationReport:
    openapi = _load_openapi_spec()
    operations = _iter_operations(openapi)
    operation_keys = set(operations)

    endpoint_map = {(entry.method, entry.path): entry for entry in ENDPOINT_HANDLER_MAP}
    mapped_keys = set(endpoint_map)

    missing_endpoint_mappings = sorted(
        f"{method} {path}" for method, path in (operation_keys - mapped_keys)
    )
    extra_endpoint_mappings = sorted(
        f"{method} {path}" for method, path in (mapped_keys - operation_keys)
    )

    missing_handlers: list[str] = []
    missing_route_markers: dict[str, list[str]] = {}
    auth_handler_mismatches: dict[str, list[str]] = {}
    status_mismatches: list[str] = []

    covered_endpoints = 0

    for method, path in sorted(operation_keys):
        mapping = endpoint_map.get((method, path))
        if mapping is None:
            continue

        handler_path = HANDLERS_DIR / mapping.handler_file
        endpoint_label = f"{method} {path}"

        if not handler_path.exists():
            missing_handlers.append(str(handler_path))
            continue

        source = handler_path.read_text(encoding="utf-8")
        missing_markers = [
            marker for marker in mapping.route_markers if marker not in source
        ]
        if missing_markers:
            missing_route_markers[endpoint_label] = missing_markers
            continue

        operation = operations[(method, path)]
        success_codes = _success_status_codes(operation)
        if not success_codes:
            status_mismatches.append(
                f"{endpoint_label}: no 2xx success response defined in OpenAPI"
            )
        else:
            status_markers = _status_markers_for_operation(method, success_codes)
            if status_markers and not _contains_any_marker(source, status_markers):
                status_mismatches.append(
                    f"{endpoint_label}: handler missing success-status marker for {sorted(success_codes)}"
                )

        if (method, path) in ASYNC_ENDPOINTS and "202" not in success_codes:
            status_mismatches.append(
                f"{endpoint_label}: async endpoint missing 202 response in OpenAPI"
            )

        expected_secure = (method, path) not in PUBLIC_ENDPOINTS
        security = operation.get("security")
        has_bearer_auth = isinstance(security, list) and any(
            isinstance(item, dict) and "BearerAuth" in item for item in security
        )

        if expected_secure and not has_bearer_auth:
            auth_handler_mismatches.setdefault(endpoint_label, []).append(
                "OpenAPI missing BearerAuth security declaration"
            )
        if not expected_secure and has_bearer_auth:
            auth_handler_mismatches.setdefault(endpoint_label, []).append(
                "OpenAPI should not require auth for this endpoint"
            )

        if expected_secure:
            missing_auth_markers = [
                marker for marker in mapping.auth_markers if marker not in source
            ]
            if missing_auth_markers:
                auth_handler_mismatches.setdefault(endpoint_label, []).extend(
                    missing_auth_markers
                )

        if (
            endpoint_label not in missing_route_markers
            and endpoint_label not in auth_handler_mismatches
            and endpoint_label
            not in {mismatch.split(":", 1)[0] for mismatch in status_mismatches}
        ):
            covered_endpoints += 1

    request_refs = _collect_request_schema_refs(operations)
    response_refs = _collect_response_schema_refs(operations)
    api_model_classes = _extract_api_model_class_names()

    missing_request_schemas = sorted(
        schema_name
        for schema_name in request_refs
        if schema_name not in api_model_classes
    )
    missing_response_schemas = sorted(
        schema_name
        for schema_name in response_refs
        if schema_name not in api_model_classes
    )

    auth_security_mismatches = sorted(
        f"{method} {path}"
        for (method, path), operation in operations.items()
        if (
            (method, path) in PUBLIC_ENDPOINTS
            and isinstance(operation.get("security"), list)
        )
        or (
            (method, path) not in PUBLIC_ENDPOINTS
            and not (
                isinstance(operation.get("security"), list)
                and any(
                    isinstance(item, dict) and "BearerAuth" in item
                    for item in operation["security"]
                )
            )
        )
    )

    # Endpoint coverage is route-marker based. Keep schema/auth/status mismatches separate.
    covered_endpoints = (
        len(operation_keys)
        - len(missing_endpoint_mappings)
        - len(missing_route_markers)
        - len(missing_handlers)
    )

    return ValidationReport(
        total_endpoints=len(operation_keys),
        covered_endpoints=covered_endpoints,
        missing_endpoint_mappings=missing_endpoint_mappings,
        extra_endpoint_mappings=extra_endpoint_mappings,
        missing_handlers=sorted(set(missing_handlers)),
        missing_route_markers=missing_route_markers,
        missing_request_schemas=missing_request_schemas,
        missing_response_schemas=missing_response_schemas,
        status_mismatches=status_mismatches,
        auth_security_mismatches=auth_security_mismatches,
        auth_handler_mismatches=auth_handler_mismatches,
    )


def _print_human_report(report: ValidationReport) -> None:
    print("OpenAPI Coverage Report")
    print("-----------------------")
    print(f"Coverage: {report.covered_endpoints}/{report.total_endpoints}")

    if report.missing_endpoint_mappings:
        print("Missing endpoint mappings:")
        for entry in report.missing_endpoint_mappings:
            print(f"  - {entry}")

    if report.extra_endpoint_mappings:
        print("Extra endpoint mappings:")
        for entry in report.extra_endpoint_mappings:
            print(f"  - {entry}")

    if report.missing_handlers:
        print("Missing handler files:")
        for entry in report.missing_handlers:
            print(f"  - {entry}")

    if report.missing_route_markers:
        print("Missing route markers:")
        for endpoint, markers in sorted(report.missing_route_markers.items()):
            print(f"  - {endpoint}")
            for marker in markers:
                print(f"    * {marker}")

    if report.missing_request_schemas:
        print("Missing request schema models:")
        for schema in report.missing_request_schemas:
            print(f"  - {schema}")

    if report.missing_response_schemas:
        print("Missing response schema models:")
        for schema in report.missing_response_schemas:
            print(f"  - {schema}")

    if report.status_mismatches:
        print("Status mismatches:")
        for mismatch in report.status_mismatches:
            print(f"  - {mismatch}")

    if report.auth_security_mismatches:
        print("Auth security mismatches:")
        for mismatch in report.auth_security_mismatches:
            print(f"  - {mismatch}")

    if report.auth_handler_mismatches:
        print("Auth handler mismatches:")
        for endpoint, mismatches in sorted(report.auth_handler_mismatches.items()):
            print(f"  - {endpoint}")
            for mismatch in mismatches:
                print(f"    * {mismatch}")

    if report.is_success():
        print("Result: PASS")
    else:
        print("Result: FAIL")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate OpenAPI coverage and contract consistency"
    )
    parser.add_argument("--json", action="store_true", help="Print report as JSON")
    args = parser.parse_args()

    report = build_validation_report()

    if args.json:
        print(json.dumps(asdict(report), indent=2, sort_keys=True))
    else:
        _print_human_report(report)

    return 0 if report.is_success() else 1


if __name__ == "__main__":
    raise SystemExit(main())
