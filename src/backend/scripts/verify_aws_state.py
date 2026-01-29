"""Verify that core CareerVP AWS resources exist (or do not exist)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from typing import Final

import boto3
from botocore.client import BaseClient  # type: ignore[import-untyped]
from botocore.exceptions import BotoCoreError, ClientError

DEFAULT_ENV: Final[str] = 'dev'
SERVICE_PREFIX: Final[str] = 'careervp'
EXPECTED_LAMBDAS: Final[tuple[str, ...]] = (
    'cv-parser',
    'vpr-generator',
)
EXPECTED_TABLES: Final[tuple[str, ...]] = (
    'users',
    'idempotency',
)
EXPECTED_BUCKET_PURPOSES: Final[tuple[str, ...]] = ('cvs',)


def _lambda_name(feature: str, env: str) -> str:
    return f'{SERVICE_PREFIX}-{feature}-lambda-{env}'


def _table_name(feature: str, env: str) -> str:
    return f'{SERVICE_PREFIX}-{feature}-table-{env}'


def _bucket_prefix(purpose: str, env: str) -> str:
    return f'{SERVICE_PREFIX}-{env}-{purpose}-'


def _check_exists(
    check_fn: Callable[[], None],
    identifier: str,
    should_exist: bool,
) -> tuple[bool, str]:
    try:
        check_fn()
        return should_exist, (f'✅ Found: {identifier}' if should_exist else f'⚠️ Still present: {identifier}')
    except ClientError as exc:
        error_code = exc.response.get('Error', {}).get('Code')
        if error_code in {'ResourceNotFoundException', 'NoSuchBucket'}:
            return (not should_exist), (f'✅ Absent: {identifier}' if not should_exist else f'❌ Missing: {identifier}')
        raise
    except BotoCoreError as exc:  # pragma: no cover - smoke test script
        return False, f'❌ BotoCoreError for {identifier}: {exc}'


def _lambda_check_factory(client: BaseClient, function_name: str) -> Callable[[], None]:
    def _check() -> None:
        client.get_function(FunctionName=function_name)

    return _check


def _table_check_factory(client: BaseClient, table_name: str) -> Callable[[], None]:
    def _check() -> None:
        client.describe_table(TableName=table_name)

    return _check


def verify_resources(mode: str, env: str = DEFAULT_ENV) -> int:
    should_exist = mode == 'deployed'
    lambda_client: BaseClient = boto3.client('lambda')
    dynamo_client: BaseClient = boto3.client('dynamodb')
    s3_client: BaseClient = boto3.client('s3')
    print(f'--- Verifying AWS State ({mode}) for environment: {env} ---')
    results: list[tuple[bool, str]] = []

    for feature in EXPECTED_LAMBDAS:
        name = _lambda_name(feature, env)
        results.append(
            _check_exists(
                _lambda_check_factory(lambda_client, name),
                f'Lambda {name}',
                should_exist,
            )
        )

    for feature in EXPECTED_TABLES:
        name = _table_name(feature, env)
        results.append(
            _check_exists(
                _table_check_factory(dynamo_client, name),
                f'DynamoDB {name}',
                should_exist,
            )
        )

    bucket_names = [bucket['Name'] for bucket in s3_client.list_buckets().get('Buckets', [])]
    for purpose in EXPECTED_BUCKET_PURPOSES:
        prefix = _bucket_prefix(purpose, env)
        matching = [name for name in bucket_names if name.startswith(prefix)]
        if should_exist:
            results.append(
                (
                    bool(matching),
                    f'✅ Bucket with prefix {prefix}* found: {matching[:1] or "n/a"}' if matching else f'❌ Bucket prefix missing: {prefix}*',
                )
            )
        else:
            results.append((not matching, f'✅ No buckets with prefix {prefix}*' if not matching else f'⚠️ Buckets still present: {matching}'))

    for _success_flag, message in results:
        print(message)

    if all(success for success, _ in results):
        print('\n✨ AWS state verification PASSED')
        return 0
    print('\n❌ AWS state verification FAILED')
    return 1


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Verify CareerVP AWS state.')
    parser.add_argument(
        '--mode',
        choices=['deployed', 'clean'],
        required=True,
        help='deployed=resources must exist, clean=resources must be absent.',
    )
    parser.add_argument(
        '--env',
        default=DEFAULT_ENV,
        help='Environment suffix used in resource names (default: dev).',
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    sys.exit(verify_resources(mode=args.mode, env=args.env))


if __name__ == '__main__':
    main()
