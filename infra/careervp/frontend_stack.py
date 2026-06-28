"""Frontend CDK Stack: CloudFront + S3 + ACM + Route53."""

from __future__ import annotations

import os
from typing import Any

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_route53 as route53
from aws_cdk import aws_route53_targets as targets
from aws_cdk import aws_s3 as s3
from constructs import Construct


class FrontendStack(Stack):
    """CloudFront + S3 static hosting for the CareerVP Next.js frontend."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str = "dev",
        domain: str = "dev.careervp.com",
        is_production: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._env_name = environment
        self.domain = domain
        removal_policy = (
            RemovalPolicy.RETAIN if is_production else RemovalPolicy.DESTROY
        )

        # S3 bucket for static assets
        self.bucket = s3.Bucket(
            self,
            "FrontendBucket",
            bucket_name=f"careervp-frontend-{self._env_name}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            removal_policy=removal_policy,
            auto_delete_objects=not is_production,
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.HEAD],
                    allowed_origins=[f"https://{domain}"],
                    allowed_headers=["*"],
                    max_age=3600,
                )
            ],
        )

        # Origin Access Control for CloudFront → S3
        self.oac = cloudfront.S3OriginAccessControl(
            self,
            "OAC",
            description=f"OAC for careervp-frontend-{self._env_name}",
        )

        s3_origin = origins.S3BucketOrigin.with_origin_access_control(
            self.bucket,
            origin_access_control=self.oac,
        )

        # Custom-domain wiring (ACM certificate + CloudFront alias + Route53 record)
        # is GATED behind an explicit opt-in flag and defaults to OFF. This prevents
        # an unrelated `cdk deploy` from accidentally creating an ACM cert, attaching
        # a CloudFront alias, or writing a Route53 A-alias record — the last of which
        # can collide with / repoint an existing `{domain}` CNAME and break the live
        # site. Enable deliberately via `-c enable_custom_domain=true` or
        # ENABLE_CUSTOM_DOMAIN=true when you actually intend to manage the domain.
        self.enable_custom_domain = self._resolve_enable_custom_domain()

        # ACM certificate (must be us-east-1 for CloudFront)
        # Skip certificate if no hosted zone is configured (dev/testing)
        cert_env = self._resolve_cert_env()
        has_hosted_zone = bool(os.environ.get("HOSTED_ZONE_NAME", "careervp.com"))
        self.certificate = (
            acm.Certificate(
                self,
                "Certificate",
                domain_name="careervp.com",
                subject_alternative_names=["*.careervp.com"],
                validation=acm.CertificateValidation.from_dns(),
                certificate_name=f"careervp-cert-{self._env_name}",
            )
            if cert_env and has_hosted_zone and self.enable_custom_domain
            else None
        )

        # CloudFront distribution
        distribution_kwargs: dict[str, Any] = {
            "default_behavior": cloudfront.BehaviorOptions(
                origin=s3_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True,
            ),
            "error_responses": [
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
            ],
            "comment": f"careervp-cf-{self._env_name}",
        }

        if self.certificate:
            distribution_kwargs["domain_names"] = [domain]
            distribution_kwargs["certificate"] = self.certificate

        self.distribution = cloudfront.Distribution(
            self,
            "Distribution",
            **distribution_kwargs,
        )

        # Route53 alias record (only when custom domain is explicitly enabled AND a
        # hosted zone name is configured). Gating on enable_custom_domain prevents an
        # accidental A-alias write that could collide with an existing {domain} CNAME.
        hosted_zone_name = os.environ.get("HOSTED_ZONE_NAME", "careervp.com")
        self.record: route53.ARecord | None = None
        if not self.enable_custom_domain:
            hosted_zone_name = ""
        try:
            if not hosted_zone_name:
                raise RuntimeError("custom domain disabled; skip Route53 record")
            hosted_zone = route53.HostedZone.from_lookup(
                self,
                "HostedZone",
                domain_name=hosted_zone_name,
            )
            subdomain = domain.split(".")[0] if domain != hosted_zone_name else ""
            self.record = route53.ARecord(
                self,
                "AliasRecord",
                zone=hosted_zone,
                record_name=subdomain or None,
                target=route53.RecordTarget.from_alias(
                    targets.CloudFrontTarget(self.distribution)
                ),
            )
        except Exception:
            # Hosted zone lookup fails in env-agnostic synth; skip record creation.
            pass

        # Stack outputs
        CfnOutput(
            self, "CloudFrontUrl", value=self.distribution.distribution_domain_name
        )
        CfnOutput(self, "BucketName", value=self.bucket.bucket_name)
        CfnOutput(self, "DistributionId", value=self.distribution.distribution_id)

    def _resolve_cert_env(self) -> bool:
        """Return True only when running in a real AWS environment."""
        account = self.account
        region = self.region
        return bool(account and account != "unknown" and region == "us-east-1")

    def _resolve_enable_custom_domain(self) -> bool:
        """Opt-in gate for custom-domain resources. Defaults to disabled.

        Resolution order: CDK context `enable_custom_domain` > env
        `ENABLE_CUSTOM_DOMAIN`. Any of {"true", "1", "yes"} (case-insensitive)
        enables it. Anything else (including unset) leaves it disabled so an
        accidental deploy never creates an ACM cert, CloudFront alias, or Route53
        record for the domain.
        """
        ctx = self.node.try_get_context("enable_custom_domain")
        raw = ctx if ctx is not None else os.environ.get("ENABLE_CUSTOM_DOMAIN", "")
        return str(raw).strip().lower() in ("true", "1", "yes")
