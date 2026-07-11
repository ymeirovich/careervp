---
spec_id: Q-07-Q-09-KNOWLEDGE-CR-MARGIN
title: "Knowledge-table user_id key and company research margin guard"
status: draft
owner: backend
tier: T1
scope_lock_clause: [Q-07, Q-09]
tooling:
  Q-07: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}
  Q-09: {claude_code: {model: sonnet, effort: medium}, codex: {model: gpt-5-codex, reasoning: medium}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - Q-07/Q-09: Knowledge Table and CR Margin Guard

## Problem Statement

The deployed knowledge table is keyed by `userEmail` and `/knowledge-base` is mis-wired. Company Research also risks sending raw Tavily content into prompts. Q-07 fixes the key/route; Q-09 bounds Tavily input before CR-first multiplies usage.

## Evidence

- `infra/careervp/api_db_construct.py:337-361` defines knowledge table partition key `userEmail` and GSI `knowledgeType`.
- `src/backend/careervp/handlers/knowledge_base_handler.py:26-54` reads the knowledge table and exposes query behavior.
- `infra/careervp/api_construct.py:2934` maps `/knowledge-base` to `company_research_func`, proving the route is currently mis-wired.
- `src/backend/careervp/handlers/company_research_worker_handler.py:27` calls `research_company`; Q-09 must bound Tavily/raw input before persisted CR is reused.
- Scope-lock Q-09 requires truncation and `include_raw_content:false` for ~15k Tavily-token margin risk.

## Fix Plan

1. Recreate/migrate knowledge storage to `user_id`/surrogate key, not `userEmail`.
2. Wire `/knowledge-base` to `knowledge_base_handler` or retire the route explicitly if not used.
3. Add CR fetch options setting `include_raw_content:false`.
4. Bound CR prompt projection with deterministic truncation and real tokenizer from Q-10.
5. Keep Q-05/PFACT keys non-PII and tenant-filtered.

## RED Tests to Write First

- `test_q07_knowledge_table_pk_is_user_id_not_user_email`: synth asserts knowledge table partition key is `user_id` or `pk`, not `userEmail`.
- `test_q07_knowledge_base_route_not_company_research_handler`: synth route map and assert `/knowledge-base` maps to intended handler or is absent by explicit decision.
- `test_q09_tavily_include_raw_content_false`: patch Tavily client and assert search request sets `include_raw_content=False`.
- `test_q09_cr_projection_token_cap_exact`: oversized CR fixture is truncated to the named cap with exact deterministic field-drop order.

## Acceptance Criteria

**AC-Q07-1** - Given knowledge storage, when synthesized and queried, then tenant key is `user_id`-based and no PII email partition key remains.

**AC-Q07-2** - Given `/knowledge-base`, when route map is inspected, then it is correctly wired or explicitly retired.

**AC-Q09-1** - Given Company Research fetch, when Tavily is called, then raw content is not included and prompt projection is token bounded.

## Done-when

All RED tests pass; no frontend contract drift; `cdk diff` zero stateful replacement for infra changes; naming validator passes.

## Sequencing / Dependencies

Q-09 must precede Q-01 CR-first reorder. Q-07 depends on P-24 identity surrogate for durable `user_id`.

