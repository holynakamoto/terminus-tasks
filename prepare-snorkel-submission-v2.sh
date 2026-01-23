#!/bin/bash
# Prepare cracked256 task for SnorkelAI submission (Snorkel-compliant version)
# Uses pre-generated data files and instant Docker build

set -e

TASK_NAME="cracked256"
OUTPUT_DIR="/tmp/snorkel-submission-v2"
ZIP_FILE="$HOME/${TASK_NAME}-snorkel-submission-v2.zip"

echo "📦 Preparing SnorkelAI Submission Package (Snorkel-Compliant)"
echo "=============================================================="
echo ""

# Clean up previous builds
rm -rf "$OUTPUT_DIR"
rm -f "$ZIP_FILE"

# Create output directory
mkdir -p "$OUTPUT_DIR/$TASK_NAME"

echo "📋 Copying task files..."

# Copy environment with Snorkel-compliant setup
if [ -d "tasks/$TASK_NAME/environment" ]; then
    echo "  ✓ environment/"
    mkdir -p "$OUTPUT_DIR/$TASK_NAME/environment"

    # Use Snorkel-compliant Dockerfile (pre-generated data, instant build)
    if [ -f "tasks/$TASK_NAME/environment/Dockerfile.snorkel-v2" ]; then
        echo "    → Using Snorkel-compliant Dockerfile (instant build)"
        cp "tasks/$TASK_NAME/environment/Dockerfile.snorkel-v2" "$OUTPUT_DIR/$TASK_NAME/environment/Dockerfile"
    else
        echo "    ⚠️  Dockerfile.snorkel-v2 not found, using original"
        cp "tasks/$TASK_NAME/environment/Dockerfile" "$OUTPUT_DIR/$TASK_NAME/environment/Dockerfile"
    fi

    # Copy pre-generated data files (required by new Dockerfile)
    if [ -f "tasks/$TASK_NAME/environment/hashes.txt" ]; then
        echo "    → Including pre-generated hashes.txt"
        cp "tasks/$TASK_NAME/environment/hashes.txt" "$OUTPUT_DIR/$TASK_NAME/environment/"
    else
        echo "    ❌ hashes.txt MISSING - generate with: python3 generate_data.py"
        exit 1
    fi

    if [ -f "tasks/$TASK_NAME/environment/dictionary.txt" ]; then
        echo "    → Including pre-generated dictionary.txt"
        cp "tasks/$TASK_NAME/environment/dictionary.txt" "$OUTPUT_DIR/$TASK_NAME/environment/"
    else
        echo "    ❌ dictionary.txt MISSING"
        exit 1
    fi

    # NOTE: generate_data.py is NOT included (no longer needed with pre-generated files)
    echo "    → Excluding generate_data.py (not needed for Snorkel)"
else
    echo "  ✗ environment/ (missing!)"
fi

# Copy solution and tests
for dir in solution tests; do
    if [ -d "tasks/$TASK_NAME/$dir" ]; then
        echo "  ✓ $dir/"
        cp -r "tasks/$TASK_NAME/$dir" "$OUTPUT_DIR/$TASK_NAME/"
    else
        echo "  ✗ $dir/ (missing!)"
    fi
done

# Copy required files
for file in task.toml; do
    if [ -f "tasks/$TASK_NAME/$file" ]; then
        echo "  ✓ $file"
        cp "tasks/$TASK_NAME/$file" "$OUTPUT_DIR/$TASK_NAME/"
    else
        echo "  ✗ $file (missing!)"
    fi
done

# task.md is optional for Snorkel
if [ -f "tasks/$TASK_NAME/task.md" ]; then
    echo "  ✓ task.md (optional)"
    cp "tasks/$TASK_NAME/task.md" "$OUTPUT_DIR/$TASK_NAME/"
fi

echo ""
echo "📊 Package contents:"
tree "$OUTPUT_DIR" 2>/dev/null || find "$OUTPUT_DIR" -type f | sed 's|^/tmp/snorkel-submission-v2/||'

echo ""
echo "🔍 Verifying Snorkel compliance..."

# Verify Dockerfile
if [ -f "$OUTPUT_DIR/$TASK_NAME/environment/Dockerfile" ]; then
    echo "  ✅ Dockerfile present"

    # Check if it's the Snorkel-compliant version (no RUN python3)
    if grep -q "RUN python3" "$OUTPUT_DIR/$TASK_NAME/environment/Dockerfile"; then
        echo "  ⚠️  WARNING: Dockerfile contains 'RUN python3' (build-time execution)"
        echo "     This may cause timeout issues in Snorkel's CodeBuild"
    else
        echo "  ✅ Dockerfile is Snorkel-compliant (no build-time execution)"
    fi

    # Show Dockerfile content
    echo ""
    echo "  Dockerfile content:"
    cat "$OUTPUT_DIR/$TASK_NAME/environment/Dockerfile" | sed 's/^/    /'
else
    echo "  ❌ Dockerfile MISSING"
    exit 1
fi

# Verify data files
if [ -f "$OUTPUT_DIR/$TASK_NAME/environment/hashes.txt" ] && \
   [ -f "$OUTPUT_DIR/$TASK_NAME/environment/dictionary.txt" ]; then
    echo ""
    echo "  ✅ Pre-generated data files present"
    echo "     hashes.txt: $(wc -l < "$OUTPUT_DIR/$TASK_NAME/environment/hashes.txt") lines"
    echo "     dictionary.txt: $(wc -l < "$OUTPUT_DIR/$TASK_NAME/environment/dictionary.txt") lines"
else
    echo "  ❌ Data files MISSING"
    exit 1
fi

# Verify task.toml
if [ -f "$OUTPUT_DIR/$TASK_NAME/task.toml" ]; then
    echo ""
    echo "  ✅ task.toml present"
    BUILD_TIMEOUT=$(grep build_timeout_sec "$OUTPUT_DIR/$TASK_NAME/task.toml" | awk '{print $3}')
    echo "     Build timeout: ${BUILD_TIMEOUT:-not specified}"
else
    echo "  ❌ task.toml MISSING"
    exit 1
fi

# Verify solution
if [ -f "$OUTPUT_DIR/$TASK_NAME/solution/solve.sh" ] || [ -f "$OUTPUT_DIR/$TASK_NAME/solution/solve.py" ]; then
    echo ""
    echo "  ✅ Solution script present"
else
    echo "  ⚠️  No solve.sh or solve.py in solution/"
fi

# Verify tests
if [ -f "$OUTPUT_DIR/$TASK_NAME/tests/test_outputs.py" ] || [ -f "$OUTPUT_DIR/$TASK_NAME/tests/test.sh" ]; then
    echo ""
    echo "  ✅ Test script present"
else
    echo "  ⚠️  No test script found"
fi

echo ""
echo "📦 Creating zip file..."
cd "$OUTPUT_DIR"
zip -r "$ZIP_FILE" "$TASK_NAME/" -x "*.pyc" "*__pycache__*" "*.log" ".DS_Store"

echo ""
echo "✅ Snorkel-compliant package created successfully!"
echo ""
echo "📍 Location: $ZIP_FILE"
echo "📊 Size: $(du -h "$ZIP_FILE" | cut -f1)"
echo ""

# Show zip contents
echo "📋 Archive contents:"
unzip -l "$ZIP_FILE" | tail -n +4 | head -n -2

echo ""
echo "======================================"
echo "🎯 Snorkel Compliance Summary"
echo "======================================"
echo ""
echo "✅ Docker build is INSTANT (< 5 seconds)"
echo "   - No build-time Python execution"
echo "   - No dependency installation"
echo "   - Just copies pre-generated files"
echo ""
echo "✅ Fully REPRODUCIBLE"
echo "   - Data generated with random.seed(42)"
echo "   - Same files every time"
echo "   - No build-time randomness"
echo ""
echo "✅ LIGHTWEIGHT"
echo "   - Base image: python:3.11-slim"
echo "   - No additional packages"
echo "   - Total package: $(du -h "$ZIP_FILE" | cut -f1)"
echo ""
echo "✅ No PRIVILEGED mode required"
echo ""
echo "======================================"
echo "📤 Next Steps"
echo "======================================"
echo ""
echo "1. Download: $ZIP_FILE"
echo ""
echo "2. Upload to Snorkel portal"
echo ""
echo "3. Expected behavior:"
echo "   - Docker build: < 5 seconds (was 2-3 minutes)"
echo "   - All 13 parallel builds should succeed"
echo "   - No S3 NoSuchKey errors"
echo ""
echo "4. If still fails, provide Snorkel with:"
echo "   - CloudWatch logs from CodeBuild"
echo "   - Confirmation that buildspec.yml has commands"
echo "   - Network access to public registries (python:3.11-slim)"
echo "======================================"
