#!/usr/bin/env bash
set -euo pipefail

# Ensure verifier log directory exists and reward file is created even if script exits early
mkdir -p /logs/verifier
trap 'if [ ! -f /logs/verifier/reward.txt ]; then echo 0 > /logs/verifier/reward.txt; fi' EXIT

echo "=== [1/5] Load verifier environment ==="
if [ -f /logs/verifier/env.sh ]; then
    # shellcheck disable=SC1091
    source /logs/verifier/env.sh
    echo "Loaded /logs/verifier/env.sh"
else
    echo "✗ /logs/verifier/env.sh not found"
    cat <<'EOF'
Create /logs/verifier/env.sh that exports:
  export CC_armv7_unknown_linux_gnueabihf=/path/to/arm-linux-gnueabihf-gcc
  export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER=/path/to/arm-linux-gnueabihf-gcc
EOF
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

# Verify environment variables
echo "Checking environment variables..."
missing=0
if [ -z "${CC_armv7_unknown_linux_gnueabihf:-}" ]; then
    echo "✗ CC_armv7_unknown_linux_gnueabihf is not set"
    missing=1
fi
if [ -z "${CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER:-}" ]; then
    echo "✗ CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER is not set"
    missing=1
fi
if [ "$missing" -ne 0 ]; then
    cat <<'EOF'
Environment configuration required.
Create /logs/verifier/env.sh that exports:
  export CC_armv7_unknown_linux_gnueabihf=/path/to/arm-linux-gnueabihf-gcc
  export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER=/path/to/arm-linux-gnueabihf-gcc
EOF
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
echo "✓ Environment variables are set"
echo " CC_armv7_unknown_linux_gnueabihf=$CC_armv7_unknown_linux_gnueabihf"
echo " CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER=$CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER"

echo "Validating compiler/linker paths..."
if [ ! -x "$CC_armv7_unknown_linux_gnueabihf" ]; then
    echo "✗ CC_armv7_unknown_linux_gnueabihf does not point to an executable file:"
    echo " $CC_armv7_unknown_linux_gnueabihf"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
if [ ! -x "$CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER" ]; then
    echo "✗ CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER does not point to an executable file:"
    echo " $CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
if ! "$CC_armv7_unknown_linux_gnueabihf" --version 2>/dev/null | grep -qi "arm-linux-gnueabihf"; then
    echo "✗ CC_armv7_unknown_linux_gnueabihf does not appear to be an arm-linux-gnueabihf-gcc toolchain:"
    echo " $CC_armv7_unknown_linux_gnueabihf"
    echo "Version output:"
    "$CC_armv7_unknown_linux_gnueabihf" --version 2>/dev/null || true
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
echo "✓ Compiler/linker paths are valid and executable"

echo "=== [2/5] Verify Cargo config ==="
if [ ! -f /app/.cargo/config.toml ]; then
    echo "✗ .cargo/config.toml not found"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
if ! grep -q "armv7-unknown-linux-gnueabihf" /app/.cargo/config.toml; then
    echo "✗ .cargo/config.toml missing armv7 glibc target"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
if ! grep -q "linker" /app/.cargo/config.toml; then
    echo "✗ .cargo/config.toml missing linker configuration"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
echo "✓ .cargo/config.toml is properly configured"

echo "=== [3/5] Verify ARMv7 binary exists (already built by agent) ==="
cd /app
ARM_BINARY_PATH="/app/target/armv7-unknown-linux-gnueabihf/release/sample-cli"
if [ ! -f "$ARM_BINARY_PATH" ]; then
    echo "✗ ARMv7 binary not found at $ARM_BINARY_PATH"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
echo "✓ ARMv7 binary exists"

# Verify it's actually an ARM binary
if ! file "$ARM_BINARY_PATH" | grep -q "ARM"; then
    echo "✗ Binary is not ARM architecture"
    file "$ARM_BINARY_PATH"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
echo "✓ ARMv7 binary is correct architecture"

echo "=== [4/5] Verify host binary exists (already built by agent) ==="
HOST_BINARY_PATH="/app/target/release/sample-cli"
if [ ! -f "$HOST_BINARY_PATH" ]; then
    echo "✗ Host binary not found at $HOST_BINARY_PATH"
    echo "Agent must build the host binary with 'cargo build --release' in solve.sh"
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi
echo "✓ Host binary exists"

echo "=== [5/5] Run host binary tests (test 1 + test 2) ==="
run_test () {
    local input="$1"
    local expected="$2"
    local label="$3"
    set +e
    local output
    output=$("$HOST_BINARY_PATH" "$input" 2>&1)
    local exit_code=$?
    set -e
    if [ $exit_code -ne 0 ]; then
        echo "✗ Host binary execution failed ($label)"
        echo "Output: $output"
        echo 0 > /logs/verifier/reward.txt
        exit 1
    fi
    local output_clean expected_clean
    output_clean=$(echo "$output" | tr -d '\n\r' | xargs)
    expected_clean=$(echo "$expected" | tr -d '\n\r' | xargs)
    echo "Filtered output ($label): '$output_clean'"
    echo "Expected output ($label): '$expected_clean'"
    if [ "$output_clean" != "$expected_clean" ]; then
        echo "✗ Output mismatch ($label)"
        echo "Expected: $expected_clean"
        echo "Got: $output_clean"
        echo 0 > /logs/verifier/reward.txt
        exit 1
    fi
    echo "✓ $label passed"
}
run_test 5 "Result: 10" "test 1"
run_test 7 "Result: 14" "test 2"

echo "=== All tests passed ==="
echo 1 > /logs/verifier/reward.txt
