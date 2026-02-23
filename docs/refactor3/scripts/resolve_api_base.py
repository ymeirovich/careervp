#!/usr/bin/env python3
"""
API_BASE Resolution Helper

Single source of truth for resolving the API_BASE URL for live tests.
Resolution order:
  1. ENV variable: API_BASE
  2. CloudFormation stack output: ApiGateway or Apigateway
  3. Fail if neither is set

No hardcoded production default URL.
"""

import os
import sys
from typing import Optional

import boto3
import botocore.exceptions


# Default stack name - can be overridden via ENV.
# Keep common stack names for local runs where STACK_NAME is not set.
STACK_NAME = os.environ.get("STACK_NAME", "CareerVpCrudDev")
FALLBACK_STACK_NAMES = ("CareerVpCrudDev", "careervp-api")


def get_api_base_from_environment() -> Optional[str]:
    """Check for API_BASE in environment variables."""
    api_base = os.environ.get("API_BASE")
    if api_base:
        return api_base.rstrip("/")
    return None


def _extract_api_base_from_outputs(outputs: list[dict[str, str]]) -> Optional[str]:
    """Extract API base URL from CloudFormation outputs."""
    # Look for ApiGateway first (REST API), then Apigateway (HTTP API)
    for output_key in ["ApiGateway", "Apigateway", "ApiUrl", "Endpoint"]:
        for output in outputs:
            if output.get("OutputKey") == output_key:
                url = output.get("OutputValue")
                if url:
                    return url.rstrip("/")

    # Also check for any output containing API Gateway host pattern
    for output in outputs:
        url = output.get("OutputValue", "")
        if "execute-api" in url:
            return url.rstrip("/")

    return None


def _candidate_stack_names() -> list[str]:
    """Build ordered unique stack-name candidates for lookup."""
    candidates: list[str] = []
    for name in (STACK_NAME, *FALLBACK_STACK_NAMES):
        if name and name not in candidates:
            candidates.append(name)
    return candidates


def get_api_base_from_cloudformation(stack_name: str = STACK_NAME) -> Optional[str]:
    """
    Get API_BASE from CloudFormation stack outputs.

    Looks for:
    - ApiGateway (API Gateway REST API)
    - Apigateway (API Gateway v2 HTTP API)

    Args:
        stack_name: CloudFormation stack name

    Returns:
        API base URL from stack outputs, or None if not found

    Raises:
        RuntimeError: If AWS credentials are missing or stack doesn't exist
    """
    client = boto3.client("cloudformation", region_name="us-east-1")
    # Preserve explicit caller arg first, then try common fallbacks.
    stack_candidates = [stack_name, *_candidate_stack_names()]
    deduped_candidates: list[str] = []
    for candidate in stack_candidates:
        if candidate and candidate not in deduped_candidates:
            deduped_candidates.append(candidate)

    for candidate in deduped_candidates:
        try:
            response = client.describe_stacks(StackName=candidate)
        except botocore.exceptions.ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code == "ValidationError":
                # Stack name not found. Continue to next candidate.
                continue
            raise RuntimeError(
                f"Failed to describe CloudFormation stack '{candidate}': {e}"
            ) from e
        except botocore.exceptions.BotoCoreError as e:
            raise RuntimeError(
                f"Failed to describe CloudFormation stack '{candidate}': {e}"
            ) from e

        stacks = response.get("Stacks", [])
        if not stacks:
            continue

        outputs = stacks[0].get("Outputs", [])
        api_base = _extract_api_base_from_outputs(outputs)
        if api_base:
            return api_base

    return None


def resolve_api_base() -> str:
    """
    Resolve API_BASE using the standard resolution order.

    Resolution order:
      1. ENV variable: API_BASE
      2. CloudFormation stack output: ApiGateway or Apigateway
      3. Fail if neither is set

    Returns:
        Resolved API base URL

    Raises:
        RuntimeError: If API_BASE cannot be resolved
    """
    # Step 1: Check environment variable
    env_api_base = get_api_base_from_environment()
    if env_api_base:
        return env_api_base.rstrip("/")

    # Step 2: Try CloudFormation stack output
    cf_api_base = get_api_base_from_cloudformation()
    if cf_api_base:
        return cf_api_base

    # Step 3: Fail with clear error message
    raise RuntimeError(
        f"Cannot resolve API_BASE. "
        f"Set API_BASE environment variable or ensure CloudFormation stack "
        f"'{STACK_NAME}' has ApiGateway/Apigateway output."
    )


def print_resolved_api_base() -> str:
    """Print and return the resolved API_BASE."""
    api_base = resolve_api_base()
    print(f"Resolved API_BASE: {api_base}")
    return api_base


if __name__ == "__main__":
    try:
        print_resolved_api_base()
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
