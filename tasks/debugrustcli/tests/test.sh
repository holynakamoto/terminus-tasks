#!/usr/bin/env bash
set -euo pipefail

echo "=== Setting up test environment ==="

# Ensure log directory exists
mkdir -p /logs/verifier
if [ ! -w /logs/verifier ]; then
  echo "Error: /logs/verifier is not writable" >&2
  exit 1
fi

echo "=== Running pytest tests ==="
if [ ! -d /app ]; then
  echo "Error: /app directory does not exist" >&2
  exit 1
fi
cd /app

# Run pytest using uv (Harbor requirement)
# Install pytest and pytest-json-ctrf using uv
set +e
uvx \
  -p 3.11 \
  -w pytest==8.3.4 \
  -w pytest-json-ctrf==0.3.5 \
  pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -v --tb=short --color=yes -rA
pytest_status=$?
set -e

if [ $pytest_status -eq 0 ]; then
  echo "=== All tests passed ==="
  echo 1 > /logs/verifier/reward.txt
else
  echo "=== Tests failed ==="
  echo 0 > /logs/verifier/reward.txt
fi

exit $pytest_status
