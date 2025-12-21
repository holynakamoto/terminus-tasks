#!/usr/bin/env bash
set -euo pipefail

# Ensure reward file exists even if script exits early
trap 'if [ ! -f /logs/verifier/reward.txt ]; then echo 0 > /logs/verifier/reward.txt; fi' EXIT

echo "=== [1/6] Load Harbor verifier environment ==="

# Source environment variables exported by solve.sh
if [ -f /logs/verifier/env.sh ]; then
    source /logs/verifier/env.sh
    echo "Loaded /logs/verifier/env.sh"
else
    echo "Warning: /logs/verifier/env.sh not found"
fi

# Verify environment variables
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

echo "✓ Environment variables are set"
echo "  CC_armv7_unknown_linux_gnueabihf=$CC_armv7_unknown_linux_gnueabihf"
echo "  CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER=$CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER"

echo "=== [2/6] Verify Cargo config ==="
if [ ! -f /app/.cargo/config.toml ]; then
    echo "✗ .cargo/config.toml not found"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

if ! grep -q "armv7-unknown-linux-gnueabihf" /app/.cargo/config.toml; then
    echo "✗ .cargo/config.toml missing armv7 target"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

if ! grep -q "linker" /app/.cargo/config.toml; then
    echo "✗ .cargo/config.toml missing linker configuration"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

echo "✓ .cargo/config.toml is properly configured"

echo "=== [3/6] Build ARMv7 static binary ==="
cd /app

cargo clean
if ! cargo build --release --target armv7-unknown-linux-gnueabihf; then
    echo "✗ Build failed"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

BINARY_PATH="/app/target/armv7-unknown-linux-gnueabihf/release/sample-cli"
if [ ! -f "$BINARY_PATH" ]; then
    echo "✗ Binary not found at $BINARY_PATH"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

echo "✓ Binary built successfully"

echo "=== [4/6] Run binary under QEMU (test 1) ==="
TEST_INPUT=5
EXPECTED_OUTPUT="Result: 10"

set +e
OUTPUT=$(qemu-arm -L /usr/arm-linux-gnueabihf "$BINARY_PATH" "$TEST_INPUT" 2>&1)
EXIT_CODE=$?

# Retry with smaller -R if memory reservation fails
if [ $EXIT_CODE -ne 0 ] && echo "$OUTPUT" | grep -q "Unable to reserve.*bytes"; then
    for R_VALUE in "0x40000000" "0x20000000" "0x10000000" "0x8000000"; do
        echo "Memory reservation failed, retrying with -R $R_VALUE..."
        OUTPUT=$(qemu-arm -L /usr/arm-linux-gnueabihf -R "$R_VALUE" "$BINARY_PATH" "$TEST_INPUT" 2>&1)
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 0 ] || ! echo "$OUTPUT" | grep -q "Unable to reserve.*bytes"; then
            break
        fi
    done
fi

if [ $EXIT_CODE -ne 0 ]; then
    echo "✗ Binary execution failed (test 1)"
    echo "Output: $OUTPUT"
    echo 0 > /logs/verifier/reward.txt
    set -e
    exit 1
fi

OUTPUT_CLEAN=$(echo "$OUTPUT" | tr -d '\n\r' | xargs)
EXPECTED_CLEAN=$(echo "$EXPECTED_OUTPUT" | tr -d '\n\r' | xargs)
if [ "$OUTPUT_CLEAN" != "$EXPECTED_CLEAN" ]; then
    echo "✗ Output mismatch (test 1)"
    echo "Expected: $EXPECTED_CLEAN"
    echo "Got:      $OUTPUT_CLEAN"
    echo 0 > /logs/verifier/reward.txt
    set -e
    exit 1
fi

echo "✓ Test 1 passed"

echo "=== [5/6] Run binary under QEMU (test 2) ==="
TEST_INPUT_2=7
EXPECTED_OUTPUT_2="Result: 14"

OUTPUT_2=$(qemu-arm -L /usr/arm-linux-gnueabihf "$BINARY_PATH" "$TEST_INPUT_2" 2>&1)
EXIT_CODE_2=$?

if [ $EXIT_CODE_2 -ne 0 ] && echo "$OUTPUT_2" | grep -q "Unable to reserve.*bytes"; then
    for R_VALUE in "0x40000000" "0x20000000" "0x10000000" "0x8000000"; do
        echo "Memory reservation failed, retrying with -R $R_VALUE..."
        OUTPUT_2=$(qemu-arm -L /usr/arm-linux-gnueabihf -R "$R_VALUE" "$BINARY_PATH" "$TEST_INPUT_2" 2>&1)
        EXIT_CODE_2=$?
        if [ $EXIT_CODE_2 -eq 0 ] || ! echo "$OUTPUT_2" | grep -q "Unable to reserve.*bytes"; then
            break
        fi
    done
fi

if [ $EXIT_CODE_2 -ne 0 ]; then
    echo "✗ Binary execution failed (test 2)"
    echo "Output: $OUTPUT_2"
    echo 0 > /logs/verifier/reward.txt
    set -e
    exit 1
fi

OUTPUT_2_CLEAN=$(echo "$OUTPUT_2" | tr -d '\n\r' | xargs)
EXPECTED_2_CLEAN=$(echo "$EXPECTED_OUTPUT_2" | tr -d '\n\r' | xargs)
if [ "$OUTPUT_2_CLEAN" != "$EXPECTED_2_CLEAN" ]; then
    echo "✗ Output mismatch (test 2)"
    echo "Expected: $EXPECTED_2_CLEAN"
    echo "Got:      $OUTPUT_2_CLEAN"
    echo 0 > /logs/verifier/reward.txt
    set -e
    exit 1
fi

echo "✓ Test 2 passed"

echo "=== [6/6] All tests passed ==="
echo 1 > /logs/verifier/reward.txt
set -e
