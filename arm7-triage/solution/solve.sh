#!/bin/bash
# CANARY_STRING_PLACEHOLDER

set -euo pipefail

cd /app

echo "Fixing ARMv7 cross-compilation setup..."

# Step 1: Verify cross-toolchain is installed
if ! command -v arm-linux-gnueabihf-gcc &> /dev/null; then
    echo "Error: arm-linux-gnueabihf-gcc not found"
    exit 1
fi

echo "✓ Cross-toolchain found: $(which arm-linux-gnueabihf-gcc)"

# Step 2: Set environment variables for Rust's target toolchain
# Write to multiple locations to ensure persistence across different shell types

# Create env file that will be sourced
cat > /etc/rust-arm-env.sh << 'EOF'
export CC_armv7_unknown_linux_gnueabihf="arm-linux-gnueabihf-gcc"
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER="arm-linux-gnueabihf-gcc"
EOF

# 1. Write to /etc/environment (used by PAM)
echo 'CC_armv7_unknown_linux_gnueabihf=arm-linux-gnueabihf-gcc' >> /etc/environment
echo 'CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER=arm-linux-gnueabihf-gcc' >> /etc/environment
# Set BASH_ENV so non-interactive bash shells source our env file
echo 'BASH_ENV=/etc/rust-arm-env.sh' >> /etc/environment

# 2. Write to /etc/profile.d/ (sourced by login shells)
cat > /etc/profile.d/rust-arm-env.sh << 'EOF'
export CC_armv7_unknown_linux_gnueabihf="arm-linux-gnueabihf-gcc"
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER="arm-linux-gnueabihf-gcc"
EOF

# 3. Write to ~/.bashrc (sourced by interactive non-login bash shells)
cat >> ~/.bashrc << 'EOF'
export CC_armv7_unknown_linux_gnueabihf="arm-linux-gnueabihf-gcc"
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER="arm-linux-gnueabihf-gcc"
EOF

# 4. Set BASH_ENV for the current session and future sessions
export BASH_ENV=/etc/rust-arm-env.sh

# 5. Export for current session
export CC_armv7_unknown_linux_gnueabihf="arm-linux-gnueabihf-gcc"
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER="arm-linux-gnueabihf-gcc"

echo "✓ Environment variables set"

# Step 3: Fix .cargo/config.toml
# The broken config has wrong target triple (armv7-unknown-linux-musleabihf instead of gnueabihf)
# Fix it to use the correct target triple and linker

cat > .cargo/config.toml << 'EOF'
[target.armv7-unknown-linux-gnueabihf]
linker = "arm-linux-gnueabihf-gcc"
EOF

echo "✓ Fixed .cargo/config.toml"

# Step 4: Add the ARM target if not already installed
if ! rustup target list --installed | grep -q "armv7-unknown-linux-gnueabihf"; then
    echo "Installing ARM target..."
    rustup target add armv7-unknown-linux-gnueabihf
fi

echo "✓ ARM target available"

# Step 5: Build the project
echo "Building ARM binary..."
cargo build --target armv7-unknown-linux-gnueabihf --release

echo "✓ Build completed successfully"

# Step 6: Verify the binary exists
BINARY_PATH="./target/armv7-unknown-linux-gnueabihf/release/sample-cli"
if [ ! -f "$BINARY_PATH" ]; then
    echo "Error: Binary not found at $BINARY_PATH"
    exit 1
fi

# Step 7: Test with QEMU
echo "Testing binary with QEMU..."
TEST_INPUT=5
EXPECTED_OUTPUT="Result: 10"

# Disable exit-on-error temporarily for better debugging
set +e

# Run with QEMU using -L option to specify the ARM library path
# Let QEMU handle memory management automatically
echo "Running: qemu-arm -L /usr/arm-linux-gnueabihf $BINARY_PATH $TEST_INPUT"
OUTPUT=$(qemu-arm -L /usr/arm-linux-gnueabihf "$BINARY_PATH" "$TEST_INPUT" 2>&1)
EXIT_CODE=$?

echo "Exit code: $EXIT_CODE"
echo "Raw output: '$OUTPUT'"

if [ $EXIT_CODE -ne 0 ]; then
    echo "Error: Binary execution failed with exit code $EXIT_CODE"
    set -e
    exit 1
fi

# Trim whitespace for comparison
OUTPUT_CLEAN=$(echo "$OUTPUT" | tr -d '\n\r' | xargs)
EXPECTED_CLEAN=$(echo "$EXPECTED_OUTPUT" | tr -d '\n\r' | xargs)

echo "Cleaned output: '$OUTPUT_CLEAN'"
echo "Expected output: '$EXPECTED_CLEAN'"

if [ "$OUTPUT_CLEAN" != "$EXPECTED_CLEAN" ]; then
    echo "Error: Output mismatch!"
    set -e
    exit 1
fi

set -e
echo "✓ Binary executed successfully"
echo "✓ Cross-compilation setup verified"
