# Task: CICD Pipeline Setup

**Status:** Not Started
**Spec Reference:** [[docs/specs/99-gap-remediation.md#GAP-03]]
**Priority:** P0 - Required before deployment

## Overview

Create GitHub Actions workflows for PR validation and deployment. This enables automated testing, linting, and deployment to AWS environments.

## Todo

### PR Validation Workflow (`.github/workflows/pr-validation.yml`)

- [ ] Create workflow file
- [ ] Add lint job (ruff check + ruff format --check)
- [ ] Add typecheck job (mypy --strict)
- [ ] Add test job (pytest tests/unit/)
- [ ] Add cdk-synth job (verify infrastructure compiles)

### Deployment Workflow (`.github/workflows/deploy.yml`)

- [ ] Create workflow file
- [ ] Add dev deployment on main push
- [ ] Add staging deployment with manual approval
- [ ] Add prod deployment with manual approval
- [ ] Configure AWS credentials via GitHub secrets

### CDK Diff Workflow (`.github/workflows/cdk-diff.yml`)

- [ ] Create workflow file
- [ ] Run cdk diff on PRs
- [ ] Comment diff output on PR

### Pre-commit Hook Update (`.pre-commit-config.yaml`)

- [ ] Add pytest hook for unit tests

### GitHub Secrets Required

| Secret | Description |
| ------ | ----------- |
| `AWS_ACCESS_KEY_ID` | AWS credentials for deployment |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials for deployment |
| `ANTHROPIC_API_KEY` | Claude API key (optional, for integration tests) |

### Commit

- [ ] Commit with message: `ci: add GitHub Actions workflows for PR validation and deployment`

---

## Codex Implementation Guide

### File Paths

| File | Purpose |
| ---- | ------- |
| `.github/workflows/pr-validation.yml` | PR checks |
| `.github/workflows/deploy.yml` | Deployment workflow |
| `.github/workflows/cdk-diff.yml` | CDK diff on PR |

### PR Validation Workflow

```yaml
name: PR Validation

on:
  pull_request:
    branches: [main, develop]
    paths:
      - 'src/backend/**'
      - 'infra/**'
      - '.github/workflows/**'

env:
  PYTHON_VERSION: '3.14'

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: cd src/backend && uv sync

      - name: Check formatting
        run: cd src/backend && uv run ruff format --check .

      - name: Check linting
        run: cd src/backend && uv run ruff check .

  typecheck:
    name: Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: cd src/backend && uv sync

      - name: Run mypy
        run: cd src/backend && uv run mypy careervp --strict

  test:
    name: Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: cd src/backend && uv sync

      - name: Run tests
        run: cd src/backend && uv run pytest tests/unit/ -v --tb=short

      - name: Run tests with coverage
        run: |
          cd src/backend
          uv run pytest tests/unit/ --cov=careervp --cov-report=xml --cov-report=term-missing

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: src/backend/coverage.xml
          fail_ci_if_error: false

  cdk-synth:
    name: CDK Synth
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install CDK
        run: npm install -g aws-cdk

      - name: Install infra dependencies
        run: cd infra && uv sync

      - name: Build backend
        run: cd src/backend && uv sync && mkdir -p .build/lambdas

      - name: Synth CDK
        run: cd infra && cdk synth
```

### Deployment Workflow

```yaml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        default: 'dev'
        type: choice
        options:
          - dev
          - staging
          - prod

env:
  PYTHON_VERSION: '3.14'

jobs:
  # Run all validation first
  validate:
    uses: ./.github/workflows/pr-validation.yml

  deploy-dev:
    name: Deploy to Dev
    needs: validate
    runs-on: ubuntu-latest
    environment: dev
    if: github.ref == 'refs/heads/main' || github.event.inputs.environment == 'dev'
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install CDK
        run: npm install -g aws-cdk

      - name: Install and build backend
        run: |
          cd src/backend
          uv sync
          uv build

      - name: Install infra dependencies
        run: cd infra && uv sync

      - name: Deploy
        run: cd infra && cdk deploy --require-approval never
        env:
          ENVIRONMENT: dev

  deploy-staging:
    name: Deploy to Staging
    needs: deploy-dev
    runs-on: ubuntu-latest
    environment: staging
    if: github.event.inputs.environment == 'staging'
    steps:
      # ... similar to deploy-dev

  deploy-prod:
    name: Deploy to Production
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    if: github.event.inputs.environment == 'prod'
    steps:
      # ... similar to deploy-dev with extra safety checks
```

### CDK Diff Workflow

```yaml
name: CDK Diff

on:
  pull_request:
    branches: [main]
    paths:
      - 'infra/**'
      - 'src/backend/**'

jobs:
  cdk-diff:
    name: CDK Diff
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install CDK
        run: npm install -g aws-cdk

      - name: Build backend
        run: cd src/backend && uv sync && mkdir -p .build/lambdas

      - name: Install infra dependencies
        run: cd infra && uv sync

      - name: CDK Diff
        id: diff
        run: |
          cd infra
          cdk diff 2>&1 | tee diff_output.txt
          echo "diff<<EOF" >> $GITHUB_OUTPUT
          cat diff_output.txt >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT

      - name: Comment PR
        uses: actions/github-script@v7
        with:
          script: |
            const diff = `${{ steps.diff.outputs.diff }}`;
            const body = `## CDK Diff\n\n\`\`\`\n${diff}\n\`\`\``;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });
```

### Verification

```bash
# Validate workflow syntax (requires act CLI)
act -l

# Or validate manually by creating a test PR
```

### Commit Instructions

```bash
cd /Users/yitzchak/Documents/dev/careervp
mkdir -p .github/workflows
git add .github/workflows/
git commit -m "ci: add GitHub Actions workflows for PR validation and deployment

- Add pr-validation.yml with lint, typecheck, test, cdk-synth jobs
- Add deploy.yml with dev/staging/prod environments
- Add cdk-diff.yml to comment infrastructure changes on PRs
- Configure CodeCov integration for test coverage

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Acceptance Criteria

- [ ] PR validation runs on all PRs to main/develop
- [ ] Lint, typecheck, test, and cdk-synth jobs all pass
- [ ] Deployment workflow deploys to dev on main push
- [ ] CDK diff comments infrastructure changes on PRs
- [ ] Required GitHub secrets documented
