# P-23 Lambda Canary and Revert Runbook

## Scope

P-23 protects Lambda code and configuration deployments for public/API-route
functions. It does not change the live API Gateway Cognito authorizer and does
not instantiate the dormant P-24 custom authorizer.

## Pre-deploy check

1. The human reviews the prepared CloudFormation change set and its replacement
   report. Do not deploy from automation.
2. Confirm the relevant Lambda alias has a CodeDeploy deployment group using
   `CodeDeployDefault.LambdaCanary10Percent5Minutes` and its error plus resolver
   outcome alarms are enabled.
3. Run the P-24 synthetic resolver canary: the known `sub` must resolve to the
   expected internal `user_id`.

## Revert lever 1 — Lambda code or Lambda configuration

For a failed Lambda code/configuration deployment, use **CodeDeploy alias rollback**.
The deployment group's alarm rollback returns the stable Lambda
alias to its prior published version; a human can also stop the deployment with
rollback enabled. Verify the alias version and the API route after rollback.

## Revert lever 2 — API Gateway authorizer or method configuration

For an API Gateway authorizer, authorizationType, method, or integration
configuration change, use a **stage-level API Gateway redeploy** to restore the
previous API Gateway deployment/stage configuration. This is **not a Lambda-alias canary**:
CodeDeploy cannot roll back API Gateway control-plane
configuration.

## Fire-drill record

Record the change-set identifier, affected alias/deployment group, alarm state,
the known-sub resolver result, and the post-revert route check in the P-29
evidence pack.
