#!/bin/bash
# Test Portkey configuration using OpenHands' Python environment (which has LiteLLM)

OPENHANDS_PYTHON="$HOME/.local/share/uv/tools/openhands/bin/python"

if [ ! -f "$OPENHANDS_PYTHON" ]; then
    echo "❌ OpenHands Python not found at $OPENHANDS_PYTHON"
    echo "   Make sure OpenHands is installed: pip install openhands"
    exit 1
fi

echo "Using OpenHands Python: $OPENHANDS_PYTHON"
echo ""

# Source the Portkey config if not already sourced
if [ -z "$ANTHROPIC_BASE_URL" ]; then
    echo "Sourcing setup_portkey.sh..."
    source "$(dirname "$0")/setup_portkey.sh"
    echo ""
fi

# Run the test script with OpenHands' Python
"$OPENHANDS_PYTHON" "$(dirname "$0")/test_portkey.py"

