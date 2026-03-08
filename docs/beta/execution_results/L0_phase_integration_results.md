# L0 Phase Integration Results

**Date:** 2026-02-27  
**Branch:** `beta/exec-runbk`  
**Test file:** `tests/integration/test_l0_phase_integration.py`  
**Invariant:** I1  
**Evidence:** `docs/beta/evidence/I1_generators/generator-output-audit.json`

## Re-validation

**Date:** 2026-02-27  
**Branch:** `beta/fix-gaps1`

Command:

```bash
cd src/backend && uv run pytest tests/integration/test_l0_phase_integration.py -v --tb=short -m integration
```

Observed outcome:

- `1 passed`

Evidence re-check:

- `docs/beta/evidence/I1_generators/generator-output-audit.json`
- Record count: `250`
- Template matches (`is_template=true`): `0`
- Environment in evidence rows: `local-integration-test`

## Scope

- Execute all 5 generators (`cover_letter`, `interview_prep`, `gap_analysis`, `cv_tailoring`, `vpr`)
- 50 runs per generator
- Detect template output patterns and persist machine-readable audit evidence

## Result

- Total runs: `250` (`50 x 5`)
- Template matches: `0`
- Evidence file written: `yes`

## Command

```bash
cd src/backend && uv run pytest tests/integration/test_l0_phase_integration.py -v --tb=short -m integration
```

Observed outcome:

- `1 passed`

## Evidence Validation

```bash
jq 'length' docs/beta/evidence/I1_generators/generator-output-audit.json
jq '[.[] | select(.is_template==true)] | length' docs/beta/evidence/I1_generators/generator-output-audit.json
```

Observed outcome:

- Record count: `250`
- Template matches: `0`

## Notes

- Replaced prior scaffold integration test (`assert True`) with executable generator audit.
- Evidence format matches runbook/outline requirements:
  - `generator`
  - `run_id`
  - `is_template`
  - `template_match`
  - `response_excerpt`
  - `environment`
