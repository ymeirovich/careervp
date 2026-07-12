from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

import scripts.emit_json_schemas as schema_emitter
from scripts.emit_json_schemas import CONTRACT_MODELS, build_schema_bundle, emit_schema_files

# scope-lock: F-01 F-06


def test_oracle_be_schema_regenerates(tmp_path: Path) -> None:
    written = emit_schema_files(tmp_path)

    assert sorted(path.name for path in written) == [f'{schema_name}.json' for schema_name in sorted(CONTRACT_MODELS)]

    committed_dir = Path(__file__).resolve().parents[2] / 'contract' / 'schemas'
    for schema_name in CONTRACT_MODELS:
        regenerated = json.loads((tmp_path / f'{schema_name}.json').read_text(encoding='utf-8'))
        committed = json.loads((committed_dir / f'{schema_name}.json').read_text(encoding='utf-8'))
        assert regenerated == committed, f'{schema_name}.json is stale; run uv run python scripts/emit_json_schemas.py'


def test_oracle_schema_bundle_contains_all_contract_models() -> None:
    bundle = build_schema_bundle()
    vpr_schema = cast(dict[str, Any], bundle['VPRStatusResponse'])

    assert sorted(bundle) == sorted(CONTRACT_MODELS)
    assert vpr_schema['properties']['result']['anyOf'][0]['$ref'].endswith('/VPRStatusResult')
    assert 'CVTailoringRequest' in bundle
    assert 'ErrorResponse' in bundle


def test_oracle_schema_emitter_main_prints_written_paths(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    output_path = tmp_path / 'VPRStatusResponse.json'
    monkeypatch.setattr(schema_emitter, 'emit_schema_files', lambda: [output_path])

    schema_emitter.main()

    assert capsys.readouterr().out == f'{output_path}\n'
