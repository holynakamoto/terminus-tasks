#!/bin/bash
# Test if cracked256 Docker image is publicly accessible without authentication
# This simulates what SnorkelAI's CodeBuild would experience

# Use safer options: fail on undefined variables and pipeline failures
# but don't exit on command failures (we handle those explicitly)
set -u -o pipefail

echo "🧪 Testing Public Docker Image Access"
echo "======================================"
echo ""

TASK_NAME="cracked256"
REPO="holynakamoto/terminus-tasks"
IMAGE="ghcr.io/${REPO,,}/task-${TASK_NAME}"

echo "Testing image: $IMAGE"
echo ""

# Step 1: Log out of GHCR to simulate unauthenticated access
echo "📤 Logging out of GHCR..."
docker logout ghcr.io 2>/dev/null || true
echo ""

# Step 2: Try pulling different tags
echo "🔍 Attempting to pull image tags..."
echo ""

SUCCESS=false

# Try common tags
for TAG in "main" "latest" "$(git rev-parse HEAD 2>/dev/null | cut -c1-7 || echo 'sha-unknown')"; do
    FULL_IMAGE="${IMAGE}:${TAG}"
    echo "Trying: $FULL_IMAGE"

    if docker pull "$FULL_IMAGE" 2>&1 | tee /tmp/pull_output.txt; then
        echo "✅ SUCCESS: Image $FULL_IMAGE is publicly accessible!"
        echo ""

        # Show image details
        echo "Image details:"
        docker images "$FULL_IMAGE" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
        echo ""

        # Test if it can run
        echo "Testing if image runs..."
        CONTAINER_ID=$(docker run -d "$FULL_IMAGE")
        sleep 2

        # Check if container is running (non-fatal check)
        if docker ps -q -f id="$CONTAINER_ID" | grep -q .; then
            echo "✅ Container started successfully"
            # Stop the running container
            docker stop "$CONTAINER_ID" > /dev/null 2>&1 || true
        else
            echo "⚠️  Container exited (may be expected for some images)"
        fi

        # Always clean up: force-remove container regardless of state
        docker rm -f "$CONTAINER_ID" > /dev/null 2>&1 || true

        SUCCESS=true
        break
    else
        # Check error type
        if grep -q "unauthorized" /tmp/pull_output.txt || grep -q "not found" /tmp/pull_output.txt; then
            echo "❌ FAILED: Image not accessible (auth required or doesn't exist)"
        else
            echo "⚠️  Unknown error"
        fi
        echo ""
    fi
done

echo ""
echo "======================================"

if [ "$SUCCESS" = true ]; then
    echo "✅ RESULT: Image IS publicly accessible"
    echo ""
    echo "SnorkelAI's CodeBuild should be able to pull this image."
    exit 0
else
    echo "❌ RESULT: Image NOT publicly accessible"
    echo ""
    echo "Possible issues:"
    echo "  1. Image visibility is set to Private in GHCR settings"
    echo "  2. Image hasn't been built/pushed yet for these tags"
    echo "  3. Repository name mismatch"
    echo ""
    echo "To fix:"
    echo "  1. Go to: https://github.com/${REPO}/pkgs/container/task-${TASK_NAME}"
    echo "  2. Click 'Package settings'"
    echo "  3. Change visibility to 'Public'"
    echo "  4. Ensure images are pushed by running: git push (triggers build-task-images workflow)"
    exit 1
fi
