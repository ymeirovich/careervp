# Issues Tracker

Known issues surfaced during the redesign that are **real but deliberately deferred** — each
is parked here rather than silently absorbed into whatever step happened to find it.

This file is *not* the contract. Nothing here is a scope-lock clause, and nothing here is a
commitment. It is the holding pen: an issue leaves this file either by being promoted into a
scope-lock clause (via the §0.3 amendment protocol) or by being closed with a reason.

| Field | Meaning |
|-------|---------|
| **Found** | When and by which step the issue surfaced |
| **Severity** | `high` (will bite a real user), `medium` (will bite an operator), `low` (hygiene) |
| **Disposition** | What we decided to do *for now*, and why that is defensible |
| **Trigger** | The condition that should force this back onto the table |

---

## I-01 — No presigned-upload route: CV upload is inline base64 through Lambda

- **Found:** 2026-07-12, step 0.64b (running the P-30 smoke harness against the custom domain).
- **Severity:** medium — becomes **high** the first time a user uploads a large scanned CV.
- **Status:** OPEN, deferred.

**What is true.** The API has no presigned-upload endpoint. `POST /users/me/cv` takes the file
inline as base64 `cv_content` and the handler performs the S3 `put_object` itself
(`src/backend/careervp/handlers/cv_upload_handler.py`). All 58 deployed routes were enumerated:
no upload/presign surface exists anywhere. The only presigned URLs in the system are for
**download** (`export_handler`, `vpr_status_handler`, and frontend-contract rule 8).

**Why it matters.** Inline base64 through API Gateway + Lambda inherits two hard ceilings:
API Gateway caps the request payload at **10 MB**, Lambda at **6 MB** synchronous — and base64
inflates the payload by ~33%, so the *effective* file limit is roughly **4.5 MB**. A scanned-PDF
CV clears that easily. The failure mode is a hard 413 with no graceful path, and it is invisible
in dev because test CVs are small.

**How this was discovered.** P-30's 4th wire was written as `presigned_upload` against an endpoint
that never existed and was never planned — it 404'd identically on the custom domain *and* on the
raw `execute-api` URL. The wire was repointed to the real upload path (scope-lock v2.3.0). That
fixes the *canary*; it does not fix the *ceiling*, which is this issue.

**Disposition.** Not fixed now, deliberately. A presigned-PUT upload path is a real feature
(new route + handler + bucket CORS + a frontend change to do the direct PUT), and Wave 0 is
guardrails-and-truth. P-30 is a deploy-canary clause, not a feature clause — building a feature
inside it would be exactly the scope smuggling the contract exists to prevent.

**Trigger — promote to a clause when any of these is true:**
- a real user hits the ~4.5 MB ceiling (watch for 413s on `POST /users/me/cv`), **or**
- OCR / scanned-PDF ingest is picked up (it is V2-deferred today, and it *guarantees* large files), **or**
- Wave 4's NFR-SCALE work is scheduled — this belongs in that conversation.

---

## I-02 — The P-30 upload wire has a per-run side effect: an AI parse and a persisted CV row

- **Found:** 2026-07-12, step 0.64b (implementing the wire-4 repoint).
- **Severity:** low now, medium once the canary runs on every deploy as intended.
- **Status:** OPEN, accepted for now.

**What is true.** `POST /users/me/cv` does not just write to S3 — it then calls `parse_cv`, which
invokes the AI parser, and persists a CV row. So every P-30 smoke run costs one Haiku parse and
leaves a CV behind for the smoke user. The dev smoke user already carries **13** accumulated CVs.

**Why it is accepted.** This *is* the real user write path, and a canary that does not exercise
the real path is a canary that lies. The cost is genuinely small (one Haiku call on a ~200-byte
document). The pollution is confined to one synthetic user and is not user-visible.

**Why it is still an issue.** P-30's whole point is "baseline green **before and after** each
change" — so the run count is 2× every risky deploy, forever, and the CV rows grow without bound.
An unbounded-growth test fixture is the kind of thing that is free until it is suddenly not.

**Trigger — fix when any of these is true:**
- the smoke harness is wired into CI/CD to run automatically (right now it is human-invoked), **or**
- the smoke user's CV count starts affecting the read-back assertion's latency, **or**
- the AI-parse cost shows up in the P-32 cost-anomaly monitor.

**Likely fix.** A teardown step (`DELETE` the CV the wire just created — note this needs a delete
route that may not exist), or a dedicated smoke tenant with a short S3/DynamoDB TTL.

---

## I-03 — "Deploy Frontend" does not deploy the frontend

- **Found:** 2026-07-12, step 0.64b (getting the workflow green for O-9).
- **Severity:** low — naming/expectation hazard, not a defect.
- **Status:** OPEN, cosmetic.

**What is true.** After the 3d28d7d rewrite, `.github/workflows/deploy-frontend.yml` runs
typecheck + unit + integration + `next build`. It does **not** deploy: Amplify deploys itself from
its own branch webhook. The workflow is a *build-validation gate*, and its old S3-sync deploy path
(which is what had been failing since 2026-05-03 with `Credentials could not be loaded` — it used
OIDC creds that were never wired up) was correctly deleted.

**Why it matters.** A workflow named "Deploy Frontend" that is green will be read by a future
operator as "the frontend deployed." It did not. That misreading is exactly how a bad build reaches
users under a green check.

**Disposition.** Renaming a workflow is trivial but touches CI identity (branch protection required
checks reference workflow names), so it is not worth doing mid-O-9. Rename to
`Validate Frontend Build` when CI required-checks are next touched.

**Also noted (trivial):** the workflow emits a Node 20 deprecation warning
(`actions/checkout@v4`, `actions/setup-node@v4` are being forced onto Node 24). Harmless today;
bump the action majors when convenient.

---

## I-04 — The frontend build gate does not run on feature branches

- **Found:** 2026-07-12, step 0.64b.
- **Severity:** low.
- **Status:** OPEN.

**What is true.** `deploy-frontend.yml` triggers on `push` to **main** (path-filtered to
`src/frontend/**`) plus manual `workflow_dispatch`. So frontend regressions on a feature branch are
not caught by *this* workflow until they land on main — the point at which Amplify also picks them up.

**Why it is not urgent.** Frontend typecheck/unit/integration are covered on branches by the other
CI workflows (`ui-upgrade-checks`, `db-redesign-checks`), so the coverage gap is narrower than it
looks. This is about the *gate* being main-only, not about the checks being absent.

**Trigger.** Fold into the same pass as I-03 (CI required-checks review).

---

## I-05 — A backend unit test is red on `db-redesign`: AI-assist reports 0 tokens

- **Found:** 2026-07-12, step 0.64b (running the mandatory backend suite before committing).
- **Severity:** medium — it is either a real metering bug or a stale test, and we do not yet know which.
- **Status:** OPEN, **not** introduced by 0.64b.

**What is true.** `tests/unit/test_ai_assist_handler.py::test_success_returns_200_with_resolved_context`
fails on `assert body['tokens'] >= 1` with `assert 0 >= 1`. The rest of the suite is green
(1330 passed / 1 failed). Confirmed pre-existing by stashing the 0.64b changes and re-running on a
clean tree — it fails identically, so it is not fallout from the smoke-harness work.

**Why it matters — and why it should not just be silenced.** The assertion is about **token
metering**, and Q-10 ("real token metering; retire the `len/4` estimate") is a T1 launch-blocker
clause tied to NFR-COST-1 and the 91% margin target. A handler reporting `tokens: 0` is exactly the
symptom Q-10 exists to eliminate. So the honest reading is: this is either (a) the AI-assist path
genuinely not metering tokens — in which case it is a real Q-10 defect wearing a test's clothes —
or (b) a test whose mock stopped supplying a usage block. Those have very different fixes, and
guessing between them is how a cost bug ships.

**Disposition.** Left red, deliberately, and surfaced here rather than fixed inside an unrelated
step (0.64b is the O-9/custom-domain slice; fixing a metering bug in it would be scope smuggling —
and "make the test pass" is the specific temptation to avoid until (a) vs (b) is settled).

**Trigger.** Diagnose before Q-10's step runs — Q-10 cannot be evidenced as done while this is red.
Start by checking whether the handler reads a real `usage` block from the Anthropic response or
still falls back to an estimate.
