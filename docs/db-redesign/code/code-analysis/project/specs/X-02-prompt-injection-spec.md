---
spec_id: X-02-PROMPT-INJECTION
title: "Prompt-injection hardening and generated-output sanitization"
status: draft
owner: backend
tier: T2
scope_lock_clause: X-02
claude_code: {model: opus, effort: high}
codex: {model: gpt-5-codex, reasoning: high}
format_note: "AUTHOR ONLY. RED tests are inline descriptions; pytest/vitest files are written later at IMPLEMENT time."
---

# Spec - X-02: Prompt Injection Hardening

## Problem Statement

Untrusted CV, JD, and Tavily-scraped CR text must be delimited/tagged in every artifact prompt. Generated artifact fields rendered by the frontend must be sanitized/encoded, and SSRF guard behavior must be preserved. End-to-end XSS closure needs one explicit frontend verification task because the sink is in `src/frontend`.

## Evidence

- `project-scope-lock.md:211` defines X-02 and states Q-08 red-team is the test while defenses are implemented here.
- `src/backend/careervp/handlers/company_research_worker_handler.py:27` consumes scraped/researched company content.
- `src/backend/careervp/logic/prompts/` contains prompt templates that must delimit untrusted blocks.
- `src/backend/careervp/logic/fvs_validator.py` already gates factual validity but does not substitute for prompt-injection defense.
- `src/frontend/app/layout.tsx:10` confirms frontend app exists; render-sink verification must inspect frontend artifact renderers during implementation.

## Fix Plan

1. Inventory every artifact prompt consuming CV, JD, CR, gap answers, or user-entered text.
2. Wrap untrusted text in explicit delimiters/tags and instructions that it is data, not instructions.
3. Sanitize/encode generated HTML/Markdown fields before they reach frontend render sinks.
4. Preserve and test SSRF guard for external URL fetches.
5. Add one frontend verification test that an injection payload in an artifact field renders safely.

## RED Tests to Write First

- `test_x02_all_prompt_builders_delimit_untrusted_blocks`: static/fixture test asserts CV/JD/CR blocks include exact opening/closing delimiters.
- `test_x02_prompt_injection_fixture_ignored_by_model_prompt`: prompt fixture includes `ignore previous instructions`; assert it remains inside data delimiters and system instruction says not to follow it.
- `test_x02_generated_markdown_sanitized_before_response`: malicious generated field `<script>alert(1)</script>` is encoded/removed in API response.
- `test_x02_ssrf_guard_still_blocks_private_ip`: URL fetch fixture for `169.254.169.254` or private IP is rejected.
- `test_x02_frontend_artifact_render_sink_safe`: frontend renders an injection payload artifact and asserts no script execution / no dangerous HTML sink.

## Acceptance Criteria

**AC-X02-1** - Given untrusted CV/JD/CR text, when a prompt is built, then text is tagged as data and cannot escape delimiters.

**AC-X02-2** - Given generated artifact fields, when returned/rendered, then XSS payloads are encoded or sanitized.

**AC-X02-3** - Given SSRF payload URLs, when external fetch guard evaluates them, then private/link-local/internal targets are blocked.

## Done-when

All RED tests pass; Q-08 red-team includes the payloads; frontend verification is green for render sink safety.

## Sequencing / Dependencies

Coordinates with Q-08. Cross-boundary frontend verification is explicit and limited to render safety.

