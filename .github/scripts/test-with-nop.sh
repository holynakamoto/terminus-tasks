#!/bin/bash
# Test that a no-op agent cannot solve the task
set -e

TASK_NAME=$1
TASK_DIR="$HOME/harbor_tasks/$TASK_NAME"

if [ -z "$TASK_NAME" ]; then
    echo "Error: Task name required"
    exit 1
fi

if [ ! -d "$TASK_DIR" ]; then
    echo "Error: Task directory not found: $TASK_DIR"
    exit 1
fi

echo "🤖 Testing $TASK_NAME with NOP agent"
echo "========================================"

# NOP test: Try to run without any solution
# This should fail (proving the task requires real work)

if [ -f "$TASK_DIR/environment/Dockerfile" ]; then
    echo "Building Docker environment..."
    docker build -t "$TASK_NAME-nop" "$TASK_DIR/environment/" > /dev/null 2>&1

    # Run tests without running the solution
    # If tests pass, the task is too easy or leaking the answer
    echo "Running tests without solution (should fail)..."
    if docker run --rm \
        -v "$TASK_DIR/tests:/tests:ro" \
        -w /app \
        "$TASK_NAME-nop" \
        bash -c "if [ -f /tests/test.sh ]; then bash /tests/test.sh; fi && if [ -f /tests/test_outputs.py ]; then python3 -m pytest /tests/test_outputs.py -v; fi" > /dev/null 2>&1; then
        echo "❌ NOP agent unexpectedly passed (task is too easy or has leaked solution)"
        exit 1
    else
        echo "✅ NOP agent correctly failed (task requires real work)"
        exit 0
    fi
else
    echo "❌ No Dockerfile found in environment/"
    exit 1
fi
