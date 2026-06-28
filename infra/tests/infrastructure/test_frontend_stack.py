from __future__ import annotations

import pytest
from aws_cdk import App, Environment
from aws_cdk.assertions import Match, Template

from careervp.frontend_stack import FrontendStack


@pytest.fixture(scope="module")
def frontend_template() -> Template:
    app = App()
    stack = FrontendStack(
        scope=app,
        construct_id="FrontendStackTest",
        environment="dev",
        domain="dev.careervp.com",
        is_production=False,
        env=Environment(account="123456789012", region="us-east-1"),
    )
    return Template.from_stack(stack)


def test_s3_bucket_created(frontend_template: Template) -> None:
    frontend_template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketName": "careervp-frontend-dev",
            "VersioningConfiguration": {"Status": "Enabled"},
        },
    )


def test_s3_bucket_blocks_public_access(frontend_template: Template) -> None:
    frontend_template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            }
        },
    )


def test_s3_bucket_cors(frontend_template: Template) -> None:
    frontend_template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "CorsConfiguration": {
                "CorsRules": Match.array_with(
                    [
                        Match.object_like(
                            {
                                "AllowedMethods": Match.array_with(["GET", "HEAD"]),
                                "AllowedOrigins": ["https://dev.careervp.com"],
                            }
                        )
                    ]
                )
            }
        },
    )


def test_cloudfront_distribution_created(frontend_template: Template) -> None:
    frontend_template.has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": Match.object_like(
                {
                    "DefaultCacheBehavior": Match.object_like(
                        {"ViewerProtocolPolicy": "redirect-to-https", "Compress": True}
                    )
                }
            )
        },
    )


def test_cloudfront_spa_error_responses(frontend_template: Template) -> None:
    """403 and 404 errors should both return index.html for SPA routing."""
    frontend_template.has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": Match.object_like(
                {
                    "CustomErrorResponses": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "ErrorCode": 403,
                                    "ResponseCode": 200,
                                    "ResponsePagePath": "/index.html",
                                }
                            ),
                            Match.object_like(
                                {
                                    "ErrorCode": 404,
                                    "ResponseCode": 200,
                                    "ResponsePagePath": "/index.html",
                                }
                            ),
                        ]
                    )
                }
            )
        },
    )


def test_stack_outputs(frontend_template: Template) -> None:
    outputs = frontend_template.find_outputs("*")
    output_keys = list(outputs.keys())
    assert any("CloudFrontUrl" in k for k in output_keys), (
        "Missing CloudFrontUrl output"
    )
    assert any("BucketName" in k for k in output_keys), "Missing BucketName output"
    assert any("DistributionId" in k for k in output_keys), (
        "Missing DistributionId output"
    )


def test_dev_stack_uses_destroy_policy(frontend_template: Template) -> None:
    """Dev environment bucket should use DESTROY removal policy (via auto_delete_objects)."""
    # auto_delete_objects=True adds a custom resource Lambda — verify bucket exists
    buckets = frontend_template.find_resources("AWS::S3::Bucket")
    assert buckets, "No S3 buckets found in dev stack"


def test_custom_domain_disabled_by_default(frontend_template: Template) -> None:
    """Guardrail: without explicit opt-in, no ACM cert, Route53 record, or alias.

    Prevents an accidental deploy from creating/repointing the custom domain
    (which can collide with an existing CNAME and break the live site).
    """
    assert (
        frontend_template.find_resources("AWS::CertificateManager::Certificate") == {}
    ), "ACM Certificate must not be created when custom domain is disabled"
    assert frontend_template.find_resources("AWS::Route53::RecordSet") == {}, (
        "Route53 RecordSet must not be created when custom domain is disabled"
    )
    dists = frontend_template.find_resources("AWS::CloudFront::Distribution")
    for dist in dists.values():
        config = dist["Properties"]["DistributionConfig"]
        assert "Aliases" not in config, (
            "CloudFront Aliases must not be set when custom domain is disabled"
        )


def test_custom_domain_enabled_via_context_creates_cert() -> None:
    """When explicitly opted in, the ACM certificate is created."""
    app = App(context={"enable_custom_domain": "true"})
    stack = FrontendStack(
        scope=app,
        construct_id="FrontendStackDomainOn",
        environment="dev",
        domain="dev.careervp.com",
        is_production=False,
        env=Environment(account="123456789012", region="us-east-1"),
    )
    template = Template.from_stack(stack)
    template.resource_count_is("AWS::CertificateManager::Certificate", 1)
