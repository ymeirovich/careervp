"""
MIGRATION GUIDE: Instrumenting Existing CareerVP Agents
========================================================

TIME ESTIMATE: ~20 minutes per agent (8 agents = ~3 hours total)

The change to each agent is minimal — replace the Anthropic() client
with TrackedAnthropicClient(). Everything else is unchanged.
"""

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: BEFORE (existing pattern in every agent)
# ─────────────────────────────────────────────────────────────────────────────

BEFORE = """
import os
from anthropic import Anthropic

client = Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])

def lambda_handler(event, context):
    application_id = event['application_id']
    # ... build prompt ...

    response = client.messages.create(
        model=os.environ['MODEL_NAME'],
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    output = response.content[0].text
    return {"application_id": application_id, "output": output}
"""

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: AFTER (instrumented — 3 lines changed, 1 line added)
# ─────────────────────────────────────────────────────────────────────────────

AFTER = """
import os
from token_tracker import TrackedAnthropicClient   # ← LINE 1: changed import

def lambda_handler(event, context):
    application_id = event['application_id']
    user_id = event.get('user_id', 'unknown')       # ← LINE 2: ensure user_id in event

    tracker = TrackedAnthropicClient(               # ← LINE 3: replace Anthropic()
        agent_name="vpr-strategist",                #   set agent name here
        application_id=application_id,
        user_id=user_id,
    )

    # ... build prompt (unchanged) ...

    response = tracker.create(                      # ← LINE 4: .create() instead of client.messages.create()
        model=os.environ['MODEL_NAME'],
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
        _stage="primary_generation",                # optional: label this call
    )
    output = response.content[0].text

    # Optional: include totals in return value for Step Functions visibility
    totals = tracker.get_totals()
    return {
        "application_id": application_id,
        "output": output,
        "agent_totals": totals,
    }
"""

# ─────────────────────────────────────────────────────────────────────────────
# AGENT NAME REGISTRY — use these exact strings for consistency
# ─────────────────────────────────────────────────────────────────────────────

AGENT_NAMES = {
    "cv_parser": "cv-parser",
    "company_research": "company-research",
    "gap_analysis_question_gen": "gap-analysis-question-generator",
    "vpr_strategist": "vpr-strategist",
    "cv_tailor": "cv-tailor",
    "cover_letter_writer": "cover-letter-writer",
    "interview_prep_generator": "interview-prep-generator",
    "quality_validator": "quality-validator",
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP FUNCTIONS: ensure user_id flows through all states
# ─────────────────────────────────────────────────────────────────────────────

STEP_FUNCTIONS_INPUT_EXAMPLE = """
// Add user_id to your Step Functions execution input
// It will be passed through to every Lambda via the event

{
  "application_id": "app_abc123",
  "user_id": "user_xyz789",         // <-- add this field
  "cv_id": "cv_001",
  "company_name": "Acme Corp",
  // ... rest of existing fields
}

// In your state machine definition, pass it through each state:
"Parameters": {
    "application_id.$": "$.application_id",
    "user_id.$": "$.user_id",           // <-- thread this through every state
    "cv_facts.$": "$.cv_facts",
    // ...
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# COGNITO INTEGRATION: get user_id from JWT claims in API Gateway
# ─────────────────────────────────────────────────────────────────────────────

COGNITO_USER_ID_EXTRACTION = """
# In your API Gateway → Lambda integration (orchestrator entry point):

def lambda_handler(event, context):
    # API Gateway passes Cognito claims in requestContext
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})

    # Use Cognito 'sub' (stable user UUID) as user_id
    user_id = claims.get('sub', 'anonymous')

    # Or use email if preferred (less stable across account recreation)
    # user_id = claims.get('email', 'anonymous')

    # Pass into Step Functions execution input
    sfn.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        input=json.dumps({
            "application_id": generate_application_id(),
            "user_id": user_id,          # <-- from Cognito
            # ... rest of fields
        })
    )
"""

# ─────────────────────────────────────────────────────────────────────────────
# CHECKLIST
# ─────────────────────────────────────────────────────────────────────────────

MIGRATION_CHECKLIST = """
Infrastructure (one-time):
  [ ] Deploy TokenUsageTable (DynamoDB)
  [ ] Deploy DailyCostRollupTable (DynamoDB)
  [ ] Deploy TokenTrackerLayer (Lambda Layer)
  [ ] Deploy DailyRollupFunction + EventBridge schedule
  [ ] Deploy CostAlertTopic (SNS) + subscribe your email
  [ ] Deploy CloudWatch alarms (VPRCostSpike, DailyTokenBudget)
  [ ] Add AgentTokenTrackingPolicy to all agent Lambda execution roles

Per-agent changes (~20 min each):
  [ ] cv-parser              — add TrackedAnthropicClient
  [ ] company-research       — add TrackedAnthropicClient
  [ ] gap-analysis           — add TrackedAnthropicClient, label self-correction stages
  [ ] vpr-strategist         — add TrackedAnthropicClient, label all 3 possible calls
  [ ] cv-tailor              — add TrackedAnthropicClient, label 3-step verification
  [ ] cover-letter-writer    — add TrackedAnthropicClient
  [ ] interview-prep         — add TrackedAnthropicClient
  [ ] quality-validator      — add TrackedAnthropicClient if using AI checks

Step Functions:
  [ ] Add user_id to execution input schema
  [ ] Thread user_id through all state Parameters

API Gateway / Cognito:
  [ ] Extract user sub from JWT claims in orchestrator Lambda
  [ ] Pass user_id into Step Functions execution input

Validation:
  [ ] Run one test application end-to-end
  [ ] Verify records appear in careervp-token-usage table
  [ ] Verify CloudWatch metrics appear in CareerVP/TokenUsage namespace
  [ ] Trigger daily rollup manually: invoke careervp-daily-cost-rollup
  [ ] Verify rollup records in careervp-daily-cost-rollup table
  [ ] Confirm SNS alert email arrives (set threshold to $0.01 for test)
"""
