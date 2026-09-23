# Astra Pass A — independent results

The full [YAML audit](2026-09-13-ASTRA-PASS-A-results.yaml) contains one record for every manifest ID, in manifest order, with exact claims, conjuncts, inspected citations, independently derived mechanisms, executable controls, verdicts, uncertainties and change-of-verdict criteria. Its evidence catalog retains the actual commands, working directories, environments, exit codes and output. Reused command entries use YAML anchors. A separate [raw command ledger](../evidence/astra-pass-a/commands.json) is also available.

This is an audit of commit `cea07992539c09724a4f05be3761f24b8f4e4d5f` on `tools/proof-harness`, with the existing dirty worktree recorded. No application fixes or deployments were made. The excluded prior-review files were not opened. Pass-B files appeared during the run but were not consulted.

The VPR export and missing-row status paths reproduced cross-owner content disclosure using synthetic data and moto. The actual deployed stage routes to matching handler source through `live-devx` version 16. No live cross-user export or cancellation was invoked.

Two useful corrections are the GPA trigger and historical test sensitivity. A directly constructed float GPA fails in the DAL, but the real parser discards extracted GPA before persistence. An existing upload test passes against the pre-change handler and fails against the fatal-write change when the historical fixtures are loaded. Neither result supports the original broad wording.

## Governing instructions

The repository enumeration found `AGENTS.md`, `.clauderules`, and `CLAUDE.md`; all three were read. The invoked Pass A/1 handoff governs the review procedure, blinding, evidence discipline and verdict labels. Repository instructions govern preservation of existing work, AWS mocking, provider mocking and the documented test commands.

The review did not apply implementation-only actions: no global format/fix pass, code repair, frontend checks, CDK synthesis, commit, deployment, or progress-checklist update. Running global mutation against a dirty checkout would alter the audited object. Expected negative controls and failing historical assertions are evidence, not implementation tasks. No Python, frontend or infrastructure source was edited.

CLAUDE.md feature descriptions, model-policy recommendations, historical decisions and pricing were treated as non-authoritative context. The handoff requests GPT-6 Astra with high reasoning; this session cannot independently inspect the model-selector UI or reasoning setting. The metadata records that limitation instead of claiming the operator checklist was verified.

The prohibited `P1-VERDICTS.md`, `ASTRA-evidence-register.yaml`, and `docs/evidence/p1-repro/` contents were never opened. Historical `git show` output included commit-message interpretations; the verdict uses executable reconstruction, not that prose. No subagents were used.

## Per-finding YAML records

Read the [complete records](2026-09-13-ASTRA-PASS-A-results.yaml). A `CONFIRMED` verdict may apply to the demonstrated mechanism while explicitly refuting a trigger or scope conjunct, as required by the handoff. In particular, S11d does **not** confirm that extracted GPA currently makes uploads fail. `UNPROVABLE-WITHOUT-DEPLOY` is the handoff's uncertainty label; some missing proof can be obtained without deploying.

## Summary table

| Finding | Verdict | Confidence | Evidence IDs | Instrument mismatch | Refuted subclaims | Reason |
|---|---|---|---|---|---|---|
| S0a | CONFIRMED | high | batch1, config0, alias0, stage_export, deployed_source | No | None established | VPR export drops owner identity; synthetic attacker receives victim DOCX. |
| S0b | CONFIRMED | high | batch1, config1, alias1, stage_export, deployed_source, lifecycle, ttl | Yes | The VPR results bucket does not have indefinite configured retention: the live lifecycle applies a 365-day expiration rule. / Age over 24 hours alone is not the trigger tested by the handler; it requires a missing row and accessible S3 result. | Missing-row fallback bypasses ownership; retention and 24-hour scope overstated. |
| S11d | CONFIRMED | high | batch1, batch3, deployed_source, history_diff | Yes | The stated current upload trigger is false: the real parser does not copy extracted GPA into Education. / The same cost_usd omission does not apply to the current VPR model, which has no such field. / 7cdc5e5 changed the second-table write handling, not GPA propagation; the first write already returned 500 on errors. | DAL float failure confirmed; real parser discards GPA, so claimed upload trigger is false. |
| S25 | CONFIRMED | high | batch1, batch5, deployed_source | Yes | Applications do not universally have to remain at cv_selected forever: the response-submission upsert is a demonstrated alternative path. | Pending transition loses owner; alternative response-submission path refutes universal stall. |
| S1 | REFUTED | high | batch2_final, config2, alias2, stage_export, deployed_source | Yes | The asserted reachable cross-tenant fallback on the current route is contradicted by the dominating dependency check. / The current DAL VPR model cannot supply the claimed job_posting attribute. | Real dependency resolver blocks foreign VPR before alleged fallback. |
| S2 | REFUTED | high | batch2_final, stage_export, alias2, deployed_source | Yes | The guard is not just not event.get(httpMethod): it also requires three top-level fields. / Normal HTTP v2 body fields do not satisfy that top-level requirement. / The audited deployed public integration is REST, not HTTP API v2. | Top-level SFN payload required; ordinary HTTP v2 body cannot select it. |
| S6 | CONFIRMED | high | batch2_final | Yes | Total LLM API failure is not treated as successful generation. / GAP_QUESTIONS_GENERATED is a logic Result code; the inspected HTTP success body contains questions and does not itself expose that code. | Malformed output becomes templates; invocation errors remain failures. |
| S7 | CONFIRMED | high | batch2_final | No | None established | Section defaults and exhausted quality gates succeed; public response drops warning. |
| S8 | CONFIRMED | high | batch1, config3, live0 | Yes | On the ordinary ClientError path, the DAL catches the exception and returns an unsuccessful Result; it does not always raise into the handler except branch. | Wrong table/schema loses gap answers; DAL returns failure rather than always raising. |
| S10 | CONFIRMED | high | batch3, config1 | Yes | The direct jobs-status write is not syntactically wrapped in except Exception: pass; its unsuccessful Result is ignored instead. / Continued generation/billing is a conditional consequence of failed stop and worker behavior, not an observed universal outcome. | Ignored Result and swallowed chain errors still produce cancelled/200. |
| S11 | CONFIRMED | high | batch3 | Yes | The described legacy-to-canonical phantom-write transition is absent in these current handlers. | Unconditional update permits partial upsert; alleged schema-switch cause is false. |
| S23 | CONFIRMED | high | batch2_final | No | If interpreted as an exact total tokenizer-call count, n*m omits the additional n requirement tokenizations; the big-O statement remains correct. | Repeated evidence tokenization scales as n*(m+1); no explicit pool cap. |
| S26 | UNPROVABLE-WITHOUT-DEPLOY | medium | batch4 | Yes | Scraped input is explicitly bounded by MAX_PROMPT_WORDS=2500 at the very cited company_research.py:479. / There is not a total absence of privileged channels across all these pipelines: company research and VPR use separate system prompts. / VPR input is structured into labeled JSON sections; an absolute no-delimiters characterization is inaccurate. | Input-handling weaknesses shown; successful prompt injection not reproduced. |
| K9 | CONFIRMED | high | batch1, config_cleanup, deployed_source | No | None established | Required jobs variable missing in live configuration; matching deployed code raises. |
| G1 | UNPROVABLE-WITHOUT-DEPLOY | medium | batch2_final, batch3, existing_tests | No | None established | Named helper/upload protections verified; universal write safety and full issue closure unproven. |
| G4 | CONFIRMED | high | batch3, batch5 | No | None established | Real multi-page reads work; a page-two error still becomes an empty list. |
| PREMISE-P2 | UNPROVABLE-WITHOUT-DEPLOY | medium | batch4, batch1, batch2_final, config0, config2, config3, live0 | Yes | None established | The claimed 35-item causal group is not enumerated; alias existence is insufficient proof. |
| PREMISE-P3 | REFUTED | high | ast_counts | Yes | About 40 exact Exception/pass occurrences is contradicted by the explicit count of 12. / The interview-prep broad catches must not be counted as 17 bare-pass handlers. / Exact pass-only broad catches are not the default among 479 exception handlers. | 12 exact broad-pass blocks, not approximately 40; zero in interview-prep handler. |
| PREMISE-P4 | REFUTED | high | history_diff, history_parent_focus, history_changed_focus, history_parent_scoped, history_changed_scoped, existing_tests | Yes | The spot-check implication that no existing test could detect the fatal-write change is false. / The historical suite cannot be characterized as uniformly self-closing from this example: a pre-existing assertion rejects the changed behavior. | A pre-existing test detects the fatal-write change once its real fixtures load. |
| PREMISE-P5 | UNPROVABLE-WITHOUT-DEPLOY | medium | batch5, stage_export, alias3, live0, live1, deployed_source | Yes | One name grep alone does not establish live reachability, especially with table aliases, shared environment variables and unused packaged modules. | Application route is disconnected from the table; absolute zero live usage is unproven. |

## Manifest reconciliation

```yaml
input_manifest_ids: [S0a, S0b, S11d, S25, S1, S2, S6, S7, S8, S10, S11, S23, S26, K9, G1, G4, PREMISE-P2, PREMISE-P3, PREMISE-P4, PREMISE-P5]
processed_ids: [S0a, S0b, S11d, S25, S1, S2, S6, S7, S8, S10, S11, S23, S26, K9, G1, G4, PREMISE-P2, PREMISE-P3, PREMISE-P4, PREMISE-P5]
missing_ids: []
extra_ids: []
duplicates: []
order_matches: true
context_pressure_omissions: []
```

All 20 IDs were processed. Uncertainty is recorded as a verdict, not silently omitted.

The dependent-session scope decisions are:

- P2: shrink to demonstrated table, schema and partition contracts, and build an explicit causal map before a broad redesign.
- P3: shrink the blanket exception rewrite to a categorized inventory of broad-pass, error-to-empty and ignored-Result mechanisms.
- P4: shrink the wholesale test-suite replacement framing; preserve tests with demonstrated sensitivity and inspect fixture realism and enforcement.
- P5: stand as a reachability, product-contract and usage investigation. The evidence does not authorize deleting the table.

## Run metadata

```yaml
prompt_version: A/1
requested_model: GPT-6 Astra
runtime_self_identification: Codex / GPT-6 per session configuration
model_selector_independently_verified: false
requested_reasoning_effort: high
runtime_reasoning_effort_independently_verified: false
repo_commit: cea07992539c09724a4f05be3761f24b8f4e4d5f
branch: tools/proof-harness
aws_account: "788159322332"
aws_region: us-east-1
aws_caller: arn:aws:iam::788159322332:user/presgen_user
credential_policy_read_only_verified: false
live_operations: read-only
resource_environment: devx
api_id: ymzhvcxod0
api_stage: prod
api_deployment: 4e2k57
lambda_alias: live-devx
verified_route_alias_version: "16"
deployed_package_sha256_base64: FvIo0I3Kkl7C8DQCrU+Y51tS/UH3DPafiwcnFZescEU=
first_recorded_utc: "2026-09-13T08:58:59Z"
evidence_assembly_utc: "2026-09-13T18:55:24Z"
existing_upload_suite: "15 passed"
independent_final_batches: [batch1, batch2_final, batch3, batch4, batch5]
historical_parent_control: "1 passed"
historical_changed_handler: "1 expected failure: 500 != 201"
application_code_changes: []
commits: []
deployments: []
```

The YAML metadata enumerates all 137 locally AST-inspected application Python files, additional instruction/infra/test files, 28 citation-source hashes, historical revisions and the inspected AWS resources. The deployed package was read into memory; every application Python entry was searched for knowledge-table references, and nine named source files were hash-compared. The local historical checkout is `/private/tmp/careervp-pass-a-history.ZlyBch`.

Live resource inspection covered the CareerVpCrudDevx template, 11 DynamoDB GlobalTable resources, bucket lifecycle definitions, Lambda inventory/configurations and aliases, jobs TTL, API resources and the actual deployed `prod` stage export. `devx` is the resource environment; `prod` is the stage name. Those identifiers must not be conflated.

Measurement corrections are retained in the raw evidence: oversized command output was discarded after truncation; an incomplete synthetic EvidenceList and missing moto control table were repaired before accepting batch 2; explicit historical fixture discovery changed the regression conclusion. The repository verifier passed for both its default dev scope and the audit's devx scope, but it covers only one Lambda, two tables and a bucket prefix. Its result was not treated as full deployment validation.

Command output is captured as a combined stream. The YAML stores that verbatim under `stdout` and records `stderr: null`, because separate stderr was unavailable. No separate-stream evidence was invented.

