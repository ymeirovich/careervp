from __future__ import annotations

from aws_cdk import Duration, NestedStack
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cloudwatch_actions
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_sns as sns
from constructs import Construct

from . import constants
from .naming_utils import NamingUtils


class CompanyResearchNestedStack(NestedStack):
    """Additive company-research Tavily wiring and observability."""

    def __init__(
        self,
        scope: Construct,
        id_: str,
        *,
        naming: NamingUtils,
        company_research_lambda: _lambda.Function,
        company_research_worker_lambda: _lambda.Function,
        company_research_role: iam.Role,
        company_research_cache_table: dynamodb.TableV2,
        notification_topic: sns.ITopic,
    ) -> None:
        super().__init__(scope, id_)
        self.naming = naming

        self._inject_tavily_secret_env(
            company_research_lambda,
            company_research_worker_lambda,
        )
        self._add_company_research_access_policy(
            company_research_role,
            company_research_cache_table,
        )
        self._add_tavily_alarms(notification_topic)

    def _inject_tavily_secret_env(
        self,
        company_research_lambda: _lambda.Function,
        company_research_worker_lambda: _lambda.Function,
    ) -> None:
        for function in (company_research_lambda, company_research_worker_lambda):
            function.add_environment(
                constants.TAVILY_API_KEY_SSM_PARAM_ENV,
                constants.TAVILY_API_KEY_SSM_PARAM,
            )

    def _add_company_research_access_policy(
        self,
        company_research_role: iam.Role,
        company_research_cache_table: dynamodb.TableV2,
    ) -> None:
        tavily_param_arn = (
            f"arn:aws:ssm:{self.naming.region}:{self.naming.account_id}:parameter/"
            f"{constants.TAVILY_API_KEY_SSM_PARAM.lstrip('/')}"
        )
        iam.CfnPolicy(
            self,
            "CompanyResearchTavilyAccessPolicy",
            policy_name=(
                f"{constants.SERVICE_PREFIX}-company-research-tavily-policy-"
                f"{self.naming.environment}"
            ),
            roles=[company_research_role.role_name],
            policy_document={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": "ssm:GetParameter",
                        "Resource": tavily_param_arn,
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "dynamodb:GetItem",
                            "dynamodb:PutItem",
                            "dynamodb:UpdateItem",
                            "dynamodb:DeleteItem",
                            "dynamodb:Query",
                        ],
                        "Resource": company_research_cache_table.table_arn,
                    },
                ],
            },
        )

    def _add_tavily_alarms(self, notification_topic: sns.ITopic) -> None:
        alarm_action = cloudwatch_actions.SnsAction(notification_topic)

        tavily_failure_alarm = cloudwatch.Alarm(
            self,
            "TavilySearchFailureAlarm",
            alarm_name=(
                f"{constants.SERVICE_PREFIX}-tavily-search-failure-"
                f"{self.naming.environment}"
            ),
            metric=self._metric("TavilySearchFailure", statistic="Sum"),
            threshold=5,
            evaluation_periods=3,
            datapoints_to_alarm=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        tavily_failure_alarm.add_alarm_action(alarm_action)

        all_sources_failed_alarm = cloudwatch.Alarm(
            self,
            "CompanyResearchAllSourcesFailedAlarm",
            alarm_name=(
                f"{constants.SERVICE_PREFIX}-company-research-all-sources-failed-"
                f"{self.naming.environment}"
            ),
            metric=self._metric("CompanyResearchAllSourcesFailed", statistic="Sum"),
            threshold=0,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        all_sources_failed_alarm.add_alarm_action(alarm_action)

    def _metric(self, metric_name: str, *, statistic: str) -> cloudwatch.Metric:
        return cloudwatch.Metric(
            namespace=constants.METRICS_NAMESPACE,
            metric_name=metric_name,
            dimensions_map={
                constants.METRICS_DIMENSION_KEY: constants.SERVICE_NAME,
            },
            statistic=statistic,
            period=Duration.minutes(5),
        )
