"""Fail-fast resolution of table environment variables.

A handler that cannot reach its table must fail loudly. It must never degrade
to a no-op that returns a success shape — that is how
``careervp-artifact-cleanup-lambda-devx`` answered ``{'status': 'ok',
'cleaned': 0}`` 57 consecutive times for a total configuration failure, with
zero errors on its CloudWatch metric and nothing to alarm on.

Silent degradation is indistinguishable from "there was nothing to do". A
raised exception is not.
"""

from __future__ import annotations

import os


class MissingTableEnvError(RuntimeError):
    """A required table environment variable is unset or blank."""


def require_table_env(*env_keys: str, purpose: str) -> str:
    """Return the first non-empty value among ``env_keys``, or raise.

    ``purpose`` names what the table is for, so the failure says which wiring
    is missing rather than only which variable is blank.
    """
    if not env_keys:
        raise ValueError('require_table_env needs at least one environment variable name')

    for env_key in env_keys:
        value = os.environ.get(env_key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    raise MissingTableEnvError(f'{purpose} table is not configured: none of {", ".join(env_keys)} is set')
