import os
from typing import Literal

import aws_cdk.aws_sns as sns
from aws_cdk import CfnOutput, Duration, NestedStack, RemovalPolicy, aws_apigateway
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_logs as logs
from aws_cdk import aws_sns_subscriptions as sns_subscriptions
from cdk_monitoring_constructs import (
    AlarmFactoryDefaults,
    CustomMetricGroup,
    DefaultDashboardFactory,
    ErrorRateThreshold,
    LatencyThreshold,
    MetricStatistic,
    MonitoringFacade,
    SnsAlarmActionStrategy,
)
from constructs import Construct

from . import constants
from .naming_utils import NamingUtils

MonitoringMode = Literal["all", "notifications", "dashboards", "alarms"]
_Q10_PRICE_PER_APP = 25.0 / 20.0
_Q10_COST_PER_APP_ALARM_THRESHOLD = 0.30 * _Q10_PRICE_PER_APP

# P-21: alarms must reach a real on-call destination. Each environment has a
# default subscribed endpoint so a synthesized stack is never left with zero
# subscribers; the human overrides it per deploy via ALARM_SUBSCRIPTION_EMAILS
# (comma-separated). Email subscriptions require a one-time human inbox
# confirmation — that confirmation is the P-21 deploy-gate evidence, not
# something CDK can assert (see scripts/deploy_evidence.py).
_DEFAULT_ALARM_EMAILS: dict[str, str] = {
    "dev": "careervp-alerts-dev@careervp.com",
    "stage": "careervp-alerts-stage@careervp.com",
    "staging": "careervp-alerts-stage@careervp.com",
    "prod": "careervp-alerts@careervp.com",
    "production": "careervp-alerts@careervp.com",
}


def resolve_alarm_emails(environment: str) -> list[str]:
    """Return the alarm subscription endpoints for an environment.

    ``ALARM_SUBSCRIPTION_EMAILS`` (comma-separated) overrides the per-env
    default. Returns at least one endpoint for every known environment so the
    monitoring topic is never synthesized without a subscriber.
    """
    override = os.getenv("ALARM_SUBSCRIPTION_EMAILS", "").strip()
    if override:
        return [email.strip() for email in override.split(",") if email.strip()]
    default = _DEFAULT_ALARM_EMAILS.get(environment)
    return [default] if default else []


class CrudMonitoring(Construct):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        crud_api: aws_apigateway.RestApi,
        db: dynamodb.TableV2,
        idempotency_table: dynamodb.TableV2,
        functions: list[_lambda.Function],
        naming: NamingUtils,
        mode: MonitoringMode = "all",
        notification_topic: sns.ITopic | None = None,
        create_dashboards: bool = True,
    ) -> None:
        super().__init__(scope, id_)
        self.id_ = id_
        self.naming = naming
        self.create_dashboards = create_dashboards
        self.notification_topic = notification_topic or self._build_topic()
        if mode == "notifications":
            return
        create_alarm_resources = mode in ("all", "alarms")
        self._build_high_level_dashboard(
            crud_api, self.notification_topic, create_alarm_resources
        )
        self._build_low_level_dashboard(
            db,
            idempotency_table,
            functions,
            self.notification_topic,
            create_alarm_resources,
        )

    def _build_topic(self) -> sns.Topic:
        key = kms.Key(
            self,
            "MonitoringKey",
            description="KMS Key for SNS Topic Encryption",
            enable_key_rotation=True,  # Enables automatic key rotation
            removal_policy=RemovalPolicy.DESTROY,
            pending_window=Duration.days(7),
        )
        topic = sns.Topic(
            self,
            f"{self.id_}alarms",
            display_name=f"{self.id_}alarms",
            master_key=key,
            topic_name=self.naming.topic_name(constants.MONITORING_FEATURE),
        )
        # Grant CloudWatch permissions to publish to the SNS topic
        topic.add_to_resource_policy(
            statement=iam.PolicyStatement(
                actions=["sns:Publish"],
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudwatch.amazonaws.com")],
                resources=[topic.topic_arn],
            )
        )
        # P-21: subscribe at least one on-call endpoint so alarms are not silent.
        for email in resolve_alarm_emails(self.naming.environment):
            topic.add_subscription(sns_subscriptions.EmailSubscription(email))
        CfnOutput(
            self, id=constants.MONITORING_TOPIC, value=topic.topic_name
        ).override_logical_id(constants.MONITORING_TOPIC)
        return topic

    def _build_high_level_dashboard(
        self,
        crud_api: aws_apigateway.RestApi,
        topic: sns.ITopic,
        create_alarm_resources: bool,
    ) -> None:
        fault_rate_alarm = (
            {"internal_error": ErrorRateThreshold(max_error_rate=1)}
            if create_alarm_resources
            else None
        )
        high_level_facade = MonitoringFacade(
            self,
            f"{self.id_}HighFacade",
            alarm_factory_defaults=AlarmFactoryDefaults(
                actions_enabled=True,
                alarm_name_prefix=self.id_,
                action=SnsAlarmActionStrategy(on_alarm_topic=topic),
            ),
            dashboard_factory=self._build_dashboard_factory(
                f"{self.id_}HighFacadeDashboards"
            ),
        )
        high_level_facade.add_large_header("Order REST API High Level Dashboard")
        high_level_facade.monitor_api_gateway(
            api=crud_api,
            add5_xx_fault_rate_alarm=fault_rate_alarm,
        )
        metric_factory = high_level_facade.create_metric_factory()
        create_metric = metric_factory.create_metric(
            metric_name="ValidCreateOrderEvents",
            namespace=constants.METRICS_NAMESPACE,
            statistic=MetricStatistic.N,
            dimensions_map={constants.METRICS_DIMENSION_KEY: constants.SERVICE_NAME},
            label="create order events",
            period=Duration.days(1),
        )

        group = CustomMetricGroup(metrics=[create_metric], title="Daily Order Requests")
        high_level_facade.monitor_custom(
            metric_groups=[group],
            human_readable_name="Daily KPIs",
            alarm_friendly_name="KPIs",
        )

    def _build_low_level_dashboard(
        self,
        db: dynamodb.TableV2,
        idempotency_table: dynamodb.TableV2,
        functions: list[_lambda.Function],
        topic: sns.ITopic,
        create_alarm_resources: bool,
    ) -> None:
        latency_alarm = (
            {"p90": LatencyThreshold(max_latency=Duration.seconds(3))}
            if create_alarm_resources
            else None
        )
        low_level_facade = MonitoringFacade(
            self,
            f"{self.id_}LowFacade",
            alarm_factory_defaults=AlarmFactoryDefaults(
                actions_enabled=True,
                alarm_name_prefix=self.id_,
                action=SnsAlarmActionStrategy(on_alarm_topic=topic),
            ),
            dashboard_factory=self._build_dashboard_factory(
                f"{self.id_}LowFacadeDashboards"
            ),
        )
        low_level_facade.add_large_header("Orders REST API Low Level Dashboard")
        for func in functions:
            low_level_facade.monitor_lambda_function(
                lambda_function=func,
                add_latency_p90_alarm=latency_alarm,
            )
            low_level_facade.monitor_log(
                log_group_name=func.log_group.log_group_name,
                human_readable_name="Error logs",
                pattern="ERROR",
                alarm_friendly_name="error logs",
            )

            if not create_alarm_resources:
                continue

            validation_exception_metric_id = (
                f"{func.node.id}DynamoValidationExceptionMetric"
            )
            logs.MetricFilter(
                self,
                validation_exception_metric_id,
                log_group=func.log_group,
                filter_pattern=logs.FilterPattern.literal('"ValidationException"'),
                metric_namespace=constants.METRICS_NAMESPACE,
                metric_name=f"{func.function_name}-DynamoValidationException",
                metric_value="1",
                default_value=0,
            )
            validation_alarm = cloudwatch.Alarm(
                self,
                f"{func.node.id}DynamoValidationExceptionAlarm",
                metric=cloudwatch.Metric(
                    namespace=constants.METRICS_NAMESPACE,
                    metric_name=f"{func.function_name}-DynamoValidationException",
                    statistic="Sum",
                    period=Duration.minutes(5),
                ),
                threshold=1,
                evaluation_periods=1,
                datapoints_to_alarm=1,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
                alarm_name=f"{func.function_name}-DynamoValidationException",
            )
            # P-21: this hand-built alarm must also route to the on-call topic
            # (the MonitoringFacade alarms already do via SnsAlarmActionStrategy).
            validation_alarm.add_alarm_action(cloudwatch_actions.SnsAction(topic))

        low_level_facade.monitor_dynamo_table(
            table=db, billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )
        low_level_facade.monitor_dynamo_table(
            table=idempotency_table, billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

    def _build_dashboard_factory(self, id_: str) -> DefaultDashboardFactory | None:
        if self.create_dashboards:
            return None
        return DefaultDashboardFactory(
            self,
            id_,
            dashboard_name_prefix=self.id_,
            create_alarm_dashboard=self.create_dashboards,
            create_dashboard=self.create_dashboards,
            create_summary_dashboard=False,
        )


class MonitoringNestedStack(NestedStack):
    def __init__(
        self,
        scope: Construct,
        id_: str,
        monitoring_id: str,
        crud_api: aws_apigateway.RestApi,
        db: dynamodb.TableV2,
        idempotency_table: dynamodb.TableV2,
        functions: list[_lambda.Function],
        notification_topic: sns.ITopic,
        naming: NamingUtils,
    ) -> None:
        super().__init__(scope, id_)
        self.monitoring = CrudMonitoring(
            self,
            monitoring_id,
            crud_api,
            db,
            idempotency_table,
            functions,
            naming=naming,
            notification_topic=notification_topic,
            create_dashboards=False,
        )
        cost_per_application_alarm = cloudwatch.Alarm(
            self,
            "CostPerApplicationAlarm",
            metric=cloudwatch.Metric(
                namespace=constants.METRICS_NAMESPACE,
                metric_name="CostPerApplicationUSD",
                statistic="Maximum",
                period=Duration.minutes(5),
                dimensions_map={"TrafficOrigin": "product"},
            ),
            threshold=_Q10_COST_PER_APP_ALARM_THRESHOLD,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        cost_per_application_alarm.add_alarm_action(
            cloudwatch_actions.SnsAction(notification_topic)
        )
