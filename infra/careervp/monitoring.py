from typing import Any

import aws_cdk.aws_sns as sns
from aws_cdk import CfnOutput, Duration, NestedStack, RemovalPolicy, aws_apigateway
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_logs as logs
from cdk_monitoring_constructs import (
    AlarmFactoryDefaults,
    CustomMetricGroup,
    ErrorRateThreshold,
    LatencyThreshold,
    MetricStatistic,
    MonitoringFacade,
    SnsAlarmActionStrategy,
)
from constructs import Construct

from . import constants
from .naming_utils import NamingUtils


def build_monitoring_topic(
    scope: Construct, id_: str, naming: NamingUtils
) -> sns.Topic:
    """Create the alarm SNS topic and its encryption key in the PARENT stack.

    FE-UI-036: the KMS key is a stateful resource and must NOT move across a
    nested-stack boundary (a logical-id change would REPLACE it). The topic and
    key therefore stay in the parent; the (nested) dashboards/alarms reference
    the topic downward as an alarm action.
    """
    key = kms.Key(
        scope,
        "MonitoringKey",
        description="KMS Key for SNS Topic Encryption",
        enable_key_rotation=True,  # Enables automatic key rotation
        removal_policy=RemovalPolicy.DESTROY,
        pending_window=Duration.days(7),
    )
    topic = sns.Topic(
        scope,
        f"{id_}alarms",
        display_name=f"{id_}alarms",
        master_key=key,
        topic_name=naming.topic_name(constants.MONITORING_FEATURE),
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
    CfnOutput(
        scope, id=constants.MONITORING_TOPIC, value=topic.topic_name
    ).override_logical_id(constants.MONITORING_TOPIC)
    return topic


class CrudMonitoring(NestedStack):
    """Dashboards, alarms, and metric filters extracted into their own template.

    FE-UI-036 phase 1: monitoring is OUTBOUND-ONLY (it observes parent
    Lambdas/queues/tables; nothing depends on it), so it is the lowest-risk
    subtree to relocate. The SNS topic + KMS key are built in the parent (see
    ``build_monitoring_topic``) and passed in; only stateless dashboards/alarms
    live here. ``monitoring_id`` preserves the original alarm/widget name prefix
    so alarm names are unchanged.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        monitoring_id: str,
        crud_api: aws_apigateway.RestApi,
        db: dynamodb.TableV2,
        idempotency_table: dynamodb.TableV2,
        functions: list[_lambda.Function],
        naming: NamingUtils,
        topic: sns.Topic,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.id_ = monitoring_id
        self.naming = naming
        self.notification_topic = topic
        self._build_high_level_dashboard(crud_api, topic)
        self._build_low_level_dashboard(db, idempotency_table, functions, topic)

    def _build_high_level_dashboard(
        self, crud_api: aws_apigateway.RestApi, topic: sns.Topic
    ) -> None:
        high_level_facade = MonitoringFacade(
            self,
            f"{self.id_}HighFacade",
            alarm_factory_defaults=AlarmFactoryDefaults(
                actions_enabled=True,
                alarm_name_prefix=self.id_,
                action=SnsAlarmActionStrategy(on_alarm_topic=topic),
            ),
        )
        high_level_facade.add_large_header("Order REST API High Level Dashboard")
        high_level_facade.monitor_api_gateway(
            api=crud_api,
            add5_xx_fault_rate_alarm={
                "internal_error": ErrorRateThreshold(max_error_rate=1)
            },
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
        topic: sns.Topic,
    ) -> None:
        low_level_facade = MonitoringFacade(
            self,
            f"{self.id_}LowFacade",
            alarm_factory_defaults=AlarmFactoryDefaults(
                actions_enabled=True,
                alarm_name_prefix=self.id_,
                action=SnsAlarmActionStrategy(on_alarm_topic=topic),
            ),
        )
        low_level_facade.add_large_header("Orders REST API Low Level Dashboard")
        for func in functions:
            low_level_facade.monitor_lambda_function(
                lambda_function=func,
                add_latency_p90_alarm={
                    "p90": LatencyThreshold(max_latency=Duration.seconds(3))
                },
            )
            low_level_facade.monitor_log(
                log_group_name=func.log_group.log_group_name,
                human_readable_name="Error logs",
                pattern="ERROR",
                alarm_friendly_name="error logs",
            )

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
            cloudwatch.Alarm(
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

        low_level_facade.monitor_dynamo_table(
            table=db, billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )
        low_level_facade.monitor_dynamo_table(
            table=idempotency_table, billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )
