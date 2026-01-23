#!/bin/bash
# Prepare cracked256 task for SnorkelAI submission
# This creates a zip file with all necessary components

set -e

TASK_NAME="cracked256"
OUTPUT_DIR="/tmp/snorkel-submission"
ZIP_FILE="$HOME/${TASK_NAME}-snorkel-submission.zip"

echo "📦 Preparing SnorkelAI Submission Package"
echo "=========================================="
echo ""

# Clean up previous builds
rm -rf "$OUTPUT_DIR"
rm -f "$ZIP_FILE"

# Create output directory
mkdir -p "$OUTPUT_DIR/$TASK_NAME"

echo "📋 Copying task files..."

# Copy required directories
for dir in environment solution tests; do
    if [ -d "tasks/$TASK_NAME/$dir" ]; then
        echo "  ✓ $dir/"
        cp -r "tasks/$TASK_NAME/$dir" "$OUTPUT_DIR/$TASK_NAME/"
    else
        echo "  ✗ $dir/ (missing!)"
    fi
done

# Copy required files
for file in task.md task.toml; do
    if [ -f "tasks/$TASK_NAME/$file" ]; then
        echo "  ✓ $file"
        cp "tasks/$TASK_NAME/$file" "$OUTPUT_DIR/$TASK_NAME/"
    else
        echo "  ✗ $file (missing!)"
    fi
done

# Optional: metadata.json if it exists
if [ -f "tasks/$TASK_NAME/metadata.json" ]; then
    echo "  ✓ metadata.json (optional)"
    cp "tasks/$TASK_NAME/metadata.json" "$OUTPUT_DIR/$TASK_NAME/"
fi

echo ""
echo "📊 Package contents:"
tree "$OUTPUT_DIR" 2>/dev/null || find "$OUTPUT_DIR" -type f

echo ""
echo "🔍 Verifying critical components..."

# Verify Dockerfile
if [ -f "$OUTPUT_DIR/$TASK_NAME/environment/Dockerfile" ]; then
    echo "  ✅ Dockerfile present"
    echo "     Content preview:"
    head -n 5 "$OUTPUT_DIR/$TASK_NAME/environment/Dockerfile" | sed 's/^/       /'
else
    echo "  ❌ Dockerfile MISSING - SnorkelAI cannot build without this!"
    exit 1
fi

# Verify generate_data.py
if [ -f "$OUTPUT_DIR/$TASK_NAME/environment/generate_data.py" ]; then
    echo "  ✅ generate_data.py present (required for Docker build)"
else
    echo "  ⚠️  generate_data.py missing - Dockerfile RUN command will fail!"
fi

# Verify task.toml
if [ -f "$OUTPUT_DIR/$TASK_NAME/task.toml" ]; then
    echo "  ✅ task.toml present"
    echo "     Build timeout: $(grep build_timeout_sec "$OUTPUT_DIR/$TASK_NAME/task.toml" || echo 'not specified')"
else
    echo "  ❌ task.toml MISSING"
    exit 1
fi

# Verify solution
if [ -f "$OUTPUT_DIR/$TASK_NAME/solution/solve.sh" ] || [ -f "$OUTPUT_DIR/$TASK_NAME/solution/solve.py" ]; then
    echo "  ✅ Solution script present"
else
    echo "  ⚠️  No solve.sh or solve.py in solution/"
fi

# Verify tests
if [ -f "$OUTPUT_DIR/$TASK_NAME/tests/test_outputs.py" ] || [ -f "$OUTPUT_DIR/$TASK_NAME/tests/test.sh" ]; then
    echo "  ✅ Test script present"
else
    echo "  ⚠️  No test script found"
fi

echo ""
echo "📦 Creating zip file..."
cd "$OUTPUT_DIR"
zip -r "$ZIP_FILE" "$TASK_NAME/" -x "*.pyc" "*__pycache__*" "*.log" ".DS_Store"

echo ""
echo "✅ Package created successfully!"
echo ""
echo "📍 Location: $ZIP_FILE"
echo "📊 Size: $(du -h "$ZIP_FILE" | cut -f1)"
echo ""

# Show zip contents
echo "📋 Archive contents:"
unzip -l "$ZIP_FILE" | tail -n +4 | head -n -2

echo ""
echo "======================================"
echo "📤 Next steps:"
echo ""
echo "1. Download the zip file:"
echo "   $ZIP_FILE"
echo ""
echo "2. Upload to SnorkelAI portal"
echo ""
echo "3. If SnorkelAI still fails, they need to:"
echo "   - Pull your public GHCR image: ghcr.io/holynakamoto/terminus-tasks/task-cracked256:main"
echo "   - OR build from included Dockerfile (may take ~5-10 min)"
echo ""
echo "4. Include these details in your support ticket:"
echo "   - Task has Dockerfile with build-time data generation"
echo "   - Build timeout in task.toml: 1600 seconds (27 minutes)"
echo "   - Public GHCR image available as fallback"
echo "   - Docker build runs: python3 generate_data.py (takes ~30 seconds)"
echo "======================================"
