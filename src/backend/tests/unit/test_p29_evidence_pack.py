"""P-29 RED tests: pre-deploy evidence snapshot pack.

Runs the collector offline with fixtures (no AWS access). See
``scripts/evidence_pack.py``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[2] / 'scripts' / 'evidence_pack.py'
_spec = importlib.util.spec_from_file_location('evidence_pack', _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
evidence_pack = importlib.util.module_from_spec(_spec)
sys.modules['evidence_pack'] = evidence_pack
_spec.loader.exec_module(evidence_pack)

REQUIRED_SECTIONS = evidence_pack.REQUIRED_SECTIONS


def test_p29_evidence_pack_contains_required_sections():
    evidence = evidence_pack.collect_evidence(evidence_pack.dry_run_sources())
    for section in REQUIRED_SECTIONS:
        assert section in evidence, f'missing section {section}'
    # must be JSON-serializable
    json.loads(json.dumps(evidence, default=str))


def test_p29_evidence_redacts_secret_values():
    evidence = evidence_pack.collect_evidence(evidence_pack.dry_run_sources())
    fn_env = evidence['lambda_env']['careervp-cv-upload-dev']
    # secret-like key name is preserved but its value is redacted
    assert 'TAVILY_API_KEY' in fn_env
    assert fn_env['TAVILY_API_KEY'] == '***REDACTED***'
    # non-secret value is untouched
    assert fn_env['TABLE_NAME'] == 'careervp-users-dev'


def test_p29_blocks_deploy_without_backup_arns():
    good = evidence_pack.collect_evidence(evidence_pack.dry_run_sources())
    assert evidence_pack.validate_evidence(good) == []

    no_backups = dict(good)
    no_backups['dynamodb_backups'] = []
    assert evidence_pack.validate_evidence(no_backups) != []

    missing_section = dict(good)
    del missing_section['cognito']
    assert evidence_pack.validate_evidence(missing_section) != []


def test_p29_records_next_public_api_url():
    evidence = evidence_pack.collect_evidence(evidence_pack.dry_run_sources())
    amplify = evidence['amplify']
    assert amplify['NEXT_PUBLIC_API_URL'] == 'https://api.dev.careervp.com'
    assert amplify['next_public_api_url_kind'] == 'custom_domain'
    assert evidence['timestamp']

    # AC-P29-3: the classifier distinguishes raw execute-api from custom domain
    assert evidence_pack.classify_api_url('https://abc123.execute-api.us-east-1.amazonaws.com/prod') == 'raw_execute_api'
    assert evidence_pack.classify_api_url('') == 'unknown'
