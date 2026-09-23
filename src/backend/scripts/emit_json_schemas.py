from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from careervp.models.api_models import (
    ApplicationHubData,
    AsyncTaskResponse,
    CompanyResearchResultResponse,
    CoverLetterStatusResponse,
    CVTailoringRequest,
    CVTailoringStatusResponse,
    ErrorResponse,
    ExportResponse,
    InterviewPrepPatchResponse,
    InterviewPrepStatusResponse,
    VPRStatusResponse,
)

CONTRACT_MODELS: dict[str, type[BaseModel]] = {
    'ApplicationHubData': ApplicationHubData,
    'AsyncTaskResponse': AsyncTaskResponse,
    'CompanyResearchResult': CompanyResearchResultResponse,
    'CoverLetterStatusResponse': CoverLetterStatusResponse,
    'CVTailoredStatusResponse': CVTailoringStatusResponse,
    'CVTailoringRequest': CVTailoringRequest,
    'ErrorResponse': ErrorResponse,
    'ExportResponse': ExportResponse,
    'InterviewPrepPatchResponse': InterviewPrepPatchResponse,
    'InterviewPrepStatusResponse': InterviewPrepStatusResponse,
    'VPRStatusResponse': VPRStatusResponse,
}

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / 'contract' / 'schemas'


def build_schema_bundle() -> dict[str, dict[str, object]]:
    return {schema_name: model.model_json_schema(ref_template='#/$defs/{model}') for schema_name, model in sorted(CONTRACT_MODELS.items())}


def emit_schema_files(output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for schema_name, schema in build_schema_bundle().items():
        output_path = output_dir / f'{schema_name}.json'
        output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        written.append(output_path)
    return written


def main() -> None:
    for output_path in emit_schema_files():
        print(output_path)


if __name__ == '__main__':
    main()
