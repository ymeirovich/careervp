"""
dashboards/query_examples.py

How to retrieve token tracking data for dashboards, reports, and debugging.
All queries use the tables created by token_tracking_tables.py.

Run these ad-hoc from a Lambda, from the AWS console, or from a local
script with appropriate IAM credentials.
"""

import boto3
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")

TOKEN_USAGE_TABLE = "careervp-token-usage"
DAILY_ROLLUP_TABLE = "careervp-daily-cost-rollup"


# ── 1. Per-application full breakdown ─────────────────────────────────────────


def get_application_cost_breakdown(application_id: str) -> dict:
    """
    All agent calls for a single application.
    Returns each call with tokens, cost, stage, and duration.

    Use case: "Show me exactly what this application cost and why."
    """
    table = dynamodb.Table(TOKEN_USAGE_TABLE)
    resp = table.query(
        KeyConditionExpression=Key("application_id").eq(application_id),
        ScanIndexForward=True,  # chronological
    )
    items = resp["Items"]

    # Group by agent
    by_agent = {}
    for item in items:
        agent = item["agent_name"]
        if agent not in by_agent:
            by_agent[agent] = {
                "calls": [],
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost_usd": 0.0,
                "self_correction_calls": 0,
            }
        entry = by_agent[agent]
        entry["calls"].append(
            {
                "stage": item.get("stage"),
                "input_tokens": int(item.get("input_tokens", 0)),
                "output_tokens": int(item.get("output_tokens", 0)),
                "cost_usd": float(item.get("total_usd", 0)),
                "duration_ms": item.get("duration_ms"),
                "timestamp": item.get("timestamp"),
                "anthropic_request_id": item.get("anthropic_request_id"),
            }
        )
        entry["total_input_tokens"] += int(item.get("input_tokens", 0))
        entry["total_output_tokens"] += int(item.get("output_tokens", 0))
        entry["total_cost_usd"] += float(item.get("total_usd", 0))
        if "self_correction" in str(item.get("stage", "")):
            entry["self_correction_calls"] += 1

    grand_total_cost = sum(v["total_cost_usd"] for v in by_agent.values())

    return {
        "application_id": application_id,
        "total_cost_usd": round(grand_total_cost, 6),
        "total_api_calls": len(items),
        "agents": by_agent,
    }


# ── 2. Per-user monthly cost ───────────────────────────────────────────────────


def get_user_monthly_cost(user_id: str, year: int, month: int) -> dict:
    """
    All token usage for a user in a calendar month.

    Use case: "Is this user profitable? How many applications did they run?"
    """
    table = dynamodb.Table(TOKEN_USAGE_TABLE)
    month_start_ms = int(
        datetime(year, month, 1, tzinfo=timezone.utc).timestamp() * 1000
    )
    if month == 12:
        month_end_ms = int(
            datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp() * 1000
        )
    else:
        month_end_ms = int(
            datetime(year, month + 1, 1, tzinfo=timezone.utc).timestamp() * 1000
        )

    resp = table.query(
        IndexName="user-id-index",
        KeyConditionExpression=(
            Key("user_id").eq(user_id)
            & Key("sk").between(f"{month_start_ms}#", f"{month_end_ms}#~")
        ),
    )
    items = resp["Items"]

    by_agent = {}
    application_ids = set()
    total_cost = 0.0

    for item in items:
        agent = item["agent_name"]
        by_agent[agent] = by_agent.get(agent, 0.0) + float(item.get("total_usd", 0))
        application_ids.add(item["application_id"])
        total_cost += float(item.get("total_usd", 0))

    return {
        "user_id": user_id,
        "period": f"{year}-{month:02d}",
        "total_cost_usd": round(total_cost, 4),
        "applications_run": len(application_ids),
        "cost_per_app_usd": round(total_cost / max(len(application_ids), 1), 4),
        "by_agent": {k: round(v, 4) for k, v in by_agent.items()},
    }


# ── 3. Daily cost summary (from rollup table) ──────────────────────────────────


def get_daily_summary(date_str: str) -> dict:
    """
    Pre-aggregated daily summary — fast, cheap query.
    date_str: "2026-02-24"

    Use case: dashboard, daily email report, anomaly detection.
    """
    table = dynamodb.Table(DAILY_ROLLUP_TABLE)
    resp = table.query(
        KeyConditionExpression=Key("date_agent").begins_with(date_str + "#"),
    )
    items = {item["date_agent"].split("#", 1)[1]: item for item in resp["Items"]}

    daily = items.get("DAILY_TOTAL", {})
    agents = {
        k: v
        for k, v in items.items()
        if not k.startswith("model:") and k != "DAILY_TOTAL"
    }
    models = {
        k.replace("model:", ""): v for k, v in items.items() if k.startswith("model:")
    }

    return {
        "date": date_str,
        "total_cost_usd": float(daily.get("total_cost_usd", 0)),
        "total_tokens": int(daily.get("total_tokens", 0)),
        "total_api_calls": int(daily.get("call_count", 0)),
        "by_agent": {
            name: {
                "cost_usd": float(data.get("total_cost_usd", 0)),
                "input_tokens": int(data.get("input_tokens", 0)),
                "output_tokens": int(data.get("output_tokens", 0)),
                "call_count": int(data.get("call_count", 0)),
                "self_correction_rate": float(data.get("self_correction_rate", 0)),
            }
            for name, data in agents.items()
        },
        "by_model": {
            name: {
                "cost_usd": float(data.get("total_cost_usd", 0)),
                "total_tokens": int(data.get("total_tokens", 0)),
            }
            for name, data in models.items()
        },
    }


# ── 4. Cost trend over a date range ───────────────────────────────────────────


def get_cost_trend(start_date: str, end_date: str) -> list:
    """
    Daily cost totals between two dates (inclusive).
    start_date, end_date: "YYYY-MM-DD"

    Use case: monthly cost chart, detect cost creep over time.
    """

    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    results = []
    current = start
    table = dynamodb.Table(DAILY_ROLLUP_TABLE)

    while current <= end:
        date_str = str(current)
        try:
            resp = table.get_item(
                Key={"date_agent": f"{date_str}#DAILY_TOTAL", "model": "ALL"}
            )
            item = resp.get("Item", {})
            results.append(
                {
                    "date": date_str,
                    "total_cost_usd": float(item.get("total_cost_usd", 0)),
                    "total_tokens": int(item.get("total_tokens", 0)),
                    "call_count": int(item.get("call_count", 0)),
                }
            )
        except Exception as e:
            results.append({"date": date_str, "error": str(e)})
        current += timedelta(days=1)

    return results


# ── 5. Agent performance profiler ─────────────────────────────────────────────


def profile_agent(agent_name: str, days: int = 7) -> dict:
    """
    Token statistics for a specific agent over the last N days.
    Uses agent-name-index GSI.

    Use case: "Is the VPR self-correction loop getting worse?"
    """
    table = dynamodb.Table(TOKEN_USAGE_TABLE)
    cutoff_ms = int(
        (datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000
    )

    resp = table.query(
        IndexName="agent-name-index",
        KeyConditionExpression=(
            Key("agent_name").eq(agent_name) & Key("sk").gte(f"{cutoff_ms}#")
        ),
    )
    items = resp["Items"]

    if not items:
        return {"agent_name": agent_name, "days": days, "calls": 0}

    input_tokens = [int(i.get("input_tokens", 0)) for i in items]
    output_tokens = [int(i.get("output_tokens", 0)) for i in items]
    costs = [float(i.get("total_usd", 0)) for i in items]
    durations = [int(i.get("duration_ms", 0)) for i in items if i.get("duration_ms")]

    self_corrections = sum(
        1 for i in items if "self_correction" in str(i.get("stage", ""))
    )

    return {
        "agent_name": agent_name,
        "period_days": days,
        "total_calls": len(items),
        "self_correction_calls": self_corrections,
        "self_correction_rate": round(self_corrections / len(items), 3),
        "input_tokens": {
            "min": min(input_tokens),
            "max": max(input_tokens),
            "avg": round(sum(input_tokens) / len(input_tokens)),
            "total": sum(input_tokens),
        },
        "output_tokens": {
            "min": min(output_tokens),
            "max": max(output_tokens),
            "avg": round(sum(output_tokens) / len(output_tokens)),
            "total": sum(output_tokens),
        },
        "output_input_ratio": round(sum(output_tokens) / max(sum(input_tokens), 1), 3),
        "cost_usd": {
            "min": round(min(costs), 5),
            "max": round(max(costs), 5),
            "avg": round(sum(costs) / len(costs), 5),
            "total": round(sum(costs), 4),
        },
        "duration_ms": {
            "avg": round(sum(durations) / len(durations)) if durations else None,
            "max": max(durations) if durations else None,
        },
    }


# ── EXAMPLE OUTPUTS ────────────────────────────────────────────────────────────
"""
get_application_cost_breakdown("app_abc123"):
{
  "application_id": "app_abc123",
  "total_cost_usd": 0.312,
  "total_api_calls": 8,
  "agents": {
    "vpr-strategist": {
      "calls": [
        {"stage": "primary_generation",      "input_tokens": 10840, "output_tokens": 12400, "cost_usd": 0.219, "duration_ms": 34200},
        {"stage": "stage6_meta_evaluation",  "input_tokens":  2100, "output_tokens":  4800, "cost_usd": 0.078, "duration_ms": 18100},
      ],
      "total_input_tokens": 12940, "total_output_tokens": 17200,
      "total_cost_usd": 0.297, "self_correction_calls": 0
    },
    "gap-analysis-question-generator": {
      "calls": [{"stage": "primary_generation", "input_tokens": 7200, "output_tokens": 800, "cost_usd": 0.034}],
      ...
    }
  }
}

profile_agent("vpr-strategist", days=7):
{
  "agent_name": "vpr-strategist",
  "total_calls": 42,
  "self_correction_rate": 0.19,       # <-- watch this number
  "output_input_ratio": 1.33,         # vs 0.25 in architecture doc
  "cost_usd": {"avg": 0.285, "max": 0.891, "total": 11.97}
}
"""
