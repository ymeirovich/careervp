# DynamoDB Tables Stack (Refactoring Phases)
# Generated from: infra/careervp/specs/dynamodb_spec.yaml
# Uses NamingUtils for consistent naming: careervp-{feature}-table-{env}

import careervp.constants as constants
from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_dynamodb as dynamodb,
)
from careervp.naming_utils import NamingUtils
from constructs import Construct


class DynamoDBStack(Stack):
    """DynamoDB tables for CareerVP refactoring phases.

    Note: Existing tables (users, sessions, jobs, idempotency) are in ApiDbConstruct.
    This stack adds NEW tables needed by the refactoring phases.
    All names use NamingUtils.table_name() for consistency.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        naming = NamingUtils()

        # CVs table (Phase 4)
        self.cvs_table = dynamodb.Table(
            self,
            "CVsTable",
            table_name=naming.table_name(constants.CVS_TABLE_NAME),
            partition_key=dynamodb.Attribute(
                name="user_email",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="cv_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Applications table
        self.applications_table = dynamodb.Table(
            self,
            "ApplicationsTable",
            table_name=naming.table_name(constants.APPLICATIONS_TABLE_NAME),
            partition_key=dynamodb.Attribute(
                name="user_email",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="application_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Gap responses table (Phase 5)
        self.gap_responses_table = dynamodb.Table(
            self,
            "GapResponsesTable",
            table_name=naming.table_name(constants.GAP_RESPONSES_TABLE_NAME),
            partition_key=dynamodb.Attribute(
                name="user_email",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="application_id",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Knowledge base table (Phase 8)
        self.knowledge_table = dynamodb.Table(
            self,
            "KnowledgeTable",
            table_name=naming.table_name(constants.KNOWLEDGE_TABLE_NAME),
            partition_key=dynamodb.Attribute(
                name="user_email",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="entity_type",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
        )
