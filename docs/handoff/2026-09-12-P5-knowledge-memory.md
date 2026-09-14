# P5 — Cumulative career memory & vector search architecture

**Model: Opus 5, xhigh effort (architecture) → hand the go/no-go to Fable 5, high.**
**Prerequisite: read `docs/handoff/2026-09-12-P0-COMMON.md` first — it is binding.**

This is the one **greenfield** design in this package. Everything else is
remediation. Treat it accordingly: it is not a launch blocker and must not be
allowed to become one.

---

## The product idea

The owner's intent, in their words:

> *"I thought that gap analysis were stored there for future use. E.g. gap
> answers from Job 1 are utilized by Job 20, allowing Job 20 questions to be a
> deeper analysis because it already knows the information of Job 1-19."*

That is **cumulative career memory**: every gap answer, every tailoring decision,
every verified achievement the user supplies becomes durable knowledge that makes
the *next* application better. Application 20 should not ask what application 3
already learned.

Strategically this is the strongest moat in the product — it is the one feature
that gets better with use and cannot be replicated by a competitor's first
session with a new user. It is also, today, entirely unbuilt.

## Current state — verify each of these before designing

**OBSERVATION (verify independently):** the `knowledge` table exists in CDK at
`infra/careervp/api_db_construct.py:428-465`:

- partition key `userEmail` (STRING), sort key `knowledgeType` (STRING)
- GSI `entity-index`: pk `knowledgeType`, sk `entityId`, projection ALL
- TTL attribute `expiration`, 365-day retention, PITR enabled

**And it is completely dead.** `knowledge_base_handler.py` and
`dal/knowledge_repository.py` have zero infra references; `GET /knowledge-base`
is actually served by `company_research_handler.py:55,305`. The table has **zero
live readers and zero live writers**. Confirm this yourself before proceeding —
if it is wrong, the whole design changes.

Three problems with the existing schema for the stated purpose, which you should
verify and then either accept or overturn:

1. **`userEmail` as partition key.** Every other table keys on `userId` (the
   Cognito `sub`). This both fragments identity and puts PII in a key — it
   propagates into logs, metrics, and index names, and it breaks if a user
   changes their email.
2. **`userEmail` + `knowledgeType` yields one row per (user, type).** The stated
   use case needs *many facts per type per user* — 19 jobs' worth of gap answers
   is not one row. The current schema cannot hold the data the feature needs.
3. **365-day TTL on career facts.** A verified achievement from 2024 is still
   true in 2027. Question whether TTL belongs here at all, or only on
   derived/cached entries.

Since the table is dead and holds no data, **you may redesign it freely.** That
is a rare luxury in this codebase; use it.

## Part 1 — The knowledge model (design this first, independent of vectors)

Before any vector question, answer: **what is a unit of knowledge here?**

- What entity types matter? Candidates: verified achievement, skill with evidence,
  employment fact, gap answer, user preference/voice, rejected phrasing. Derive
  these from what the app actually collects — read `logic/gap_analysis.py`,
  `models/cv.py`, `models/vpr.py` — don't invent a taxonomy.
- **Provenance is mandatory.** Every fact must record where it came from (which
  application, which gap question, user-asserted vs. CV-parsed vs. LLM-inferred)
  and when. This is not optional bookkeeping: the FVS validator
  (`logic/fvs_validator.py`) exists to prevent hallucinated claims reaching a CV,
  and a memory system that launders an LLM inference into an apparent fact would
  defeat it. Design the trust tier into the record.
- **Contradiction and correction.** The user says "I led a team of 3" in
  application 2 and "a team of 8" in application 15. What happens? Last-write-
  wins, both retained with recency, or surfaced for user confirmation? This is a
  product decision — present the options with costs, don't pick silently.
- **Right to delete.** A user deleting their account or a specific fact must
  actually remove it, including from any index. Design for this now.
- Key schema, GSIs, access patterns, and item-size budget, given DynamoDB's 400KB
  item limit.

## Part 2 — Should vector search be used, and how?

**Verified facts (2026-08-05 GA — re-verify, this is a month old and moving):**

- DynamoDB native vector search is GA in all commercial regions + GovCloud.
- Up to **4,096 dimensions**; Cosine, Euclidean, and Dot Product distance.
- **Inline filtering** on exact-match attributes inside the vector query — this
  matters enormously here, because every query must be scoped to one `userId`.
- Single-digit-ms latency, 99%+ recall claimed.
- Billing: per byte with a **1KB minimum** per write and per search, plus
  per-GB-month index storage **on top of** normal table charges. A 768-dim vector
  is ~3KB.
- **⚠️ CloudFormation does NOT support the `VectorIndexes` property.** The index
  must be added via the `UpdateTable` API after table creation — in CDK, via an
  `AwsCustomResource`.

That last point is the crux, and it is a governance problem specific to this
project, not a generic inconvenience:

> This project's entire deploy safety model is **P-28**: automation may only
> `CreateChangeSet`; a human executes it after reviewing a machine-parsed
> `DescribeChangeSet` Replacement report (`make review`, GO/READ/STOP). A vector
> index created by an `AwsCustomResource` is **invisible to that review** — it
> cannot be inspected for `Replacement: True`, and a change to it will not appear
> in the change set the human approves.

Address this head-on. Options to cost out (at minimum):

- **(a) Defer** until CloudFormation supports `VectorIndexes` natively. Cheapest,
  and the index is additive so nothing is lost by waiting.
- **(b) `AwsCustomResource`** with an explicit, documented P-28 carve-out and a
  compensating control — e.g. a `preflight` premise that asserts the index exists
  with the expected dimensions and distance function, so drift is detected even
  though change-set review can't see it.
- **(c) Human-run one-time `UpdateTable`**, recorded as a P-29-style evidence
  artifact, treated like the other human-gated steps this project already has.
- **(d) Don't use DynamoDB vectors at all** — keyword/GSI retrieval, or a
  different store. Argue this honestly; for a corpus of a few hundred facts per
  user, **exact retrieval by type and recency may genuinely beat semantic search**
  and costs nothing new. Do not let novelty win on its own.

Then the retrieval design, if vectors survive the analysis:

- Which embedding model, and where it runs. Note the project's existing model
  policy in `CLAUDE.md` (Sonnet for strategic, Haiku for template work) and its
  91% margin target — embedding every gap answer has a real per-user cost.
  Compute it.
- What text gets embedded — the raw answer, a normalized fact, or a summary?
- How `userId` scoping is *enforced*, not merely intended. Given this codebase
  just produced two live cross-tenant leaks, a retrieval path that could return
  another user's career facts into an LLM prompt is the highest-severity bug this
  feature could introduce. Specify the guard and the test that proves it.
- How retrieved facts enter the prompt **without** becoming an injection vector.
  The inventory's S26 documents that user free-text already reaches prompts
  undelimited, and that `gap_analysis.py:281-286` concatenates system and user
  prompts into a single user-role message. Retrieved memory is user-authored text
  being replayed into a privileged position — this is strictly worse. Design the
  containment.

## Part 3 — Phasing

Give a phased plan where **every phase ships value independently**:

- **Phase 0** — schema only. Get the knowledge model right and start *writing*
  facts (from gap answers, at minimum) even if nothing reads them yet. This is
  the cheap, high-value move: data accumulates from day one, and a corpus that
  exists is what makes Phase 2 possible later. Missing this now means the feature
  is a year behind whenever you do build it.
- **Phase 1** — non-vector retrieval. Exact/recency/type-scoped reads feeding gap
  analysis. Prove the product hypothesis (do application-20 questions actually get
  better?) before paying for embeddings.
- **Phase 2** — vector index, only if Phase 1 shows retrieval quality is the
  binding constraint.

State plainly which phases are **post-launch**. The owner's stated timeline is
"immediate/overdue" and V1 scope is already fixed; this feature is not in V1
scope. **Phase 0 is the only part that has a claim on pre-launch attention**, and
only because writing facts now is nearly free and not doing it is irreversible.

## Output

Per `P0-COMMON.md` §4, ending with the traceability table. For this session the
ADDITIONS list is the main payload — every proposed component with its cost and
the requirement it serves.

Plus:

1. The knowledge model (Part 1), including the contradiction-handling decision
   presented as options.
2. The vector go/no-go with all four options costed, **including the P-28
   governance conflict and your proposed compensating control**.
3. The phased plan with an explicit pre-launch / post-launch line.
4. The `userId`-scoping guarantee and the test that proves it.
5. The prompt-injection containment design for replayed user text.

## Constraints

- **Design only. No implementation in this session.**
- Re-verify the vector-search facts above against current AWS documentation —
  they were gathered 2026-09-12 and the feature GA'd 2026-08-05. If anything has
  changed (especially CloudFormation support), the recommendation may change with
  it.
- Do not let this feature become a launch blocker. If your analysis concludes it
  should be fully deferred to post-launch, that is a completely acceptable
  answer — say it clearly.

## Handback

The go/no-go on Part 2 goes to **Fable 5, high effort**, with one question:
*"For a pre-launch app with zero users, an overdue timeline, and ~100 open
defects, is any part of this worth doing before launch — and if so, exactly which
part and why?"* The default answer should be "Phase 0 only"; make your write-up
good enough that Fable can disagree with that on evidence.
