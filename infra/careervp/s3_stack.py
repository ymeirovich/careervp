# S3 Buckets Stack (Refactoring Phases)
# Generated from: infra/careervp/specs/s3_spec.yaml
# Uses NamingUtils for consistent naming: careervp-{env}-{purpose}-{region_code}-{hash}

import careervp.constants as constants
from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_s3 as s3,
)
from careervp.naming_utils import NamingUtils
from constructs import Construct


class S3Stack(Stack):
    """S3 buckets for CareerVP refactoring phases.

    Note: Existing buckets (cv uploads, vpr results) are in ApiDbConstruct.
    This stack adds NEW buckets needed by the refactoring phases.
    All names use NamingUtils.bucket_name() for consistency.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        naming = NamingUtils()

        # CVs bucket (Phase 4) - user CV document storage
        self.cvs_bucket = s3.Bucket(
            self,
            "CVsBucket",
            bucket_name=naming.bucket_name(constants.CV_BUCKET_NAME),
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
            cors=[
                s3.CorsRule(
                    allowed_origins=["https://careervp.com", "http://localhost:3000"],
                    allowed_methods=[
                        s3.HttpMethod.GET,
                        s3.HttpMethod.PUT,
                        s3.HttpMethod.DELETE,
                    ],
                    allowed_headers=["*"],
                )
            ],
        )

        # Generated files bucket (Phase 6) - cover letters, tailored CVs
        self.generated_bucket = s3.Bucket(
            self,
            "GeneratedBucket",
            bucket_name=naming.bucket_name(constants.GENERATED_BUCKET_NAME),
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True,
            removal_policy=RemovalPolicy.RETAIN,
            cors=[
                s3.CorsRule(
                    allowed_origins=["https://careervp.com", "http://localhost:3000"],
                    allowed_methods=[s3.HttpMethod.GET, s3.HttpMethod.PUT],
                    allowed_headers=["*"],
                )
            ],
        )
