"""Rule-13 proof for the Wave-2 gate: its pure verdict logic must fail on purpose.

The gate's side effects (subprocess, AWS) are not exercised here; only the pure
:func:`gate_passed` predicate and the blocking semantics of each status, so the
test runs offline and deterministically.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import scripts.wave_gate as wave_gate
from scripts.wave_gate import Cmd, GateCheck, Status, gate_passed, run


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


def test_run_can_scrub_live_smoke_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('API_BASE', 'https://live.example.test')
    result = run(
        [sys.executable, '-c', 'import os; print(os.getenv("API_BASE", "missing"))'],
        cwd=Path.cwd(),
        remove_env=('API_BASE',),
    )

    assert result.returncode == 0
    assert result.stdout.strip() == 'missing'


def test_smoke_harness_writes_canonical_evidence_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(cmd: list[str], *, cwd: Path, timeout: int = 1200, remove_env: tuple[str, ...] = ()) -> Cmd:
        captured['cmd'] = cmd
        captured['cwd'] = cwd
        captured['timeout'] = timeout
        captured['remove_env'] = remove_env
        return Cmd(0, '', '')

    monkeypatch.setenv('API_BASE', 'https://api.example.test')
    monkeypatch.setenv('SMOKE_TOKEN', 'token')
    monkeypatch.setattr(wave_gate, 'run', fake_run)

    result = wave_gate.check_smoke_harness()

    assert result.status is Status.PASS
    assert captured['cmd'] == ['uv', 'run', 'python', 'scripts/smoke_harness.py', '--evidence-dir', str(wave_gate.EVIDENCE_DIR)]
    assert captured['cwd'] == wave_gate.BACKEND_DIR
