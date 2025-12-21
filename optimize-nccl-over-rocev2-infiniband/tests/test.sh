#!/bin/bash

# Test runner for NCCL optimization task
# This script will be copied to /tests/test.sh and run from the working directory

set -e

echo "Setting up test environment..."

# Install test dependencies
apt-get update -qq
apt-get install -y -qq curl python3 python3-pip

# Install UV for fast Python package management
curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh
source $HOME/.local/bin/env

echo "Running NCCL optimization tests..."
echo ""

# Run pytest with CTRF reporting
uvx \
  --with pytest==8.4.1 \
  --with pytest-json-ctrf==0.3.5 \
  pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -v -rA

# Check test results
if [ $? -eq 0 ]; then
  echo ""
  echo "✓ All tests passed!"
  echo 1 > /logs/verifier/reward.txt
  exit 0
else
  echo ""
  echo "✗ Some tests failed"
  echo 0 > /logs/verifier/reward.txt
  exit 1
fi
