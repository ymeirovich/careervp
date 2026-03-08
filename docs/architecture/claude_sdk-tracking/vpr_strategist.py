"""
agents/vpr_strategist.py  —  VPR Strategist Agent (fully instrumented)

Demonstrates the complete instrumentation pattern:
  - TrackedAnthropicClient wraps every API call
  - Each of the 6 internal stages tracked separately
  - Self-correction loop tracked with stage label
  - Totals written back to the application DynamoDB record
  - Zero changes to prompts or outputs
"""

import os
import json
import logging
from typing import Any

from token_tracker import TrackedAnthropicClient  # from Lambda layer

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

MODEL = os.environ.get("MODEL_NAME", "claude-sonnet-4-5-20250929")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "4000"))

# DynamoDB for persisting results (existing infra)
import boto3

dynamodb = boto3.resource("dynamodb")
apps_table = dynamodb.Table(
    os.environ.get("APPLICATIONS_TABLE", "careervp-applications")
)


def lambda_handler(event: dict, context: Any) -> dict:
    application_id = event["application_id"]
    user_id = event["user_id"]

    # ── Instantiate tracked client ────────────────────────────────────────────
    # This is the ONLY change to existing agent code.
    # Replace:  client = Anthropic(api_key=...)
    # With:     tracker = TrackedAnthropicClient(...)
    tracker = TrackedAnthropicClient(
        agent_name="vpr-strategist",
        application_id=application_id,
        user_id=user_id,
        model=MODEL,
    )

    # ── Build the prompt (unchanged from existing architecture) ───────────────
    cv_facts = event["cv_facts"]
    gap_responses = event["gap_responses"]
    job_requirements = event["job_requirements"]
    company_research = event["company_research"]

    prompt = VPR_GENERATION_PROMPT.format(
        cv_facts_json=json.dumps(cv_facts, indent=2),
        gap_responses_json=json.dumps(gap_responses, indent=2),
        job_requirements_json=json.dumps(job_requirements, indent=2),
        company_research_json=json.dumps(company_research, indent=2),
    )

    # ── Primary generation (Stage 1-5 in one call) ───────────────────────────
    # _stage label is stripped by TrackedAnthropicClient before the API call
    response = tracker.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
        _stage="primary_generation",
        _extra_metadata={"prompt_version": "v1.0", "job_title": event.get("job_title")},
    )

    vpr_content = response.content[0].text

    # ── Stage 6: Meta-evaluation / self-correction ────────────────────────────
    meta_prompt = f"""
Review this Value Proposition Report and make it 20% more persuasive:

{vpr_content}

Apply improvements and output the final version only.
"""
    meta_response = tracker.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": meta_prompt}],
        _stage="stage6_meta_evaluation",  # tracked separately in DynamoDB
    )

    final_vpr = meta_response.content[0].text

    # ── Quality check — conditional third call ────────────────────────────────
    word_count = len(final_vpr.split())
    if word_count < 1200:
        logger.warning(f"VPR too short ({word_count} words), requesting expansion")
        expand_response = tracker.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "user", "content": meta_prompt},
                {"role": "assistant", "content": final_vpr},
                {
                    "role": "user",
                    "content": "Expand the Evidence & Alignment Matrix section to reach 1500+ words.",
                },
            ],
            _stage="self_correction_expansion",  # clearly labelled in tracking
        )
        final_vpr = expand_response.content[0].text

    # ── Get accumulated totals for this invocation ────────────────────────────
    totals = tracker.get_totals()
    # e.g. {"input_tokens": 22400, "output_tokens": 14800, "total_cost_usd": 0.289}

    logger.info(
        f"[vpr-strategist] COMPLETE app={application_id} "
        f"total_in={totals['input_tokens']} "
        f"total_out={totals['output_tokens']} "
        f"total_cost=${totals['total_cost_usd']:.4f} "
        f"api_calls={tracker._call_count}"
    )

    # ── Persist totals into application record ────────────────────────────────
    # Adds per-agent cost breakdown to existing application item in DynamoDB
    _update_application_costs(application_id, "vpr-strategist", totals)

    return {
        "application_id": application_id,
        "vpr_content": final_vpr,
        "agent_totals": totals,  # passed downstream via Step Functions
        # Note: detailed per-call records already in careervp-token-usage table
    }


def _update_application_costs(application_id: str, agent_name: str, totals: dict):
    """
    Update the application's cost_breakdown map in DynamoDB.
    Uses update expression to add agent costs without overwriting other agents.
    """
    import decimal

    try:
        apps_table.update_item(
            Key={"applicationId": application_id},
            UpdateExpression=(
                "SET cost_breakdown.#agent = :totals, "
                "total_cost = if_not_exists(total_cost, :zero) + :cost"
            ),
            ExpressionAttributeNames={"#agent": agent_name},
            ExpressionAttributeValues={
                ":totals": {
                    k: decimal.Decimal(str(v)) if isinstance(v, float) else v
                    for k, v in totals.items()
                },
                ":cost": decimal.Decimal(str(totals["total_cost_usd"])),
                ":zero": decimal.Decimal("0"),
            },
        )
    except Exception as e:
        logger.error(f"Failed to update application costs: {e}")


# ── Prompt template (unchanged from architecture doc) ─────────────────────────
VPR_GENERATION_PROMPT = """You are an expert career strategist creating a Value Proposition Report.

Follow this 6-STAGE PROCESS exactly:

STAGE 1: COMPANY & ROLE RESEARCH
Analyze the company research and identify:
- 3-5 strategic priorities or current challenges
- 5-7 role success criteria from job posting

COMPANY RESEARCH:
{company_research_json}

JOB REQUIREMENTS:
{job_requirements_json}

OUTPUT (Internal): Strategic priorities list + role criteria

---

STAGE 2: CANDIDATE ANALYSIS
CV FACTS:
{cv_facts_json}

GAP ANALYSIS RESPONSES (PRIMARY EVIDENCE):
{gap_responses_json}

OUTPUT (Internal): Differentiators list + career narrative

---

STAGE 3: ALIGNMENT MAPPING
Create reasoning scaffold table with 5-7 minimum alignments.

---

STAGE 4: SELF-CORRECTION & META REVIEW
Before proceeding, perform internal critique.

---

STAGE 5: GENERATE REPORT
## 1. EXECUTIVE SUMMARY (200-250 words)
## 2. EVIDENCE & ALIGNMENT MATRIX (600-800 words)
## 3. STRATEGIC DIFFERENTIATORS (300-400 words)
## 4. GAP MITIGATION STRATEGIES (200-300 words)
## 5. CULTURAL FIT ANALYSIS (150-200 words)
## 6. RECOMMENDED TALKING POINTS (150-200 words)

OUTPUT FORMAT: Professional markdown, 1,500-2,000 words.
Generate VPR now:
"""
