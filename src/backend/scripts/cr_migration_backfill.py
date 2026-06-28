"""Backfill legacy Company Research artifacts into canonical artifacts storage.

Linkage rule:
1. Prefer an explicit legacy ``application_id``/``applicationId`` attribute
   (top-level or inside ``research_data``/``company_research``), but only after
   verifying that APPLICATIONS_TABLE_NAME contains that application for the same
   user.
2. If no explicit legacy application id is present, read JOBS_TABLE_NAME by the
   CR job id. Use its ``application_id`` only when the jobs row has the same
   ``user_id`` and exact same company name as the legacy Company Research item.
3. If no explicit job application id is present, query APPLICATIONS_TABLE_NAME by
   ``userId`` and require exactly one application whose ``company_name`` or
   ``company`` exactly matches the legacy Company Research company name after
   case/space normalization.

The legacy Company Research sort-key suffix is treated only as the CR job id.
It is never guessed to be the canonical applicationId.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from careervp.logic.company_research_store import COMPANY_RESEARCH_ARTIFACT_PREFIX, cr_artifact_key, write_cr_artifact  # noqa: E402
from careervp.models.company import CompanyResearchResult, ResearchSource  # noqa: E402

DEFAULT_REGION = 'us-east-1'
DEFAULT_USERS_TABLE = 'careervp-users-table-dev'
DEFAULT_ARTIFACTS_TABLE = 'careervp-artifacts-table-dev'
DEFAULT_APPLICATIONS_TABLE = 'careervp-applications-table-dev'
DEFAULT_JOBS_TABLE = 'careervp-jobs-table-dev'
DEFAULT_REPORT_DIR = Path('reports')

MigrationCategory = Literal['migrate', 'skip-already-present', 'quarantine']


@dataclass(frozen=True)
class MigrationConfig:
    users_table_name: str = DEFAULT_USERS_TABLE
    artifacts_table_name: str = DEFAULT_ARTIFACTS_TABLE
    applications_table_name: str = DEFAULT_APPLICATIONS_TABLE
    jobs_table_name: str | None = DEFAULT_JOBS_TABLE
    region_name: str = DEFAULT_REGION
    apply: bool = False
    allow_nondev: bool = False
    quarantine_report_path: Path | None = None


@dataclass(frozen=True)
class MigrationAction:
    category: MigrationCategory
    user_id: str
    legacy_sk: str
    cr_job_id: str
    company_name: str
    confidence_score: float | None
    application_id: str | None = None
    linkage_rule: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class MigrationResult:
    scanned_count: int
    migrate_count: int
    skip_already_present_count: int
    quarantine_count: int
    actions: tuple[MigrationAction, ...]
    quarantine_report_path: Path | None


def run_migration(config: MigrationConfig) -> MigrationResult:
    """Plan or apply the legacy Company Research backfill."""
    _validate_dev_tables(config)
    os.environ['AWS_DEFAULT_REGION'] = config.region_name
    os.environ['ARTIFACTS_TABLE_NAME'] = config.artifacts_table_name

    dynamodb = boto3.resource('dynamodb', region_name=config.region_name)
    users_table = dynamodb.Table(config.users_table_name)
    artifacts_table = dynamodb.Table(config.artifacts_table_name)
    applications_table = dynamodb.Table(config.applications_table_name)
    jobs_table = dynamodb.Table(config.jobs_table_name) if config.jobs_table_name else None

    actions: list[MigrationAction] = []
    for legacy_item in _scan_legacy_cr_items(users_table):
        action = _plan_item(
            legacy_item=legacy_item,
            artifacts_table=artifacts_table,
            applications_table=applications_table,
            jobs_table=jobs_table,
        )
        actions.append(action)
        if config.apply and action.category == 'migrate' and action.application_id is not None:
            write_cr_artifact(
                application_id=action.application_id,
                user_id=action.user_id,
                result=_materialize_result(legacy_item),
            )

    quarantine_path: Path | None = None
    if config.apply:
        quarantine_path = config.quarantine_report_path or _default_quarantine_report_path()
        _write_quarantine_report(quarantine_path, actions)

    return MigrationResult(
        scanned_count=len(actions),
        migrate_count=sum(1 for action in actions if action.category == 'migrate'),
        skip_already_present_count=sum(1 for action in actions if action.category == 'skip-already-present'),
        quarantine_count=sum(1 for action in actions if action.category == 'quarantine'),
        actions=tuple(actions),
        quarantine_report_path=quarantine_path,
    )


def _plan_item(*, legacy_item: Mapping[str, Any], artifacts_table: Any, applications_table: Any, jobs_table: Any | None) -> MigrationAction:
    user_id = _resolve_user_id(legacy_item)
    legacy_sk = _as_str(legacy_item.get('sk'))
    cr_job_id = _cr_job_id_from_sk(legacy_sk)
    company_name = _company_name(legacy_item)
    confidence_score = _confidence_score(legacy_item)

    if not user_id:
        return _quarantine(
            user_id='',
            legacy_sk=legacy_sk,
            cr_job_id=cr_job_id,
            company_name=company_name,
            confidence_score=confidence_score,
            reason='missing user_id/pk',
        )
    if not cr_job_id:
        return _quarantine(
            user_id=user_id,
            legacy_sk=legacy_sk,
            cr_job_id='',
            company_name=company_name,
            confidence_score=confidence_score,
            reason='legacy sk does not contain a CR job id',
        )

    resolved = _resolve_application_id(legacy_item=legacy_item, applications_table=applications_table, jobs_table=jobs_table, user_id=user_id)
    if resolved is None:
        return _quarantine(
            user_id=user_id,
            legacy_sk=legacy_sk,
            cr_job_id=cr_job_id,
            company_name=company_name,
            confidence_score=confidence_score,
            reason='no verified applicationId linkage',
        )
    application_id, linkage_rule = resolved

    if _canonical_artifact_exists(artifacts_table, application_id):
        return MigrationAction(
            category='skip-already-present',
            user_id=user_id,
            legacy_sk=legacy_sk,
            cr_job_id=cr_job_id,
            company_name=company_name,
            confidence_score=confidence_score,
            application_id=application_id,
            linkage_rule=linkage_rule,
        )

    return MigrationAction(
        category='migrate',
        user_id=user_id,
        legacy_sk=legacy_sk,
        cr_job_id=cr_job_id,
        company_name=company_name,
        confidence_score=confidence_score,
        application_id=application_id,
        linkage_rule=linkage_rule,
    )


def _resolve_application_id(
    *,
    legacy_item: Mapping[str, Any],
    applications_table: Any,
    jobs_table: Any | None,
    user_id: str,
) -> tuple[str, str] | None:
    explicit_id = _explicit_application_id(legacy_item)
    if explicit_id and _application_exists(applications_table=applications_table, user_id=user_id, application_id=explicit_id):
        return explicit_id, 'explicit legacy application_id verified against applications-table'

    job_application_id = _job_application_id(legacy_item=legacy_item, jobs_table=jobs_table, user_id=user_id)
    if job_application_id:
        return job_application_id, 'explicit jobs-table application_id with matching user_id+company_name'

    company_name = _company_name(legacy_item)
    if not company_name:
        return None

    matches: list[str] = []
    for application in _query_user_applications(applications_table=applications_table, user_id=user_id):
        app_company = _as_str(application.get('company_name')) or _as_str(application.get('company'))
        if _normalize_company(app_company) != _normalize_company(company_name):
            continue
        application_id = _as_str(application.get('applicationId')) or _as_str(application.get('application_id'))
        app_owner = _as_str(application.get('user_id')) or _as_str(application.get('userId'))
        if application_id and app_owner in {'', user_id}:
            matches.append(application_id)

    unique_matches = sorted(set(matches))
    if len(unique_matches) == 1:
        return unique_matches[0], 'unique applications-table userId+company_name match'
    return None


def _job_application_id(*, legacy_item: Mapping[str, Any], jobs_table: Any | None, user_id: str) -> str | None:
    if jobs_table is None:
        return None

    cr_job_id = _cr_job_id_from_sk(_as_str(legacy_item.get('sk')))
    if not cr_job_id:
        return None

    try:
        response = jobs_table.get_item(Key={'job_id': cr_job_id})
    except ClientError as exc:
        if exc.response.get('Error', {}).get('Code') == 'ResourceNotFoundException':
            return None
        raise

    job = response.get('Item')
    if not isinstance(job, Mapping):
        return None
    if _as_str(job.get('user_id')) != user_id:
        return None
    if _normalize_company(_as_str(job.get('company_name')) or _as_str(job.get('company'))) != _normalize_company(_company_name(legacy_item)):
        return None

    return _as_str(job.get('application_id')) or _as_str(job.get('applicationId')) or None


def _scan_legacy_cr_items(users_table: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    scan_kwargs: dict[str, Any] = {
        'FilterExpression': Attr('sk').begins_with(COMPANY_RESEARCH_ARTIFACT_PREFIX),
    }
    while True:
        response = users_table.scan(**scan_kwargs)
        response_items = response.get('Items', [])
        items.extend(item for item in response_items if isinstance(item, dict))
        last_key = response.get('LastEvaluatedKey')
        if not isinstance(last_key, dict):
            return items
        scan_kwargs['ExclusiveStartKey'] = last_key


def _query_user_applications(*, applications_table: Any, user_id: str) -> list[dict[str, Any]]:
    response = applications_table.query(KeyConditionExpression=Key('userId').eq(user_id))
    items = response.get('Items', [])
    return [item for item in items if isinstance(item, dict)]


def _application_exists(*, applications_table: Any, user_id: str, application_id: str) -> bool:
    response = applications_table.get_item(Key={'userId': user_id, 'applicationId': application_id})
    item = response.get('Item')
    if not isinstance(item, dict):
        return False
    owner = _as_str(item.get('user_id')) or _as_str(item.get('userId'))
    return owner in {'', user_id}


def _canonical_artifact_exists(artifacts_table: Any, application_id: str) -> bool:
    response = artifacts_table.get_item(Key=cr_artifact_key(application_id))
    return isinstance(response.get('Item'), dict)


def _materialize_result(legacy_item: Mapping[str, Any]) -> CompanyResearchResult:
    nested = _nested_payload(legacy_item)
    confidence = _confidence_score(legacy_item)
    timestamp = _timestamp(legacy_item)
    return CompanyResearchResult(
        company_name=_company_name(legacy_item),
        overview=_first_text(legacy_item, nested, ('overview', 'culture')),
        mission=_optional_text(_first_text(legacy_item, nested, ('mission',))),
        values=_list_of_strings(_first_value(legacy_item, nested, ('values',))),
        strategic_priorities=_list_of_strings(_first_value(legacy_item, nested, ('strategic_priorities', 'products'))),
        recent_news=_recent_news(_first_value(legacy_item, nested, ('recent_news',))),
        financial_summary=_optional_text(_first_text(legacy_item, nested, ('financial_summary', 'funding_status'))),
        source=_source(_first_text(legacy_item, nested, ('source',))),
        source_urls=_list_of_strings(_first_value(legacy_item, nested, ('source_urls',))),
        confidence_score=confidence if confidence is not None else 0.0,
        research_timestamp=timestamp,
    )


def _write_quarantine_report(path: Path, actions: Sequence[MigrationAction]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    quarantined = [asdict(action) for action in actions if action.category == 'quarantine']
    path.write_text(json.dumps(quarantined, indent=2, default=_json_default) + '\n', encoding='utf-8')


def _default_quarantine_report_path() -> Path:
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return DEFAULT_REPORT_DIR / f'cr-migration-quarantine-{timestamp}.json'


def _validate_dev_tables(config: MigrationConfig) -> None:
    table_names = [config.users_table_name, config.artifacts_table_name, config.applications_table_name]
    if config.jobs_table_name:
        table_names.append(config.jobs_table_name)
    for table_name in table_names:
        if table_name.endswith('-dev'):
            continue
        if not config.allow_nondev:
            raise ValueError(f'Refusing non-dev table without --allow-nondev: {table_name}')
        print(f'WARNING: running against non-dev table: {table_name}', file=sys.stderr)


def _quarantine(
    *,
    user_id: str,
    legacy_sk: str,
    cr_job_id: str,
    company_name: str,
    confidence_score: float | None,
    reason: str,
) -> MigrationAction:
    return MigrationAction(
        category='quarantine',
        user_id=user_id,
        legacy_sk=legacy_sk,
        cr_job_id=cr_job_id,
        company_name=company_name,
        confidence_score=confidence_score,
        reason=reason,
    )


def _resolve_user_id(item: Mapping[str, Any]) -> str:
    user_id = _as_str(item.get('user_id')) or _as_str(item.get('userId')) or _as_str(item.get('pk'))
    if user_id.startswith('USER#'):
        return user_id.removeprefix('USER#').strip()
    return user_id


def _cr_job_id_from_sk(sk: str) -> str:
    if not sk.startswith(COMPANY_RESEARCH_ARTIFACT_PREFIX):
        return ''
    return sk.removeprefix(COMPANY_RESEARCH_ARTIFACT_PREFIX).strip()


def _explicit_application_id(item: Mapping[str, Any]) -> str:
    nested = _nested_payload(item)
    return _first_text(item, nested, ('application_id', 'applicationId'))


def _company_name(item: Mapping[str, Any]) -> str:
    nested = _nested_payload(item)
    return _first_text(item, nested, ('company_name', 'companyName', 'company'))


def _confidence_score(item: Mapping[str, Any]) -> float | None:
    nested = _nested_payload(item)
    value = _first_value(item, nested, ('confidence_score',))
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (Decimal, int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _timestamp(item: Mapping[str, Any]) -> datetime:
    nested = _nested_payload(item)
    raw = _first_text(item, nested, ('research_timestamp', 'created_at'))
    if raw:
        try:
            parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def _nested_payload(item: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ('research_data', 'company_research'):
        value = item.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def _first_value(item: Mapping[str, Any], nested: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, ''):
            return value
        nested_value = nested.get(key)
        if nested_value not in (None, ''):
            return nested_value
    return None


def _first_text(item: Mapping[str, Any], nested: Mapping[str, Any], keys: Sequence[str]) -> str:
    value = _first_value(item, nested, keys)
    return _as_str(value)


def _optional_text(value: str) -> str | None:
    return value or None


def _as_str(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ''


def _list_of_strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _recent_news(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        if isinstance(item, Mapping):
            title = _as_str(item.get('title'))
            if title:
                normalized.append(title)
        elif str(item).strip():
            normalized.append(str(item).strip())
    return normalized


def _source(raw: str) -> ResearchSource:
    try:
        return ResearchSource(raw)
    except ValueError:
        return ResearchSource.WEBSITE_SCRAPE


def _normalize_company(value: str) -> str:
    return ' '.join(value.lower().split())


def _json_default(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f'Object of type {type(value).__name__} is not JSON serializable')


def _print_plan(result: MigrationResult, *, apply: bool) -> None:
    mode = 'APPLY' if apply else 'DRY-RUN'
    print(f'Company Research migration plan ({mode})')
    print(
        'Linkage rule: explicit legacy application_id verified in applications-table; else explicit jobs-table application_id '
        'with matching user_id+company_name; else unique userId+company_name applications-table match.'
    )
    print(f'scanned={result.scanned_count}')
    print(f'migrate={result.migrate_count}')
    print(f'skip-already-present={result.skip_already_present_count}')
    print(f'quarantine={result.quarantine_count}')
    if result.quarantine_report_path is not None:
        print(f'quarantine_report={result.quarantine_report_path}')

    for action in result.actions:
        app_part = f' application_id={action.application_id}' if action.application_id else ''
        reason_part = f' reason={action.reason}' if action.reason else ''
        print(
            f'- {action.category}: user_id={action.user_id} legacy_sk={action.legacy_sk}'
            f' cr_job_id={action.cr_job_id}{app_part} company_name={action.company_name!r}{reason_part}'
        )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Backfill legacy Company Research records into canonical artifacts-table.')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true', help='Plan only; this is the default.')
    mode.add_argument('--apply', action='store_true', help='Write migrated artifacts and a quarantine report.')
    parser.add_argument('--users-table', default=DEFAULT_USERS_TABLE)
    parser.add_argument('--artifacts-table', default=DEFAULT_ARTIFACTS_TABLE)
    parser.add_argument('--applications-table', default=DEFAULT_APPLICATIONS_TABLE)
    parser.add_argument('--jobs-table', default=DEFAULT_JOBS_TABLE)
    parser.add_argument('--region', default=DEFAULT_REGION)
    parser.add_argument('--allow-nondev', action='store_true')
    parser.add_argument('--quarantine-report', type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    config = MigrationConfig(
        users_table_name=str(args.users_table),
        artifacts_table_name=str(args.artifacts_table),
        applications_table_name=str(args.applications_table),
        jobs_table_name=str(args.jobs_table) if args.jobs_table else None,
        region_name=str(args.region),
        apply=bool(args.apply),
        allow_nondev=bool(args.allow_nondev),
        quarantine_report_path=args.quarantine_report,
    )
    try:
        result = run_migration(config)
    except (ClientError, ValueError) as exc:
        print(f'BLOCKING ISSUE: Company Research migration could not run: {exc}', file=sys.stderr)
        return 1
    _print_plan(result, apply=config.apply)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
