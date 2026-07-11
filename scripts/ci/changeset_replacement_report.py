#!/usr/bin/env python3
"""P-28 Sub-clause D — DescribeChangeSet Replacement report + auto-fail gate.

Parses the JSON output of `aws cloudformation describe-change-set` and produces a
per-resource Replacement report. AUTO-FAILS (exit 1) when CloudFormation's own
`Replacement` computation is `True` for any protected stateful resource type
(RestApi / DynamoDB Table / S3 Bucket / Cognito UserPool). This is the approval artifact
the human reviewer reads BEFORE approving the human-gated execute-change-set job.

CFN's `Replacement` field is stronger than a `cdk diff` string heuristic — it is the
authoritative determination of whether an update recreates (and thus can data-loss) a
resource.

Usage:
    python3 changeset_replacement_report.py --changeset /tmp/changeset.json
    aws cloudformation describe-change-set ... | python3 changeset_replacement_report.py -
Exit code: 0 = safe; 1 = protected replacement detected (gate fails).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

PROTECTED_TYPES = frozenset(
    {
        "AWS::ApiGateway::RestApi",
        "AWS::DynamoDB::Table",
        "AWS::S3::Bucket",
        "AWS::Cognito::UserPool",
    }
)


def build_report(changeset: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Return (report, auto_fail) for a DescribeChangeSet response dict."""
    report: list[dict[str, Any]] = []
    auto_fail = False
    for change in changeset.get("Changes", []):
        rc = change.get("ResourceChange", {})
        rtype = rc.get("ResourceType", "")
        replacement = rc.get("Replacement", "False")
        entry = {
            "LogicalId": rc.get("LogicalResourceId", ""),
            "Type": rtype,
            "Action": rc.get("Action"),
            "Replacement": replacement,
        }
        if replacement == "True" and rtype in PROTECTED_TYPES:
            entry["AUTO_FAIL"] = True
            auto_fail = True
        report.append(entry)
    return {"changes": report, "auto_fail": auto_fail}, auto_fail


def _render_markdown(report: dict[str, Any]) -> str:
    lines = ["## CloudFormation Change-Set Replacement Report (P-28)", ""]
    lines.append("| Logical Id | Type | Action | Replacement | Gate |")
    lines.append("|---|---|---|---|---|")
    for e in report["changes"]:
        gate = "🚫 AUTO-FAIL" if e.get("AUTO_FAIL") else "ok"
        lines.append(
            f"| {e['LogicalId']} | {e['Type']} | {e['Action']} | {e['Replacement']} | {gate} |"
        )
    lines.append("")
    if report["auto_fail"]:
        lines.append(
            "**AUTO-FAIL:** `Replacement:True` on a protected stateful type "
            "(RestApi / DynamoDB Table / S3 Bucket / Cognito UserPool). "
            "The execute-change-set job MUST NOT run."
        )
    else:
        lines.append("No protected-type replacement detected.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P-28 change-set Replacement report")
    parser.add_argument(
        "--changeset",
        "-c",
        default="-",
        help="Path to describe-change-set JSON, or '-' for stdin",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Also append a Markdown table to $GITHUB_STEP_SUMMARY if set",
    )
    args = parser.parse_args(argv)

    raw = sys.stdin.read() if args.changeset == "-" else open(args.changeset).read()
    changeset = json.loads(raw)
    report, auto_fail = build_report(changeset)

    print(json.dumps(report, indent=2))

    if args.summary:
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with open(summary_path, "a", encoding="utf-8") as fh:
                fh.write(_render_markdown(report))

    if auto_fail:
        print(
            "AUTO-FAIL: Replacement:True detected for a protected resource type.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
