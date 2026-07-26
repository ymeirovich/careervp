"""Rule-13 proof for the Wave-2 gate: its pure verdict logic must fail on purpose.

The gate's side effects (subprocess, AWS) are not exercised here; only the pure
:func:`gate_passed` predicate and the blocking semantics of each status, so the
test runs offline and deterministically.
"""

from __future__ import annotations

from scripts.wave_gate import GateCheck, Status, gate_passed


def _c(status: Status) -> GateCheck:
    return GateCheck('x', status, 'detail')


def test_all_pass_gate_opens() -> None:
    assert gate_passed([_c(Status.PASS), _c(Status.PASS)]) is True


def test_recorded_never_blocks() -> None:
    # RECORDED (e.g. the five-bet ledger read) is informational, not a gate.
    assert gate_passed([_c(Status.PASS), _c(Status.RECORDED)]) is True


def test_single_fail_blocks() -> None:
    assert gate_passed([_c(Status.PASS), _c(Status.FAIL)]) is False


def test_unsatisfied_human_required_blocks() -> None:
    # A human-gated check with no evidence yet must hold the gate closed.
    assert gate_passed([_c(Status.PASS), _c(Status.HUMAN_REQUIRED)]) is False


def test_empty_is_vacuously_open() -> None:
    assert gate_passed([]) is True


def test_blocking_flags_per_status() -> None:
    assert _c(Status.FAIL).blocking is True
    assert _c(Status.HUMAN_REQUIRED).blocking is True
    assert _c(Status.PASS).blocking is False
    assert _c(Status.RECORDED).blocking is False
