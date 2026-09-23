"""Review a CloudFormation change set without needing to know AWS deeply.

A change set is CloudFormation's own answer to "if I apply this, what will
happen?" — computed by AWS, not predicted by a tool and not guessed by a human.
This script reads one and reduces it to a single column you have to understand:

    GO     safe to apply
    READ   apply after reading this line — it widens permissions or removes
           something rebuildable
    STOP   applying this destroys data

The only AWS-specific knowledge required to use it is which resource types hold
data. That list is STATEFUL_TYPES below, and it is four entries long.

Why "Replacement: True" is the dangerous word
---------------------------------------------
CloudFormation cannot change some properties in place. To honour the change it
deletes the resource and creates a new one. For a Lambda that is a blip. For a
DynamoDB table it means the application is now pointed at an empty table — the
old rows may survive under DeletionPolicy=Retain, but nothing reads them any
more. That is indistinguishable from data loss for a customer.

Usage
-----
    uv run python scripts/review_change.py --stack CareerVpCrudDev --latest
    uv run python scripts/review_change.py --stack X --change-set my-changeset

Exit code is 1 if any change is STOP, 0 otherwise.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final

import boto3
from botocore.exceptions import BotoCoreError, ClientError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_stamp import write_proof  # noqa: E402

GO: Final[str] = 'GO'
READ: Final[str] = 'READ'
STOP: Final[str] = 'STOP'

# The whole AWS-specific knowledge requirement. Everything not in this tuple can
# be rebuilt from source; everything in it holds work a customer would miss.
STATEFUL_TYPES: Final[tuple[str, ...]] = (
    'AWS::DynamoDB::Table',
    'AWS::DynamoDB::GlobalTable',
    'AWS::S3::Bucket',
    'AWS::Cognito::UserPool',
)

# Changing these can grant access that did not exist before. Not dangerous by
# default — but the one category where reading the diff is genuinely worth it.
PERMISSION_TYPES: Final[tuple[str, ...]] = (
    'AWS::IAM::Role',
    'AWS::IAM::Policy',
    'AWS::IAM::ManagedPolicy',
    'AWS::IAM::User',
    'AWS::IAM::Group',
    'AWS::Lambda::Permission',
    'AWS::S3::BucketPolicy',
    'AWS::SQS::QueuePolicy',
    'AWS::SNS::TopicPolicy',
    'AWS::KMS::Key',
)


@dataclass
class Verdict:
    action: str
    replacement: str
    resource_type: str
    logical_id: str
    ruling: str
    reason: str


def is_stateful(resource_type: str) -> bool:
    return resource_type in STATEFUL_TYPES


def recreation_causes(change: dict[str, Any]) -> list[str]:
    """Which property forces the replacement — the 'why' behind a STOP."""
    causes: list[str] = []
    for detail in change.get('Details', []) or []:
        target = detail.get('Target') or {}
        if target.get('RequiresRecreation') in {'Always', 'Conditionally'}:
            name = target.get('Name') or target.get('Attribute') or 'unknown property'
            if name not in causes:
                causes.append(str(name))
    return causes


def judge(change: dict[str, Any]) -> Verdict:
    action = str(change.get('Action', '?'))
    replacement = str(change.get('Replacement', '-'))
    resource_type = str(change.get('ResourceType', '?'))
    logical_id = str(change.get('LogicalResourceId', '?'))
    stateful = is_stateful(resource_type)
    causes = recreation_causes(change)
    cause_text = f' Cause: {", ".join(causes)}.' if causes else ''

    if action == 'Remove':
        if stateful:
            return Verdict(action, replacement, resource_type, logical_id, STOP, 'Removes a resource that holds data.')
        return Verdict(
            action, replacement, resource_type, logical_id, READ, 'Removes a resource. Rebuildable, but confirm nothing still points at it.'
        )

    if action == 'Add':
        return Verdict(action, replacement, resource_type, logical_id, GO, 'New resource.')

    if replacement in {'True', 'Conditional'}:
        if stateful:
            qualifier = 'will' if replacement == 'True' else 'may'
            return Verdict(
                action,
                replacement,
                resource_type,
                logical_id,
                STOP,
                f'CloudFormation {qualifier} DELETE and RECREATE this resource. The application would be pointed at an empty one.{cause_text}',
            )
        return Verdict(
            action, replacement, resource_type, logical_id, READ, f'Resource is replaced. Stateless, so expect a brief interruption only.{cause_text}'
        )

    if resource_type in PERMISSION_TYPES:
        return Verdict(action, replacement, resource_type, logical_id, READ, 'Changes permissions. One question: does it grant more than before?')

    return Verdict(action, replacement, resource_type, logical_id, GO, 'In-place modification.')


def fetch_changes(stack: str, change_set: str) -> list[dict[str, Any]]:
    client = boto3.client('cloudformation')
    changes: list[dict[str, Any]] = []
    token: str | None = None
    while True:
        kwargs: dict[str, Any] = {'StackName': stack, 'ChangeSetName': change_set}
        if token:
            kwargs['NextToken'] = token
        response = client.describe_change_set(**kwargs)
        for entry in response.get('Changes', []):
            resource_change = entry.get('ResourceChange')
            if resource_change:
                changes.append(resource_change)
        token = response.get('NextToken')
        if not token:
            return changes


def latest_change_set(stack: str) -> str:
    client = boto3.client('cloudformation')
    summaries = client.list_change_sets(StackName=stack).get('Summaries', [])
    if not summaries:
        raise SystemExit(f'no change sets on {stack}. Create one first: make create-changeset')
    newest = max(summaries, key=lambda s: s.get('CreationTime'))
    return str(newest.get('ChangeSetName'))


def render(stack: str, change_set: str, verdicts: Sequence[Verdict]) -> str:
    if not verdicts:
        return f'CHANGE SET  {change_set} on {stack}\n\nNo resource changes. Nothing to review.'

    headers = ('Action', 'Replace', 'Type', 'LogicalId')
    widths = (
        max(len(headers[0]), *(len(v.action) for v in verdicts)),
        max(len(headers[1]), *(len(v.replacement) for v in verdicts)),
        max(len(headers[2]), *(len(v.resource_type) for v in verdicts)),
        max(len(headers[3]), *(len(v.logical_id) for v in verdicts)),
    )
    order = {STOP: 0, READ: 1, GO: 2}
    ordered = sorted(verdicts, key=lambda v: order[v.ruling])

    lines = [
        f'CHANGE SET  {change_set}  on  {stack}  ·  {len(verdicts)} changes',
        '',
        f'  {headers[0].ljust(widths[0])}  {headers[1].ljust(widths[1])}  {headers[2].ljust(widths[2])}  {headers[3].ljust(widths[3])}  Ruling',
    ]
    for verdict in ordered:
        lines.append(
            f'  {verdict.action.ljust(widths[0])}  {verdict.replacement.ljust(widths[1])}  '
            f'{verdict.resource_type.ljust(widths[2])}  {verdict.logical_id.ljust(widths[3])}  {verdict.ruling}'
        )
        if verdict.ruling != GO:
            lines.append(f'      ↑ {verdict.reason}')

    counts = {ruling: sum(1 for v in verdicts if v.ruling == ruling) for ruling in (STOP, READ, GO)}
    lines += ['', f'VERDICT: {counts[STOP]} STOP · {counts[READ]} READ · {counts[GO]} GO']
    if counts[STOP]:
        lines.append('Do not execute this change set. Resolve every STOP first.')
    elif counts[READ]:
        lines.append('Read each READ line above, then execute if you agree with it.')
    else:
        lines.append('Safe to execute.')
    return '\n'.join(lines)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Classify a CloudFormation change set into GO / READ / STOP')
    parser.add_argument('--stack', required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--change-set')
    group.add_argument('--latest', action='store_true', help='use the most recently created change set on the stack')
    parser.add_argument('--no-write', action='store_true')
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        change_set = latest_change_set(args.stack) if args.latest else args.change_set
        changes = fetch_changes(args.stack, change_set)
    except (BotoCoreError, ClientError) as exc:
        print(f'cannot read change set: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2

    verdicts = [judge(change) for change in changes]
    print(render(args.stack, change_set, verdicts))

    if not args.no_write:
        path = write_proof(
            'change-review',
            {'change_set': change_set, 'verdicts': [asdict(v) for v in verdicts]},
            stack=args.stack,
            read_deployed=False,
        )
        print(f'\nproof: {path}')

    return 1 if any(v.ruling == STOP for v in verdicts) else 0


if __name__ == '__main__':
    raise SystemExit(main())
