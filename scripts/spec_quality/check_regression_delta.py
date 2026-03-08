#!/usr/bin/env python3
"""Fail closed when current regression metrics exceed baseline metrics."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


STATUS_CODE_RE = re.compile(r"\b([1-5]\d{2})\b")
EMPTY_ARRAY_RE = re.compile(r":\s*\[\s*\]")
GENERATED_ID_MISSING_RE = re.compile(
    r"generated\s*id\s*missing|missing\s*generated\s*id|after\s*polling\s*window",
    re.IGNORECASE,
)


@dataclass
class Metrics:
    non_2xx_count: int
    empty_array_count: int
    generated_id_missing_count: int


def _flatten_to_text(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True)
    except Exception:
        return str(value)


def _extract_explicit_metrics(obj: Any) -> Metrics | None:
    if not isinstance(obj, dict):
        return None
    keys = {
        "non_2xx_count": [
            "non_2xx_count",
            "non2xx",
            "new_non_2xx_on_changed_endpoints",
        ],
        "empty_array_count": ["empty_array_count", "empty_arrays"],
        "generated_id_missing_count": [
            "generated_id_missing_count",
            "generated_id_missing",
        ],
    }
    extracted: dict[str, int] = {}
    for target, aliases in keys.items():
        for alias in aliases:
            value = obj.get(alias)
            if isinstance(value, int):
                extracted[target] = value
                break
    if len(extracted) == 3:
        return Metrics(**extracted)
    return None


def _extract_metrics(path: Path) -> Metrics:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    try:
        parsed = json.loads(raw)
        explicit = _extract_explicit_metrics(parsed)
        if explicit is not None:
            return explicit
        text = _flatten_to_text(parsed)
    except json.JSONDecodeError:
        text = raw

    status_codes = [int(m.group(1)) for m in STATUS_CODE_RE.finditer(text)]
    non_2xx_count = sum(1 for code in status_codes if code < 200 or code >= 300)
    empty_array_count = len(EMPTY_ARRAY_RE.findall(text))
    generated_id_missing_count = len(GENERATED_ID_MISSING_RE.findall(text))
    return Metrics(
        non_2xx_count=non_2xx_count,
        empty_array_count=empty_array_count,
        generated_id_missing_count=generated_id_missing_count,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare baseline vs current artifacts and fail if current regression "
            "signals increase."
        )
    )
    parser.add_argument("--baseline", required=True, help="Baseline artifact path")
    parser.add_argument("--current", required=True, help="Current artifact path")
    parser.add_argument("--out", help="Optional JSON report output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    baseline_path = Path(args.baseline)
    current_path = Path(args.current)
    if not baseline_path.exists():
        print(f"ERROR: Baseline artifact missing: {baseline_path}", file=sys.stderr)
        return 2
    if not current_path.exists():
        print(f"ERROR: Current artifact missing: {current_path}", file=sys.stderr)
        return 2

    baseline = _extract_metrics(baseline_path)
    current = _extract_metrics(current_path)

    deltas = {
        "non_2xx_count": current.non_2xx_count - baseline.non_2xx_count,
        "empty_array_count": current.empty_array_count - baseline.empty_array_count,
        "generated_id_missing_count": (
            current.generated_id_missing_count - baseline.generated_id_missing_count
        ),
    }
    violations = [name for name, delta in deltas.items() if delta > 0]

    report = {
        "baseline_path": str(baseline_path),
        "current_path": str(current_path),
        "baseline_metrics": asdict(baseline),
        "current_metrics": asdict(current),
        "deltas": deltas,
        "violations": violations,
        "status": "pass" if not violations else "fail",
    }

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    else:
        print(json.dumps(report, indent=2))

    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
