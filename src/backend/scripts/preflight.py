"""Preflight — check the facts your work is about to rest on, before it does.

Why this exists
---------------
Work on this project has repeatedly been built on an assumption about AWS
configuration that turned out to be false — and the assumption was never
re-tested, so days of work sat on top of it before anyone noticed. The defence
is not "be more careful". It is to make the premises *executable*, cheap, and
run at the start of every session, so a wrong one dies in seconds instead of
becoming load-bearing.

Three results, not two
----------------------
    PASS      a command ran and the fact holds
    FAIL      a command ran and the fact does not hold
    UNKNOWN   the fact could not be checked at all

UNKNOWN is deliberately distinct from PASS. "I could not check whether access
logging is on" must never be read as "access logging is on" — that specific
confusion is the reason this file exists.

Nothing here is guessed
-----------------------
Resource names are *discovered* from the live CloudFormation stack (including
nested stacks) rather than hardcoded, so this script cannot quietly check the
wrong table or a Lambda that no longer exists.

Usage
-----
    uv run python scripts/preflight.py                     # default stack
    uv run python scripts/preflight.py --stack CareerVpCrudDev
    uv run python scripts/preflight.py --json              # machine-readable

Exit code is 1 if any premise FAILS, 0 otherwise. UNKNOWNs are reported loudly
but do not fail the run: not knowing is a reason to look, not a reason to stop.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Final

import boto3
from botocore.exceptions import BotoCoreError, ClientError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_stamp import DEFAULT_STACK, describe_stamp, stamp, write_proof  # noqa: E402

PASS: Final[str] = 'PASS'
FAIL: Final[str] = 'FAIL'
UNKNOWN: Final[str] = 'UNKNOWN'

# Resource types that hold data. Losing one of these loses customer work; every
# other resource in the stack can be rebuilt from source. This tuple is the
# entire AWS-specific knowledge a reviewer needs to carry.
STATEFUL_TYPES: Final[tuple[str, ...]] = (
    'AWS::DynamoDB::Table',
    'AWS::DynamoDB::GlobalTable',
    'AWS::S3::Bucket',
    'AWS::Cognito::UserPool',
)

MIN_LOG_RETENTION_DAYS: Final[int] = 7


@dataclass
class Premise:
    """One fact, the command that checked it, and what came back."""

    name: str
    status: str
    detail: str
    command: str
    observed: Any = field(default=None)


@dataclass
class Inventory:
    """What the live stack actually contains, discovered not assumed."""

    resources: list[dict[str, str]]
    nested_stacks: list[str]
    errors: list[str]

    def of_type(self, resource_type: str) -> list[dict[str, str]]:
        return [r for r in self.resources if r['type'] == resource_type]

    def of_types(self, types: Sequence[str]) -> list[dict[str, str]]:
        return [r for r in self.resources if r['type'] in types]


def _client(service: str) -> Any:
    return boto3.client(service)


def discover(stack: str) -> Inventory:
    """Walk the stack and every nested stack, listing what is really there."""
    resources: list[dict[str, str]] = []
    nested: list[str] = []
    errors: list[str] = []
    pending = [stack]
    seen: set[str] = set()

    cfn = _client('cloudformation')
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        try:
            paginator = cfn.get_paginator('list_stack_resources')
            for page in paginator.paginate(StackName=current):
                for summary in page.get('StackResourceSummaries', []):
                    entry = {
                        'stack': current,
                        'logical_id': summary.get('LogicalResourceId', ''),
                        'physical_id': summary.get('PhysicalResourceId', ''),
                        'type': summary.get('ResourceType', ''),
                        'status': summary.get('ResourceStatus', ''),
                    }
                    resources.append(entry)
                    if entry['type'] == 'AWS::CloudFormation::Stack' and entry['physical_id']:
                        nested.append(entry['physical_id'])
                        pending.append(entry['physical_id'])
        except (BotoCoreError, ClientError) as exc:
            errors.append(f'{current}: {type(exc).__name__}')

    return Inventory(resources=resources, nested_stacks=nested, errors=errors)


# --------------------------------------------------------------------------
# Premises. Each returns exactly one Premise and never raises: an exception is
# an UNKNOWN, not a crash, because a crashed preflight teaches you nothing.
# --------------------------------------------------------------------------


def premise_stack_healthy(stack: str) -> Premise:
    command = f'aws cloudformation describe-stacks --stack-name {stack}'
    try:
        response = _client('cloudformation').describe_stacks(StackName=stack)
    except (BotoCoreError, ClientError) as exc:
        return Premise('stack healthy', UNKNOWN, f'cannot describe: {type(exc).__name__}', command)

    stacks = response.get('Stacks', [])
    if not stacks:
        return Premise('stack healthy', FAIL, 'stack not found', command)

    status = str(stacks[0].get('StackStatus', ''))
    updated = str(stacks[0].get('LastUpdatedTime', stacks[0].get('CreationTime', '')))
    ok = status.endswith('_COMPLETE') and 'ROLLBACK' not in status
    return Premise(
        'stack healthy',
        PASS if ok else FAIL,
        f'{status}, last updated {updated}',
        command,
        observed={'status': status, 'last_updated': updated},
    )


def premise_sha_stamped(header: dict[str, Any]) -> Premise:
    command = 'aws cloudformation describe-stacks --query "Stacks[0].Outputs[?OutputKey==\'DeployedGitSha\']"'
    deployed = header.get('deployed_sha')
    if not deployed:
        return Premise('deployed commit is known', UNKNOWN, str(header.get('deployed_sha_detail')), command)
    if deployed.endswith('-dirty'):
        return Premise(
            'deployed commit is known',
            FAIL,
            f'stack was deployed from a DIRTY tree ({deployed}) — the running code is not in git',
            command,
            observed=deployed,
        )
    matches = header.get('deployed_matches_head')
    if matches is True:
        return Premise('deployed commit is known', PASS, f'stack runs {deployed[:7]}, same as HEAD', command, observed=deployed)
    return Premise(
        'deployed commit is known',
        PASS,
        f'stack runs {deployed[:7]}; your HEAD is {str(header.get("git_short"))} — deploy before trusting live results',
        command,
        observed=deployed,
    )


def premise_access_logging(inventory: Inventory) -> Premise:
    apis = inventory.of_type('AWS::ApiGateway::RestApi')
    command = 'aws apigateway get-stages --rest-api-id <id>'
    if not apis:
        return Premise('api access logging enabled', UNKNOWN, 'no RestApi found in the stack', command)

    api_id = apis[0]['physical_id']
    command = f'aws apigateway get-stages --rest-api-id {api_id}'
    try:
        stages = _client('apigateway').get_stages(restApiId=api_id).get('item', [])
    except (BotoCoreError, ClientError) as exc:
        return Premise('api access logging enabled', UNKNOWN, f'cannot read stages: {type(exc).__name__}', command)

    if not stages:
        return Premise('api access logging enabled', FAIL, f'{api_id} has no stages', command)

    without = [s.get('stageName', '?') for s in stages if not s.get('accessLogSettings', {}).get('destinationArn')]
    if without:
        return Premise('api access logging enabled', FAIL, f'no access log destination on stage(s): {", ".join(without)}', command)

    arns = [s['accessLogSettings']['destinationArn'] for s in stages]
    return Premise('api access logging enabled', PASS, f'{len(stages)} stage(s) logging', command, observed=arns)


def premise_log_retention(inventory: Inventory) -> Premise:
    apis = inventory.of_type('AWS::ApiGateway::RestApi')
    command = 'aws logs describe-log-groups --log-group-name-prefix <access log group>'
    if not apis:
        return Premise('access logs kept long enough', UNKNOWN, 'no RestApi found', command)

    api_id = apis[0]['physical_id']
    try:
        stages = _client('apigateway').get_stages(restApiId=api_id).get('item', [])
        arns = [s.get('accessLogSettings', {}).get('destinationArn') for s in stages]
        groups = [arn.split(':log-group:')[1].split(':')[0] for arn in arns if arn and ':log-group:' in arn]
    except (BotoCoreError, ClientError, IndexError) as exc:
        return Premise('access logs kept long enough', UNKNOWN, f'cannot resolve log groups: {type(exc).__name__}', command)

    if not groups:
        return Premise('access logs kept long enough', UNKNOWN, 'no access log group configured', command)

    command = f'aws logs describe-log-groups --log-group-name-prefix {groups[0]}'
    findings: list[str] = []
    worst = PASS
    for group in groups:
        try:
            described = _client('logs').describe_log_groups(logGroupNamePrefix=group).get('logGroups', [])
        except (BotoCoreError, ClientError) as exc:
            findings.append(f'{group}: unreadable ({type(exc).__name__})')
            worst = UNKNOWN if worst == PASS else worst
            continue
        match = next((g for g in described if g.get('logGroupName') == group), None)
        if match is None:
            findings.append(f'{group}: not found')
            worst = FAIL
            continue
        days = match.get('retentionInDays')
        if days is None:
            findings.append(f'{group}: never expires')
            continue
        findings.append(f'{group}: {days}d')
        if int(days) < MIN_LOG_RETENTION_DAYS:
            worst = FAIL

    return Premise('access logs kept long enough', worst, '; '.join(findings), command, observed=findings)


def premise_stateful_retained(stack: str, inventory: Inventory) -> Premise:
    """Would an accidental stack delete take the data with it?

    Read from the *deployed* template, not from local source: what protects
    live data is the policy CloudFormation is holding, not the one in the repo.
    """
    command = f'aws cloudformation get-template --stack-name {stack}'
    stateful = inventory.of_types(STATEFUL_TYPES)
    if not stateful:
        return Premise('stateful resources retained', UNKNOWN, 'no stateful resources discovered', command)

    cfn = _client('cloudformation')
    templates: dict[str, dict[str, Any]] = {}
    for stack_name in {r['stack'] for r in stateful}:
        try:
            body = cfn.get_template(StackName=stack_name).get('TemplateBody')
        except (BotoCoreError, ClientError) as exc:
            return Premise('stateful resources retained', UNKNOWN, f'cannot read template for {stack_name}: {type(exc).__name__}', command)
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                return Premise(
                    'stateful resources retained', UNKNOWN, f'template for {stack_name} is not JSON (YAML templates unsupported here)', command
                )
        templates[stack_name] = body if isinstance(body, dict) else {}

    unprotected: list[str] = []
    protected = 0
    for resource in stateful:
        definition = templates.get(resource['stack'], {}).get('Resources', {}).get(resource['logical_id'], {})
        policy = definition.get('DeletionPolicy')
        if policy == 'Retain':
            protected += 1
        else:
            unprotected.append(f'{resource["logical_id"]} ({resource["type"].split("::")[-1]}, DeletionPolicy={policy or "none"})')

    if unprotected:
        return Premise(
            'stateful resources retained',
            FAIL,
            f'{len(unprotected)} unprotected: ' + '; '.join(unprotected[:5]),
            command,
            observed=unprotected,
        )
    return Premise('stateful resources retained', PASS, f'{protected}/{protected} Retain', command, observed=protected)


def tables_the_code_uses(inventory: Inventory) -> tuple[set[str], int]:
    """Which tables does the *running code* expect?

    Derived from the deployed Lambda environment variables rather than from a
    hardcoded list, so this cannot drift out of date and cannot check a table
    the application stopped using.
    """
    lam = _client('lambda')
    wanted: set[str] = set()
    unreadable = 0
    for function in inventory.of_type('AWS::Lambda::Function'):
        try:
            config = lam.get_function_configuration(FunctionName=function['physical_id'])
        except (BotoCoreError, ClientError):
            unreadable += 1
            continue
        for key, value in (config.get('Environment', {}).get('Variables', {}) or {}).items():
            if 'TABLE' in key.upper() and isinstance(value, str) and value:
                wanted.add(value)
    return wanted, unreadable


def _classify_tables(names: Sequence[str], managed: set[str]) -> tuple[list[str], list[str], list[str]]:
    """Sort table names into (missing, inactive, unmanaged)."""
    ddb = _client('dynamodb')
    missing: list[str] = []
    inactive: list[str] = []
    unmanaged: list[str] = []

    for name in names:
        try:
            status = ddb.describe_table(TableName=name)['Table']['TableStatus']
        except ClientError as exc:
            code = exc.response.get('Error', {}).get('Code')
            (missing if code == 'ResourceNotFoundException' else inactive).append(name if code == 'ResourceNotFoundException' else f'{name}: {code}')
            continue
        except BotoCoreError as exc:
            inactive.append(f'{name}: {type(exc).__name__}')
            continue
        if status != 'ACTIVE':
            inactive.append(f'{name}: {status}')
        if name not in managed:
            unmanaged.append(name)

    return missing, inactive, unmanaged


def premise_tables(inventory: Inventory) -> Premise:
    """Do the tables the code points at exist, and does CloudFormation own them?

    Existence is not enough. A table that exists but is not a resource in any
    stack will not be recreated by a rebuild, will not be protected by a stack
    policy, and will not appear in a change-set review — so nothing warns you
    before it is lost. An unmanaged table is a table nobody is looking after.
    """
    command = 'aws lambda get-function-configuration (read TABLE env vars) + aws dynamodb describe-table'
    wanted, unreadable = tables_the_code_uses(inventory)
    if not wanted:
        detail = 'no TABLE env vars found on any Lambda' + (f' ({unreadable} unreadable)' if unreadable else '')
        return Premise('tables exist and are managed', UNKNOWN, detail, command)

    managed = {
        r['physical_id']
        for r in inventory.of_types(('AWS::DynamoDB::Table', 'AWS::DynamoDB::GlobalTable'))
    }
    missing, inactive, unmanaged = _classify_tables(sorted(wanted), managed)
    observed = {'wanted': sorted(wanted), 'missing': missing, 'inactive': inactive, 'unmanaged': unmanaged}

    if missing:
        return Premise(
            'tables exist and are managed',
            FAIL,
            f'{len(missing)} table(s) the code needs do not exist: ' + ', '.join(missing[:4]),
            command,
            observed=observed,
        )
    if inactive:
        return Premise('tables exist and are managed', FAIL, '; '.join(inactive[:4]), command, observed=observed)
    if unmanaged:
        return Premise(
            'tables exist and are managed',
            FAIL,
            f'{len(unmanaged)}/{len(wanted)} table(s) exist but NO CloudFormation stack owns them — a rebuild would not recreate them: '
            + ', '.join(unmanaged[:4]),
            command,
            observed=observed,
        )
    return Premise('tables exist and are managed', PASS, f'{len(wanted)}/{len(wanted)} exist, ACTIVE, and stack-managed', command, observed=observed)


def premise_lambda_code(stack: str, inventory: Inventory) -> Premise:
    """Did the last deploy ship the code to *every* function that shares a build?

    All application Lambdas point at one asset (constants.BUILD_FOLDER), so they
    must all report the same CodeSha256. If two report different ones, a deploy
    updated some functions and not others — the silent partial deploy.

    Functions are grouped by the asset key in the *deployed template*, not by
    name. CDK generates its own helper Lambdas (bucket notifications, log
    retention) that legitimately carry their own code; grouping by asset keeps
    them out of the comparison instead of guessing from their names. An earlier
    version of this check flagged one such helper as a partial deploy — a false
    positive, and the reason the grouping is derived rather than assumed.
    """
    functions = inventory.of_type('AWS::Lambda::Function')
    command = 'aws cloudformation get-template (read Code.S3Key) + aws lambda get-function-configuration --query CodeSha256'
    if not functions:
        return Premise('one code build per asset', UNKNOWN, 'no Lambda functions discovered', command)

    cfn = _client('cloudformation')
    templates: dict[str, dict[str, Any]] = {}
    for stack_name in {f['stack'] for f in functions}:
        try:
            body = cfn.get_template(StackName=stack_name).get('TemplateBody')
        except (BotoCoreError, ClientError):
            continue
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                continue
        templates[stack_name] = body if isinstance(body, dict) else {}

    lam = _client('lambda')
    # asset key -> {code sha -> [logical ids]}
    by_asset: dict[str, dict[str, list[str]]] = {}
    last_modified: list[str] = []
    unreadable = 0

    for function in functions:
        definition = templates.get(function['stack'], {}).get('Resources', {}).get(function['logical_id'], {})
        code = definition.get('Properties', {}).get('Code', {})
        asset = str(code.get('S3Key') or ('inline' if 'ZipFile' in code else 'unknown'))
        try:
            config = lam.get_function_configuration(FunctionName=function['physical_id'])
        except (BotoCoreError, ClientError):
            unreadable += 1
            continue
        by_asset.setdefault(asset, {}).setdefault(str(config.get('CodeSha256', '?')), []).append(function['logical_id'])
        last_modified.append(str(config.get('LastModified', '')))

    if not by_asset:
        return Premise('one code build per asset', UNKNOWN, f'none of {len(functions)} functions readable', command)

    split = {asset: {sha[:12]: len(ids) for sha, ids in shas.items()} for asset, shas in by_asset.items() if len(shas) > 1}
    newest = max(last_modified) if last_modified else 'unknown'

    if split:
        return Premise(
            'one code build per asset',
            FAIL,
            f'{len(split)} asset(s) split across builds: {split} — a deploy shipped only part of the change',
            command,
            observed=split,
        )

    biggest = max(by_asset.values(), key=lambda shas: sum(len(v) for v in shas.values()))
    app_count = sum(len(v) for v in biggest.values())
    detail = f'{len(by_asset)} asset group(s), largest has {app_count} functions on one build; newest change {newest}'
    return Premise(
        'one code build per asset', PASS, detail, command, observed={'groups': len(by_asset), 'largest': app_count, 'last_modified': newest}
    )


def premise_llm_key(env: str) -> Premise:
    name = f'/careervp/{env}/anthropic-api-key'
    command = f'aws ssm get-parameter --name {name}'
    try:
        _client('ssm').get_parameter(Name=name, WithDecryption=False)
    except ClientError as exc:
        code = exc.response.get('Error', {}).get('Code', '')
        if code == 'ParameterNotFound':
            return Premise('llm api key present', FAIL, f'{name} does not exist — every AI feature will fail', command)
        return Premise('llm api key present', UNKNOWN, f'{code or type(exc).__name__}', command)
    except BotoCoreError as exc:
        return Premise('llm api key present', UNKNOWN, type(exc).__name__, command)
    return Premise('llm api key present', PASS, f'{name} exists', command, observed=name)


def premise_user_pool(inventory: Inventory) -> Premise:
    pools = inventory.of_type('AWS::Cognito::UserPool')
    command = 'aws cognito-idp describe-user-pool-client --user-pool-id <id> --client-id <id>'
    if not pools:
        return Premise('sign-in callbacks configured', UNKNOWN, 'no user pool discovered', command)

    clients = inventory.of_type('AWS::Cognito::UserPoolClient')
    if not clients:
        return Premise('sign-in callbacks configured', FAIL, 'user pool has no app client in this stack', command)

    pool_id = pools[0]['physical_id']
    idp = _client('cognito-idp')
    urls: list[str] = []
    for client in clients:
        try:
            described = idp.describe_user_pool_client(UserPoolId=pool_id, ClientId=client['physical_id'])
        except (BotoCoreError, ClientError) as exc:
            return Premise('sign-in callbacks configured', UNKNOWN, f'{type(exc).__name__}', command)
        urls.extend(described.get('UserPoolClient', {}).get('CallbackURLs', []) or [])

    if not urls:
        return Premise('sign-in callbacks configured', FAIL, 'no callback URLs — the browser sign-in flow cannot complete', command)
    return Premise('sign-in callbacks configured', PASS, f'{len(urls)} callback URL(s)', command, observed=urls)


def run_premises(stack: str, env: str) -> tuple[list[Premise], dict[str, Any], Inventory]:
    header = stamp(stack)
    inventory = discover(stack)

    premises = [
        premise_stack_healthy(stack),
        premise_sha_stamped(header),
        premise_access_logging(inventory),
        premise_log_retention(inventory),
        premise_stateful_retained(stack, inventory),
        premise_tables(inventory),
        premise_lambda_code(stack, inventory),
        premise_llm_key(env),
        premise_user_pool(inventory),
    ]
    return premises, header, inventory


def render(premises: Sequence[Premise], header: dict[str, Any], inventory: Inventory) -> str:
    marks = {PASS: '✔', FAIL: '✖', UNKNOWN: '?'}
    counts = {PASS: 0, FAIL: 0, UNKNOWN: 0}
    for premise in premises:
        counts[premise.status] += 1

    lines = [
        f'PREFLIGHT  {describe_stamp(header)}',
        f'           {counts[PASS]} pass · {counts[UNKNOWN]} unknown · {counts[FAIL]} fail'
        f'   ({len(inventory.resources)} resources across {len(inventory.nested_stacks) + 1} stacks)',
        '',
    ]
    width = max(len(p.name) for p in premises)
    for premise in premises:
        lines.append(f'{marks[premise.status]} {premise.name.ljust(width)}  {premise.detail}')
    if counts[UNKNOWN]:
        lines += [
            '',
            'UNKNOWN is not PASS. Each one above is a fact nobody has checked —',
            'resolve it or accept that work resting on it is unverified.',
        ]
    if inventory.errors:
        lines += ['', 'discovery errors: ' + '; '.join(inventory.errors)]
    return '\n'.join(lines)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Check the premises this session will rest on')
    parser.add_argument('--stack', default=DEFAULT_STACK)
    parser.add_argument('--env', default=None, help='SSM path segment; inferred from the stack name when omitted')
    parser.add_argument('--json', action='store_true', help='emit JSON instead of the table')
    parser.add_argument('--no-write', action='store_true', help='do not write a proof file')
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    env = args.env or ('devx' if args.stack.lower().endswith('devx') else 'dev')

    premises, header, inventory = run_premises(args.stack, env)
    payload = {
        'premises': [asdict(p) for p in premises],
        'resource_count': len(inventory.resources),
        'nested_stack_count': len(inventory.nested_stacks),
        'discovery_errors': inventory.errors,
    }

    if args.json:
        print(json.dumps({**header, **payload}, indent=2, sort_keys=True))
    else:
        print(render(premises, header, inventory))

    if not args.no_write:
        path = write_proof('preflight', payload, stack=args.stack)
        if not args.json:
            print(f'\nproof: {path}')

    return 1 if any(p.status == FAIL for p in premises) else 0


if __name__ == '__main__':
    raise SystemExit(main())
