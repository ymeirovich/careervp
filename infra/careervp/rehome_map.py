"""Auto-generated P-26 Job-1 resource-import logical-id map.

Source of truth: src/backend/tests/infrastructure/test_p26_job1_resource_import_outcomes.py
(EXPECTED_REHOMED_RESOURCES + P24_AUTHORIZER). Maps each already-deployed
explicit physical name to its CURRENT (parent-template) logical id, so the
CrudFeaturesNestedStack can re-home the construct while preserving the logical
id byte-for-byte (a human-gated ``cdk refactor`` resource-import, P-26 Job 1).
"""

from __future__ import annotations

from typing import TypeVar

from aws_cdk import CfnResource
from constructs import IConstruct

_T = TypeVar("_T", bound=IConstruct)


def rehome(construct: _T, physical_name: str) -> _T:
    """Preserve a re-homed resource's deployed logical id byte-for-byte.

    P-26 Job 1 moves explicitly-named resources into ``CrudFeaturesNestedStack``
    via a human-gated ``cdk refactor`` resource-import. CloudFormation refactor
    maps ``OldStack.OldLogicalId -> NewStack.NewLogicalId``; keeping the logical
    id identical (only the containing template changes) is what makes the move a
    clean IMPORT with no delete/create. The deployed logical ids are dev-specific
    (``CareerVpCrudDev...``); for other environments the physical name is not in
    the map and the natural nested logical id is left in place (no environment
    but dev is deployed for this migration).
    """
    logical_id = REHOME_LOGICAL_IDS.get(physical_name)
    if logical_id is not None:
        child = construct.node.default_child
        if not isinstance(child, CfnResource):
            raise TypeError(
                f"rehome() expected an L2 construct with a CfnResource default "
                f"child for {physical_name!r}, got {type(child).__name__}"
            )
        child.override_logical_id(logical_id)
    return construct


def rehome_cfn(resource: CfnResource, physical_name: str) -> CfnResource:
    """``rehome`` for a raw L1 ``CfnResource`` (e.g. a nested state machine)."""
    logical_id = REHOME_LOGICAL_IDS.get(physical_name)
    if logical_id is not None:
        resource.override_logical_id(logical_id)
    return resource


REHOME_LOGICAL_IDS: dict[str, str] = {
    "careervp-application-api-lambda-dev": "CareerVpCrudDevCrudApplicationApiLambdaBB38A503",
    "/aws/lambda/careervp-application-api-lambda-dev": "CareerVpCrudDevCrudApplicationApiLogGroupF9368C99",
    "careervp-artifact-cleanup-lambda-dev": "CareerVpCrudDevCrudArtifactCleanupLambda79CF058B",
    "/aws/lambda/careervp-artifact-cleanup-lambda-dev": "CareerVpCrudDevCrudArtifactCleanupLogGroupF215564C",
    "careervp-artifact-failure-handler-lambda-dev": "CareerVpCrudDevCrudArtifactFailureHandlerLambda18A7802A",
    "/aws/lambda/careervp-artifact-failure-handler-lambda-dev": "CareerVpCrudDevCrudArtifactFailureHandlerLogGroupE59906E1",
    "careervp-artifact-chain-statemachine-dev": "CareerVpCrudDevCrudArtifactChainArtifactChainStateMachine53EF3518",
    "careervp-auth-api-lambda-dev": "CareerVpCrudDevCrudAuthApiLambda17FB112D",
    "/aws/lambda/careervp-auth-api-lambda-dev": "CareerVpCrudDevCrudAuthApiLogGroup9F324CD2",
    "careervp-billing-lambda-dev": "CareerVpCrudDevCrudBillingLambda7D1D661F",
    "/aws/lambda/careervp-billing-lambda-dev": "CareerVpCrudDevCrudBillingLambdaLogGroupB22C0DB8",
    "careervp-billing-reconcile-lambda-dev": "CareerVpCrudDevCrudBillingReconcileLambda2B292B98",
    "/aws/lambda/careervp-billing-reconcile-lambda-dev": "CareerVpCrudDevCrudBillingReconcileLambdaLogGroup3CD29189",
    "careervp-billing-webhook-dlq-dlq-dev": "CareerVpCrudDevCrudBillingWebhookDlq3349F8E1",
    "careervp-company-research-lambda-dev": "CareerVpCrudDevCrudCompanyResearch7A3F17FB",
    "/aws/lambda/careervp-company-research-lambda-dev": "CareerVpCrudDevCrudCompanyResearchLogGroup9D47E2A9",
    "careervp-company-research-worker-lambda-dev": "CareerVpCrudDevCrudCompanyResearchWorkerLambda7D8ABCDC",
    "/aws/lambda/careervp-company-research-worker-lambda-dev": "CareerVpCrudDevCrudCompanyResearchWorkerLogGroupF63FB2D2",
    "careervp-cr-failure-handler-lambda-dev": "CareerVpCrudDevCrudCrFailureHandlerLambda3034CC59",
    "/aws/lambda/careervp-cr-failure-handler-lambda-dev": "CareerVpCrudDevCrudCrFailureHandlerLogGroup4CCF8D21",
    "careervp-company-research-dlq-dev": "CareerVpCrudDevCrudCareerVpCrudDevCruddbCareerVpCrudDevCruddbCompanyResearchDlq39CA5884",
    "careervp-company-research-queue-dev": "CareerVpCrudDevCrudCareerVpCrudDevCruddbCareerVpCrudDevCruddbCompanyResearchQueue2CE10D1C",
    "careervp-cover-letter-api-lambda-dev": "CareerVpCrudDevCrudCoverLetterApiLambdaF1340087",
    "/aws/lambda/careervp-cover-letter-api-lambda-dev": "CareerVpCrudDevCrudCoverLetterApiLogGroup75F7680F",
    "careervp-cover-letter-status-lambda-dev": "CareerVpCrudDevCrudCoverLetterStatusLambdaEE80146D",
    "/aws/lambda/careervp-cover-letter-status-lambda-dev": "CareerVpCrudDevCrudCoverLetterStatusLogGroup70DE4647",
    "careervp-cover-letter-worker-lambda-dev": "CareerVpCrudDevCrudCoverLetterWorkerLambda57C8BA85",
    "/aws/lambda/careervp-cover-letter-worker-lambda-dev": "CareerVpCrudDevCrudCoverLetterWorkerLogGroup4E9F0784",
    "careervp-cover-letter-worker-dlq-dev": "CareerVpCrudDevCrudCoverLetterWorkerDlqBBEFFA3C",
    "careervp-cover-letter-jobs-queue-dev": "CareerVpCrudDevCrudcoverletterjobs0FAEBAD6",
    "careervp-cover-letter-jobs-dlq-dlq-dev": "CareerVpCrudDevCrudcoverletterjobsdlq986C2324",
    "careervp-cv-parser-lambda-dev": "CareerVpCrudDevCrudCVParserBC347720",
    "/aws/lambda/careervp-cv-parser-lambda-dev": "CareerVpCrudDevCrudCVParserLogGroup4B625C9D",
    "careervp-cvtailor-lambda-dev": "CareerVpCrudDevCrudCVTailor6C64016D",
    "/aws/lambda/careervp-cvtailor-lambda-dev": "CareerVpCrudDevCrudCVTailorLogGroup4E8E3F04",
    "careervp-cv-tailor-worker-lambda-dev": "CareerVpCrudDevCrudCvTailorWorkerLambda833E005A",
    "/aws/lambda/careervp-cv-tailor-worker-lambda-dev": "CareerVpCrudDevCrudCvTailorWorkerLogGroupBB311D9E",
    "careervp-cv-tailor-worker-dlq-dev": "CareerVpCrudDevCrudCvTailorWorkerDlqD913C386",
    "careervp-cv-upload-worker-lambda-dev": "CareerVpCrudDevCrudCvUploadWorkerLambda00500EE7",
    "/aws/lambda/careervp-cv-upload-worker-lambda-dev": "CareerVpCrudDevCrudCvUploadWorkerLogGroup1210A83E",
    "careervp-cv-upload-dlq-dev": "CareerVpCrudDevCrudCareerVpCrudDevCruddbCareerVpCrudDevCruddbCvUploadDlq99105D39",
    "careervp-cv-upload-queue-dev": "CareerVpCrudDevCrudCareerVpCrudDevCruddbCareerVpCrudDevCruddbCvUploadQueue20D0E259",
    "careervp-cv-upload-worker-dlq-dev": "CareerVpCrudDevCrudCvUploadWorkerDlqD5275284",
    "careervp-export-lambda-dev": "CareerVpCrudDevCrudExportLambdaF1173216",
    "/aws/lambda/careervp-export-lambda-dev": "CareerVpCrudDevCrudExportLambdaLogGroupB1893654",
    "careervp-gap-api-lambda-dev": "CareerVpCrudDevCrudGapApiLambda812F6815",
    "/aws/lambda/careervp-gap-api-lambda-dev": "CareerVpCrudDevCrudGapApiLogGroup3B58D93C",
    "careervp-gap-analysis-dlq-dev": "CareerVpCrudDevCrudCareerVpCrudDevCruddbCareerVpCrudDevCruddbGapAnalysisDlq355FDF74",
    "careervp-gap-analysis-queue-dev": "CareerVpCrudDevCrudCareerVpCrudDevCruddbCareerVpCrudDevCruddbGapAnalysisQueue6C243C65",
    "careervp-health-api-lambda-dev": "CareerVpCrudDevCrudHealthApiLambda7362A696",
    "/aws/lambda/careervp-health-api-lambda-dev": "CareerVpCrudDevCrudHealthApiLogGroupF9614AF7",
    "careervp-interview-prep-api-lambda-dev": "CareerVpCrudDevCrudInterviewPrepApiLambdaA473A407",
    "/aws/lambda/careervp-interview-prep-api-lambda-dev": "CareerVpCrudDevCrudInterviewPrepApiLogGroup12C2854A",
    "careervp-interview-prep-status-lambda-dev": "CareerVpCrudDevCrudInterviewPrepStatusLambdaEFD56213",
    "/aws/lambda/careervp-interview-prep-status-lambda-dev": "CareerVpCrudDevCrudInterviewPrepStatusLogGroup5A879FE2",
    "careervp-interview-prep-worker-lambda-dev": "CareerVpCrudDevCrudInterviewPrepWorkerLambdaBE85EFC5",
    "/aws/lambda/careervp-interview-prep-worker-lambda-dev": "CareerVpCrudDevCrudInterviewPrepWorkerLogGroupF0BA00E7",
    "careervp-interview-prep-worker-dlq-dev": "CareerVpCrudDevCrudInterviewPrepWorkerDlqD6FA7DCB",
    "careervp-interview-prep-jobs-queue-dev": "CareerVpCrudDevCrudinterviewprepjobs713C5624",
    "careervp-interview-prep-jobs-dlq-dlq-dev": "CareerVpCrudDevCrudinterviewprepjobsdlqA1000EAC",
    "careervp-job-api-lambda-dev": "CareerVpCrudDevCrudJobApiLambda5F3D17FE",
    "/aws/lambda/careervp-job-api-lambda-dev": "CareerVpCrudDevCrudJobApiLogGroup40EC5CF5",
    "careervp-user-api-lambda-dev": "CareerVpCrudDevCrudUserApiLambdaE7900064",
    "/aws/lambda/careervp-user-api-lambda-dev": "CareerVpCrudDevCrudUserApiLogGroup8DF747CB",
    "careervp-vpr-dlq-handler-lambda-dev": "CareerVpCrudDevCrudVprDlqHandlerLambda64532BB1",
    "/aws/lambda/careervp-vpr-dlq-handler-lambda-dev": "CareerVpCrudDevCrudVprDlqHandlerLogGroupA7335FA3",
    "careervp-vpr-sqs-worker-lambda-dev": "CareerVpCrudDevCrudVprSqsWorkerLambda01847413",
    "/aws/lambda/careervp-vpr-sqs-worker-lambda-dev": "CareerVpCrudDevCrudVprSqsWorkerLogGroup777D34E7",
    "careervp-vpr-status-lambda-dev": "CareerVpCrudDevCrudvprstatus48B483FB",
    "/aws/lambda/careervp-vpr-status-lambda-dev": "CareerVpCrudDevCrudvprstatusLogGroupD5CDD69C",
    "careervp-vpr-submit-lambda-dev": "CareerVpCrudDevCrudvprsubmit2E46A7B1",
    "/aws/lambda/careervp-vpr-submit-lambda-dev": "CareerVpCrudDevCrudvprsubmitLogGroup46EC4888",
    "careervp-vpr-worker-lambda-dev": "CareerVpCrudDevCrudvprworker4EBCC689",
    "/aws/lambda/careervp-vpr-worker-lambda-dev": "CareerVpCrudDevCrudvprworkerLogGroup98A9863E",
    "careervp-vpr-jobs-queue-dev": "CareerVpCrudDevCrudvprjobs73443C56",
    "careervp-vpr-jobs-dlq-dlq-dev": "CareerVpCrudDevCrudvprjobsdlq3FC5ADD0",
    "careervp-api-authorizer-lambda-dev": "CareerVpCrudDevCrudApiAuthorizerLambda",
}
