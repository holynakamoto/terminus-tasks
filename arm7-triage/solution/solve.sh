#!/usr/bin/env bash
set -euo pipefail

echo "=== [1/6] System info ==="
uname -a

# Ensure Rust toolchain is available (some task images omit Rust binaries even if based on a Rust tag).
# Install via rustup if rustc/cargo are missing, then ensure PATH is set for this script.
if ! command -v rustc >/dev/null 2>&1 || ! command -v cargo >/dev/null 2>&1 || ! command -v rustup >/dev/null 2>&1; then
  echo "Rust toolchain not found; installing via rustup..."
  apt-get update
  apt-get install -y --no-install-recommends ca-certificates curl
  curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable --no-modify-path
fi

# rustup may install into /usr/local/cargo/bin (common in container images) or ~/.cargo/bin (default).
# Prefer /usr/local/cargo/bin when present, otherwise fall back to ~/.cargo/bin.
if [ -d "/usr/local/cargo/bin" ]; then
  export PATH="/usr/local/cargo/bin:${PATH}"
elif [ -d "${HOME}/.cargo/bin" ]; then
  export PATH="${HOME}/.cargo/bin:${PATH}"
else
  # Last-ditch: keep prior PATH; rustc/cargo checks below will fail with a clear error.
  export PATH="${PATH}"
fi

rustc --version
cargo --version
rustup --version

echo "=== [2/6] Installing ARMv7 toolchain (build-only) ==="
apt-get update
apt-get install -y \
  gcc-arm-linux-gnueabihf \
  libc6-dev-armhf-cross \
  ca-certificates \
  file \
  binutils

# Resolve absolute path to ARM GCC for verifier checks (expects an executable file path).
ARM_GCC_PATH="$(command -v arm-linux-gnueabihf-gcc || true)"
if [[ -z "${ARM_GCC_PATH}" ]]; then
  echo "ERROR: arm-linux-gnueabihf-gcc not found on PATH after install"
  exit 1
fi
echo "Found ARM GCC at: ${ARM_GCC_PATH}"

echo "=== [3/6] Installing Rust targets (ARMv7 for build-only validation) ==="
rustup target add armv7-unknown-linux-musleabihf
rustup target add armv7-unknown-linux-gnueabihf

echo "=== [4/6] Configuring cross-compilation env ==="
# Export for current shell (both musl and glibc targets) using absolute path
export CC_armv7_unknown_linux_musleabihf="$ARM_GCC_PATH"
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_MUSLEABIHF_LINKER="$ARM_GCC_PATH"
export CC_armv7_unknown_linux_gnueabihf="$ARM_GCC_PATH"
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER="$ARM_GCC_PATH"

# Persist for verifier (runs in separate shell)
mkdir -p /logs/verifier
# Harbor convention: verifier can source this file
cat > /logs/verifier/env.sh <<EOF
# Add Rust binaries to PATH
export PATH="/usr/local/cargo/bin:\${PATH}"

# Cross-compilation environment variables
export CC_armv7_unknown_linux_musleabihf="$ARM_GCC_PATH"
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_MUSLEABIHF_LINKER="$ARM_GCC_PATH"
export CC_armv7_unknown_linux_gnueabihf="$ARM_GCC_PATH"
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER="$ARM_GCC_PATH"
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
# We keep this config because the verifier checks for the ARMv7 glibc target/linker.
rm -rf /app/.cargo/config.toml /app/.cargo/config
mkdir -p /app/.cargo
cat > /app/.cargo/config.toml <<EOF
[target.armv7-unknown-linux-musleabihf]
linker = "$ARM_GCC_PATH"
rustflags = [
  "-C", "target-feature=+crt-static",
  "-C", "link-arg=-static",
  "-C", "link-arg=-no-pie"
]

[target.armv7-unknown-linux-gnueabihf]
linker = "$ARM_GCC_PATH"

[env]
CC_armv7_unknown_linux_musleabihf = "$ARM_GCC_PATH"
CARGO_TARGET_ARMV7_UNKNOWN_LINUX_MUSLEABIHF_LINKER = "$ARM_GCC_PATH"
CC_armv7_unknown_linux_gnueabihf = "$ARM_GCC_PATH"
CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER = "$ARM_GCC_PATH"
EOF

echo "=== Effective Cargo config ==="
cat /app/.cargo/config.toml

echo "=== [5/6] Host build + run (correctness validation; no QEMU) ==="
cd /app
cargo clean
cargo build --release

HOST_BIN="./target/release/sample-cli"
if [[ ! -x "$HOST_BIN" ]]; then
  echo "ERROR: Host binary not found or not executable: $HOST_BIN"
  exit 1
fi

INPUT=5
EXPECTED="Result: 10"

echo "Running host binary: $HOST_BIN $INPUT"
set +e
HOST_OUT=$("$HOST_BIN" "$INPUT" 2>&1)
HOST_EXIT=$?
set -e

echo "Host exit code: $HOST_EXIT"
echo "Host raw output: '$HOST_OUT'"

if [[ $HOST_EXIT -ne 0 ]]; then
  echo "ERROR: Host execution failed"
  exit 1
fi

HOST_OUT_CLEAN=$(echo "$HOST_OUT" | tr -d '\n\r' | xargs)
EXPECTED_CLEAN=$(echo "$EXPECTED" | tr -d '\n\r' | xargs)

if [[ "$HOST_OUT_CLEAN" != "$EXPECTED_CLEAN" ]]; then
  echo "ERROR: Output mismatch (host run)"
  echo "Expected: $EXPECTED_CLEAN"
  echo "Got:      $HOST_OUT_CLEAN"
  exit 1
fi

echo "✓ Host correctness check passed"

echo "=== [6/6] ARMv7 build-only validation (no execution) ==="
# Build ARMv7 artifacts to ensure cross-compilation works in the environment,
# but do not execute them (avoids qemu-user VM mapping restrictions in CodeBuild).
cargo build --release --target armv7-unknown-linux-musleabihf
ARM_MUSL_BIN="./target/armv7-unknown-linux-musleabihf/release/sample-cli"

if [[ ! -f "$ARM_MUSL_BIN" ]]; then
  echo "ERROR: ARMv7 musl binary not found: $ARM_MUSL_BIN"
  exit 1
fi

echo "=== Checking ARMv7 musl binary ==="
file "$ARM_MUSL_BIN"
readelf -h "$ARM_MUSL_BIN" 2>/dev/null | head -10 || true
readelf -l "$ARM_MUSL_BIN" 2>/dev/null | grep -A5 "INTERP" || echo "✓ No INTERP segment (static binary)"

# Also ensure the glibc target builds (verifier expects this toolchain/config).
cargo build --release --target armv7-unknown-linux-gnueabihf
ARM_GLIBC_BIN="./target/armv7-unknown-linux-gnueabihf/release/sample-cli"

if [[ ! -f "$ARM_GLIBC_BIN" ]]; then
  echo "ERROR: ARMv7 glibc binary not found: $ARM_GLIBC_BIN"
  exit 1
fi

echo "=== Checking ARMv7 glibc binary ==="
file "$ARM_GLIBC_BIN"
readelf -h "$ARM_GLIBC_BIN" 2>/dev/null | head -10 || true
readelf -l "$ARM_GLIBC_BIN" 2>/dev/null | grep -A5 "INTERP" || echo "Note: No INTERP segment found (unexpected for glibc target, but not fatal here)"

echo "=== ✅ ORACLE PASSED ==="
