"""
infrastructure/token_tracking_tables.py
CloudFormation / SAM additions for token tracking.

Add to your existing agents-stack.yaml or deploy as a separate stack.
"""

# ============================================================================
# CLOUDFORMATION YAML  (paste into your agents-stack.yaml Resources section)
# ============================================================================

CLOUDFORMATION_YAML = """
  # ── Token Usage Table ──────────────────────────────────────────────────────
  # One record per agent API call. SK allows multiple calls per agent per app.
  # TTL set to 90 days to control storage costs.
  TokenUsageTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: careervp-token-usage
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: application_id
          AttributeType: S
        - AttributeName: sk                     # {timestamp_ms}#{agent_name}
          AttributeType: S
        - AttributeName: user_id
          AttributeType: S
        - AttributeName: agent_name
          AttributeType: S
      KeySchema:
        - AttributeName: application_id
          KeyType: HASH
        - AttributeName: sk
          KeyType: RANGE
      GlobalSecondaryIndexes:
        # Query all calls for a user across all applications
        - IndexName: user-id-index
          KeySchema:
            - AttributeName: user_id
              KeyType: HASH
            - AttributeName: sk
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
        # Query all calls for a specific agent (cost-per-agent analysis)
        - IndexName: agent-name-index
          KeySchema:
            - AttributeName: agent_name
              KeyType: HASH
            - AttributeName: sk
              KeyType: RANGE
          Projection:
            ProjectionType: ALL
      TimeToLiveSpecification:
        AttributeName: ttl_epoch
        Enabled: true
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      Tags:
        - Key: Project
          Value: CareerVP
        - Key: Purpose
          Value: TokenTracking

  # ── Daily Cost Rollup Table ────────────────────────────────────────────────
  # Aggregated daily summaries per agent — powers the cost dashboard.
  # Updated by the DailyRollupFunction (triggered by EventBridge).
  DailyCostRollupTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: careervp-daily-cost-rollup
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: date_agent             # e.g. "2026-02-24#vpr-strategist"
          AttributeType: S
        - AttributeName: model
          AttributeType: S
      KeySchema:
        - AttributeName: date_agent
          KeyType: HASH
        - AttributeName: model
          KeyType: RANGE
      Tags:
        - Key: Project
          Value: CareerVP

  # ── Lambda Layer ───────────────────────────────────────────────────────────
  TokenTrackerLayer:
    Type: AWS::Serverless::LayerVersion
    Properties:
      LayerName: careervp-token-tracker
      Description: Shared token tracking utility for all CareerVP agents
      ContentUri: lambda_layer/
      CompatibleRuntimes:
        - python3.11
      RetentionPolicy: Retain

  # ── Daily Rollup Lambda ────────────────────────────────────────────────────
  DailyRollupFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: careervp-daily-cost-rollup
      CodeUri: functions/daily_rollup/
      Handler: lambda_function.lambda_handler
      Runtime: python3.11
      Timeout: 300
      MemorySize: 512
      Environment:
        Variables:
          TOKEN_USAGE_TABLE: !Ref TokenUsageTable
          DAILY_ROLLUP_TABLE: !Ref DailyCostRollupTable
          ALERT_TOPIC_ARN: !Ref CostAlertTopic
      Events:
        DailyTrigger:
          Type: Schedule
          Properties:
            Schedule: cron(0 1 * * ? *)    # 01:00 UTC daily
            Description: Aggregate previous day token usage
      Policies:
        - DynamoDBReadPolicy:
            TableName: !Ref TokenUsageTable
        - DynamoDBWritePolicy:
            TableName: !Ref DailyCostRollupTable
        - SNSPublishMessagePolicy:
            TopicName: !GetAtt CostAlertTopic.TopicName

  # ── Cost Alert Topic ───────────────────────────────────────────────────────
  CostAlertTopic:
    Type: AWS::SNS::Topic
    Properties:
      TopicName: careervp-cost-alerts
      Subscription:
        - Protocol: email
          Endpoint: !Ref AlertEmail    # pass as parameter

  # ── CloudWatch Alarms ──────────────────────────────────────────────────────
  # Alarm: VPR cost spike (triggers if any single VPR call > $1.00)
  VPRCostSpikeAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: CareerVP-VPR-CostSpike
      AlarmDescription: VPR agent single-call cost exceeds $1.00 (1000 milli-USD)
      Namespace: CareerVP/TokenUsage
      MetricName: CostMilliUSD
      Dimensions:
        - Name: AgentName
          Value: vpr-strategist
      Statistic: Maximum
      Period: 300          # 5 minutes
      EvaluationPeriods: 1
      Threshold: 1000      # $1.00 in milli-USD
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref CostAlertTopic

  # Alarm: Daily total tokens across all agents > 10M (budget guard)
  DailyTokenBudgetAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: CareerVP-DailyTokenBudget
      AlarmDescription: Daily token usage exceeds 10M tokens
      Namespace: CareerVP/TokenUsage
      MetricName: TotalTokens
      Statistic: Sum
      Period: 86400        # 24 hours
      EvaluationPeriods: 1
      Threshold: 10000000
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref CostAlertTopic

  # ── IAM additions for existing agent Lambdas ──────────────────────────────
  # Add this policy to every agent Lambda's role:
  AgentTokenTrackingPolicy:
    Type: AWS::IAM::ManagedPolicy
    Properties:
      ManagedPolicyName: careervp-agent-token-tracking
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Action:
              - dynamodb:PutItem
            Resource: !GetAtt TokenUsageTable.Arn
          - Effect: Allow
            Action:
              - cloudwatch:PutMetricData
            Resource: '*'
            Condition:
              StringEquals:
                cloudwatch:namespace: CareerVP/TokenUsage

Parameters:
  AlertEmail:
    Type: String
    Description: Email address for cost alerts

Outputs:
  TokenUsageTableArn:
    Value: !GetAtt TokenUsageTable.Arn
    Export:
      Name: CareerVP-TokenUsageTable-Arn

  TokenTrackerLayerArn:
    Value: !Ref TokenTrackerLayer
    Export:
      Name: CareerVP-TokenTrackerLayer-Arn
"""

# ============================================================================
# ENVIRONMENT VARIABLE ADDITIONS  (add to every agent Lambda)
# ============================================================================

AGENT_ENV_VARS = """
# Add to every agent Lambda's Environment.Variables in your SAM template:

  TOKEN_USAGE_TABLE: !Ref TokenUsageTable
  DAILY_ROLLUP_TABLE: !Ref DailyCostRollupTable

# Add the shared layer to every agent Lambda:
  Layers:
    - !Ref TokenTrackerLayer
"""
