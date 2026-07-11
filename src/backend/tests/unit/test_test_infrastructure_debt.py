"""Test-infrastructure debt checks for db-redesign Wave 0 step 0.5.

Scope-lock clauses:
- T-01: branch coverage must be enabled.
- T-02: dependency resolver/company-research mocks must be opt-in and real key
  schemas must be available via moto fixtures.
- T-03: differentiated coverage gates must be wired.
"""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Any

import pytest

from scripts.check_coverage_gates import COVERAGE_GATES

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_t01_branch_coverage_is_enabled_in_coverage_config() -> None:
    coverage_config_path = BACKEND_ROOT / '.coveragerc'
    parser = configparser.ConfigParser()

    assert coverage_config_path.exists()
    parser.read(coverage_config_path)

    assert parser.getboolean('run', 'branch') is True


def test_t02_dependency_mocks_are_opt_in(pytestconfig: pytest.Config) -> None:
    fixture_manager = pytestconfig.pluginmanager.get_plugin('funcmanage')
    assert fixture_manager is not None
    # _arg2fixturedefs is the fixture registry populated during collection; it
    # does not require a collection node (unlike getfixturedefs on pytest 8+).
    registry = fixture_manager._arg2fixturedefs
    artifact_fixture = registry.get('mock_artifact_dependency_resolver')
    company_fixture = registry.get('mock_company_research_load')

    assert artifact_fixture is not None
    assert company_fixture is not None
    assert artifact_fixture[-1]._autouse is False
    assert company_fixture[-1]._autouse is False


def test_t02_moto_real_key_schema_fixtures(moto_applications_table: Any, moto_artifacts_table: Any, moto_cvs_table: Any) -> None:
    assert moto_artifacts_table.key_schema == [
        {'AttributeName': 'applicationId', 'KeyType': 'HASH'},
        {'AttributeName': 'artifactId', 'KeyType': 'RANGE'},
    ]
    assert moto_applications_table.key_schema == [
        {'AttributeName': 'userId', 'KeyType': 'HASH'},
        {'AttributeName': 'applicationId', 'KeyType': 'RANGE'},
    ]
    assert moto_cvs_table.key_schema == [
        {'AttributeName': 'userId', 'KeyType': 'HASH'},
        {'AttributeName': 'cvId', 'KeyType': 'RANGE'},
    ]


def test_t03_differentiated_coverage_gates_are_exact() -> None:
    assert COVERAGE_GATES['core'].line_percent == pytest.approx(85.0)
    assert COVERAGE_GATES['core'].branch_percent == pytest.approx(80.0)
    assert COVERAGE_GATES['supporting'].line_percent == pytest.approx(78.0)
    assert COVERAGE_GATES['supporting'].branch_percent == pytest.approx(70.0)
    assert COVERAGE_GATES['overall'].line_percent == pytest.approx(80.0)
    assert COVERAGE_GATES['overall'].branch_percent == pytest.approx(70.0)
