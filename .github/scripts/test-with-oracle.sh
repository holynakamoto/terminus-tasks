#!/bin/bash
# Test a task by running its oracle solution directly
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

echo "🤖 Testing $TASK_NAME with Oracle solution"
echo "========================================"

# Check if solution directory exists
if [ ! -d "$TASK_DIR/solution" ]; then
    echo "❌ No solution directory found"
    exit 1
fi

# Find the solution script (solve.sh, solve.py, etc.)
SOLVE_SCRIPT=""
if [ -f "$TASK_DIR/solution/solve.sh" ]; then
    SOLVE_SCRIPT="$TASK_DIR/solution/solve.sh"
elif [ -f "$TASK_DIR/solution/solve.py" ]; then
    SOLVE_SCRIPT="$TASK_DIR/solution/solve.py"
else
    echo "❌ No solve script found in solution/"
    exit 1
fi

echo "Found solution script: $SOLVE_SCRIPT"

# Build the Docker image if Dockerfile exists
if [ -f "$TASK_DIR/environment/Dockerfile" ]; then
    echo "Building Docker environment..."
    docker buildx build \
        --cache-from=type=local,src=/tmp/.buildx-cache \
        --cache-to=type=local,dest=/tmp/.buildx-cache-new,mode=max \
        --load \
        -t "$TASK_NAME-test" \
        "$TASK_DIR/environment/"

    # Move cache to prevent unlimited growth
    if [ -d "/tmp/.buildx-cache-new" ]; then
        rm -rf /tmp/.buildx-cache
        mv /tmp/.buildx-cache-new /tmp/.buildx-cache
    fi

    # Run solution AND tests in the same container to preserve state
    echo "Running solution and tests in Docker container..."

    # Set CI_FAST_MODE for faster testing (reduces iteration counts in compatible tasks)
    # Timeout: 15 minutes (900s) to match CodeBuild's typical timeout
    # Some tasks like cracked256 with high PBKDF2 iterations can take 8-10 minutes
    timeout 900 docker run --rm \
        -e CI_FAST_MODE=1 \
        -v "$TASK_DIR/solution:/solution:ro" \
        -v "$TASK_DIR/tests:/tests:ro" \
        -w /app \
        "$TASK_NAME-test" \
        bash -c '
            set -e
            echo "=== Running solution ==="
            cp /solution/* /app/
            chmod +x /app/solve.sh 2>/dev/null || true
            if [ -f /app/solve.sh ]; then
                /app/solve.sh
            elif [ -f /app/solve.py ]; then
                python3 /app/solve.py
            else
                echo "No solve script found"
                exit 1
            fi

            echo ""
            echo "=== Running tests ==="
            if [ -f /tests/test.sh ]; then
                bash /tests/test.sh
            fi
            if [ -f /tests/test_outputs.py ]; then
                python3 -m pytest /tests/test_outputs.py -v
            fi
        '

    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 124 ]; then
        echo "⚠️  Oracle test TIMEOUT (exceeded 900s / 15 minutes)"
        echo "This task may be too computationally intensive for CI"
        echo "Consider adding CI_FAST_MODE support to the oracle solution"
        exit 1
    elif [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Oracle test PASSED"
        exit 0
    else
        echo "❌ Oracle test FAILED with exit code $EXIT_CODE"
        exit 1
    fi
else
    echo "❌ No Dockerfile found in environment/"
    exit 1
fi
