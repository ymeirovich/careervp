#!/usr/bin/env python3
"""Validate infra route inventory and optional deployed parity inputs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROUTE_TUPLE_RE = re.compile(
    r'\(\s*"(?P<path>/[^"]+)"\s*,\s*"(?P<method>[A-Z]+)"\s*,\s*self\.[^)]+\)'
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build infra route inventory from api_construct.py and optionally compare "
            "to a deployed inventory JSON file."
        )
    )
    parser.add_argument("--env", required=True, help="Target environment label")
    parser.add_argument(
        "--infra-source",
        required=True,
        help="Path to infra/careervp/api_construct.py",
    )
    parser.add_argument("--out", help="Optional JSON report output path")
    parser.add_argument(
        "--filter-route",
        help='Optional route to verify, format: "METHOD /path"',
    )
    parser.add_argument(
        "--deployed-routes",
        help=(
            "Optional deployed inventory JSON. Supported formats: list of "
            '"METHOD /path" strings, list of {method,path,auth}, or {routes:[...]}'
        ),
    )
    parser.add_argument(
        "--check-auth",
        action="store_true",
        help="When deployed-routes include auth values, verify they are present.",
    )
    return parser.parse_args()


def _load_infra_routes(infra_source: Path) -> set[tuple[str, str]]:
    text = infra_source.read_text(encoding="utf-8")
    return {
        (match.group("method"), match.group("path"))
        for match in ROUTE_TUPLE_RE.finditer(text)
    }


def _normalize_deployed_routes(raw: Any) -> tuple[set[tuple[str, str]], dict[str, str]]:
    auth_map: dict[str, str] = {}
    if isinstance(raw, dict):
        raw = raw.get("routes", [])
    if not isinstance(raw, list):
        raise ValueError("deployed routes must be a list or {routes:[...]}")

    routes: set[tuple[str, str]] = set()
    for entry in raw:
        if isinstance(entry, str):
            parts = entry.strip().split(maxsplit=1)
            if len(parts) != 2:
                raise ValueError(f"invalid deployed route entry: {entry}")
            method, path = parts[0].upper(), parts[1]
            routes.add((method, path))
        elif isinstance(entry, dict):
            method = str(entry.get("method", "")).upper()
            path = str(entry.get("path", ""))
            if not method or not path:
                raise ValueError(f"invalid deployed route dict: {entry}")
            routes.add((method, path))
            auth = entry.get("auth")
            if auth is not None:
                auth_map[f"{method} {path}"] = str(auth)
        else:
            raise ValueError(f"unsupported deployed route entry type: {type(entry)}")
    return routes, auth_map


def main() -> int:
    args = parse_args()
    infra_source = Path(args.infra_source)
    if not infra_source.exists():
        print(f"ERROR: infra source missing: {infra_source}", file=sys.stderr)
        return 2

    infra_routes = _load_infra_routes(infra_source)
    warnings: list[str] = []
    violations: list[str] = []

    filter_route_present: bool | None = None
    if args.filter_route:
        parts = args.filter_route.strip().split(maxsplit=1)
        if len(parts) != 2:
            print(
                f'ERROR: --filter-route must look like "METHOD /path": {args.filter_route}',
                file=sys.stderr,
            )
            return 2
        needle = (parts[0].upper(), parts[1])
        filter_route_present = needle in infra_routes
        if not filter_route_present:
            violations.append(f"infra_missing_filter_route:{needle[0]} {needle[1]}")

    deployed_routes: set[tuple[str, str]] | None = None
    deployed_auth: dict[str, str] = {}
    missing_in_deployed: list[str] = []
    extra_in_deployed: list[str] = []

    if args.deployed_routes:
        deployed_path = Path(args.deployed_routes)
        if not deployed_path.exists():
            print(
                f"ERROR: deployed routes file missing: {deployed_path}", file=sys.stderr
            )
            return 2
        raw = json.loads(deployed_path.read_text(encoding="utf-8"))
        deployed_routes, deployed_auth = _normalize_deployed_routes(raw)

        missing = infra_routes - deployed_routes
        extra = deployed_routes - infra_routes
        missing_in_deployed = sorted(f"{m} {p}" for m, p in missing)
        extra_in_deployed = sorted(f"{m} {p}" for m, p in extra)
        if missing_in_deployed:
            violations.append(f"missing_in_deployed:{len(missing_in_deployed)}")
        if extra_in_deployed:
            violations.append(f"extra_in_deployed:{len(extra_in_deployed)}")
    else:
        warnings.append(
            "deployed routes not provided; only infra inventory checks executed"
        )

    if args.check_auth:
        if not deployed_auth:
            warnings.append(
                "auth check requested, but deployed-routes had no auth data; auth parity skipped"
            )

    report = {
        "env": args.env,
        "infra_source": str(infra_source),
        "infra_route_count": len(infra_routes),
        "filter_route": args.filter_route,
        "filter_route_present_in_infra": filter_route_present,
        "deployed_routes_provided": bool(args.deployed_routes),
        "missing_in_deployed": missing_in_deployed,
        "extra_in_deployed": extra_in_deployed,
        "warnings": warnings,
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
