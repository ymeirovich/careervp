"""Unit tests for REFACTOR3 artifact bootstrap inventory."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
REFACTOR3_DIR = PROJECT_ROOT / 'docs' / 'refactor3'


REQUIRED_SPECS = [
    'api_contract_spec.yaml',
    'auth_and_authorizer_spec.yaml',
    'route_mapping_spec.yaml',
    'async_flow_spec.yaml',
    'dal_alignment_spec.yaml',
    'validation_spec.yaml',
    'release_gate_spec.yaml',
]

REQUIRED_VALIDATIONS = [
    'phase_exit_gates.md',
    'endpoint_2xx_scorecard.md',
    'deployment_validation.md',
]


def test_payload_contract_count_is_27() -> None:
    payload_files = sorted((REFACTOR3_DIR / 'payloads').glob('*.json'))
    assert len(payload_files) == 27, f'Expected 27 payload contracts, found {len(payload_files)}'


def test_required_refactor3_specs_exist() -> None:
    specs_dir = REFACTOR3_DIR / 'specs'
    missing = [name for name in REQUIRED_SPECS if not (specs_dir / name).is_file()]
    assert not missing, f'Missing required spec files: {missing}'


def test_required_refactor3_validation_docs_exist() -> None:
    validations_dir = REFACTOR3_DIR / 'validations'
    missing = [name for name in REQUIRED_VALIDATIONS if not (validations_dir / name).is_file()]
    assert not missing, f'Missing required validation files: {missing}'
