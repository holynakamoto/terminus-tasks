#!/bin/bash

# Use this file to install test dependencies and run the tests.
# It will be copied to /tests/test.sh and run from the working directory.

echo "============================================================"
echo "[DEBUG] test.sh starting at $(date -Iseconds)"
echo "[DEBUG] Hostname: $(hostname)"
echo "[DEBUG] Working directory: $(pwd)"
echo "============================================================"

# Show what files exist before testing
echo "[DEBUG] Checking /app directory contents:"
ls -la /app/ 2>/dev/null || echo "[DEBUG] /app directory not found or empty"

echo "[DEBUG] Checking if output file exists:"
if [ -f /app/cracked.csv ]; then
    echo "[DEBUG] /app/cracked.csv exists"
    echo "[DEBUG] File size: $(stat -c%s /app/cracked.csv 2>/dev/null || stat -f%z /app/cracked.csv 2>/dev/null || echo 'unknown')"
    echo "[DEBUG] Line count: $(wc -l < /app/cracked.csv)"
    echo "[DEBUG] First 10 lines:"
    head -10 /app/cracked.csv
else
    echo "[DEBUG] /app/cracked.csv DOES NOT EXIST - agent may have failed or timed out"
fi

echo "[DEBUG] Checking hashes.txt integrity:"
if [ -f /app/hashes.txt ]; then
    echo "[DEBUG] /app/hashes.txt exists with $(wc -l < /app/hashes.txt) lines"
else
    echo "[DEBUG] /app/hashes.txt DOES NOT EXIST"
fi

echo "============================================================"
echo "[DEBUG] Installing test dependencies..."
echo "============================================================"

apt-get update
apt-get install -y curl

curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh

source $HOME/.local/bin/env

echo "[DEBUG] Running pytest at $(date -Iseconds)..."

# CTRF produces a standard test report in JSON format which is useful for logging.
uvx \
  --with pytest==8.4.1 \
  --with pytest-json-ctrf==0.3.5 \
  pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
