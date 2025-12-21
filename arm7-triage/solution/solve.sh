#!/usr/bin/env bash
set -euo pipefail

echo "=== [1/6] System info ==="
uname -a
rustc --version || true
cargo --version || true

echo "=== [2/6] Installing ARMv7 toolchain + QEMU ==="
apt-get update
apt-get install -y \
  gcc-arm-linux-gnueabihf \
  libc6-dev-armhf-cross \
  qemu-user \
  ca-certificates

echo "=== [3/6] Installing Rust target ==="
rustup target add armv7-unknown-linux-gnueabihf

echo "=== [4/6] Configuring cross-compilation env ==="
# Export for current shell
export CC_armv7_unknown_linux_gnueabihf=arm-linux-gnueabihf-gcc
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER=arm-linux-gnueabihf-gcc

# Persist for verifier (runs in separate shell)
mkdir -p /logs/verifier
# Harbor convention: verifier can source this file
cat > /logs/verifier/env.sh <<'EOF'
export CC_armv7_unknown_linux_gnueabihf=arm-linux-gnueabihf-gcc
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER=arm-linux-gnueabihf-gcc
EOF
chmod +x /logs/verifier/env.sh

# Also ensure bash sources it for non-interactive shells
# Modify /etc/bash.bashrc to source env.sh if it exists
if [[ -f /etc/bash.bashrc ]]; then
  if ! grep -q "/logs/verifier/env.sh" /etc/bash.bashrc; then
    echo 'if [[ -f /logs/verifier/env.sh ]]; then source /logs/verifier/env.sh; fi' >> /etc/bash.bashrc
  fi
fi

# Create Cargo config with static linking
mkdir -p /app/.cargo
cat > /app/.cargo/config.toml <<'EOF'
[target.armv7-unknown-linux-gnueabihf]
linker = "arm-linux-gnueabihf-gcc"
rustflags = [
  "-C", "target-feature=+crt-static",
  "-C", "link-arg=-static",
  "-C", "link-arg=-Wl,-static"
]

[env]
CC_armv7_unknown_linux_gnueabihf = "arm-linux-gnueabihf-gcc"
CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER = "arm-linux-gnueabihf-gcc"
EOF

echo "=== Effective Cargo config ==="
cat /app/.cargo/config.toml

echo "=== [5/6] Building project ==="
cd /app
cargo clean
cargo build --release --target armv7-unknown-linux-gnueabihf

BIN="./target/armv7-unknown-linux-gnueabihf/release/sample-cli"

if [[ ! -x "$BIN" ]]; then
  echo "ERROR: Binary not found or not executable: $BIN"
  exit 1
fi

# Verify binary is truly static
if readelf -l "$BIN" | grep -q INTERP; then
  echo "ERROR: Binary is not fully static (INTERP section found)"
  exit 1
fi

echo "=== [6/6] Running oracle validation via QEMU ==="

INPUT=5
EXPECTED="Result: 10"

# Run static binary directly under QEMU (no -L or -R needed)
OUTPUT=$(qemu-arm "$BIN" "$INPUT" 2>&1)
EXIT_CODE=$?

if [[ $EXIT_CODE -ne 0 ]]; then
  echo "ERROR: QEMU execution failed with exit code $EXIT_CODE"
  echo "QEMU output: $OUTPUT"
  exit 1
fi

echo "Program output: $OUTPUT"

if [[ "$OUTPUT" != "$EXPECTED" ]]; then
  echo "ERROR: Output mismatch"
  echo "Expected: $EXPECTED"
  echo "Got:      $OUTPUT"
  exit 1
fi

echo "=== ✅ ORACLE PASSED ==="
