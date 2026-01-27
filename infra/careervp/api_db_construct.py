"""
CareerVP Database and Storage Constructs.
DynamoDB tables and S3 buckets for the CV processing pipeline.
"""

import careervp.constants as constants
from aws_cdk import CfnOutput, Duration, RemovalPolicy
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_s3 as s3
from constructs import Construct


class ApiDbConstruct(Construct):
    """
    Creates DynamoDB tables and S3 buckets for CareerVP.

    Tables:
    - Users: Single table design for user profiles and parsed CVs
    - Idempotency: For Lambda idempotency

    Buckets:
    - CV Bucket: Stores uploaded CV files (PDF, DOCX)
    """

    def __init__(self, scope: Construct, id_: str) -> None:
        super().__init__(scope, id_)

        # DynamoDB Tables
        self.users_table: dynamodb.TableV2 = self._build_users_table(id_)
        self.idempotency_db: dynamodb.TableV2 = self._build_idempotency_table(id_)

        # S3 Buckets
        self.cv_bucket: s3.Bucket = self._build_cv_bucket(id_)

        # Backwards compatibility alias
        self.db = self.users_table

    def _build_users_table(self, id_prefix: str) -> dynamodb.TableV2:
        """
        Users table with Single Table Design.
        PK: user_id
        SK: record_type (PROFILE, CV, SESSION#<id>, JOB#<id>)
        """
        table_id = f"{id_prefix}{constants.USERS_TABLE_NAME}"
        table = dynamodb.TableV2(
            self,
            table_id,
            table_name=None,
            partition_key=dynamodb.Attribute(
                name="pk", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(name="sk", type=dynamodb.AttributeType.STRING),
            billing=dynamodb.Billing.on_demand(),
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True,
                recovery_period_in_days=7,
            ),
            removal_policy=RemovalPolicy.DESTROY,
            contributor_insights_specification=dynamodb.ContributorInsightsSpecification(
                enabled=True,
                mode=dynamodb.ContributorInsightsMode.THROTTLED_KEYS,
            ),
            global_secondary_indexes=[
                dynamodb.GlobalSecondaryIndexPropsV2(
                    index_name="email-index",
                    partition_key=dynamodb.Attribute(
                        name="email", type=dynamodb.AttributeType.STRING
                    ),
                    projection_type=dynamodb.ProjectionType.ALL,
                ),
                dynamodb.GlobalSecondaryIndexPropsV2(
                    index_name="user_id-index",
                    partition_key=dynamodb.Attribute(
                        name="user_id", type=dynamodb.AttributeType.STRING
                    ),
                    sort_key=dynamodb.Attribute(
                        name="sk", type=dynamodb.AttributeType.STRING
                    ),
                    projection_type=dynamodb.ProjectionType.ALL,
                ),
            ],
        )
        CfnOutput(
            self, id=constants.TABLE_NAME_OUTPUT, value=table.table_name
        ).override_logical_id(constants.TABLE_NAME_OUTPUT)
        return table

    def _build_idempotency_table(self, id_: str) -> dynamodb.TableV2:
        """Idempotency table for Lambda Powertools."""
        table_id = f"{id_}{constants.IDEMPOTENCY_TABLE_NAME}"
        table = dynamodb.TableV2(
            self,
            table_id,
            table_name=table_id,
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
            billing=dynamodb.Billing.on_demand(),
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="expiration",
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True,
                recovery_period_in_days=35,
            ),
        )
        CfnOutput(
            self, id=constants.IDEMPOTENCY_TABLE_NAME_OUTPUT, value=table.table_name
        ).override_logical_id(constants.IDEMPOTENCY_TABLE_NAME_OUTPUT)
        return table

    def _build_cv_bucket(self, id_prefix: str) -> s3.Bucket:
        """
        S3 bucket for CV uploads.
        Lifecycle: 7 days -> Glacier, 30 days -> Delete
        """
        bucket_id = f"{id_prefix}{constants.CV_BUCKET_NAME}"
        bucket = s3.Bucket(
            self,
            bucket_id,
            bucket_name=None,  # Auto-generate unique name
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=False,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="transition-to-glacier",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(7),
                        )
                    ],
                    expiration=Duration.days(30),
                    enabled=True,
                ),
            ],
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.POST,
                        s3.HttpMethods.GET,
                    ],
                    allowed_origins=["*"],  # Restrict in production
                    allowed_headers=["*"],
                    max_age=3000,
                )
            ],
        )
        CfnOutput(
            self, id=constants.CV_BUCKET_OUTPUT, value=bucket.bucket_name
        ).override_logical_id(constants.CV_BUCKET_OUTPUT)
        return bucket
