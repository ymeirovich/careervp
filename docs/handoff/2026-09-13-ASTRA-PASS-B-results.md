# Astra Pass B — evidence and instrument audit

Completed against `cea07992539c09724a4f05be3761f24b8f4e4d5f`, prompt B/1. **20/20 manifest IDs: 12 prior conclusions upheld, 4 overturned, 4 unprovable at their claimed scope.** These are Pass B adjudication counts, not a re-derivation of P1’s defect base rate.

The four substantive corrections are:

- **S1:** The normal CV-tailoring path requires an owned upstream VPR before the cited fallback. Changing only the dependency owner produces 409; the unsafe fallback is called zero times. The isolated DAL method remains unscoped, but P1’s claimed reachable path is false.
- **S11:** Each cited cancel handler reads and writes its own key schema. The opposite schema fails before update. An unconditional update can still recreate a deleted record under the **same** key; this separate race does not establish P1’s cross-schema phantom mechanism.
- **PREMISE-P3:** The AST totals reproduce, but “no raise” does not mean success. At least 46 of the 144 blocks contain explicit failure Result/HTTP error returns. A controlled return-value example gets the same classifier label for opposite outcomes; an internally caught nested raise also defeats “any raise means surfaces.”
- **PREMISE-P4:** With the parent’s tests and environment fixed, changing only the upload handler to its `7cdc5e5` version adds a failure in `TestCVUploadDynamoDBPersistence::test_openapi_payload_uses_bearer_token_for_user_id`. A red baseline does not imply that no existing test can detect a regression. P1’s separate P-05 probe criticism remains supported.

The complete [20 YAML records](2026-09-13-ASTRA-PASS-B-results.yaml) retain P1’s verdict/claim, the manifest text, separate conjunct verdicts, exact rerun commands, raw-output links, matched controls, instrument checks and falsifiers. **A scalar REFUTED identifies a contradicted conjunct; it does not erase confirmed mechanisms listed in that record.** UPHELD preserves P1’s supported central conclusion, with secondary overstatements identified explicitly. UNPROVABLE-WITHOUT-DEPLOY is the mandated label for insufficient evidence; the missing evidence may be a read-only historical trace rather than an actual deployment.

## Summary table

| Finding | P1 verdict | Upheld? | My verdict | Confidence | Evidence IDs | Instrument mismatch | Overturn basis |
|---|---|---|---|---|---|---|---|
| S0a | CONFIRMED — proven by execution, no deploy required. | UPHELD | CONFIRMED | high | E-001, E-013, E-018, E-022 | true | n/a |
| S0b | mechanism CONFIRMED by execution. Stated trigger (24h TTL) REFUTED. | UPHELD | REFUTED | high | E-002, E-005, E-022 | true | n/a |
| S11d | CONFIRMED at the DAL layer. Live user impact UNPROVABLE-WITHOUT-DEPLOY. | UNPROVABLE-WITHOUT-DEPLOY | REFUTED | high | E-003, E-019, E-010, E-022 | false | n/a |
| S25 | CONFIRMED (the call is broken). "Never advanced" REFUTED as written. | UNPROVABLE-WITHOUT-DEPLOY | UNPROVABLE-WITHOUT-DEPLOY | high | E-004, E-006, E-022 | true | n/a |
| S1 | CONFIRMED | OVERTURNED | REFUTED | high | B matched source controls | true | mechanism_false |
| S2 | Mechanism CONFIRMED / exploitability REFUTED | UPHELD | REFUTED | high | E-015, E-022 | false | n/a |
| S6 | CONFIRMED | UPHELD | CONFIRMED | high | B matched source controls | false | n/a |
| S7 | CONFIRMED, understated | UPHELD | CONFIRMED | high | E-021 | true | n/a |
| S8 | CONFIRMED (live schema proof) | UPHELD | CONFIRMED | high | E-014, E-022 | false | n/a |
| S10 | CONFIRMED in substance / mechanism partly misstated | UPHELD | CONFIRMED | high | B matched source controls | false | n/a |
| S11 | CONFIRMED | OVERTURNED | REFUTED | high | B matched source controls | true | mechanism_false |
| S23 | mechanism CONFIRMED. "On the request path" REFUTED. Severity REFUTED. | UNPROVABLE-WITHOUT-DEPLOY | REFUTED | medium | E-017, E-022 | true | n/a |
| S26 | 6 of 7 sub-claims CONFIRMED / "unbounded" REFUTED | UPHELD | REFUTED | high | E-020 | true | n/a |
| K9 | CONFIRMED (live metrics) | UPHELD | CONFIRMED | high | E-008, E-007, E-022 | false | n/a |
| G1 | GOOD — and mutation-proven | UPHELD | CONFIRMED | high | E-012 | false | n/a |
| G4 | GOOD | UPHELD | CONFIRMED | high | B matched source controls | false | n/a |
| PREMISE-P2 | the two-cause framing STANDS. The cited anchor is WRONG. | UPHELD | REFUTED | high | E-007 | false | n/a |
| PREMISE-P3 | the count is REFUTED. The characterisation is CONFIRMED and understated. | OVERTURNED | REFUTED | high | E-009 | true | harness_defect |
| PREMISE-P4 | CONFIRMED, with a specific and severe instance — and the suite is stronger than feared in other places. | OVERTURNED | CONFIRMED | high | E-010, E-011, E-012, E-013 | true | raw_contradiction |
| PREMISE-P5 | CONFIRMED, and more strongly than claimed. | UNPROVABLE-WITHOUT-DEPLOY | UNPROVABLE-WITHOUT-DEPLOY | medium | E-016, E-007, E-022 | true | n/a |

“Instrument mismatch” also records a narrower tested layer than the claimed layer. It does not automatically invalidate a sound handler proof.

## Reproductions and instrument integrity

The main working-tree unit command returned **1427 passed, 15 skipped, 4 xfailed**. [Raw baseline](../evidence/astra-pass-b/unit-baseline.log). The isolated historical/mutation environments were different and were assessed against their own baselines:

| Run | Result | Interpretation |
|---|---|---|
| Five defect-asserting S0a/S0b/S25 cases | 5 passed | Green means the asserted defects reproduced. |
| Four scratch files, explicitly selected | 3 failed, 13 passed | GPA TypeError plus the scratch probe’s two empty-200 assertions; not three new production defects. |
| Original P-05 integration probe | 9 passed | All stop at the unauthenticated 401 boundary. |
| Isolated head, blocked unmocked AWS transport | 46 failed, 1380 passed | Matched mutation baseline, not a clean release result. |
| Both VPR ownership checks disabled | 47 failed, 1379 passed | One added cancel-ownership failure. |
| Status ownership check alone disabled | 46 failed, 1380 passed | No added failures; a separate poisoned-input control proves the mutant returns foreign data. |
| Header fallback, both header spellings | 52 failed, 1374 passed | Six added failures, no recovered failures. |
| Parent upload tests, before → one-file fatal-write change | 9 failed / 3 passed → 10 failed / 2 passed | A named pre-existing test detects the change. |

The header mutation’s three Cognito middleware tests share a fixture carrying header, body and query identity together. They are not independent body/query mutations. An earlier lowercase-only mutation produced three failures; the comparable two-spelling version produced six. [Mutation diff](../evidence/astra-pass-b/E012-both-header-cases.diff), [full log](../evidence/astra-pass-b/E012-both-header-cases.log).

P1’s E-010 worktree counts and claimed single-failure mutation baseline did **not** reproduce. The initial worktree runs encountered unmocked AWS paths and were interrupted; those partial logs are retained. Subsequent full runs denied transport before a socket send, with the same interpreter and dependencies. Their additional failures cannot be attributed solely to the historical commit. The decisive upload comparison keeps parent tests, working directory, mocks and interpreter identical and changes only the handler file. [Exact diff](../evidence/astra-pass-b/E010-fatal-write-only.diff), [before](../evidence/astra-pass-b/E010-matched-before.json), [after](../evidence/astra-pass-b/E010-matched-after.json).

P-05’s registry pins export to `cv_tailored`. Authenticated owner-positive controls show that its export seed returns 404 even for the owner, and its gap seed returns empty questions even for the owner. Thus “no secret leaked” does not prove those two fixtures reach their intended objects. Company research does return the seeded content to the owner and an empty result to the attacker; the empty 200 still differs from the denial contract. P1 corrected its prose but left the two failing empty-200 assertions in the supplied scratch test. [Owner/attacker raw responses](../evidence/astra-pass-b/independent-controls.json).

The audit also corrected and retained its own instrument mistakes: directory discovery omitted the scratch filenames; DynamoDB’s reserved `ttl` projection required an alias; the first S8 control used the wrong sort-key prefix; and an initial synthetic Result omitted its required code. Corrected controls, commands and outputs are alongside the initial receipts. None of these unsuccessful attempts is presented as a successful proof. E-002/E-003/E-004 have sound mechanism controls; independent fixtures generate incidental UUIDs/timestamps, and the additional GPA control fixes the CV id.

## Live-source correspondence: E-022

E-022 was checked **before opening P1’s verdicts**. `DEPLOYED_GIT_SHA` is null. The cited `service_stack.py` addition is an uncommitted **CloudFormation output**, not a Lambda environment variable; the live stack output is also absent. A timestamp or missing stamp alone cannot identify the deployed application source.

Read-only inspection then downloaded the Lambda deployment ZIP, verified its SHA-256 against AWS `CodeSha256`, and compared all **137 `careervp/*.py` members** against the commit and worktree: **zero mismatches**. Export/status/CV-parser/CV-tailor `live-devx` aliases resolve to version 16 with that bundle; worker and cleanup latest versions share it. This establishes application-source correspondence for those checked functions without deploying. It does not establish dependency equivalence, all deployment configuration, or a completed production attack. [Bundle comparison and per-file hashes](../evidence/astra-pass-b/deployed-bundle-comparison.json).

The actual deployed `prod` stage export for REST API `ymzhvcxod0` confirms the export/status integrations and Cognito authorizer. Alias-specific Lambda resource policies permit API Gateway invocation; an unqualified `get-policy` failure did not establish absence of alias permissions. The attached WAF has managed rules and IP rate limiting, not an observed per-artifact owner check. These checks strengthen the relevance of the moto leak proofs, but **no real two-user HTTPS attack was executed**. [Deployed stage export](../evidence/astra-pass-b/deployed-api-oas.json), [alias permission](../evidence/astra-pass-b/export-policy-live-devx.json), [WAF](../evidence/astra-pass-b/waf-prod.json).

S0b’s full scan found 36 jobs: 10 completed with approximately one-year TTLs, 26 `active` without TTL. All ten current result objects have corresponding completed rows. However, the worker uploads S3 before canonical persistence and TTL extension, so failed completion can strand an object with an older job TTL. The live bucket also expires objects after 365 days, contradicting indefinite persistence and making a one-year leak dependent on deletion ordering. The independently reproduced **DynamoDB read-error → absent-row fallback → foreign data** mechanism requires neither expiry. The 26 writers and historical failure cohorts remain unattributed.

S25’s 12-row snapshot cannot prove historical transitions or writers. Its upsert initializes an absent application at `gap_responses_submitted` but preserves an existing `cv_selected` state. S11d’s live parser GPA frequency remains unknown, despite verified serialization failure. K9 has stronger evidence: 336 errors across 336 invocations in the sampled 14-day window, plus a raw `MissingTableEnvError` log matching deployed source. That does not establish all-time cleanup history.

The STS identity is account `788159322332`, region `us-east-1`, user `presgen_user`. **The supplied credentials are administrative (AdminAccess group), not read-only**, contrary to the operator checklist. All audit AWS calls were read-only. Model selector/effort also cannot be independently confirmed: the system identifies GPT-6/Codex; Astra/high were requested, not verified runtime metadata.

## Trust-sweep spot checks and traceability

| P1 sweep row | Independent check | Assessment |
|---|---|---|
| TipTap paste sanitization | Read editor paste hook, StarterKit `link:false`, serializer tag allowlist/attribute dropping and DOMParser fallback | Source mechanism supported; SSR fallback returns unsanitized input. No browser attack executed. |
| CSP / framing / HSTS | Read Next config, middleware, Amplify config and CloudFront distribution source | No configured controls at those sources; not a live response-header measurement. |
| Token storage | Read cookie construction and Cognito client configuration | Missing Secure and JavaScript-accessible cookie confirmed in source. SDK storage/runtime refresh-token exposure remains an inference. |
| WAF body/rate controls | Read construct and attached devx stage WAF response | 64KB inspection, body-size Count override and 1000/IP/300s supported for devx. Future production impact is not measured. |
| PII logging | Read interview handler’s CV payload and generation-context INFO calls | Source disclosure supported on reached paths; “every invocation” is too broad. Live execution frequency was not measured. |
| Server input bounds | Read request model constraints and search `validate_cv_upload` callers; execute string-length model controls | The validator is unwired and named fields accept large strings. This is not proof of a successful oversized HTTP upload. |

These six rows meet the requested spot-check minimum. The sweep’s evidence standard is materially weaker than the controlled Tier-1 proofs: several rows turn source presence/absence into a system-level or all-invocations assertion without a positive control. Some are useful and candidly marked as inferences. P1 reports two terminated Tier-2 verifier agents and its own subsequent verification; the S1/S11 missed dominating paths show weaknesses in the final work, but there is no evidence that agent termination caused them. No agent was delegated work in this audit.

For the traceability table, retain the export/status and silent-failure work, but qualify deployment claims as above. Do not infer a state writer from the S25 scan, all-time inactivity from the knowledge count, or safe ownership from empty fixtures. P2’s authority/key-grammar work stands with corrected anchors. P3 should target caller-visible error propagation, not all 144 no-raise catches. P4 should improve authenticated branch coverage and mocks while preserving demonstrated controls. P5’s deletion-only recommendation remains unproven without consumer/history evidence and the explicit feature-scope decision already acknowledged by P1.

## Manifest reconciliation

```yaml
input_count: 20
processed_count: 20
input_ids: ["S0a", "S0b", "S11d", "S25", "S1", "S2", "S6", "S7", "S8", "S10", "S11", "S23", "S26", "K9", "G1", "G4", "PREMISE-P2", "PREMISE-P3", "PREMISE-P4", "PREMISE-P5"]
processed_ids: ["S0a", "S0b", "S11d", "S25", "S1", "S2", "S6", "S7", "S8", "S10", "S11", "S23", "S26", "K9", "G1", "G4", "PREMISE-P2", "PREMISE-P3", "PREMISE-P4", "PREMISE-P5"]
missing: []
extra: []
order_matches: true
omission_reasons: []
pass_a_output_read: false
p1_base_rate_rederived: false
```

## Calibration self-check

- Overturned conclusions without new raw evidence: **0**.
- Harness-artifact claims without inspecting raw output: **0**.
- Declined to uphold a finding with a sound control: **yes, at composite scope only**. S11d’s DAL failure and S25’s broken call remain confirmed; their broader live/history conclusions remain unproven. Their sound controls are not discarded.
- Semantic-only overturns: **0**. Severity/wording disagreements are recorded separately. The four overturns concern reachable behavior, classifier behavior or a measured test delta.
- No “could not reproduce” result was used by itself as refutation. Unknown billing, live parser output, historical writes, effective IAM restrictions and HTTPS execution remain unknown.

## Instructions, changes and run metadata

Root `AGENTS.md` and `CLAUDE.md` are the only repository agent instruction files found; `.clauderules` is incorporated. Preservation, mock-only testing and the initial deployed-state check apply. The task is a source/evidence audit: implementation-only formatter/type/naming/frontend checks do not authorize changing the dirty working tree. No production fixes landed, so `PROGRESS.md` and `plan.md` were not updated. `CLAUDE.md:40` really selects `tests/unit/`, excluding execution of the integration probe.

Only audit documents and receipts were added. Both temporary mutation worktrees are restored and clean; their locations remain in the metadata for reproduction. No deployment, live write, commit or merge was performed. Main-tree unit tests are green; the audit intentionally retains defect-reproducing failures and non-green isolated baselines instead of presenting them as a release pass.

[Run metadata](../evidence/astra-pass-b/run-metadata.json) records model-verification limits, B/1, full commit, AWS identity/region/stage, timestamps, Python/package versions, instruction scope and verification commands. [File inventory](../evidence/astra-pass-b/inspected-files.json) distinguishes semantic reads, AST/hash coverage, test scope and raw receipts. [Resource inventory](../evidence/astra-pass-b/inspected-resources.json) lists exact AWS commands, returned resource ARNs, timestamps and failures. [Final worktree status](../evidence/astra-pass-b/final-worktree-status.json) records restored mutations. [Artifact validation](../evidence/astra-pass-b/artifact-validation.json) verifies required fields, manifest order and evidence links.
