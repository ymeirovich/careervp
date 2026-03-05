#!/usr/bin/env python3
"""Run targeted live smoke assertions for RECOVERY steps."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


CHECKS = [
    (
        "gap_post_persistence",
        "docs/refactor/live_tests/test_05_gap_analysis.py::"
        "TestGapAnalysisEndpoints::test_generate_gap_questions",
    ),
    (
        "cover_letter_status_resolvable",
        "docs/refactor/live_tests/test_07_cover_letter.py::"
        "TestCoverLetterEndpoints::test_get_cover_letter_status",
    ),
    (
        "vpr_list_includes_generated",
        "docs/refactor/live_tests/test_04_vpr.py::TestVPREndpoints::test_list_vprs",
    ),
    (
        "cv_tailoring_delete_not_403",
        "docs/refactor/live_tests/test_06_cv_tailoring.py::"
        "TestCVTailoringEndpoints::test_delete_tailored_cv_roundtrip",
    ),
    (
        "interview_prep_status_resolvable",
        "docs/refactor/live_tests/test_08_interview_prep.py::"
        "TestInterviewPrepEndpoints::test_get_interview_prep_status",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the 5 targeted smoke checks required by RECOVERY_001 and "
            "emit a machine-readable JSON report."
        )
    )
    parser.add_argument(
        "--step", required=True, help="RECOVERY step label, e.g. RECOVERY_002"
    )
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument(
        "--max-seconds",
        type=int,
        default=180,
        help="Maximum total runtime before force-failing (default: 180 seconds)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    started = time.time()
    results: list[dict[str, object]] = []
    failures = 0

    for name, node_id in CHECKS:
        elapsed = time.time() - started
        if elapsed > args.max_seconds:
            failures += 1
            results.append(
                {
                    "name": name,
                    "node_id": node_id,
                    "status": "fail",
                    "exit_code": 124,
                    "reason": f"smoke runtime exceeded {args.max_seconds}s",
                }
            )
            continue

        cmd = [sys.executable, "-m", "pytest", "-q", node_id]
        proc = subprocess.run(
            cmd,
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        ok = proc.returncode == 0
        if not ok:
            failures += 1
        results.append(
            {
                "name": name,
                "node_id": node_id,
                "status": "pass" if ok else "fail",
                "exit_code": proc.returncode,
                "stdout_tail": proc.stdout[-1200:],
                "stderr_tail": proc.stderr[-1200:],
            }
        )

    duration_seconds = round(time.time() - started, 3)
    report = {
        "step": args.step,
        "max_seconds": args.max_seconds,
        "duration_seconds": duration_seconds,
        "assertion_count": len(CHECKS),
        "failure_count": failures,
        "status": "pass" if failures == 0 else "fail",
        "checks": results,
    }

    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failure_count": failures}, indent=2))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
