#!/usr/bin/env python3
"""
CareerVP read-only DynamoDB recon — answers the DB-redesign blocking questions
WITHOUT exposing any credentials or PII.

Emits ONLY structural metadata:
  - declared key schema, GSIs (+ projection), billing mode, PITR, TTL, stream, item count, size
  - from a SMALL sample per table: which known key-conventions appear (the "3-schema drift"),
    and the distinct SK prefixes (structural, e.g. ARTIFACT#VPR#) — never attribute VALUES.

It NEVER writes, NEVER prints item values, NEVER prints attribute values.
Safe to paste the output back into the chat.

USAGE (in YOUR terminal, where your AWS creds live):
    # option A: a named profile you control
    AWS_PROFILE=your-dev-profile python3 recon.py --env dev --region us-east-1

    # option B: SSO
    aws sso login --profile your-dev-profile
    AWS_PROFILE=your-dev-profile python3 recon.py --env dev --region us-east-1

Use READ-ONLY, DEV creds (not prod). Minimal IAM: dynamodb:ListTables,
DescribeTable, DescribeContinuousBackups, DescribeTimeToLive, Scan (limited).
"""

import argparse, json, sys
from collections import Counter

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    sys.exit(
        "boto3 not found. Run inside the backend env (uv run / the venv) or: pip install boto3"
    )

# Known key-convention signatures to detect the multi-schema drift (attribute NAMES only).
KEY_CONVENTIONS = {
    "pk/sk": ("pk", "sk"),
    "userId/cvId": ("userId", "cvId"),
    "userId/applicationId": ("userId", "applicationId"),
    "userId/questionId": ("userId", "questionId"),
    "applicationId/artifactId": ("applicationId", "artifactId"),
    "job_id": ("job_id",),
    "userEmail/knowledgeType": ("userEmail", "knowledgeType"),
    "id": ("id",),
    "cacheKey": ("cacheKey",),
    "cache_key": ("cache_key",),
}
SAMPLE_LIMIT = 40  # per table; small, read-only


def analyze_table(ddb, name):
    out = {"table": name}
    try:
        d = ddb.describe_table(TableName=name)["Table"]
    except ClientError as e:
        return {"table": name, "error": str(e.response["Error"]["Code"])}
    out["key_schema"] = [
        f"{k['AttributeName']}({k['KeyType']})" for k in d.get("KeySchema", [])
    ]
    out["billing"] = d.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED?")
    out["item_count"] = d.get("ItemCount")  # approximate, free (no scan)
    out["size_bytes"] = d.get("TableSizeBytes")
    out["stream"] = d.get("StreamSpecification", {}).get("StreamViewType", None)
    out["gsis"] = [
        {
            "name": g["IndexName"],
            "keys": [f"{k['AttributeName']}({k['KeyType']})" for k in g["KeySchema"]],
            "projection": g["Projection"]["ProjectionType"],
        }
        for g in d.get("GlobalSecondaryIndexes", [])
    ]
    # PITR
    try:
        pitr = ddb.describe_continuous_backups(TableName=name)
        out["pitr"] = pitr["ContinuousBackupsDescription"][
            "PointInTimeRecoveryDescription"
        ]["PointInTimeRecoveryStatus"]
    except ClientError:
        out["pitr"] = "unknown"
    # TTL
    try:
        ttl = ddb.describe_time_to_live(TableName=name)["TimeToLiveDescription"]
        out["ttl"] = {
            "status": ttl.get("TimeToLiveStatus"),
            "attr": ttl.get("AttributeName"),
        }
    except ClientError:
        out["ttl"] = "unknown"

    # Sampled read — detect key-convention drift + SK prefixes. NAMES/PREFIXES ONLY.
    conv_counter = Counter()
    sk_prefixes = Counter()
    sampled = 0
    try:
        resp = ddb.scan(TableName=name, Limit=SAMPLE_LIMIT)
        for item in resp.get("Items", []):
            sampled += 1
            attrs = set(item.keys())
            for label, sig in KEY_CONVENTIONS.items():
                if all(a in attrs for a in sig):
                    conv_counter[label] += 1
            # SK prefix is structural (e.g. ARTIFACT#VPR#, CV#, SUBSCRIPTION#) — not PII.
            for skname in ("sk", "SK"):
                if skname in item and "S" in item[skname]:
                    val = item[skname]["S"]
                    prefix = val.split("#")[0] + "#" if "#" in val else val[:12]
                    sk_prefixes[prefix] += 1
    except ClientError as e:
        out["sample_error"] = e.response["Error"]["Code"]
    out["sampled_items"] = sampled
    out["key_conventions_seen"] = dict(conv_counter)
    out["sk_prefixes_seen"] = dict(sk_prefixes.most_common(15))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", default="dev")
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--prefix", default="careervp-")
    args = ap.parse_args()

    ddb = boto3.client("dynamodb", region_name=args.region)
    names = []
    paginator = ddb.get_paginator("list_tables")
    for page in paginator.paginate():
        names += page["TableNames"]
    target = sorted(
        n for n in names if n.startswith(args.prefix) and n.endswith(f"-{args.env}")
    )
    if not target:
        target = sorted(n for n in names if args.prefix in n and args.env in n)

    report = {
        "env": args.env,
        "region": args.region,
        "tables": [analyze_table(ddb, n) for n in target],
    }
    print("\n===== CAREERVP DYNAMODB RECON (safe to paste back) =====\n")
    print(json.dumps(report, indent=2, default=str))
    print("\n===== END =====")


if __name__ == "__main__":
    main()
