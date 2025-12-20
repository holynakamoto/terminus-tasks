#!/bin/bash
set -euo pipefail

# Ensure reward file is created even on early exit
trap 'if [ ! -f /logs/verifier/reward.txt ]; then echo 0 > /logs/verifier/reward.txt; fi' EXIT

cd /app

# Test 1: Verify environment variables are set
echo "Checking environment variables..."
if [ -z "${CC_armv7_unknown_linux_gnueabihf:-}" ]; then
    echo "✗ CC_armv7_unknown_linux_gnueabihf is not set"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

if [ -z "${CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER:-}" ]; then
    echo "✗ CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER is not set"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

echo "✓ Environment variables are set correctly"
echo "  CC_armv7_unknown_linux_gnueabihf=$CC_armv7_unknown_linux_gnueabihf"
echo "  CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER=$CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER"

# Test 2: Verify .cargo/config.toml exists and contains linker configuration
echo "Checking .cargo/config.toml..."
if [ ! -f ".cargo/config.toml" ]; then
    echo "✗ .cargo/config.toml not found"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

# Check if config.toml contains the armv7 target configuration
if ! grep -q "armv7-unknown-linux-gnueabihf" .cargo/config.toml; then
    echo "✗ .cargo/config.toml does not contain armv7-unknown-linux-gnueabihf configuration"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

if ! grep -q "linker" .cargo/config.toml; then
    echo "✗ .cargo/config.toml does not specify a linker"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

echo "✓ .cargo/config.toml is properly configured"

# Test 3: Build the ARM binary
echo "Building ARM binary..."
if ! cargo build --target armv7-unknown-linux-gnueabihf --release; then
    echo "✗ Build failed"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

echo "✓ Build succeeded"

# Verify the binary exists
BINARY_PATH="./target/armv7-unknown-linux-gnueabihf/release/sample-cli"
if [ ! -f "$BINARY_PATH" ]; then
    echo "✗ Binary not found at $BINARY_PATH"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

# Test 4: Run the binary with QEMU
# Use a deterministic test input (5) for verification
TEST_INPUT=5
EXPECTED_OUTPUT="Result: 10"

echo "Running binary with QEMU (input: $TEST_INPUT)..."

# Disable exit on error for better debugging
set +e

# Use QEMU with -L option to specify ARM library path
# Let QEMU handle memory management automatically
OUTPUT=$(qemu-arm -L /usr/arm-linux-gnueabihf "$BINARY_PATH" "$TEST_INPUT" 2>&1)
EXIT_CODE=$?

echo "Exit code: $EXIT_CODE"
echo "Raw output: '$OUTPUT'"

if [ $EXIT_CODE -ne 0 ]; then
    echo "✗ Binary execution failed with exit code $EXIT_CODE"
    echo 0 > /logs/verifier/reward.txt
    set -e
    exit 1
fi

# Trim whitespace when comparing
OUTPUT_CLEAN=$(echo "$OUTPUT" | tr -d '\n\r' | xargs)
EXPECTED_CLEAN=$(echo "$EXPECTED_OUTPUT" | tr -d '\n\r' | xargs)

echo "Cleaned output: '$OUTPUT_CLEAN'"
echo "Expected: '$EXPECTED_CLEAN'"

if [ "$OUTPUT_CLEAN" != "$EXPECTED_CLEAN" ]; then
    echo "✗ Output mismatch"
    echo 0 > /logs/verifier/reward.txt
    set -e
    exit 1
fi

set -e
echo "✓ Binary executed successfully"
echo "✓ Output matches expected"

# Test 5: Try a different input to ensure it's not hardcoded
TEST_INPUT_2=7
EXPECTED_OUTPUT_2="Result: 14"

echo "Running binary with QEMU (input: $TEST_INPUT_2)..."

set +e
# Use QEMU with -L option to specify ARM library path
# Let QEMU handle memory management automatically
OUTPUT_2=$(qemu-arm -L /usr/arm-linux-gnueabihf "$BINARY_PATH" "$TEST_INPUT_2" 2>&1)
EXIT_CODE_2=$?

echo "Exit code (test 2): $EXIT_CODE_2"
echo "Raw output (test 2): '$OUTPUT_2'"

if [ $EXIT_CODE_2 -ne 0 ]; then
    echo "✗ Binary execution failed with exit code $EXIT_CODE_2"
    echo 0 > /logs/verifier/reward.txt
    set -e
    exit 1
fi

# Trim whitespace when comparing
OUTPUT_2_CLEAN=$(echo "$OUTPUT_2" | tr -d '\n\r' | xargs)
EXPECTED_2_CLEAN=$(echo "$EXPECTED_OUTPUT_2" | tr -d '\n\r' | xargs)

echo "Cleaned output (test 2): '$OUTPUT_2_CLEAN'"
echo "Expected (test 2): '$EXPECTED_2_CLEAN'"

if [ "$OUTPUT_2_CLEAN" != "$EXPECTED_2_CLEAN" ]; then
    echo "✗ Output mismatch for second test"
    echo 0 > /logs/verifier/reward.txt
    set -e
    exit 1
fi

set -e

echo "✓ All tests passed"
echo 1 > /logs/verifier/reward.txt
