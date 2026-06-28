"""Unit-test-level VPR helpers (fixtures defined in tests/conftest.py)."""

from __future__ import annotations

import json
from typing import Any

from careervp.models.result import Result, ResultCode


def mock_llm_result(payload: dict[str, Any]) -> Result[dict[str, Any]]:
    """Wrap a dict payload as a successful LLM Result."""
    return Result(
        success=True,
        data={
            'text': json.dumps(payload),
            'input_tokens': 100,
            'output_tokens': 200,
            'cost': 0.003,
            'model': 'claude-sonnet-4-6',
        },
        code=ResultCode.SUCCESS,
    )


def mock_llm_failure(error: str = 'LLM timeout') -> Result[None]:
    """Return a failed LLM Result."""
    return Result(success=False, data=None, code=ResultCode.LLM_TIMEOUT, error=error)
