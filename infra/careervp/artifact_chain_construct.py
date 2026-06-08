"""
Artifact Chain Construct (FE-UI-031).

Defines the AWS Step Functions *Standard* state machine that orchestrates the
sequential artifact chain:

    Company Research -> VPR -> Tailored CV

Each step uses the ``sqs:sendMessage.waitForTaskToken`` integration pattern: the
state machine enqueues a message containing ``task_token`` and pauses until the
downstream worker calls ``SendTaskSuccess`` / ``SendTaskFailure``. The machine is
purely additive — it wraps existing SQS workers via task tokens without
rewriting them. Failure branches invoke thin Lambda handlers that mark the
application record.

Standard (not Express) is required: the chain can take up to ~2 hours (VPR is
slow), exceeding the 5-minute Express limit.

NOTE on data threading: the ASL references input paths such as ``$.company_context``
and ``$.vpr_id`` that are produced by upstream workers. Wiring those workers to
emit task-token output is handled by separate tickets; this construct defines the
orchestration shell. With ``ARTIFACT_CHAIN_ENABLED`` defaulting to "false", the
machine is opt-in at the environment level.
"""

from __future__ import annotations

from aws_cdk import Duration, RemovalPolicy
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_logs as logs
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as sfn_tasks
from constructs import Construct

from . import constants
from .naming_utils import NamingUtils


class ArtifactChainConstruct(Construct):
    """Step Functions Standard workflow for the CR -> VPR -> CV artifact chain."""

    def __init__(
        self,
        scope: Construct,
        id_: str,
        *,
        naming: NamingUtils,
        company_research_queue: sqs.IQueue,
        vpr_jobs_queue: sqs.IQueue,
        cv_tailoring_queue: sqs.IQueue,
        cr_failure_handler: _lambda.IFunction,
        artifact_failure_handler: _lambda.IFunction,
        logs_kms_key: kms.IKey | None = None,
    ) -> None:
        super().__init__(scope, id_)
        self.naming = naming

        # --- Failure branches (terminal Lambda tasks) ---------------------------
        handle_cr_failure = sfn_tasks.LambdaInvoke(
            self,
            "HandleCRFailure",
            lambda_function=cr_failure_handler,
            # Pass the raw execution input ($) so the handler can read user_id/job_id.
            payload=sfn.TaskInput.from_json_path_at("$"),
            payload_response_only=True,
            comment="Sets company_research_error=true and state=cr_failed",
        )

        handle_vpr_failure = sfn_tasks.LambdaInvoke(
            self,
            "HandleVPRFailure",
            lambda_function=artifact_failure_handler,
            payload=sfn.TaskInput.from_object(
                {
                    "artifact_type": "vpr",
                    "context": sfn.JsonPath.object_at("$"),
                }
            ),
            payload_response_only=True,
        )

        handle_cv_failure = sfn_tasks.LambdaInvoke(
            self,
            "HandleCVFailure",
            lambda_function=artifact_failure_handler,
            payload=sfn.TaskInput.from_object(
                {
                    "artifact_type": "cv_tailored",
                    "context": sfn.JsonPath.object_at("$"),
                }
            ),
            payload_response_only=True,
        )

        # --- Task-token SQS steps ----------------------------------------------
        # result_path=DISCARD keeps the original execution input available to the
        # next state (the SendTaskSuccess output would otherwise overwrite it).
        start_cv_tailoring = sfn_tasks.SqsSendMessage(
            self,
            "StartCVTailoring",
            queue=cv_tailoring_queue,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            heartbeat_timeout=sfn.Timeout.duration(Duration.seconds(300)),
            result_path=sfn.JsonPath.DISCARD,
            message_body=sfn.TaskInput.from_object(
                {
                    "user_id": sfn.JsonPath.string_at("$.user_id"),
                    "job_id": sfn.JsonPath.string_at("$.job_id"),
                    "vpr_id": sfn.JsonPath.string_at("$.vpr_id"),
                    "task_token": sfn.JsonPath.task_token,
                }
            ),
        )
        start_cv_tailoring.add_retry(
            errors=["States.TaskFailed"],
            interval=Duration.seconds(30),
            max_attempts=2,
            backoff_rate=2.0,
        )
        start_cv_tailoring.add_catch(handle_cv_failure, errors=["States.ALL"])

        start_vpr = sfn_tasks.SqsSendMessage(
            self,
            "StartVPR",
            queue=vpr_jobs_queue,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            heartbeat_timeout=sfn.Timeout.duration(Duration.seconds(300)),
            result_path=sfn.JsonPath.DISCARD,
            message_body=sfn.TaskInput.from_object(
                {
                    "user_id": sfn.JsonPath.string_at("$.user_id"),
                    "job_id": sfn.JsonPath.string_at("$.job_id"),
                    "company_context": sfn.JsonPath.string_at("$.company_context"),
                    "task_token": sfn.JsonPath.task_token,
                }
            ),
        )
        start_vpr.add_retry(
            errors=["States.TaskFailed"],
            interval=Duration.seconds(30),
            max_attempts=2,
            backoff_rate=2.0,
        )
        start_vpr.add_catch(handle_vpr_failure, errors=["States.ALL"])
        start_vpr.next(start_cv_tailoring)

        start_company_research = sfn_tasks.SqsSendMessage(
            self,
            "StartCompanyResearch",
            queue=company_research_queue,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            heartbeat_timeout=sfn.Timeout.duration(Duration.seconds(180)),
            result_path=sfn.JsonPath.DISCARD,
            message_body=sfn.TaskInput.from_object(
                {
                    "user_id": sfn.JsonPath.string_at("$.user_id"),
                    "job_id": sfn.JsonPath.string_at("$.job_id"),
                    "company_name": sfn.JsonPath.string_at("$.company_name"),
                    "job_posting_url": sfn.JsonPath.string_at("$.job_posting_url"),
                    "task_token": sfn.JsonPath.task_token,
                }
            ),
        )
        start_company_research.add_retry(
            errors=["CRRetryableError"],
            interval=Duration.seconds(120),
            max_attempts=3,
            backoff_rate=2.0,
        )
        start_company_research.add_catch(
            handle_cr_failure,
            errors=["CRHardFail", "States.TaskFailed"],
        )
        start_company_research.next(start_vpr)

        # --- State machine ------------------------------------------------------
        log_group = logs.LogGroup(
            self,
            "ArtifactChainLogGroup",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
            encryption_key=logs_kms_key,
        )

        self.state_machine = sfn.StateMachine(
            self,
            "ArtifactChainStateMachine",
            state_machine_name=self.naming.state_machine_name(
                constants.ARTIFACT_CHAIN_STATE_MACHINE_FEATURE
            ),
            state_machine_type=sfn.StateMachineType.STANDARD,
            definition_body=sfn.DefinitionBody.from_chainable(start_company_research),
            tracing_enabled=True,
            timeout=Duration.hours(2),
            logs=sfn.LogOptions(
                destination=log_group,
                level=sfn.LogLevel.ERROR,
                # Cost control: do not log full state payloads.
                include_execution_data=False,
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )
