"""P-21 RED test: subscription-confirmation evidence must gate the deploy.

Email subscriptions require a human inbox confirmation that CDK cannot assert.
The deploy gate stays blocked until a ``Confirmed`` subscription ARN is recorded
(AC-P21-2). See ``scripts/deploy_evidence.py``.
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

validate = deploy_evidence.validate_sns_subscription_confirmed


def test_p21_subscription_confirmation_evidence_required():
    """A Confirmed subscription with an ARN passes the gate."""
    evidence = {
        'sns_subscriptions': [
            {
                'subscription_arn': 'arn:aws:sns:us-east-1:788159322332:careervp-monitoring:abc',
                'status': 'Confirmed',
                'endpoint': 'careervp-alerts-dev@careervp.com',
            }
        ]
    }
    assert validate(evidence) == []


def test_p21_gate_fails_closed_when_evidence_missing():
    assert validate({}) != []
    assert validate({'sns_subscriptions': []}) != []


def test_p21_pending_confirmation_does_not_satisfy_gate():
    evidence = {
        'sns_subscriptions': [
            {
                'subscription_arn': 'PendingConfirmation',
                'status': 'PendingConfirmation',
                'endpoint': 'careervp-alerts-dev@careervp.com',
            }
        ]
    }
    assert validate(evidence) != []
