#!/usr/bin/env bash
#
# Execute Architect Prompt: Complete Company Research Transformation Layer
# This script runs the architect agent to generate missing components
#
# Usage:
#   ./run_architect_prompt.sh [--dry-run]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_FILE="${SCRIPT_DIR}/architect_company_research_missing.prompt"
OUTPUT_RESULTS="${SCRIPT_DIR}/../EXECUTION_RESULTS.md"

echo "=============================================="
echo "Company Research - Architect Prompt Runner"
echo "=============================================="
echo ""

# Check if prompt file exists
if [ ! -f "${PROMPT_FILE}" ]; then
    echo "ERROR: Prompt file not found: ${PROMPT_FILE}"
    exit 1
fi

# Display prompt summary
echo "Prompt file: ${PROMPT_FILE}"
echo "Output to: ${OUTPUT_RESULTS}"
echo ""

echo "This will:"
echo "  1. Analyze existing files"
echo "  2. Generate missing spec files (YAML)"
echo "  3. Update EXECUTION_RUNBOOK.md with missing steps"
echo "  4. Document results in EXECUTION_RESULTS.md"
echo ""

# Ask for confirmation unless dry-run
if [ "$1" != "--dry-run" ]; then
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

echo "Running architect agent..."
echo ""

# The actual execution would use Claude Code CLI
# This is a placeholder for the execution command
cat << 'EOF'
To execute this prompt with Claude Code Opus:

1. Copy the contents of architect_company_research_missing.prompt
2. Run with Claude Code:

   claude --model opus \
     --system-prompt "$(cat docs/refactor/prompts/architect_company_research_missing.prompt)" \
     --output-format markdown

3. The agent will:
   - Analyze existing state
   - Generate 4 spec files:
     * company_research_model_spec.yaml
     * company_research_fvs_spec.yaml
     * company_research_payload_spec.yaml
     * company_research_e2e_spec.yaml
   - Update EXECUTION_RUNBOOK.md with steps X.0, X.FVS, X.PAYLOAD, X.E2E, X.LIVE
   - Document results in EXECUTION_RESULTS.md

Expected output:
- 4 new YAML spec files in docs/refactor/specs/
- Updated EXECUTION_RUNBOOK.md with 5 new steps
- Updated EXECUTION_RESULTS.md with addendum section
EOF

echo ""
echo "=============================================="
echo "Prompt ready for execution"
echo "=============================================="
