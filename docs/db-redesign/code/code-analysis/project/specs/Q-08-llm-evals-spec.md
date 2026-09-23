---
spec_id: Q-08-LLM-EVALS
title: "LLM output-quality eval harness and golden dataset"
status: draft
owner: quality
tier: T1
scope_lock_clause: Q-08
claude_code: {model: opus, effort: high}
codex: {model: gpt-5-codex, reasoning: high}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; eval files are written later at IMPLEMENT time."
---

# Spec - Q-08: LLM Evals

## Problem Statement

Model and prompt changes need measured quality gates: promptfoo, golden dataset, deterministic LLM judge, FVS gate, and OWASP LLM red-team. Golden data must avoid raw user CV PII unless a sanitization/consent decision exists.

## Evidence

- `project-scope-lock.md:178` defines Q-08 with promptfoo, golden dataset, LLM judge at temp 0, FVS gate, and OWASP-LLM red-team.
- `src/backend/careervp/logic/fvs_validator.py` implements the Fact Verification System that must gate generated prose.
- `src/backend/careervp/logic/utils/llm_client.py` contains routing/model behavior that Q-03/Q-10 decisions rely on.
- `Q-gap-analysis-track-spec.md` requires a Haiku-vs-Sonnet eval set for Q-03 value measurement.

## Fix Plan

1. Create sanitized golden cases for CV, JD, CR, gap, VPR, cover, and interview outputs.
2. Wire promptfoo with deterministic model settings and LLM-judge temperature 0.
3. Add FVS checks to fail hallucinated immutable facts.
4. Add OWASP LLM prompt-injection red-team cases, coordinating with X-02 defense.
5. Record eval score thresholds and block model/prompt upgrades that regress below threshold.

## RED Tests to Write First

- `test_q08_golden_dataset_has_pii_provenance`: assert every fixture has `source`, `sanitized`, and `consent_or_synthetic` metadata.
- `test_q08_promptfoo_config_uses_temp_zero_judge`: parse config and assert judge temperature is exactly 0.
- `test_q08_fvs_gate_fails_mutated_immutable_fact`: mutate a date/title in output; assert FVS gate fails.
- `test_q08_redteam_prompt_injection_cases_exist`: assert OWASP prompt-injection cases cover CV, JD, and Tavily CR.
- `test_q08_quality_gate_blocks_regression`: fixture lower than threshold fails CI gate.

## Acceptance Criteria

**AC-Q08-1** - Given a prompt/model change, when evals run, then quality, FVS, and red-team gates execute deterministically.

**AC-Q08-2** - Given golden data, when audited, then no raw user CV appears without sanitization/consent metadata.

## Done-when

All RED tests pass; eval harness can run locally/CI; thresholds and dataset provenance are documented.

## Sequencing / Dependencies

Scores Q-03 Sonnet value and X-02 red-team; does not itself implement prompt defenses.

