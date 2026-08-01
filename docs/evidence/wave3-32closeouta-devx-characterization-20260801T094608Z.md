# Wave-3 step 3.2-CLOSEOUT-A — live characterization of `CareerVpCrudDevx`

**Date:** 2026-08-01 · **Stack:** `CareerVpCrudDevx` · **API base:**
`https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/` (resolved live from the stack's
`RawApiInvokeUrl` output, not copied from any document)

**Deploy of record:** `CareerVpCrudDevx` `UPDATE_COMPLETE` at `2026-08-01T09:12:51Z`; the
interview-prep API and worker Lambdas report `LastModified 2026-08-01T09:17Z`, so this
characterization runs against v3.0.0 backend code, not the 2026-07-26 code the stack carried
before this step.

**Companion files (same timestamp):**
- `…-20260801T094608Z.json` — per-wire status, latency, and response excerpt for every call.
- `…-20260801T094608Z.probe.py` — the exact probe that produced it.

This is the **before-picture for step 3.6**. It records what the deployed stack actually did.
It asserts nothing and fixes nothing; a failure here is data.

---

## 1. Why this baseline was taken with a probe rather than the two live-API suites

The prompt's deliverable was `uv run pytest tests/integration/test_full_pipeline_integration.py
tests/e2e/ -v` against devx. That command was run, twice, and is quoted verbatim in §2. It
**cannot** produce a characterization, because every authenticated wire fails at the first
hop for a reason that has nothing to do with D-H4/P-01: the helpers send the Cognito
**access token** and the API Gateway authorizer accepts only the **ID token**.

So the baseline below was produced by a standalone HTTP probe that walks the same wire
sequence with the token the authorizer actually accepts. The probe is committed alongside
this file. **No test file was modified to obtain it** beyond the two-line `application_id`
reconciliation this step was authorized to make.

---

## 2. The live-API suite run, verbatim

Against devx, `API_BASE=https://ymzhvcxod0.execute-api.us-east-1.amazonaws.com/prod/`:

```
============= 8 failed, 4 passed, 12 skipped, 4 warnings in 32.37s =============

FAILED tests/integration/test_full_pipeline_integration.py::test_full_pipeline_integration
FAILED tests/e2e/test_e2e_contract_gate_validation.py::test_e2e_contract_gate_validation
FAILED tests/e2e/test_e2e_error_handling.py::test_e2e_unauthorized_access_returns_401
FAILED tests/e2e/test_e2e_error_handling.py::test_e2e_invalid_input_returns_400
FAILED tests/e2e/test_e2e_error_handling.py::test_e2e_not_found_returns_404
FAILED tests/e2e/test_e2e_error_handling.py::test_e2e_prerequisites_not_met_returns_422
FAILED tests/e2e/test_e2e_happy_path_full_job_application.py::test_e2e_happy_path_full_job_application
FAILED tests/e2e/test_e2e_quality_gates.py::test_e2e_quality_gates
```

Representative failures — all 401, none reaching an artifact wire:

```
E  AssertionError: GET /users/me returned 401; expected [200];
   body={"error": "UNAUTHORIZED", "code": "UNAUTHORIZED", "request_id": "256edd05-..."}

E  AssertionError: All payload attempts failed for POST /users/me/cv; expected status 201.
   Attempts: payload={'text_content': ...} -> status=401;
             payload={'file_content': ..., 'file_type': 'txt'} -> status=401
```

**The 4 that passed** are `tests/e2e/test_vpr_async_polling.py` (4 tests) — they do not
authenticate against the live stack. **The 12 that skipped** are the `API_BASE`-gated and
`@pytest.mark.e2e` modules. **A skipped suite is not a passing suite, and a suite that 401s
before its first assertion is not a characterization.**

For contrast, the same command with `API_BASE` unset — the state of every prior Wave-3
session — reports `4 passed, 20 skipped`, which is how two broken fixtures stayed invisible.

---

## 3. What the deployed stack actually did, wire by wire

Walked with the ID token and the live request contracts. `✅` = behaved as the contract says.

| # | Wire | Result | Notes |
|---|---|---|---|
| 1 | `POST /auth/register` | **201** ✅ | |
| 2 | `POST /auth/login` | **200** ✅ | returns `access_token`, `id_token`, `refresh_token` |
| 3 | `GET /users/me` with **access_token** | **401** ❌ | `{"error":"UNAUTHORIZED","code":"UNAUTHORIZED"}` — what the suites send |
| 4 | `GET /users/me` with **id_token** | **200** ✅ | what the authorizer accepts |
| 5 | `POST /users/me/cv` | **201** ✅ | only with the `{cv_content,file_name}` shape |
| 6 | `POST /jobs` | **201** ✅ | only with `{title,company_name,description,url}`, `url` reachable |
| 7 | `POST /company-research/fetch` | **202** ✅ | `{"request_id":"comp-res-…","status":"processing"}` |
| 8 | `POST /gap-analysis/questions` | **200** ⚠️ | 10 questions in **27 965 ms** — against a 29 s API-GW cap; a prior run **504**ed at 29 222 ms |
| 9 | `POST /jobs/{jobId}/gap-responses` | **200** ✅ | 10 response ids |
| 10 | `POST /vpr/generate` | **202** ✅ | `request_id=416cdaed-…` |
| 11 | `GET /vpr/{vprId}/status` | **200 → `completed`** ✅ | terminal after 18 polls (~90 s) |
| 12 | `POST /cv-tailoring/generate` | **202 → `completed`** ✅ | terminal after 1 poll |
| 13 | `POST /cover-letter/generate` | **409** ❌ | `{"status":"upstream_required","missing":["vpr"]}` — though the VPR completed at #11 |
| 14 | `POST /interview-prep/generate` **with** `application_id` | **409** ❌ | same `upstream_required / missing:["vpr"]` — passes the identity guard, blocked on the same upstream |
| 15 | `POST /interview-prep/generate` **without** application identity | **400** ✅ | `{"error":"application_id/job_id is required","status_code":400,"code":"MISSING_REQUIRED_FIELD"}` |

### Async jobs

- **Completed:** VPR (`416cdaed-…`), CV-tailoring (`cv-tail-3784be33-…`), company research (202 accepted).
- **Never started:** cover letter and interview prep — both refused at submit with 409, so no
  worker ever ran. **The F1 interview-prep worker-path failure did not reproduce, because the
  request never got as far as a 202.** That is a different failure from the one F1 describes,
  and it is recorded as such rather than folded into F1.

---

## 4. What this proves about D-H4 / P-01

**Wire 15 is the v3.0.0 contract, confirmed live and exactly as the spec pins it.** The old
fixture shape — `{vpr_id, gap_response_ids}` with no application identity — is refused before
dependency resolution with the precise envelope `AC-P01-1` names: `error='application_id/job_id
is required'`, `status_code=400`, `code=MISSING_REQUIRED_FIELD`.

**Wire 14 proves the fixture reconciliation this step made was both correct and necessary.**
With `application_id` present the request passes the identity guard and reaches upstream
resolution; without it, it never does. The two fixtures could not have been left as they were.

**What is NOT proven:** no interview-prep artifact was generated end to end, because of the
finding in §5.1. The contract half of D-H4/P-01 is observed live; the generation half is not.

---

## 5. New defects found while running against the live stack — flagged, not fixed

### 5.1 `F-DEVX-1` — a completed VPR is never registered as a canonical artifact, so the whole downstream chain is unreachable

**Plain English:** you can generate a VPR and the app will tell you it finished, but the
cover-letter and interview-prep features will insist the VPR is still missing, forever. Via
the public API on devx there is no way to produce either artifact.

**Evidence.** VPR `416cdaed-…` reached `status: completed` at wire 11 with a full result body.
The canonical artifacts table then contains **no** VPR row:

```
careervp-artifacts-table-devx, applicationId = ea808c10-… (the application):  1 item
    artifactId=ARTIFACT#COMPANY_RESEARCH#ea808c10-…  artifactType=company_research
careervp-artifacts-table-devx, applicationId = 416cdaed-… (the VPR request id): 0 items
```

The completed VPR lives only in `careervp-jobs-table-devx`, keyed `job_id = 416cdaed-…`
(the *request* id) with `status=COMPLETED`. Note also that `POST /vpr/generate` returns
`"job_id": "416cdaed-…"` — echoing its own request id into a field named `job_id`, while the
actual application is `ea808c10-…`. Downstream upstream-resolution looks for a `vpr` artifact
under the application and finds nothing → `409 upstream_required, missing:["vpr"]`.

**ROOT CAUSE — diagnosed 2026-08-01, no longer just a symptom.** The VPR is not lost. It is
written to a **different physical table** than the one the readers query, because
`DYNAMODB_TABLE_NAME` — the variable `DynamoDalHandler` uses as `self.table_name` — resolves
to a different table per Lambda:

```
careervp-vpr-worker-lambda-devx          DYNAMODB_TABLE_NAME = careervp-users-table-devx
careervp-interview-prep-api-lambda-devx  DYNAMODB_TABLE_NAME = careervp-artifacts-table-devx
careervp-cover-letter-api-lambda-devx    DYNAMODB_TABLE_NAME = careervp-artifacts-table-devx
```

`save_vpr` / `get_vpr` use the **legacy `pk`/`sk` key grammar**
(`dynamo_dal_handler.py:306`, `:332`, `:355`). Across all 11 devx tables, the **only** one keyed
`pk`/`sk` is `careervp-users-table-devx`; the artifacts table is keyed
`applicationId`/`artifactId`. So:

```
 WRITE  vpr-worker  --save_vpr--> users-table      {pk: <application_id>, sk: ARTIFACT#VPR#v1}
                                  key grammar matches → SUCCEEDS (silently, in the wrong table)

 READ   interview-  --get_vpr---> artifacts-table  Key('pk').eq(<application_id>)
        prep api                  no 'pk' key on this table → ValidationException
                                       │
                                       └─ swallowed by `except Exception: return None`
                                          (artifact_dependency_utils.py:41-45)
                                               │
                                               └─ resolver reads that as "vpr missing"
                                                     └─ 409 upstream_required
```

**Verified directly:** for application `5ebd442d-…`, `careervp-users-table-devx` contains one
item at `pk=5ebd442d-…, sk=ARTIFACT#VPR#v1`. The artifacts table contains none. The VPR exists;
the reader is looking in the wrong place with a key name that table does not have.

**Why it never surfaced as an error:** the `except Exception: return None` in
`DynamoArtifactDependencyRepos.get_artifact` converts a hard schema mismatch into an ordinary
"upstream not ready", so a mis-wired table reads exactly like a user who hasn't generated a VPR.

**Why CV-tailoring appears to work:** `careervp-cvtailor-lambda-devx` has **no**
`DYNAMODB_TABLE_NAME` at all, so it never takes this read path.

**This is D-H2 / D-H4 exactly.** It is the legacy `pk`/`sk` grammar versus the canonical
`applicationId`/`artifactId` grammar, plus one env var meaning different things in different
Lambdas — the precise hazard 3.1-GREEN's row warned about when it recorded that
`ARTIFACTS_TABLE_NAME` and `COMPANY_RESEARCH_TABLE_NAME` point at different physical tables and
that "collapsing them would silently retarget reads". **The redesign's premise is confirmed by
live evidence, and this is the first observed user-facing cost of the split key authority.**
**Owner: D-H2/D-H4 key-authority work (`CoreRepository` / `TableRegistry`), not this step.**

**Inconsistency worth a second look:** CV-tailoring (wire 12) *succeeded* against the same
completed VPR. So cv-tailoring and cover-letter/interview-prep resolve their VPR upstream by
different means, and only the latter two fail.

**Confirmed on a second run (2026-08-01, after the table above).** Two alternative
explanations were tested and both are eliminated:

1. *"The probe never passed `application_id` to `/vpr/generate`."* `VPRGenerateRequest` accepts
   an optional `application_id`, so the VPR might simply have been unattributed. Re-run with
   `application_id` **passed**: VPR `81817fd3-…` again reached `completed`, and the artifacts
   table again held **0** VPR rows under the application (`5ebd442d-…`) and **0** under the VPR
   request id. `POST /cover-letter/generate` and `POST /interview-prep/generate` both returned
   `409 upstream_required missing:["vpr"]` exactly as before. **Passing `application_id` changes
   nothing; the defect is not a client omission.**
2. *"Only the VPR fails to register."* No — CV-tailoring `cv-tail-f2e4d203-…` reported
   `completed` on that same run and **also has no artifact row**. Across both runs the only
   artifact ever written to `careervp-artifacts-table-devx` is `company_research`.

3. *"This step's devx deploy introduced it."* Eliminated by a control run against
   **`CareerVpCrudDev`** — a stack this step never deployed, carrying v3.0.0 since 2026-07-27 via
   the pre-repoint CI job. Same result: VPR `2b239197-…` reached `completed`, and
   `careervp-artifacts-table-dev` holds **0** VPR rows under the application
   (`b6d9f04e-…`) and **0** under the VPR request id — only `company_research`. The control also
   reproduced the `access_token`→401 / `id_token`→200 split and 504'd `/gap-analysis/questions`
   **3 times out of 3**. **So F-DEVX-1, F-DEVX-2 and F-DEVX-5 are pre-existing and
   stack-independent; the 2026-08-01 devx deploy did not cause any of them.**

**Restated, wider than first recorded:** it is not that the VPR specifically fails to register.
The canonical artifacts table is essentially **not being populated by the generators at all** —
only the company-research path writes to it. Generators that report `completed` leave no
canonical artifact behind, and every consumer that resolves upstreams through that table
therefore sees an empty application.

### 5.2 `F-DEVX-2` — the live-API suites authenticate with the wrong token type

Both helpers take `access_token` from the login response:
- `src/backend/tests/e2e/e2e_helpers.py:118` — `login_token = require(login.data, 'access_token')`
- `src/backend/tests/integration/integration_helpers.py:152` — `require_field(login_response.data, 'access_token')`

The API Gateway Cognito authorizer accepts the **ID token**; the access token yields 401 on
every authenticated route (wires 3 vs 4 are the controlled comparison). **Not fixed here** —
changing it is beyond this step's "add `application_id`, add NOTHING else" instruction. Until
it is fixed, these suites cannot verify anything against a live stack.

### 5.3 `F-DEVX-3` — the live-API suites use stale request shapes on three wires

Independent of the token, these payloads cannot validate against the deployed contract:

| Wire | Helper sends | Deployed contract requires |
|---|---|---|
| `POST /users/me/cv` | `{text_content}` / `{file_content,file_type}` | `{cv_content,file_name}` — `cv_upload_handler.py:266-283` injects the authenticated `user_id` **only** for that shape; the helper shapes fail `CVParseRequest` on a missing `user_id` |
| `POST /jobs` | `{title,company,job_description}` / `{position,company,description}` | `JobCreateRequest` = `{title,company_name,description}` (`api_models.py:115-120`), and `url` is both **required** and live-fetched for reachability |
| `POST /company-research/fetch` | `{domain}` | `CompanyResearchRequest` = `{job_id, url?, company_name?}` |

### 5.4 `F-DEVX-4` — all four artifact status polls target routes that do not exist

The suites poll bare `/{id}`; the deployed API exposes only `/{id}/status`:

```
/vpr/{vprId}                 ['OPTIONS']              /vpr/{vprId}/status                 ['GET','OPTIONS']
/cv-tailoring/{cvTailoringId}['DELETE','OPTIONS','PATCH']  /cv-tailoring/{…}/status       ['GET','OPTIONS']
/cover-letter/{coverLetterId}['OPTIONS','PATCH']      /cover-letter/{…}/status            ['GET','OPTIONS']
/interview-prep/{interviewPrepId}['OPTIONS','PATCH']  /interview-prep/{…}/status          ['GET','OPTIONS']
```

A bare `GET /vpr/{id}` returns `403 {"error":"DEFAULT_4XX"}` — the API Gateway default
response for an unrouted method, easily misread as an authorization failure.

### 5.5 `F-DEVX-5` — `POST /gap-analysis/questions` runs at the API Gateway timeout

Observed across runs: **27 965 ms** (200), **29 222 ms** (504), then on a later run
**29 257 ms (504) → 29 218 ms (504) → 28 238 ms (200)**. That is **3 timeouts in 5 calls**; the
wire only succeeds when the model happens to come back a second or so under the 29 s API Gateway
integration cap. This is not occasional flakiness — it is a wire sitting on its ceiling. When it
504s the whole downstream chain silently empties (no gap ids → cover-letter and interview-prep
400 on `gap_response_ids must not be empty`), which is how a timeout here masquerades as a
validation error three wires later.

### 5.6 `F-DEVX-6` — CV parse 500s when the model returns a work entry with no company

With a CV giving no explicit employer, `POST /users/me/cv` returned **500**:

```
{"success":false,…,"error":"Failed to validate extracted data: 1 validation error for
 WorkExperience\ncompany\n  Input should be a valid string [type=string_type,
 input_value=None, input_type=NoneType]"}
```

`WorkExperience.company` is a required `str` (`careervp/models/cv.py`), and the extractor can
emit `None`. Model output is not defensively handled, so a thin CV is a 500 rather than a 4xx
or a degraded parse.

### 5.7 `F-DEVX-7` — `make deploy-devx` cannot deploy devx

**This is the defect that blocked step 5 of this prompt on the first two attempts.** Scope-lock
v2.6.0 requires devx to be built with `ENVIRONMENT=devx` **and** `-c p26_rehome_features=true`,
from first creation. The `deploy-devx` target added in `a8ef789` passes only `ENVIRONMENT=devx`;
`p26_rehome_features` is absent from `infra/cdk.json`, and `cdk` runs from `src/backend`, which
has no `cdk.json`. Without the flag the 76 P-26 feature resources synthesize into the **parent**
stack instead of `CrudFeaturesNestedStack`, with new logical ids, so CloudFormation tries to
create resources whose physical names the nested stack already owns:

```
❌ CareerVpCrudDevx failed: ToolkitError: ChangeSet 'cdk-deploy-change-set' on stack
   'CareerVpCrudDevx' failed early validation:
  - Resource of type 'AWS::Logs::LogGroup' with identifier
    '/aws/lambda/careervp-cvtailor-lambda-devx' already exists.
  … 27 log groups …
  - Resource of type 'AWS::CodeDeploy::Application' with identifier
    'careervp-api-canary-application-devx' already exists.
```

Synth comparison: **without** the flag → 32 log groups in the parent template, 0 in the nested
one. **With** the flag → 2 in the parent, 30 in the nested, logical ids matching the deployed
stack exactly (`CVParserLogGroup486ACA03`, …).

**Consequence for CI:** `db-redesign-checks.yml`'s `deploy-backend-dev` job calls
`make deploy-devx`, so **it will fail on every push to `db-redesign` that touches
`src/backend/**` or `infra/**`.** The a8ef789 repoint is not yet functional.

**Not fixed here.** The one-line fix is a Makefile/`cdk.json` change, and `infra/` edits belong
to 3.4. This step deployed by invoking the documented v2.6.0 command directly with the flag
(and with `allowed_origins` read from `infra/cdk.json`, so CORS was not altered).

---

## 6. Deploy record

```
✨  Total time: 1052.49s      EXIT=0
CareerVpCrudDevx   UPDATE_COMPLETE   2026-08-01T09:12:51Z
careervp-interview-prep-api-lambda-devx     LastModified 2026-08-01T09:17:09Z
careervp-interview-prep-worker-lambda-devx  LastModified 2026-08-01T09:17:08Z
```

264 resources; the P-23 canary deployment groups
(`CodeDeployDefault.LambdaCanary10Percent5Minutes`) account for most of the ~17 minutes.

**Correcting the record:** adversarial-review round 1 said the v3.0.0 backend change "is not
deployed". That was wrong about the code and right about devx. The code had been live on
`CareerVpCrudDev` since 2026-07-27 via the pre-repoint CI job (`careervp-interview-prep-api-lambda-dev`,
`LastModified 2026-07-30T10:27Z`); `CareerVpCrudDevx` was still on 2026-07-26 code until this
step. The accurate statement is "deployed to the retiring stack, never verified against the
intended one" — now no longer true: devx carries it as of 2026-08-01T09:17Z.
