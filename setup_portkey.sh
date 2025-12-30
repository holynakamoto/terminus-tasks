#!/bin/bash
# Portkey configuration script for OpenHands
# This sets up environment variables to use Portkey as a proxy for Anthropic
#
# Usage: source setup_portkey.sh
# DO NOT run with ./setup_portkey.sh - it must be sourced to set environment variables

# Your Portkey API key (provided)
export PORTKEY_API_KEY="fdZYjptATE8UssqQiT/x5fdrgJ2g"

# Use Portkey API key for Anthropic (Portkey proxies Anthropic)
export ANTHROPIC_API_KEY="$PORTKEY_API_KEY"

# Portkey base URL (REQUIRED for LiteLLM/OpenHands CLI)
export ANTHROPIC_BASE_URL="https://api.portkey.ai/v1"

# LiteLLM also checks these variable names
export LITELLM_API_BASE="https://api.portkey.ai/v1"

# Portkey provider header (REQUIRED - update with your actual provider name)
# Check your Portkey dashboard -> Providers -> Anthropic -> provider name/slug
# Common values: "anthropic-main", "anthropic", or your custom provider name
export ANTHROPIC_HEADERS='{"x-portkey-provider":"anthropic-main"}'

# Alternative: If your Portkey workspace uses virtual keys instead:
# export ANTHROPIC_HEADERS='{"x-portkey-virtual-key":"anthropic-main"}'

# Model configuration (optional - defaults in agent_script.py)
export LLM_MODEL="anthropic/claude-sonnet-4-5-20250929"

# For OpenHands CLI specifically
export OPENHANDS_LLM_PROVIDER="anthropic"

echo "✅ Portkey configuration loaded!"
echo ""
echo "Configuration:"
echo "  PORTKEY_API_KEY: ${PORTKEY_API_KEY:0:20}..."
echo "  ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:0:20}..."
echo "  ANTHROPIC_BASE_URL: $ANTHROPIC_BASE_URL"
echo "  LITELLM_API_BASE: $LITELLM_API_BASE"
echo "  ANTHROPIC_HEADERS: $ANTHROPIC_HEADERS"
echo "  LLM_MODEL: $LLM_MODEL"
echo ""
echo "⚠️  IMPORTANT: Update ANTHROPIC_HEADERS with your actual Portkey provider name"
echo "   Check: Portkey Dashboard -> Providers -> Anthropic -> provider name"
echo ""
echo "⚠️  NOTE: LiteLLM (used by OpenHands CLI) may not support headers via env vars"
echo "   If you get authentication errors, you may need to:"
echo "   1. Check your Portkey provider name is correct"
echo "   2. Try using virtual keys instead of provider"
echo "   3. Configure Portkey to work without explicit headers"
echo ""
echo "To use this configuration:"
echo "  source setup_portkey.sh"
echo ""
echo "For OpenHands CLI (may need explicit base URL):"
echo "  openhands --llm-model anthropic/claude-sonnet-4-5-20250929"
echo ""
echo "For Python SDK (better header support):"
echo "  python agent_script.py"
echo ""
echo "To test Portkey connection:"
echo "  ./test_portkey_openhands.sh  # Uses OpenHands' Python (has LiteLLM)"
echo "  # OR test directly with OpenHands CLI:"
echo "  openhands"

