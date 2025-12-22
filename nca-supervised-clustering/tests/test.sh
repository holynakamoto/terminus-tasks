#!/bin/bash
set -euo pipefail

# Create logs directory for Harbor framework
mkdir -p /logs/verifier

# Ensure reward file is created even on early exit
trap 'if [ ! -f /logs/verifier/reward.txt ]; then echo 0 > /logs/verifier/reward.txt; fi' EXIT

# Install dependencies
apt-get update
apt-get install -y curl

pip3 install --break-system-packages --no-cache-dir \
    "numpy==1.26.4" \
    "scikit-learn==1.3.2" \
    "pytest==8.4.1" \
    "pytest-json-ctrf==0.3.5"

# Note: The dataset is generated during Docker image build (see environment/Dockerfile)
# The Oracle agent runs the solution automatically before test.sh executes
# We just verify the dataset exists and then run the tests

echo "Verifying test dataset exists..."
if [ ! -f "/app/data/dataset.npz" ]; then
    echo "ERROR: Dataset not found at /app/data/dataset.npz"
    exit 1
fi
echo "✓ Test dataset found at /app/data/dataset.npz"

# Run tests
echo "Running tests..."
if python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA; then
  echo "✓ All tests passed"
  echo 1 > /logs/verifier/reward.txt
else
  echo "✗ Tests failed"
  echo 0 > /logs/verifier/reward.txt
fi
