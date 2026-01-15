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
    docker build -t "$TASK_NAME-test" "$TASK_DIR/environment/"

    # Run the solution in the container
    echo "Running solution in Docker container..."
    docker run --rm \
        -v "$TASK_DIR/solution:/solution:ro" \
        -v "$TASK_DIR/tests:/tests:ro" \
        -w /app \
        "$TASK_NAME-test" \
        bash -c "cp /solution/* /app/ && chmod +x /app/solve.sh && /app/solve.sh"

    SOLVE_EXIT=$?

    if [ $SOLVE_EXIT -ne 0 ]; then
        echo "❌ Solution script failed with exit code $SOLVE_EXIT"
        exit 1
    fi

    # Run tests in the container
    echo "Running tests..."
    docker run --rm \
        -v "$TASK_DIR/tests:/tests:ro" \
        -w /app \
        "$TASK_NAME-test" \
        bash -c "if [ -f /tests/test.sh ]; then bash /tests/test.sh; fi && if [ -f /tests/test_outputs.py ]; then python3 -m pytest /tests/test_outputs.py -v; fi"

    TEST_EXIT=$?

    if [ $TEST_EXIT -eq 0 ]; then
        echo "✅ Oracle test PASSED"
        exit 0
    else
        echo "❌ Oracle test FAILED"
        exit 1
    fi
else
    echo "❌ No Dockerfile found in environment/"
    exit 1
fi
