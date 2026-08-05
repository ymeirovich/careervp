from typing import Any

from aws_cdk import Aws, CfnOutput, RemovalPolicy
from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_wafv2 as waf
from constructs import Construct

from .naming_utils import NamingUtils

_RATE_LIMITS_BY_ENVIRONMENT = {
    "dev": 2_000,
    "staging": 1_500,
    "prod": 1_000,
}
_DEFAULT_RATE_LIMIT = 1_000

# Environments whose CV-upload route must accept a real CV file.
#
# AWSManagedRulesCommonRuleSet's SizeRestrictions_BODY BLOCKs any request body
# over 8,192 bytes. `POST /users/me/cv` carries the CV base64-encoded inside a
# JSON body (the frontend uses FileReader.readAsDataURL), and base64 inflates by
# 4/3, so the effective ceiling was a ~6 KB file. A one-page docx is 40 KB.
#
# Measured on devx 2026-08-05: an 8,120-byte body reached the handler, an
# 8,520-byte body was refused with 403. WAF logs name the rule outright:
#   {"action":"BLOCK","terminatingRule":{"ruleId":"SizeRestrictions_BODY"}}
# That is why every object ever written to the CV bucket is a sub-kilobyte .txt:
# no real CV file has ever been able to reach the parser.
#
# Two changes, deliberately paired:
#   1. SizeRestrictions_BODY -> Count, so body size no longer terminates.
#   2. Body inspection limit 8 KB -> 64 KB, so the *content* rules
#      (CrossSiteScripting_BODY, GenericRFI_BODY, GenericLFI_BODY,
#      EC2MetaDataSSRF_BODY) actually examine a realistic upload instead of its
#      first 8 KB. Without (2), (1) would let large bodies through
#      under-inspected; with it, coverage is wider than before this change.
#
# Scoped to devx on purpose: dev and staging are out of scope for wave 3 and
# must not change behaviour when they are next deployed.
_LARGE_BODY_ENVIRONMENTS = frozenset({"devx"})


class WafToApiGatewayConstruct(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        api: apigateway.RestApi,
        naming: NamingUtils,
        feature: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(scope, id, **kwargs)
        self.naming = naming
        self.feature = feature
        web_acl_name = naming.resource_name(feature, "waf")
        metric_name = web_acl_name.replace("-", "")

        allow_large_bodies = naming.environment in _LARGE_BODY_ENVIRONMENTS
        common_rule_set_overrides = (
            [
                waf.CfnWebACL.RuleActionOverrideProperty(
                    name="SizeRestrictions_BODY",
                    action_to_use=waf.CfnWebACL.RuleActionProperty(count={}),
                )
            ]
            if allow_large_bodies
            else None
        )
        association_config = (
            waf.CfnWebACL.AssociationConfigProperty(
                request_body={
                    "API_GATEWAY": waf.CfnWebACL.RequestBodyAssociatedResourceTypeConfigProperty(
                        default_size_inspection_limit="KB_64",
                    )
                }
            )
            if allow_large_bodies
            else None
        )

        # Create WAF WebACL with AWS Managed Rules
        web_acl = waf.CfnWebACL(
            self,
            "ProductApiGatewayWebAcl",
            scope="REGIONAL",  # Change to CLOUDFRONT if you're using edge-optimized API
            default_action=waf.CfnWebACL.DefaultActionProperty(allow={}),
            name=web_acl_name,
            association_config=association_config,
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                sampled_requests_enabled=True,
                cloud_watch_metrics_enabled=True,
                metric_name=metric_name,
            ),
            rules=[
                waf.CfnWebACL.RuleProperty(
                    name="Product-AWSManagedRulesCommonRuleSet",
                    priority=0,
                    override_action={"none": {}},
                    statement=waf.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                            name="AWSManagedRulesCommonRuleSet",
                            vendor_name="AWS",
                            rule_action_overrides=common_rule_set_overrides,
                        )
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="Product-AWSManagedRulesCommonRuleSet",
                    ),
                ),
                # Block Amazon IP reputation list managed rule group
                waf.CfnWebACL.RuleProperty(
                    name="Product-AWSManagedRulesAmazonIpReputationList",
                    priority=1,
                    override_action={"none": {}},
                    statement=waf.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                            name="AWSManagedRulesAmazonIpReputationList",
                            vendor_name="AWS",
                        )
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="Product-AWSManagedRulesAmazonIpReputationList",
                    ),
                ),
                # Block Anonymous IP list managed rule group
                waf.CfnWebACL.RuleProperty(
                    name="Product-AWSManagedRulesAnonymousIpList",
                    priority=2,
                    override_action={"none": {}},
                    statement=waf.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                            name="AWSManagedRulesAnonymousIpList", vendor_name="AWS"
                        )
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="Product-AWSManagedRulesAnonymousIpList",
                    ),
                ),
                # rule for blocking known Bad Inputs
                waf.CfnWebACL.RuleProperty(
                    name="Product-AWSManagedRulesKnownBadInputsRuleSet",
                    priority=3,
                    override_action={"none": {}},
                    statement=waf.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                            name="AWSManagedRulesKnownBadInputsRuleSet",
                            vendor_name="AWS",
                        )
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="Product-AWSManagedRulesKnownBadInputsRuleSet",
                    ),
                ),
                waf.CfnWebACL.RuleProperty(
                    name=f"careervp-api-rate-limit-{naming.environment}",
                    priority=4,
                    action=waf.CfnWebACL.RuleActionProperty(block={}),
                    statement=waf.CfnWebACL.StatementProperty(
                        rate_based_statement=waf.CfnWebACL.RateBasedStatementProperty(
                            aggregate_key_type="IP",
                            limit=_RATE_LIMITS_BY_ENVIRONMENT.get(
                                naming.environment,
                                _DEFAULT_RATE_LIMIT,
                            ),
                        )
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name=f"careervp-api-rate-limit-{naming.environment}",
                    ),
                ),
            ],
        )

        # Associate WAF with API Gateway
        waf.CfnWebACLAssociation(
            self,
            "ApiGatewayWafAssociation",
            resource_arn=api.deployment_stage.stage_arn,
            web_acl_arn=web_acl.attr_arn,
        )

        # Enable logging for WAF, must start with 'aws-waf-logs-' prefix
        log_group_name = f"aws-waf-logs-{web_acl_name}"
        # Create CloudWatch Log Group for WAF logging
        waf_log_group = logs.LogGroup(
            self,
            "WafLogGroup",
            log_group_name=log_group_name,
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Attach resource policy to allow WAF to write to the log group
        waf_log_group.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.AnyPrincipal()],
                actions=[
                    "logs:PutLogEvents",
                    "logs:CreateLogStream",
                    "logs:DescribeLogGroups",
                ],
                resources=[f"{waf_log_group.log_group_arn}:*"],
            )
        )

        # Output the Log Group ARN for visibility
        CfnOutput(
            self, id="WafLogGroupArn", value=waf_log_group.log_group_arn
        ).override_logical_id("WafLogGroupArn")

        # Construct the Log Group ARN manually as its not available in the CDK
        log_group_arn = f"arn:{Aws.PARTITION}:logs:{Aws.REGION}:{Aws.ACCOUNT_ID}:log-group:{log_group_name}:*"

        enable_waf_logging = waf.CfnLoggingConfiguration(
            self,
            "WafLoggingConfiguration",
            resource_arn=web_acl.attr_arn,
            log_destination_configs=[log_group_arn],
        )

        web_acl.node.add_dependency(waf_log_group)
        enable_waf_logging.node.add_dependency(
            web_acl
        )  # Ensure WebACL is created first
