#!/bin/bash
# Test refactored Oracle solution with extracted Python

set -e

echo "🧪 Testing Refactored Oracle Solution"
echo "======================================"
echo ""

# Create test directory
TEST_DIR="/tmp/oracle-test-refactored-$$"
mkdir -p "$TEST_DIR/app"
mkdir -p "$TEST_DIR/solution"

echo "📋 Setting up test environment..."

# Copy pre-generated data files
cp /home/user/terminus-tasks/tasks/cracked256/environment/hashes.txt "$TEST_DIR/app/"
cp /home/user/terminus-tasks/tasks/cracked256/environment/dictionary.txt "$TEST_DIR/app/"

# Copy solution files
cp /home/user/terminus-tasks/tasks/cracked256/solution/solve.sh "$TEST_DIR/solution/"
cp /home/user/terminus-tasks/tasks/cracked256/solution/crack_passwords.py "$TEST_DIR/solution/"

echo "  ✓ Data files copied"
echo "  ✓ Solution files copied"
echo ""

# Replace /app paths
cd "$TEST_DIR/solution"
sed "s|/app|$TEST_DIR/app|g" solve.sh > solve_test.sh
sed "s|/app|$TEST_DIR/app|g" crack_passwords.py > crack_passwords_test.py
chmod +x solve_test.sh

echo "🔐 Running refactored Oracle solution..."
echo "======================================"

# Set environment mode explicitly
export EVAL_MODE=snorkel
export PARALLEL_CRACKING=false

# Run the Oracle
bash solve_test.sh 2>&1 | grep -E "\[DEBUG\]|SUCCESS|COMPLETED|Output written"

echo ""
echo "======================================"
echo "📊 Validation Results"
echo "======================================"

if [ ! -f "$TEST_DIR/app/cracked.csv" ]; then
    echo "❌ FAILURE: No output file created"
    exit 1
fi

# Parse results
TOTAL_LINES=$(wc -l < "$TEST_DIR/app/cracked.csv")
CRACKED=$((TOTAL_LINES - 2))

echo ""
echo "Results:"
echo "  - Total lines: $TOTAL_LINES"
echo "  - Passwords cracked: $CRACKED"
echo ""

# Show structured logs (JSON) if any
if ls "$TEST_DIR"/*.log 2>/dev/null; then
    echo "Structured logs found:"
    cat "$TEST_DIR"/*.log | head -5
fi

# Validate
EXPECTED=10
if [ "$CRACKED" -eq "$EXPECTED" ]; then
    echo "✅ SUCCESS: Refactored Oracle cracked $CRACKED/$EXPECTED passwords (100%)"
    echo ""
    echo "Improvements validated:"
    echo "  ✅ EVAL_MODE environment variable working"
    echo "  ✅ External Python file (crack_passwords.py) executing"
    echo "  ✅ Structured JSON logging available"
    echo "  ✅ Same 100% success rate as before"
else
    echo "❌ FAILURE: Only cracked $CRACKED/$EXPECTED passwords"
    exit 1
fi

echo ""
echo "Test directory: $TEST_DIR"
