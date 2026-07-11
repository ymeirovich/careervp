#!/usr/bin/env python3
"""P-28 Sub-clause E — scope-lock contract self-protection CI check (§0.3).

The two contract twins — `project-scope-lock.md` and `project-scope-lock.yaml` — are
write-protected from agent/orchestrator sessions. An agent may PROPOSE an amendment but
may not silently edit the contract: every downstream net (scope-diff.py, the oracle, wave
gates) audits code AGAINST this contract, so a silent contract edit would turn drift
DETECTION into drift ENFORCEMENT.

Any diff touching either twin must satisfy ALL of:
  1. Twin-sync      — both files changed together.
  2. Version bump   — `meta.version` in the YAML strictly increases.
  3. Change-log row — the YAML `changelog:` block gains a new entry.
  4. Approval trailer — the commit message carries `Scope-Lock-Approved-By: <name> <date>`.

A diff touching neither twin is a no-op pass.

CLI (CI mode): compares HEAD against a base ref via git and exits 1 on violation.
    python3 check_scope_lock_integrity.py --base origin/main
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field

import yaml  # type: ignore[import-untyped]

MD_SUFFIX = "project-scope-lock.md"
YAML_SUFFIX = "project-scope-lock.yaml"
APPROVAL_TRAILER = re.compile(r"Scope-Lock-Approved-By:\s*\S+", re.IGNORECASE)


@dataclass
class Result:
    ok: bool
    reasons: list[str] = field(default_factory=list)


def _touches(changed_files: list[str], suffix: str) -> bool:
    return any(f.replace("\\", "/").endswith(suffix) for f in changed_files)


def _parse_version(text: str | None) -> tuple[int, ...] | None:
    if not text:
        return None
    try:
        doc = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return None
    version = (doc.get("meta") or {}).get("version")
    if version is None:
        return None
    try:
        return tuple(int(p) for p in str(version).split("."))
    except ValueError:
        return None


def _changelog_len(text: str | None) -> int:
    if not text:
        return 0
    try:
        doc = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return 0
    changelog = doc.get("changelog")
    return len(changelog) if isinstance(changelog, list) else 0


def check_integrity(
    changed_files: list[str],
    yaml_before: str | None,
    yaml_after: str | None,
    commit_message: str,
) -> Result:
    """Pure, importable core of the guard. See module docstring for the rules."""
    md_touched = _touches(changed_files, MD_SUFFIX)
    yaml_touched = _touches(changed_files, YAML_SUFFIX)

    # No-op: a diff that touches neither contract twin passes immediately.
    if not md_touched and not yaml_touched:
        return Result(ok=True)

    reasons: list[str] = []

    # 1. Twin-sync.
    if md_touched != yaml_touched:
        missing = YAML_SUFFIX if md_touched else MD_SUFFIX
        reasons.append(
            f"twin-sync: both twins must change together (missing {missing})"
        )

    # 2. Version bump.
    before_v = _parse_version(yaml_before)
    after_v = _parse_version(yaml_after)
    if after_v is None:
        reasons.append("version: could not read meta.version from the new YAML")
    elif before_v is not None and not (after_v > before_v):
        reasons.append(
            f"version: meta.version must strictly increase ({before_v} -> {after_v})"
        )

    # 3. Change-log row.
    if _changelog_len(yaml_after) <= _changelog_len(yaml_before):
        reasons.append("changelog: the YAML changelog must gain a new §12 entry")

    # 4. Approval trailer.
    if not APPROVAL_TRAILER.search(commit_message or ""):
        reasons.append(
            "approval: commit message must carry a `Scope-Lock-Approved-By: <name> <date>` trailer"
        )

    return Result(ok=not reasons, reasons=reasons)


def _git(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    ).stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P-28 scope-lock integrity guard")
    parser.add_argument(
        "--base", default="origin/main", help="Base ref to diff against"
    )
    parser.add_argument("--head", default="HEAD", help="Head ref")
    args = parser.parse_args(argv)

    merge_base = _git(["merge-base", args.base, args.head]).strip() or args.base
    changed = [
        line
        for line in _git(
            ["diff", "--name-only", f"{merge_base}..{args.head}"]
        ).splitlines()
        if line.strip()
    ]

    def show(ref: str, suffix: str) -> str | None:
        path = next(
            (f for f in changed if f.endswith(suffix)),
            None,
        )
        if path is None:
            # File unchanged in this diff — read its current content for version/changelog.
            path = next(
                (
                    line
                    for line in _git(["ls-files", f"*{suffix}"]).splitlines()
                    if line.strip()
                ),
                None,
            )
            if path is None:
                return None
        out = _git(["show", f"{ref}:{path}"])
        return out or None

    yaml_before = show(merge_base, YAML_SUFFIX)
    yaml_after = show(args.head, YAML_SUFFIX)
    commit_message = _git(["log", "-1", "--format=%B", args.head])

    result = check_integrity(changed, yaml_before, yaml_after, commit_message)
    if result.ok:
        print("scope-lock integrity: OK")
        return 0
    print("scope-lock integrity: FAIL", file=sys.stderr)
    for reason in result.reasons:
        print(f"  - {reason}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
