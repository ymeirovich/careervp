#!/bin/bash
# Step 0.1.2: Upgrade Node/CDK dependencies (F-004)
# Fix Node.js and CDK vulnerabilities

set -e

echo "=== Step 0.1.2: Upgrade Node/CDK dependencies (F-004) ==="

cd /Users/yitzchak/Documents/dev/careervp

# Check package.json exists
if [ ! -f "package.json" ]; then
    echo "ERROR: package.json not found"
    exit 1
fi

# Backup package.json and package-lock.json
cp package.json package.json.bak
cp package-lock.json package-lock.json.bak 2>/dev/null || true

# Upgrade CDK dependencies
echo "Upgrading Node/CDK dependencies..."
npm update aws-cdk-lib cdk-monitoring-constructs

# Run npm audit
echo "Running npm audit..."
if npm audit --omit=dev --audit-level=high; then
    echo "SUCCESS: 0 high/critical vulnerabilities found"
else
    echo "WARNING: npm audit found vulnerabilities - review output above"
    # Don't fail as we want to see the output
fi

# Verify CDK synth still works
cd infra
echo "Verifying CDK synthesis..."
if npx cdk synth; then
    echo "SUCCESS: CDK synth completed successfully"
else
    echo "ERROR: CDK synth failed"
    cd ..
    mv package.json.bak package.json
    mv package-lock.json.bak package-lock.json 2>/dev/null || true
    exit 1
fi

# Cleanup
cd ..
rm -f package.json.bak
rm -f package-lock.json.bak 2>/dev/null || true

echo "=== Step 0.1.2 Complete ==="
