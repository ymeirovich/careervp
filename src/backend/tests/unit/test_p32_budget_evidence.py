"""P-32 Wave 0 RED tests: Budgets + Cost Anomaly Detection console evidence.

The Wave 0 slice of P-32 is human console work (AWS Budgets + Cost Anomaly
Detection) — it is not expressed in CDK (see specs/P-32-cost-obs-edge-spec.md,
Fix Plan item 4: "Do not store console-only configuration as fake CDK code").
The only automatable net is an evidence validator that fails closed until a
human pastes the budget name/threshold/subscriber and the anomaly monitor +
subscription ARNs. See ``scripts/deploy_evidence.py``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[2] / 'scripts' / 'deploy_evidence.py'
_spec = importlib.util.spec_from_file_location('deploy_evidence', _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
deploy_evidence = importlib.util.module_from_spec(_spec)
sys.modules['deploy_evidence'] = deploy_evidence
_spec.loader.exec_module(deploy_evidence)

validate_budget = deploy_evidence.validate_budget_evidence
validate_anomaly = deploy_evidence.validate_cost_anomaly_evidence


def test_p32_budget_console_evidence_required():
    evidence = {
        'aws_budget': {
            'budget_name': 'careervp-dev-monthly',
            'threshold_amount': 500,
            'subscriber': 'careervp-alerts-dev@careervp.com',
            'captured_at': '2026-07-12T00:00:00Z',
        }
    }
    assert validate_budget(evidence) == []


def test_p32_budget_gate_fails_closed_when_evidence_missing():
    assert validate_budget({}) != []
    assert validate_budget({'aws_budget': {}}) != []


def test_p32_budget_gate_fails_closed_on_partial_evidence():
    partial = {
        'aws_budget': {
            'budget_name': 'careervp-dev-monthly',
            # threshold_amount, subscriber, captured_at all missing
        }
    }
    errors = validate_budget(partial)
    assert errors != []
    assert any('threshold_amount' in e for e in errors)
    assert any('subscriber' in e for e in errors)
    assert any('captured_at' in e for e in errors)


def test_p32_cost_anomaly_evidence_required():
    evidence = {
        'cost_anomaly_detection': {
            'monitor_arn': 'arn:aws:ce::788159322332:anomalymonitor/abc123',
            'subscription_arn': 'arn:aws:ce::788159322332:anomalysubscription/def456',
            'captured_at': '2026-07-12T00:00:00Z',
        }
    }
    assert validate_anomaly(evidence) == []


def test_p32_cost_anomaly_gate_fails_closed_when_evidence_missing():
    assert validate_anomaly({}) != []
    assert validate_anomaly({'cost_anomaly_detection': {}}) != []
