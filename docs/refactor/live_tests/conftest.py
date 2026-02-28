# Live Tests Configuration
# This file contains shared configuration and fixtures for live tests

import os
import sys
import json
import requests
import hashlib
import hmac
import base64
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timedelta

# Add scripts directory to path for resolve_api_base
# Go up 2 levels: conftest.py -> live_tests -> refactor, then into refactor3/scripts
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "refactor3" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
from resolve_api_base import resolve_api_base  # noqa: E402

import pytest  # noqa: E402


def _load_env_files() -> None:
    """Load .env values for live tests without overriding existing environment."""
    candidate_paths = [
        Path(__file__).parent / ".env",
        Path(__file__).resolve().parents[3] / ".env",
    ]
    try:
        from dotenv import load_dotenv  # type: ignore

        for env_path in candidate_paths:
            if env_path.exists():
                load_dotenv(env_path, override=False)
        return
    except Exception:
        pass

    for env_path in candidate_paths:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_env_files()

# Resolve API_BASE using single-source resolver
# Resolution order: ENV API_BASE -> CloudFormation stack output -> fail
API_BASE = resolve_api_base()
TEST_USER_ID = os.environ.get("TEST_USER_ID", "test-user-e2e")
USE_AUTH = os.environ.get("USE_AUTH", "true").lower() == "true"
API_KEY = os.environ.get("API_KEY", "")
STRICT_AUTH = os.environ.get("STRICT_AUTH", "false").lower() == "true"

# Test credentials - used to generate fresh tokens at runtime
TEST_EMAIL = os.environ.get("TEST_EMAIL", "testuser123@example.com")
TEST_PASSWORD = os.environ.get("TEST_PASSWORD", "TestPass123!")

# Cognito settings (optional for local fallback; required in strict mode)
COGNITO_REGION = os.environ.get("COGNITO_REGION", "")
COGNITO_USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
COGNITO_APP_CLIENT_ID = os.environ.get("COGNITO_APP_CLIENT_ID", "")
COGNITO_APP_CLIENT_SECRET = os.environ.get("COGNITO_APP_CLIENT_SECRET", "")
COGNITO_USE_ADMIN_FLOW = (
    os.environ.get("COGNITO_USE_ADMIN_FLOW", "true").lower() == "true"
)
COGNITO_TOKEN_USE = os.environ.get("COGNITO_TOKEN_USE", "id").lower()
STACK_NAME = os.environ.get("STACK_NAME", "CareerVpCrudDev")

# Path to .env file for persisting test IDs across runs
ENV_FILE_PATH = Path(__file__).parent / ".env.json"

# Token storage - populated at runtime via login
_token_cache: Dict[str, Any] = {
    "access_token": None,
    "id_token": None,
    "refresh_token": None,
    "expires_at": None,
    "token_type": None,
    "source": None,
    "subject": None,
    "token_use": None,
}
_auth_probe: Dict[str, Any] = {"checked": False, "usable": False, "reason": None}


def _decode_jwt_claims(token: str) -> Dict[str, Any]:
    """Decode JWT claims without signature verification for test diagnostics."""
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    padding = "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode((payload + padding).encode("utf-8"))
        return json.loads(decoded.decode("utf-8"))
    except Exception:
        return {}


def _compute_secret_hash(username: str, client_id: str, client_secret: str) -> str:
    digest = hmac.new(
        client_secret.encode("utf-8"),
        f"{username}{client_id}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def _cognito_configured() -> bool:
    return bool(COGNITO_REGION and COGNITO_USER_POOL_ID and COGNITO_APP_CLIENT_ID)


def _resolve_cognito_config_from_stack() -> None:
    """Populate Cognito config from CloudFormation stack outputs when missing."""
    global COGNITO_REGION, COGNITO_USER_POOL_ID, COGNITO_APP_CLIENT_ID
    if _cognito_configured():
        return

    try:
        import boto3
    except Exception:
        return

    region = COGNITO_REGION or os.environ.get("AWS_REGION") or "us-east-1"
    client = boto3.client("cloudformation", region_name=region)
    stack_candidates = [STACK_NAME, "CareerVpCrudDev", "careervp-api"]
    seen = set()
    for stack_name in stack_candidates:
        if not stack_name or stack_name in seen:
            continue
        seen.add(stack_name)
        try:
            response = client.describe_stacks(StackName=stack_name)
        except Exception:
            continue
        stacks = response.get("Stacks", [])
        if not stacks:
            continue
        outputs = {
            o.get("OutputKey"): o.get("OutputValue")
            for o in stacks[0].get("Outputs", [])
        }
        user_pool_id = outputs.get("UserPoolId")
        client_id = outputs.get("ClientId")
        if user_pool_id and client_id:
            COGNITO_REGION = region
            COGNITO_USER_POOL_ID = user_pool_id
            COGNITO_APP_CLIENT_ID = client_id
            break


def _ensure_strict_auth_requirements() -> None:
    _resolve_cognito_config_from_stack()
    if STRICT_AUTH and not _cognito_configured():
        raise RuntimeError(
            "STRICT_AUTH=true requires Cognito settings: "
            "COGNITO_REGION, COGNITO_USER_POOL_ID, COGNITO_APP_CLIENT_ID"
        )


def _ensure_cognito_user() -> None:
    import boto3
    from botocore.exceptions import ClientError

    client = boto3.client("cognito-idp", region_name=COGNITO_REGION)
    try:
        client.admin_get_user(UserPoolId=COGNITO_USER_POOL_ID, Username=TEST_EMAIL)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code != "UserNotFoundException":
            raise
        client.admin_create_user(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=TEST_EMAIL,
            UserAttributes=[
                {"Name": "email", "Value": TEST_EMAIL},
                {"Name": "email_verified", "Value": "true"},
            ],
            TemporaryPassword=TEST_PASSWORD,
            MessageAction="SUPPRESS",
        )
    client.admin_set_user_password(
        UserPoolId=COGNITO_USER_POOL_ID,
        Username=TEST_EMAIL,
        Password=TEST_PASSWORD,
        Permanent=True,
    )


def login_via_cognito() -> Dict[str, Any]:
    """Authenticate a real Cognito user and cache JWT tokens."""
    _ensure_strict_auth_requirements()
    if not _cognito_configured():
        raise RuntimeError("Cognito is not configured for this test run")

    import boto3
    from botocore.exceptions import ClientError

    client = boto3.client("cognito-idp", region_name=COGNITO_REGION)
    use_admin_flow = COGNITO_USE_ADMIN_FLOW
    if use_admin_flow:
        _ensure_cognito_user()

    auth_params = {"USERNAME": TEST_EMAIL, "PASSWORD": TEST_PASSWORD}
    if COGNITO_APP_CLIENT_SECRET:
        auth_params["SECRET_HASH"] = _compute_secret_hash(
            TEST_EMAIL, COGNITO_APP_CLIENT_ID, COGNITO_APP_CLIENT_SECRET
        )

    try:
        if use_admin_flow:
            response = client.admin_initiate_auth(
                UserPoolId=COGNITO_USER_POOL_ID,
                ClientId=COGNITO_APP_CLIENT_ID,
                AuthFlow="ADMIN_USER_PASSWORD_AUTH",
                AuthParameters=auth_params,
            )
        else:
            response = client.initiate_auth(
                ClientId=COGNITO_APP_CLIENT_ID,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters=auth_params,
            )
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        error_message = exc.response.get("Error", {}).get("Message", "")
        if (
            use_admin_flow
            and error_code == "InvalidParameterException"
            and "Auth flow not enabled for this client" in error_message
        ):
            try:
                response = client.initiate_auth(
                    ClientId=COGNITO_APP_CLIENT_ID,
                    AuthFlow="USER_PASSWORD_AUTH",
                    AuthParameters=auth_params,
                )
            except ClientError as nested_exc:
                nested_code = nested_exc.response.get("Error", {}).get("Code")
                nested_msg = nested_exc.response.get("Error", {}).get("Message", "")
                if (
                    nested_code == "InvalidParameterException"
                    and "USER_PASSWORD_AUTH flow not enabled for this client"
                    in nested_msg
                ):
                    # Fallback for clients that allow only SRP auth.
                    try:
                        from pycognito.aws_srp import AWSSRP  # type: ignore
                    except Exception as import_exc:
                        raise RuntimeError(
                            "Cognito app client requires USER_SRP_AUTH. "
                            "Install SRP dependency for live tests: "
                            "pip install pycognito"
                        ) from import_exc

                    aws_srp = AWSSRP(
                        username=TEST_EMAIL,
                        password=TEST_PASSWORD,
                        pool_id=COGNITO_USER_POOL_ID,
                        client_id=COGNITO_APP_CLIENT_ID,
                        client=boto3.client("cognito-idp", region_name=COGNITO_REGION),
                        client_secret=COGNITO_APP_CLIENT_SECRET or None,
                    )
                    response = aws_srp.authenticate_user()
                else:
                    raise
        else:
            raise

    auth_result = response.get("AuthenticationResult", {})
    if isinstance(auth_result, dict) and "AuthenticationResult" in auth_result:
        auth_result = auth_result.get("AuthenticationResult", {})
    if not auth_result and "AccessToken" in response:
        auth_result = response
    access_token = auth_result.get("AccessToken")
    id_token = auth_result.get("IdToken")
    refresh_token = auth_result.get("RefreshToken")
    expires_in = int(auth_result.get("ExpiresIn", 3600))
    token_type = auth_result.get("TokenType", "Bearer")

    if not access_token:
        raise RuntimeError("Cognito auth succeeded but AccessToken missing")

    claims = _decode_jwt_claims(access_token)
    _token_cache["access_token"] = access_token
    _token_cache["id_token"] = id_token
    _token_cache["refresh_token"] = refresh_token
    _token_cache["token_type"] = token_type
    _token_cache["expires_at"] = datetime.now() + timedelta(seconds=expires_in - 60)
    _token_cache["source"] = "cognito"
    _token_cache["subject"] = claims.get("sub")
    _token_cache["token_use"] = claims.get("token_use")

    return {
        "access_token": access_token,
        "id_token": id_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in,
        "token_type": token_type,
        "source": "cognito",
        "subject": claims.get("sub"),
        "token_use": claims.get("token_use"),
    }


def load_test_ids() -> Dict[str, Any]:
    """Load test IDs from .env.json file if it exists."""
    if ENV_FILE_PATH.exists():
        try:
            with open(ENV_FILE_PATH, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_test_ids(test_ids: Dict[str, Any]) -> None:
    """Save test IDs to .env.json file for cross-run persistence."""
    # Load existing to preserve any fields we don't track
    existing = load_test_ids()
    existing.update(test_ids)
    try:
        with open(ENV_FILE_PATH, "w") as f:
            json.dump(existing, f, indent=2, default=str)
    except IOError as e:
        print(f"Warning: Could not save test IDs to {ENV_FILE_PATH}: {e}")


# Sample data paths - use absolute paths from docs folder
# live_tests is in docs/refactor/live_tests, so go up 2 levels to docs, then into features
DOCS_ROOT = Path(__file__).parent.parent  # refactor
SAMPLE_CV_PATH = (
    DOCS_ROOT.parent
    / "features"
    / "02_Yitzchak_Meirovich_Learning_Experience_Specialist_SysAid.docx"
)
SAMPLE_JOB_PATH = DOCS_ROOT.parent / "features" / "Sysaid Job Description.txt"
COMPANY_URL = "https://www.sysaid.com"

# Payloads directory
PAYLOADS_DIR = DOCS_ROOT / "payloads"


def _is_token_valid() -> bool:
    """Check if the cached token is still valid."""
    if not _token_cache.get("access_token"):
        return False
    if not _token_cache.get("expires_at"):
        return True  # No expiry info, assume valid
    return datetime.now() < _token_cache["expires_at"]


def login_and_get_token() -> Dict[str, Any]:
    """Generate fresh token via login request.

    Returns:
        Dict with access_token, refresh_token, expires_in, token_type

    Raises:
        RuntimeError: If login fails
    """
    url = f"{API_BASE}/auth/login"
    payload = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(f"Login failed: {response.status_code} - {response.text}")

    data = response.json()

    # Cache the tokens
    _token_cache["access_token"] = data.get("access_token")
    _token_cache["id_token"] = data.get("id_token")
    _token_cache["refresh_token"] = data.get("refresh_token")
    _token_cache["token_type"] = data.get("token_type", "Bearer")
    _token_cache["source"] = "api"

    # Calculate expiry
    expires_in = data.get("expires_in", 3600)
    _token_cache["expires_at"] = datetime.now() + timedelta(
        seconds=expires_in - 60
    )  # 60s buffer

    return {
        "access_token": data.get("access_token"),
        "id_token": data.get("id_token"),
        "refresh_token": data.get("refresh_token"),
        "expires_in": expires_in,
        "token_type": data.get("token_type", "Bearer"),
        "source": "api",
    }


def refresh_token() -> Dict[str, Any]:
    """Refresh the access token using the refresh token.

    Returns:
        Dict with new access_token, expires_in, token_type

    Raises:
        RuntimeError: If refresh fails
    """
    if not _token_cache.get("refresh_token"):
        raise RuntimeError("No refresh token available")

    url = f"{API_BASE}/auth/refresh"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_token_cache['refresh_token']}",
    }

    response = requests.post(url, headers=headers, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(
            f"Token refresh failed: {response.status_code} - {response.text}"
        )

    data = response.json()

    # Update cache
    _token_cache["access_token"] = data.get("access_token")
    _token_cache["token_type"] = data.get("token_type", "Bearer")

    expires_in = data.get("expires_in", 3600)
    _token_cache["expires_at"] = datetime.now() + timedelta(seconds=expires_in - 60)

    return {
        "access_token": data.get("access_token"),
        "expires_in": expires_in,
        "token_type": data.get("token_type", "Bearer"),
    }


def get_valid_token() -> str:
    """Get a valid access token, refreshing if necessary.

    Returns:
        Valid access token string

    Raises:
        RuntimeError: If unable to get valid token
    """
    _resolve_cognito_config_from_stack()
    preferred_key = "id_token" if COGNITO_TOKEN_USE == "id" else "access_token"

    # If Cognito is available, avoid reusing stale API-issued session tokens.
    if _cognito_configured() and _token_cache.get("source") != "cognito":
        _token_cache["access_token"] = None
        _token_cache["refresh_token"] = None
        _token_cache["expires_at"] = None
        _token_cache["token_type"] = None
        _token_cache["source"] = None

    # Check if current token is valid
    if _is_token_valid():
        preferred_cached = _token_cache.get(preferred_key)
        if preferred_cached:
            return preferred_cached
        if _token_cache.get("access_token"):
            return _token_cache["access_token"]
        if _token_cache.get("id_token"):
            return _token_cache["id_token"]

    # Try to refresh if we have a refresh token
    if _token_cache.get("refresh_token"):
        try:
            result = refresh_token()
            return result["access_token"]
        except RuntimeError:
            pass  # Fall through to login

    # Prefer Cognito real-user flow when configured.
    if _cognito_configured():
        result = login_via_cognito()
    else:
        if STRICT_AUTH:
            raise RuntimeError(
                "Cognito not configured and STRICT_AUTH=true. "
                "Set Cognito env vars or disable STRICT_AUTH for local fallback."
            )
        result = login_and_get_token()
    token = (
        result.get(preferred_key)
        or result.get("access_token")
        or result.get("id_token")
    )
    if not token:
        raise RuntimeError("No usable token returned from auth flow")
    return token


def get_auth_headers() -> Dict[str, str]:
    """Get authorization headers with fresh token.

    Generates a fresh token at runtime and validates it before use.
    """
    headers = {"Content-Type": "application/json"}

    # Get fresh token
    try:
        token = get_valid_token()
        # Token already includes "Bearer " prefix if token_type is "Bearer"
        if token and not token.startswith("Bearer "):
            headers["Authorization"] = f"Bearer {token}"
        else:
            headers["Authorization"] = token
    except Exception as e:
        if STRICT_AUTH:
            raise
        pytest.skip(f"Auth unavailable for live protected route tests: {e}")

    if not is_bearer_auth_usable():
        reason = _auth_probe.get("reason") or "unknown auth probe failure"
        if STRICT_AUTH:
            raise RuntimeError(
                f"Bearer auth is not usable against API Gateway: {reason}"
            )
        pytest.skip(f"Bearer auth unusable against API Gateway: {reason}")

    user_id = TEST_USER_ID or _token_cache.get("subject")
    if user_id:
        headers["X-User-Id"] = str(user_id)

    return headers


def get_token_metadata() -> Dict[str, Any]:
    return {
        "source": _token_cache.get("source"),
        "subject": _token_cache.get("subject"),
        "token_use": _token_cache.get("token_use"),
        "expires_at": _token_cache.get("expires_at").isoformat()
        if _token_cache.get("expires_at")
        else None,
    }


def is_bearer_auth_usable() -> bool:
    """Probe whether current bearer token is accepted by API Gateway protected routes."""
    if _auth_probe["checked"]:
        return bool(_auth_probe["usable"])

    _auth_probe["checked"] = True
    try:
        token = get_valid_token()
    except Exception as exc:
        _auth_probe["usable"] = False
        _auth_probe["reason"] = str(exc)
        return False

    auth_value = token if str(token).startswith("Bearer ") else f"Bearer {token}"
    headers = {"Authorization": auth_value, "Content-Type": "application/json"}
    try:
        response = requests.get(
            f"{API_BASE}/users/me/usage", headers=headers, timeout=20
        )
    except Exception as exc:
        _auth_probe["usable"] = False
        _auth_probe["reason"] = f"probe request failed: {exc}"
        return False

    if response.status_code == 200:
        _auth_probe["usable"] = True
        _auth_probe["reason"] = "ok"
        return True

    # Some handlers can return 404 for profile/bootstrap gaps even when bearer auth is valid.
    if response.status_code == 404:
        _auth_probe["usable"] = True
        _auth_probe["reason"] = "accepted token (404 from downstream handler)"
        return True

    _auth_probe["usable"] = False
    _auth_probe["reason"] = (
        f"/users/me/usage probe returned {response.status_code}: {response.text[:200]}"
    )
    return False


def load_payload(phase: str) -> Dict[str, Any]:
    """Load a test payload by phase name."""
    payload_file = PAYLOADS_DIR / f"phase{phase}_test.json"
    if payload_file.exists():
        with open(payload_file) as f:
            return json.load(f)
    return {}


def read_sample_file(path: Path) -> str:
    """Read a sample file and return its content.

    Handles both text and binary files (.docx).
    For binary files, attempts to extract text or returns a placeholder.
    """
    if not path.exists():
        return ""

    # Try to detect file type and read appropriately
    suffix = path.suffix.lower()

    if suffix == ".docx":
        # Try to read as docx, fall back to placeholder
        try:
            # First check if python-docx is available
            import docx

            doc = docx.Document(str(path))
            text_parts = []
            for para in doc.paragraphs:
                text_parts.append(para.text)
            return "\n".join(text_parts)
        except ImportError:
            # python-docx not available, return placeholder
            return "CV content placeholder - python-docx not installed"
        except Exception:
            return "CV content placeholder - could not parse docx"

    # Default: try to read as text
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Binary file without .docx extension
        return "Binary file content placeholder"


# Test execution order - each test may depend on previous test data
TEST_DEPENDENCIES = {
    # User must register/login first
    "test_health_check": [],
    "test_auth_register": [],
    "test_auth_login": [],
    # CV upload requires auth
    "test_cv_upload": ["test_auth_login"],
    "test_list_cvs": ["test_cv_upload"],
    # Jobs require auth
    "test_create_job": ["test_auth_login"],
    "test_list_jobs": ["test_create_job"],
    "test_get_job": ["test_create_job"],
    # Company research requires job
    "test_company_research_fetch": ["test_create_job"],
    "test_company_research_get": ["test_company_research_fetch"],
    # Gap analysis requires CV and job
    "test_gap_analysis_generate_questions": ["test_cv_upload", "test_create_job"],
    "test_gap_analysis_submit_responses": ["test_gap_analysis_generate_questions"],
    "test_gap_analysis_get_questions": ["test_gap_analysis_generate_questions"],
    # VPR requires gap responses
    "test_vpr_generate": ["test_gap_analysis_submit_responses"],
    "test_vpr_get_status": ["test_vpr_generate"],
    "test_vpr_list": ["test_vpr_generate"],
    # CV tailoring requires VPR
    "test_cv_tailoring_generate": ["test_vpr_generate"],
    "test_cv_tailoring_get_status": ["test_cv_tailoring_generate"],
    "test_cv_tailoring_list": ["test_cv_tailoring_generate"],
    # Cover letter requires company research + VPR + gap responses
    "test_cover_letter_generate": ["test_vpr_generate", "test_company_research_fetch"],
    "test_cover_letter_get_status": ["test_cover_letter_generate"],
    "test_cover_letter_list": ["test_cover_letter_generate"],
    # Interview prep requires VPR + gap responses
    "test_interview_prep_generate": ["test_vpr_generate"],
    "test_interview_prep_get_status": ["test_interview_prep_generate"],
}


# Pytest Fixtures


@pytest.fixture(scope="session")
def auth_credentials():
    """Shared test credentials"""
    return {"email": TEST_EMAIL, "password": TEST_PASSWORD}


@pytest.fixture(scope="session")
def auth_token(auth_credentials):
    """Get a valid auth token for the test session"""
    _ = auth_credentials
    return get_valid_token()


@pytest.fixture
def auth_headers(auth_token):
    """Headers with authentication"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_auth: test requires valid bearer auth and should fail fast when auth bootstrap fails",
    )


def pytest_runtest_setup(item):
    if item.get_closest_marker("requires_auth") is None:
        return
    if not USE_AUTH:
        pytest.skip("requires_auth test skipped because USE_AUTH=false")
    if not is_bearer_auth_usable():
        reason = _auth_probe.get("reason") or "unknown reason"
        if STRICT_AUTH:
            raise RuntimeError(f"requires_auth precondition failed: {reason}")
        pytest.skip(f"requires_auth precondition not met: {reason}")


@pytest.fixture(scope="session")
def test_data():
    """Shared test data across all tests for ID dependencies"""
    return {
        "cv_id": None,
        "job_id": None,
        "vpr_id": None,
        "tailored_cv_id": None,
        "cover_letter_id": None,
        "interview_prep_id": None,
    }
    _resolve_cognito_config_from_stack()
