#!/usr/bin/env python3
"""Validate yaml2 closure readiness and evidence freshness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore[import-untyped]
except Exception as exc:  # pragma: no cover
    print(f"ERROR: PyYAML is required: {exc}", file=sys.stderr)
    raise SystemExit(2)


PASS_STATUSES = {"validated", "closed"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check yaml2 specs for closure-ready status and pass evidence references."
        )
    )
    parser.add_argument("--yaml2-dir", required=True, help="Directory with yaml2 specs")
    parser.add_argument(
        "--evidence-dir", required=True, help="Evidence artifact directory"
    )
    parser.add_argument("--out", help="Optional JSON output path")
    return parser.parse_args()


def _glob_for_reference(evidence_dir: Path, reference: str) -> list[Path]:
    pattern = Path(reference).name.replace("<timestamp>", "*")
    return sorted(evidence_dir.glob(pattern))


def main() -> int:
    args = parse_args()
    yaml2_dir = Path(args.yaml2_dir)
    evidence_dir = Path(args.evidence_dir)
    issues: list[str] = []
    spec_summaries: list[dict[str, object]] = []

    if not yaml2_dir.exists():
        print(f"ERROR: yaml2 dir missing: {yaml2_dir}", file=sys.stderr)
        return 2
    if not evidence_dir.exists():
        print(f"ERROR: evidence dir missing: {evidence_dir}", file=sys.stderr)
        return 2

    yaml_files = sorted(yaml2_dir.glob("*.yaml"))
    if not yaml_files:
        issues.append("no yaml2 specs found")

    for file_path in yaml_files:
        try:
            spec = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(f"{file_path.name}: YAML parse error: {exc}")
            continue

        spec_id = str(spec.get("spec_id", file_path.stem))
        status = str(spec.get("status", "")).strip().lower()
        traceability = spec.get("traceability_matrix") or []
        spec_issues: list[str] = []

        if status not in PASS_STATUSES:
            spec_issues.append(
                f"status must be one of {sorted(PASS_STATUSES)}, got '{status or 'missing'}'"
            )

        if not isinstance(traceability, list) or not traceability:
            spec_issues.append("traceability_matrix missing or empty")
        else:
            for item in traceability:
                if not isinstance(item, dict):
                    spec_issues.append("invalid traceability entry")
                    continue
                requirement_id = str(item.get("requirement_id", "")).strip()
                result = str(item.get("result", "")).strip().lower()
                evidence_reference = str(item.get("evidence_reference", "")).strip()
                if not requirement_id:
                    spec_issues.append("traceability item missing requirement_id")
                    continue
                if result != "pass":
                    spec_issues.append(
                        f"{requirement_id}: result is '{result or 'missing'}'"
                    )
                if not evidence_reference:
                    spec_issues.append(f"{requirement_id}: missing evidence_reference")
                    continue
                matches = _glob_for_reference(evidence_dir, evidence_reference)
                if not matches:
                    spec_issues.append(
                        f"{requirement_id}: no artifact match for {Path(evidence_reference).name}"
                    )

        if spec_issues:
            issues.extend(f"{spec_id}: {msg}" for msg in spec_issues)

        spec_summaries.append(
            {
                "file": str(file_path),
                "spec_id": spec_id,
                "status": status,
                "issue_count": len(spec_issues),
            }
        )

    report = {
        "yaml2_dir": str(yaml2_dir),
        "evidence_dir": str(evidence_dir),
        "spec_count": len(yaml_files),
        "spec_summaries": spec_summaries,
        "issues": issues,
        "status": "pass" if not issues else "fail",
    }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    else:
        print(json.dumps(report, indent=2))

    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
