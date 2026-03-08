# CareerVP Best Practices Specifications

This directory contains machine-readable YAML specifications that define development standards for the CareerVP project. These specs combine **current codebase conventions** with **AWS Well-Architected Framework** best practices.

## Table of Contents

| Spec File | Purpose |
|-----------|---------|
| [code_quality_security_spec.yaml](./yaml/code_quality_security_spec.yaml) | Security and code quality rules |
| [prompt_optimization_spec.yaml](./yaml/prompt_optimization_spec.yaml) | Prompt engineering for AI models |
| [prompt_optimization_cdk_spec.yaml](./yaml/prompt_optimization_cdk_spec.yaml) | CDK-specific prompt optimization |
| [lambda_handler_spec.yaml](./yaml/lambda_handler_spec.yaml) | Lambda function development |
| [dynamodb_modeling_spec.yaml](./yaml/dynamodb_modeling_spec.yaml) | DynamoDB data modeling |
| [testing_spec.yaml](./yaml/testing_spec.yaml) | Testing patterns and strategies |
| [frontend_spec.yaml](./yaml/frontend_spec.yaml) | Frontend development standards |
| [cicd_spec.yaml](./yaml/cicd_spec.yaml) | CI/CD pipeline standards |

---

## Spec Overview

### code_quality_security_spec.yaml

**Purpose:** Mandatory security and code quality rules to prevent vulnerabilities.

**Key Sections:**
- Authentication & Authorization
- Input Validation
- Secret Management
- Error Handling
- Logging

**When to Reference:** Before writing any security-sensitive code.

---

### prompt_optimization_spec.yaml

**Purpose:** Guidelines for writing effective prompts for AI models.

**Key Sections:**
- Prompt structure
- Few-shot examples
- Output format specifications

**When to Reference:** When implementing AI-generated features.

---

### prompt_optimization_cdk_spec.yaml

**Purpose:** CDK-specific prompt patterns for infrastructure tasks.

**Key Sections:**
- Stack definitions
- Resource configurations
- Deployment patterns

**When to Reference:** When writing CDK infrastructure code.

---

### lambda_handler_spec.yaml

**Purpose:** Lambda function development standards combining codebase patterns with AWS best practices.

**Key Sections:**
1. **Handler Structure** - Powertools integration, routing patterns
2. **Request/Response** - Pydantic validation, response formatting
3. **Error Handling** - Exception patterns, Result mapping
4. **Authentication** - User extraction, ownership validation
5. **AWS Lambda Optimization** - Memory, timeout, cold start, idempotency
6. **Observability** - Structured logging, metrics, tracing
7. **CORS** - Origin validation, preflight handling

**Codebase Source:** Patterns from `handlers/auth_handler.py`, `handlers/vpr_handler.py`

**AWS WAF Augmentation:**
- Cold start optimization (provisioned concurrency)
- Idempotency requirements
- Memory/timeout recommendations

---

### dynamodb_modeling_spec.yaml

**Purpose:** DynamoDB data modeling standards.

**Key Sections:**
1. **Table Design** - Single table pattern, naming conventions
2. **Key Schema** - PK/SK patterns, prefix conventions
3. **GSI Design** - Index naming, projections
4. **Access Patterns** - Query over Scan, pagination
5. **Item Design** - Entity types, version tracking
6. **TTL** - Automatic expiration
7. **Capacity** - On-demand vs provisioned
8. **Security** - Encryption, IAM access
9. **Backup/Recovery** - PITR, on-demand backups

**Codebase Source:** Patterns from `dal/dynamo_dal_handler.py`, `dal/jobs_repository.py`

**AWS WAF Augmentation:**
- GSI projection optimization
- VPC endpoint recommendations
- Point-in-time recovery

---

### testing_spec.yaml

**Purpose:** Testing patterns and CI/CD integration.

**Key Sections:**
1. **Test Organization** - Directory structure, naming
2. **Unit Tests** - Isolation, mocking, environment
3. **Integration Tests** - Component boundaries, event fixtures
4. **E2E Tests** - Real environment, markers
5. **AWS Mocking** - Boto3 clients, async support
6. **Fixtures** - Scoping, conftest patterns
7. **TDD Patterns** - RED phase, assertions
8. **CI/CD Integration** - Coverage, parallel execution
9. **Contract Testing** - API validation
10. **Chaos Engineering** - Failure injection

**Codebase Source:** Patterns from `tests/` directory structure

**AWS WAF Augmentation:**
- Test isolation best practices
- Contract testing
- Chaos testing patterns

---

### frontend_spec.yaml

**Purpose:** Frontend development standards (design-agnostic).

**Key Sections:**
1. **Project Structure** - Feature-based organization
2. **TypeScript** - Strict mode, type definitions
3. **API Client** - Centralized calls, auth headers, error handling
4. **State Management** - Server vs client state, React Query
5. **Components** - Structure, composition, custom hooks
6. **Security** - XSS prevention, security headers, token storage
7. **Performance** - Code splitting, CDN, caching
8. **Error Handling** - Boundaries, reporting, fallbacks
9. **Accessibility** - Semantic HTML, keyboard navigation
10. **Testing** - Pyramid, unit, E2E
11. **Internationalization** - i18n setup, string externalization

**Note:** This spec focuses on architecture and patterns, not visual design.

**AWS WAF Augmentation:**
- CDN integration
- Security headers
- CloudFront/RUM integration

---

### cicd_spec.yaml

**Purpose:** CI/CD pipeline standards.

**Key Sections:**
1. **Pipeline Structure** - Stages, parallel execution
2. **Source Control** - PR requirements, branch strategy
3. **Build Process** - Caching, artifacts, reproducible builds
4. **Testing in CI** - Unit tests, static analysis, security scans
5. **Security** - Secrets management, least privilege, build isolation
6. **Deployment** - Environments, blue/green, rollback
7. **IaC** - CDK synth, diff review, drift detection
8. **Monitoring** - Notifications, metrics
9. **Versioning** - Semantic versioning, git tags
10. **Compliance** - Audit logging, compliance scans

**AWS WAF Augmentation:**
- IAM least privilege for CI/CD
- Blue/green deployments
- Drift detection

---

## How to Use These Specs

### 1. Development
Reference these specs when:
- Creating new Lambda handlers
- Designing DynamoDB tables
- Writing tests
- Building frontend features
- Configuring CI/CD pipelines

### 2. Code Review
Use specs to verify:
- Security requirements are met
- Best practices are followed
- AWS Well-Architected principles are applied

### 3. Automation
These specs are machine-readable and can be used for:
- Linter rules
- Code generation templates
- Compliance checking
- Onboarding documentation

---

## Spec Format

Each spec follows a consistent YAML structure:

```yaml
spec_version: "1.0"
date: "YYYY-MM-DD"
purpose: "Description of the spec"
enforcement: "How to enforce"

section_name:
  section: "Human-readable section name"
  rule_id:
    id: "UNIQUE_RULE_ID"
    name: "Rule name"
    severity: "required|recommended|critical"
    description: "What the rule requires"
    status: "required|recommended"
    codebase_example: "Example from codebase"
    aws_waf_note: "AWS best practice context"
```

---

## Severity Levels

| Level | Meaning |
|-------|---------|
| **required** | Must follow - enforced in code review |
| **recommended** | Should follow - improves quality |
| **critical** | Must follow - security/safety critical |

---

## Updating Specs

When updating specs:
1. Update the `date` field
2. Increment `spec_version` if making breaking changes
3. Document rationale for changes
4. Run analysis to check for new non-compliance

---

## Related Documents

- [CLAUDE.md](../CLAUDE.md) - Project context and decisions
- [docs/architecture/](docs/architecture/) - System architecture
