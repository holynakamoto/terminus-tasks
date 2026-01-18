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
    docker buildx build \
        --cache-from=type=local,src=/tmp/.buildx-cache \
        --cache-to=type=local,dest=/tmp/.buildx-cache-new,mode=max \
        --load \
        -t "$TASK_NAME-nop" \
        "$TASK_DIR/environment/" 2>&1 | grep -v "^#" || true

    # Move cache to prevent unlimited growth
    if [ -d "/tmp/.buildx-cache-new" ]; then
        rm -rf /tmp/.buildx-cache
        mv /tmp/.buildx-cache-new /tmp/.buildx-cache
    fi

    # Run tests without running the solution
    # If tests pass, the task is too easy or leaking the answer
    echo "Running tests without solution (should fail)..."

    # Capture test output for debugging if it unexpectedly passes
    TEST_OUTPUT=$(mktemp)
    if docker run --rm \
        -v "$TASK_DIR/tests:/tests:ro" \
        -w /app \
        "$TASK_NAME-nop" \
        bash -c "if [ -f /tests/test.sh ]; then bash /tests/test.sh; fi && if [ -f /tests/test_outputs.py ]; then python3 -m pytest /tests/test_outputs.py -v; fi" > "$TEST_OUTPUT" 2>&1; then
        echo "❌ NOP agent unexpectedly passed (task is too easy or has leaked solution)"
        echo "Test output:"
        cat "$TEST_OUTPUT"
        rm -f "$TEST_OUTPUT"
        exit 1
    else
        echo "✅ NOP agent correctly failed (task requires real work)"
        rm -f "$TEST_OUTPUT"
        exit 0
    fi
else
    echo "❌ No Dockerfile found in environment/"
    exit 1
fi
