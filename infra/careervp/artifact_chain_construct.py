"""
Artifact Chain Construct (FE-UI-031).

Defines the AWS Step Functions *Standard* state machine that orchestrates the
sequential artifact chain:

    Company Research -> VPR -> Tailored CV

Company Research and VPR use the ``sqs:sendMessage.waitForTaskToken``
integration pattern: the state machine enqueues a message containing
``task_token`` and pauses until the downstream worker calls ``SendTaskSuccess`` /
``SendTaskFailure``. CV tailoring is invoked synchronously because it reuses the
fast existing CV Lambda path. Failure branches invoke thin Lambda handlers that
mark the application record.

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
        cover_letter_queue: sqs.IQueue,
        interview_prep_queue: sqs.IQueue,
        cv_tailoring_func: _lambda.IFunction,
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

        handle_cover_letter_failure = sfn_tasks.LambdaInvoke(
            self,
            "HandleCoverLetterFailure",
            lambda_function=artifact_failure_handler,
            payload=sfn.TaskInput.from_object(
                {
                    "artifact_type": "cover_letter",
                    "context": sfn.JsonPath.object_at("$"),
                }
            ),
            payload_response_only=True,
        )

        handle_interview_prep_failure = sfn_tasks.LambdaInvoke(
            self,
            "HandleInterviewPrepFailure",
            lambda_function=artifact_failure_handler,
            payload=sfn.TaskInput.from_object(
                {
                    "artifact_type": "interview_prep",
                    "context": sfn.JsonPath.object_at("$"),
                }
            ),
            payload_response_only=True,
        )

        handle_final_artifacts_failure = sfn_tasks.LambdaInvoke(
            self,
            "HandleFinalArtifactsFailure",
            lambda_function=artifact_failure_handler,
            payload=sfn.TaskInput.from_object(
                {
                    "artifact_type": "final_artifacts",
                    "context": sfn.JsonPath.object_at("$"),
                }
            ),
            payload_response_only=True,
        )

        # --- Task-token SQS steps ----------------------------------------------
        start_cover_letter = sfn_tasks.SqsSendMessage(
            self,
            "StartCoverLetter",
            queue=cover_letter_queue,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            heartbeat_timeout=sfn.Timeout.duration(Duration.seconds(300)),
            result_path="$.cover_letter_result",
            message_body=sfn.TaskInput.from_object(
                {
                    "user_id": sfn.JsonPath.string_at("$.user_id"),
                    "job_id": sfn.JsonPath.string_at("$.job_id"),
                    "vpr_id": sfn.JsonPath.string_at("$.vpr_result.vpr_id"),
                    "company_context": sfn.JsonPath.object_at(
                        "$.company_research_result.company_context"
                    ),
                    "task_token": sfn.JsonPath.task_token,
                }
            ),
        )
        start_cover_letter.add_retry(
            errors=["States.TaskFailed"],
            interval=Duration.seconds(30),
            max_attempts=2,
            backoff_rate=2.0,
        )
        start_cover_letter.add_catch(
            handle_cover_letter_failure,
            errors=["States.ALL"],
            result_path="$.cover_letter_error",
        )

        start_interview_prep = sfn_tasks.SqsSendMessage(
            self,
            "StartInterviewPrep",
            queue=interview_prep_queue,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            heartbeat_timeout=sfn.Timeout.duration(Duration.seconds(300)),
            result_path="$.interview_prep_result",
            message_body=sfn.TaskInput.from_object(
                {
                    "user_id": sfn.JsonPath.string_at("$.user_id"),
                    "job_id": sfn.JsonPath.string_at("$.job_id"),
                    "vpr_id": sfn.JsonPath.string_at("$.vpr_result.vpr_id"),
                    "task_token": sfn.JsonPath.task_token,
                }
            ),
        )
        start_interview_prep.add_retry(
            errors=["States.TaskFailed"],
            interval=Duration.seconds(30),
            max_attempts=2,
            backoff_rate=2.0,
        )
        start_interview_prep.add_catch(
            handle_interview_prep_failure,
            errors=["States.ALL"],
            result_path="$.interview_prep_error",
        )

        generate_final_artifacts = sfn.Parallel(
            self,
            "GenerateFinalArtifacts",
            comment="Generate cover letter and interview prep concurrently",
            result_path="$.final_artifacts_result",
        )
        generate_final_artifacts.branch(start_cover_letter)
        generate_final_artifacts.branch(start_interview_prep)
        generate_final_artifacts.add_catch(
            handle_final_artifacts_failure,
            errors=["States.ALL"],
            result_path="$.final_artifacts_error",
        )

        start_cv_tailoring = sfn_tasks.LambdaInvoke(
            self,
            "StartCVTailoring",
            lambda_function=cv_tailoring_func,
            payload_response_only=True,
            result_path="$.cv_tailoring_result",
            payload=sfn.TaskInput.from_object(
                {
                    "user_id": sfn.JsonPath.string_at("$.user_id"),
                    "cv_id": sfn.JsonPath.string_at("$.cv_id"),
                    "job_id": sfn.JsonPath.string_at("$.job_id"),
                    "vpr_id": sfn.JsonPath.string_at("$.vpr_result.vpr_id"),
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
        start_cv_tailoring.next(generate_final_artifacts)

        start_vpr = sfn_tasks.SqsSendMessage(
            self,
            "StartVPR",
            queue=vpr_jobs_queue,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            result_path="$.vpr_result",
            message_body=sfn.TaskInput.from_object(
                {
                    "user_id": sfn.JsonPath.string_at("$.user_id"),
                    "cv_id": sfn.JsonPath.string_at("$.cv_id"),
                    "job_id": sfn.JsonPath.string_at("$.job_id"),
                    "application_id": sfn.JsonPath.string_at("$.application_id"),
                    "company_context": sfn.JsonPath.object_at(
                        "$.company_research_result.company_context"
                    ),
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
            result_path="$.company_research_result",
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
