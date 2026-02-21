#!/bin/bash
# Step 0.3.1: Remove ALL AUTHORIZER_DISABLED Checks
# Finding 4 - Remove auth bypass patterns

set -e

echo "=== Step 0.3.1: Remove AUTHORIZER_DISABLED ==="

cd /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers

# Find all AUTHORIZER_DISABLED occurrences
echo "Searching for AUTHORIZER_DISABLED patterns..."
FOUND_FILES=$(grep -r "AUTHORIZER_DISABLED" . --include="*.py" 2>/dev/null || true)

if [ -z "$FOUND_FILES" ]; then
    echo "SUCCESS: No AUTHORIZER_DISABLED patterns found - already clean!"
    exit 0
fi

echo "Found AUTHORIZER_DISABLED in the following files:"
echo "$FOUND_FILES"

# Define the handlers to clean
HANDLERS=(
    "cv_tailoring_handler.py"
    "cover_letter_handler.py"
    "interview_prep_handler.py"
    "company_research_handler.py"
)

# Remove AUTHORIZER_DISABLED function blocks from each handler
for handler in "${HANDLERS[@]}"; do
    if [ -f "$handler" ]; then
        echo "Processing $handler..."

        # Create backup
        cp "$handler" "${handler}.bak"

        # Remove lines containing AUTHORIZER_DISABLED
        # This handles various patterns like:
        # - if os.getenv("AUTHORIZER_DISABLED")
        # - if AUTHORIZER_DISABLED
        # - "AUTHORIZER_DISABLED" in os.getenv

        # Use a more sophisticated approach - find and remove the entire if block
        # For simplicity, we'll remove specific patterns

        # Pattern 1: Remove the environment check line
        sed -i '' '/AUTHORIZER_DISABLED/d' "$handler"

        # Pattern 2: Remove empty if blocks left behind
        sed -i '' '/^[[:space:]]*if os\.getenv.*:$/d' "$handler"
        sed -i '' '/^[[:space:]]*return.*:$/d' "$handler"

        echo "  Removed AUTHORIZER_DISABLED from $handler"
    fi
done

# Also handle any other files that might have it
grep -r "AUTHORIZER_DISABLED" . --include="*.py" -l 2>/dev/null | while read -r file; do
    echo "Additional file with AUTHORIZER_DISABLED: $file"
    # For any additional files, just warn
done

# Verify removal
echo ""
echo "Verifying removal..."
REMAINING=$(grep -r "AUTHORIZER_DISABLED" . --include="*.py" 2>/dev/null || true)

if [ -z "$REMAINING" ]; then
    echo "SUCCESS: All AUTHORIZER_DISABLED patterns removed (0 matches)"
    # Clean up backups
    for handler in "${HANDLERS[@]}"; do
        rm -f "${handler}.bak" 2>/dev/null || true
    done
else
    echo "WARNING: Some AUTHORIZER_DISABLED patterns may still exist:"
    echo "$REMAINING"
    echo ""
    echo "Manual review may be required for remaining patterns"
fi

echo "=== Step 0.3.1 Complete ==="
