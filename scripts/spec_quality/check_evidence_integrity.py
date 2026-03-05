#!/usr/bin/env python3
"""Validate required evidence fields and references for a RECOVERY spec."""

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify evidence artifacts are present and contain required integrity fields."
        )
    )
    parser.add_argument("--spec", required=True, help="Path to step_*.yaml spec")
    parser.add_argument(
        "--artifacts-dir",
        required=True,
        help="Evidence artifact directory, usually docs/evidence",
    )
    parser.add_argument(
        "--require-deployment-id-for",
        action="append",
        default=[],
        help="Blocking gate names that require deployment_id (e.g., post_deploy)",
    )
    parser.add_argument("--out", help="Optional JSON report output path")
    return parser.parse_args()


def _split_evidence_reference(value: str) -> list[str]:
    # Supports values like: "file-a-<timestamp>.json and file-b-<timestamp>.json"
    parts = [p.strip() for p in value.split(" and ")]
    return [p for p in parts if p]


def _reference_to_glob(reference: str) -> str:
    return Path(reference).name.replace("<timestamp>", "*")


def main() -> int:
    args = parse_args()
    spec_path = Path(args.spec)
    artifacts_dir = Path(args.artifacts_dir)
    required_deployment_gates = set(args.require_deployment_id_for)
    issues: list[str] = []
    checked_files: list[str] = []

    if not spec_path.exists():
        print(f"ERROR: spec missing: {spec_path}", file=sys.stderr)
        return 2
    if not artifacts_dir.exists():
        print(f"ERROR: artifacts dir missing: {artifacts_dir}", file=sys.stderr)
        return 2

    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec_id = str(spec.get("spec_id", "")).strip()
    if not spec_id:
        issues.append("spec missing spec_id")

    traceability = spec.get("traceability_matrix") or []
    if not isinstance(traceability, list) or not traceability:
        issues.append("traceability_matrix missing or empty")

    for item in traceability:
        if not isinstance(item, dict):
            issues.append("invalid traceability entry type")
            continue
        requirement_id = str(item.get("requirement_id", "")).strip()
        blocking_gate = str(item.get("blocking_gate", "")).strip()
        evidence_reference = str(item.get("evidence_reference", "")).strip()
        if not requirement_id:
            issues.append("traceability entry missing requirement_id")
            continue
        if not evidence_reference:
            issues.append(f"{requirement_id}: missing evidence_reference")
            continue

        refs = _split_evidence_reference(evidence_reference)
        if not refs:
            issues.append(f"{requirement_id}: unable to parse evidence_reference")
            continue

        matched_any = False
        for ref in refs:
            glob_pattern = _reference_to_glob(ref)
            matches = sorted(artifacts_dir.glob(glob_pattern))
            if not matches:
                issues.append(f"{requirement_id}: no artifact matches {glob_pattern}")
                continue
            matched_any = True
            for artifact in matches:
                checked_files.append(str(artifact))
                try:
                    payload = json.loads(artifact.read_text(encoding="utf-8"))
                except Exception as exc:
                    issues.append(
                        f"{requirement_id}: invalid JSON artifact {artifact.name}: {exc}"
                    )
                    continue

                required_fields = [
                    "spec_id",
                    "requirement_id",
                    "git_sha",
                    "executed_at_utc",
                ]
                if blocking_gate in required_deployment_gates:
                    required_fields.append("deployment_id")

                missing = [
                    field
                    for field in required_fields
                    if payload.get(field) in (None, "", [])
                ]
                if missing:
                    issues.append(
                        f"{requirement_id}: {artifact.name} missing fields: {', '.join(missing)}"
                    )
                if payload.get("spec_id") and payload.get("spec_id") != spec_id:
                    issues.append(
                        f"{requirement_id}: {artifact.name} spec_id mismatch "
                        f"(expected {spec_id}, got {payload.get('spec_id')})"
                    )
                if (
                    payload.get("requirement_id")
                    and payload.get("requirement_id") != requirement_id
                ):
                    issues.append(
                        f"{requirement_id}: {artifact.name} requirement_id mismatch "
                        f"(got {payload.get('requirement_id')})"
                    )
        if not matched_any:
            # Keep explicit failure when all references were unresolved.
            issues.append(f"{requirement_id}: no evidence artifacts resolved")

    report = {
        "spec": str(spec_path),
        "artifacts_dir": str(artifacts_dir),
        "checked_file_count": len(set(checked_files)),
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
