#!/usr/bin/env python3
"""Self-check for summarize_cdk_diff.py. Run: python3 scripts/ci/test_summarize_cdk_diff.py

Deliberately dependency-free (no pytest) and living beside the script rather
than under src/backend/tests/, because anything under src/backend/** matches
db-redesign-checks.yml's path filter and would turn a CI-only change into a
CloudFormation deploy of CareerVpCrudDevx. cdk-diff.yml runs this before it
trusts the summarizer.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "summarize_cdk_diff.py"
GITHUB_COMMENT_CAP = 65_536

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name} {detail}")
        failures.append(name)


def run(diff_text: str) -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "diff.txt").write_text(diff_text, encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(d / "diff.txt"),
                str(d / "sum.md"),
                str(d / "com.md"),
            ],
            check=True,
            capture_output=True,
        )
        return (d / "com.md").read_text(encoding="utf-8"), (d / "sum.md").read_text(
            encoding="utf-8"
        )


def oversized_diff() -> str:
    """Mimics this app's real shape: ~557 resources over 6 stacks, well past the cap."""
    lines: list[str] = []
    for stack in range(6):
        lines.append(f"Stack CareerVpCrudDevx/Nested{stack}")
        lines.append("IAM Statement Changes")
        lines.append("Security Group Changes")
        for res in range(95):
            mark = ("[+]", "[~]", "[-]")[res % 3]
            lines.append(
                f"  {mark} AWS::IAM::Policy Resource{stack}_{res} " + "x" * 120
            )
    return "\n".join(lines)


print("summarize_cdk_diff self-check")

# The regression this whole change exists for: the old workflow piped the raw
# diff into the comment and GitHub rejected it with "Body is too long".
big = oversized_diff()
comment, summary = run(big)
check(
    "oversized diff exceeds GitHub cap to begin with",
    len(big) > GITHUB_COMMENT_CAP,
    f"({len(big)} chars)",
)
check(
    "comment fits under GitHub cap",
    len(comment) < GITHUB_COMMENT_CAP,
    f"({len(comment)} chars)",
)
check("full diff preserved in job summary", len(summary) > GITHUB_COMMENT_CAP)
check("per-stack table rendered", comment.count("| `CareerVpCrudDevx/Nested") == 6)
check("destructive changes surfaced", "removed" in comment and "⚠️" in comment)

# An empty diff must not be reported as "no changes" -- that is how a broken
# diff step gets mistaken for a clean one.
comment, _ = run("")
check("empty diff is flagged, not called clean", "failed diff" in comment.lower())
check("empty diff comment stays small", len(comment) < 1000)

# IAM-only change: the shape PR #229 is reviewed against.
iam_only = (
    "Stack CareerVpCrudDevx/CrudFeatures\n"
    "IAM Statement Changes\n"
    "│ + │ ${cvs-table} │ Allow │ dynamodb:Query │\n"
    "Resources\n"
    "[~] AWS::IAM::Policy InterviewPrepWorkerRoleDefaultPolicy\n"
)
comment, _ = run(iam_only)
check("IAM block counted", "IAM statement/policy block" in comment)
# Scope this to the warning line: the headline count legitimately reads
# "0 added - 1 modified - 0 removed", so a whole-comment search would match it.
warning = next((ln for ln in comment.splitlines() if ln.startswith("> ")), "")
check(
    "warning names only the nonzero category",
    warning.count("**") == 2 and "**1 modified**" in warning,
)
check('warning omits the zero "removed" count', "0 removed" not in warning)

print()
if failures:
    print(f"FAILED: {len(failures)} check(s): {', '.join(failures)}")
    raise SystemExit(1)
print("All checks passed.")
