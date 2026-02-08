"""Compatibility LLM client for CV tailoring tests."""

from __future__ import annotations

import json
from typing import Any, cast

import boto3

bedrock_client = boto3.client('bedrock-runtime')


class LLMClient:
    """Simple LLM client wrapper used by CV tailoring handler."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client or bedrock_client

    def generate(self, prompt: str, timeout: int = 300) -> dict[str, Any]:
        """Invoke Bedrock model and return parsed JSON payload."""
        _ = timeout
        response = self._client.invoke_model(
            body=json.dumps({'prompt': prompt}),
            modelId='claude-haiku-4-5-20251001',
        )
        body = response.get('body')
        if hasattr(body, 'read'):
            payload = body.read()
        else:
            payload = body
        if isinstance(payload, bytes):
            payload = payload.decode('utf-8')
        if isinstance(payload, str):
            return cast(dict[str, Any], json.loads(payload))
        return cast(dict[str, Any], payload)
