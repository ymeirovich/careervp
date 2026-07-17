"""P-26 Job 1 resource-import outcome tests.

scope_lock_clause: P-26

These are RED outcome tests for the accepted P-26 Job 1 amendment. They assert
the desired post-migration shape only: a human-gated CloudFormation
resource-import / ``cdk refactor`` migration has re-homed explicitly named
feature resources into per-feature nested stacks while preserving their physical
names. They intentionally do not inspect or tailor to an implementation.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, NamedTuple

import pytest

os.environ.setdefault('JSII_RUNTIME_PACKAGE_CACHE', '/tmp/jsii-cache')

try:
    from aws_cdk import App, Environment, NestedStack
    from aws_cdk.assertions import Template

    CDK_AVAILABLE = True
except Exception:  # pragma: no cover - environment guard
    CDK_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CDK_AVAILABLE, reason='aws-cdk not available')

REPO_ROOT = Path(__file__).resolve().parents[4]
INFRA_SRC = str(REPO_ROOT / 'infra')

PARENT_HEADROOM_TARGET = 400

ARTIFACT_CHAIN_STATE_MACHINE_LOGICAL_ID = 'CareerVpCrudDevCrudArtifactChainArtifactChainStateMachine53EF3518'

Resource = dict[str, Any]
TemplateJson = dict[str, Any]


class SynthesizedTemplates(NamedTuple):
    parent: TemplateJson
    nested: dict[str, TemplateJson]


class RehomedResource(NamedTuple):
    feature: str
    logical_id: str
    resource_type: str
    physical_property: str
    physical_value: str


# Spec lines 96-104 require moving feature Lambdas/log groups/queues around,
# not including the RestApi; amendment lines 164-171 supersede the mechanism as
# resource-import with physical ids preserved.
EXPECTED_REHOMED_RESOURCES: tuple[RehomedResource, ...] = (
    RehomedResource(
        'application-api',
        'CareerVpCrudDevCrudApplicationApiLambdaBB38A503',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-application-api-lambda-dev',
    ),
    RehomedResource(
        'application-api',
        'CareerVpCrudDevCrudApplicationApiLogGroupF9368C99',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-application-api-lambda-dev',
    ),
    RehomedResource(
        'artifact-chain',
        'CareerVpCrudDevCrudArtifactCleanupLambda79CF058B',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-artifact-cleanup-lambda-dev',
    ),
    RehomedResource(
        'artifact-chain',
        'CareerVpCrudDevCrudArtifactCleanupLogGroupF215564C',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-artifact-cleanup-lambda-dev',
    ),
    RehomedResource(
        'artifact-chain',
        'CareerVpCrudDevCrudArtifactFailureHandlerLambda18A7802A',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-artifact-failure-handler-lambda-dev',
    ),
    RehomedResource(
        'artifact-chain',
        'CareerVpCrudDevCrudArtifactFailureHandlerLogGroupE59906E1',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-artifact-failure-handler-lambda-dev',
    ),
    RehomedResource(
        'artifact-chain',
        'CareerVpCrudDevCrudArtifactChainArtifactChainStateMachine53EF3518',
        'AWS::StepFunctions::StateMachine',
        'StateMachineName',
        'careervp-artifact-chain-statemachine-dev',
    ),
    RehomedResource(
        'auth-api',
        'CareerVpCrudDevCrudAuthApiLambda17FB112D',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-auth-api-lambda-dev',
    ),
    RehomedResource(
        'auth-api',
        'CareerVpCrudDevCrudAuthApiLogGroup9F324CD2',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-auth-api-lambda-dev',
    ),
    RehomedResource(
        'billing',
        'CareerVpCrudDevCrudBillingLambda7D1D661F',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-billing-lambda-dev',
    ),
    RehomedResource(
        'billing',
        'CareerVpCrudDevCrudBillingLambdaLogGroupB22C0DB8',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-billing-lambda-dev',
    ),
    RehomedResource(
        'billing',
        'CareerVpCrudDevCrudBillingReconcileLambda2B292B98',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-billing-reconcile-lambda-dev',
    ),
    RehomedResource(
        'billing',
        'CareerVpCrudDevCrudBillingReconcileLambdaLogGroup3CD29189',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-billing-reconcile-lambda-dev',
    ),
    RehomedResource(
        'billing',
        'CareerVpCrudDevCrudBillingWebhookDlq3349F8E1',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-billing-webhook-dlq-dlq-dev',
    ),
    RehomedResource(
        'company-research',
        'CareerVpCrudDevCrudCompanyResearch7A3F17FB',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-company-research-lambda-dev',
    ),
    RehomedResource(
        'company-research',
        'CareerVpCrudDevCrudCompanyResearchLogGroup9D47E2A9',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-company-research-lambda-dev',
    ),
    RehomedResource(
        'company-research',
        'CareerVpCrudDevCrudCompanyResearchWorkerLambda7D8ABCDC',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-company-research-worker-lambda-dev',
    ),
    RehomedResource(
        'company-research',
        'CareerVpCrudDevCrudCompanyResearchWorkerLogGroupF63FB2D2',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-company-research-worker-lambda-dev',
    ),
    RehomedResource(
        'company-research',
        'CareerVpCrudDevCrudCrFailureHandlerLambda3034CC59',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-cr-failure-handler-lambda-dev',
    ),
    RehomedResource(
        'company-research',
        'CareerVpCrudDevCrudCrFailureHandlerLogGroup4CCF8D21',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-cr-failure-handler-lambda-dev',
    ),
    RehomedResource(
        'company-research',
        'CareerVpCrudDevCrudCareerVpCrudDevCruddbCareerVpCrudDevCruddbCompanyResearchDlq39CA5884',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-company-research-dlq-dev',
    ),
    RehomedResource(
        'company-research',
        'CareerVpCrudDevCrudCareerVpCrudDevCruddbCareerVpCrudDevCruddbCompanyResearchQueue2CE10D1C',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-company-research-queue-dev',
    ),
    RehomedResource(
        'cover-letter',
        'CareerVpCrudDevCrudCoverLetterApiLambdaF1340087',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-cover-letter-api-lambda-dev',
    ),
    RehomedResource(
        'cover-letter',
        'CareerVpCrudDevCrudCoverLetterApiLogGroup75F7680F',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-cover-letter-api-lambda-dev',
    ),
    RehomedResource(
        'cover-letter',
        'CareerVpCrudDevCrudCoverLetterStatusLambdaEE80146D',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-cover-letter-status-lambda-dev',
    ),
    RehomedResource(
        'cover-letter',
        'CareerVpCrudDevCrudCoverLetterStatusLogGroup70DE4647',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-cover-letter-status-lambda-dev',
    ),
    RehomedResource(
        'cover-letter',
        'CareerVpCrudDevCrudCoverLetterWorkerLambda57C8BA85',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-cover-letter-worker-lambda-dev',
    ),
    RehomedResource(
        'cover-letter',
        'CareerVpCrudDevCrudCoverLetterWorkerLogGroup4E9F0784',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-cover-letter-worker-lambda-dev',
    ),
    RehomedResource(
        'cover-letter',
        'CareerVpCrudDevCrudCoverLetterWorkerDlqBBEFFA3C',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-cover-letter-worker-dlq-dev',
    ),
    RehomedResource(
        'cover-letter',
        'CareerVpCrudDevCrudcoverletterjobs0FAEBAD6',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-cover-letter-jobs-queue-dev',
    ),
    RehomedResource(
        'cover-letter',
        'CareerVpCrudDevCrudcoverletterjobsdlq986C2324',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-cover-letter-jobs-dlq-dlq-dev',
    ),
    RehomedResource(
        'cv-parser',
        'CareerVpCrudDevCrudCVParserBC347720',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-cv-parser-lambda-dev',
    ),
    RehomedResource(
        'cv-parser',
        'CareerVpCrudDevCrudCVParserLogGroup4B625C9D',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-cv-parser-lambda-dev',
    ),
    RehomedResource(
        'cv-tailor',
        'CareerVpCrudDevCrudCVTailor6C64016D',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-cvtailor-lambda-dev',
    ),
    RehomedResource(
        'cv-tailor',
        'CareerVpCrudDevCrudCVTailorLogGroup4E8E3F04',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-cvtailor-lambda-dev',
    ),
    RehomedResource(
        'cv-tailor',
        'CareerVpCrudDevCrudCvTailorWorkerLambda833E005A',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-cv-tailor-worker-lambda-dev',
    ),
    RehomedResource(
        'cv-tailor',
        'CareerVpCrudDevCrudCvTailorWorkerLogGroupBB311D9E',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-cv-tailor-worker-lambda-dev',
    ),
    RehomedResource(
        'cv-tailor',
        'CareerVpCrudDevCrudCvTailorWorkerDlqD913C386',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-cv-tailor-worker-dlq-dev',
    ),
    RehomedResource(
        'cv-upload',
        'CareerVpCrudDevCrudCvUploadWorkerLambda00500EE7',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-cv-upload-worker-lambda-dev',
    ),
    RehomedResource(
        'cv-upload',
        'CareerVpCrudDevCrudCvUploadWorkerLogGroup1210A83E',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-cv-upload-worker-lambda-dev',
    ),
    RehomedResource(
        'cv-upload',
        'CareerVpCrudDevCrudCareerVpCrudDevCruddbCareerVpCrudDevCruddbCvUploadDlq99105D39',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-cv-upload-dlq-dev',
    ),
    RehomedResource(
        'cv-upload',
        'CareerVpCrudDevCrudCareerVpCrudDevCruddbCareerVpCrudDevCruddbCvUploadQueue20D0E259',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-cv-upload-queue-dev',
    ),
    RehomedResource(
        'cv-upload',
        'CareerVpCrudDevCrudCvUploadWorkerDlqD5275284',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-cv-upload-worker-dlq-dev',
    ),
    RehomedResource(
        'export',
        'CareerVpCrudDevCrudExportLambdaF1173216',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-export-lambda-dev',
    ),
    RehomedResource(
        'export',
        'CareerVpCrudDevCrudExportLambdaLogGroupB1893654',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-export-lambda-dev',
    ),
    RehomedResource(
        'gap-analysis',
        'CareerVpCrudDevCrudGapApiLambda812F6815',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-gap-api-lambda-dev',
    ),
    RehomedResource(
        'gap-analysis',
        'CareerVpCrudDevCrudGapApiLogGroup3B58D93C',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-gap-api-lambda-dev',
    ),
    RehomedResource(
        'gap-analysis',
        'CareerVpCrudDevCrudCareerVpCrudDevCruddbCareerVpCrudDevCruddbGapAnalysisDlq355FDF74',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-gap-analysis-dlq-dev',
    ),
    RehomedResource(
        'gap-analysis',
        'CareerVpCrudDevCrudCareerVpCrudDevCruddbCareerVpCrudDevCruddbGapAnalysisQueue6C243C65',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-gap-analysis-queue-dev',
    ),
    RehomedResource(
        'health-api',
        'CareerVpCrudDevCrudHealthApiLambda7362A696',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-health-api-lambda-dev',
    ),
    RehomedResource(
        'health-api',
        'CareerVpCrudDevCrudHealthApiLogGroupF9614AF7',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-health-api-lambda-dev',
    ),
    RehomedResource(
        'interview-prep',
        'CareerVpCrudDevCrudInterviewPrepApiLambdaA473A407',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-interview-prep-api-lambda-dev',
    ),
    RehomedResource(
        'interview-prep',
        'CareerVpCrudDevCrudInterviewPrepApiLogGroup12C2854A',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-interview-prep-api-lambda-dev',
    ),
    RehomedResource(
        'interview-prep',
        'CareerVpCrudDevCrudInterviewPrepStatusLambdaEFD56213',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-interview-prep-status-lambda-dev',
    ),
    RehomedResource(
        'interview-prep',
        'CareerVpCrudDevCrudInterviewPrepStatusLogGroup5A879FE2',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-interview-prep-status-lambda-dev',
    ),
    RehomedResource(
        'interview-prep',
        'CareerVpCrudDevCrudInterviewPrepWorkerLambdaBE85EFC5',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-interview-prep-worker-lambda-dev',
    ),
    RehomedResource(
        'interview-prep',
        'CareerVpCrudDevCrudInterviewPrepWorkerLogGroupF0BA00E7',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-interview-prep-worker-lambda-dev',
    ),
    RehomedResource(
        'interview-prep',
        'CareerVpCrudDevCrudInterviewPrepWorkerDlqD6FA7DCB',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-interview-prep-worker-dlq-dev',
    ),
    RehomedResource(
        'interview-prep',
        'CareerVpCrudDevCrudinterviewprepjobs713C5624',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-interview-prep-jobs-queue-dev',
    ),
    RehomedResource(
        'interview-prep',
        'CareerVpCrudDevCrudinterviewprepjobsdlqA1000EAC',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-interview-prep-jobs-dlq-dlq-dev',
    ),
    RehomedResource(
        'job-api',
        'CareerVpCrudDevCrudJobApiLambda5F3D17FE',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-job-api-lambda-dev',
    ),
    RehomedResource(
        'job-api',
        'CareerVpCrudDevCrudJobApiLogGroup40EC5CF5',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-job-api-lambda-dev',
    ),
    RehomedResource(
        'user-api',
        'CareerVpCrudDevCrudUserApiLambdaE7900064',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-user-api-lambda-dev',
    ),
    RehomedResource(
        'user-api',
        'CareerVpCrudDevCrudUserApiLogGroup8DF747CB',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-user-api-lambda-dev',
    ),
    RehomedResource(
        'vpr',
        'CareerVpCrudDevCrudVprDlqHandlerLambda64532BB1',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-vpr-dlq-handler-lambda-dev',
    ),
    RehomedResource(
        'vpr',
        'CareerVpCrudDevCrudVprDlqHandlerLogGroupA7335FA3',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-vpr-dlq-handler-lambda-dev',
    ),
    RehomedResource(
        'vpr',
        'CareerVpCrudDevCrudVprSqsWorkerLambda01847413',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-vpr-sqs-worker-lambda-dev',
    ),
    RehomedResource(
        'vpr',
        'CareerVpCrudDevCrudVprSqsWorkerLogGroup777D34E7',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-vpr-sqs-worker-lambda-dev',
    ),
    RehomedResource(
        'vpr',
        'CareerVpCrudDevCrudvprstatus48B483FB',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-vpr-status-lambda-dev',
    ),
    RehomedResource(
        'vpr',
        'CareerVpCrudDevCrudvprstatusLogGroupD5CDD69C',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-vpr-status-lambda-dev',
    ),
    RehomedResource(
        'vpr',
        'CareerVpCrudDevCrudvprsubmit2E46A7B1',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-vpr-submit-lambda-dev',
    ),
    RehomedResource(
        'vpr',
        'CareerVpCrudDevCrudvprsubmitLogGroup46EC4888',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-vpr-submit-lambda-dev',
    ),
    RehomedResource(
        'vpr',
        'CareerVpCrudDevCrudvprworker4EBCC689',
        'AWS::Lambda::Function',
        'FunctionName',
        'careervp-vpr-worker-lambda-dev',
    ),
    RehomedResource(
        'vpr',
        'CareerVpCrudDevCrudvprworkerLogGroup98A9863E',
        'AWS::Logs::LogGroup',
        'LogGroupName',
        '/aws/lambda/careervp-vpr-worker-lambda-dev',
    ),
    RehomedResource(
        'vpr',
        'CareerVpCrudDevCrudvprjobs73443C56',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-vpr-jobs-queue-dev',
    ),
    RehomedResource(
        'vpr',
        'CareerVpCrudDevCrudvprjobsdlq3FC5ADD0',
        'AWS::SQS::Queue',
        'QueueName',
        'careervp-vpr-jobs-dlq-dlq-dev',
    ),
)


ARTIFACT_CHAIN_GRANT_TARGETS = {
    'states:StartExecution': (
        'CareerVpCrudDevCrudvprsubmit2E46A7B1',
        'CareerVpCrudDevCrudCoverLetterApiLambdaF1340087',
        'CareerVpCrudDevCrudInterviewPrepApiLambdaA473A407',
        'CareerVpCrudDevCrudCVTailor6C64016D',
        'CareerVpCrudDevCrudGapApiLambda812F6815',
    ),
    'states:SendTaskSuccess': (
        'CareerVpCrudDevCrudCompanyResearchWorkerLambda7D8ABCDC',
        'CareerVpCrudDevCrudVprSqsWorkerLambda01847413',
        'CareerVpCrudDevCrudCoverLetterWorkerLambda57C8BA85',
        'CareerVpCrudDevCrudInterviewPrepWorkerLambdaBE85EFC5',
    ),
    'states:SendTaskFailure': (
        'CareerVpCrudDevCrudCompanyResearchWorkerLambda7D8ABCDC',
        'CareerVpCrudDevCrudVprSqsWorkerLambda01847413',
        'CareerVpCrudDevCrudCoverLetterWorkerLambda57C8BA85',
        'CareerVpCrudDevCrudInterviewPrepWorkerLambdaBE85EFC5',
    ),
}


P24_AUTHORIZER = RehomedResource(
    'api-authorizer',
    'CareerVpCrudDevCrudApiAuthorizerLambda',
    'AWS::Lambda::Function',
    'FunctionName',
    'careervp-api-authorizer-lambda-dev',
)


def _dev_stack() -> Any:
    if INFRA_SRC not in sys.path:
        sys.path.insert(0, INFRA_SRC)

    from careervp.naming_utils import NamingUtils  # type: ignore[import-not-found]
    from careervp.service_stack import ServiceStack  # type: ignore[import-not-found]

    app = App()
    naming = NamingUtils(environment='dev', region='us-east-1', account_id='788159322332')
    return ServiceStack(
        scope=app,
        id=naming.stack_id('crud'),
        env=Environment(account='788159322332', region='us-east-1'),
        is_production_env=False,
        naming=naming,
        stack_feature='crud',
    )


def _nested_stack_templates(stack: Any) -> dict[str, TemplateJson]:
    nested: dict[str, TemplateJson] = {}
    for construct in stack.node.find_all():
        if isinstance(construct, NestedStack):
            nested[construct.node.path] = dict(Template.from_stack(construct).to_json())
    return nested


@lru_cache(maxsize=1)
def _templates() -> SynthesizedTemplates:
    stack = _dev_stack()
    return SynthesizedTemplates(
        parent=dict(Template.from_stack(stack).to_json()),
        nested=_nested_stack_templates(stack),
    )


def _resource(template: TemplateJson, logical_id: str) -> Resource | None:
    resources = template.get('Resources', {})
    candidate = resources.get(logical_id)
    if isinstance(candidate, dict):
        return candidate
    return None


def _nested_resource(logical_id: str) -> tuple[str, Resource] | None:
    for nested_name, template in _templates().nested.items():
        candidate = _resource(template, logical_id)
        if candidate is not None:
            return nested_name, candidate
    return None


def _resource_with_physical_name(expected: RehomedResource) -> tuple[str, str, Resource] | None:
    for template_name, template in (('parent', _templates().parent), *_templates().nested.items()):
        for logical_id, resource in template.get('Resources', {}).items():
            if not isinstance(resource, dict):
                continue
            if resource.get('Type') != expected.resource_type:
                continue
            if resource.get('Properties', {}).get(expected.physical_property) == expected.physical_value:
                return template_name, logical_id, resource
    return None


def _template_blob() -> str:
    return repr({'parent': _templates().parent, 'nested': _templates().nested})


def _failure_summary(failures: list[str], *, limit: int = 20) -> str:
    displayed = failures[:limit]
    remaining = len(failures) - len(displayed)
    summary = '\n'.join(displayed)
    if remaining > 0:
        summary += f'\n... {remaining} more failures omitted'
    return summary


def test_parent_template_resource_count_is_below_job1_headroom_target() -> None:
    # Spec line 103 names <400 as the Job-1 headroom target; AC-P26-2 at
    # spec lines 164-166 requires the completed decomposition to trend there.
    parent_count = len(_templates().parent.get('Resources', {}))

    assert parent_count < PARENT_HEADROOM_TARGET, (
        f'P-26 Job 1 must reduce the parent template below {PARENT_HEADROOM_TARGET} resources; current parent has {parent_count}.'
    )


def test_rehomed_feature_resources_live_in_nested_stacks_not_parent() -> None:
    # Spec lines 96-102 require feature Lambdas/log groups/queues to move into
    # per-feature nested stacks while the RestApi remains in the parent.
    failures: list[str] = []

    for expected in EXPECTED_REHOMED_RESOURCES:
        parent_resource = _resource(_templates().parent, expected.logical_id)
        nested_match = _nested_resource(expected.logical_id)

        if parent_resource is not None:
            failures.append(f'{expected.logical_id} ({expected.resource_type}) still lives in the parent template')
        if nested_match is None:
            failures.append(f'{expected.logical_id} ({expected.resource_type}) is absent from all nested templates')
            continue

        nested_name, nested_resource = nested_match
        if nested_resource.get('Type') != expected.resource_type:
            failures.append(f'{expected.logical_id} in {nested_name} has type {nested_resource.get("Type")!r}; expected {expected.resource_type!r}')

    assert not failures, 'P-26 Job 1 re-home outcome is incomplete:\n' + _failure_summary(failures)


def test_rehomed_physical_names_are_preserved_byte_identical() -> None:
    # Amendment lines 164-171 make resource-import mandatory because the
    # existing explicit physical names must be preserved with no delete/create.
    failures: list[str] = []

    for expected in EXPECTED_REHOMED_RESOURCES:
        match = _resource_with_physical_name(expected)
        if match is None:
            failures.append(f'{expected.feature}: no {expected.resource_type} has {expected.physical_property}={expected.physical_value!r}')
            continue

        template_name, logical_id, resource = match
        if template_name == 'parent':
            failures.append(
                f'{expected.feature}: {expected.physical_value!r} is still in the parent at {logical_id}, not imported into a feature nested stack'
            )
        if logical_id != expected.logical_id:
            failures.append(
                f'{expected.feature}: {expected.physical_value!r} moved under logical id {logical_id}; '
                f'expected resource-import mapping to keep {expected.logical_id}'
            )
        physical_value = resource.get('Properties', {}).get(expected.physical_property)
        if physical_value != expected.physical_value:
            failures.append(
                f'{expected.feature}: {expected.logical_id} has {expected.physical_property}={physical_value!r}; expected {expected.physical_value!r}'
            )

    assert not failures, 'P-26 Job 1 physical-id preservation is incomplete:\n' + _failure_summary(failures)


def test_artifact_chain_grants_still_resolve_after_rehoming() -> None:
    # Amendment lines 109-114 require the artifact-chain grant_start_execution /
    # grant_task_response export locks to be broken/re-imported in the same
    # transaction; spec line 53 explains the cross-stack export/import lock.
    failures: list[str] = []

    for action, target_logical_ids in ARTIFACT_CHAIN_GRANT_TARGETS.items():
        if action not in _template_blob():
            failures.append(f'artifact-chain grant action {action!r} is missing from synthesized templates')
        for target_logical_id in target_logical_ids:
            if _nested_resource(target_logical_id) is None:
                failures.append(f'artifact-chain grant target {target_logical_id} is not re-homed into a nested template')

    if ARTIFACT_CHAIN_STATE_MACHINE_LOGICAL_ID not in _template_blob():
        failures.append(f'artifact-chain state machine {ARTIFACT_CHAIN_STATE_MACHINE_LOGICAL_ID} is not referenced by the synthesized grant graph')

    assert not failures, 'P-26 Job 1 artifact-chain grant resolution is incomplete:\n' + _failure_summary(failures)


def test_p24_api_authorizer_lambda_is_accounted_for_in_rehome_mapping() -> None:
    # Amendment lines 164-171 cover explicit-name movable Lambdas. The P-24
    # authorizer was added later at api_construct.py:2034 with the same physical
    # naming pattern, so the Job-1 mapping must account for it too.
    parent_resource = _resource(_templates().parent, P24_AUTHORIZER.logical_id)
    nested_match = _nested_resource(P24_AUTHORIZER.logical_id)
    physical_match = _resource_with_physical_name(P24_AUTHORIZER)

    assert parent_resource is None, f'{P24_AUTHORIZER.logical_id} must not remain in the parent after P-26 Job 1'
    assert nested_match is not None, f'{P24_AUTHORIZER.logical_id} is missing from all per-feature nested templates'
    assert physical_match is not None, f'{P24_AUTHORIZER.logical_id} must preserve FunctionName={P24_AUTHORIZER.physical_value!r}'
    assert physical_match[0] != 'parent', f'{P24_AUTHORIZER.physical_value!r} is still in the parent template'
