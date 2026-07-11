---
spec_id: D-H4-P-01-CANONICAL-ARTIFACT
title: "Canonical artifact_id storage and upstream resolution for cover letter/interview prep"
status: draft
owner: backend
tier: T1
scope_lock_clause: [D-H4, P-01]
tooling:
  D-H4: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
  P-01: {claude_code: {model: opus, effort: high}, codex: {model: gpt-5-codex, reasoning: high}}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest files are written later at IMPLEMENT time."
---

# Spec - D-H4/P-01: Canonical Artifact Routing

## Problem Statement

Cover letter and interview prep fail because upstream artifacts have multiple schemas/keys and `vpr_id` routing is ambiguous. D-H4 stores one canonical `artifact_id` and passes resolved upstreams; P-01 is the user-facing defect this closes.

## Evidence

- `project-scope-lock.md:116` defines P-01 as cover-letter/interview-prep failure caused by 3-schema / `vpr_id` routing.
- `src/backend/careervp/handlers/vpr_status_handler.py:184-192,253` projects company research provenance into VPR status, showing status payloads already carry upstream provenance fields.
- `src/backend/careervp/handlers/cv_tailoring_handler.py:983-986` extracts path parameters for artifact ids, showing wire ids are route-provided opaque keys.
- `src/frontend/lib/types.ts:75` defines hub `artifact_id: string | null`, and `types.ts:517` requires CV tailoring to send `vpr_id: null` when absent.
- Scope-lock §3 requires `artifact_id` round-trip, hub `artifact_id` resolvable by status endpoint, and `vpr_id` null-vs-absent preservation.

## Fix Plan

1. Characterize current VPR, CV tailoring, cover letter, and interview-prep artifact ids.
2. Store one canonical opaque `artifact_id` per artifact and route status reads through it.
3. Resolve upstream VPR/CR/CV dependencies through D-H2 repository, not raw client-supplied keys.
4. Keep public `application_id == job_id`, `artifact_id`, and `vpr_id` semantics stable.
5. Prove migration parity for legacy ids before removing dual-read support.

## RED Tests to Write First

- `test_dh4_status_endpoint_resolves_hub_artifact_id`: seed hub artifact; assert status endpoint resolves the same `artifact_id`.
- `test_p01_cover_letter_uses_resolved_vpr_not_client_key`: call cover letter generation with a stale/cross-tenant `vpr_id`; assert repository resolves owned canonical VPR or rejects.
- `test_p01_interview_prep_uses_resolved_vpr_not_client_key`: same assertion for interview prep.
- `test_dh4_cv_tailoring_preserves_vpr_id_null`: request with present `vpr_id: null`; assert accepted and distinguishable from omitted.
- `test_dh4_legacy_artifact_id_parity_before_cutover`: D-H2 harness asserts legacy id and canonical id projections are identical.

## Acceptance Criteria

**AC-DH4-1** - Given a hub `artifact_id`, when status is requested, then the endpoint resolves that opaque id and returns the same artifact identity.

**AC-P01-1** - Given cover-letter or interview-prep generation, when upstream VPR is needed, then the handler uses resolved owned upstreams and not arbitrary client keys.

**AC-DH4-2** - Given CV-tailoring sends `vpr_id: null`, when parsed by backend, then null is accepted and omitted remains distinguishable.

## Done-when

All RED tests pass; F-01 oracle is green for §3 items 1-3; migration parity evidence exists; no route versioning required.

## Sequencing / Dependencies

Depends on D-H2/D-H3. Must precede full P-01 closure and Wave 4 frontend contract fixes that rely on stable artifact ids.

