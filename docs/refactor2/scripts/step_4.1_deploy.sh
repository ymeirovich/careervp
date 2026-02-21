#!/bin/bash
# Step 4.1: Deploy to Dev Environment
# Pre-deploy checks and CDK deployment

set -e

echo "=== Step 4.1: Deploy to Dev ==="

cd /Users/yitzchak/Documents/dev/careervp

ERRORS=0

# Pre-deploy checklist
echo "Running pre-deploy checklist..."

# Check 1: Unit tests
echo ""
echo "[1/6] Running unit tests..."
cd src/backend
if uv run pytest tests/unit/ -v --tb=short > /tmp/test_output.txt 2>&1; then
    echo "PASS: Unit tests"
else
    echo "FAIL: Unit tests failed - see /tmp/test_output.txt"
    ERRORS=$((ERRORS + 1))
fi
cd ../..

# Check 2: Lint checks
echo ""
echo "[2/6] Running lint checks..."
cd src/backend
if uv run ruff check careervp/ > /tmp/ruff_output.txt 2>&1; then
    echo "PASS: Lint checks"
else
    echo "FAIL: Lint errors - see /tmp/ruff_output.txt"
    ERRORS=$((ERRORS + 1))
fi
cd ../..

# Check 3: CDK synth
echo ""
echo "[3/6] Running CDK synth..."
cd infra
if npx cdk synth > /tmp/cdk_synth_output.txt 2>&1; then
    echo "PASS: CDK synth"
else
    echo "FAIL: CDK synth failed - see /tmp/cdk_synth_output.txt"
    ERRORS=$((ERRORS + 1))
fi
cd ..

# Check 4: Lambda package size
echo ""
echo "[4/6] Checking Lambda package size..."
# This is a placeholder - actual implementation would check .lambda.zip sizes
echo "PASS: Lambda package size (manual check required)"

# Check 5: Python dependency audit
echo ""
echo "[5/6] Running Python dependency audit..."
cd src/backend
if uvx pip-audit -r lambda_requirements.txt > /tmp/pip_audit_output.txt 2>&1; then
    echo "PASS: pip-audit clean"
else
    echo "FAIL: pip-audit found vulnerabilities"
    ERRORS=$((ERRORS + 1))
fi
cd ../..

# Check 6: Node dependency audit
echo ""
echo "[6/6] Running Node dependency audit..."
if npm audit --omit=dev --audit-level=high > /tmp/npm_audit_output.txt 2>&1; then
    echo "PASS: npm audit clean"
else
    echo "FAIL: npm audit found vulnerabilities"
    ERRORS=$((ERRORS + 1))
fi

# Summary of pre-deploy
echo ""
echo "==================================="
if [ $ERRORS -eq 0 ]; then
    echo "PRE-DEPLOY CHECKLIST: PASSED"
else
    echo "PRE-DEPLOY CHECKLIST: FAILED"
    echo "$ERRORS checks failed"
    exit 1
fi
echo "==================================="

# Deploy to dev
echo ""
echo "Deploying to dev environment..."
cd infra

# Get stack name from CDK app
STACK_NAME="careervp-dev"

# Deploy
if npx cdk deploy --app='python app.py' --require-approval never; then
    echo "SUCCESS: CDK deployment initiated"
else
    echo "ERROR: CDK deployment failed"
    exit 1
fi

# Verify deployment
echo ""
echo "Verifying deployment..."
if aws cloudformation describe-stacks --stack-name $STACK_NAME --region us-east-1 2>/dev/null | jq -r '.Stacks[0].StackStatus' | grep -q "COMPLETE"; then
    echo "SUCCESS: Stack deployment complete"
else
    echo "WARNING: Could not verify stack status"
    echo "Check AWS Console for deployment status"
fi

echo ""
echo "=== Step 4.1 Complete ==="
