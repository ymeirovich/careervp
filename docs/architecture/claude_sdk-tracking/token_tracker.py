"""
careervp/lambda_layer/token_tracker.py

Shared Lambda Layer — imported by every agent Lambda.

HOW IT WORKS:
  - The Anthropic SDK returns response.usage natively on every API call.
    These token counts are FREE — they do NOT count against your token quota
    and do NOT require any prompt changes.
  - response._request_id is the Anthropic request ID (for cross-referencing
    Anthropic's own usage dashboard if needed).
  - This layer captures that usage, calculates cost, and writes one
    DynamoDB record + one CloudWatch metric per agent invocation.
  - Step Functions passes application_id and agent_name through the
    event payload — no external tag system needed.

ZERO PROMPT IMPACT: Nothing is added to the prompt or response.
"""

import os
import time
import json
import decimal
import functools
import logging
from typing import Optional, Callable
from datetime import datetime, timezone

import boto3
from anthropic import Anthropic

logger = logging.getLogger(__name__)

# ── Pricing (per 1K tokens, USD) ─────────────────────────────────────────────
# Update these if Anthropic changes pricing
MODEL_PRICING = {
    "claude-haiku-4-5-20251001":   {"input": 0.0008, "output": 0.004,
                                    "cache_write": 0.001, "cache_read": 0.00008},
    "claude-sonnet-4-5-20250929":  {"input": 0.003,  "output": 0.015,
                                    "cache_write": 0.00375, "cache_read": 0.0003},
    # Fallback for unknown models
    "default":                     {"input": 0.003,  "output": 0.015,
                                    "cache_write": 0.00375, "cache_read": 0.0003},
}

# ── AWS clients (module-level = reused across warm invocations) ───────────────
_dynamodb = None
_cloudwatch = None

def _get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return _dynamodb

def _get_cloudwatch():
    global _cloudwatch
    if _cloudwatch is None:
        _cloudwatch = boto3.client("cloudwatch", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return _cloudwatch


# ── Cost calculation ──────────────────────────────────────────────────────────

def calculate_cost(model: str, input_tokens: int, output_tokens: int,
                   cache_write_tokens: int = 0, cache_read_tokens: int = 0) -> dict:
    """
    Returns a cost breakdown dict with individual line items and total_usd.
    Uses Decimal for DynamoDB compatibility.
    """
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])

    input_cost        = (input_tokens        / 1000) * pricing["input"]
    output_cost       = (output_tokens       / 1000) * pricing["output"]
    cache_write_cost  = (cache_write_tokens  / 1000) * pricing["cache_write"]
    cache_read_cost   = (cache_read_tokens   / 1000) * pricing["cache_read"]
    total             = input_cost + output_cost + cache_write_cost + cache_read_cost

    return {
        "input_cost_usd":       round(input_cost,       6),
        "output_cost_usd":      round(output_cost,      6),
        "cache_write_cost_usd": round(cache_write_cost, 6),
        "cache_read_cost_usd":  round(cache_read_cost,  6),
        "total_usd":            round(total,            6),
    }


# ── DynamoDB writer ───────────────────────────────────────────────────────────

def record_usage(
    application_id: str,
    user_id: str,
    agent_name: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_write_tokens: int = 0,
    cache_read_tokens: int = 0,
    anthropic_request_id: Optional[str] = None,
    duration_ms: Optional[int] = None,
    success: bool = True,
    error_type: Optional[str] = None,
    stage: Optional[str] = None,          # e.g. "self_correction_attempt_2"
    extra_metadata: Optional[dict] = None
) -> dict:
    """
    Write one usage record to DynamoDB and emit CloudWatch metrics.

    DynamoDB table: careervp-token-usage
      PK: application_id
      SK: {timestamp}#{agent_name}  (allows multiple calls per agent per app)

    Returns the cost breakdown dict.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    timestamp_ms = int(time.time() * 1000)

    cost = calculate_cost(model, input_tokens, output_tokens,
                          cache_write_tokens, cache_read_tokens)

    record = {
        # Keys
        "application_id":    application_id,
        "sk":                f"{timestamp_ms}#{agent_name}",

        # Identity
        "user_id":           user_id,
        "agent_name":        agent_name,
        "model":             model,
        "stage":             stage or "primary",
        "timestamp":         now_iso,
        "timestamp_ms":      timestamp_ms,

        # Tokens — direct from response.usage, zero prompt overhead
        "input_tokens":           input_tokens,
        "output_tokens":          output_tokens,
        "cache_write_tokens":     cache_write_tokens,
        "cache_read_tokens":      cache_read_tokens,
        "total_tokens":           input_tokens + output_tokens,

        # Cost
        **{k: decimal.Decimal(str(v)) for k, v in cost.items()},

        # Diagnostics
        "success":               success,
        "error_type":            error_type,
        "duration_ms":           duration_ms,
        "anthropic_request_id":  anthropic_request_id,  # links to Anthropic dashboard
    }

    if extra_metadata:
        record["extra_metadata"] = json.dumps(extra_metadata)

    # Write to DynamoDB (fire-and-forget pattern; errors logged not raised)
    try:
        table = _get_dynamodb().Table(
            os.environ.get("TOKEN_USAGE_TABLE", "careervp-token-usage")
        )
        table.put_item(Item=record)
    except Exception as e:
        logger.error(f"[token_tracker] DynamoDB write failed: {e}")

    # Emit CloudWatch custom metrics
    _emit_cloudwatch_metrics(agent_name, model, input_tokens,
                              output_tokens, cost["total_usd"],
                              success, duration_ms)

    return cost


# ── CloudWatch metrics ────────────────────────────────────────────────────────

def _emit_cloudwatch_metrics(agent_name: str, model: str,
                              input_tokens: int, output_tokens: int,
                              cost_usd: float, success: bool,
                              duration_ms: Optional[int]):
    """
    Emit metrics to CloudWatch namespace 'CareerVP/TokenUsage'.
    Dimensions: AgentName, Model — enables per-agent filtering in dashboards.
    """
    namespace = "CareerVP/TokenUsage"
    dims_agent = [{"Name": "AgentName", "Value": agent_name}]
    dims_model = [{"Name": "Model",     "Value": model}]
    dims_both  = [{"Name": "AgentName", "Value": agent_name},
                  {"Name": "Model",     "Value": model}]

    metric_data = [
        # Token counts
        {"MetricName": "InputTokens",  "Dimensions": dims_both,
         "Value": input_tokens,  "Unit": "Count"},
        {"MetricName": "OutputTokens", "Dimensions": dims_both,
         "Value": output_tokens, "Unit": "Count"},
        {"MetricName": "TotalTokens",  "Dimensions": dims_both,
         "Value": input_tokens + output_tokens, "Unit": "Count"},

        # Cost (stored as milli-dollars to stay in numeric range)
        {"MetricName": "CostMilliUSD", "Dimensions": dims_both,
         "Value": cost_usd * 1000, "Unit": "None"},

        # Per-agent aggregates (useful for per-agent alarms)
        {"MetricName": "InputTokens",  "Dimensions": dims_agent,
         "Value": input_tokens,  "Unit": "Count"},
        {"MetricName": "OutputTokens", "Dimensions": dims_agent,
         "Value": output_tokens, "Unit": "Count"},
        {"MetricName": "CostMilliUSD", "Dimensions": dims_agent,
         "Value": cost_usd * 1000, "Unit": "None"},

        # Success / failure
        {"MetricName": "InvocationSuccess", "Dimensions": dims_agent,
         "Value": 1 if success else 0, "Unit": "Count"},
        {"MetricName": "InvocationFailure", "Dimensions": dims_agent,
         "Value": 0 if success else 1, "Unit": "Count"},
    ]

    if duration_ms is not None:
        metric_data.append({
            "MetricName": "DurationMs", "Dimensions": dims_agent,
            "Value": duration_ms, "Unit": "Milliseconds"
        })

    try:
        cw = _get_cloudwatch()
        # CloudWatch accepts max 20 metrics per call
        for i in range(0, len(metric_data), 20):
            cw.put_metric_data(Namespace=namespace,
                               MetricData=metric_data[i:i+20])
    except Exception as e:
        logger.error(f"[token_tracker] CloudWatch emit failed: {e}")


# ── Decorator ─────────────────────────────────────────────────────────────────

def track_tokens(agent_name: str, model_env_var: str = "MODEL_NAME"):
    """
    Decorator for agent Lambda handlers.

    Usage:
        @track_tokens("vpr-strategist")
        def lambda_handler(event, context):
            ...

    The decorated function must:
      - Accept (event, context) as args
      - Have event["application_id"] and event["user_id"]
      - Return a dict with key "usage" containing an Anthropic Usage object
        OR set event["_claude_response"] to the raw Anthropic response object

    Alternatively, use the TrackedAnthropicClient below for automatic capture.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(event, context):
            start_ms = int(time.time() * 1000)
            application_id = event.get("application_id", "unknown")
            user_id        = event.get("user_id", "unknown")
            model          = os.environ.get(model_env_var, "unknown")

            try:
                result = func(event, context)
                duration_ms = int(time.time() * 1000) - start_ms

                # Extract usage from result if agent stored it
                usage_data = result.get("_token_usage") if isinstance(result, dict) else None
                if usage_data:
                    record_usage(
                        application_id=application_id,
                        user_id=user_id,
                        agent_name=agent_name,
                        model=model,
                        input_tokens=usage_data.get("input_tokens", 0),
                        output_tokens=usage_data.get("output_tokens", 0),
                        cache_write_tokens=usage_data.get("cache_creation_input_tokens", 0),
                        cache_read_tokens=usage_data.get("cache_read_input_tokens", 0),
                        anthropic_request_id=usage_data.get("request_id"),
                        duration_ms=duration_ms,
                        stage=usage_data.get("stage"),
                        extra_metadata=usage_data.get("extra_metadata"),
                    )
                    # Clean internal key before returning to Step Functions
                    result.pop("_token_usage", None)

                return result

            except Exception as e:
                duration_ms = int(time.time() * 1000) - start_ms
                record_usage(
                    application_id=application_id,
                    user_id=user_id,
                    agent_name=agent_name,
                    model=model,
                    input_tokens=0,
                    output_tokens=0,
                    duration_ms=duration_ms,
                    success=False,
                    error_type=type(e).__name__,
                )
                raise

        return wrapper
    return decorator


# ── Tracked Anthropic client ──────────────────────────────────────────────────

class TrackedAnthropicClient:
    """
    Thin wrapper around Anthropic() that auto-captures usage on every
    messages.create() call and accumulates totals for the current invocation.

    Usage in any agent Lambda:

        from token_tracker import TrackedAnthropicClient

        tracker = TrackedAnthropicClient(
            agent_name="vpr-strategist",
            application_id=event["application_id"],
            user_id=event["user_id"],
        )

        response = tracker.create(
            model=MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        # usage auto-recorded — no extra code needed

        # If agent does self-correction (multiple calls), each is tracked
        # with its stage label:
        response2 = tracker.create(
            model=MODEL,
            max_tokens=2000,
            messages=[...],
            _stage="self_correction_attempt_1",   # custom kwarg, stripped before API call
        )

        # At end of handler, get totals for DynamoDB application record
        totals = tracker.get_totals()
        # {"input_tokens": 12500, "output_tokens": 8200, "total_cost_usd": 0.247}
    """

    def __init__(self, agent_name: str, application_id: str, user_id: str,
                 model: Optional[str] = None):
        self.agent_name     = agent_name
        self.application_id = application_id
        self.user_id        = user_id
        self.model          = model or os.environ.get("MODEL_NAME", "unknown")
        self._client        = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self._call_count    = 0
        self._totals        = {
            "input_tokens": 0, "output_tokens": 0,
            "cache_write_tokens": 0, "cache_read_tokens": 0,
            "total_cost_usd": 0.0,
        }

    def create(self, **kwargs) -> object:
        """
        Calls client.messages.create(**kwargs).
        Intercepts response.usage — zero tokens added to prompt.
        Strips private kwargs (_stage, _extra_metadata) before API call.
        """
        stage          = kwargs.pop("_stage", f"call_{self._call_count + 1}")
        extra_metadata = kwargs.pop("_extra_metadata", None)
        model          = kwargs.get("model", self.model)

        start_ms = int(time.time() * 1000)
        response = self._client.messages.create(**kwargs)
        duration_ms = int(time.time() * 1000) - start_ms

        self._call_count += 1
        usage = response.usage

        # Extract all token fields (cache fields present only if caching enabled)
        input_tokens       = getattr(usage, "input_tokens", 0)
        output_tokens      = getattr(usage, "output_tokens", 0)
        cache_write        = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cache_read         = getattr(usage, "cache_read_input_tokens", 0) or 0
        request_id         = getattr(response, "_request_id", None)

        # Record this individual call
        cost = record_usage(
            application_id=self.application_id,
            user_id=self.user_id,
            agent_name=self.agent_name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_write_tokens=cache_write,
            cache_read_tokens=cache_read,
            anthropic_request_id=request_id,
            duration_ms=duration_ms,
            stage=stage,
            extra_metadata=extra_metadata,
        )

        # Accumulate totals
        self._totals["input_tokens"]       += input_tokens
        self._totals["output_tokens"]      += output_tokens
        self._totals["cache_write_tokens"] += cache_write
        self._totals["cache_read_tokens"]  += cache_read
        self._totals["total_cost_usd"]     += cost["total_usd"]

        logger.info(
            f"[{self.agent_name}] stage={stage} "
            f"in={input_tokens} out={output_tokens} "
            f"cost=${cost['total_usd']:.5f} "
            f"request_id={request_id}"
        )

        return response

    def get_totals(self) -> dict:
        """Return accumulated token/cost totals for this Lambda invocation."""
        return dict(self._totals)
