#!/bin/bash
# Step 0.4.1: Change log_event=True to False
# Finding 9 - Disable sensitive event logging

set -e

echo "=== Step 0.4.1: Disable Sensitive Event Logging ==="

cd /Users/yitzchak/Documents/dev/careervp/src/backend/careervp/handlers

# Find all log_event=True occurrences
echo "Searching for log_event=True patterns..."
FOUND=$(grep -rn "log_event.*True" . --include="*.py" 2>/dev/null || true)

if [ -z "$FOUND" ]; then
    echo "SUCCESS: No log_event=True patterns found - already clean!"
    exit 0
fi

echo "Found log_event=True in the following locations:"
echo "$FOUND"

# Define the files that need changes (from the runbook)
FILES_TO_FIX=(
    "vpr_handler.py"
    "vpr_submit_handler.py"
    "vpr_status_handler.py"
    "vpr_worker_handler.py"
)

# Change log_event=True to log_event=False
for file in "${FILES_TO_FIX[@]}"; do
    if [ -f "$file" ]; then
        echo "Processing $file..."

        # Create backup
        cp "$file" "${file}.bak"

        # Replace log_event=True with log_event=False
        sed -i '' 's/log_event=True/log_event=False/g' "$file"

        # Verify the change
        if grep -q "log_event=False" "$file"; then
            echo "  SUCCESS: Changed log_event to False in $file"
        else
            echo "  WARNING: Could not verify change in $file"
        fi
    else
        echo "  WARNING: $file not found"
    fi
done

# Verify no log_event=True remains
echo ""
echo "Verifying removal..."
REMAINING=$(grep -rn "log_event.*True" . --include="*.py" 2>/dev/null || true)

if [ -z "$REMAINING" ]; then
    echo "SUCCESS: All log_event=True patterns changed to False (0 matches)"
    # Clean up backups
    for file in "${FILES_TO_FIX[@]}"; do
        rm -f "${file}.bak" 2>/dev/null || true
    done
else
    echo "WARNING: Some log_event=True patterns may still exist:"
    echo "$REMAINING"
fi

echo "=== Step 0.4.1 Complete ==="
