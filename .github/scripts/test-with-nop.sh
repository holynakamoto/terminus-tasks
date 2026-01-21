#!/bin/bash
# Test a task with NOP (no operation) solution
# Enhanced to use pre-built Docker images from GHCR when available
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

echo "🔍 Testing $TASK_NAME with NOP solution"
echo "======================================"

# Build or pull the Docker image
if [ -f "$TASK_DIR/environment/Dockerfile" ]; then
    IMAGE_NAME="$TASK_NAME-test"
    
    # Try to use pre-built image from GHCR if available
    if [ -n "$USE_PREBUILT_IMAGES" ] && [ "$USE_PREBUILT_IMAGES" = "true" ]; then
        # Determine the correct image tag
        if [ "$GITHUB_EVENT_NAME" = "pull_request" ]; then
            GHCR_IMAGE="ghcr.io/${GITHUB_REPOSITORY,,}/task-$TASK_NAME:pr-$GITHUB_PR_NUMBER"
        else
            GHCR_IMAGE="ghcr.io/${GITHUB_REPOSITORY,,}/task-$TASK_NAME:${GITHUB_REF_NAME}"
        fi
        
        echo "Attempting to pull pre-built image: $GHCR_IMAGE"
        if docker pull "$GHCR_IMAGE" 2>/dev/null; then
            echo "✅ Using pre-built image from GHCR"
            docker tag "$GHCR_IMAGE" "$IMAGE_NAME"
        else
            echo "⚠️  Pre-built image not found, falling back to local build"
            USE_PREBUILT_IMAGES="false"
        fi
    fi
    
    # Build locally if pre-built image not used
    if [ "$USE_PREBUILT_IMAGES" != "true" ]; then
        echo "Building Docker environment locally..."
        docker buildx build \
            --cache-from=type=local,src=/tmp/.buildx-cache \
            --cache-to=type=local,dest=/tmp/.buildx-cache-new,mode=max \
            --load \
            -t "$IMAGE_NAME" \
            "$TASK_DIR/environment/"

        # Move cache to prevent unlimited growth
        if [ -d "/tmp/.buildx-cache-new" ]; then
            rm -rf /tmp/.buildx-cache
            mv /tmp/.buildx-cache-new /tmp/.buildx-cache
        fi
    fi

    # Run NOP test - container should start successfully and pass basic tests
    echo "Running NOP test in Docker container..."
    
    # Timeout: 5 minutes (300s) - NOP should be quick
    timeout 300 docker run --rm \
        -v "$TASK_DIR/tests:/tests:ro" \
        -w /app \
        "$IMAGE_NAME" \
        bash -c '
            set -e
            echo "=== Running NOP test ==="
            echo "Container started successfully"
            
            # Check basic environment
            echo "Python version: $(python3 --version 2>&1 || echo \"Python not installed\")"
            echo "Working directory: $(pwd)"
            echo "Available commands: $(ls /usr/local/bin 2>/dev/null | head -5 || echo \"none\")"
            
            # Run basic tests if they exist
            if [ -f /tests/test.sh ]; then
                echo "Running test.sh in NOP mode..."
                # NOP mode: just verify tests can load/parse without running full suite
                bash -n /tests/test.sh && echo "✅ test.sh syntax OK"
            elif [ -f /tests/test_outputs.py ]; then
                echo "Running pytest collection..."
                python3 -m pytest /tests/test_outputs.py --collect-only -q
            fi
            
            echo "✅ NOP test completed successfully"
        '

    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 124 ]; then
        echo "⚠️  NOP test TIMEOUT (exceeded 300s / 5 minutes)"
        exit 1
    elif [ $EXIT_CODE -eq 0 ]; then
        echo "✅ NOP test PASSED"
        exit 0
    else
        echo "❌ NOP test FAILED with exit code $EXIT_CODE"
        exit 1
    fi
else
    echo "❌ No Dockerfile found in environment/"
    exit 1
fi
