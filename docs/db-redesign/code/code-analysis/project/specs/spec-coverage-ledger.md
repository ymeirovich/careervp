---
spec_id: T-SPEC-COVERAGE-LEDGER
title: "Spec coverage ledger, CI gates, and scope-diff drift checker"
status: draft
owner: quality
tier: T1
scope_lock_clause: [T-06, T-07, T-09]
tooling:
  T-06: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
  T-07: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}
  T-09: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest/vitest files are written later at IMPLEMENT time."
---

# Spec - T-06/T-07/T-09: Coverage Ledger and Drift Nets

## Problem Statement

Step 0.4 only works if authored specs remain traceable to the immutable scope lock. T-06 owns the spec-coverage ledger, T-07 owns the CI gate set, and T-09 owns `scope-diff.py` drift detection through `scope_lock_clause` frontmatter.

## Evidence

- `docs/db-redesign/code/code-analysis/project/redesign-execution-plan.md:133` defines Wave 0 step 0.4 as scaffolding all spec files.
- `docs/db-redesign/code/code-analysis/project/redesign-execution-plan.md:213-225` lists the still-TO-AUTHOR specs and `scope-diff.py` traceability behavior.
- `docs/db-redesign/code/code-analysis/project/scope-diff.py:1-22` documents its clause/spec/test/impl drift purpose and outputs.
- `docs/db-redesign/code/code-analysis/project/scope-diff.py:48-82` parses YAML frontmatter and handles list-valued `scope_lock_clause`.
- `docs/db-redesign/code/code-analysis/project/project-scope-lock.yaml` defines `spec_test_acceptance` and `spec_frontmatter_forms`.

## Fix Plan

1. Maintain this ledger as the single list of authored spec files, grouped clauses, and implementation state references.
2. Ensure every authored spec carries valid YAML frontmatter and every list-valued `scope_lock_clause` has a per-clause `tooling` entry.
3. Wire CI gates for ruff, mypy --strict, pytest, cdk synth/resource count, Checkov, Bandit, pip-audit, CodeQL, scope-diff, and the frontend oracle.
4. Extend `scope-diff.py` only as needed to distinguish intentionally inline/mechanical clauses from missing spec coverage, without weakening drift detection.
5. Do not edit `project-scope-lock.md` or `.yaml` from agent sessions.

## RED Tests to Write First

- `test_t09_scope_diff_accepts_list_valued_scope_lock_clause`: fixture spec with `[A, B]` and both tooling entries maps both clauses.
- `test_t09_scope_diff_rejects_missing_tooling_entry`: fixture spec with list-valued clauses but missing one tooling entry reports tooling error.
- `test_t06_ledger_has_row_for_every_to_author_spec`: compare execution-plan TO-AUTHOR list to specs dir; assert each target file exists or is explicitly mechanical-inline.
- `test_t07_ci_gate_list_contains_required_eight`: parse workflow config and assert ruff, mypy, pytest, cdk synth, Checkov, Bandit, pip-audit, and CodeQL are present.
- `test_t09_contract_files_write_protected_in_ci`: CI fixture changing scope-lock files without human approval trailer fails.

## Acceptance Criteria

**AC-T06-1** - Given the TO-AUTHOR list, when step 0.4 completes, then every listed spec file exists or is explicitly reported as mechanical-inline/future-wave.

**AC-T07-1** - Given CI config, when gates are inspected, then the eight required gates plus scope-diff and oracle are present.

**AC-T09-1** - Given any spec frontmatter, when `scope-diff.py` runs, then valid clauses are covered, orphan clauses are reported, and missing multi-clause tooling fails.

## Done-when

All RED tests pass at implementation time; `python docs/db-redesign/code/code-analysis/project/scope-diff.py` runs after fan-out and the uncovered list is understood, not ignored.

## Sequencing / Dependencies

Wave 0 net. This spec does not authorize editing the scope-lock twins.

