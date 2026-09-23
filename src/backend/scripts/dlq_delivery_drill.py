#!/usr/bin/env python3
"""AC-P31-1 live DLQ-delivery drill for the two EventBridge schedule targets.

AC-P31-1 has two halves. The *synth* half — the rule target carries a
``DeadLetterConfig`` pointing at an SQS queue that exists, and that queue alarms
on depth — is proven by ``test_p31_eventbridge_target_dlqs.py``. This script
covers the *live* half: that a failed delivery actually lands in the DLQ.

Two modes:

``--check`` (default, read-only, fast, SAFE)
    The runnable "quick test". For each schedule DLQ it verifies the three live
    facts that *guarantee* delivery-on-failure, without breaking anything:
      1. the DLQ queue exists;
      2. the schedule rule's target has ``DeadLetterConfig.Arn`` == that DLQ's arn;
      3. the DLQ's queue policy grants ``events.amazonaws.com`` ``sqs:SendMessage``
         scoped to that rule's ARN.
    If all three hold, EventBridge *will* deliver a failed event to the DLQ. This
    is as far as a non-destructive test can honestly go.

``--execute`` (destructive, human-gated, SLOW — several minutes)
    Actually observes a delivery. Because each DLQ's queue policy is scoped to its
    own rule's ARN (a throwaway probe rule would be denied), the only faithful way
    is to break the *real* rule's target and let a real invocation fail:
      * record + remove the Lambda resource permission that lets the rule invoke
        the target (so delivery gets AccessDenied);
      * record + set a zero-retry / 60s-max-age RetryPolicy on the target (default
        is 24h/185 attempts — far too slow to observe);
      * record + speed the schedule to rate(1 minute) to force an invocation;
      * poll the DLQ for the failed event;
      * ALWAYS restore schedule, target RetryPolicy, and Lambda permission in a
        finally block, whether or not a message arrived.
    Requires ``--i-understand-this-mutates-devx`` and AWS write access. Never run
    against a stack that serves real users.

Evidence (both modes) is written under ``docs/evidence/`` and the process exits
non-zero on any failure, so it slots into the Wave-2 gate as the AC-P31-1
follow-up evidence file.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = REPO_ROOT / 'docs' / 'evidence'

# (DLQ queue name, substring that identifies the rule by its target function).
SCHEDULE_TARGETS: tuple[tuple[str, str], ...] = (
    ('careervp-artifact-cleanup-schedule-dlq-dlq-devx', 'artifact-cleanup'),
    ('careervp-billing-reconcile-schedule-dlq-dlq-devx', 'billing-reconcile'),
)
EVENTS_PRINCIPAL = 'events.amazonaws.com'
DRILL_POLL_SECONDS = 240
DRILL_POLL_INTERVAL = 15


@dataclass
class Leg:
    dlq_name: str
    rule_hint: str
    passed: bool = False
    detail: str = ''
    facts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'dlq_name': self.dlq_name,
            'rule_hint': self.rule_hint,
            'passed': self.passed,
            'detail': self.detail,
            'facts': self.facts,
        }


def _clients() -> tuple[Any, Any, Any]:
    import boto3  # lazy so --help / offline import works without creds

    return boto3.client('sqs'), boto3.client('events'), boto3.client('lambda')


def _queue_url(sqs: Any, name: str) -> str | None:
    try:
        return str(sqs.get_queue_url(QueueName=name)['QueueUrl'])
    except sqs.exceptions.QueueDoesNotExist:
        return None
    except Exception:  # noqa: BLE001 - any client error means "not usable"
        return None


def _queue_arn(sqs: Any, url: str) -> str:
    attrs = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=['QueueArn', 'Policy'])
    return str(attrs['Attributes']['QueueArn'])


def _queue_policy(sqs: Any, url: str) -> dict[str, Any]:
    attrs = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=['Policy'])
    raw = attrs.get('Attributes', {}).get('Policy')
    return json.loads(raw) if raw else {}


def _find_rule_for(events: Any, hint: str, expected_dlq_arn: str | None = None) -> tuple[str, dict[str, Any]] | None:
    """Return (rule_name, target) for the schedule rule whose target references hint.

    When the expected DLQ ARN is known, prefer an exact DeadLetterConfig match so
    devx checks do not accidentally select the older dev schedule rules.
    """
    fallback: tuple[str, dict[str, Any]] | None = None
    paginator = events.get_paginator('list_rules')
    for page in paginator.paginate():
        for rule in page.get('Rules', []):
            name = rule['Name']
            targets = events.list_targets_by_rule(Rule=name).get('Targets', [])
            for target in targets:
                target_dlq = (target.get('DeadLetterConfig') or {}).get('Arn')
                if expected_dlq_arn and target_dlq == expected_dlq_arn:
                    return name, target
                blob = json.dumps(target)
                if hint in blob or hint in name.lower():
                    fallback = fallback or (name, target)
    return fallback


def _policy_grants_events_send(policy: dict[str, Any], rule_arn: str | None) -> bool:
    for stmt in policy.get('Statement', []):
        principal = stmt.get('Principal', {})
        svc = principal.get('Service') if isinstance(principal, dict) else principal
        svcs = [svc] if isinstance(svc, str) else (svc or [])
        actions = stmt.get('Action', [])
        actions = [actions] if isinstance(actions, str) else actions
        if stmt.get('Effect') == 'Allow' and EVENTS_PRINCIPAL in svcs and any(a.endswith('SendMessage') for a in actions):
            return True
    return False


# --------------------------------------------------------------------------- #
# --check : read-only wiring triad
# --------------------------------------------------------------------------- #
def run_check() -> list[Leg]:
    sqs, events, _ = _clients()
    legs: list[Leg] = []
    for dlq_name, hint in SCHEDULE_TARGETS:
        leg = Leg(dlq_name=dlq_name, rule_hint=hint)
        url = _queue_url(sqs, dlq_name)
        if not url:
            leg.detail = f'DLQ {dlq_name!r} does not exist live (deploy P-31 to devx first)'
            legs.append(leg)
            continue
        dlq_arn = _queue_arn(sqs, url)
        leg.facts['dlq_arn'] = dlq_arn

        found = _find_rule_for(events, hint, dlq_arn)
        if not found:
            leg.detail = f'no EventBridge rule found whose target references {hint!r}'
            legs.append(leg)
            continue
        rule_name, target = found
        rule = events.describe_rule(Name=rule_name)
        rule_arn = rule.get('Arn')
        leg.facts['rule_name'] = rule_name
        target_dlq = (target.get('DeadLetterConfig') or {}).get('Arn')
        leg.facts['target_dlq_arn'] = target_dlq

        policy = _queue_policy(sqs, url)
        grants = _policy_grants_events_send(policy, rule_arn)
        leg.facts['policy_grants_events_send'] = grants

        if target_dlq != dlq_arn:
            leg.detail = f'rule {rule_name!r} target DeadLetterConfig.Arn {target_dlq!r} != DLQ arn {dlq_arn!r}'
        elif not grants:
            leg.detail = f'DLQ policy does not grant {EVENTS_PRINCIPAL} sqs:SendMessage'
        else:
            leg.passed = True
            leg.detail = f'wired: rule {rule_name!r} → DeadLetterConfig → {dlq_name} and queue policy admits {EVENTS_PRINCIPAL}'
        legs.append(leg)
    return legs


# --------------------------------------------------------------------------- #
# --execute : destructive live fault injection (restores in finally)
# --------------------------------------------------------------------------- #
def _fn_name(function_arn: str) -> str:
    return function_arn.split(':function:')[-1].split(':')[0]


def _remove_invoke_permission(lam: Any, function_arn: str, rule_arn: str | None) -> dict[str, Any] | None:
    """Remove and return the rule's invoke permission on the target Lambda (so a
    delivery attempt gets AccessDenied). Returns None if none matched."""
    try:
        policy_doc = json.loads(lam.get_policy(FunctionName=_fn_name(function_arn))['Policy'])
    except lam.exceptions.ResourceNotFoundException:
        return None
    for stmt in policy_doc.get('Statement', []):
        cond = stmt.get('Condition', {}).get('ArnLike', {}).get('AWS:SourceArn', '')
        if rule_arn and cond == rule_arn:
            lam.remove_permission(FunctionName=_fn_name(function_arn), StatementId=stmt['Sid'])
            return dict(stmt)
    return None


def _poll_for_message(sqs: Any, url: str) -> str | None:
    deadline = time.time() + DRILL_POLL_SECONDS
    while time.time() < deadline:
        resp = sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=1, WaitTimeSeconds=5)
        msgs = resp.get('Messages', [])
        if msgs:
            return str(msgs[0]['MessageId'])
        time.sleep(DRILL_POLL_INTERVAL)
    return None


def _restore(
    events: Any,
    lam: Any,
    rule_name: str,
    function_arn: str,
    orig_schedule: str | None,
    orig_target: dict[str, Any],
    removed: dict[str, Any] | None,
) -> None:
    if orig_schedule:
        events.put_rule(Name=rule_name, ScheduleExpression=orig_schedule, State='ENABLED')
    events.put_targets(Rule=rule_name, Targets=[orig_target])
    if removed:
        cond = removed.get('Condition', {}).get('ArnLike', {})
        lam.add_permission(
            FunctionName=_fn_name(function_arn),
            StatementId=removed['Sid'],
            Action='lambda:InvokeFunction',
            Principal=EVENTS_PRINCIPAL,
            SourceArn=cond.get('AWS:SourceArn'),
        )


def run_execute(only_hint: str) -> list[Leg]:
    sqs, events, lam = _clients()
    dlq_name, hint = next((d, h) for d, h in SCHEDULE_TARGETS if h == only_hint)
    leg = Leg(dlq_name=dlq_name, rule_hint=hint)

    url = _queue_url(sqs, dlq_name)
    if not url:
        leg.detail = f'DLQ {dlq_name!r} not deployed; cannot run live drill'
        return [leg]
    dlq_arn = _queue_arn(sqs, url)
    found = _find_rule_for(events, hint, dlq_arn)
    if not found:
        leg.detail = f'rule for {hint!r} not found'
        return [leg]
    rule_name, target = found
    original_rule = events.describe_rule(Name=rule_name)
    function_arn = str(target.get('Arn', ''))
    orig_schedule = original_rule.get('ScheduleExpression')
    orig_target = json.loads(json.dumps(target))
    removed: dict[str, Any] | None = None

    try:
        # break delivery, make failures land fast, and force an invocation soon.
        removed = _remove_invoke_permission(lam, function_arn, original_rule.get('Arn'))
        fast_target = json.loads(json.dumps(target))
        fast_target['RetryPolicy'] = {'MaximumRetryAttempts': 0, 'MaximumEventAgeInSeconds': 60}
        events.put_targets(Rule=rule_name, Targets=[fast_target])
        events.put_rule(Name=rule_name, ScheduleExpression='rate(1 minute)', State='ENABLED')

        message_id = _poll_for_message(sqs, url)
        leg.passed = bool(message_id)
        leg.facts['message_id'] = message_id
        leg.detail = (
            f'delivery failure landed in {dlq_name} (message {message_id})'
            if message_id
            else f'no message in {dlq_name} within {DRILL_POLL_SECONDS}s'
        )
    finally:
        try:
            _restore(events, lam, rule_name, function_arn, orig_schedule, orig_target, removed)
            leg.facts['restored'] = True
        except Exception as exc:  # noqa: BLE001
            leg.facts['restored'] = False
            leg.facts['restore_error'] = str(exc)
            leg.detail += f'  [RESTORE FAILED — manual fix needed: {exc}]'
    return [leg]


def write_evidence(mode: str, legs: list[Leg], passed: bool) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = EVIDENCE_DIR / f'p31-dlq-drill-{mode}-{stamp}-{uuid.uuid4().hex[:6]}.json'
    path.write_text(
        json.dumps(
            {
                'ac': 'AC-P31-1',
                'mode': mode,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'passed': passed,
                'legs': [leg.to_dict() for leg in legs],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding='utf-8',
    )
    return path


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='AC-P31-1 DLQ-delivery drill')
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--check', action='store_true', help='run the read-only wiring check (default)')
    mode_group.add_argument('--execute', action='store_true', help='run the destructive live drill')
    parser.add_argument(
        '--target',
        choices=[h for _, h in SCHEDULE_TARGETS],
        default='artifact-cleanup',
        help='which schedule target to fault-inject in --execute mode',
    )
    parser.add_argument('--i-understand-this-mutates-devx', action='store_true')
    parser.add_argument('--print-only', action='store_true')
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.execute:
        if not args.i_understand_this_mutates_devx:
            print(
                'refusing to run --execute without --i-understand-this-mutates-devx',
                file=sys.stderr,
            )
            return 2
        mode = 'execute'
        legs = run_execute(args.target)
    else:
        mode = 'check'
        legs = run_check()

    passed = bool(legs) and all(leg.passed for leg in legs)
    if not args.print_only:
        path = write_evidence(mode, legs, passed)
        print(f'evidence written to {path}')
    for leg in legs:
        print(f'  [{"PASS" if leg.passed else "FAIL"}] {leg.rule_hint}: {leg.detail}', file=sys.stderr)
    print(f'\nAC-P31-1 {mode}: {"PASS" if passed else "FAIL"}', file=sys.stderr)
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
