#!/bin/bash

# Local test script that properly mimics Harbor environment
set -e

TASK_PATH="$(cd "$(dirname "$0")" && pwd)"
IMAGE_TAG="harbor-oracle-test:$(cd "$TASK_PATH" && git rev-parse --short HEAD 2>/dev/null || echo "latest")"
TIMESTAMP="$(date +%Y-%m-%d__%H-%M-%S)"
JOBS_DIR="${TASK_PATH}/jobs/${TIMESTAMP}"
LOGS_DIR="${JOBS_DIR}/logs"

echo "Building Docker image..."
docker build --platform=linux/amd64 -t "$IMAGE_TAG" -f "${TASK_PATH}/environment/Dockerfile" "${TASK_PATH}/environment" > /dev/null

echo "Running oracle trial..."
mkdir -p "$LOGS_DIR/verifier"

# Run the test with proper mounts
if docker run --rm --platform=linux/amd64 -w /app \
  -v "${TASK_PATH}/tls_security_analyzer.py:/app/tls_security_analyzer.py:ro" \
  -v "${TASK_PATH}/instruction.md:/app/instruction.md:ro" \
  -v "${TASK_PATH}/README.md:/app/README.md:ro" \
  -v "${TASK_PATH}/solution:/solution:ro" \
  -v "${TASK_PATH}/tests:/tests:ro" \
  -v "${LOGS_DIR}:/logs" \
  "$IMAGE_TAG" bash -lc '
    set -euo pipefail
    if [[ -f /solution/solve.sh ]]; then
      bash /solution/solve.sh > /dev/null 2>&1
    fi
    if [[ -f /tests/test.sh ]]; then
      bash /tests/test.sh > /dev/null 2>&1
    fi
  ' 2>/dev/null; then
  REWARD=1
else
  REWARD=0
fi

# Check for reward file
if [[ -f "${LOGS_DIR}/verifier/reward.txt" ]]; then
  REWARD=$(cat "${LOGS_DIR}/verifier/reward.txt")
fi

# Write result
cat > "${JOBS_DIR}/result.json" <<EOF
{
  "agent": "oracle",
  "dataset": "adhoc",
  "trials": 1,
  "errors": 0,
  "mean": ${REWARD},
  "rewards": [${REWARD}]
}
EOF

echo "  1/1 Mean: ${REWARD}"
echo "Results written to ${JOBS_DIR}/result.json"
echo ""
echo "        oracle on adhoc         "
echo "┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓"
echo "┃ Metric              ┃ Value  ┃"
echo "┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩"
echo "│ Agent               │ oracle │"
echo "│ Dataset             │ adhoc  │"
echo "│ Trials              │ 1      │"
echo "│ Errors              │ 0      │"
echo "│                     │        │"
echo "│ Mean                │ ${REWARD}  │"
echo "│                     │        │"
echo "│ Reward Distribution │        │"
if [[ "$REWARD" == "1" || "$REWARD" == "1.0" ]]; then
  echo "│   reward = 1.0      │ 1      │"
else
  echo "│   reward = 0.0      │ 1      │"
fi
echo "└─────────────────────┴────────┘"
