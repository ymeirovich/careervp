This prompt is optimized for a Junior Codex developer to ensure the multi-environment subdomain configuration aligns with CareerVP's architectural and security standards.

---

**Directives**
@spec `prompt_optimization_spec.yaml`
@spec `prompt_optimization_cdk_spec.yaml`
@spec `code_quality_security_spec.yaml`
@pattern `src/backend/careervp/handlers/*_handler.py`

**Role**
You are acting as a Senior AWS and Software Architect handing off an infrastructure-as-code task to a Junior Codex Developer. Your goal is to provision and map custom subdomains for both the Development and Staging environments using the AWS CDK.

**Problem**
Internal teams are currently forced to use raw AWS execute-api URLs (`4xe2tdq8z6` for Dev and `1aj6084o45` for Stage). This creates friction in frontend configuration, lacks brand consistency, and bypasses our intended regional SSL/TLS termination standards.

**Solution**
Update the CDK stack to implement `apigateway.DomainName` and `apigateway.BasePathMapping` for two environments:

1. **Dev:** `dev.careervp.com` mapping to API Gateway `4xe2tdq8z6` (Stage: `prod`).
2. **Stage:** `stage.careervp.com` mapping to API Gateway `1aj6084o45` (Stage: `prod`).

**Think**

1. **Context Awareness**: Determine if these APIs are defined within the same CDK app or if you need to use `RestApi.from_rest_api_id` to reference them.
2. **Certificate Strategy**: Locate the ACM certificates for `*.careervp.com` or specific subdomains. These must reside in `us-east-1`.
3. **Endpoint Logic**: Per `prompt_optimization_cdk_spec.yaml`, we must use `REGIONAL` endpoints to maintain consistency with our latency and routing requirements.
4. **Logical IDs**: Plan unique logical IDs for each `DomainName` and `Mapping` resource to avoid `ConflictException` during deployment.
5. **Security Validation**: Cross-reference `code_quality_security_spec.yaml` to ensure any handlers touched during this infrastructure update strictly use `@require_auth`.

**Then**

1. **Reference APIs**: Import or reference the two gateways using their IDs: `4xe2tdq8z6` and `1aj6084o45`.
2. **Define Custom Domains**: Create `apigateway.DomainName` constructs for `dev.careervp.com` and `stage.careervp.com`.
3. **Configure TLS**: Set the security policy to `TLS_1_2` for both domains.
4. **Map Stages**: Use `BasePathMapping` to connect both domains to their respective `/prod` stages. Ensure the `base_path` is empty so the subdomain maps directly to the API root.
5. **Regional Setup**: Explicitly set `endpoint_type=apigateway.EndpointType.REGIONAL`.
6. **Outputs**: Export the regional domain names (the `.cloudfront.net` or `.execute-api.` targets provided by the Custom Domain construct) for DNS configuration in Cloudflare.

**Constraints**

* **MUST** use `TLS_1_2`.
* **MUST** use `REGIONAL` endpoint types (Rule `APIGW_004`).
* **DO NOT** include `/prod` in the CNAME target; the mapping handles the path routing.
* **MUST** derive `user_id` from the authorizer context in any associated handler code, never the payload.

**Prohibited**

* **Avoid** `ConflictException`: Do not reuse logical IDs between the dev and stage domain constructs.
* **No** hardcoded ARNs for certificates; use `acm.Certificate.from_certificate_arn` or lookups.
* **No** use of Edge-optimized endpoints.

**Output**

* **Modify**: `infra/careervp_stack.py` (or the specific infrastructure module managing API Gateway).
* **Verify**: Ensure `@require_auth` is present in `src/backend/careervp/handlers/`.

**Verify**

1. Run `npx cdk synth` to validate the CloudFormation template structure.
2. Run `npx cdk diff` to ensure no accidental resource deletions occur.
3. Verify that `dev.careervp.com` and `stage.careervp.com` appear in the `Outputs` section.
4. Run `pytest tests/unit/test_auth.py` to ensure security decorators remain functional.
