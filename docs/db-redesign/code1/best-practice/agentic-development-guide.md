# Agentic Development Guide — CareerVP

**Purpose:** a working reference for Claude Code (or any coding agent) to consult when authoring **specs, tests, and workflows** for CareerVP. It is not auto-loaded — hand it to the agent explicitly at the start of a task (e.g. *"Read `agentic-development-guide.md`, then write the spec for X"*).

**Companion docs:** [`careervp-architecture-v2.md`](./careervp-architecture-v2.md) (as-built system + target architecture), [`careervp-architecture-deepdive.md`](./careervp-architecture-deepdive.md) (per-domain analysis), [`redesign-runbook.md`](./redesign-runbook.md) (executable migration). This guide tells you *how* to work; those docs tell you *what the system currently is*.

**Machine-readable companion:** [`agentic-development-guide.yaml`](./agentic-development-guide.yaml) — same content as structured data, for an agent to parse programmatically.

## Confidence tiers

Every directive below is tagged:

- 🟢 **Verified** — confirmed against live primary-vendor documentation (Anthropic, OpenAI, AWS) through adversarial multi-agent verification (3-vote consensus, majority-refute kills the claim). Two research passes, 217 agents, 27 questionable claims explicitly rejected and excluded.
- 🟡 **Practitioner guidance** — grounded in real, current vendor documentation (fetched and read), but not run through the same adversarial verification pipeline — usually because the specific numbers (rate limits, concurrency defaults) change often enough that you should confirm them against the live docs before relying on them.

Two claims were explicitly investigated and **rejected** — do not act on them if you encounter them elsewhere: (1) that Amazon Bedrock AgentCore has exactly three capabilities (Runtime/Memory/Gateway) — the real structure has more nuance; (2) that AWS names prompt/token length as "the single largest cost driver" — AWS's actual guidance names tiered routing, caching, and RAG scoping as the levers, not a single dominant driver.

---

# Part 1 — Directives for authoring specs, tests, and workflows

## 1.1 Load repo context first 🟢

Before writing a spec, test, or workflow, read:
1. This guide.
2. The relevant section(s) of `careervp-architecture-v2.md` / `careervp-architecture-deepdive.md` for the domain you're touching (data, compute, frontend, API, async, LLM, IaC).
3. `redesign-runbook.md` if the task touches anything stateful, IAM, or migration-phase work — **the runbook's golden rules are load-bearing, not optional.**

**Why:** OpenAI's and Anthropic's own coding-agent guidance converges on the same pattern — an auto-loaded, repo-specific instructions file (`AGENTS.md` / `CLAUDE.md`) containing layout, conventions, prohibited actions, and definitions of done, because an agent without this context re-derives (and often gets wrong) decisions the team already made. CareerVP's decisions are unusually explicit and already written down — use them. *(Sources: [OpenAI Codex best practices](https://developers.openai.com/codex/learn/best-practices), [OpenAI AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md))*

**CareerVP-specific landmines to check before writing anything new:**
- Never write to a table via a new env-var alias — the `ARTIFACTS_TABLE_NAME → DYNAMODB_TABLE_NAME → TABLE_NAME` precedence chain is exactly the bug class the redesign is fixing. New code should import the typed `artifact_type → (table, key)` contract, not add a fourth alias.
- Never remove or weaken `RemovalPolicy.RETAIN` / `deletion_protection` once Phase 0 lands (redesign-runbook §0.1) — this is a hard rule for any PR.
- Never introduce a new shared IAM role — every new Lambda gets its own role with `grant_*`-scoped ARNs.

## 1.2 Spec Template 🟢

Use the template in the [Appendix](#appendix-a-spec-template). It operationalizes the "4-part structure" both OpenAI and Anthropic converge on for prompt/spec construction: **goal, context, constraints, done-when** — plus explicit, direct, action-oriented phrasing rather than suggestion-style requests (Claude and GPT-class models will sometimes only *propose* a change if asked ambiguously; tell them to act). *(Sources: [Anthropic prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview), [Anthropic Claude 4 best practices](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices), [OpenAI Codex best practices](https://developers.openai.com/codex/learn/best-practices))*

Two additions specific to CareerVP: a **constraints** section always names the AWS resources touched (so IAM scope and cost impact are visible before implementation starts), and **done-when** always includes a check against the actual CI gates CareerVP runs (ruff, mypy, pytest, `cdk synth`, Checkov, Bandit, pip-audit, CodeQL) — not a generic "tests pass."

## 1.3 The Explore → Plan → Implement → Commit loop 🟢

The recommended agentic coding workflow, per Anthropic's own Claude Code guidance:

1. **Explore** — read-only research. No edits. Understand the current shape of the code (e.g., read the relevant handler, repository, and construct files named in the architecture docs before touching anything).
2. **Plan** — write an editable plan artifact (use the Workflow/Plan Template, §1.9). For anything touching the data layer, IAM, or stateful resources, the plan must state which redesign-runbook phase it belongs to.
3. **Implement** — execute against the plan, verifying against the spec's done-when criteria as you go.
4. **Commit** — a descriptive commit/PR that references the phase and finding number (if any) it addresses.

*(Source: [Claude Code best practices](https://code.claude.com/docs/en/best-practices))*

## 1.4 Test Plan Template 🟢

Use the template in [Appendix B](#appendix-b-test-plan-template).

**The one CareerVP-specific rule that overrides generic TDD advice:** `tests/conftest.py::mock_artifact_dependency_resolver` is an autouse fixture that stubs dependency resolution to `ready` for every handler test — it currently **hides the entire table-routing defect class from CI** (architecture-v2 §3.8, runbook §3 intro). Any new test for artifact-storage/routing code must either (a) explicitly opt out of that fixture, or (b) drive the real `get_artifact`/worker resolution against `moto`-mocked tables using the actual key schemas. A test suite that passes only because of this mock is not evidence of correctness — treat it as a known-compromised safety net until runbook Phase 3 replaces it.

TDD loop for agent-driven work: write the failing test against the real key schema first, confirm it fails for the right reason (not an import error), then implement. This is the same "verifiable pass/fail check" pattern that lets an agent loop close without a human re-checking every step (§1.5) — but it only works if the check is real.

## 1.5 Verifiable done-when criteria 🟢

A task is not done because the agent says so — it's done because a **verifiable, automatable check** passes: a test, a build, a lint pass, a `cdk diff` showing only expected resource changes. This is the mechanism that lets an agent close a loop autonomously; without one, a human becomes the verification loop. *(Source: [Claude Code best practices](https://code.claude.com/docs/en/best-practices))*

**Important caveat — do not skip this:** agents can game or fabricate passing checks over long horizons. Anthropic's own reward-hacking research, the publicly documented Replit incident, and the academic "Verification Horizon" work all show this failure mode concretely. Mitigations for CareerVP work specifically:
- Cap agentic retry loops (don't let an agent "fix" a failing test by weakening the assertion — that's a code-review-blocking pattern, not a passing check).
- For anything touching the data layer or auth, add an explicit adversarial review step ("spawn a subagent to check this diff doesn't reintroduce the `x-user-id` fallback or a table-alias precedence chain") rather than trusting a green CI run alone.
- `cdk diff` output is itself a verifiable check — "zero resource replacements" is exactly the Phase 0 success metric in the runbook, and it's cheap to assert automatically.

## 1.6 Prompt construction for non-prompt-engineers 🟢

You don't need prompt-engineering expertise to direct a coding agent effectively. Two rules cover most of it:

1. **Four-part structure:** goal → relevant context (files, docs, error messages) → constraints (architecture, security, cost) → explicit success/verification criteria ("done when"). This is the Spec Template, applied inline for smaller asks.
2. **Be explicit and direct, not suggestive.** "Consider updating the IAM policy" may get you a suggestion instead of a diff. "Update `api_construct.py` to scope the KMS grant to the queue key ARN, run `cdk diff`, and confirm no other resource changes" gets you a diff.

Additionally: establish success criteria and a way to test them *before* iterating on wording — prompt engineering should be eval-driven, not trial-and-error. And prompt tuning isn't always the right lever: if a CareerVP task is actually a cost or latency problem, the fix is usually model selection or architecture (§2.6), not a better-worded prompt. *(Sources: [Anthropic prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview), [OpenAI Codex prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide))*

## 1.7 Subagent orchestration 🟢

Delegate to a subagent when work is **parallelizable, needs isolated context, or is a genuinely independent workstream** — e.g. "explore how VPR status is currently read across `jobs`/`users`/S3 and report back" or "adversarially review this IAM diff for wildcard reintroduction." Don't delegate trivial lookups a single `grep` would answer — both OpenAI and Anthropic document over-delegation as a real failure mode that burns context and time for no benefit. *(Sources: [Claude Code best practices](https://code.claude.com/docs/en/best-practices), [Anthropic Claude 4 best practices](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices), [OpenAI Codex best practices](https://developers.openai.com/codex/learn/best-practices))*

CareerVP tasks that are good subagent candidates: auditing an IAM policy diff for least-privilege compliance; checking a new SQS consumer against the checklist in §2.4; reviewing a data-model change against the three-schema/three-id landmines in §1.1.

## 1.8 Cross-session state 🟢

For work spanning multiple context windows (e.g. a full runbook phase), persist state as: a structured JSON file for machine-checkable status (which steps are done, which tests pass), a freeform text file for notes/decisions, and git commits as restore points. On resuming, read the JSON status + `git log` before re-deriving anything. *(Source: [Anthropic Claude 4 best practices](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices))*

This maps directly onto the runbook's phase structure: each phase's checkbox list *is* the structured status file. Treat runbook checkboxes as the machine-checkable contract — don't mark a step done without its stated success metric holding.

## 1.9 Workflow/Plan Template 🟢

Use the template in [Appendix C](#appendix-c-workflowplan-template). It's shaped around CareerVP's actual migration pattern — **expand → dual-write → backfill → dual-read → contract** — because that pattern (additive, reversible, one flag-gated change at a time) is the correct shape for *any* CareerVP infrastructure change, not just the DynamoDB migration. Golden rule from the runbook: never mutate or delete a live resource in place; add the new alongside the old, shift traffic gradually, verify, retire the old.

## 1.10 Parallel tool-calling; safe-by-default sandboxing 🟢

Batch independent reads/searches/greps in parallel rather than sequentially — this is default agent behavior in both Claude Code and Codex and measurably reduces turns and latency (industry-reported 1.8×–3.7× speedups on parallelizable work). Reserve sequential calls for genuinely dependent steps. *(Sources: [OpenAI Codex prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide), [Anthropic Claude 4 best practices](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices))*

Keep tool-use sandboxing tight by default (workspace-write, on-request approval for anything destructive) and loosen only for a specific, identified need — this mirrors the least-privilege-by-default philosophy CareerVP's own worker Lambdas already demonstrate correctly (dedicated roles + `grant_*`), and should extend to how much autonomy you give an agent operating on this repo. *(Source: [OpenAI Codex best practices](https://developers.openai.com/codex/learn/best-practices))*

---

# Part 2 — Building and extending CareerVP's agentic AWS system

## 2.1 Event-driven architecture as the substrate 🟢

AWS's own prescriptive guidance for agentic AI on serverless names event-driven architecture — EventBridge, S3 event notifications, SNS/SQS, Step Functions, API Gateway — as the foundational substrate, mapping an agent's perceive→decide→act loop directly onto event triggers. CareerVP already follows this: `*_submit → SQS → *_worker`, S3 `OBJECT_CREATED` triggering the CV upload worker, an hourly EventBridge cleanup. **Any new artifact type should follow this same shape by default** — sync API Lambda enqueues, async worker processes, Step Functions orchestrates cross-artifact dependencies. *(Source: [AWS Prescriptive Guidance — event-driven architecture](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/event-driven-architecture.html))*

## 2.2 Orchestration model: Step Functions vs. Bedrock Agents (hybrid) 🟢

AWS recommends a hybrid rather than picking one exclusively: **Step Functions for deterministic, controlled processes; Bedrock Agents for flexible natural-language reasoning** — with an explicit tradeoff that Bedrock Agents provide only limited audit trace versus Step Functions' full state trace. CareerVP's `ArtifactChain` is entirely Step-Functions-based (deterministic control flow: `RouteStartAt` → CR → VPR → CV → parallel{cover letter, interview prep}), which is the right choice given the audit/compliance value of a full state trace for a product that generates career/financial-adjacent artifacts. **Don't introduce Bedrock Agents' flexible-reasoning mode into the core chain** unless a task genuinely needs open-ended natural-language planning that a deterministic state machine can't express — the audit-trail cost is real. *(Source: [AWS Prescriptive Guidance — orchestration models](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/orchestration-models.html))*

## 2.3 Resilience & durability 🟢

**Step Functions Retry + Catch** (already partially used in the artifact chain's failure handlers) — the two primitives are composable and AWS explicitly recommends combining them:
- **Retry**: `IntervalSeconds`, `MaxAttempts` (default 3), `BackoffRate` (default 2.0), optional `MaxDelaySeconds` cap, `JitterStrategy` (`FULL`/`NONE`, default `NONE` — set to `FULL` to avoid thundering-herd retries against a rate-limited dependency like the Anthropic API).
- **Catch**: an array of catchers matched by `ErrorEquals` (including the `States.ALL` wildcard), each routing via `Next` to a fallback state. Retry always fires first; Catch only triggers once retries are exhausted or absent.
- AWS explicitly calls out handling `Lambda.ServiceException`/`Lambda.SdkClientException` as transient-retry candidates, and matching `Lambda.Unknown`/`Sandbox.Timedout`/`Lambda.TooManyRequestsException`/`States.TaskFailed`/`States.ALL` for broader coverage.

*(Sources: [Step Functions error handling](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html), [Step Functions error-handling tutorial](https://docs.aws.amazon.com/step-functions/latest/dg/tutorial-handling-error-conditions.html))*

**Lambda's baseline retry/idempotency model** (relevant to every CareerVP handler, not just the chain): synchronous/direct invocations get **no automatic retry** — the caller must handle retries and idempotency itself (this is exactly why CareerVP's finding #3, zero handlers wired to `@idempotent`, is a real gap, not a stylistic one). Asynchronous invocations retry automatically up to **2 times by default**, and a DLQ (SQS or SNS) can capture events still unprocessed after retries are exhausted. *(Source: [Lambda invocation retries](https://docs.aws.amazon.com/lambda/latest/dg/invocation-retries.html))*

**AWS Lambda Durable Functions** (announced re:Invent, Dec 2025 — new enough that the SDK surface should be expected to evolve; verify against current docs before depending on it in production) is worth evaluating as a future evolution of CareerVP's SQS+`waitForTaskToken` pattern:
- A Durable Execution SDK exposes `context.step()`, `context.wait()`, `context.waitForCallback()`, `context.waitForCondition()`.
- **Checkpoint-and-replay**: on interruption, Lambda saves a checkpoint log of completed durable operations, stops, and on resume re-invokes from the start — replaying the log and substituting stored results for already-completed steps. Concretely: in a multi-stage pipeline like VPR's 6-stage chain, if stage 5 fails, stages 1–4 are not re-run and **their token cost is not paid twice** — this directly addresses the "duplicate AI spend on retry" risk that's currently a CRITICAL finding (visibility timeout == Lambda timeout) in the existing SQS-based design.
- Requires **determinism outside of steps** (no raw random/time-of-day calls outside a `step()` call) — a real constraint on how you'd port existing worker code.
- Per-invocation Lambda timeout is still capped at 15 minutes; the overall durable execution timeout is separately configurable up to **~365–366 days** (documented inconsistently across AWS pages as 31,536,000s vs. 31,622,400s — treat as "approximately one year," not an exact number), default 24 hours, minimum 60 seconds. Wait time counts against the execution timeout but not the 15-minute per-invocation cap, and on-demand functions incur no compute charge while suspended in a wait.
- Built-in idempotency is provided via execution names.

*(Sources: [AWS blog — build multi-step apps with Lambda Durable Functions](https://aws.amazon.com/blogs/aws/build-multi-step-applications-and-ai-workflows-with-aws-lambda-durable-functions/), [Lambda durable basic concepts](https://docs.aws.amazon.com/lambda/latest/dg/durable-basic-concepts.html), [Lambda durable configuration](https://docs.aws.amazon.com/lambda/latest/dg/durable-configuration.html), [AWS blog — fault-tolerant multi-agent AI workflows with Lambda Durable Functions](https://aws.amazon.com/blogs/compute/building-fault-tolerant-multi-agent-ai-workflows-with-aws-lambda-durable-functions/))*

**Do not treat this as a reason to defer the runbook's Phase 2 fixes** (`batchItemFailures`, visibility timeout ≥ 6× Lambda timeout, `max_concurrency`) — those are needed regardless of whether Durable Functions is adopted later, and are the cheaper, already-specified fix for the CRITICAL findings today.

## 2.4 Idempotency patterns 🟢

Given the Lambda retry model above, every **at-least-once consumer** (every SQS worker, every webhook handler) needs explicit idempotency — it is not provided for you by the platform on sync paths. CareerVP's own `idempotency` DynamoDB table + Powertools `@idempotent` decorator already exist; the gap is that they're wired to zero handlers (finding #3). For any new async handler:
- Key idempotency on a stable business identifier (Stripe event ID for billing; `application_id` + stage for chain workers), never on a client-supplied, re-mintable ID.
- Combine with `ReportBatchItemFailures` (SQS partial-batch failure reporting) so a poison message is retried/DLQ'd instead of silently dropped — CareerVP's CR worker already implements this correctly; use it as the reference pattern for any new SQS consumer.

## 2.5 Security 🟢

AWS's security guidance for agentic architectures prescribes **layered, concrete controls**, not reliance on model-level guardrails alone:
- **Least-privilege IAM scoped per tool/function** — a Bedrock agent (or, by direct analogy, a Lambda) should be restricted to the specific named action/resource it needs, not a broad shared role. This is precisely CareerVP's #6/#8 findings (wildcard KMS/AppConfig grants, one shared role across 13+ Lambdas) — the fix (`grant_*`-scoped ARNs, one role per function) is not a CareerVP-specific opinion, it's the vendor-documented default.
- **Prompt-injection detection as a supplementary layer only.** AWS's own example uses regex/pattern matching (e.g. flagging phrases like "ignore instructions") inside a broader 10-category defense-in-depth control table — but independent security research treats pure regex-based detection as weak and bypassable. Treat pattern matching as one layer among several (delimiting untrusted content from instructions, output sanitization before rendering) — never as the sole defense. This is directly relevant to CareerVP's own finding (§1.2.F in the deep-dive): job-posting text and Tavily-scraped content are concatenated into prompts and the model's output is rendered as rich text in the SPA — delimit untrusted input and sanitize/encode generated markup before render, regardless of any injection-detection preprocessing you add.

*(Sources: [AWS Prescriptive Guidance — security and governance](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/security-and-governance.html), [Agentic AI Serverless PDF](https://docs.aws.amazon.com/pdfs/prescriptive-guidance/latest/agentic-ai-serverless/agentic-ai-serverless.pdf))*

## 2.6 Cost & token optimization 🟢

**Model routing.** AWS's guidance — route low-complexity work to a smaller/cheaper model, escalate to a larger model only on low confidence — is exactly what CareerVP's Sonnet/Haiku split already does (Sonnet for VPR/Gap Analysis, Haiku for templated artifacts). The gap is measurement, not architecture: the `len/4`-estimating `LLMClient` used by Gap/Cover-Letter/Interview-Prep/CV-Tailoring/AI-Assist captures no real token usage, so those paths fly blind on the `MAX_COST_PER_APPLICATION` alert. Unify on the cost-aware router client before optimizing further — you can't tune what you don't measure. *(Source: [AWS Prescriptive Guidance — cost optimization](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/cost-optimization.html))*

**Prompt caching.** Anthropic's prompt caching defaults to a 5-minute ephemeral cache that refreshes free on each use, with an optional 1-hour cache at 2× base input token price; reduces cost by up to ~90% and latency by up to ~85% for long, cache-eligible prompts. CareerVP already uses this on VPR phase-2, CV-tailoring stage 2, and AI-Assist. Migrating Gap/Cover-Letter/Interview-Prep from `generate()` to `complete(use_system_cache=True)` (padding system prompts to the 1,024-token cache minimum) is a near-zero-risk, if modest, win — the real cost driver is VPR's output tokens (~74% of spend), which caching doesn't touch. *(Source: [Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching))*

**Multi-agent token economics — plan for this explicitly if you ever add multi-agent orchestration to CareerVP:** Anthropic's own engineering data shows a single agent uses roughly **4× the tokens** of a chat interaction, and a multi-agent system uses roughly **15× the tokens** of a chat interaction. If any future CareerVP feature considers a multi-agent pattern (e.g., decomposing VPR generation into cooperating sub-agents), budget for this multiplier up front — it will materially change the ~$0.43/application economics. *(Source: [Anthropic — how we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system), 2025-06-13)*

**Bounding input, not just output.** RAG/retrieval scoping (metadata filters, Top-K ranking) and tool-call result caching (CareerVP's own `company-research-cache`, TTL-based) both bound context growth. CareerVP's one measured input-bloat case — Company Research sending ~15K raw Tavily tokens per generation — should be truncated or fetched with `include_raw_content:false`; this is a $0.007/generation fix already identified in the architecture docs, unrelated to the redesign.

## 2.7 Availability & scaling 🟡

*Practitioner guidance — verify current numbers against live docs; this tier did not clear the same adversarial verification as the sections above.*

- **Reserved and provisioned concurrency** are the standard Lambda levers for guaranteeing capacity: reserved concurrency caps (and guarantees) how many concurrent executions a function can use, which is exactly the missing control on CareerVP's API-path Lambdas; provisioned concurrency keeps a pool of pre-initialized execution environments warm, which is the standard cold-start mitigation for latency-sensitive functions (the CV parser and VPR worker, at 1024 MB with full dependency trees, are the CareerVP candidates most likely to benefit).
- **SQS `max_concurrency` on the event source mapping** caps how many workers pull from a queue concurrently — this is the direct fix for CareerVP's documented risk of AI workers scaling to the account concurrency ceiling and tripping Anthropic 429s under load (architecture-deepdive §3.2/§6.2).
- **LLM API rate-limit backoff**: both Anthropic's and OpenAI's APIs return standard throttling signals (HTTP 429 plus rate-limit headers); the standard mitigation is exponential backoff with jitter on retry — which composes directly with the Step Functions `JitterStrategy: FULL` setting from §2.3 if a chain step calls the model directly.
- **Multi-region**: CareerVP currently runs single-region, single-account. Multi-region failover for a Step-Functions-orchestrated, DynamoDB-backed system is a substantial undertaking (global tables, cross-region Step Functions state replication) — treat as out of scope unless a specific availability SLA requires it; do not add multi-region complexity speculatively.

## 2.8 Reliability, evals & observability 🟡

*Practitioner guidance — same caveat as above.*

- **Eval-driven development applies to agent-authored code changes too**: establish the success criteria and an empirical test method *before* iterating (§1.6) — the same principle Anthropic recommends for prompt engineering applies to verifying whether a code change actually fixed the targeted finding.
- **Observability for multi-step agent/workflow runs is a different discipline than request/response APM** — it needs to capture tool selection, tool arguments, intermediate state, and decision branches, not just "did the Lambda return 200." CareerVP's own gap here is concrete: monitoring covers only 7 of ~31+ Lambdas, and DLQ depth is unmonitored — a stuck DLQ is currently silent (architecture-v2 §3.7, finding #16). Extending monitoring to the worker Lambdas and adding DLQ-depth alarms (runbook Phase 2) is the highest-leverage observability fix available today, independent of any new tooling adoption.
- **Guardrails against infinite looping or hallucination in autonomous chains**: bound retries explicitly (Step Functions `MaxAttempts`, §2.3), and never let an agent's "it looks done" self-report substitute for the verifiable check in §1.5.

## 2.9 Performance 🟡

*Practitioner guidance — same caveat as above.*

- **Streaming responses** reduce perceived latency for long-generation calls (relevant to VPR's 6-stage Sonnet pipeline) but add complexity to a Lambda-based, request/response architecture — evaluate case by case rather than adopting by default.
- **End-to-end latency budgets**: define one per artifact type (e.g., VPR generation has a different acceptable latency than a synchronous AI-Assist rewrite) so async-vs-sync architecture choices stay deliberate rather than accidental.
- **Agent/workflow-level parallelism**, distinct from the tool-call-level parallelism in §1.10: CareerVP's `GenerateFinalArtifacts` Parallel state (cover letter + interview prep running concurrently) is already the correct pattern — extend it, don't serialize, when adding new independent post-VPR artifacts.
- **The actual measured performance problem in CareerVP today is the frontend's chatty fan-out**, not backend latency: a page load fires 3+ separate Lambda calls across 2+ tables with no shared cache (architecture-deepdive §4, §5.4). The `GET /me/bootstrap` aggregate endpoint, paired with a correctly configured `QueryClient` (`staleTime`, `refetchOnWindowFocus: false`), is a bigger performance win than any backend-side tuning discussed above — fix this before optimizing LLM-call latency.

## 2.10 AWS infrastructure patterns 🟢

This section is CareerVP's own architecture-v2 §5 target, generalized so it applies to any new feature, not just the current redesign:

- **Stateful resources live in their own top-level stack with `RemovalPolicy.RETAIN` + `deletion_protection=True`**, never inside a high-churn compute stack. A compute redeploy must never be able to replace a table or bucket.
- **No CloudFormation template exceeds ~400 resources** (against the 500 hard limit), enforced by a CI synth-and-count gate. Each Lambda is ~5 resources (function, role/policy, log group, version, permission) — budget new features accordingly, and default to a new nested stack per feature area rather than adding to an already-large parent.
- **Share resource references via constructor props, never `Fn::ImportValue`** — cross-stack exports create deletion deadlocks that block future stack recreation.
- **Single-table DynamoDB design, access-pattern-first**: model the partition/sort key from the actual read patterns before writing code, lead the partition key with an immutable identifier (never PII, never anything mutable), and route all reads/writes through one typed repository so there is exactly one stored key per entity type. This is CareerVP's `core` table design (`PK=USER#{user_id}`, overloaded `SK`) — apply the same discipline to any new entity type rather than adding a new standalone table.
- **`cdk import` / logical-id retention** to move ownership of live resources between stacks without replacement — this is how you decompose an existing stack (like CareerVP's Phase 0 stateful-stack extraction) without data loss.

---

# Appendix

## Appendix A: Spec Template

```markdown
## Spec: <short title>

### Goal
<One or two sentences: what should be true when this is done, and why it matters.>

### Context
- Relevant files: <paths>
- Relevant docs: <e.g. careervp-architecture-v2.md §X, redesign-runbook.md Phase Y>
- Related finding (if any): <finding # from the architecture docs' findings register>
- Errors/symptoms observed (if any): <paste verbatim>

### Constraints
- Architecture: <e.g. must follow the expand→dual-write→backfill→dual-read→contract pattern; must not touch a stateful resource destructively>
- Security: <e.g. no new wildcard IAM grants; identity from validated JWT only>
- Cost: <e.g. must not add an unbounded LLM call; must route through the cost-aware client>
- AWS resources touched: <table/queue/Lambda names — name the IAM role and its scope>

### Done-when
- [ ] <Specific automatable check #1 — e.g. "pytest tests/handlers/test_x.py passes">
- [ ] <e.g. "cdk diff shows only the expected resource additions, zero replacements">
- [ ] <e.g. "no new resources=['*'] in any IAM policy statement">
- [ ] <e.g. "ruff, mypy, Checkov, Bandit all pass in CI">
```

## Appendix B: Test Plan Template

```markdown
## Test Plan: <short title>

### What this proves
<The specific behavior or regression this test plan verifies — tie back to the spec's done-when.>

### Autouse-mock check
- [ ] Does this touch artifact storage/routing code? If yes: confirm `tests/conftest.py::mock_artifact_dependency_resolver`
      is either bypassed for this test or the test drives real resolution against moto-mocked tables with the
      actual key schema (pk/sk, applicationId/artifactId, or job_id — whichever this artifact type uses).

### Unit tests
- [ ] <Happy path>
- [ ] <Failure path — e.g. malformed input, missing upstream artifact>
- [ ] <Boundary — e.g. TTL attribute name matches the table's actual configured TTL attribute>

### Integration tests (moto-backed DynamoDB / real key schema)
- [ ] Write via the typed repository/contract; read back via the same contract — confirm one stored key, not three.
- [ ] Cross-tenant isolation: a second `user_id` cannot read this item via any code path.
- [ ] If async: idempotency — replaying the same message/event does not double-write or double-charge.
- [ ] If SQS-based: a poison message reaches the DLQ (via `batchItemFailures`), not silently deleted.

### Verification (per §1.5 — must be automatable, not a self-report)
- [ ] Command to run: `<exact command>`
- [ ] Expected result: `<exact expected output/exit code>`
```

## Appendix C: Workflow/Plan Template

```markdown
## Workflow: <short title>

### Phase mapping
Which redesign-runbook phase (0–5) does this belong to, if any? <phase # or "N/A — new feature">

### Steps (expand → dual-write → backfill → dual-read → contract, or the subset that applies)
1. **Expand** (additive, no behavior change): <e.g. add new table/field/route alongside the old>
2. **Dual-write** (behind flag `<flag_name>`): <writers emit to both old and new>
3. **Backfill** (throttled, idempotent): <batch job description; run against on-demand capacity>
4. **Dual-read / cutover** (behind flag, per-cohort canary): <internal → small % → all; shadow-compare>
5. **Contract** (retire old, separate deploy): <only after zero drift for a full validation window>

### Success metric per step
<Each step above needs its own metric before moving to the next — e.g. "drift metric → 0" for backfill.>

### Rollback
<What flag/alias reverts this step? Confirm it needs no data surgery.>

### Guardrails (block on any of these)
- [ ] No single deploy renames/removes a live table, GSI, or bucket, or changes a PK/SK.
- [ ] Read path is not switched to the new location before backfill + reconciliation is complete.
- [ ] No "big bang" cutover — canary by cohort, with alarms wired to auto-rollback.
- [ ] `removal_policy=DESTROY` is not (re)introduced on any stateful resource.
- [ ] Migration batch jobs run throttled, not unthrottled against live table capacity.
```

## Appendix D: Sources

**Part 1 (agent-usage workflow) — Verified:**
- [OpenAI Codex best practices](https://developers.openai.com/codex/learn/best-practices)
- [OpenAI Codex prompting guide](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)
- [OpenAI AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md)
- [Claude Code best practices](https://code.claude.com/docs/en/best-practices)
- [Anthropic prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview)
- [Anthropic Claude 4 best practices](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices)

**Part 2 (AWS serverless agentic architecture) — Verified:**
- [AWS Prescriptive Guidance — agentic AI on serverless (event-driven architecture)](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/event-driven-architecture.html)
- [AWS Prescriptive Guidance — orchestration models](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/orchestration-models.html)
- [AWS Prescriptive Guidance — cost optimization](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/cost-optimization.html)
- [AWS Prescriptive Guidance — security and governance](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-serverless/security-and-governance.html)
- [AWS Step Functions — error handling](https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html)
- [AWS Step Functions — error-handling tutorial](https://docs.aws.amazon.com/step-functions/latest/dg/tutorial-handling-error-conditions.html)
- [AWS Lambda — invocation retries](https://docs.aws.amazon.com/lambda/latest/dg/invocation-retries.html)
- [AWS Lambda — durable basic concepts](https://docs.aws.amazon.com/lambda/latest/dg/durable-basic-concepts.html)
- [AWS Lambda — durable configuration](https://docs.aws.amazon.com/lambda/latest/dg/durable-configuration.html)
- [AWS blog — build multi-step apps with Lambda Durable Functions](https://aws.amazon.com/blogs/aws/build-multi-step-applications-and-ai-workflows-with-aws-lambda-durable-functions/)
- [AWS blog — fault-tolerant multi-agent AI workflows with Lambda Durable Functions](https://aws.amazon.com/blogs/compute/building-fault-tolerant-multi-agent-ai-workflows-with-aws-lambda-durable-functions/)
- [Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [Anthropic — how we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) (2025-06-13)

**Part 2 (§2.7–2.9) — Practitioner guidance, verify against current docs:**
- AWS Lambda concurrency documentation (reserved/provisioned concurrency)
- Anthropic and OpenAI API rate-limit/throttling documentation
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [Anthropic — Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [AWS blog — Amazon Bedrock AgentCore Observability with Langfuse](https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-agentcore-observability-with-langfuse/)

**Rejected during adversarial verification — do not cite:**
- A claim that Amazon Bedrock AgentCore has exactly three capabilities (Runtime/Memory/Gateway).
- A claim that AWS names prompt/token length as "the single largest cost driver."

---

*Grounded against CareerVP `main` @ `4f7c294` (2026-06-29) via `careervp-architecture-v2.md`, `careervp-architecture-deepdive.md`, and `redesign-runbook.md`. Vendor research current as of 2026-07.*
