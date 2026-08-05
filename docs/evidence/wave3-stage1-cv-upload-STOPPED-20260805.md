# Wave-3 Stage 1 — CV Upload: STOPPED at gate (a)

- **Date:** 2026-08-05
- **Branch:** `db-redesign` (Stage 0 committed at `2d55bc5`; Stage 1 step 1 in the working tree)
- **Environment:** AWS 788159322332 / us-east-1 / **devx** only. `dev` and `staging` untouched.
- **Status:** **STOPPED per the brief** — "STOP AND REPORT if (a), (c), (f) or (g) fails."
  Gate (a) fails for an environmental reason. Steps 4–6 (the irreversible half) were
  **not** started.

---

## 1. THE BLOCKER — gate (a) cannot pass: WAF blocks the upload at 8192 bytes

`POST /users/me/cv` with the required 40,108-byte docx returns **403**, and the
request never reaches the Lambda.

```
POST /users/me/cv   (40,108-byte docx, base64 -> ~53,478-byte body)
<<<HTTP 403 in 0.357846s>>>
{"error": "DEFAULT_4XX", "code": "DEFAULT_4XX", "request_id": "658ddf36-7a9b-4d90-b196-5933597145ce"}
```

**Stage 0's instrument is what identified it.** The access-log row shows the
request was rejected before any integration ran, and *not* by the authorizer:

```json
{"status":"403","httpMethod":"POST","path":"/prod/users/me/cv","responseLatency":"11",
 "authorizerError":"-","integrationStatus":"-","responseLength":"101"}
```

`integrationStatus: "-"` (no Lambda) with `authorizerError: "-"` (not auth) is
the exact signature Stage 0 added. Before Stage 0 this was an opaque 4xx.

### Isolation — it is body size, not content, route, or auth

| probe | body | result |
|---|---:|---|
| tiny `text_content` | ~50 B | **400** — reaches the handler |
| the docx, with `file_name` | ~53 KB | **403** |
| the docx, without `file_name` | ~53 KB | **403** |
| 30 KB filler `text_content` (no docx) | ~30 KB | **403** |
| `GET /users/me/cv` | — | **200** |

### The exact threshold: 8192 bytes

| body bytes | result |
|---:|---|
| 4,020 | 500 (reaches handler) |
| 7,020 | 500 (reaches handler) |
| 7,920 | 500 (reaches handler) |
| **8,120** | **500 — reaches handler** |
| **8,520** | **403 — blocked** |
| 10,020 | 403 — blocked |

### Cause, confirmed at the source

`careervp-core-waf-devx` is associated with **this** API:

```
careervp-core-waf-devx -> arn:aws:apigateway:us-east-1::/restapis/ymzhvcxod0/stages/prod
careervp-core-waf-dev  -> arn:aws:apigateway:us-east-1::/restapis/4xe2tdq8z6/stages/prod
```

Rule `[0] Product-AWSManagedRulesCommonRuleSet`, `OverrideAction: {"None": {}}`
(i.e. its rules are **active**, not counting). That managed group contains
`SizeRestrictions_BODY`, whose limit is 8 KB — matching the measured cutoff
exactly.

`get-sampled-requests` for that rule's metric confirms the blocks:

```json
{"uri": "/prod/users/me/cv", "method": "POST", "action": "BLOCK", "ts": "2026-08-05T23:10:55.891+03:00"}
{"uri": "/prod/users/me/cv", "method": "POST", "action": "BLOCK", "ts": "2026-08-05T23:10:55.393+03:00"}
{"uri": "/prod/users/me/cv", "method": "POST", "action": "BLOCK", "ts": "2026-08-05T23:09:15.486+03:00"}
```

### Why this matters beyond the gate

**CV upload has never been able to accept a real CV.** Base64 inflates by ~4/3,
so the ceiling is roughly a **6 KB binary file**. A one-page PDF or docx is
typically 30–100 KB. This independently explains the two facts the brief
supplied: the bucket's 24 objects average ~530 bytes, and every one of the 22
DLQ objects is a `.txt` of 113–740 bytes. **No genuine binary CV has ever been
uploaded to this system**, and none can be until this is resolved.

It also reframes N14's `/users/me/cv POST` row (86 calls, 51 4xx): a portion of
those 4xx are almost certainly WAF 403s, not contract failures.

**I did not change the WAF.** Raising or scoping `SizeRestrictions_BODY` is
precisely the "adjacent fix" the brief forbids, and it is a security-posture
decision for a human: the options (exclude the rule, scope it to
`/users/me/cv`, or move uploads to a presigned S3 PUT that bypasses the API
body entirely) have materially different risk.

---

## 2. What DID pass

### Gate (c) — parse produces work experience WITH company names — **PASS**

Not the blocker. With a valid CV under the ceiling:

```
POST /users/me/cv  <<<HTTP 201 in 4.215429s>>>
cv_id  : 6077ad2e-929b-4e5e-a448-c12ca6b9a7da
status : parsed
name   : Jane Doe
experience entries:
   company='Integration Labs Ltd'   role='Senior Backend Engineer'  duration='2021 - Present'
   company='Northwind Software Ltd' role='Backend Engineer'         duration='2018 - 2021'
```

No F-DEVX-6 null-company 500. (F-DEVX-6 is nonetheless real and is what explains
the single unmatched DLQ object — see §3.)

### Gate (f) — `GET /users/me/cv` still lists the CV — **PASS**

This was flagged as "the single most likely thing to break", and it is the one
the repoint actually had to get right:

```
GET /users/me/cv  ->  HTTP 200
  cvs returned: 1
   cvId=6077ad2e-929b-4e5e-a448-c12ca6b9a7da  full_name='Jane Doe'
```

### Step-2 rehearsal — readers healthy, no regressions

All list/read endpoints after deploy #2, and Lambda error counts for every
repointed reader:

```
/users/me/cv 200   /cover-letters 200   /interview-preps 200
/cv-tailorings 200 /vprs 200            /users/me 200

cv-parser 0 errors    user-api 0 errors    cover-letter-api none
interview-prep-api none   gap-api none     cvtailor none
vpr-worker none           ai-assist none
```

### Gate (b) — **not applicable yet, by design**

Counts before → after the upload: users-table CV# **31 → 32**, cvs-table
**28 → 29**. Both incremented because **both writes still run** — that is exactly
what step 2 requires ("verify every reader still finds CVs WHILE BOTH WRITES
STILL RUN"). "Exactly one table" is a step-4 outcome and was not attempted.

### Gates (d), (e), (g), (h), (i) — NOT REACHED

Not attempted, because gate (a) is a stop condition:
- (d) worker deleted / no orphaned notification — step 6
- (g) every downstream reader proven per reader — needs a full journey
- (h) forced cvs-table write failure returns 5xx — step 4
- (i) zero CV# rows in users-table — step 6

---

## 3. Stage 1.1 — diagnosis (complete)

### The 22 DLQ messages

Read non-destructively (`receive-message --visibility-timeout 0`); **nothing was
deleted**. All 22 are `aws:s3` `ObjectCreated:Put` on
`careervp-devx-cvs-use1-747cad`, across 4 users, all `.txt`, 113–740 bytes.

| user | messages | CV rows (users / cvs) |
|---|---:|---|
| `f44804d8-…` (p30-smoke) | 6 | 6 / 6 |
| `8428d4e8-…` (harness) | 13 | 12 / 12 |
| `a4f8b498-…` (e2e) | 1 | 1 / 1 |
| `848834a8-…` (ymeirovich) | 2 | 2 / 2 |

### The correlation — **PASSES**

Per-user: **4 of 4** users have CVs. I also ran the stricter per-object check,
matching each DLQ message's S3 key against `source_file_key` on the stored CVs:
**21 of 22 objects have a CV row in BOTH tables.**

The single exception is explained, not hand-waved. I fetched the object:

```
8428d4e8-…/cdc0b0b2-4e55-46ce-b1a6-0cf6d4f91c5f.txt   113 bytes
---
Jane Doe
Senior Backend Engineer
Built Python APIs, AWS Lambda workloads, DynamoDB data models, and CI pipelines.
```

No `WORK EXPERIENCE` section and no named employer — exactly what
`tests/e2e/e2e_helpers.py:206-207` documents the parser as rejecting
("`WorkExperience.company` is a required str, which 500s the upload"). Its
740-byte sibling, which *does* carry named employers, persisted normally. Since
the S3 put (`cv_upload_handler.py:132`) happens **before** `parse_cv`
(`:154`), a rejected CV still leaves an object behind. This is F-DEVX-6
behaviour, **not** work the worker dropped.

⇒ **Redundancy proven on real traffic.** The synchronous path covered every
upload the worker dropped.

### Root cause — confirmed by live reproduction, not inference

Invoking the worker with a real S3 event from the DLQ:

```
FunctionError: Unhandled
errorType   : KeyError
errorMessage: 'httpMethod'
  cv_upload_handler.py:383 in lambda_handler -> app.resolve(event, context)
  aws_lambda_powertools/event_handler/api_gateway.py:2612 -> self.current_event.http_method.upper()
  data_classes/common.py:237 -> return self["httpMethod"]
```

Wiring confirmed: handler `careervp.handlers.cv_upload_handler.lambda_handler`
(the same one bound to `POST /users/me/cv`), **no** event-source mapping, an S3
bucket notification with principal `s3.amazonaws.com`, timeout 300s.

Current metrics: **72 invocations / 72 errors** — 100%. (The audit's 66 was an
earlier snapshot; the brief's 72 is right.)

### "Predates the window, or dies before it can log?" — **PREDATES**

Settled by measurement. The log group has `retentionInDays: 1` and
`storedBytes: 0`, and the newest DLQ event is 2026-08-03. The fresh invoke above
produced a full log stream immediately, including — via Stage 0's new decorator —

```json
{"level":"ERROR","message":"request failed with an unhandled exception","status_code":500,
 "service":"careervp-cv-upload-worker","exception_name":"KeyError"}
```

So it logs fine; the 14-day silence was retention expiry, not a pre-logging death.

---

## 4. Stage 1.2 — decision: **DELETE** (not yet executed)

The rule was applied, not re-litigated. All three overturn conditions checked:

| condition | finding |
|---|---|
| 1.1 correlation fails? | **No** — it passes (§3). |
| a producer of bucket objects bypassing the API handler? | **No.** `cv_upload_handler.py:132` is the only `put_object` to the CV bucket; `export_handler.py:427` and `vpr_worker_handler.py:486` write other buckets. `user_handler.py:273` only `delete_object`. The frontend posts to `/users/me/cv` (`api/methods.ts:138`); its only presigned references are downloads. |
| any CV originating from the worker? | **No** — 72/72 lifetime failures. |

**RECORDED, as required.** The worker's timeout is **300s** against the API
Lambda's **60s**, so it may well have been intended as the large-file path.
Deleting it breaks nothing today, because it has never once succeeded — but it
converts *"large CVs accidentally broken"* into *"large CVs unsupported."*

That trade-off now collides with §1: the WAF ceiling means large CVs are
**already** unsupported at the edge, 6× below a typical docx. Whoever resolves
the WAF decision should settle the large-file story at the same time — a
presigned-S3 upload path would answer both, and would be the deliberate version
of the feature this deletion removes.

**Not executed.** Deleting the worker is step 6, in the irreversible half.

---

## 5. Stage 1.3 — step 1 done, step 2 verified, steps 4–6 NOT started

### Key authority (no new alias, per scope-lock §4)

`table_registry.resolve_cv_table_name()` resolves `CVS_TABLE_NAME` — an env key
that already exists and is already set on **26 of 31** devx Lambdas.
Deliberately **not** a precedence chain: a fallback to
`USERS_TABLE_NAME`/`TABLE_NAME` is what let readers keep silently resolving to
the old home. Added alongside: `cv_key_condition()` and `canonical_cv_key()`.

### Readers repointed

| reader | was | now |
|---|---|---|
| `user_handler._list_user_cvs` | `TABLE_NAME` + **legacy pk/sk condition** | CV table + `userId` condition |
| `user_handler.get_user_cv` / `delete_user_cv` | `TABLE_NAME` | CV table |
| `cover_letter_handler._load_user_cv` | **USERS first**, then CVS | CV table first |
| `interview_prep_handler` context | CVS, then artifacts dal | CV table first |
| `gap_handler` | CVS **or USERS** | CV table only |
| `vpr_worker_handler` | `DYNAMODB_TABLE_NAME` (users) | CV table |
| `cv_tailoring_handler` ×2 | artifacts dal | CV table |
| `ai_assist_handler` | `CVS_TABLE_NAME` = **users** | env repointed to cvs |

Env-only change was ai-assist's `CVS_TABLE_NAME` (users → cvs). Its
**`ARTIFACTS_TABLE_NAME` was deliberately left on users-table** for Stage 4, as
instructed.

### Two new defects found while repointing

1. **ai-assist had no IAM grant on `cvs_table`.** Repointing the env var alone
   would have produced `AccessDeniedException` at runtime — on the one Lambda
   with zero invocations and no test, i.e. invisible. Grant added in the same
   change. This is the third-mistake risk the audit predicted (§4.3), caught
   before deploy rather than by it.
2. **`vpr_worker_handler:411` defaulted to a hardcoded `careervp-users-dev`** —
   a **cross-environment** read: a devx worker would have read a **dev** table
   had `DYNAMODB_TABLE_NAME` ever been unset. Removed by the repoint.

### Census correction (third one)

`CVTailoringLogic` — census row 7 (`cv_tailoring_logic:200`) — is constructed
**only in tests**; `grep 'CVTailoringLogic('` finds no production call site. It
is not a live CV reader, so it was left alone rather than churned.

### Verification

`ruff format` / `ruff check` clean; `mypy careervp --strict` clean (137 files);
**1425 unit passed**, 15 skipped, 4 xfailed (baseline 1419 → 1424 after Stage 0
→ 1425 with the new regression test); **154 infra tests passed**.
Deploy #2: `UPDATE_COMPLETE`, 863.57s.

Test fallout was real and was fixed honestly rather than papered over: 59 tests
failed on the first run because `resolve_cv_table_name()` requires
`CVS_TABLE_NAME`. `tests/conftest.py` now sets it globally (matching the name
the existing `moto_cvs_table` fixture creates); the remaining 11 were tests that
encoded "the CV lives in the users table" and were updated to seed the new home.

### New regression test (1.4)

`test_list_user_cvs_surfaces_query_failure_instead_of_an_empty_list` pins the
trap found in Stage 0's census: a failed CV query must raise, never return
`200 {"cvs": []}`. Written by patching the module's boto3 boundary — my first
attempt patched a *different* client instance than the handler builds and so
passed vacuously, which is the same "tests that don't call the way a consumer
calls" failure the brief warns about.

---

## 6. What a human must decide before Stage 1 can finish

1. **The WAF `SizeRestrictions_BODY` decision (blocks gate (a) outright).**
   Exclude the rule / scope it to `/users/me/cv` / move to presigned S3 upload.
   Security posture, not a mechanical fix.
2. **Whether to proceed into steps 4–6** once (1) is resolved. Steps 1–2 are
   deployed and reversible; 4–6 delete the users-table CV rows and make the
   cvs-table write fatal.
3. **F-DEVX-6** (null-company → 500) remains open and out of scope, but it is
   what produced the one unmatched DLQ object.

## 7. Still true and unfixed (flagged, not fixed)

- The D-H2 ratchet does not scan `careervp/dal/`; `dynamo_dal_handler.py:533`
  still **writes** `applicationId = user_id`.
- `careervp-artifact-cleanup-lambda-devx` now errors on every scheduled run
  (intended — it has no `DYNAMODB_TABLE_NAME`; the config fix is P3.2).
- The 22 DLQ messages are **still in the queue**, undrained, as required
  (1.5: drain only after the path works).
