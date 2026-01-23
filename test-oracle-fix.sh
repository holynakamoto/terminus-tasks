#!/bin/bash
# Quick test of Oracle solve.sh with pre-generated data

set -e

echo "🧪 Testing Oracle Solution with Pre-Generated Data"
echo "=================================================="
echo ""

# Create test directory
TEST_DIR="/tmp/oracle-test-$$"
mkdir -p "$TEST_DIR/app"
cd "$TEST_DIR"

# Copy pre-generated data files
echo "📋 Copying pre-generated data files..."
cp /home/user/terminus-tasks/tasks/cracked256/environment/hashes.txt "$TEST_DIR/app/"
cp /home/user/terminus-tasks/tasks/cracked256/environment/dictionary.txt "$TEST_DIR/app/"

echo "  ✓ hashes.txt: $(wc -l < "$TEST_DIR/app/hashes.txt") lines"
echo "  ✓ dictionary.txt: $(wc -l < "$TEST_DIR/app/dictionary.txt") lines"
echo ""

# Copy Oracle solution
cp /home/user/terminus-tasks/tasks/cracked256/solution/solve.sh "$TEST_DIR/"

echo "🔐 Running Oracle solution..."
echo "=================================================="

# Run the Oracle (with /app paths mapped to our test dir)
cd "$TEST_DIR"
# Use sed to replace /app with our test dir
sed "s|/app/|$TEST_DIR/app/|g" solve.sh > solve_test.sh
chmod +x solve_test.sh

# Run it
bash solve_test.sh

echo ""
echo "=================================================="
echo "📊 Results"
echo "=================================================="

if [ -f "$TEST_DIR/app/cracked.csv" ]; then
    LINES=$(wc -l < "$TEST_DIR/app/cracked.csv")
    CRACKED=$((LINES - 2))  # Minus canary and header

    echo "✅ Output file created: cracked.csv"
    echo "📈 Cracked: $CRACKED passwords"
    echo ""
    echo "First 15 lines:"
    head -15 "$TEST_DIR/app/cracked.csv"
    echo ""

    # Expected: 10 valid hashes in pre-generated data
    if [ "$CRACKED" -ge 10 ]; then
        echo "✅ SUCCESS: Cracked all 10 expected passwords!"
    elif [ "$CRACKED" -ge 8 ]; then
        echo "⚠️  PARTIAL: Cracked $CRACKED/10 (80%+)"
    else
        echo "❌ FAILURE: Only cracked $CRACKED/10 (< 80%)"
    fi
else
    echo "❌ FAILURE: No output file created"
    exit 1
fi

echo ""
echo "Cleaning up test directory: $TEST_DIR"
# rm -rf "$TEST_DIR"
echo "(Skipped cleanup for debugging - manually delete if needed)"
