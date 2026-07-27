"""RED contracts for D-H2/D-H3 key authority and schema-mismatch surfacing.

Spec:
docs/db-redesign/code/code-analysis/project/specs/D-H2-D-H3-key-authority-spec.md
Acceptance criteria: AC-DH2-1, AC-DH3-1

Rule-13 import technique: the two behavior tests import the not-yet-existing
``careervp.dal.core_repository`` module inside the test, catch ``ImportError``,
and fail through an explicit acceptance-criterion assertion naming the required
module. Collection therefore succeeds, and neither test is RED because of a
bare import or missing fixture.

B-3-5 scope boundary: auth, trial, and user-pool keying belongs to Wave-6 D-H8.
Application/users/gap-questions/knowledge table fallbacks are likewise outside
the artifacts/core table boundary. Company Research is an artifact and remains
in scope.
"""

from __future__ import annotations

import importlib
import inspect
import re
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

from careervp.dal.dynamo_dal_handler import DynamoDalHandler
from careervp.models.result import Result, ResultCode

_REPO_ROOT = Path(__file__).resolve().parents[4]
_HANDLERS_ROOT = _REPO_ROOT / 'src' / 'backend' / 'careervp' / 'handlers'
_LOGIC_ROOT = _REPO_ROOT / 'src' / 'backend' / 'careervp' / 'logic'
_CORE_REPOSITORY_MODULE = 'careervp.dal.core_repository'
_TABLE_REGISTRY_MODULE = 'careervp.dal.table_registry'
_ARTIFACTS_TABLE_NAME = 'careervp-dh2-artifacts-table-test'
_APPLICATION_ID = 'app-dh2-001'
_ARTIFACT_ID = 'ARTIFACT#COVER_LETTER#dh2-001'

# These modules build keys for non-artifact records. D-H8, not D-H2, owns them.
_OUT_OF_SCOPE_KEY_MODULES = {
    'src/backend/careervp/handlers/auth_handler.py',
    'src/backend/careervp/logic/auth_service.py',
    'src/backend/careervp/logic/trial_service.py',
}

# Live 2026-07-27 B-3-5 census: exactly 9 USER# sites across these 5 files.
# This is a ratchet: deletion is allowed; a new source signature is not.
_USER_HASH_BASELINE = {
    (
        'src/backend/careervp/handlers/auth_handler.py',
        "'pk': f'USER#{user_id}',",
    ),
    (
        'src/backend/careervp/handlers/company_research_handler.py',
        "if item_pk not in (user_id, f'USER#{user_id}') and item_uid != user_id:",
    ),
    (
        'src/backend/careervp/handlers/company_research_handler.py',
        "{'pk': f'USER#{user_id}', 'sk': f'{COMPANY_RESEARCH_KB_PREFIX}{job_id}'},",
    ),
    (
        'src/backend/careervp/handlers/company_research_handler.py',
        "(f'USER#{user_id}', COMPANY_RESEARCH_KB_PREFIX),",
    ),
    (
        'src/backend/careervp/logic/auth_service.py',
        "return f'USER#{user_id}'",
    ),
    (
        'src/backend/careervp/logic/auth_service.py',
        "if isinstance(pk, str) and pk.startswith('USER#'):",
    ),
    (
        'src/backend/careervp/logic/auth_service.py',
        "return pk.removeprefix('USER#')",
    ),
    (
        'src/backend/careervp/logic/company_research_store.py',
        "{'pk': f'USER#{user_id}', 'sk': f'{LEGACY_COMPANY_RESEARCH_PREFIX}{application_id}'},",
    ),
    (
        'src/backend/careervp/logic/trial_service.py',
        "return f'USER#{user_id}'",
    ),
}

# The spec labels this "23 sites", but its enumerated list contains these 22
# source locations across 9 files. B-3-5 records the delta. The documented
# maximum remains 23 while this signature set catches a new site even when an
# old site disappears.
_ENV_PRECEDENCE_DOCUMENTED_MAX = 23
_ENV_PRECEDENCE_BASELINE = {
    (
        'src/backend/careervp/handlers/ai_assist_handler.py',
        "for env_key in ('ARTIFACTS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME'):",
    ),
    (
        'src/backend/careervp/handlers/ai_assist_handler.py',
        "for env_key in ('COMPANY_RESEARCH_TABLE_NAME', 'ARTIFACTS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME'):",
    ),
    (
        'src/backend/careervp/handlers/company_research_handler.py',
        "for env_key in ('DYNAMODB_TABLE_NAME', 'TABLE_NAME'):",
    ),
    (
        'src/backend/careervp/handlers/cover_letter_handler.py',
        "table_name = os.environ.get('ARTIFACTS_TABLE_NAME') or os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME') or ''",
    ),
    (
        'src/backend/careervp/handlers/cover_letter_handler.py',
        "'ARTIFACTS_TABLE_NAME'",
    ),
    (
        'src/backend/careervp/handlers/cover_letter_handler.py',
        "if os.environ.get('ARTIFACTS_TABLE_NAME')",
    ),
    (
        'src/backend/careervp/handlers/cover_letter_handler.py',
        "table_name = os.environ.get('ARTIFACTS_TABLE_NAME') or os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME') or ''",
    ),
    (
        'src/backend/careervp/handlers/cover_letter_handler.py',
        "table_name = os.environ.get('ARTIFACTS_TABLE_NAME') or os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME') or ''",
    ),
    (
        'src/backend/careervp/handlers/cover_letter_handler.py',
        "table_name = os.environ.get('ARTIFACTS_TABLE_NAME') or os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME') or ''",
    ),
    (
        'src/backend/careervp/handlers/cover_letter_submit_handler.py',
        "for env_key in ('ARTIFACTS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME'):",
    ),
    (
        'src/backend/careervp/handlers/cv_tailoring_handler.py',
        "table_name = os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', '')",
    ),
    (
        'src/backend/careervp/handlers/cv_tailoring_handler.py',
        "dal = DynamoDalHandler((os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', '')))",
    ),
    (
        'src/backend/careervp/handlers/cv_tailoring_handler.py',
        "dal = DynamoDalHandler((os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', '')))",
    ),
    (
        'src/backend/careervp/handlers/cv_tailoring_handler.py',
        "table_name = os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', '')",
    ),
    (
        'src/backend/careervp/handlers/cv_tailoring_handler.py',
        "table_name = os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', '')",
    ),
    (
        'src/backend/careervp/handlers/cv_tailoring_handler.py',
        "table = DynamoDalHandler((os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', '')))._get_db_handler(",
    ),
    (
        'src/backend/careervp/handlers/cv_tailoring_handler.py',
        "(os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', ''))",
    ),
    (
        'src/backend/careervp/handlers/cv_tailoring_handler.py',
        "dal = DynamoDalHandler((os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', '')))",
    ),
    (
        'src/backend/careervp/handlers/export_handler.py',
        "table_name = os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', '')",
    ),
    (
        'src/backend/careervp/handlers/interview_prep_handler.py',
        "for env_key in ('ARTIFACTS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME'):",
    ),
    (
        'src/backend/careervp/handlers/interview_prep_submit_handler.py',
        "for env_key in ('ARTIFACTS_TABLE_NAME', 'DYNAMODB_TABLE_NAME', 'TABLE_NAME'):",
    ),
    (
        'src/backend/careervp/handlers/vpr_submit_handler.py',
        "dal=DynamoDalHandler(os.environ.get('DYNAMODB_TABLE_NAME') or os.environ.get('TABLE_NAME', '')),",
    ),
}

_ARTIFACT_KEY_BUILD_PATTERN = re.compile(
    r"""(?x)
    (?:['"](?:pk|sk)['"]\s*:)
    |(?:Key\(\s*['"](?:pk|sk)['"]\s*\))
    |(?:(?:=|:|return)\s*f?['"](?:ARTIFACT|COMPANY_RESEARCH)\#)
    """
)
_SCOPED_ENV_CHAIN_PATTERN = re.compile(r'DYNAMODB_TABLE_NAME.*TABLE_NAME')
_OUT_OF_SCOPE_TABLE_PREFIXES = (
    'APPLICATIONS_TABLE_NAME',
    'USERS_TABLE_NAME',
    'GAP_QUESTIONS_TABLE_NAME',
    'KNOWLEDGE_TABLE_NAME',
)


def _iter_python_files(*roots: Path) -> Iterator[Path]:
    for root in roots:
        yield from sorted(root.rglob('*.py'))


type SourceHit = tuple[str, int, str]


def _source_hit(path: Path, lineno: int, line: str) -> SourceHit:
    return (path.relative_to(_REPO_ROOT).as_posix(), lineno, line.strip())


def _format_hits(hits: list[SourceHit] | set[SourceHit]) -> str:
    return '\n'.join(f'{path}:{lineno}: {line}' for path, lineno, line in sorted(hits))


def _line_hits(pattern: re.Pattern[str], *roots: Path) -> list[SourceHit]:
    hits: list[SourceHit] = []
    for path in _iter_python_files(*roots):
        for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
            if pattern.search(line):
                hits.append(_source_hit(path, lineno, line))
    return hits


def _source_signatures(hits: list[SourceHit] | set[SourceHit]) -> set[tuple[str, str]]:
    return {(path, line) for path, _lineno, line in hits}


def _import_contract_class(module_path: str, class_name: str, acceptance_criterion: str) -> type[Any]:
    try:
        module: ModuleType = importlib.import_module(module_path)
    except ImportError as exc:
        pytest.fail(f'{acceptance_criterion}: {class_name} not importable at {module_path}: {exc}')

    imported_class = getattr(module, class_name, None)
    assert isinstance(imported_class, type), f'{acceptance_criterion}: {module_path} must export class {class_name}'
    return imported_class


def _construct_with_known_dependencies(
    target_class: type[Any],
    dependencies: dict[str, Any],
    acceptance_criterion: str,
) -> Any:
    signature = inspect.signature(target_class)
    kwargs: dict[str, Any] = {}
    missing: list[str] = []
    for name, parameter in signature.parameters.items():
        if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if name in dependencies:
            kwargs[name] = dependencies[name]
        elif parameter.default is inspect.Parameter.empty:
            missing.append(name)

    assert missing == [], (
        f'{acceptance_criterion}: {target_class.__name__} must be constructible from the artifacts '
        f'table registry/resource; unsupported required parameters: {missing}'
    )
    return target_class(**kwargs)


def _canonical_cover_letter_read_methods(repository: Any) -> list[tuple[str, Callable[..., Any]]]:
    methods: list[tuple[str, Callable[..., Any]]] = []
    for name in dir(repository):
        if 'cover_letter' not in name or not name.startswith(('get', 'read')):
            continue
        candidate = getattr(repository, name)
        if not callable(candidate):
            continue
        parameters = inspect.signature(candidate).parameters
        if {'application_id', 'artifact_id'}.issubset(parameters):
            methods.append((name, candidate))
    return methods


def test_dh2_all_artifact_keys_built_by_core_repository() -> None:
    """AC-DH2-1: artifacts/core key construction has one approved authority."""
    user_hash_sites = _line_hits(re.compile(r'USER#'), _HANDLERS_ROOT, _LOGIC_ROOT)
    unexpected_user_hash_signatures = _source_signatures(user_hash_sites) - _USER_HASH_BASELINE
    assert unexpected_user_hash_signatures == set(), (
        'AC-DH2-1: B-3-5 USER# ratchet found a new site outside the frozen 9-site/5-file baseline:\n'
        + '\n'.join(f'{path}: {line}' for path, line in sorted(unexpected_user_hash_signatures))
    )
    assert len(user_hash_sites) <= 9
    assert len({path for path, _lineno, _line in user_hash_sites}) <= 5

    construction_sites = _line_hits(_ARTIFACT_KEY_BUILD_PATTERN, _HANDLERS_ROOT, _LOGIC_ROOT)
    in_scope_user_hash_sites = {site for site in user_hash_sites if site[0] not in _OUT_OF_SCOPE_KEY_MODULES}
    artifact_key_sites = {site for site in construction_sites if site[0] not in _OUT_OF_SCOPE_KEY_MODULES} | in_scope_user_hash_sites

    assert artifact_key_sites == set(), (
        'AC-DH2-1: artifacts/core keys are still built outside the approved '
        'careervp/dal/table_registry.py and careervp/dal/core_repository.py modules. '
        'Auth/trial/user-pool keying is explicitly excluded for Wave-6 D-H8:\n' + _format_hits(artifact_key_sites)
    )


def test_dh3_validation_exception_not_returned_as_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-DH3-1: a canonical-key schema mismatch is never an empty success."""
    _import_contract_class(_CORE_REPOSITORY_MODULE, 'CoreRepository', 'AC-DH3-1')

    schema_mismatch = ClientError(
        error_response={
            'Error': {
                'Code': 'ValidationException',
                'Message': 'The provided key element does not match the schema',
            }
        },
        operation_name='GetItem',
    )
    table = MagicMock()
    table.get_item.side_effect = [schema_mismatch, {}]
    handler = DynamoDalHandler(_ARTIFACTS_TABLE_NAME)
    monkeypatch.setattr(handler, '_get_db_handler', MagicMock(return_value=table))

    result = handler.read_cover_letter_by_artifact_id(_APPLICATION_ID, _ARTIFACT_ID)
    actual = (result.success, result.data, result.code)
    expected = (False, None, ResultCode.TABLE_SCHEMA_MISMATCH)
    false_not_found = (True, None, ResultCode.SUCCESS)

    assert actual == expected, f'AC-DH3-1: expected exactly {expected!r}, got {actual!r}'
    assert actual != false_not_found, f'AC-DH3-1: schema mismatch was returned as not found: {actual!r}'


def test_dh2_core_repository_reads_canonical_only_items(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-DH2-1: every cover-letter repository read sees canonical-only items."""
    core_repository_class = _import_contract_class(_CORE_REPOSITORY_MODULE, 'CoreRepository', 'AC-DH2-1')
    table_registry_class = _import_contract_class(_TABLE_REGISTRY_MODULE, 'TableRegistry', 'AC-DH2-1')

    canonical_item = {
        'applicationId': _APPLICATION_ID,
        'artifactId': _ARTIFACT_ID,
        'artifactType': 'cover_letter',
        'job_id': 'dh2-001',
        'status': 'COMPLETED',
    }
    assert 'pk' not in canonical_item and 'sk' not in canonical_item

    with mock_aws():
        dynamodb_resource = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb_resource.create_table(
            TableName=_ARTIFACTS_TABLE_NAME,
            KeySchema=[
                {'AttributeName': 'applicationId', 'KeyType': 'HASH'},
                {'AttributeName': 'artifactId', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'applicationId', 'AttributeType': 'S'},
                {'AttributeName': 'artifactId', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        table.put_item(Item=canonical_item)
        monkeypatch.setenv('ARTIFACTS_TABLE_NAME', _ARTIFACTS_TABLE_NAME)

        dal = DynamoDalHandler(_ARTIFACTS_TABLE_NAME)
        monkeypatch.setattr(dal, '_get_db_handler', MagicMock(return_value=table))
        registry_dependencies = {
            'artifacts_table_name': _ARTIFACTS_TABLE_NAME,
            'table_name': _ARTIFACTS_TABLE_NAME,
            'dynamodb_resource': dynamodb_resource,
        }
        registry = _construct_with_known_dependencies(
            table_registry_class,
            registry_dependencies,
            'AC-DH2-1',
        )
        repository_dependencies = {
            **registry_dependencies,
            'dal': dal,
            'registry': registry,
            'table_registry': registry,
        }
        repository = _construct_with_known_dependencies(
            core_repository_class,
            repository_dependencies,
            'AC-DH2-1',
        )

        read_methods = _canonical_cover_letter_read_methods(repository)
        assert read_methods, 'AC-DH2-1: CoreRepository must expose at least one cover-letter read method accepting application_id and artifact_id'
        for method_name, read_method in read_methods:
            result = read_method(application_id=_APPLICATION_ID, artifact_id=_ARTIFACT_ID)
            assert isinstance(result, Result), f'AC-DH2-1: CoreRepository.{method_name} must return Result, got {type(result).__name__}'
            assert (result.success, result.data, result.code) == (
                True,
                canonical_item,
                ResultCode.SUCCESS,
            ), f'AC-DH2-1: CoreRepository.{method_name} did not return the canonical-only item'


def test_dh2_no_env_table_precedence_in_handlers() -> None:
    """AC-DH2-1: handlers do not choose the artifacts/core table by precedence."""
    precedence_sites = _line_hits(_SCOPED_ENV_CHAIN_PATTERN, _HANDLERS_ROOT)
    precedence_sites = [site for site in precedence_sites if not any(prefix in site[2] for prefix in _OUT_OF_SCOPE_TABLE_PREFIXES)]

    # Preserve the spec's two explicitly enumerated lines from the multi-line
    # cover-letter resolution diagnostic.
    precedence_sites.extend(
        site
        for site in _line_hits(
            re.compile(r"^\s*(?:'ARTIFACTS_TABLE_NAME'|if os\.environ\.get\('ARTIFACTS_TABLE_NAME'\))\s*$"),
            _HANDLERS_ROOT,
        )
        if site[0] == 'src/backend/careervp/handlers/cover_letter_handler.py'
    )

    unexpected_signatures = _source_signatures(precedence_sites) - _ENV_PRECEDENCE_BASELINE
    assert unexpected_signatures == set(), 'AC-DH2-1: B-3-5 precedence ratchet found a new artifacts/core fallback site:\n' + '\n'.join(
        f'{path}: {line}' for path, line in sorted(unexpected_signatures)
    )
    assert len(precedence_sites) <= _ENV_PRECEDENCE_DOCUMENTED_MAX
    assert len({path for path, _lineno, _line in precedence_sites}) <= 9

    assert precedence_sites == [], (
        'AC-DH2-1: handlers still resolve the artifacts/core table through '
        'ARTIFACTS_TABLE_NAME -> DYNAMODB_TABLE_NAME -> TABLE_NAME or its two-key tail. '
        'APPLICATIONS_/USERS_/GAP_QUESTIONS_/KNOWLEDGE_ fallbacks and a single unconditional '
        "os.environ['ARTIFACTS_TABLE_NAME'] read are explicitly out of scope:\n" + _format_hits(precedence_sites)
    )
