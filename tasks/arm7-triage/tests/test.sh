#!/usr/bin/env bash
set -euo pipefail

echo "=== Setting up test environment ==="

# Source the cross-compilation environment if it exists
# (pytest tests will validate this file's existence and content)
if [ -f /logs/verifier/env.sh ]; then
    # shellcheck disable=SC1091
    source /logs/verifier/env.sh
    echo "✓ Loaded /logs/verifier/env.sh"
else
    echo "⚠ /logs/verifier/env.sh not found (will be validated by pytest)"
fi

# Ensure log directory exists
mkdir -p /logs/verifier
if [ ! -w /logs/verifier ]; then
  echo "Error: /logs/verifier is not writable" >&2
  exit 1
fi

# Install test dependencies
echo "=== Installing test dependencies ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends python3 python3-pip
apt-get clean
rm -rf /var/lib/apt/lists/*
pip3 install --no-cache-dir --quiet --break-system-packages pytest==8.3.4

echo "=== Running pytest tests ==="
if [ ! -d /app ]; then
  echo "Error: /app directory does not exist" >&2
  exit 1
fi
cd /app

# Run pytest with verbose output
# pytest will execute all validations from test_outputs.py
set +e
pytest /tests/test_outputs.py -v --tb=short --color=yes -rA
pytest_status=$?
set -e

if [ $pytest_status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
