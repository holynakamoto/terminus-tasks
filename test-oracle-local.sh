#!/bin/bash
# Test Oracle solution locally with pre-generated data
# Simulates Snorkel/Harbor environment

set -e

echo "🧪 Testing Oracle Solution Locally"
echo "===================================="
echo ""

# Create test directory
TEST_DIR="/tmp/oracle-test-local-$$"
mkdir -p "$TEST_DIR/app"
cd "$TEST_DIR"

echo "📋 Setting up test environment..."

# Copy pre-generated data files
cp /home/user/terminus-tasks/tasks/cracked256/environment/hashes.txt "$TEST_DIR/app/"
cp /home/user/terminus-tasks/tasks/cracked256/environment/dictionary.txt "$TEST_DIR/app/"

echo "  ✓ hashes.txt: $(wc -l < "$TEST_DIR/app/hashes.txt") lines"
echo "  ✓ dictionary.txt: $(wc -l < "$TEST_DIR/app/dictionary.txt") lines"

# Copy Oracle solution
cp /home/user/terminus-tasks/tasks/cracked256/solution/solve.sh "$TEST_DIR/"

# Replace /app paths with our test directory
sed "s|/app|$TEST_DIR/app|g" solve.sh > solve_local.sh
chmod +x solve_local.sh

echo ""
echo "🔐 Running Oracle solution..."
echo "===================================="

# Run the Oracle
bash solve_local.sh

echo ""
echo "===================================="
echo "📊 Validation Results"
echo "===================================="

if [ ! -f "$TEST_DIR/app/cracked.csv" ]; then
    echo "❌ FAILURE: No output file created"
    exit 1
fi

# Parse results
TOTAL_LINES=$(wc -l < "$TEST_DIR/app/cracked.csv")
CRACKED=$((TOTAL_LINES - 2))  # Minus canary and header

echo ""
echo "Output file analysis:"
echo "  - Total lines: $TOTAL_LINES"
echo "  - Header + canary: 2"
echo "  - Passwords cracked: $CRACKED"
echo ""

# Show output
echo "Output file contents:"
echo "----------------------------------------"
cat "$TEST_DIR/app/cracked.csv"
echo "----------------------------------------"
echo ""

# Validate expected passwords
EXPECTED=10
if [ "$CRACKED" -eq "$EXPECTED" ]; then
    echo "✅ SUCCESS: Cracked $CRACKED/$EXPECTED passwords (100%)"
    SUCCESS_RATE="100%"
elif [ "$CRACKED" -ge 8 ]; then
    echo "⚠️  PARTIAL: Cracked $CRACKED/$EXPECTED passwords (80%+)"
    SUCCESS_RATE="$(( (CRACKED * 100) / EXPECTED ))%"
else
    echo "❌ FAILURE: Only cracked $CRACKED/$EXPECTED passwords (< 80%)"
    SUCCESS_RATE="$(( (CRACKED * 100) / EXPECTED ))%"
    exit 1
fi

echo ""
echo "===================================="
echo "🎯 Final Results"
echo "===================================="
echo "  Oracle Success Rate: $SUCCESS_RATE"
echo "  Expected for Snorkel: 100%"
echo ""

if [ "$CRACKED" -eq "$EXPECTED" ]; then
    echo "  ✅ Oracle will PASS in Snorkel/Harbor (reward: 1.0)"
else
    echo "  ❌ Oracle will FAIL in Snorkel/Harbor (reward: 0.0)"
fi

echo ""
echo "Test directory: $TEST_DIR"
echo "(Not cleaned up for debugging)"
