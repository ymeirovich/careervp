"""RED-first tests for clause P-28 — deploy identity safety + CI pipeline closure.

Spec: docs/db-redesign/code/code-analysis/project/specs/P-28-deploy-identity-spec.md

Covers:
  A) infra/app.py hard-pins account/region with a fail-fast on wrong-profile deploy.
  B) .github/workflows/deploy.yml: concurrency group=deploy, cancel-in-progress false.
  C) create-change-set (automation) vs execute-change-set (human-gated env) split.
  D) DescribeChangeSet Replacement report auto-fails on protected-type Replacement:True.
  E) scripts/ci/check_scope_lock_integrity.py rejects scope-lock edits lacking a
     §12 change-log row / version bump / twin-sync / approval trailer.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

# src/backend/tests/infra/ -> repo root
REPO_ROOT = Path(__file__).resolve().parents[4]
APP_PY = REPO_ROOT / 'infra' / 'app.py'
DEPLOY_YML = REPO_ROOT / '.github' / 'workflows' / 'deploy.yml'
SCOPE_LOCK_GUARD_YML = REPO_ROOT / '.github' / 'workflows' / 'scope-lock-guard.yml'
SCOPE_LOCK_SCRIPT = REPO_ROOT / 'scripts' / 'ci' / 'check_scope_lock_integrity.py'
REPLACEMENT_SCRIPT = REPO_ROOT / 'scripts' / 'ci' / 'changeset_replacement_report.py'

PINNED_ACCOUNT = '788159322332'


def _load_script(path: Path, name: str) -> ModuleType:
    assert path.exists(), f'P-28: script missing at {path}'
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------- Sub-clause A
def test_app_py_pins_account_and_region() -> None:
    text = APP_PY.read_text(encoding='utf-8')
    assert PINNED_ACCOUNT in text, 'P-28: app.py must hard-pin account 788159322332'
    assert '"us-east-1"' in text or "'us-east-1'" in text, 'P-28: app.py must hard-pin region us-east-1'
    # Must not silently fall back to ambient inference for the account.
    assert 'session.Session().region_name' not in text, 'P-28: the ambient session.region_name fallback must be removed'
    assert 'client("sts").get_caller_identity' not in text, 'P-28: the ambient STS account inference must be removed'


def test_app_py_fails_fast_on_wrong_account() -> None:
    """AC-P28-1: a mismatched CDK_DEFAULT_ACCOUNT must abort before synth."""
    text = APP_PY.read_text(encoding='utf-8')
    assert 'SystemExit' in text or 'raise' in text, 'P-28: app.py must fail fast (raise/SystemExit) on wrong account'
    assert 'P-28' in text, 'P-28: app.py fail-fast should be labelled P-28'


# ---------------------------------------------------------------- Sub-clause B
def test_deploy_workflow_no_cancel_in_progress() -> None:
    doc = yaml.safe_load(DEPLOY_YML.read_text(encoding='utf-8'))
    concurrency = doc.get('concurrency')
    assert concurrency, 'P-28: deploy.yml must have a top-level concurrency block'
    assert concurrency.get('cancel-in-progress') in (False, None), 'P-28: cancel-in-progress must be false — a 2nd push must not cancel a CFN update'
    assert concurrency.get('group') == 'deploy', "P-28: concurrency group must be the literal 'deploy' (one slot for all triggers)"


# ---------------------------------------------------------------- Sub-clause C
def _run_bodies(job: dict) -> str:
    """Concatenate the `run:` bodies of a job's steps (actual commands, not prose)."""
    return '\n'.join(step['run'] for step in (job.get('steps') or []) if isinstance(step.get('run'), str))


def _executes_change_set(job: dict) -> bool:
    body = _run_bodies(job)
    return 'make execute-changeset' in body or 'cloudformation execute-change-set' in body


def test_deploy_workflow_splits_create_and_execute() -> None:
    doc = yaml.safe_load(DEPLOY_YML.read_text(encoding='utf-8'))
    jobs = doc.get('jobs', {})
    # A create job that produces the change set (name marks it, and it must not execute).
    create_jobs = {name: j for name, j in jobs.items() if ('change-set' in name or 'changeset' in name) and 'execute' not in name}
    assert create_jobs, 'P-28: deploy.yml must have a change-set creation job'

    # The job that executes the change set must be a SEPARATE job gated by needs+environment.
    execute_jobs = {name: j for name, j in jobs.items() if _executes_change_set(j)}
    assert execute_jobs, 'P-28: deploy.yml must have a job that runs ExecuteChangeSet'
    for name, job in execute_jobs.items():
        assert name not in create_jobs, f"P-28: '{name}' both creates and executes — the split is the invariant"
        assert job.get('needs'), f"P-28: execute job '{name}' must `needs:` the create-change-set job"
        assert job.get('environment'), (
            f"P-28: execute job '{name}' must have an `environment:` gate (required reviewer configured in GitHub settings)"
        )


def test_automation_job_does_not_execute_change_set() -> None:
    """AC-P28-3: the automation (create) job must not call ExecuteChangeSet."""
    doc = yaml.safe_load(DEPLOY_YML.read_text(encoding='utf-8'))
    jobs = doc.get('jobs', {})
    for name, job in jobs.items():
        if ('change-set' in name or 'changeset' in name) and 'execute' not in name:
            assert not _executes_change_set(job), f"P-28: create job '{name}' must NOT call execute-change-set"


# ---------------------------------------------------------------- Sub-clause D
def test_replacement_report_auto_fails_on_protected_replacement() -> None:
    mod = _load_script(REPLACEMENT_SCRIPT, 'changeset_replacement_report')
    changeset = {
        'Changes': [
            {
                'ResourceChange': {
                    'LogicalResourceId': 'CrudApi1234',
                    'ResourceType': 'AWS::ApiGateway::RestApi',
                    'Action': 'Modify',
                    'Replacement': 'True',
                }
            },
            {
                'ResourceChange': {
                    'LogicalResourceId': 'SomeLambda',
                    'ResourceType': 'AWS::Lambda::Function',
                    'Action': 'Modify',
                    'Replacement': 'True',
                }
            },
        ]
    }
    report, auto_fail = mod.build_report(changeset)
    assert auto_fail is True, 'P-28: Replacement:True on a RestApi must auto-fail'
    entries = {e['LogicalId']: e for e in report['changes']}
    assert entries['CrudApi1234'].get('AUTO_FAIL') is True
    # A non-protected replacement (Lambda) must NOT trip the gate on its own.
    assert entries['SomeLambda'].get('AUTO_FAIL') is not True


def test_replacement_report_passes_on_safe_changeset() -> None:
    mod = _load_script(REPLACEMENT_SCRIPT, 'changeset_replacement_report')
    changeset = {
        'Changes': [
            {
                'ResourceChange': {
                    'LogicalResourceId': 'UsersTable',
                    'ResourceType': 'AWS::DynamoDB::Table',
                    'Action': 'Modify',
                    'Replacement': 'False',
                }
            }
        ]
    }
    _report, auto_fail = mod.build_report(changeset)
    assert auto_fail is False, 'P-28: no protected replacement -> report must pass'


@pytest.mark.parametrize(
    'rtype',
    [
        'AWS::ApiGateway::RestApi',
        'AWS::DynamoDB::Table',
        'AWS::S3::Bucket',
        'AWS::Cognito::UserPool',
    ],
)
def test_replacement_report_covers_all_protected_types(rtype: str) -> None:
    mod = _load_script(REPLACEMENT_SCRIPT, 'changeset_replacement_report')
    changeset = {
        'Changes': [
            {
                'ResourceChange': {
                    'LogicalResourceId': 'X',
                    'ResourceType': rtype,
                    'Action': 'Modify',
                    'Replacement': 'True',
                }
            }
        ]
    }
    _report, auto_fail = mod.build_report(changeset)
    assert auto_fail is True, f'P-28: Replacement:True on {rtype} must auto-fail'


# ---------------------------------------------------------------- Sub-clause E
def test_scope_lock_ci_check_rejects_missing_changelog() -> None:
    mod = _load_script(SCOPE_LOCK_SCRIPT, 'check_scope_lock_integrity')
    # Both files changed, but no version bump / changelog row / approval trailer.
    result = mod.check_integrity(
        changed_files=[
            'docs/db-redesign/code/code-analysis/project/project-scope-lock.md',
            'docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml',
        ],
        yaml_before='meta:\n  version: 2.1.1\nchangelog: []\n',
        yaml_after='meta:\n  version: 2.1.1\nchangelog: []\n',
        commit_message='tweak scope lock wording',
    )
    assert result.ok is False, 'P-28: missing changelog/version/trailer must FAIL'


def test_scope_lock_ci_check_rejects_single_file_edit() -> None:
    mod = _load_script(SCOPE_LOCK_SCRIPT, 'check_scope_lock_integrity')
    result = mod.check_integrity(
        changed_files=[
            'docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml',
        ],
        yaml_before='meta:\n  version: 2.1.1\nchangelog: []\n',
        yaml_after='meta:\n  version: 2.1.2\nchangelog:\n  - 2026-07-12 x\n',
        commit_message='Scope-Lock-Approved-By: Yitzchak 2026-07-12',
    )
    assert result.ok is False, 'P-28: touching one twin but not the other must FAIL'


def test_scope_lock_ci_check_passes_on_compliant_change() -> None:
    mod = _load_script(SCOPE_LOCK_SCRIPT, 'check_scope_lock_integrity')
    result = mod.check_integrity(
        changed_files=[
            'docs/db-redesign/code/code-analysis/project/project-scope-lock.md',
            'docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml',
        ],
        yaml_before='meta:\n  version: 2.1.1\nchangelog: []\n',
        yaml_after=('meta:\n  version: 2.1.2\nchangelog:\n  - {date: 2026-07-12, change: add clause P-99}\n'),
        commit_message=('Amend scope lock: add P-99\n\nScope-Lock-Approved-By: Yitzchak Meirovich 2026-07-12'),
    )
    assert result.ok is True, f'P-28: compliant amendment must PASS (got {result.reasons})'


def test_scope_lock_ci_check_noop_on_unrelated_files() -> None:
    mod = _load_script(SCOPE_LOCK_SCRIPT, 'check_scope_lock_integrity')
    result = mod.check_integrity(
        changed_files=['src/backend/careervp/logic/gap_analysis.py'],
        yaml_before=None,
        yaml_after=None,
        commit_message='fix gap analysis',
    )
    assert result.ok is True, 'P-28: a diff not touching scope-lock files is a no-op pass'


def test_scope_lock_guard_workflow_exists() -> None:
    assert SCOPE_LOCK_GUARD_YML.exists(), 'P-28: .github/workflows/scope-lock-guard.yml must exist'
    doc = yaml.safe_load(SCOPE_LOCK_GUARD_YML.read_text(encoding='utf-8'))
    # `on:` parses to Python True (YAML 1.1) — accept either key form.
    triggers = doc.get('on', doc.get(True, {}))
    assert 'pull_request' in triggers, 'P-28: guard must run on pull_request'
