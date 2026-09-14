# Astra Pass C — reconciliation

Completed for `cea07992539c09724a4f05be3761f24b8f4e4d5f`, branch `tools/proof-harness`, prompt `C/1`. **All 20 manifest IDs are reconciled: 12 CONFIRMED, 3 REFUTED, 5 UNPROVABLE-WITHOUT-DEPLOY.** These mixed counts include a good claim and planning premises; they are **not** a defect base rate.

The [authoritative YAML](2026-09-13-ASTRA-PASS-C-results.yaml) contains every required field, exact A/B/P1 scalar labels, conjunct-level explanations, disconfirming efforts, replay commands and raw receipt links. The [out-of-manifest register](2026-09-13-ASTRA-PASS-C-unadjudicated.yaml) preserves 14 additional claims without verdicts. No application fix, live AWS write, deployment, commit or planning-checklist update was made.

The main corrections are actionable: the cited CV-tailoring IDOR and HTTP-v2 authentication bypass do not follow their alleged paths; the GPA serialization failure is latent because the parser discards GPA; cancellation has a real same-key race rather than the claimed cross-schema cause; and an existing historical upload test detects the fatal-write change. The export/status handler leaks and silent-success mechanisms remain real at their demonstrated layers.

## Master comparison

Labels below are copied from the authoritative YAML inputs. In particular, B's scalar REFUTED can refer to a false conjunct while its record confirms the core mechanism. `U` abbreviates `UNPROVABLE-WITHOUT-DEPLOY` only in this table. `AS` means AGREE-SUBSTANTIVE, `AF` AGREE-SUPERFICIAL, `D` DISAGREE and `BU` BOTH-UNCERTAIN. Full P1 phrasing is preserved in C's YAML; its compact representation here does not change the record.

| Finding | P1 | Pass A | Pass B | Final | Confidence | Bucket | Decided by | Refuted subclaims |
|---|---|---|---|---|---|---|---|---|
| S0a | Confirmed; execution | CONFIRMED | CONFIRMED | CONFIRMED | high | AS | [C02-additional](../evidence/astra-pass-c/C02-additional.json) | None established |
| S0b | Core confirmed; 24h trigger refuted | CONFIRMED | REFUTED | CONFIRMED | high | AS | [C02-additional](../evidence/astra-pass-c/C02-additional.json) | Any completed VPR older than 24 hours necessarily exposes this fallback; completed jobs extend TTL to approximately one year and the observed result cohort still has rows. / The configured results bucket retains objects indefinitely; its enabled all-prefix expiration is 365 days. |
| S11d | DAL confirmed; live impact U | CONFIRMED | REFUTED | CONFIRMED | high | D | [C03-parser-races-pagination](../evidence/astra-pass-c/C03-parser-races-pagination.json) | Extracting GPA in the current parser necessarily makes upload fail; the parser omits GPA when constructing Education. / The claimed save_vpr cost_usd sibling is an active equivalent trigger; cost_usd belongs to another model and no application save_vpr caller was found. / Commit 7cdc5e5 introduced GPA propagation or made the first save newly fatal; it changed failure handling of the second dedicated-CV-table write. |
| S25 | Call confirmed; never-advanced refuted | CONFIRMED | U | U | medium | BU | [C01-independent](../evidence/astra-pass-c/C01-independent.json) | Response-submission upsert necessarily advances an existing cv_selected application; the matched control leaves it unchanged. This corrects a possible interpretation of the alternative path, not the original empty-owner finding. |
| S1 | Confirmed | REFUTED | REFUTED | REFUTED | high | AS | [C01-independent](../evidence/astra-pass-c/C01-independent.json) | The normal cited route reaches the unscoped fallback with the attacker-selected foreign VPR. / The current stored VPR model provides the asserted job_posting payload for this disclosure; job_posting belongs to VPRRequest. |
| S2 | Mechanism confirmed; exploit refuted | REFUTED | REFUTED | REFUTED | high | AS | [C01-independent](../evidence/astra-pass-c/C01-independent.json) | The guard is only absence of httpMethod. / An ordinary API Gateway HTTP-v2 request body satisfies the direct-invoke field contract. / The inspected public route uses HTTP API v2. |
| S6 | Confirmed | CONFIRMED | CONFIRMED | CONFIRMED | high | AS | [C01-independent](../evidence/astra-pass-c/C01-independent.json) | Total LLM API failure is indistinguishable from successful generation. / GAP_QUESTIONS_GENERATED is necessarily exposed in the HTTP success body; it is the logic Result code. |
| S7 | Confirmed, understated | CONFIRMED | CONFIRMED | CONFIRMED | high | AS | [C01-independent](../evidence/astra-pass-c/C01-independent.json) | None established |
| S8 | Confirmed; live schema | CONFIRMED | CONFIRMED | CONFIRMED | high | AS | [C02-additional](../evidence/astra-pass-c/C02-additional.json) | The ordinary schema failure always raises into the handler exception block; the DAL catches ClientError and returns failure. |
| S10 | Confirmed; mechanism partly misstated | CONFIRMED | CONFIRMED | CONFIRMED | high | AS | [C03-parser-races-pagination](../evidence/astra-pass-c/C03-parser-races-pagination.json) | All status writes are literally except Exception/pass; the main job write's unsuccessful Result is ignored instead. |
| S11 | Confirmed | CONFIRMED | REFUTED | CONFIRMED | high | AS | [C03-parser-races-pagination](../evidence/astra-pass-c/C03-parser-races-pagination.json) | These cancel paths read a legacy item and write a distinct canonical phantom; cover uses canonical keys throughout and CV-tailor uses legacy keys throughout. |
| S23 | Mechanism confirmed; request path/severity refuted | CONFIRMED | REFUTED | CONFIRMED | high | AF | [C01-independent](../evidence/astra-pass-c/C01-independent.json) | This generator's work runs synchronously inside the current public API Gateway generation request. / n*m is the exact total tokenizer invocation count; it excludes n requirement tokenizations, although the stated big-O term is valid. |
| S26 | 6/7 confirmed; unbounded refuted | U | REFUTED | U | medium | BU | [C01-independent](../evidence/astra-pass-c/C01-independent.json) | Scraped company text is unbounded; MAX_PROMPT_WORDS is 2500. / There is no privileged-channel capability anywhere in the client; complete has system_prompt and company/VPR use separate system prompts. / VPR inputs have no structural delimiters; labeled JSON sections exist. Delimiters alone do not prove injection resistance. |
| K9 | Confirmed; metrics | CONFIRMED | CONFIRMED | CONFIRMED | high | AS | [C01-independent](../evidence/astra-pass-c/C01-independent.json) | None established |
| G1 | Good; mutation-proven | U | CONFIRMED | U | medium | BU | [C10-targeted-controls](../evidence/astra-pass-c/C10-targeted-controls.json) | None established |
| G4 | Good | CONFIRMED | CONFIRMED | CONFIRMED | high | AS | [C03-parser-races-pagination](../evidence/astra-pass-c/C03-parser-races-pagination.json) | None established |
| PREMISE-P2 | Two-cause framing stands; anchor wrong | U | REFUTED | U | medium | BU | [C10-targeted-controls](../evidence/astra-pass-c/C10-targeted-controls.json) | Removing self.db alone eliminates the independently present resolver chains and dual key grammars. |
| PREMISE-P3 | Count refuted; characterization confirmed | REFUTED | REFUTED | REFUTED | high | AS | [C10-targeted-controls](../evidence/astra-pass-c/C10-targeted-controls.json) | There are approximately 40 exact except Exception/pass blocks; the defined source-only count is 12. / All 144 non-pass no-raise handlers return success-shaped outcomes. / Any nested Raise proves an exception surfaces to the caller. |
| PREMISE-P4 | Confirmed; mixed suite strength | REFUTED | CONFIRMED | CONFIRMED | high | AF | [C06-history-after](../evidence/astra-pass-c/C06-history-after.json) | No existing test could detect 7cdc5e5's fatal-write change because the parent suite was already red. / P1's isolated one-failure mutation baseline is reproduced by the retained controlled runs; their baseline has 46 failures. / Mutation survival proves globally zero line or branch coverage of status ownership; it establishes no additional failing assertion in the selected run, not a coverage census. |
| PREMISE-P5 | Confirmed, stronger | U | U | U | medium | BU | [C04-page-error-knowledge](../evidence/astra-pass-c/C04-page-error-knowledge.json) | One name grep is sufficient to settle all live and historical table usage or deletion safety. |

The bucket counts are 12 substantive agreements, two superficial agreements, one disagreement and five uncertainty buckets. S0b and S11 are substantive agreements despite opposite scalar labels: both passes confirm the core and reject the stated trigger/cause. S11d contains a real disagreement over parser/model reachability. S23 lacks a shared ruling on the public-route conjunct. PREMISE-P4's labels adjudicate different conjuncts: historical test sensitivity versus the P-05 probe's coverage claim.

For S25, S26, G1, PREMISE-P2 and PREMISE-P5, at least one authoritative pass leaves the composite claim uncertain. Procedure step 4 therefore preserves that verdict. Their known narrower mechanisms remain explicit. In particular, S25's empty-owner write is confirmed; the historical assertion remains uncertain. This distinction also governs the base-rate calculation below.

### Narrative versus YAML

The A and B narrative tables' verdict labels agree with their YAML fields; no scalar table/YAML mismatch was found. B explicitly explains its scalar-conjunct convention. Its narrative description of four substantive corrections is not interchangeable with its independent-verdict column: PREMISE-P4 remains CONFIRMED there because of the P-05 issue. C does not convert that deliberate split into a voting disagreement. B's S11d YAML confirms a general save_vpr serialization omission while leaving parser output uncertain; C's actual model/parser controls reject the named cost_usd sibling trigger and the current GPA-upload trigger. This is an evidence-based correction to B, not an MD/YAML discrepancy.

## Global finding: a moto leak is not an executed deployed exploit

**A handler-level leak under moto establishes a handler authorization defect for the supplied event, data and dependency behavior. It does not, by itself, establish an exploitable deployed leak.** The test supplies synthetic `requestContext.authorizer.claims`; it traverses no Cognito token validation, API Gateway event construction, WAF or effective execution-role/storage policy. The scratch test's descriptions of “real” authenticated claims do not change that fact.

E-018 alone establishes neither the executing deployment nor resource-level authorization. The stronger retained evidence includes the **deployed** `prod` stage export for REST API `ymzhvcxod0`, Cognito user pool `us-east-1_bAZ6jb6HP`, `aws_proxy` integration URIs, `live-devx` version-16 aliases, alias-specific API Gateway invoke grants, and the attached WAF configuration. These are distinct layers and objects. An unqualified Lambda `get-policy` failure does not contradict a valid alias policy. WAF managed/rate rules are not evidence of an artifact-owner comparison.

For a compelling end-to-end proof, the owner must first retrieve a known synthetic artifact through the same public route. A second real Cognito user must then request that exact artifact ID through the deployed stage, with request IDs tying responses to the verified alias/version. For export, retrieve the returned URL and inspect the actual DOCX for the synthetic secret. For status, retain the raw body, and, if claiming a downloadable object, retrieve the URL as well. For S0b, establish the jobs-row/error and S3-object preconditions at the time of the request. Use the same runtime/dependencies, configuration, execution role and bucket policy; record relevant boundaries, resource-policy conditions, encryption and network restrictions. **No pass established this complete transaction.** C did not execute export on live AWS: despite being a GET, it writes an S3 object.

The per-ID consequences are:

| ID | What survives | What remains unproved |
|---|---|---|
| S0a | Confirmed unscoped VPR read and synthetic victim DOCX export | Real two-user HTTPS export and live URL retrieval |
| S0b | Confirmed missing-row and read-error fallback before ownership | Live fallback cohort, expiry ordering, authenticated HTTPS body/URL exposure |
| S1 | Refutation of the specified fallback path under the real resolver contract | Safety of every other unscoped caller or integration |
| S2 | Refutation of ordinary HTTP-body selection of the SFN contract | Effective direct-invoke authority of every external principal |
| S11d | Latent DAL float rejection; current parser drops GPA | Provider extraction frequency, which is not needed to decide this parser path |
| S25 | Wrong-owner transition and existing/new-row distinction | Historical writer/transition claims; exact real-service exception class |
| S8 | Wrong-table gap lookup and silent empty context | A complete public cover-letter request on its routed alias and dependencies |
| S10 / S11 | Failed-effect acknowledgement and unconditional same-key race | Measured live cancellation continuation, competing writers or billed work |
| G1 | Helper/upload identity controls | Universal write safety and F-DEVX-8 closure |
| G4 | Successful multi-page cursor handling | General list error handling or unrelated export pagination |
| PREMISE-P4 | A probe testing the auth gate cannot certify ownership branches | Historical CI enforcement and whole-suite coverage claims |
| PREMISE-P5 | Disconnected source wiring and schema mismatch | Zero external/all-time use and deletion safety |

The confirmed source/handler findings warrant remediation without overstating them as completed production attacks. K9 is different: it has a raw deployed exception log identifying the same startup failure, in addition to metrics and source/configuration correspondence.

## E-022 ruling: application source matched; execution equivalence remains bounded

C audited [B's bundle-comparison receipt](../evidence/astra-pass-b/deployed-bundle-comparison.json) instead of downloading the ZIP again. The recorded method groups functions by AWS `CodeSha256`, verifies the downloaded archive digest, and compares member-byte SHA-256 values with commit source. C independently recalculated the **137 commit-file hashes**, checked the exact tracked application-Python member set in both directions, and found **zero mismatches, zero missing/extra Python members and zero duplicate recorded members**. The four checked export/status/parser/tailor aliases resolve to version 16 on that recorded bundle; worker and cleanup latest versions share the same hash. [C integrity computation](../evidence/astra-pass-c/C05-receipt-integrity.json).

This is a sound application-source correspondence method. It supports B's claim at that scope. Its `download_sha256_verified` value is retained command evidence, not an archive C independently rehashed: the ZIP bytes are not retained in that JSON. C accepts the receipt as instructed and does not pretend that rechecking its commit hashes independently authenticates the original download. The evidence applies to the recorded resources and times, not future alias movement.

The missing `DEPLOYED_GIT_SHA` no longer justifies a blanket “no source correspondence” caveat for the checked functions. The local `service_stack.py` addition is an uncommitted CloudFormation output, not a Lambda environment variable; the retained live output is absent. A build stamp would be useful provenance, but it is not required to compare application bytes.

What is now clean **at source level**: S0a/S0b export/status code, S1/S2 CV-tailor code, S11d parser code, and K9 cleanup code for the checked snapshots. The complete package also contains the source used for S6/S7/S8/S10/S11/S23/G1/G4/P2/P3/P4/P5. Package inclusion alone does not establish each module's executing alias or external consumers. Source-only algorithm, model and test conclusions require no deployment correspondence.

What still carries a **live execution/configuration caveat**: S0a/S0b HTTPS access; S8's full routed cover-letter execution; S10/S11 live effects; S23 worker latency/cost; S6/S7 provider output and billed impact; S26 injection success; G1 universal boundary safety; S25/P5 histories; and P2's group-level causal claim. S1/S2 refute their named paths rather than certify all system security. K9's recorded failure is directly observed; only all-time history and subsequent configuration changes remain open. No dependency equivalence, Lambda layers/runtime/import behavior, full IAM/configuration equality or end-to-end attack follows from comparing `careervp/*.py`.

## Manifest reconciliation

All four lists—manifest, A, B and C—contain exactly these 20 IDs, in this order:

```text
S0a S0b S11d S25 S1 S2 S6 S7 S8 S10 S11 S23 S26 K9
G1 G4 PREMISE-P2 PREMISE-P3 PREMISE-P4 PREMISE-P5
```

Each pass processed 20/20. Missing IDs: none. Extra IDs: none. Duplicates: none. Omission reasons: none. The unadjudicated register is explicitly excluded from these lists. [Machine-readable reconciliation](../evidence/astra-pass-c/manifest-reconciliation.json).

## Base rate: sampling frame, denominator and uncertainty

The reported sampling frame is the original inventory's **SEV-1/2/3 defect IDs**, drawn using `sort -R` before substantive reading. The ten sampled defect IDs represented here are `S1 S2 S6 S7 S8 S10 S11 S23 S26 K9`. The two additional “confirmed-good” checks, G1/G4, come from a different population and test false reassurance. The four Tier-1 IDs, `S0a S0b S11d S25`, were deliberately selected for impact, not randomly. C has the handoff's sampling description, not an independently verifiable random seed/draw transcript or exact full finite-population size. The uncertainty calculations are conditional on that reported design.

“Core defect” means an actionable defect in the specified mechanism at the evidenced layer. It includes S11d's latent DAL failure and S25's proven bad transition even though the respective live-upload/history claims are not proven. It does **not** count an unscoped method signature or trusted SFN interface as the alleged reachable unauthorized exploit when that path is contradicted. S26's input exposures do not, without a provider attack, establish successful injection. These are source/mechanism rates, **not deployed exploitation rates**.

“Materially wrong subclaim” means a directly contradicted trigger, scope or cause that changes remediation or impact classification. Merely unproven impact is not false. Exception-wrapper wording in S8/S10 is corrected in the YAML but does not change the primary fix, so it is not counted as materially wrong. Historical S25 transition assertions, S7 billing and S10 continuation remain unproven, not counted as disproven.

| Population and outcome | Numerator / denominator | Rate | 95% uncertainty interval |
|---|---:|---:|---|
| Random defect sample: demonstrated core | 7 / 10 | 70% | Wilson 39.7–89.2% |
| Random defect sample: refuted central exploit | 2 / 10 | 20% | Wilson 5.7–51.0% |
| Random defect sample: unresolved injection | 1 / 10 | 10% descriptive | Not folded into either resolved category |
| Random defect sample: materially wrong subclaim | 6 / 10 | 60% | Wilson 31.3–83.2% |
| Purposive Tier-1: demonstrated core | 4 / 4 | 100% descriptive | No population interval: purposive selection |
| Purposive Tier-1: materially wrong subclaim | 2 / 4 | 50% descriptive | No population interval: purposive selection |
| Combined, descriptive only: demonstrated core | 11 / 14 | 78.6% | No pooled population interval |
| Combined, descriptive only: materially wrong subclaim | 8 / 14 | 57.1% | No pooled population interval |
| Separate good checks: confirmed at full named scope | 1 / 2 | 50% descriptive | Too small/different frame; G1 composite remains uncertain |

The seven random core defects are S6/S7/S8/S10/S11/S23/K9. S1/S2's central exploit paths are refuted, and S26 is unresolved. The eight materially wrong entries are **S0b, S11d, S1, S2, S6, S11, S23, S26**. Their corrections concern, respectively: retention/trigger; parser and sibling reachability; a dominating dependency check; event-envelope requirements; transport versus content failure; same-key versus cross-schema race; synchronous versus asynchronous execution; and limits/channel structure. Five of these eight also have confirmed core defects; two have refuted central attacks and one has uncertain injection success.

Thus P1's **14/14 core defects** becomes **11 demonstrated, 2 refuted central allegations, 1 uncertain**. Its **0 fully refuted** becomes **2 refuted central exploit claims**, under the decision-relevant definition above. If “fully refuted” instead requires every incidental code statement to be false, that statistic is not useful: both entries still point to real signatures/branches. Its **6/14 materially wrong** becomes **8/14** under the explicit coding rule; the exact IDs make this judgment auditable. C does not silently count a narrowed source CONFIRMED as confirmation of a universal system allegation.

Sensitivity: discarding unresolved S26 gives 7/9 = 77.8%, Wilson 45.3–93.7%, but unresolved claims need not be missing at random. Counting it as eventually demonstrated gives 8/10 = 80%, Wilson 49.0–94.3%. Neither is a license to classify it now. Wilson intervals use `z=1.959963984540054`, with no finite-population correction because the exact frame/draw is unavailable. [Counts, membership and calculations](../evidence/astra-pass-c/base-rate.json).

Four premises are excluded because they are planning/measurement claims rather than sampled defects. G1/G4 are excluded from defect prevalence because they were selected from the good list. Tier-1 is excluded from random-sample inference because selection favors impact. Additional findings from A/B/C are excluded because their discovery was not a blind random draw. The approximately 85 unadjudicated findings may also differ in severity, subsystem and detection method; correlated failures further weaken simple independent-sample assumptions. Ten cases cannot establish a precise prevalence, a uniform severity level, a shared root cause or a count of remaining production exploits.

P1's advice to treat each entry as “a reliable pointer to a location and an unreliable description of the problem” is **supported as a triage heuristic, not as a universal reliability claim**. Many locations contain actionable defects and descriptions often misstate the cause or trigger. But two of ten random central attacks are contradicted, one is unproven, and the intervals are wide. Preserve the pointers, then prove reachability and the exact mechanism before choosing a fix.

## Corrections to P1, ordered by effect on the next engineering action

1. **S1 — remove the claimed reachable CV-tailoring IDOR from the confirmed-exploit queue.** A real owner-aware dependency resolver blocks it; C's poisoned fallback is never reached. Review other unscoped callers separately instead of fixing an unreachable branch on this evidence.
2. **PREMISE-P4 — preserve demonstrated tests and repair specific instruments.** The historical no-test-could-catch assertion is false: the unchanged parent's authenticated upload test newly fails after the handler change. The separate P-05 mismatch survives. Baseline rebasing and mutation limits are below.
3. **PREMISE-P5 — do not convert empty/unwired into deletion authorization.** Zero historical/external use remains uncertain; require a bounded history/consumer inventory and feature-scope decision.
4. **S11 — fix the unconditional same-key update/race.** The alleged legacy-read/canonical-write phantom is contradicted. A schema migration alone does not repair the demonstrated race.
5. **S11d — prioritize the actual storage contract, not an asserted current GPA-upload outage.** A directly constructed GPA-bearing UserCV fails, but the real parser drops GPA; cost_usd is not on the saved VPR. Provider GPA frequency is not the missing step needed to determine this current code path.
6. **S2 — separate a trusted direct-invoke interface from a public authentication bypass.** The required top-level fields are absent from ordinary HTTP-v2 bodies and the inspected deployment uses REST. Effective untrusted direct invocation would be a different proving task.
7. **PREMISE-P3 — replace the 144 presumed-success classification.** Broad catches without raise can return explicit error Results/HTTP errors; nested raises can be caught internally. Target actual caller-visible error masking instead of rewriting all such catches.
8. **PREMISE-P2 — keep authority/key work, with a causal map.** Neither the alias nor the two-cause story proves the approximately 35-item reduction. Narrow remediation to demonstrated contracts until those IDs and reproductions are mapped.
9. **S25 — retain the wrong-owner defect; withdraw the scan-based historical conclusion.** An upsert creates absent rows at submitted but leaves existing cv_selected rows unchanged. Eight submitted snapshots neither prove those records traversed the state machine nor establish who wrote them.
10. **S23 — retain repeated tokenization; leave severity open.** Async location refutes the API-timeout framing. A short synthetic benchmark cannot refute worker CPU/latency/cost impact, and evidence length materially changes the same pair-count benchmark.
11. **S26 — retain separate input exposures; do not count injection as executed.** Scraped text is bounded, the client has a privileged-channel API, and labeled JSON exists. None proves injection resistance; no real-provider attack was run.
12. **G1 — narrow GOOD to the tested helper/upload boundaries.** The shared header/body/query mutation fixture does not certify every independent identity input or every public write path; full issue closure stays uncertain.
13. **S0b — retain fallback remediation and correct retention reasoning.** Completed rows have approximately one-year TTLs, bucket retention is not configured indefinitely, and the read-error fallback needs neither expiry. A one-year age alone is also insufficient. Failed completion before TTL extension is separately registered, without assuming its historical frequency.
14. **S0a and other security conclusions — narrow “proven by execution” to the actual layer.** Synthetic handler execution proves a local defect, not a Cognito/API/IAM transaction. This changes the deployment validation needed, not the ownership fix.
15. **S6/S8/S10/K9/S7 — retain cores and bound the claims.** S6 distinguishes malformed content from invocation failure. S8's schema error normally arrives as a failed Result. S10 does not prove universal continuation/billing. K9's measured window and startup error do not prove all-time cleanup history. S7's warning loss does not itself measure provider charges. These mostly qualify supported P1 cores rather than overturn them.

G4's exact pagination claim stands; its page-two error observation is separately registered. Corrections already recognized in P1's structured wording are identified as retained qualifiers, not falsely presented as new overturns.

## What the next proving run must cover

The consolidated **final uncertain set is exactly S25, S26, G1, PREMISE-P2 and PREMISE-P5**. “WITHOUT-DEPLOY” is the handoff's label; several missing inputs are historical evidence or source contracts and cannot be supplied by deployment alone.

| ID | Exact required environment, credential or artifact | Deciding observation |
|---|---|---|
| S25 | Read-only access to retained DynamoDB data events or stream old/new images for `arn:aws:dynamodb:us-east-1:788159322332:table/careervp-applications-table-devx`, covering the claimed history, joined to writer/request IDs. For current behavior, an isolated stack matching the recorded route/source/runtime, synthetic owner and an existing `cv_selected` application; execute question generation and response submission and retain every intermediate row. | Historical transition/writer evidence settles history. A current flow settles only current behavior. Creating a missing row at submitted is not evidence of advancing an existing row. |
| S26 | Isolated provider evaluation with the deployed model IDs, prompts, library versions and decoding settings pinned; synthetic inputs, sandbox-only persistence, paired benign/adversarial company/CV/job/gap cases, explicit unauthorized-output criteria and scoped provider credentials. No real LLM calls in unit tests. | Retained provider requests/responses and downstream outputs demonstrating instruction override under the stated trigger; bounded failures do not prove universal immunity. |
| G1 | F-DEVX-8 acceptance criteria plus an enumerated public-write route/authorizer/integration inventory. Isolated matching deployment, two real users in a test Cognito pool, independent header/body/query identity mutations and verification of actual persisted owner keys for every route and trusted-invoke adapter. | Exhaustive named-contract coverage, not one helper test or a mixed-input fixture. |
| PREMISE-P2 | The exact approximately 35 finding IDs, with writer/reader, environment-to-table resolution, key grammar and failing-contract map; an isolated checkout at `cea0799` with each reproduction executable before/after only the proposed authority/key change. No AWS credential is inherently required. | Whether that change fixes each mapped failure; failures outside the map cannot validate/refute the unspecified group. |
| PREMISE-P5 | Read-only retained data events for `arn:aws:dynamodb:us-east-1:788159322332:table/careervp-knowledge-table-devx` over an explicitly bounded window, external/cross-account consumer and IAM inventory, plus product scope/retention decision. | A consumer refutes dead-table scope. Complete bounded-window evidence may support inactivity for that window; absent historical logging cannot prove all-time zero. |

Additional impact gaps survive confirmed mechanisms and must not disappear from the next run:

- **S0a/S0b:** the two-user HTTPS/URL transaction described above. In an already provisioned synthetic test deployment, a status request can be made with `curl --silent --show-error --dump-header response.headers --header "Authorization: $TEST_USER_B_JWT" "$TEST_API_BASE/vpr/$SYNTHETIC_VPR_ID/status" --output response.json`; execute an owner-positive request first and repeat with explicit row-present/missing conditions. Export uses the analogous `/jobs/$SYNTHETIC_JOB_ID/artifacts/vpr/export?format=docx` path but **writes S3**, so it belongs only in a separately authorized isolated environment. No such operation was performed on live AWS here.
- **S7/S10:** synthetic generation/cancel traces correlated with provider usage and billing to establish actual incurred work, with mocked providers in unit tests and any real-provider evaluation kept separate.
- **S23:** a deployed-equivalent worker benchmark using measured, privacy-preserving size distributions and p95/p99 latency/CPU/memory, not only a synthetic pair-count microbenchmark.
- **S8:** an owner-positive persisted gap-answer fixture verified through the actual routed cover-letter alias and serialized generation context.

Read-only credentials should be provisioned by the operator for future inspection. These instructions describe missing proof; they do not authorize this session to create resources, mutate rows, trigger paid generation, export live data or cancel live work.

## Unadjudicated claims

The [separate YAML register](2026-09-13-ASTRA-PASS-C-unadjudicated.yaml) records evidence offered by A/B and a proving-run assessment for every entry:

| ID | Captured claim | Offered by |
|---|---|---|
| U01 | Page-two errors discard accumulated list results | A, B |
| U02 | S3 write precedes canonical persistence and TTL extension | B |
| U03 | 26 active jobs without TTL, writer unattributed | B |
| U04 | 365-day VPR bucket lifecycle and retention/deletion-order questions | A, B |
| U05 | Parser discards GPA | A |
| U06 | Separate tailored-CV export query lacks pagination | B |
| U07 | Unsanitized SSR paste fallback | B |
| U08 | Source absence of CSP/framing/HSTS controls | B |
| U09 | Cookie attributes and inferred SDK token exposure | B |
| U10 | WAF inspection/body-rule/rate settings and intended contract | B |
| U11 | Interview-prep PII logging on reached paths | B |
| U12 | Unwired CV upload validator and server field limits | B |
| U13 | Gap/export owner-positive fixture deficiencies | B |
| U14 | Unmocked AWS fixture paths in isolated tests | B |

These are not 14 new confirmed production defects. U10 may be an intentional configuration; U03 may describe a separate job entity population. U13/U14 are instrument issues. U04's configured retention is already decisive against the S0b indefinite-retention conjunct, but its broader product-retention effects receive no verdict. No item enters the base-rate sample or silently expands a manifest verdict.

## Process findings

**Credential scope.** The retained IAM receipt places `presgen_user` in group `AdminAccess`, with AWS `AdministratorAccess`. C's STS read confirms the same principal in account `788159322332`. No genuinely read-only credential was supplied or provisioned; creating IAM credentials would itself violate the handoff's no-live-write rule. A and B report only read calls, and C issued only the prerequisite verifier reads and STS identity read. The restriction is **self-imposed, not enforced by IAM**. Residual risk is accidental or misdirected mutation with administrative authority; successful restraint in these runs does not provide an IAM boundary. No claim is made that an administrative group necessarily bypasses every possible organization-level deny.

**Mis-asserting reproduction artifact.** C independently gets **3 failed / 13 passed** from the four explicitly selected scratch files. One failure is the intentionally exposed GPA TypeError. The other two use a denial-status assertion to label empty 200 responses as “served cross-tenant data,” although their marker lists are empty. The gap owner-positive fixture is also empty, and the export owner-positive fixture is missing its intended artifact. These outcomes cannot be read as three production disclosure defects. Recommend splitting tests into authentication, ownership denial-contract, actual confidential-content disclosure and fixture-validity assertions; add owner-positive controls and an explicit VPR-export case. Express the known GPA failure with an appropriate expected-exception/reproduction contract. **Do not merely relax every empty-200 test to pass. No scratch assertion was changed in this audit.** [Fresh reproduction receipt](../evidence/astra-pass-c/C08-p1-reproductions.json).

**Rebased mutation ruling.** P1's isolated counts and single-failure baseline do not survive B's transport-controlled environment: the retained baseline has 46 failures, both-ownership mutation 47, status-only mutation 46, and two-spelling header mutation 52. C compared exact failure sets: both ownership checks add only the named cancel test, status-only adds/recoveries zero, and header fallback adds six with no recoveries. C also independently reran the historical one-handler comparison, reproducing 9/3 -> 10/2, and a poisoned status-only control, reproducing 403 -> 200 for a foreign pending job. Therefore **the narrow mutation-sensitivity gap survives rebasing**: the selected run has no additional failing assertion for the status guard even though the guard demonstrably changes access. “Zero test coverage” is too broad if interpreted as zero executed lines/branches or no tests anywhere; no coverage census was performed, and pre-existing failing tests can mask additional signals. The poisoned control returns foreign job metadata, not a full VPR document. [Failure-set comparison](../evidence/astra-pass-c/C09-mutation-log-comparison.json), [fresh poisoned control](../evidence/astra-pass-c/C10-targeted-controls.json).

C also retains its own unsuccessful instruments. Combining selected units and integration tests initially hit an unmocked CloudFormation setup path, blocked before transport. Wrapping all tests in one outer moto context then shared tables across cases. The correct rerun uses the integration fixture's supported table environment overrides and leaves each case's own moto context intact: **nine pass**. The original B S8 control's wrong sort-key prefix was retained but rejected; C02's corrected nonempty control governs. An auxiliary source-inventory extraction encountered a non-file historical citation and was regenerated. These failures are recorded, not recast as system defects or successful validations.

## Run metadata and validation

- Requested model/effort: GPT-6 Astra, high, with xhigh requested for disputed IDs. Session instructions identify Codex/GPT-6; selector and effort were not independently observable and no model switch is claimed.
- Prompt: `C/1`. Commit: `cea07992539c09724a4f05be3761f24b8f4e4d5f`. Branch: `tools/proof-harness`. The existing dirty worktree was preserved.
- AWS: account `788159322332`, region `us-east-1`, resource environment `devx`; REST stage is named `prod`. These names are not interchangeable. Prior detailed resource observations are dated September 13 UTC; C does not claim to have freshly scanned every resource.
- The required `verify_aws_state.py --mode deployed --env devx` passed. It checks one Lambda, two tables and a bucket prefix; it is not full deployment validation. Initial sandbox cache access failed; the approved rerun succeeded. STS identity was independently read in C.
- Fresh current checks: **58 selected unit tests passed; 9 P-05 integration tests passed**. Four main independent control batches and targeted model/identity/classifier/mutation controls passed. Expected red scratch/historical controls are evidence, not a release result. C did not rerun the full B mutation suites or claim a current full-unit-suite green baseline.
- Only audit Markdown/YAML/JSON artifacts were authored. No Python, frontend or infrastructure source was edited; no global formatter/fixer was applied to the audited dirty tree. No code/tests landed, so PROGRESS.md and plan.md were not changed. No subagents or external messaging were used. P1-VERDICTS.md prose was not opened.
- Input inventory covers A/B YAML and narrative records, both raw-receipt directories, the manifest/evidence register and P1 reproduction sources. Source inspection includes 67 citation excerpts plus relevant full control-flow/model paths. Hash coverage of every application Python file is distinguished from semantic inspection. Detailed resource inspection in C was of retained AWS receipts; live C operations were limited as described above.

[Run metadata and UTC timestamps](../evidence/astra-pass-c/run-metadata.json), [input receipt hashes](../evidence/astra-pass-c/input-receipt-inventory.json), [source excerpts](../evidence/astra-pass-c/C11-source-excerpts.json), [output validation](../evidence/astra-pass-c/validation.json). The filenames retain the September 13 handoff date; the user requested continuation on September 14 local time.
