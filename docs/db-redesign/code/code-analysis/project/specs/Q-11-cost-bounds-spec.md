---
spec_id: Q-11-COST-BOUNDS
title: "Prompt-cache breakpoints and bounded artifact/Tavily tokens"
status: draft
owner: backend
tier: T2
scope_lock_clause: Q-11
claude_code: {model: sonnet, effort: medium}
codex: {model: gpt-5-codex, reasoning: medium}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - Q-11: Cost Bounds

## Problem Statement

LLM output lengths, prompt-cache breakpoints, and Tavily input must be explicitly bounded so C-2 margin is protected under realistic usage.

## Evidence

- `project-scope-lock.md:181` defines Q-11 as prompt-cache breakpoints, bounded artifact output `max_tokens`, and bounded Tavily input.
- `src/backend/careervp/logic/utils/llm_client.py` owns model invocation and routing behavior.
- `infra/careervp/api_construct.py:484-494` creates `llm-cache-table`, so cache hit rate and breakpoints must be measured rather than assumed.
- `Q-gap-analysis-track-spec.md` defines CR digest token cap behavior that Q-11 should generalize across artifacts.

## Fix Plan

1. Set per-artifact `max_tokens` by task type and enforce in router/client calls.
2. Define prompt-cache breakpoint policy and measure hit rate via Q-10 metrics.
3. Bound Tavily input fields and raw content consistently with Q-09.
4. Add regression tests for max token values and prompt-cache policy.

## RED Tests to Write First

- `test_q11_every_artifact_task_has_max_tokens`: inspect task configs and assert VPR/CV/cover/interview/gap/CR have numeric max token limits.
- `test_q11_router_passes_max_tokens_to_provider`: fake provider call asserts exact `max_tokens` from task config.
- `test_q11_prompt_cache_breakpoints_configured`: assert cache breakpoint policy exists and is attached to eligible prompts.
- `test_q11_tavily_input_bound_matches_q09`: assert Tavily/raw-content settings do not exceed Q-09 limits.

## Acceptance Criteria

**AC-Q11-1** - Given any artifact LLM task, when invoked, then provider call has an explicit bounded `max_tokens`.

**AC-Q11-2** - Given prompt-cache-eligible prompts, when invoked, then breakpoint policy is applied and hit/miss is measured by Q-10.

## Done-when

All RED tests pass; Q-10 metering can report the cost impact; no frontend contract drift.

## Sequencing / Dependencies

Depends on Q-10. Coordinates with Q-09 for Tavily bounds.

