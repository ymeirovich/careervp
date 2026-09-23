Internal memo · Engineering & Finance
2026-07-01
CareerVP × Claude Sonnet 5
A cost-benefit read on migrating the strategic (VPR) model tier — grounded in four independent code audits, not vendor pricing sheets.

Recommendation
Pilot Sonnet 5 on VPR Generation only — don't touch the Haiku-tier tasks. Fix two concrete migration blockers first (§6), then canary against your existing CostUSD metrics before any broad rollout. Net cost impact is favorable through the Aug 31, 2026 intro-pricing window and unfavorable after — timing matters as much as the model choice.
Contents
01Correcting the premise
02Where Sonnet-tier applies
03Sonnet 4.6 vs. Sonnet 5
04Cost model
05Benefit beyond cost
06Migration checklist
07Rollout plan
08Open questions
01
Correcting the premise
The ask was "Sonnet 4.5 vs. Sonnet 5." That's not what's actually deployed.

No live code path in careervp calls Sonnet 4.5. The deployed strategic model, confirmed in the CDK source of truth and pinned by a unit test, is Sonnet 4.6:

Source	What it says	Status
infra/careervp/constants.py:191	STRATEGIC_MODEL_ID = "claude-sonnet-4-6"	Live
tests/unit/test_llm_client.py:51	assert SONNET_MODEL_ID == 'claude-sonnet-4-6'	Enforced by CI
docs/architecture/system_design.md:19	"Claude Sonnet 4.5"	Stale doc
docs/specs/00-llm-router.md:9	sonnet-4.5	Stale doc
Two of your own docs disagree with your own code and your own test suite. That's worth fixing independent of anything else in this memo — someone will eventually plan around the wrong baseline. Every comparison below is Sonnet 4.6 → Sonnet 5, the real migration. (If your actual intended baseline genuinely is 4.5, the case for upgrading is only stronger: 4.5 lacks adaptive-thinking-by-default and the xhigh effort tier that 4.6 and Sonnet 5 both have.)

02
Where Sonnet-tier actually applies
CareerVP already runs a two-tier strategy. Only one slice of it is a Sonnet 5 candidate.

Requests route through one of two client implementations: a proper hybrid router (LLMRouter) used by VPR generation, CV parsing, and Company Research; and a legacy client (LLMClient) that quietly defaults to Haiku whenever a caller doesn't override the model — which is most of the remaining features, including one that isn't supposed to be on Haiku (see row marked below).

Task	Tier today	% of AI cost	Sonnet 5 relevant?
VPR Generation
5-stage synthesis → self-correction (rule-based) → format → meta-evaluate	Sonnet 4.6	~74%	Yes — primary candidate
Gap Analysis
Documented as Sonnet; code path never overrides model_name	Haiku 4.5 Routing bug	~0%	Only if the bug is fixed
CV Parsing	Haiku 4.5	low	No — extraction task
Company Research structuring	Haiku 4.5	low	No — extraction task
CV Tailoring	Haiku 4.5	low	No — templated rewrite
Cover Letter	Haiku 4.5	low	No — bounded, templated
Interview Prep	Haiku 4.5	low	No — templated
AI Assist (field rewrite)	Haiku 4.5	low	No — latency-sensitive UX
The answer to "is Sonnet 5 correct for this task" is: yes for VPR, no for the rest of the app. Don't migrate careervp to Sonnet 5 — migrate the VPR pipeline. Fix the Gap Analysis routing bug before deciding whether it belongs in this conversation at all: right now you can't cost an upgrade to a task that isn't running where the docs say it is.

03
Sonnet 4.6 vs. Sonnet 5
The relevant differences for a pipeline that does multi-stage synthesis with an explicit temperature setting and no thinking config today.

Dimension	Sonnet 4.6 (current)	Sonnet 5	Matters here?
Input / output price per MTok	$3.00 / $15.00	$3.00 / $15.00
$2.00 / $10.00 intro, through 2026-08-31	Yes — §04
Tokenizer	baseline	~1.3× tokens for same text	Yes — §04
temperature / top_p / top_k	Accepted at any value	Non-default values return 400	Blocking — VPR Stage 3 uses temp=0.65
Thinking when omitted	Off by default	Adaptive thinking on by default	Check max_tokens headroom
Effort levels	low–xhigh	low–xhigh, plus max	Tuning opportunity, not required
Vision resolution	1568px	2576px (high-res)	Not used — VPR is text-only
Assistant prefill	Not supported	Not supported	No change — careervp doesn't prefill
Capability framing, for context: Sonnet 5 is positioned as reaching near-Opus quality on coding and agentic work — the closest analogue careervp has to that is VPR's multi-stage synthesize → self-correct → meta-evaluate loop, which is exactly the kind of task that tends to benefit.

04
Cost model
Netting the intro discount against the tokenizer change, using your own baseline numbers.

~$0.32
EST. VPR COST / APPLICATION
(4.6, pending 5-stage refresh)
~74%
SHARE OF TOTAL AI SPEND
88–89%
CURRENT MARGIN vs. 91% TARGET
100 / 500
USERS / APPS·MO — YOUR OWN BASELINE
Sonnet 5's list price is unchanged from Sonnet 4.6 ($3/$15 per MTok) — but a new tokenizer means roughly 30% more tokens for the same input/output, and an introductory 33% price cut is active on both input and output through 2026-08-31. Netting the two:

Sonnet 4.6 (now)	Sonnet 5, intro window	Sonnet 5, standard pricing
Price / MTok (in·out)	$3 · $15	$2 · $10	$3 · $15
Relative tokens, same content	1.00×	1.30×	1.30×
Net effective cost vs. today	baseline	≈ −13%	≈ +30%
Est. VPR cost / application	~$0.27–0.32	~$0.24–0.28	~$0.35–0.42
Est. monthly VPR spend, at 500 apps/mo	~$135–160	~$120–140	~$175–210
At your current, early-stage volume the absolute swing either way is under $75/month — not the deciding factor by itself. It becomes one as usage grows: your own cost-model doc already shows margin compressing from 88.8% at 5 applications/user/month to 35.2% at 30/month. A further 30% cost increase on the largest line item lands hardest exactly on your heaviest users, at exactly the volume where margin is already thinnest.

Data caveat
Only two real CloudWatch cost samples exist across your entire pipeline, both for Company Research on Haiku. Every Sonnet-tier figure above — including the ~$0.32/application VPR estimate — is derived from prompt structure, not measured production spend. Treat every dollar figure on this page as directional until you pull real telemetry.
05
Benefit beyond the token bill
VPR quality is the product's actual differentiator. The pipeline enforces an elaborate rule set — banned-word lists, evidence-grounding, exact schema constraints, anti-AI-detection heuristics, a dedicated meta-evaluation quality gate. A stronger model plausibly means fewer rule violations and fewer regeneration loops at that gate — a cost saving the token-price math above doesn't capture at all.
Finer effort control. Sonnet 5's effort range extends to max (both models already support xhigh), giving you a lever to spend more on the synthesis stage specifically while holding the line elsewhere — a more surgical tool than a flat model swap.
Fewer retries, if any. If Sonnet 5 reduces the self-correction/meta-evaluation failure rate, that shows up as real savings nowhere in a per-token cost model.
None of this is quantified yet — it's the argument for running the pilot in §7, not a substitute for measuring it.

06
Migration checklist
Two of these are genuine blockers specific to your code, not generic migration advice.

Blocking
VPR Stage 3 will 400 on Sonnet 5 as-is. The Phase-2 synthesis call — your single largest cost line item — passes an explicit temperature=0.65. Sonnet 5 rejects any non-default temperature/top_p/top_k. Remove it or move variance control into the prompt before touching the model string.
vpr_generator.py — Stage 3 · via logic/utils/llm_client.py LLMRouter.invoke()
Blocking (CI)
A unit test hard-asserts the current model string. assert SONNET_MODEL_ID == 'claude-sonnet-4-6' will fail the moment you flip the env var, unless updated in the same change.
src/backend/tests/unit/test_llm_client.py:51, 55–56
Tune
Adaptive thinking now defaults on. Stages 1, 2, 5, and 6 default to max_tokens≈2500. Thinking tokens now eat into that budget where they didn't on 4.6 — check headroom before a stage starts truncating.
Independent
Resolve the Gap Analysis routing gap first. Documented as Sonnet/"Strategic," actually defaults to Haiku (model_name never passed). Decide intentionally — fix the routing or formally accept Haiku — before this feature enters any Sonnet-upgrade cost math.
logic/gap_analysis.py:286
Doc debt
Align the docs to the code. system_design.md and 00-llm-router.md still say Sonnet 4.5 — the source of the original question here. Fix so the next person doesn't plan against the wrong baseline again.
Doc debt
Refresh cost-model.md for the 5-stage pipeline. The doc still assumes 6 LLM-backed VPR stages; Stage 4 self-correction was merged into Stage 3 and is now rule-based only. Real VPR cost is likely below the doc's current ~$0.32 estimate.
Confirmed safe
The model swap itself is trivial. One CDK constant (STRATEGIC_MODEL_ID) plus cdk deploy — no application code changes required for the ID change alone.
07
Rollout plan
Fix both blockers in §6 (temperature removal, test assertion) — this is required work regardless of timing.
Canary Sonnet 5 on VPR generation only, gated behind your existing CostUSD / VPRCostUSD CloudWatch metrics and the MAX_COST_PER_APPLICATION alert already in code — you have the instrumentation, you just haven't used it for this yet.
Measure, don't estimate. Compare real per-application VPR cost, not the cost-model doc's estimate, before and after.
Weigh the quality signal — meta-evaluation gate pass rate, regeneration-loop frequency, or user-reported VPR usefulness — alongside the cost delta before wider rollout.
Decide on timing consciously. Migrating now lands inside the favorable intro-pricing window (through 2026-08-31); migrating after that reverts to standard pricing with the tokenizer cost increase intact. If you're not ready to fix the temperature blocker in the next ~8 weeks, the pricing argument for rushing weakens on its own.
08
Open questions for the team
Is the Gap Analysis Haiku fallback a bug, or has Haiku quietly proven "good enough" there — and if the latter, should the docs just say so?
What's today's real VPR retry/self-correction failure rate? A Sonnet 5 reduction there is savings the token math can't see.
What quality signal actually defines "worth it" for this upgrade — user-reported usefulness, or downstream interview/offer conversion — given VPR is the product's core differentiator, not a commodity feature?
Your own cost-model doc already flags prompt-caching gaps on Gap Analysis, Cover Letter, and Interview Prep, plus a likely output-truncating max_tokens=2500 on Interview Prep. Those are known, quantifiable savings independent of any model choice — cheaper to fix than to migrate. Worth doing first?
Is it worth waiting for broader field reports on Sonnet 5 quality before committing production VPR traffic to a model that's brand new as of this writing?
Sources: 4 independent code audits · infra/careervp/constants.py · logic/vpr_generator.py · logic/gap_analysis.py · docs/cost-model/cost-model.md · tests/unit/test_llm_client.py
Confidence: high on code wiring (4× corroborated) · low on dollar figures (mostly estimated, not measured)