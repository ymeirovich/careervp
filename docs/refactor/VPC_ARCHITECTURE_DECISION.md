# CareerVP VPC Architecture Decision

**Document Version:** 1.0
**Date:** 2026-02-10
**Decision:** NO VPC REQUIRED for CareerVP

---

## Executive Summary

**Decision:** CareerVP does NOT require VPC or private subnets.

**Rationale:** CareerVP is a **serverless Lambda architecture** that primarily uses:
- DynamoDB (no VPC required - AWS managed)
- S3 (no VPC required - AWS managed)
- Anthropic API (internet-based)
- Cognito (AWS managed, no VPC required)

---

## VPC Architecture Options

### Option 1: No VPC (RECOMMENDED for CareerVP)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAREERVP ARCHITECTURE (No VPC)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐                                                │
│   │  API GW    │  Public endpoint                              │
│   └──────┬──────┘                                               │
│          │                                                       │
│          ▼                                                       │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐      │
│   │   Lambda   │────▶│  DynamoDB  │     │     S3      │      │
│   │  Functions │     │  (AWSowned) │     │  (AWSowned) │      │
│   └─────────────┘     └─────────────┘     └─────────────┘      │
│          │                                                       │
│          ▼                                                       │
│   ┌─────────────┐     ┌─────────────┐                           │
│   │   Cognito  │     │  Anthropic  │                           │
│   │  (AWSowned)│     │    (HTTP)   │                           │
│   └─────────────┘     └─────────────┘                           │
│                                                                 │
│   ✅ No VPC needed                                              │
│   ✅ Lambda runs in AWS-managed VPC                           │
│   ✅ DynamoDB/S3 accessed via AWS backbone                     │
│   ✅ Lower complexity                                          │
│   ✅ No NAT Gateway costs                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Option 2: Full VPC with Private Subnets

```
┌─────────────────────────────────────────────────────────────────┐
│                    FULL VPC ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐ │
│   │                      VPC (10.0.0.0/16)                  │ │
│   │                                                         │ │
│   │  ┌──────────────┐         ┌──────────────┐            │ │
│   │  │   Public     │         │   Private    │  10.0.1.0/24│ │
│   │  │   Subnet     │  NAT    │   Subnet 1   │            │ │
│   │  │  10.0.0.0/24│◀───────│              │            │ │
│   │  └──────────────┘         │              │            │ │
│   │         │                 │              │            │ │
│   │         │                 └──────────────┘            │ │
│   │         │                        │                     │ │
│   │         │                 ┌──────────────┐            │ │
│   │         │                 │   Private    │  10.0.2.0/24│ │
│   │         │                 │   Subnet 2   │            │ │
│   │         │                 │              │            │ │
│   │         │                 └──────────────┘            │ │
│   │         │                        │                     │ │
│   └─────────┼────────────────────────┼─────────────────────┘ │
│             │                        │                      │
│             ▼                        │                      │
│   ┌──────────────┐                 │                      │
│   │   Internet   │                 │                      │
│   │   Gateway    │                 │                      │
│   └──────────────┘                 │                      │
│                                     │                      │
│   ┌──────────────────────────────────────────────────────┐ │
│   │                  NAT Gateway ($32-36/month)           │ │
│   │         Required for outbound internet from private    │ │
│   └──────────────────────────────────────────────────────┘ │
│                                                                 │
│   ❌ Complex to configure                                     │
│   ❌ NAT Gateway costs ($32-36/month + data processing)      │
│   ❌ Lambda cold starts slower in VPC                        │
│   ❌ Only needed if accessing RDS, ElastiCache, etc.        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Why CareerVP Doesn't Need VPC

### 1. Serverless-First Architecture

| Resource | VPC Required? | Reason |
|----------|---------------|--------|
| DynamoDB | ❌ No | AWS managed, accessed via AWS backbone |
| S3 | ❌ No | AWS managed, accessed via AWS backbone |
| Lambda | ❌ No | Runs in AWS-managed VPC by default |
| Cognito | ❌ No | AWS managed service |
| API Gateway | ❌ No | AWS managed service |
| Anthropic API | ❌ Internet | HTTP/HTTPS accessible |
| LinkedIn API | ❌ Internet | HTTP/HTTPS accessible |

### 2. No VPC-Only Resources in CareerVP

CareerVP does NOT use:
- ❌ Amazon RDS (uses DynamoDB)
- ❌ Amazon ElastiCache (uses DynamoDB DAX if needed)
- ❌ Amazon Redshift (not used)
- ❌ Private ALB/ELB (uses API Gateway)
- ❌ EC2 instances (uses Lambda)
- ❌ Containers in VPC (uses Fargate/Lambda)

### 3. Cost Analysis

| Component | No VPC | Full VPC |
|----------|--------|----------|
| NAT Gateway | $0 | $32-36/month |
| Data processing | $0 | ~$5-10/GB |
| Complexity | Low | High |
| Cold start time | ~1-2s | ~5-10s |
| Security | ✅ AWS managed | ✅ Enhanced |

---

## Security Without VPC

CareerVP achieves security through:

### 1. API Gateway + Cognito

```
┌─────────────────────────────────────────────────────────────────┐
│                   SECURITY WITHOUT VPC                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. API Gateway with Cognito Authorizer                       │
│     - JWT token validation                                     │
│     - User authentication                                     │
│     - Rate limiting                                          │
│                                                                 │
│  2. IAM Roles for Lambda                                     │
│     - Least-privilege access                                  │
│     - Scoped permissions                                     │
│     - CloudTrail audit logging                                │
│                                                                 │
│  3. Resource-Based Policies                                   │
│     - DynamoDB: Only allow authenticated access              │
│     - S3: Bucket policies + encryption                       │
│                                                                 │
│  4. VPC Security (AWS-managed)                               │
│     - Lambda runs in AWS-owned VPC                           │
│     - Network isolation by default                           │
│     - No public IPs for Lambda                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2. IAM Least Privilege Example

```yaml
# iam/lambda-execution-role.yaml

AWSTemplateFormatVersion: '2010-09-09'
Description: Lambda execution role with least privilege

Resources:
  LambdaExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

  # Scoped DynamoDB permissions
  LambdaDynamoDBPolicy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: lambda-dynamodb-policy
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Action:
              - dynamodb:GetItem
              - dynamodb:PutItem
              - dynamodb:Query
              - dynamodb:Scan
            Resource:
              - !Sub "arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/careervp-users-${Env}"
              - !Sub "arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/careervp-jobs-${Env}"
              - !Sub "arn:aws:dynamodb:${AWS::Region}:${AWS::AccountId}:table/careervp-knowledge-${Env}"

  # Scoped S3 permissions
  LambdaS3Policy:
    Type: AWS::IAM::Policy
    Properties:
      PolicyName: lambda-s3-policy
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Action:
              - s3:GetObject
              - s3:PutObject
            Resource:
              - !Sub "arn:aws:s3:::careervp-cvs-${Env}/*"
              - !Sub "arn:aws:s3:::careervp-artifacts-${Env}/*"

      # Deny public access
          - Effect: Deny
            Action: s3:*
            Resource:
              - !Sub "arn:aws:s3:::careervp-*-${Env}"
              - !Sub "arn:aws:s3:::careervp-*-${Env}/*"
            Principal: "*"
            Condition:
              Bool:
                aws:SecureTransport: false
```

---

## When VPC WOULD Be Needed

| Scenario | VPC Required? | Alternative |
|----------|---------------|------------|
| Accessing RDS database | ✅ Yes | Consider Aurora Serverless |
| Accessing ElastiCache | ✅ Yes | Consider DAX or DynamoDB |
| IP-based firewall rules | ✅ Yes | WAF on API Gateway |
| Lambda in VPC with RDS | ✅ Yes | Use RDS Proxy |
| Private ALB | ✅ Yes | Consider API Gateway |

---

## CareerVP Security Implementation

### 1. API Gateway Security

```python
# infrastructure/api_security.py

from aws_cdk import (
    Duration,
    Stack,
    aws_apigateway as apigw,
    aws_wafv2 as waf,
)
from constructs import Construct

class APISecurity(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # WAF for IP-based protection
        wafACL = waf.CfnWebACL(
            self, "CareerVPWAF",
            default_action=waf.CfnWebACL.DefaultActionProperty(
                allow=waf.CfnWebACL.AllowActionProperty()
            ),
            scope="REGIONAL",
            visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                cloud_watch_metrics_enabled=True,
                metric_name="careervp-waf",
                sampled_requests_enabled=True,
            ),
            rules=[
                # AWS managed rules
                waf.CfnWebACL.RuleProperty(
                    name="AWSManagedRulesCommonRuleSet",
                    priority=1,
                    statement=waf.CfnWebACL.StatementProperty(
                        managed_rule_group_statement=waf.CfnWebACL.ManagedRuleGroupStatementProperty(
                            vendor_name="AWS",
                            name="AWSManagedRulesCommonRuleSet",
                        )
                    ),
                    override_action=waf.CfnWebACL.OverrideActionProperty(
                        none=waf.CfnWebACL.NoneActionProperty()
                    ),
                    visibility_config=waf.CfnWebACL.VisibilityConfigProperty(
                        cloud_watch_metrics_enabled=True,
                        metric_name="common-rule",
                        sampled_requests_enabled=True,
                    ),
                ),
            ],
        )

        # Attach WAF to API
        api = apigw.RestApi(self, "CareerVPApi")
        api.add_gateway_response(
            "WAFBlockedResponse",
            type=apigw.ResponseType,
            status_code=403,
            templates={
                "application/json": '{"error": "Request blocked by WAF"}'
            },
        )
```

### 2. Lambda Security (No VPC)

```python
# infrastructure/lambda_security.py

from aws_cdk import (
    Duration,
    Stack,
    aws_lambda as lambda_,
    aws_iam as iam,
)
from constructs import Construct

class LambdaSecurity(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Lambda execution role with scoped permissions
        lambda_role = iam.Role(
            self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # Add DynamoDB permissions
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:Query",
                ],
                resources=[
                    "arn:aws:dynamodb:us-east-1:*:table/careervp-users-dev",
                    "arn:aws:dynamodb:us-east-1:*:table/careervp-jobs-dev",
                ],
            )
        )

        # Add S3 permissions
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:PutObject"],
                resources=["arn:aws:s3:::careervp-cvs-dev/*"],
            )
        )

        # Lambda function (NO VPC)
        lambda_func = lambda_.Function(
            self, "CareerVPFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset("src/backend"),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            # NO vpc_config = {} - runs in AWS-managed VPC
        )
```

---

## Summary

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| VPC | ❌ Not needed | Serverless architecture |
| Private Subnets | ❌ Not needed | No VPC-only resources |
| NAT Gateway | ❌ Not needed | Lambda doesn't need internet access |
| Security | ✅ API Gateway + WAF + IAM | Sufficient for CareerVP |
| Cost | ✅ $0 for network | No NAT Gateway costs |
| Complexity | ✅ Low | Simple architecture |

---

## Recommendation

**DO NOT implement VPC for CareerVP.**

The architecture should remain serverless-first with:
1. Lambda functions (no VPC)
2. API Gateway with Cognito authorizer
3. WAF for additional protection
4. IAM roles with least privilege
5. DynamoDB and S3 (AWS-managed)

This provides:
- ✅ Security (via authentication + authorization)
- ✅ Cost savings (no NAT Gateway)
- ✅ Performance (faster cold starts)
- ✅ Simplicity (less to manage)

---

**Document Version:** 1.0
**Last Updated:** 2026-02-10

---

**END OF VPC DECISION DOCUMENT**
