"""A handler that cannot reach its table must fail loudly, never report success.

Live archetype (audit N5): ``careervp-artifact-cleanup-lambda-devx`` has no
``DYNAMODB_TABLE_NAME``. It logged ``No jobs table configured — reaper
skipping`` and returned ``{'status': 'ok', 'cleaned': 0}`` on 57 consecutive
scheduled runs, with 0 errors on its CloudWatch metric. A total configuration
failure was reported as a clean sweep, so nothing could alarm on it.

These tests pin the inverse: a blank table variable raises, and the raise is
not folded back into a returned status shape.
"""

from __future__ import annotations

from typing import Any

import pytest

from careervp.handlers.utils.env_guard import MissingTableEnvError, require_table_env


def test_require_table_env_returns_first_non_empty_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('CAREERVP_TEST_PRIMARY', raising=False)
    monkeypatch.setenv('CAREERVP_TEST_FALLBACK', '  careervp-fallback-table  ')

    resolved = require_table_env('CAREERVP_TEST_PRIMARY', 'CAREERVP_TEST_FALLBACK', purpose='test')

    assert resolved == 'careervp-fallback-table'


@pytest.mark.parametrize('blank', ['', '   '])
def test_require_table_env_raises_when_unset_or_blank(blank: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('CAREERVP_TEST_PRIMARY', blank)

    with pytest.raises(MissingTableEnvError) as excinfo:
        require_table_env('CAREERVP_TEST_PRIMARY', purpose='jobs')

    assert 'jobs' in str(excinfo.value)
    assert 'CAREERVP_TEST_PRIMARY' in str(excinfo.value)


def test_cleanup_reaper_raises_instead_of_reporting_ok_when_jobs_table_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The N5 regression: this call used to return {'status': 'ok', 'cleaned': 0}."""
    from careervp.handlers import artifact_cleanup_handler

    monkeypatch.setenv('APPLICATIONS_TABLE_NAME', 'careervp-applications-table-test')
    monkeypatch.delenv('DYNAMODB_TABLE_NAME', raising=False)

    with pytest.raises(MissingTableEnvError):
        artifact_cleanup_handler.lambda_handler({}, _context())


def test_cleanup_reaper_raises_when_applications_table_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    from careervp.handlers import artifact_cleanup_handler

    monkeypatch.delenv('APPLICATIONS_TABLE_NAME', raising=False)
    monkeypatch.setenv('DYNAMODB_TABLE_NAME', 'careervp-jobs-table-test')

    with pytest.raises(MissingTableEnvError):
        artifact_cleanup_handler.lambda_handler({}, _context())


def _context() -> Any:
    class _LambdaContext:
        function_name = 'careervp-artifact-cleanup-lambda-test'
        memory_limit_in_mb = 128
        invoked_function_arn = 'arn:aws:lambda:us-east-1:000000000000:function:test'
        aws_request_id = 'test-request-id'

    return _LambdaContext()
