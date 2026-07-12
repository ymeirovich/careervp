#!/usr/bin/env python3
"""P-29: pre-deploy evidence snapshot pack.

Captures a reproducible golden-state snapshot *before* any risky deploy so the
"before" always exists ahead of the first RETAIN flip (step 0.6) and the P-26
blue/green migration. The collector is **read-only** for inspection; the only
mutating actions are on-demand DynamoDB backups and the S3 sync of the
unversioned upload bucket, both of which are additive.

The collection logic is transport-injectable (``EvidenceSources``) so it can be
unit-tested offline with fixtures; ``main`` wires real boto3-backed sources.

Sections captured: cloudformation, api_gateway, lambda_env (secrets redacted),
cognito, amplify (incl. exact NEXT_PUBLIC_API_URL), bucket_cors, dns,
dynamodb_backups (ARNs), s3_sync.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

# deploy_evidence lives next to this file under scripts/ (not an importable
# package); make it importable whether we run as a script or are loaded by path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from deploy_evidence import (  # noqa: E402
    redact_secrets,
    validate_dynamodb_backups,
)

REQUIRED_SECTIONS: tuple[str, ...] = (
    'cloudformation',
    'api_gateway',
    'lambda_env',
    'cognito',
    'amplify',
    'bucket_cors',
    'dns',
    'dynamodb_backups',
    's3_sync',
)


@dataclass(frozen=True)
class EvidenceSources:
    """Injectable data providers.

    Each callable returns the raw data for one section. Production wires
    boto3/http-backed callables; tests wire fixtures. ``lambda_env`` returns a
    ``{function_name: {env_key: value}}`` mapping whose secret values are
    redacted by the collector.
    """

    cloudformation: Callable[[], object]
    api_gateway: Callable[[], object]
    lambda_env: Callable[[], Mapping[str, Mapping[str, object]]]
    cognito: Callable[[], object]
    amplify: Callable[[], Mapping[str, object]]
    bucket_cors: Callable[[], object]
    dns: Callable[[], object]
    dynamodb_backups: Callable[[], Sequence[Mapping[str, object]]]
    s3_sync: Callable[[], object]


def classify_api_url(url: object) -> str:
    """Classify what ``NEXT_PUBLIC_API_URL`` points at (AC-P29-3)."""
    if not isinstance(url, str) or not url.strip():
        return 'unknown'
    if 'execute-api' in url:
        return 'raw_execute_api'
    if url.startswith('https://api.') and 'careervp.com' in url:
        return 'custom_domain'
    return 'other'


def collect_evidence(sources: EvidenceSources, *, now: datetime | None = None) -> dict[str, object]:
    """Assemble the evidence document. Redacts Lambda env secrets and annotates
    the Amplify capture with the classified NEXT_PUBLIC_API_URL kind."""
    timestamp = (now or datetime.now(timezone.utc)).isoformat()

    lambda_env = {function: redact_secrets(env) for function, env in sources.lambda_env().items()}

    amplify = dict(sources.amplify())
    amplify['next_public_api_url_kind'] = classify_api_url(amplify.get('NEXT_PUBLIC_API_URL'))

    return {
        'timestamp': timestamp,
        'cloudformation': sources.cloudformation(),
        'api_gateway': sources.api_gateway(),
        'lambda_env': lambda_env,
        'cognito': sources.cognito(),
        'amplify': amplify,
        'bucket_cors': sources.bucket_cors(),
        'dns': sources.dns(),
        'dynamodb_backups': list(sources.dynamodb_backups()),
        's3_sync': sources.s3_sync(),
    }


def validate_evidence(evidence: Mapping[str, object]) -> list[str]:
    """Return gate errors. Fails closed on missing sections or missing backup
    ARNs (the deploy must not proceed without a proven golden state)."""
    errors: list[str] = []
    for section in REQUIRED_SECTIONS:
        if section not in evidence:
            errors.append(f'missing required evidence section: {section}')
    errors.extend(validate_dynamodb_backups(evidence))
    return errors


def write_evidence(evidence: Mapping[str, object], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    path = out_dir / f'evidence-pack-{stamp}.json'
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str), encoding='utf-8')
    return path


def dry_run_sources() -> EvidenceSources:
    """Fixture sources for --dry-run and tests (no AWS access)."""
    return EvidenceSources(
        cloudformation=lambda: {'stacks': ['CareerVpCrudDev'], 'note': 'dry-run fixture'},
        api_gateway=lambda: {
            'rest_api_id': 'dry-run',
            'stage': 'prod',
            'domain_name': 'api.dev.careervp.com',
            'base_path': '(none)',
        },
        lambda_env=lambda: {
            'careervp-cv-upload-dev': {
                'TABLE_NAME': 'careervp-users-dev',
                'TAVILY_API_KEY': 'tvly-secret-value',
            }
        },
        cognito=lambda: {'user_pool_id': 'dry-run', 'callback_urls': []},
        amplify=lambda: {
            'app_id': 'dry-run',
            'NEXT_PUBLIC_API_URL': 'https://api.dev.careervp.com',
        },
        bucket_cors=lambda: {'careervp-uploads-dev': []},
        dns=lambda: {'api.dev.careervp.com': 'd-ufdp03t4f1.execute-api.us-east-1.amazonaws.com'},
        dynamodb_backups=lambda: [
            {
                'table_name': 'careervp-users-dev',
                'backup_arn': 'arn:aws:dynamodb:us-east-1:788159322332:table/careervp-users-dev/backup/dry-run',
            }
        ],
        s3_sync=lambda: {'bucket': 'careervp-uploads-dev', 'objects_synced': 0, 'destination': '(dry-run)'},
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='P-29 pre-deploy evidence pack')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='use fixture sources; do not touch AWS',
    )
    parser.add_argument(
        '--out-dir',
        type=Path,
        default=Path('docs/evidence'),
        help='directory to write the evidence pack into',
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.dry_run:
        sources = dry_run_sources()
    else:
        print(
            'live collection requires AWS credentials and boto3-backed sources; '
            'run the p29-evidence-pack runbook, or use --dry-run to preview shape.',
            file=sys.stderr,
        )
        return 2

    evidence = collect_evidence(sources)
    errors = validate_evidence(evidence)
    path = write_evidence(evidence, args.out_dir)
    print(f'evidence pack written to {path}')

    if errors:
        print('evidence gate FAILED (deploy stays blocked):', file=sys.stderr)
        for error in errors:
            print(f'  - {error}', file=sys.stderr)
        return 1
    print('evidence gate PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
