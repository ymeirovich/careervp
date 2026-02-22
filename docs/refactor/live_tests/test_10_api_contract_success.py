# Live Tests - Strict API Contract Success Suite
# Validates all 27 API endpoints using docs/refactor2/payloads/*.json contracts.

import copy
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import pytest
import requests

# Import configuration
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from conftest import API_BASE, save_test_ids
from test_01_auth_health import test_data


DOCS_ROOT = Path(__file__).resolve().parents[2]  # docs/
REFACTOR2_PAYLOADS_DIR = DOCS_ROOT / "refactor2" / "payloads"
LEGACY_PAYLOADS_DIR = DOCS_ROOT / "refactor" / "payloads"

STRICT_PAYLOAD_ORDER = [
    "health_check.json",
    "auth_register.json",
    "auth_login.json",
    "auth_refresh.json",
    "user_get.json",
    "user_update.json",
    "cv_upload.json",
    "cv_list.json",
    "job_create.json",
    "job_list.json",
    "job_get.json",
    "company_research_fetch.json",
    "company_research_get.json",
    "gap_questions_generate.json",
    "gap_responses_submit.json",
    "gap_questions_history.json",
    "vpr_generate.json",
    "vpr_status.json",
    "vpr_list.json",
    "cv_tailoring_generate.json",
    "cv_tailoring_status.json",
    "cv_tailoring_list.json",
    "cover_letter_generate.json",
    "cover_letter_status.json",
    "cover_letter_list.json",
    "interview_prep_generate.json",
    "interview_prep_status.json",
]

ASYNC_GENERATE_TO_STATUS = {
    "company_research_fetch.json": "company_research_get.json",
    "vpr_generate.json": "vpr_status.json",
    "cv_tailoring_generate.json": "cv_tailoring_status.json",
    "cover_letter_generate.json": "cover_letter_status.json",
    "interview_prep_generate.json": "interview_prep_status.json",
}

NO_AUTH_PAYLOADS = {
    "health_check.json",
    "auth_register.json",
    "auth_login.json",
}

PATH_PARAM_TO_STATE_KEY = {
    "jobId": "job_id",
    "vprId": "vpr_id",
    "cvTailoringId": "cv_tailoring_id",
    "coverLetterId": "cover_letter_id",
    "interviewPrepId": "interview_prep_id",
}


def _load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_refactor2_payload(filename: str) -> dict[str, Any]:
    path = REFACTOR2_PAYLOADS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing payload file: {path}")
    return _load_json(path)


def _load_legacy_context() -> dict[str, dict[str, Any]]:
    return {
        "phase1_vpr": _load_json(
            LEGACY_PAYLOADS_DIR / "phase1_vpr_generator_test.json"
        ),
        "phase2_gap": _load_json(LEGACY_PAYLOADS_DIR / "phase2_gap_analysis_test.json"),
        "phase3_tailoring": _load_json(
            LEGACY_PAYLOADS_DIR / "phase3_cv_tailoring_test.json"
        ),
        "phase4_cover": _load_json(
            LEGACY_PAYLOADS_DIR / "phase4_cover_letter_test.json"
        ),
        "phase6_interview": _load_json(
            LEGACY_PAYLOADS_DIR / "phase6_interview_prep_test.json"
        ),
        "phase8_company": _load_json(
            LEGACY_PAYLOADS_DIR / "phase8_company_research_test.json"
        ),
    }


def _print_exchange(
    payload_file: str,
    endpoint: str,
    method: str,
    request_body: Any,
    status_code: int,
    response_body: Any,
) -> None:
    output = {
        "payload_file": payload_file,
        "endpoint": endpoint,
        "method": method,
        "request": request_body,
        "status_code": status_code,
        "response": response_body,
    }
    print(f"\n=== STRICT CONTRACT RESPONSE {payload_file} ===")
    print(json.dumps(output, indent=2, default=str))


def _assert_shape(expected: Any, actual: Any, path: str = "response") -> None:
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path} must be an object"
        for key, value in expected.items():
            assert key in actual, f"Missing key at {path}: {key}"
            _assert_shape(value, actual[key], f"{path}.{key}")
        return

    if isinstance(expected, list):
        assert isinstance(actual, list), f"{path} must be an array"
        if expected and actual:
            _assert_shape(expected[0], actual[0], f"{path}[0]")
        return

    if expected is None:
        return

    assert isinstance(actual, type(expected)), (
        f"Type mismatch at {path}: expected {type(expected).__name__}, "
        f"got {type(actual).__name__}"
    )


def _resolve_path(payload: dict[str, Any], state: dict[str, Any]) -> str:
    path = payload["path"]
    for path_param, state_key in PATH_PARAM_TO_STATE_KEY.items():
        token = "{" + path_param + "}"
        if token in path:
            value = state.get(state_key)
            assert value, (
                f"Missing required state '{state_key}' to resolve path parameter "
                f"'{path_param}' for {path}"
            )
            path = path.replace(token, str(value))
    return path


def _hydrate_request(
    payload_file: str, request_body: dict[str, Any], state: dict[str, Any]
) -> dict[str, Any]:
    body = copy.deepcopy(request_body)

    if payload_file == "auth_register.json":
        unique_email = f"strict_{int(time.time())}_{uuid.uuid4().hex[:8]}@example.com"
        password = os.environ.get("TEST_PASSWORD", "TestPass123!")
        body["email"] = unique_email
        body["password"] = password
        state["user_email"] = unique_email
        state["user_password"] = password

    if payload_file == "auth_login.json":
        body["email"] = state["user_email"]
        body["password"] = state["user_password"]

    if payload_file == "auth_refresh.json":
        body = {}

    id_field_map = {
        "cv_id": "cv_id",
        "job_id": "job_id",
        "vpr_id": "vpr_id",
        "company_research_id": "company_research_id",
    }
    for request_field, state_key in id_field_map.items():
        if request_field in body and state.get(state_key):
            body[request_field] = state[state_key]

    if "gap_response_ids" in body and state.get("gap_response_ids"):
        body["gap_response_ids"] = state["gap_response_ids"]

    if payload_file == "gap_responses_submit.json":
        responses = body.get("responses", [])
        question_ids = state.get("gap_question_ids", [])
        for i, response_item in enumerate(responses):
            if i < len(question_ids):
                response_item["question_id"] = question_ids[i]

    if payload_file == "user_update.json":
        body["name"] = f"Strict Contract User {int(time.time())}"

    return body


def _update_state(
    payload_file: str,
    request_body: dict[str, Any],
    response_data: dict[str, Any],
    state: dict[str, Any],
) -> None:
    if payload_file in {"auth_register.json", "auth_login.json"}:
        if response_data.get("access_token"):
            state["access_token"] = response_data["access_token"]
        if response_data.get("refresh_token"):
            state["refresh_token"] = response_data["refresh_token"]

    if payload_file == "user_get.json" or payload_file == "user_update.json":
        if response_data.get("id"):
            state["user_id"] = response_data["id"]

    if payload_file == "cv_upload.json":
        state["cv_id"] = response_data.get("cv_id") or response_data.get("id")

    if payload_file == "job_create.json":
        state["job_id"] = response_data.get("id") or response_data.get("job_id")

    if payload_file == "company_research_fetch.json":
        state["company_research_id"] = (
            response_data.get("request_id")
            or response_data.get("company_research_id")
            or response_data.get("id")
        )

    if payload_file == "company_research_get.json" and response_data.get("id"):
        state["company_research_id"] = response_data["id"]

    if payload_file == "gap_questions_generate.json":
        questions = response_data.get("questions", [])
        question_ids = [q.get("id") for q in questions if q.get("id")]
        state["gap_question_ids"] = question_ids
        if question_ids:
            # Use question IDs as dependency handles for downstream APIs when
            # explicit response IDs are not returned by the backend.
            state["gap_response_ids"] = question_ids

    if payload_file == "gap_responses_submit.json":
        response_ids = response_data.get("response_ids")
        if isinstance(response_ids, list) and response_ids:
            state["gap_response_ids"] = response_ids
        elif not state.get("gap_response_ids"):
            state["gap_response_ids"] = state.get("gap_question_ids", [])

    if payload_file == "vpr_generate.json":
        state["vpr_id"] = response_data.get("request_id") or response_data.get("id")

    if payload_file == "vpr_status.json" and response_data.get("id"):
        state["vpr_id"] = response_data["id"]

    if payload_file == "cv_tailoring_generate.json":
        state["cv_tailoring_id"] = response_data.get("request_id") or response_data.get(
            "id"
        )

    if payload_file == "cv_tailoring_status.json" and response_data.get("id"):
        state["cv_tailoring_id"] = response_data["id"]

    if payload_file == "cover_letter_generate.json":
        state["cover_letter_id"] = response_data.get("request_id") or response_data.get(
            "id"
        )

    if payload_file == "cover_letter_status.json" and response_data.get("id"):
        state["cover_letter_id"] = response_data["id"]

    if payload_file == "interview_prep_generate.json":
        state["interview_prep_id"] = response_data.get(
            "request_id"
        ) or response_data.get("id")

    if payload_file == "interview_prep_status.json" and response_data.get("id"):
        state["interview_prep_id"] = response_data["id"]

    _sync_with_shared_test_data(state)


def _sync_with_shared_test_data(state: dict[str, Any]) -> None:
    tokens = test_data.setdefault("tokens", {})

    if state.get("access_token"):
        tokens["access"] = state["access_token"]
    if state.get("refresh_token"):
        tokens["refresh"] = state["refresh_token"]

    if state.get("user_id"):
        test_data["user_id"] = state["user_id"]
    if state.get("cv_id"):
        test_data["cv_id"] = state["cv_id"]
    if state.get("job_id"):
        test_data["job_id"] = state["job_id"]
    if state.get("vpr_id"):
        test_data["vpr_id"] = state["vpr_id"]
    if state.get("gap_response_ids"):
        test_data["gap_response_ids"] = state["gap_response_ids"]
    if state.get("company_research_id"):
        test_data["company_research_id"] = state["company_research_id"]
    if state.get("cv_tailoring_id"):
        test_data["cv_tailoring_id"] = state["cv_tailoring_id"]
    if state.get("cover_letter_id"):
        test_data["cover_letter_id"] = state["cover_letter_id"]
    if state.get("interview_prep_id"):
        test_data["interview_prep_id"] = state["interview_prep_id"]

    save_test_ids(test_data)


def _build_headers(payload_file: str, state: dict[str, Any]) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}

    if payload_file in NO_AUTH_PAYLOADS:
        return headers

    if payload_file == "auth_refresh.json":
        refresh_token = state.get("refresh_token")
        assert refresh_token, "Missing refresh_token for /auth/refresh"
        headers["Authorization"] = (
            refresh_token
            if str(refresh_token).startswith("Bearer ")
            else f"Bearer {refresh_token}"
        )
        return headers

    access_token = state.get("access_token")
    assert access_token, (
        f"Missing access_token for authenticated payload {payload_file}"
    )
    headers["Authorization"] = (
        access_token
        if str(access_token).startswith("Bearer ")
        else f"Bearer {access_token}"
    )
    if state.get("user_id"):
        headers["X-User-Id"] = str(state["user_id"])
    return headers


def _execute_payload(
    payload_file: str, state: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    payload = _load_refactor2_payload(payload_file)
    method = str(payload["method"]).upper()
    path = _resolve_path(payload, state)
    url = f"{API_BASE}{path}"
    request_body = _hydrate_request(
        payload_file, payload.get("request", {}) or {}, state
    )
    headers = _build_headers(payload_file, state)

    request_kwargs: dict[str, Any] = {
        "headers": headers,
        "timeout": 60,
    }
    if method in {"POST", "PUT", "PATCH"}:
        request_kwargs["json"] = request_body

    response = requests.request(method, url, **request_kwargs)
    try:
        response_data = response.json()
    except ValueError as exc:
        pytest.fail(
            f"{payload_file}: response body is not valid JSON "
            f"(status={response.status_code}): {response.text[:500]} ({exc})"
        )

    _print_exchange(
        payload_file=payload_file,
        endpoint=path,
        method=method,
        request_body=request_body,
        status_code=response.status_code,
        response_body=response_data,
    )

    expected_status = payload["expected_response"]["status_code"]
    assert response.status_code == expected_status, (
        f"{payload_file}: expected HTTP {expected_status}, got {response.status_code}"
    )
    _assert_shape(payload["expected_response"]["body"], response_data)

    return payload, request_body, response_data


def _poll_until_completed(
    status_payload_file: str,
    state: dict[str, Any],
    poll_interval_seconds: int = 5,
    max_attempts: int = 24,
) -> None:
    payload = _load_refactor2_payload(status_payload_file)
    method = str(payload["method"]).upper()
    assert method == "GET", f"Polling requires GET status endpoint, got {method}"

    path = _resolve_path(payload, state)
    url = f"{API_BASE}{path}"
    headers = _build_headers(status_payload_file, state)
    expected_status = payload["expected_response"]["status_code"]

    for attempt in range(1, max_attempts + 1):
        response = requests.get(url, headers=headers, timeout=30)
        try:
            data = response.json()
        except ValueError as exc:
            pytest.fail(
                f"{status_payload_file}: poll returned non-JSON response "
                f"(status={response.status_code}): {response.text[:500]} ({exc})"
            )

        _print_exchange(
            payload_file=f"{status_payload_file}::poll[{attempt}]",
            endpoint=path,
            method=method,
            request_body={},
            status_code=response.status_code,
            response_body=data,
        )

        assert response.status_code == expected_status, (
            f"{status_payload_file}: polling expected HTTP {expected_status}, "
            f"got {response.status_code}"
        )

        status_value = str(data.get("status", "completed")).lower()
        if not data.get("status") or status_value == "completed":
            _assert_shape(payload["expected_response"]["body"], data)
            _update_state(status_payload_file, {}, data, state)
            return

        if status_value in {"failed", "error"}:
            pytest.fail(
                f"{status_payload_file}: async operation failed: "
                f"{json.dumps(data, default=str)}"
            )

        time.sleep(poll_interval_seconds)

    pytest.fail(
        f"{status_payload_file}: async operation did not reach completed state after "
        f"{max_attempts * poll_interval_seconds} seconds"
    )


def _validate_quality(
    payload_file: str, response_data: dict[str, Any], legacy: dict[str, dict[str, Any]]
) -> None:
    if payload_file == "gap_questions_generate.json":
        gap_context = legacy["phase2_gap"]
        validation = (
            gap_context.get("expected", {}).get("validation", {})
            if isinstance(gap_context, dict)
            else {}
        )
        min_questions = int(validation.get("min_questions", 3))
        max_questions = int(validation.get("max_questions", 10))
        questions = response_data.get("questions", [])
        assert isinstance(questions, list), "gap questions must be an array"
        assert min_questions <= len(questions) <= max_questions, (
            f"expected between {min_questions} and {max_questions} gap questions, "
            f"got {len(questions)}"
        )
        for q in questions:
            assert q.get("tags"), "each gap question must include tags"
            assert q.get("strategic_intent"), (
                "each gap question must include strategic_intent"
            )

    if payload_file == "vpr_status.json":
        result = response_data.get("result", {})
        assert result.get("uvp"), "VPR must include non-empty uvp"
        differentiators = result.get("differentiators", [])
        assert isinstance(differentiators, list), "VPR differentiators must be an array"
        assert len(differentiators) >= 3, "VPR must include at least 3 differentiators"

    if payload_file == "cv_tailoring_status.json":
        result = response_data.get("result", {})
        if isinstance(result.get("ats_score"), (int, float)):
            assert result["ats_score"] >= 8.0, "cv-tailoring ats_score must be >= 8.0"
        fvs_validation = result.get("fvs_validation")
        if isinstance(fvs_validation, dict) and "is_valid" in fvs_validation:
            assert fvs_validation["is_valid"] is True, (
                "cv-tailoring fvs_validation must pass"
            )

    if payload_file == "cover_letter_status.json":
        cover_context = legacy["phase4_cover"]
        paragraph_rules = (
            cover_context.get("polling_validation", {})
            .get("result_validation", {})
            .get("paragraph_structure", {})
        )
        result = response_data.get("result", {})
        paragraphs = result.get("paragraphs", {})
        assert isinstance(paragraphs, dict), (
            "cover-letter result must include paragraphs"
        )

        hook = paragraphs.get("hook", {})
        hook_min = int(paragraph_rules.get("hook", {}).get("min_word_count", 80))
        hook_max = int(paragraph_rules.get("hook", {}).get("max_word_count", 100))
        if "word_count" in hook:
            assert hook_min <= int(hook["word_count"]) <= hook_max

        close = paragraphs.get("close", {})
        close_min = int(paragraph_rules.get("close", {}).get("min_word_count", 60))
        close_max = int(paragraph_rules.get("close", {}).get("max_word_count", 80))
        if "word_count" in close:
            assert close_min <= int(close["word_count"]) <= close_max

    if payload_file == "interview_prep_status.json":
        interview_context = legacy["phase6_interview"]
        min_questions = int(
            interview_context.get("validation", {}).get("min_questions", 8)
        )
        result = response_data.get("result", {})
        questions = result.get("questions", [])
        assert isinstance(questions, list), "interview-prep questions must be an array"
        assert len(questions) >= min_questions, (
            f"interview-prep must include at least {min_questions} questions"
        )
        for q in questions:
            suggested = q.get("suggested_answer", {})
            if isinstance(suggested, dict) and "format" in suggested:
                assert str(suggested["format"]).upper() == "STAR", (
                    "interview-prep suggested_answer.format must be STAR"
                )

    if payload_file == "company_research_get.json":
        company_context = legacy["phase8_company"]
        required_fields = company_context.get("validation", {}).get(
            "required_fields", []
        )
        for field in required_fields:
            assert response_data.get(field), (
                f"company-research missing required field: {field}"
            )


class TestAPIContractSuccess:
    """Strict payload-driven API contract suite."""

    def test_api_contract_success_for_all_27_endpoints(self):
        legacy = _load_legacy_context()
        state: dict[str, Any] = {
            "user_email": os.environ.get("TEST_EMAIL"),
            "user_password": os.environ.get("TEST_PASSWORD", "TestPass123!"),
        }

        for payload_file in STRICT_PAYLOAD_ORDER:
            payload, request_body, response_data = _execute_payload(payload_file, state)
            _update_state(payload_file, request_body, response_data, state)
            _validate_quality(payload_file, response_data, legacy)

            if payload_file in ASYNC_GENERATE_TO_STATUS:
                _poll_until_completed(ASYNC_GENERATE_TO_STATUS[payload_file], state)

            # Keep the state synchronized for next endpoint and other test modules.
            _sync_with_shared_test_data(state)

            # Guardrail: ensure expected_response contract is always present.
            assert payload.get("expected_response"), (
                f"{payload_file}: missing expected_response contract"
            )
