#!/usr/bin/env python3
"""
CareerVP Naming Convention Validator.

Scans infra/ directory (CDK code) to ensure all AWS resource names follow
the kebab-case naming convention: careervp-{feature}-{resource_type}-{env}

Usage:
    python validate_naming.py [--path INFRA_PATH] [--strict]

Exit codes:
    0 - All validations passed
    1 - Naming violations found
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# =============================================================================
# PATTERNS
# =============================================================================

# Kebab-case pattern: lowercase letters, numbers, and hyphens only
KEBAB_CASE_PATTERN = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')

SLUG_PATTERN = r'(?:[a-z0-9]+(?:-[a-z0-9]+)*)'
ENV_PATTERN = r'(dev|staging|prod)'

RESOURCE_PATTERNS = {
    'lambda': re.compile(rf'^careervp-{SLUG_PATTERN}-lambda-{ENV_PATTERN}$'),
    'table': re.compile(rf'^careervp-{SLUG_PATTERN}-table-{ENV_PATTERN}$'),
    'api': re.compile(rf'^careervp-{SLUG_PATTERN}-api-{ENV_PATTERN}$'),
    'role': re.compile(rf'^careervp-role-{SLUG_PATTERN}-{SLUG_PATTERN}-{ENV_PATTERN}$'),
    'topic': re.compile(rf'^careervp-{SLUG_PATTERN}-topic-{ENV_PATTERN}$'),
    'queue': re.compile(rf'^careervp-{SLUG_PATTERN}-queue-{ENV_PATTERN}$'),
    'bus': re.compile(rf'^careervp-{SLUG_PATTERN}-bus-{ENV_PATTERN}$'),
}

BUCKET_RESOURCE_PATTERN = re.compile(rf'^careervp-{ENV_PATTERN}-{SLUG_PATTERN}-[a-z0-9]{{3,5}}-[a-z0-9]{{4,10}}$')

# CDK Token pattern (auto-generated suffixes to detect)
CDK_TOKEN_PATTERN = re.compile(r'\$\{Token\[.*?\]\}')

# Patterns to find resource name assignments in CDK code
FUNCTION_NAME_PATTERN = re.compile(r'function_name\s*=\s*["\']([^"\']+)["\']')
TABLE_NAME_PATTERN = re.compile(r'table_name\s*=\s*["\']([^"\']+)["\']')
BUCKET_NAME_PATTERN = re.compile(r'bucket_name\s*=\s*["\']([^"\']+)["\']')
ROLE_NAME_PATTERN = re.compile(r'role_name\s*=\s*["\']([^"\']+)["\']')
REST_API_NAME_PATTERN = re.compile(r'rest_api_name\s*=\s*["\']([^"\']+)["\']')
TOPIC_NAME_PATTERN = re.compile(r'topic_name\s*=\s*["\']([^"\']+)["\']')
QUEUE_NAME_PATTERN = re.compile(r'queue_name\s*=\s*["\']([^"\']+)["\']')
BUS_NAME_PATTERN = re.compile(r'event_bus_name\s*=\s*["\']([^"\']+)["\']')

# Pattern to detect Logical IDs (construct IDs in CDK)
CONSTRUCT_ID_PATTERN = re.compile(r'(?:super\(\)|self,)\s*["\']([^"\']+)["\']')


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class ValidationError:
    """Represents a naming convention violation."""

    file_path: Path
    line_number: int
    resource_type: str
    resource_name: str
    message: str

    def __str__(self) -> str:
        return f'{self.file_path}:{self.line_number} - {self.resource_type}: "{self.resource_name}" - {self.message}'


# =============================================================================
# VALIDATORS
# =============================================================================


def is_kebab_case(name: str) -> bool:
    """Check if a string follows kebab-case convention."""
    return bool(KEBAB_CASE_PATTERN.match(name))


def contains_cdk_token(text: str) -> bool:
    """Check if text contains CDK token patterns (auto-generated suffixes)."""
    return bool(CDK_TOKEN_PATTERN.search(text))


def validate_resource_name(
    name: str,
    resource_type: str,
    file_path: Path,
    line_number: int,
    strict: bool = False,
    resource_category: str | None = None,
) -> list[ValidationError]:
    """Validate a single resource name against naming conventions."""
    errors: list[ValidationError] = []

    # Check for CDK tokens (auto-generated suffixes)
    if contains_cdk_token(name):
        errors.append(
            ValidationError(
                file_path=file_path,
                line_number=line_number,
                resource_type=resource_type,
                resource_name=name,
                message='Contains CDK token (auto-generated suffix). Use explicit naming.',
            )
        )
        return errors

    # Skip validation for f-strings or variable references
    if '{' in name or name.startswith('f"') or name.startswith("f'"):
        return errors

    # Check kebab-case
    if not is_kebab_case(name):
        errors.append(
            ValidationError(
                file_path=file_path,
                line_number=line_number,
                resource_type=resource_type,
                resource_name=name,
                message='Does not follow kebab-case convention (lowercase, hyphens only).',
            )
        )

    # In strict mode, also check full CareerVP pattern
    if strict and resource_category:
        pattern = BUCKET_RESOURCE_PATTERN if resource_category == 'bucket' else RESOURCE_PATTERNS.get(resource_category)
        if pattern and not pattern.match(name):
            errors.append(
                ValidationError(
                    file_path=file_path,
                    line_number=line_number,
                    resource_type=resource_type,
                    resource_name=name,
                    message=f'Does not follow the expected pattern for {resource_category} resources.',
                )
            )

    return errors


def validate_logical_id(
    logical_id: str,
    file_path: Path,
    line_number: int,
) -> list[ValidationError]:
    """Validate a CDK Logical ID (construct ID)."""
    errors: list[ValidationError] = []

    # Check for CDK tokens
    if contains_cdk_token(logical_id):
        errors.append(
            ValidationError(
                file_path=file_path,
                line_number=line_number,
                resource_type='LogicalId',
                resource_name=logical_id,
                message='Contains CDK token. Logical IDs should be explicit.',
            )
        )

    # Logical IDs should be PascalCase (no hyphens, no underscores in class-like IDs)
    # But they can contain hyphens if they're composite IDs
    if re.search(r'\$\{|Token\[', logical_id):
        errors.append(
            ValidationError(
                file_path=file_path,
                line_number=line_number,
                resource_type='LogicalId',
                resource_name=logical_id,
                message='Contains token reference. Use explicit construct IDs.',
            )
        )

    return errors


# =============================================================================
# FILE SCANNER
# =============================================================================


def _validate_line(
    line: str,
    file_path: Path,
    line_num: int,
    strict: bool,
) -> list[ValidationError]:
    errors: list[ValidationError] = []

    for match in FUNCTION_NAME_PATTERN.finditer(line):
        name = match.group(1)
        errors.extend(
            validate_resource_name(
                name,
                'Lambda function_name',
                file_path,
                line_num,
                strict,
                resource_category='lambda',
            )
        )

    for match in TABLE_NAME_PATTERN.finditer(line):
        name = match.group(1)
        errors.extend(
            validate_resource_name(
                name,
                'DynamoDB table_name',
                file_path,
                line_num,
                strict,
                resource_category='table',
            )
        )

    for match in BUCKET_NAME_PATTERN.finditer(line):
        name = match.group(1)
        errors.extend(
            validate_resource_name(
                name,
                'S3 bucket_name',
                file_path,
                line_num,
                strict,
                resource_category='bucket',
            )
        )

    for match in ROLE_NAME_PATTERN.finditer(line):
        name = match.group(1)
        errors.extend(
            validate_resource_name(
                name,
                'IAM role_name',
                file_path,
                line_num,
                strict,
                resource_category='role',
            )
        )

    for match in REST_API_NAME_PATTERN.finditer(line):
        name = match.group(1)
        errors.extend(
            validate_resource_name(
                name,
                'API Gateway rest_api_name',
                file_path,
                line_num,
                strict,
                resource_category='api',
            )
        )

    for match in TOPIC_NAME_PATTERN.finditer(line):
        name = match.group(1)
        errors.extend(
            validate_resource_name(
                name,
                'SNS topic_name',
                file_path,
                line_num,
                strict,
                resource_category='topic',
            )
        )

    for match in QUEUE_NAME_PATTERN.finditer(line):
        name = match.group(1)
        errors.extend(
            validate_resource_name(
                name,
                'SQS queue_name',
                file_path,
                line_num,
                strict,
                resource_category='queue',
            )
        )

    for match in BUS_NAME_PATTERN.finditer(line):
        name = match.group(1)
        errors.extend(
            validate_resource_name(
                name,
                'Event bus name',
                file_path,
                line_num,
                strict,
                resource_category='bus',
            )
        )

    for match in CONSTRUCT_ID_PATTERN.finditer(line):
        logical_id = match.group(1)
        errors.extend(validate_logical_id(logical_id, file_path, line_num))

    return errors


def scan_file(file_path: Path, strict: bool = False) -> list[ValidationError]:
    """Scan a Python file for naming convention violations."""
    errors: list[ValidationError] = []

    try:
        content = file_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as e:
        print(f'Warning: Could not read {file_path}: {e}', file=sys.stderr)
        return errors

    lines = content.splitlines()

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        errors.extend(_validate_line(line, file_path, line_num, strict))

    return errors


def scan_directory(infra_path: Path, strict: bool = False) -> list[ValidationError]:
    """Scan all Python files in the infra directory."""
    errors: list[ValidationError] = []

    if not infra_path.exists():
        print(f'Error: Directory not found: {infra_path}', file=sys.stderr)
        sys.exit(1)

    python_files = list(infra_path.rglob('*.py'))

    if not python_files:
        print(f'Warning: No Python files found in {infra_path}', file=sys.stderr)
        return errors

    for file_path in python_files:
        relative_path = str(file_path)
        if (
            '__pycache__' in relative_path
            or '.venv' in relative_path
            or os.sep + 'cdk.out' + os.sep in relative_path
            or os.sep + 'build' + os.sep in relative_path
        ):
            continue
        errors.extend(scan_file(file_path, strict))

    return errors


# =============================================================================
# MAIN
# =============================================================================


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the naming validator."""
    parser = argparse.ArgumentParser(
        description='Validate CareerVP CDK naming conventions.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--path',
        type=Path,
        default=Path(__file__).parent.parent.parent.parent / 'infra',
        help='Path to the infra directory (default: auto-detect)',
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Enable strict mode (enforce full careervp-{feature}-{type}-{env} pattern)',
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show verbose output',
    )

    args = parser.parse_args(argv)

    infra_path: Path = args.path
    if not infra_path.is_absolute():
        infra_path = Path.cwd() / infra_path

    if args.verbose:
        print(f'Scanning: {infra_path}')
        print(f'Strict mode: {args.strict}')

    errors = scan_directory(infra_path, strict=args.strict)

    if errors:
        print(f'\nNaming Convention Violations ({len(errors)} found):\n')
        for error in errors:
            print(f'  {error}')
        print('\nPlease update resource names to follow the kebab-case convention:')
        print('  Format: careervp-{feature}-{resource_type}-{env}')
        print('  Example: careervp-cv-parser-lambda-dev')
        return 1

    if args.verbose:
        print('All naming conventions passed!')
    return 0


if __name__ == '__main__':
    sys.exit(main())
