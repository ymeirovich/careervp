"""
CareerVP Database and Storage Constructs.
DynamoDB tables and S3 buckets for the CV processing pipeline.
"""

import careervp.constants as constants
from aws_cdk import CfnOutput, Duration, RemovalPolicy
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_s3 as s3
from careervp.naming_utils import NamingUtils
from constructs import Construct


class ApiDbConstruct(Construct):
    """
    Creates DynamoDB tables and S3 buckets for CareerVP.

    Tables:
    - Users: Single table design for user profiles and parsed CVs
    - Idempotency: For Lambda idempotency
    - Jobs: Async VPR job tracking
    - CVs / Applications / Gap Responses / Knowledge / Artifacts / Company Research Cache

    Buckets:
    - CV Bucket: Stores uploaded CV files (PDF, DOCX)
    """

    def __init__(self, scope: Construct, id_: str, naming: NamingUtils) -> None:
        super().__init__(scope, id_)
        self.naming = naming

        # DynamoDB Tables
        self.users_table: dynamodb.TableV2 = self._build_users_table(id_)
        self.idempotency_db: dynamodb.TableV2 = self._build_idempotency_table(id_)
        self.jobs_table: dynamodb.TableV2 = self._build_vpr_jobs_table(id_)

        # New async/storage tables required by endpoint coverage specs.
        self.cvs_table: dynamodb.TableV2 = self._build_cvs_table(id_)
        self.applications_table: dynamodb.TableV2 = self._build_applications_table(id_)
        self.gap_responses_table: dynamodb.TableV2 = self._build_gap_responses_table(
            id_
        )
        self.knowledge_table: dynamodb.TableV2 = self._build_knowledge_table(id_)
        self.artifacts_table: dynamodb.TableV2 = self._build_artifacts_table(id_)
        self.company_research_cache_table: dynamodb.TableV2 = (
            self._build_company_research_cache_table(id_)
        )

        # S3 Buckets
        self.cv_bucket: s3.Bucket = self._build_cv_bucket(id_)
        self.vpr_results_bucket: s3.Bucket = self._build_vpr_results_bucket(id_)

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
            table_name=self.naming.table_name(constants.USERS_TABLE_NAME),
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
            table_name=self.naming.table_name(constants.IDEMPOTENCY_TABLE_NAME),
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
            bucket_name=self.naming.bucket_name(constants.CV_BUCKET_NAME),
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

    def _build_vpr_jobs_table(self, id_prefix: str) -> dynamodb.TableV2:
        """
        VPR Jobs table for async job tracking.

        PK: job_id
        GSI: idempotency-key-index for duplicate detection
        TTL: 24 hours for job data
        """
        table_id = f"{id_prefix}{constants.JOBS_TABLE_NAME}"
        table = dynamodb.TableV2(
            self,
            table_id,
            table_name=self.naming.table_name(constants.JOBS_TABLE_NAME),
            partition_key=dynamodb.Attribute(
                name="job_id", type=dynamodb.AttributeType.STRING
            ),
            billing=dynamodb.Billing.on_demand(),
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True,
                recovery_period_in_days=7,
            ),
            global_secondary_indexes=[
                dynamodb.GlobalSecondaryIndexPropsV2(
                    index_name="idempotency-key-index",
                    partition_key=dynamodb.Attribute(
                        name="idempotency_key", type=dynamodb.AttributeType.STRING
                    ),
                    projection_type=dynamodb.ProjectionType.ALL,
                ),
            ],
        )
        CfnOutput(
            self, id=constants.JOBS_TABLE_OUTPUT, value=table.table_name
        ).override_logical_id(constants.JOBS_TABLE_OUTPUT)
        return table

    def _build_cvs_table(self, id_prefix: str) -> dynamodb.TableV2:
        """CV metadata table. TTL keeps stale CV artifacts for 90 days."""
        table_id = f"{id_prefix}CvsTable"
        table = dynamodb.TableV2(
            self,
            table_id,
            table_name=self.naming.table_name(constants.CVS_TABLE_NAME),
            partition_key=dynamodb.Attribute(
                name="userId", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="cvId", type=dynamodb.AttributeType.STRING
            ),
            billing=dynamodb.Billing.on_demand(),
            time_to_live_attribute="expiration",
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True,
                recovery_period_in_days=7,
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )
        CfnOutput(
            self, id=constants.CVS_TABLE_OUTPUT, value=table.table_name
        ).override_logical_id(constants.CVS_TABLE_OUTPUT)
        return table

    def _build_applications_table(self, id_prefix: str) -> dynamodb.TableV2:
        """Applications table with status-index for per-user workflow filtering."""
        table_id = f"{id_prefix}ApplicationsTable"
        table = dynamodb.TableV2(
            self,
            table_id,
            table_name=self.naming.table_name(constants.APPLICATIONS_TABLE_NAME),
            partition_key=dynamodb.Attribute(
                name="userId", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="applicationId", type=dynamodb.AttributeType.STRING
            ),
            billing=dynamodb.Billing.on_demand(),
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True,
                recovery_period_in_days=7,
            ),
            removal_policy=RemovalPolicy.DESTROY,
            global_secondary_indexes=[
                dynamodb.GlobalSecondaryIndexPropsV2(
                    index_name="status-index",
                    partition_key=dynamodb.Attribute(
                        name="userId", type=dynamodb.AttributeType.STRING
                    ),
                    sort_key=dynamodb.Attribute(
                        name="status", type=dynamodb.AttributeType.STRING
                    ),
                    projection_type=dynamodb.ProjectionType.ALL,
                ),
            ],
        )
        CfnOutput(
            self, id=constants.APPLICATIONS_TABLE_OUTPUT, value=table.table_name
        ).override_logical_id(constants.APPLICATIONS_TABLE_OUTPUT)
        return table

    def _build_gap_responses_table(self, id_prefix: str) -> dynamodb.TableV2:
        """Gap-analysis question/answer table with 365-day TTL for old responses."""
        table_id = f"{id_prefix}GapResponsesTable"
        table = dynamodb.TableV2(
            self,
            table_id,
            table_name=self.naming.table_name(constants.GAP_RESPONSES_TABLE_NAME),
            partition_key=dynamodb.Attribute(
                name="userId", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="questionId", type=dynamodb.AttributeType.STRING
            ),
            billing=dynamodb.Billing.on_demand(),
            time_to_live_attribute="expiration",
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True,
                recovery_period_in_days=7,
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )
        CfnOutput(
            self, id=constants.GAP_RESPONSES_TABLE_OUTPUT, value=table.table_name
        ).override_logical_id(constants.GAP_RESPONSES_TABLE_OUTPUT)
        return table

    def _build_knowledge_table(self, id_prefix: str) -> dynamodb.TableV2:
        """Knowledge table with entity-index and 365-day TTL for retained entries."""
        table_id = f"{id_prefix}KnowledgeTable"
        table = dynamodb.TableV2(
            self,
            table_id,
            table_name=self.naming.table_name(constants.KNOWLEDGE_TABLE_NAME),
            partition_key=dynamodb.Attribute(
                name="userEmail", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="knowledgeType", type=dynamodb.AttributeType.STRING
            ),
            billing=dynamodb.Billing.on_demand(),
            time_to_live_attribute="expiration",
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True,
                recovery_period_in_days=7,
            ),
            removal_policy=RemovalPolicy.DESTROY,
            global_secondary_indexes=[
                dynamodb.GlobalSecondaryIndexPropsV2(
                    index_name="entity-index",
                    partition_key=dynamodb.Attribute(
                        name="knowledgeType", type=dynamodb.AttributeType.STRING
                    ),
                    sort_key=dynamodb.Attribute(
                        name="entityId", type=dynamodb.AttributeType.STRING
                    ),
                    projection_type=dynamodb.ProjectionType.ALL,
                ),
            ],
        )
        CfnOutput(
            self, id=constants.KNOWLEDGE_TABLE_OUTPUT, value=table.table_name
        ).override_logical_id(constants.KNOWLEDGE_TABLE_OUTPUT)
        return table

    def _build_artifacts_table(self, id_prefix: str) -> dynamodb.TableV2:
        """Generated artifact metadata table with type-index and 90-day TTL."""
        table_id = f"{id_prefix}ArtifactsTable"
        table = dynamodb.TableV2(
            self,
            table_id,
            table_name=self.naming.table_name(constants.ARTIFACTS_TABLE_NAME),
            partition_key=dynamodb.Attribute(
                name="applicationId", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="artifactId", type=dynamodb.AttributeType.STRING
            ),
            billing=dynamodb.Billing.on_demand(),
            time_to_live_attribute="expiration",
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True,
                recovery_period_in_days=7,
            ),
            removal_policy=RemovalPolicy.DESTROY,
            global_secondary_indexes=[
                dynamodb.GlobalSecondaryIndexPropsV2(
                    index_name="type-index",
                    partition_key=dynamodb.Attribute(
                        name="applicationId", type=dynamodb.AttributeType.STRING
                    ),
                    sort_key=dynamodb.Attribute(
                        name="artifactType", type=dynamodb.AttributeType.STRING
                    ),
                    projection_type=dynamodb.ProjectionType.ALL,
                ),
            ],
        )
        CfnOutput(
            self, id=constants.ARTIFACTS_TABLE_OUTPUT, value=table.table_name
        ).override_logical_id(constants.ARTIFACTS_TABLE_OUTPUT)
        return table

    def _build_company_research_cache_table(self, id_prefix: str) -> dynamodb.TableV2:
        """Company research cache table with 30-day TTL via expiresAt."""
        table_id = f"{id_prefix}CompanyResearchCacheTable"
        table = dynamodb.TableV2(
            self,
            table_id,
            table_name=self.naming.table_name(
                constants.COMPANY_RESEARCH_CACHE_TABLE_NAME
            ),
            partition_key=dynamodb.Attribute(
                name="cacheKey", type=dynamodb.AttributeType.STRING
            ),
            billing=dynamodb.Billing.on_demand(),
            time_to_live_attribute="expiresAt",
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True,
                recovery_period_in_days=7,
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )
        CfnOutput(
            self,
            id=constants.COMPANY_RESEARCH_CACHE_TABLE_OUTPUT,
            value=table.table_name,
        ).override_logical_id(constants.COMPANY_RESEARCH_CACHE_TABLE_OUTPUT)
        return table

    def _build_vpr_results_bucket(self, id_prefix: str) -> s3.Bucket:
        """
        S3 bucket for VPR generation results.
        Lifecycle: 7 days -> Delete
        """
        bucket_id = f"{id_prefix}{constants.VPR_RESULTS_BUCKET}"
        bucket = s3.Bucket(
            self,
            bucket_id,
            bucket_name=self.naming.results_bucket_name(constants.VPR_RESULTS_BUCKET),
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="delete-after-7-days",
                    expiration=Duration.days(7),
                    enabled=True,
                ),
            ],
        )
        return bucket
