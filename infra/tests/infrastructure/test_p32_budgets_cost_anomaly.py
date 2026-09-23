"""P-32 RED tests: AWS Budgets + Cost Anomaly Detection as CDK (Wave 0 slice).

Per human decision on 2026-07-12, this slice moved from console-only to CDK
(see specs/P-32-cost-obs-edge-spec.md Fix Plan item 4 — "unless AWS ownership
is moved into IaC by explicit decision"). A $100/month budget and a $10
absolute-impact Cost Anomaly Detection monitor/subscription must synth,
both routed to the existing careervp-monitoring SNS topic (P-21) rather than
a separate subscriber, so alerts land in the one place a human already
watches.
"""

from __future__ import annotations

from aws_cdk.assertions import Match, Template


def test_p32_budget_synths_with_monthly_limit(monitoring_template: Template) -> None:
    budgets = monitoring_template.find_resources("AWS::Budgets::Budget")
    assert budgets, "expected an AWS::Budgets::Budget resource"

    (props,) = budgets.values()
    budget_data = props["Properties"]["Budget"]
    assert budget_data["BudgetType"] == "COST"
    assert budget_data["TimeUnit"] == "MONTHLY"
    assert budget_data["BudgetLimit"]["Amount"] == 100
    assert budget_data["BudgetLimit"]["Unit"] == "USD"


def test_p32_budget_notifies_monitoring_sns_topic(
    monitoring_template: Template,
) -> None:
    (props,) = monitoring_template.find_resources("AWS::Budgets::Budget").values()
    notifications = props["Properties"]["NotificationsWithSubscribers"]
    assert notifications, "expected at least one budget notification"

    sns_subscribers = [
        subscriber
        for notification in notifications
        for subscriber in notification["Subscribers"]
        if subscriber["SubscriptionType"] == "SNS"
    ]
    assert sns_subscribers, "expected an SNS subscriber on the budget notification"


def test_p32_cost_anomaly_monitor_and_subscription_synth(
    monitoring_template: Template,
) -> None:
    monitors = monitoring_template.find_resources("AWS::CE::AnomalyMonitor")
    assert monitors, "expected an AWS::CE::AnomalyMonitor resource"

    subscriptions = monitoring_template.find_resources("AWS::CE::AnomalySubscription")
    assert subscriptions, "expected an AWS::CE::AnomalySubscription resource"

    (sub_props,) = subscriptions.values()
    sub = sub_props["Properties"]
    # SNS delivery requires IMMEDIATE frequency (DAILY/WEEKLY are email-only).
    assert sub["Frequency"] == "IMMEDIATE"
    assert sub["ThresholdExpression"], "expected a ThresholdExpression"

    sns_subscribers = [s for s in sub["Subscribers"] if s["Type"] == "SNS"]
    assert sns_subscribers, "expected an SNS subscriber on the anomaly subscription"


def test_p32_anomaly_monitor_is_not_built_outside_the_owning_environment(
    devx_monitoring_template: Template,
) -> None:
    """AWS permits ONE DIMENSIONAL/SERVICE anomaly monitor per AWS account.

    The limit is enforced on the account, not the monitor name, so the
    env-scoped name does not avoid it — a second environment requesting
    ``...-anomaly-monitor-devx`` still fails with ``AlreadyExists`` because
    dev's monitor already occupies the account's single slot. This is invisible
    to `cdk synth` and to the P-28 Replacement report, and previously took the
    whole CareerVpCrudDevx create down 9 minutes in (2026-07-19T20:13:20Z).
    """
    assert devx_monitoring_template.find_resources("AWS::CE::AnomalyMonitor") == {}, (
        "a non-dev environment must not create an AWS::CE::AnomalyMonitor: "
        "it is an account-wide singleton owned by dev"
    )
    assert (
        devx_monitoring_template.find_resources("AWS::CE::AnomalySubscription") == {}
    ), "the anomaly subscription must not outlive the monitor it points at"


def test_p32_budget_is_still_built_outside_the_owning_environment(
    devx_monitoring_template: Template,
) -> None:
    """The budget is per-environment and must survive the anomaly-monitor gate.

    Budget names are genuinely unique per account, so every environment keeps
    its own spend alerting — gating the account-singleton monitor must not take
    the budget with it.
    """
    budget_resources = devx_monitoring_template.find_resources("AWS::Budgets::Budget")
    assert budget_resources, "every environment keeps its own cost budget"

    (props,) = budget_resources.values()
    budget_data = props["Properties"]["Budget"]
    assert budget_data["BudgetName"].endswith("-devx"), (
        "the budget name must stay environment-scoped so it cannot collide "
        f"with another environment's budget (got {budget_data['BudgetName']!r})"
    )
    assert budget_data["BudgetLimit"]["Amount"] == 100


def test_p32_monitoring_topic_policy_allows_budgets_and_costalerts_principals(
    synthesized_template: Template,
) -> None:
    """The shared monitoring SNS topic must let both billing services publish,
    or the Budget/Anomaly SNS notifications above are silently undeliverable."""
    synthesized_template.has_resource_properties(
        "AWS::SNS::TopicPolicy",
        {
            "PolicyDocument": Match.object_like(
                {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Principal": {
                                        "Service": Match.any_value(),
                                    },
                                    "Action": "sns:Publish",
                                }
                            )
                        ]
                    )
                }
            )
        },
    )

    policies = synthesized_template.find_resources("AWS::SNS::TopicPolicy")
    services = {
        stmt["Principal"]["Service"]
        for props in policies.values()
        for stmt in props["Properties"]["PolicyDocument"]["Statement"]
        if isinstance(stmt.get("Principal"), dict)
        and isinstance(stmt["Principal"].get("Service"), str)
    }
    assert "budgets.amazonaws.com" in services
    assert "costalerts.amazonaws.com" in services
