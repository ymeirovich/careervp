"""
functions/daily_rollup/lambda_function.py

Runs at 01:00 UTC daily via EventBridge.
  1. Scans yesterday's token-usage records
  2. Aggregates by agent, model, and user
  3. Writes summary rows to careervp-daily-cost-rollup
  4. Publishes SNS alert if daily cost exceeds threshold
  5. Optionally writes anomaly detection data to CloudWatch

This is what powers your cost dashboard and prevents billing surprises.
"""

import os
import logging
import decimal
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import Any

import boto3
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")
cloudwatch = boto3.client("cloudwatch")

TOKEN_USAGE_TABLE = os.environ["TOKEN_USAGE_TABLE"]
DAILY_ROLLUP_TABLE = os.environ["DAILY_ROLLUP_TABLE"]
ALERT_TOPIC_ARN = os.environ.get("ALERT_TOPIC_ARN")

# Alert if daily AI cost exceeds this (USD)
DAILY_COST_ALERT_THRESHOLD_USD = float(os.environ.get("DAILY_COST_THRESHOLD", "50.0"))

# Pricing for cost calculation in rollup
MODEL_PRICING = {
    "claude-haiku-4-5-20251001": {"input": 0.0008, "output": 0.004},
    "claude-sonnet-4-5-20250929": {"input": 0.003, "output": 0.015},
    "default": {"input": 0.003, "output": 0.015},
}


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Aggregate yesterday's token usage.
    Can also be triggered manually with {"target_date": "2026-02-24"}.
    """
    target_date_str = event.get("target_date")
    if target_date_str:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    else:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    logger.info(f"Rolling up token usage for {target_date}")

    # ── Scan token-usage table for target date ────────────────────────────────
    # The SK starts with {timestamp_ms}, so we use a range condition.
    # timestamp_ms for start/end of day:
    day_start_ms = int(
        datetime(
            target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc
        ).timestamp()
        * 1000
    )
    day_end_ms = day_start_ms + 86_400_000  # +24 hours

    table = dynamodb.Table(TOKEN_USAGE_TABLE)
    rollup = dynamodb.Table(DAILY_ROLLUP_TABLE)

    # Scan with filter — for large tables, replace with GSI on date
    records = _scan_day(table, day_start_ms, day_end_ms)
    logger.info(f"Found {len(records)} usage records for {target_date}")

    if not records:
        logger.info("No records found, skipping rollup")
        return {"date": str(target_date), "records_processed": 0}

    # ── Aggregate ─────────────────────────────────────────────────────────────
    by_agent = defaultdict(lambda: _empty_bucket())
    by_model = defaultdict(lambda: _empty_bucket())
    by_user = defaultdict(lambda: _empty_bucket())
    daily_totals = _empty_bucket()

    for rec in records:
        agent = rec.get("agent_name", "unknown")
        model = rec.get("model", "unknown")
        uid = rec.get("user_id", "unknown")
        cost = float(rec.get("total_usd", 0))

        in_tok = int(rec.get("input_tokens", 0))
        out_tok = int(rec.get("output_tokens", 0))
        cw_tok = int(rec.get("cache_write_tokens", 0))
        cr_tok = int(rec.get("cache_read_tokens", 0))

        for bucket in [by_agent[agent], by_model[model], by_user[uid], daily_totals]:
            bucket["input_tokens"] += in_tok
            bucket["output_tokens"] += out_tok
            bucket["cache_write_tokens"] += cw_tok
            bucket["cache_read_tokens"] += cr_tok
            bucket["total_tokens"] += in_tok + out_tok
            bucket["total_cost_usd"] += cost
            bucket["call_count"] += 1

        # Track self-correction rate
        stage = rec.get("stage", "primary")
        if "self_correction" in stage or "attempt" in stage:
            by_agent[agent]["self_correction_calls"] += 1

        # Track failures
        if not rec.get("success", True):
            by_agent[agent]["failure_count"] += 1

    # ── Write rollup records ──────────────────────────────────────────────────
    date_str = str(target_date)
    with rollup.batch_writer() as batch:
        for agent, data in by_agent.items():
            batch.put_item(
                Item={
                    "date_agent": f"{date_str}#{agent}",
                    "model": "ALL",
                    "date": date_str,
                    "agent_name": agent,
                    **_to_decimal(data),
                    "self_correction_rate": decimal.Decimal(
                        str(
                            round(
                                data["self_correction_calls"]
                                / max(data["call_count"], 1),
                                3,
                            )
                        )
                    ),
                }
            )

        for model, data in by_model.items():
            batch.put_item(
                Item={
                    "date_agent": f"{date_str}#model:{model}",
                    "model": model,
                    "date": date_str,
                    **_to_decimal(data),
                }
            )

        # Daily total summary row
        batch.put_item(
            Item={
                "date_agent": f"{date_str}#DAILY_TOTAL",
                "model": "ALL",
                "date": date_str,
                "agent_name": "DAILY_TOTAL",
                **_to_decimal(daily_totals),
            }
        )

    logger.info(
        f"Rollup complete: {len(records)} calls, "
        f"{daily_totals['total_tokens']:,} tokens, "
        f"${daily_totals['total_cost_usd']:.4f}"
    )

    # ── Alert if daily cost threshold exceeded ────────────────────────────────
    if daily_totals["total_cost_usd"] > DAILY_COST_ALERT_THRESHOLD_USD:
        _send_cost_alert(date_str, daily_totals, by_agent)

    # ── CloudWatch anomaly detection datapoints ───────────────────────────────
    _emit_rollup_metrics(date_str, daily_totals, by_agent)

    return {
        "date": str(target_date),
        "records_processed": len(records),
        "total_tokens": daily_totals["total_tokens"],
        "total_cost_usd": daily_totals["total_cost_usd"],
        "agents_active": list(by_agent.keys()),
    }


def _scan_day(table, day_start_ms: int, day_end_ms: int) -> list:
    """Scan token-usage table for records in the target day."""
    items = []
    kwargs = {
        "FilterExpression": (Attr("timestamp_ms").between(day_start_ms, day_end_ms - 1))
    }
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        last = resp.get("LastEvaluatedKey")
        if not last:
            break
        kwargs["ExclusiveStartKey"] = last
    return items


def _empty_bucket() -> dict:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_write_tokens": 0,
        "cache_read_tokens": 0,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "call_count": 0,
        "self_correction_calls": 0,
        "failure_count": 0,
    }


def _to_decimal(d: dict) -> dict:
    return {
        k: decimal.Decimal(str(round(v, 6))) if isinstance(v, float) else v
        for k, v in d.items()
    }


def _send_cost_alert(date: str, totals: dict, by_agent: dict):
    if not ALERT_TOPIC_ARN:
        return
    agent_lines = "\n".join(
        f"  {agent}: ${data['total_cost_usd']:.4f} "
        f"({data['call_count']} calls, "
        f"{data['self_correction_calls']} self-corrections)"
        for agent, data in sorted(
            by_agent.items(), key=lambda x: -x[1]["total_cost_usd"]
        )
    )
    message = f"""
CareerVP Daily Cost Alert — {date}

Total cost: ${totals["total_cost_usd"]:.4f}
Threshold:  ${DAILY_COST_ALERT_THRESHOLD_USD:.2f}
Total tokens: {totals["total_tokens"]:,}
Total API calls: {totals["call_count"]}

Cost by agent:
{agent_lines}

Self-correction rate may be inflating costs. Check vpr-strategist and gap-analysis logs.
"""
    sns.publish(
        TopicArn=ALERT_TOPIC_ARN,
        Subject=f"[CareerVP] Daily cost ${totals['total_cost_usd']:.2f} exceeded threshold",
        Message=message,
    )
    logger.warning(f"Cost alert sent: ${totals['total_cost_usd']:.4f}")


def _emit_rollup_metrics(date: str, totals: dict, by_agent: dict):
    """
    Publish daily aggregate metrics to CloudWatch for trend analysis.
    These appear in CloudWatch dashboards as once-per-day datapoints.
    """
    metric_data = [
        {
            "MetricName": "DailyTotalCostMilliUSD",
            "Value": totals["total_cost_usd"] * 1000,
            "Unit": "None",
            "Dimensions": [{"Name": "Scope", "Value": "Daily"}],
        },
        {
            "MetricName": "DailyTotalTokens",
            "Value": totals["total_tokens"],
            "Unit": "Count",
            "Dimensions": [{"Name": "Scope", "Value": "Daily"}],
        },
        {
            "MetricName": "DailyAPICallCount",
            "Value": totals["call_count"],
            "Unit": "Count",
            "Dimensions": [{"Name": "Scope", "Value": "Daily"}],
        },
    ]
    for agent, data in by_agent.items():
        metric_data.extend(
            [
                {
                    "MetricName": "DailyAgentCostMilliUSD",
                    "Value": data["total_cost_usd"] * 1000,
                    "Unit": "None",
                    "Dimensions": [{"Name": "AgentName", "Value": agent}],
                },
                {
                    "MetricName": "DailySelfCorrectionRate",
                    "Value": data["self_correction_calls"] / max(data["call_count"], 1),
                    "Unit": "None",
                    "Dimensions": [{"Name": "AgentName", "Value": agent}],
                },
            ]
        )

    for i in range(0, len(metric_data), 20):
        cloudwatch.put_metric_data(
            Namespace="CareerVP/DailyRollup",
            MetricData=metric_data[i : i + 20],
        )
