---
spec_id: Q-05-KNOWLEDGE-BASE
title: "Cross-application knowledge base MVP"
status: draft
owner: backend
tier: T1
scope_lock_clause: Q-05
claude_code: {model: opus, effort: high}
codex: {model: gpt-5-codex, reasoning: high}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - Q-05: Knowledge Base MVP

## Problem Statement

CareerVP should reuse prior validated application knowledge without vectors in the MVP: distill prior gap answers, validated CV bullets, and VPR differentiators into per-user `PFACT` items, recall them as a rolling digest plus top-K under a strict 1,200-token cap, and keep all recall tenant-filtered.

## Evidence

- `project-scope-lock.md:175` defines Q-05 as `PFACT` items in per-user core, rolling digest + top-K under 1,200 tokens, DynamoDB brute-force rank, tenant-filtered, non-PII key.
- `infra/careervp/api_db_construct.py:337-361` creates a knowledge table currently keyed by `userEmail`, which Q-07/D-M5 must replace before durable Q-05 storage.
- `src/backend/careervp/handlers/knowledge_base_handler.py:24-54` routes knowledge base requests and reads `KNOWLEDGE_TABLE_NAME`.
- `src/backend/careervp/handlers/gap_handler.py` is the consumer that Q-gap spec says will receive `recurring_themes` and `previous_gap_responses`.

## Fix Plan

1. Define `PFACT` schema with tenant key `USER#{user_id}` and non-PII sort keys.
2. Distill only verified source material: prior gap answers, validated CV bullets, and VPR differentiators.
3. Implement brute-force DynamoDB recall for MVP with tenant filter and deterministic rank.
4. Build digest under `KB_RECALL_TOKEN_CAP = 1200` using the real tokenizer from Q-10.
5. Feed Q-gap's `recurring_themes` and `previous_gap_responses` slots without changing endpoint shapes.

## RED Tests to Write First

- `test_q05_pfact_items_are_user_scoped_non_pii`: seed PFACT; assert pk starts `USER#` and no email appears in key attributes.
- `test_q05_recall_filters_by_user`: seed two users; assert user A recall returns zero user B facts.
- `test_q05_recall_digest_respects_1200_token_cap`: oversized facts produce digest `<= 1200` real tokens with deterministic truncation.
- `test_q05_gap_slots_receive_recall_without_wire_change`: call gap prompt builder; assert recall renders internally and API request/response fixture remains unchanged.

## Acceptance Criteria

**AC-Q05-1** - Given prior validated facts for a user, when recall runs for a new application, then only that user's PFACTs are considered.

**AC-Q05-2** - Given recall output, when tokenized, then rolling digest plus top-K is at most 1,200 tokens.

**AC-Q05-3** - Given gap prompt wiring, when Q-05 is absent or empty, then Q-gap slots are safe no-ops and the wire contract is unchanged.

## Done-when

All RED tests pass; Q-10 tokenizer is used when available; F-01 oracle remains green.

## Sequencing / Dependencies

Depends on D-H2 and O-2 resolution. Q-07/D-M5 key fix should precede durable use of the deployed knowledge table.

