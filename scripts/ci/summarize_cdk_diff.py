#!/usr/bin/env python3
"""Reduce a full `cdk diff` dump to a PR comment that fits GitHub's size cap.

This app synthesises ~557 resources across 6 stacks, so piping the raw diff
straight into a PR comment -- what this workflow used to do -- exceeded
GitHub's 65,536-character limit on essentially every PR. The *comment* step
then failed while the diff itself had succeeded, which read as "cdk-diff is
broken, keep ignoring it". The full diff is still published verbatim (job
summary + artifact); only the comment is bounded.

Input is `cdk diff`'s human-readable output, not `--json`: the `[+] [~] [-]`
resource markers and the IAM/security-group tables are what a reviewer
actually compares against, and they are absent from the JSON form.

Usage: summarize_cdk_diff.py <diff-file> <summary-md-out> <comment-md-out>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# GitHub rejects an issue comment body over 65,536 characters; Actions
# truncates a step summary over 1 MiB. Leave headroom rather than budgeting to
# the edge, since the header and truncation notice are appended after.
COMMENT_LIMIT = 60_000
SUMMARY_LIMIT = 900_000
EXCERPT_LINES = 200

STACK_RE = re.compile(r"^Stack\s+(\S+)", re.MULTILINE)
ADDED_RE = re.compile(r"^\s*\[\+\]", re.MULTILINE)
MODIFIED_RE = re.compile(r"^\s*\[~\]", re.MULTILINE)
REMOVED_RE = re.compile(r"^\s*\[-\]", re.MULTILINE)
IAM_RE = re.compile(r"IAM (?:Statement|Policy) Changes", re.IGNORECASE)
SG_RE = re.compile(r"Security Group Changes", re.IGNORECASE)


def stack_rows(text: str) -> list[tuple[str, int, int, int]]:
    """Per-stack (name, added, modified, removed)."""
    rows: list[tuple[str, int, int, int]] = []
    # split() yields [preamble, name1, body1, name2, body2, ...]
    chunks = STACK_RE.split(text)
    for i in range(1, len(chunks) - 1, 2):
        name, body = chunks[i], chunks[i + 1]
        rows.append(
            (
                name,
                len(ADDED_RE.findall(body)),
                len(MODIFIED_RE.findall(body)),
                len(REMOVED_RE.findall(body)),
            )
        )
    return rows


def main() -> int:
    diff_path, summary_path, comment_path = (Path(a) for a in sys.argv[1:4])
    body = (
        diff_path.read_text(encoding="utf-8", errors="replace").strip()
        if diff_path.exists()
        else ""
    )

    rows = stack_rows(body)
    added = sum(r[1] for r in rows)
    modified = sum(r[2] for r in rows)
    removed = sum(r[3] for r in rows)
    iam = len(IAM_RE.findall(body))
    sg = len(SG_RE.findall(body))

    lines: list[str] = ["## CDK Diff", ""]
    if not body:
        lines += [
            '`cdk diff` produced no output. Treat this as a failed diff, not as "no changes".',
            "",
        ]
    elif not rows and not (added or modified or removed):
        lines += [
            f"No per-stack resource changes parsed from {len(body):,} characters of output.",
            "",
        ]
    else:
        lines += [
            f"**{added} added · {modified} modified · {removed} removed** "
            f"across {len(rows)} stack(s), from {len(body):,} characters of diff output.",
            "",
        ]
        if removed or modified:
            parts = [
                f"**{n} {label}**"
                for n, label in ((removed, "removed"), (modified, "modified"))
                if n
            ]
            lines += [
                f"> ⚠️ {' and '.join(parts)} resource(s). "
                "A modification can still force replacement -- read the full diff before merging.",
                "",
            ]
        lines += [
            "| Stack | + added | ~ modified | - removed |",
            "|---|---:|---:|---:|",
        ]
        lines += [f"| `{n}` | {a} | {m} | {r} |" for n, a, m, r in rows]
        lines += [""]
        if iam or sg:
            lines += [
                f"**{iam}** IAM statement/policy block(s), **{sg}** security-group block(s). "
                "This summary counts them; it does not judge them -- review by hand.",
                "",
            ]
        lines += [
            f"<details><summary>First {EXCERPT_LINES} lines</summary>",
            "",
            "```",
            *body.splitlines()[:EXCERPT_LINES],
            "```",
            "",
            "</details>",
            "",
        ]
    lines += ["_Full diff: this job's **Summary** tab, and the `cdk-diff` artifact._"]

    comment = "\n".join(lines)
    if len(comment) > COMMENT_LIMIT:
        comment = (
            comment[:COMMENT_LIMIT] + "\n```\n\n_...truncated; see the job summary._"
        )
    comment_path.write_text(comment, encoding="utf-8")

    summary = f"## CDK Diff (full)\n\n```\n{body or '(no output)'}\n```\n"
    if len(summary) > SUMMARY_LIMIT:
        summary = (
            summary[:SUMMARY_LIMIT]
            + "\n```\n\n_...truncated; download the `cdk-diff` artifact._\n"
        )
    summary_path.write_text(summary, encoding="utf-8")

    print(
        f"stacks={len(rows)} added={added} modified={modified} removed={removed} iam={iam} sg={sg}"
    )
    print(f"diff chars={len(body)} comment chars={len(comment)} (cap {COMMENT_LIMIT})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
