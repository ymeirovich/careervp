# P1 — Adversarial validation

**Model: Fable 5, high effort. Fresh session. Run this FIRST.**
**Prerequisite: read `docs/handoff/2026-09-12-P0-COMMON.md` — it is binding,
especially §4 (required output table).**

Paste everything below the line into a new session opened at the repo root.
Do not summarize this conversation for it — the independence is the point.

---

You are validating a defect inventory produced by automated analysis of this
repository. Your job is **not** to agree with it. Your job is to determine, by
execution and direct reading, which claims are true, which are false, and which
cannot be decided without deploying.

A wrong finding here is expensive: it sends a solo developer down a multi-day fix
for a bug that does not exist, on a project that has already lost months to
exactly that. **Finding a false claim is the highest-value outcome of this
session.** Report false ones with the same energy you'd report true ones.

## Ground rules

1. If a command can answer the question, run it. Do not tell me what you think
   first.
2. Label every claim you make: **OBSERVATION** (command + output), **INFERENCE**
   (reasoned from observations), or **OPINION** (judgment).
3. Do not trust an assertion in the inventory because it carries a file:line
   citation. Open the file. Citations in this inventory were produced by agents
   and several are expected to be wrong.
4. Three verdicts, never two: **CONFIRMED**, **REFUTED**, **UNPROVABLE-STATICALLY**.
   "I could not check this" is never "this is fine."
5. Never recommend on a judgment call. Cost the options; the human decides.

## Calibration — the failure mode you are hunting

One finding in this batch was already proven false before you started, and it is
the template for what else may be wrong.

An agent reported: *"10 devx DynamoDB tables exist but NO CloudFormation stack
owns them — a rebuild would not recreate them."* It cited a real `make preflight`
FAIL and a real evidence JSON at `docs/evidence/preflight-20260809T171854-cea0799.json`.

It was wrong. `aws cloudformation get-template --stack-name CareerVpCrudDevx`
shows all 11 tables declared and owned. The actual bug is in the measuring
instrument: `src/backend/scripts/preflight.py:366` matches the resource type
`AWS::DynamoDB::Table`, but CDK's `TableV2` construct synthesizes
`AWS::DynamoDB::GlobalTable`. Nothing matched, so everything read as unmanaged.

That is the shape: **a confident, specific, cited, reproducible failure that is an
artifact of the instrument rather than the system.** It survived two layers of
analysis. Assume more of what follows is like it.

## Your input

Read `docs/handoff/2026-09-12-RECON-FINDINGS.md`. It contains ~100 findings
grouped SEV-0 through SEV-3, plus a "six root causes" table and a
"confirmed-good" list.

## What to do

### Tier 1 — the four that change the plan (do these first, in depth)

For each, reach a CONFIRMED/REFUTED verdict with reproduction evidence:

**S0a — `GET /jobs/{jobId}/artifacts/vpr/export` has no ownership check.**
Claimed live cross-tenant read. Verify: is the route actually registered and
deployed? Does `_read_artifact` really drop `user_id` on the `vpr` branch? Is
there an upstream guard the inventory missed (authorizer, resource policy, WAF)?
If you can safely construct the two-user test against `devx` without creating
real PII, do it — otherwise say exactly what deployment step would prove it.

**S0b — VPR status S3 fallback sits above the ownership check.**
Same treatment. Specifically check whether the 24h TTL premise holds:
does `jobs_repository.py:475` actually set a 24h TTL, is TTL enabled on that
table in AWS, and does the S3 object really outlive it?

**S11d — CV upload 500s whenever the parser extracts a GPA.**
This claims a *currently live, user-facing* breakage. `models/cv.py` declares
`gpa: float | None`; `save_cv` is claimed to pass a raw float to `put_item`
outside its exception catch. Verify by reading, then by actually calling the code
path with a GPA-bearing CV (a unit test or a local moto-backed test is fine —
this does not need a deploy). If true, this may be the single highest-impact live
bug in the repo. If false, say so loudly.

**S25 — the gap-analysis state machine has never advanced.**
Claimed: `update_state(..., user_id='')` where `user_id` is the partition key, so
the conditional write fails every time and is swallowed. Verify the key schema
claim against `application_repository.py`, then verify the empty-string argument
is really what's passed, then determine whether any *other* code path sets
`gap_questions_pending` (which would falsify the "never advanced" part even if
the call is broken).

### Tier 2 — sample the rest for base rate

You do not need to verify all ~100. **Randomly sample 12** findings across
SEV-1/2/3 — pick them yourself, do not let me steer you toward ones I suspect —
and verify each. Report the confirmed/refuted/unprovable ratio. That ratio is
what tells the human how much to trust the un-sampled remainder, which matters
more than any individual verdict.

Include at least two from the "confirmed-good (do not fix)" list — a false
*negative* (something declared safe that isn't) is more dangerous than a false
positive.

### Tier 3 — the security sweep the recon did NOT do

The recon was backend-heavy. It covered Lambda handlers, API Gateway routes,
DynamoDB access, and auth logic in depth. It did **not** systematically cover
every trust boundary in the pipeline. Do that sweep now, end to end:

1. **Browser / UI** — XSS sinks, `dangerouslySetInnerHTML`, the TipTap rich-text
   editor's paste sanitization (`components/RichTextEditor/`), CSP headers,
   token storage (inventory S12 flags a non-`Secure`, JS-readable ID token).
2. **Frontend input validation** — is anything validated client-side *only*?
   Every such field is unvalidated in reality.
3. **API Gateway** — request validators/models, WAF rules (note the body-size fix
   is devx-only, `waf_construct.py:20-42`), CORS (`cors_utils.py:6` holds
   per-request origin in a module global that only 20 of 35 handlers set),
   throttling, GatewayResponse ACAO wildcards.
4. **Lambda boundaries** — input bounds and output scrubbing on every handler;
   env var and SSM secret handling; what crosses into logs.
5. **DynamoDB** — expression injection, key construction from user input,
   encryption at rest (currently AWS-owned keys, no CMK), what PII sits in keys
   (the `knowledge` table uses `userEmail` as its partition key).
6. **S3** — presigned URL scope and TTL (inventory S0a/S0b both hand out
   presigned VPR URLs), bucket policies, and the two buckets with **no
   versioning** (`api_db_construct.py:256,746` — `cv_bucket`, `static_bucket`).
7. **SQS / Step Functions** — message integrity. Several workers take `user_id`
   verbatim from the message body; is the queue writable by anything outside the
   pipeline?
8. **CloudWatch** — who can read logs that the inventory says contain full CVs
   and full prompt context (S9)? Retention is 1 day on most groups — is that a
   control or an accident?
9. **Supply chain** — dependency audit, and whether CI can deploy without a human
   (inventory flags `deploy.yml:37` hardcoding `STACK_NAME: CareerVpCrudDev` on
   the push-to-main path, which would void P-28's human-only execute gate).

For each boundary: is validation/authorization present, absent, or unverifiable?
Cite. Absent findings here are as valuable as confirmed ones from Tier 1.

### Tier 4 — validate the premises of the other four sessions

P2–P5 are about to be run on the strength of framing that came from the same
unvalidated analysis. Check the load-bearing premises before they cost four
sessions of work:

- **P2's premise** — that ~35 findings reduce to "no single table authority +
  two key schemes," rooted at `api_db_construct.py:114` (`self.db =
  self.users_table`). Is that genuinely one root cause, or several unrelated ones
  bundled by a narrative?
- **P3's premise** — that `except Exception: pass` is the *default idiom* rather
  than a handful of cherry-picked instances. The claim is ~40 occurrences; count
  them and characterize honestly.
- **P4's premise** — that the test suite contains self-closing tests that pass
  without the code they claim to test. Spot-check: did **any** pre-existing test
  fail when commit `7cdc5e5` turned a swallowed write into a fatal 500? If tests
  did catch it, the owner's distrust of the suite is overstated and P4's scope
  should shrink.
- **P5's premise** — that the `knowledge` table is entirely dead (zero live
  readers, zero live writers). One grep settles it.

## Output

Per `P0-COMMON.md` §4, ending with the traceability table — for this session the
`Status` column carries the payload (`WORKING` only where you *proved* it).

Plus:

1. **Tier 1 verdicts** — four findings, each with verdict, the command/test you
   ran, its actual output, and what the human should do about it.
2. **Tier 2 sample** — table of 12 + the ratio, and your INFERENCE about what
   that implies for the ~85 un-sampled findings.
3. **Tier 3** — the trust-boundary sweep, as a table: boundary → control present?
   → evidence → severity if absent.
4. **Tier 4** — verdict on each of the four premises, with the explicit
   instruction to the human of the form *"P<n>'s scope should grow / shrink /
   stand, because…"*.
5. **The list of claims you could not decide without a deploy**, with the
   specific command or environment each would need. This list is a deliverable,
   not an apology — it tells the human what the next proving run must cover.

Do not fix anything. Do not edit source files. This session produces a verdict,
not a diff.
