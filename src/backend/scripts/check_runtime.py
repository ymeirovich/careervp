#!/usr/bin/env python3
"""
Verify that build, packaging, and CDK runtimes stay in sync.
"""

from __future__ import annotations

import sys
from pathlib import Path

USAGE = 'usage: check_runtime.py <python_version> <runtime_enum> <arch_enum> <bundling_platform> <api_construct_path>'


def _parse_args(argv: list[str]) -> tuple[str, str, str, str, str] | None:
    if len(argv) != 6:
        return None
    version, runtime, arch, bundling, path = argv[1:6]
    return version, runtime, arch, bundling, path


def _validate_api_construct(
    api_construct_path: str,
    runtime_enum: str,
    arch_enum: str,
    bundling_platform: str,
) -> list[str]:
    errors: list[str] = []
    api_construct = Path(api_construct_path).resolve()
    if not api_construct.exists():
        errors.append(f'{api_construct} is missing; cannot validate runtime')
        return errors

    text = api_construct.read_text()
    checks = (
        (f'Runtime.{runtime_enum}', f'Expected Runtime.{runtime_enum} in {api_construct}'),
        (f'Architecture.{arch_enum}', f'Expected Architecture.{arch_enum} in {api_construct}'),
        (
            bundling_platform,
            f"Expected bundling platform '{bundling_platform}' in {api_construct}",
        ),
    )
    for needle, message in checks:
        if needle not in text:
            errors.append(message)
    return errors


def _validate_pyproject(expected_version: str) -> list[str]:
    errors: list[str] = []
    pyproject = Path('pyproject.toml')
    if not pyproject.exists():
        errors.append('pyproject.toml is missing; cannot validate runtime metadata')
        return errors

    content = pyproject.read_text()
    classifier = f'Programming Language :: Python :: {expected_version}'
    marker = f'requires-python = ">={expected_version}"'
    if classifier not in content:
        errors.append('pyproject classifiers missing expected Python version')
    if marker not in content:
        errors.append('pyproject requires-python mismatch')
    return errors


def _run_checks(
    expected_version: str,
    runtime_enum: str,
    arch_enum: str,
    bundling_platform: str,
    api_construct_path: str,
) -> list[str]:
    errors: list[str] = []
    errors.extend(
        _validate_api_construct(
            api_construct_path,
            runtime_enum,
            arch_enum,
            bundling_platform,
        )
    )
    errors.extend(_validate_pyproject(expected_version))
    return errors


def _report(errors: list[str], expected_version: str) -> int:
    if errors:
        for issue in errors:
            print(f'[runtime-check] {issue}')
        return 1
    print(f'[runtime-check] Python {expected_version} configuration looks consistent.')
    return 0


def main() -> int:
    parsed_args = _parse_args(sys.argv)
    if parsed_args is None:
        print(USAGE, file=sys.stderr)
        return 2

    (
        expected_version,
        expected_runtime_enum,
        expected_arch_enum,
        expected_bundling_platform,
        api_construct_path,
    ) = parsed_args

    errors = _run_checks(
        expected_version,
        expected_runtime_enum,
        expected_arch_enum,
        expected_bundling_platform,
        api_construct_path,
    )
    return _report(errors, expected_version)


if __name__ == '__main__':
    raise SystemExit(main())
