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
  ca-certificates \
  file \
  binutils

echo "=== [3/6] Installing Rust targets (musl for static binary, glibc for dynamic) ==="
rustup target add armv7-unknown-linux-musleabihf
rustup target add armv7-unknown-linux-gnueabihf

echo "=== [4/6] Configuring cross-compilation env ==="
# Export for current shell (both musl and glibc targets)
export CC_armv7_unknown_linux_musleabihf=arm-linux-gnueabihf-gcc
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_MUSLEABIHF_LINKER=arm-linux-gnueabihf-gcc
export CC_armv7_unknown_linux_gnueabihf=arm-linux-gnueabihf-gcc
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER=arm-linux-gnueabihf-gcc

# Persist for verifier (runs in separate shell)
mkdir -p /logs/verifier
# Harbor convention: verifier can source this file
cat > /logs/verifier/env.sh <<'EOF'
export CC_armv7_unknown_linux_musleabihf=arm-linux-gnueabihf-gcc
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_MUSLEABIHF_LINKER=arm-linux-gnueabihf-gcc
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

# Create Cargo config for both musl (static) and glibc (dynamic) targets
# musl produces statically linked binaries - no sysroot needed, avoids QEMU address space issues
# glibc produces dynamically linked binaries - required by verifier tests
# Remove any existing broken config first
rm -rf /app/.cargo/config.toml /app/.cargo/config
mkdir -p /app/.cargo
cat > /app/.cargo/config.toml <<'EOF'
[target.armv7-unknown-linux-musleabihf]
linker = "arm-linux-gnueabihf-gcc"
rustflags = [
  "-C", "target-feature=+crt-static",
  "-C", "link-arg=-static",
  "-C", "link-arg=-no-pie"
]

[target.armv7-unknown-linux-gnueabihf]
linker = "arm-linux-gnueabihf-gcc"

[env]
CC_armv7_unknown_linux_musleabihf = "arm-linux-gnueabihf-gcc"
CARGO_TARGET_ARMV7_UNKNOWN_LINUX_MUSLEABIHF_LINKER = "arm-linux-gnueabihf-gcc"
CC_armv7_unknown_linux_gnueabihf = "arm-linux-gnueabihf-gcc"
CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER = "arm-linux-gnueabihf-gcc"
EOF

echo "=== Effective Cargo config ==="
cat /app/.cargo/config.toml

echo "=== [5/6] Building project (musl target - statically linked) ==="
cd /app
cargo clean
cargo build --release --target armv7-unknown-linux-musleabihf

BIN="./target/armv7-unknown-linux-musleabihf/release/sample-cli"

if [[ ! -x "$BIN" ]]; then
  echo "ERROR: Binary not found or not executable: $BIN"
  exit 1
fi

# Verify binary exists and check type (should be static)
echo "=== Checking binary ==="
file "$BIN"
echo "--- Binary type info ---"
readelf -h "$BIN" 2>/dev/null | head -5 || true
INTERP_CHECK=$(readelf -l "$BIN" 2>/dev/null | grep -A1 "INTERP" || true)
if [[ -n "$INTERP_CHECK" ]]; then
  echo "⚠ WARNING: Binary has dynamic dependencies (unexpected for musl static target)"
  echo "$INTERP_CHECK"
else
  echo "✓ Binary is statically linked (expected for musl target)"
fi

echo "=== [6/6] Running oracle validation via QEMU ==="

INPUT=5
EXPECTED="Result: 10"

# musl target produces statically linked binaries - no sysroot needed
# Static binaries work reliably in QEMU without address space gymnastics
echo "=== QEMU Environment Diagnostics ==="
echo "--- QEMU version ---"
qemu-arm --version || echo "WARNING: qemu-arm --version failed"
echo ""

echo "--- QEMU binary location ---"
which qemu-arm || echo "WARNING: qemu-arm not found in PATH"
ls -la $(which qemu-arm 2>/dev/null || echo "/usr/bin/qemu-arm") || true
echo ""

echo "--- Binary file info ---"
file "$BIN"
echo ""

echo "--- Binary readelf info ---"
readelf -h "$BIN" 2>/dev/null | head -10 || true
echo ""
readelf -l "$BIN" 2>/dev/null | grep -A5 "INTERP" || echo "✓ No INTERP segment (static binary)"
echo ""

echo "--- System info ---"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo ""

echo "=== Attempting QEMU execution (musl static binary - no sysroot needed) ==="

# Static binaries don't need -L flag or complex address space management
# They work reliably without preloader or -R flags
QEMU_CMD="qemu-arm $BIN $INPUT"
echo "Command: $QEMU_CMD (static binary - simple execution)"
echo ""

# musl produces statically linked binaries - simple and reliable in QEMU
set +e
QEMU_COMBINED=$($QEMU_CMD 2>&1)
EXIT_CODE=$?
set -e

echo "--- QEMU execution results ---"
echo "Exit code: $EXIT_CODE"
echo "Raw output: '$QEMU_COMBINED'"
echo ""

# Static binaries produce clean output - just use it directly
OUTPUT="$QEMU_COMBINED"

# Remove any shell trace artifacts if present
OUTPUT=$(echo "$OUTPUT" | sed 's/^[[:space:]]*//' | sed '/^$/d')

if [[ $EXIT_CODE -ne 0 ]]; then
  echo "✗ ERROR: QEMU execution failed with exit code $EXIT_CODE"
  echo ""

  echo "=== Trying basic diagnostics ==="

  echo "--- Checking if binary is executable ---"
  if [[ -x "$BIN" ]]; then
    echo "✓ Binary is executable"
  else
    echo "✗ Binary is NOT executable"
    chmod +x "$BIN"
    echo "Made executable, retrying..."
    set +e
    RETRY_OUTPUT=$(qemu-arm "$BIN" "$INPUT" 2>&1)
    RETRY_EXIT=$?
    set -e
    echo "Retry exit code: $RETRY_EXIT"
    echo "Retry output: '$RETRY_OUTPUT'"
    if [[ $RETRY_EXIT -eq 0 ]]; then
      OUTPUT="$RETRY_OUTPUT"
      EXIT_CODE=0
    fi
  fi

  if [[ $EXIT_CODE -ne 0 ]]; then
    echo ""
    echo "=== Using strace for diagnostics ==="
    if command -v strace &>/dev/null; then
      echo "Running with strace (last 30 lines):"
      strace -e trace=openat,execve,mmap2 qemu-arm "$BIN" "$INPUT" 2>&1 | tail -30 || true
    else
      echo "strace not available"
    fi

    echo ""
    echo "=== QEMU execution failed ==="
    echo "Final error output: $QEMU_COMBINED"
    exit 1
  fi
fi

# OUTPUT is already set above
echo "Program output: $OUTPUT"

if [[ "$OUTPUT" != "$EXPECTED" ]]; then
  echo "ERROR: Output mismatch"
  echo "Expected: $EXPECTED"
  echo "Got:      $OUTPUT"
  exit 1
fi

echo "=== ✅ ORACLE PASSED ==="
