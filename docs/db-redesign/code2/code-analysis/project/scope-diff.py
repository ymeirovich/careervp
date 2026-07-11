#!/usr/bin/env python3
"""
scope-diff.py — CareerVP clause↔spec↔test↔impl drift checker (T-09)

Maps every backlog clause in project-scope-lock.yaml to:
  - spec_exists?         (docs/…/project/specs/*.md has scope_lock_clause: <id>)
  - test_exists?         (src/backend/tests/**/*.py references the clause id)
  - impl_state           (not_started | spec_written | test_written | implemented | verified)

Outputs:
  - UNCOVERED clauses   (no spec)
  - ORPHAN specs        (spec references a clause not in the YAML)
  - STATUS BOARD        (clause → impl_state)
  - SCOPE CREEP specs   (specs with contract_impact but no contract_impact in clause)

Exit code: 0 = clean; 1 = drift found (CI gate).

Usage:
  python3 scope-diff.py [--yaml path] [--specs-dir path] [--tests-dir path]
  python3 scope-diff.py --ci    # strict mode: exit 1 on any issue
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml required — pip install pyyaml", file=sys.stderr)
    sys.exit(2)

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = (
    SCRIPT_DIR.parent.parent.parent.parent.parent
)  # …/project/ is 5 levels deep in careervp/


def find_repo_root(start: Path) -> Path:
    """Walk up to find the repo root (has pyproject.toml or .git)."""
    for p in [start, *start.parents]:
        if (p / ".git").exists():
            return p
    return start


def parse_frontmatter(md_path: Path) -> dict:
    """Extract YAML frontmatter between --- delimiters from a Markdown file."""
    text = md_path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def collect_clause_ids(yaml_path: Path) -> list[str]:
    """Return all backlog clause IDs from the scope-lock YAML."""
    with open(yaml_path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return [entry["id"] for entry in doc.get("backlog", [])]


def collect_specs(specs_dir: Path) -> dict[str, dict]:
    """
    Return {clause_id: {file, spec_id, status, contract_impact, tooling_ok}} for every spec.
    Handles both single and list-valued scope_lock_clause.
    """
    result: dict[str, dict] = {}
    if not specs_dir.exists():
        return result
    for md in specs_dir.glob("*.md"):
        fm = parse_frontmatter(md)
        clause_field = fm.get("scope_lock_clause")
        if clause_field is None:
            continue
        clauses = (
            [clause_field] if isinstance(clause_field, str) else list(clause_field)
        )
        for clause_id in clauses:
            # For multi-clause specs, check tooling entry exists
            tooling_ok = True
            if isinstance(fm.get("scope_lock_clause"), list):
                tooling = fm.get("tooling", {})
                tooling_ok = clause_id in tooling
            result[str(clause_id)] = {
                "file": md.name,
                "spec_id": fm.get("spec_id", ""),
                "status": fm.get("status", "draft"),
                "contract_impact": fm.get("contract_impact", False),
                "tooling_ok": tooling_ok,
                "multi_clause": isinstance(fm.get("scope_lock_clause"), list),
            }
    return result


def collect_test_references(tests_dir: Path) -> dict[str, list[str]]:
    """
    Scan all .py files under tests_dir for clause ID references.
    Returns {clause_id: [file_path, ...]}
    """
    result: dict[str, list[str]] = {}
    if not tests_dir.exists():
        return result
    # Match patterns like scope_lock_clause='P-27', # P-27, "Q-02", etc.
    clause_pattern = re.compile(r"\b([PDQTFX]-\d+[a-z]?)\b")
    for py in tests_dir.rglob("*.py"):
        try:
            text = py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in clause_pattern.finditer(text):
            cid = m.group(1)
            result.setdefault(cid, [])
            rel = str(py)
            if rel not in result[cid]:
                result[cid].append(rel)
    return result


def determine_impl_state(
    clause_id: str,
    spec_map: dict[str, dict],
    test_map: dict[str, list[str]],
    impl_states_from_yaml: dict[str, str],
) -> str:
    has_spec = clause_id in spec_map
    has_test = clause_id in test_map and len(test_map[clause_id]) > 0
    yaml_state = impl_states_from_yaml.get(clause_id)
    if yaml_state in ("implemented", "verified"):
        return yaml_state
    if has_test:
        return "test_written"
    if has_spec:
        return "spec_written"
    return "not_started"


def load_yaml_impl_states(yaml_path: Path) -> dict[str, str]:
    with open(yaml_path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    states: dict[str, str] = {}
    for entry in doc.get("backlog", []):
        if "impl_state" in entry:
            states[entry["id"]] = entry["impl_state"]
    return states


def main() -> int:
    parser = argparse.ArgumentParser(description="CareerVP scope-diff drift checker")
    parser.add_argument("--yaml", default=str(SCRIPT_DIR / "project-scope-lock.yaml"))
    parser.add_argument("--specs-dir", default=str(SCRIPT_DIR / "specs"))
    parser.add_argument(
        "--tests-dir", help="Path to backend tests dir (auto-detected if omitted)"
    )
    parser.add_argument(
        "--ci", action="store_true", help="Exit 1 on any drift (CI mode)"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output JSON instead of text"
    )
    args = parser.parse_args()

    yaml_path = Path(args.yaml)
    specs_dir = Path(args.specs_dir)

    # Auto-detect tests dir
    if args.tests_dir:
        tests_dir = Path(args.tests_dir)
    else:
        repo_root = find_repo_root(Path(__file__))
        tests_dir = repo_root / "src" / "backend" / "tests"

    if not yaml_path.exists():
        print(f"ERROR: scope-lock YAML not found: {yaml_path}", file=sys.stderr)
        return 2

    # Collect data
    all_clause_ids = collect_clause_ids(yaml_path)
    spec_map = collect_specs(specs_dir)
    test_map = collect_test_references(tests_dir)
    yaml_impl_states = load_yaml_impl_states(yaml_path)

    # Build status board
    board: list[dict] = []
    for cid in all_clause_ids:
        board.append(
            {
                "id": cid,
                "spec": cid in spec_map,
                "spec_file": spec_map.get(cid, {}).get("file", ""),
                "tooling_ok": spec_map.get(cid, {}).get("tooling_ok", True),
                "test": cid in test_map,
                "test_files": test_map.get(cid, []),
                "impl_state": determine_impl_state(
                    cid, spec_map, test_map, yaml_impl_states
                ),
            }
        )

    # Diagnostics
    uncovered = [r for r in board if not r["spec"]]
    orphan_specs = {
        cid: info for cid, info in spec_map.items() if cid not in all_clause_ids
    }
    tooling_errors = [r for r in board if r["spec"] and not r["tooling_ok"]]

    if args.json:
        import json

        print(
            json.dumps(
                {
                    "board": board,
                    "uncovered": [r["id"] for r in uncovered],
                    "orphan_specs": list(orphan_specs.keys()),
                    "tooling_errors": [r["id"] for r in tooling_errors],
                    "summary": {
                        "total_clauses": len(all_clause_ids),
                        "with_spec": len([r for r in board if r["spec"]]),
                        "with_test": len([r for r in board if r["test"]]),
                        "not_started": len(
                            [r for r in board if r["impl_state"] == "not_started"]
                        ),
                        "spec_written": len(
                            [r for r in board if r["impl_state"] == "spec_written"]
                        ),
                        "test_written": len(
                            [r for r in board if r["impl_state"] == "test_written"]
                        ),
                        "implemented": len(
                            [r for r in board if r["impl_state"] == "implemented"]
                        ),
                        "verified": len(
                            [r for r in board if r["impl_state"] == "verified"]
                        ),
                    },
                },
                indent=2,
            )
        )
        return 1 if (args.ci and (uncovered or orphan_specs or tooling_errors)) else 0

    # Text output
    total = len(all_clause_ids)
    n_spec = len([r for r in board if r["spec"]])
    n_test = len([r for r in board if r["test"]])

    print("=" * 70)
    print("CareerVP scope-diff.py — clause↔spec↔test↔impl drift report")
    print("=" * 70)
    print(f"Contract:  {yaml_path}")
    print(f"Specs dir: {specs_dir}")
    print(f"Tests dir: {tests_dir}")
    print()
    print(f"Total clauses: {total}  |  With spec: {n_spec}  |  With test: {n_test}")
    print()

    # Status board
    print("── STATUS BOARD ──────────────────────────────────────────────────")
    state_width = max(len(r["impl_state"]) for r in board) + 2
    for r in board:
        spec_tag = f"[spec:{r['spec_file']}]" if r["spec"] else "[NO SPEC]"
        test_tag = f"[test:{len(r['test_files'])}]" if r["test"] else "[NO TEST]"
        warn = " ⚠️ TOOLING-MISSING" if not r["tooling_ok"] else ""
        print(
            f"  {r['id']:<8}  {r['impl_state']:<{state_width}}  {spec_tag}  {test_tag}{warn}"
        )

    # Uncovered
    if uncovered:
        print()
        print(
            f"── UNCOVERED CLAUSES ({len(uncovered)}) — no spec yet ──────────────────────"
        )
        for r in uncovered:
            print(f"  ❌ {r['id']}")
    else:
        print()
        print("── UNCOVERED CLAUSES — none ✅")

    # Orphan specs
    if orphan_specs:
        print()
        print(
            f"── ORPHAN SPECS ({len(orphan_specs)}) — reference clause not in contract ──"
        )
        for cid, info in orphan_specs.items():
            print(f"  ⚠️  {cid}  ({info['file']})")
    else:
        print()
        print("── ORPHAN SPECS — none ✅")

    # Tooling errors
    if tooling_errors:
        print()
        print(
            f"── TOOLING ERRORS ({len(tooling_errors)}) — multi-clause spec missing tooling entry ──"
        )
        for r in tooling_errors:
            print(f"  ⚠️  {r['id']}  ({r['spec_file']})")

    # Summary
    print()
    print("── SUMMARY ───────────────────────────────────────────────────────")
    for state in (
        "not_started",
        "spec_written",
        "test_written",
        "implemented",
        "verified",
    ):
        count = len([r for r in board if r["impl_state"] == state])
        print(f"  {state:<20}  {count:>3}")

    drift = bool(uncovered or orphan_specs or tooling_errors)
    print()
    if drift:
        print("RESULT: DRIFT DETECTED — see issues above")
    else:
        print("RESULT: CLEAN — no drift detected ✅")

    return 1 if (args.ci and drift) else 0


if __name__ == "__main__":
    sys.exit(main())
