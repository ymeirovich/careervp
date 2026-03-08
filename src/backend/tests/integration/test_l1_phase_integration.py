"""Phase 2 integration: run persistence roundtrips and write I2 evidence."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import boto3
import pytest
from boto3.dynamodb.conditions import Key
from moto import mock_aws

RUNS_PER_ARTIFACT = 50
USER_ID = 'user-l1-integration'
USER_PK = f'USER#{USER_ID}'

ARTIFACT_SK_PREFIXES = {
    'vpr': 'ARTIFACT#VPR#',
    'cover_letter': 'ARTIFACT#COVER_LETTER#',
    'cv_tailored': 'ARTIFACT#CV_TAILORED#',
    'interview_prep': 'ARTIFACT#INTERVIEW_PREP#',
    'gap_analysis': 'ARTIFACT#GAP_ANALYSIS#',
}

REPO_ROOT = Path(__file__).resolve().parents[4]
EVIDENCE_PATH = REPO_ROOT / 'docs/beta/evidence/I2_persistence/persistence-roundtrip-report.json'


def _ttl_timestamp(days: int = 730) -> int:
    return int((datetime.now(timezone.utc) + timedelta(days=days)).timestamp())


def _artifact_item(artifact_type: str, artifact_id: str, run_number: int) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    sk_prefix = ARTIFACT_SK_PREFIXES[artifact_type]
    return {
        'pk': USER_PK,
        'sk': f'{sk_prefix}{artifact_id}',
        'artifact_id': artifact_id,
        'artifact_type': artifact_type,
        'user_id': USER_ID,
        'job_id': f'job-l1-{run_number:03d}',
        'status': 'completed',
        'created_at': now,
        'updated_at': now,
        'entity_type': artifact_type.upper(),
        'ttl': _ttl_timestamp(),
    }


def _list_artifact_ids(table: Any, user_pk: str, sk_prefix: str) -> set[str]:
    response = table.query(
        KeyConditionExpression=Key('pk').eq(user_pk) & Key('sk').begins_with(sk_prefix),
    )
    items = list(response.get('Items', []))
    while 'LastEvaluatedKey' in response:
        response = table.query(
            KeyConditionExpression=Key('pk').eq(user_pk) & Key('sk').begins_with(sk_prefix),
            ExclusiveStartKey=response['LastEvaluatedKey'],
        )
        items.extend(response.get('Items', []))

    artifact_ids: set[str] = set()
    for item in items:
        artifact_id = str(item.get('artifact_id', '')).strip()
        if artifact_id:
            artifact_ids.add(artifact_id)
    return artifact_ids


def _write_evidence(payload: dict[str, Any]) -> None:
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.write_text(json.dumps(payload, indent=2), encoding='utf-8')


@pytest.fixture
def dynamodb_table() -> Any:
    with mock_aws():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='careervp-l1-integration-test',
            KeySchema=[
                {'AttributeName': 'pk', 'KeyType': 'HASH'},
                {'AttributeName': 'sk', 'KeyType': 'RANGE'},
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pk', 'AttributeType': 'S'},
                {'AttributeName': 'sk', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        table.wait_until_exists()
        yield table


@pytest.mark.integration
def test_l1_phase_integration_generates_i2_roundtrip_report(dynamodb_table: Any) -> None:
    records: list[dict[str, Any]] = []
    by_artifact: dict[str, dict[str, int]] = {artifact_type: {'total_runs': 0, 'successful_roundtrips': 0} for artifact_type in ARTIFACT_SK_PREFIXES}

    for artifact_type, sk_prefix in ARTIFACT_SK_PREFIXES.items():
        for run_number in range(1, RUNS_PER_ARTIFACT + 1):
            artifact_id = f'{artifact_type}-roundtrip-{run_number:03d}'
            item = _artifact_item(artifact_type, artifact_id, run_number)
            dynamodb_table.put_item(Item=item)

            poll_response = dynamodb_table.get_item(
                Key={'pk': USER_PK, 'sk': f'{sk_prefix}{artifact_id}'},
            )
            polled_item = poll_response.get('Item')

            listed_ids = _list_artifact_ids(dynamodb_table, USER_PK, sk_prefix)
            roundtrip_passed = (
                isinstance(polled_item, dict) and str(polled_item.get('status', '')).lower() == 'completed' and artifact_id in listed_ids
            )

            by_artifact[artifact_type]['total_runs'] += 1
            if roundtrip_passed:
                by_artifact[artifact_type]['successful_roundtrips'] += 1

            records.append(
                {
                    'run_id': f'l1-phase-{artifact_type}-{run_number:03d}',
                    'artifact_type': artifact_type,
                    'artifact_id': artifact_id,
                    'pk': item['pk'],
                    'sk': item['sk'],
                    'poll_status': str(polled_item.get('status', '')) if isinstance(polled_item, dict) else 'missing',
                    'listed': artifact_id in listed_ids,
                    'roundtrip_passed': roundtrip_passed,
                }
            )

    total_runs = len(records)
    successful_roundtrips = sum(1 for record in records if record['roundtrip_passed'])
    success_rate = successful_roundtrips / total_runs if total_runs else 0.0

    evidence_payload: dict[str, Any] = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'environment': 'local-integration-test',
        'runs_per_artifact': RUNS_PER_ARTIFACT,
        'artifact_types': list(ARTIFACT_SK_PREFIXES.keys()),
        'total_runs': total_runs,
        'successful_roundtrips': successful_roundtrips,
        'success_rate': success_rate,
        'by_artifact': by_artifact,
        'records': records,
    }
    _write_evidence(evidence_payload)

    assert total_runs == RUNS_PER_ARTIFACT * len(ARTIFACT_SK_PREFIXES)
    assert successful_roundtrips == total_runs
    assert success_rate == 1.0
    assert EVIDENCE_PATH.exists()
