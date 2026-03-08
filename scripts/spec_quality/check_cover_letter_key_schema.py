#!/usr/bin/env python3
"""Audit cover-letter artifact key schema from an optional exported sample file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Produce a key-schema audit report. In offline mode, accepts --input as a "
            "JSON list or NDJSON export."
        )
    )
    parser.add_argument("--table", required=True, help="Artifacts table name")
    parser.add_argument(
        "--user-sample",
        type=int,
        default=20,
        help="Requested sample size for audit reporting metadata",
    )
    parser.add_argument("--out", required=True, help="Output JSON report path")
    parser.add_argument(
        "--input",
        help=(
            "Optional local export file (JSON list or NDJSON). "
            "If omitted, report is marked manual_scan_required."
        ),
    )
    return parser.parse_args()


def _parse_input_file(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return []
    try:
        value = json.loads(text)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    except json.JSONDecodeError:
        pass

    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid NDJSON line: {exc}") from exc
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _classify(row: dict[str, Any]) -> str:
    has_legacy = "pk" in row and "sk" in row
    has_canonical = "applicationId" in row and "artifactId" in row
    if has_legacy and has_canonical:
        return "dual"
    if has_canonical:
        return "canonical_only"
    if has_legacy:
        return "legacy_only"
    return "unknown"


def main() -> int:
    args = parse_args()
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "table": args.table,
        "user_sample": args.user_sample,
        "status": "pass",
        "mode": "manual_scan_required",
        "counts": {
            "canonical_only": 0,
            "legacy_only": 0,
            "dual": 0,
            "unknown": 0,
            "total": 0,
        },
    }

    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"ERROR: input file missing: {input_path}", file=sys.stderr)
            return 2
        rows = _parse_input_file(input_path)
        for row in rows:
            key = _classify(row)
            report["counts"][key] += 1
            report["counts"]["total"] += 1
        report["mode"] = "local_input_audit"
        report["legacy_only_records"] = report["counts"]["legacy_only"]
        report["status"] = "pass" if report["counts"]["legacy_only"] == 0 else "fail"

    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
