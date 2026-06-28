"""
Category B — CR async worker canonical suite.

TEST-CHAIN-001 Category B backfill for FE-UI-030.

All cases are fully covered by the ad-hoc suite in the same package:
  tests/unit/test_company_research_worker_handler.py

Per TEST-DEBT-001 done_check ("consolidate rather than duplicate"), this file
intentionally contains no duplicate assertions.  The prescribed Category B
coverage map:

  confidence pass persists + signals          → TestConfidenceGate::test_website_scrape_passes_gate
  below-threshold → batchItemFailures         → TestConfidenceGate::test_web_search_below_threshold_retries
  hard-fail after max retries → cr_failed     → TestConfidenceGate::test_web_search_below_threshold_hard_fails_at_max_retries
  LLM_FALLBACK hard-fails immediately         → TestConfidenceGate::test_llm_fallback_always_hard_fails_immediately
  send_task_success when task_token present   → TestTaskTokenSignal::test_sends_task_success_when_token_and_chain_enabled
  send_task_failure(Error='CRHardFail')       → TestTaskTokenSignal::test_hard_fail_sends_task_failure_to_sfn
  idempotent second call is no-op             → TestIdempotency::test_skips_if_cr_already_completed
"""

import pytest


@pytest.mark.unit
def test_category_b_coverage_location() -> None:
    """Canary: verify the handler module and its public symbols are importable."""
    from careervp.handlers.company_research_worker_handler import (
        CRWorkerInput,
        RetryableError,
        _async_process_record,
        _hard_fail,
        _process_record,
        lambda_handler,
    )

    assert CRWorkerInput is not None
    assert RetryableError is not None
    assert callable(_hard_fail)
    assert callable(_process_record)
    assert callable(_async_process_record)
    assert callable(lambda_handler)
