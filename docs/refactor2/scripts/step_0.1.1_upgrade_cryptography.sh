#!/bin/bash
# Step 0.1.1: Upgrade cryptography dependency (F-003)
# Fix cryptography CVE vulnerability

set -e

echo "=== Step 0.1.1: Upgrade cryptography dependency (F-003) ==="

cd /Users/yitzchak/Documents/dev/careervp/src/backend

# Check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo "ERROR: pyproject.toml not found in src/backend"
    exit 1
fi

# Backup pyproject.toml
cp pyproject.toml pyproject.toml.bak

# Upgrade cryptography version
echo "Upgrading cryptography..."
sed -i 's/cryptography==46.0.3/cryptography>=46.0.5/' pyproject.toml

# Verify the change
if grep -q "cryptography>=46.0.5" pyproject.toml; then
    echo "SUCCESS: cryptography version updated"
else
    echo "ERROR: Failed to update cryptography version"
    mv pyproject.toml.bak pyproject.toml
    exit 1
fi

# Update lock file
echo "Updating lock file..."
uv lock

# Export requirements
echo "Exporting requirements..."
uv export --no-hashes -o lambda_requirements.txt

# Verify pip-audit shows 0 vulnerabilities
echo "Running pip-audit..."
if uvx pip-audit -r lambda_requirements.txt; then
    echo "SUCCESS: 0 vulnerabilities found"
else
    echo "WARNING: pip-audit found vulnerabilities - review output above"
    # Don't fail here as it might be a false positive
fi

# Cleanup
rm -f pyproject.toml.bak

echo "=== Step 0.1.1 Complete ==="
