#!/bin/bash
set -e

cd /app

# Step 1: Diagnose the issues - try building first to see errors
# This will reveal:
# - bindgen can't find libclang (wrong LLVM version installed)
# - openssl-sys can't find OpenSSL (in non-standard location)

# Step 2: Install the correct LLVM version (14, not 13 or 15)
# The error messages will indicate bindgen needs libclang, but the installed
# LLVM versions (13, 15) don't provide compatible libclang
apt-get update
apt-get install -y llvm-14-dev libclang-14-dev

# Step 3: Find where libclang.so is located for LLVM 14
# This requires discovering the actual path, not assuming
LIBCLANG_PATH=$(find /usr/lib/llvm-14 -name "libclang.so*" -type f 2>/dev/null | head -1 | xargs dirname 2>/dev/null)
if [ -z "$LIBCLANG_PATH" ] || [ ! -d "$LIBCLANG_PATH" ]; then
    # Try alternative locations based on architecture
    ARCH=$(uname -m)
    if [ -d "/usr/lib/llvm-14/lib" ]; then
        LIBCLANG_PATH="/usr/lib/llvm-14/lib"
    elif [ -d "/usr/lib/${ARCH}-linux-gnu/llvm-14/lib" ]; then
        LIBCLANG_PATH="/usr/lib/${ARCH}-linux-gnu/llvm-14/lib"
    elif [ -d "/usr/lib/x86_64-linux-gnu/llvm-14/lib" ]; then
        LIBCLANG_PATH="/usr/lib/x86_64-linux-gnu/llvm-14/lib"
    elif [ -d "/usr/lib/aarch64-linux-gnu/llvm-14/lib" ]; then
        LIBCLANG_PATH="/usr/lib/aarch64-linux-gnu/llvm-14/lib"
    else
        echo "Error: Could not find libclang.so for LLVM 14"
        exit 1
    fi
fi

# Step 4: Set environment variables for libclang (bindgen needs this)
export LIBCLANG_PATH="$LIBCLANG_PATH"
export LD_LIBRARY_PATH="$LIBCLANG_PATH:$LD_LIBRARY_PATH"

# Step 5: Configure OpenSSL - it's in /opt/openssl, need to tell pkg-config
# First, create pkg-config file since OpenSSL is in non-standard location
mkdir -p /opt/openssl/lib/pkgconfig

# Determine OpenSSL version from installed libraries
OPENSSL_VERSION=$(ls /opt/openssl/lib/libssl.so.* 2>/dev/null | head -1 | sed 's/.*libssl\.so\.//' || echo "3.0.0")

cat > /opt/openssl/lib/pkgconfig/openssl.pc << EOF
prefix=/opt/openssl
exec_prefix=\${prefix}
libdir=\${exec_prefix}/lib
includedir=\${prefix}/include

Name: OpenSSL
Description: Secure Sockets Layer and cryptography libraries
Version: ${OPENSSL_VERSION}
Requires: libssl libcrypto
Libs: -L\${libdir} -lssl -lcrypto
Cflags: -I\${includedir}
EOF

# Also create libssl.pc and libcrypto.pc for completeness
cat > /opt/openssl/lib/pkgconfig/libssl.pc << EOF
prefix=/opt/openssl
exec_prefix=\${prefix}
libdir=\${exec_prefix}/lib
includedir=\${prefix}/include

Name: OpenSSL-libssl
Description: Secure Sockets Layer and cryptography libraries
Version: ${OPENSSL_VERSION}
Requires: libcrypto
Libs: -L\${libdir} -lssl
Cflags: -I\${includedir}
EOF

cat > /opt/openssl/lib/pkgconfig/libcrypto.pc << EOF
prefix=/opt/openssl
exec_prefix=\${prefix}
libdir=\${exec_prefix}/lib
includedir=\${prefix}/include

Name: OpenSSL-libcrypto
Description: OpenSSL cryptography library
Version: ${OPENSSL_VERSION}
Libs: -L\${libdir} -lcrypto
Cflags: -I\${includedir}
EOF

# Step 6: Set environment variables for OpenSSL discovery
export PKG_CONFIG_PATH="/opt/openssl/lib/pkgconfig:$PKG_CONFIG_PATH"
export OPENSSL_DIR="/opt/openssl"
export OPENSSL_LIB_DIR="/opt/openssl/lib"
export OPENSSL_INCLUDE_DIR="/opt/openssl/include"

# Step 7: Set library path for runtime (needed when running the binary)
export LD_LIBRARY_PATH="/opt/openssl/lib:$LD_LIBRARY_PATH"

# Step 8: Verify pkg-config can now find OpenSSL
if ! pkg-config --exists openssl; then
    echo "Error: pkg-config still cannot find OpenSSL"
    exit 1
fi

# Step 9: Build the project
cargo build --release

# Step 10: Run the example to verify TLS works
cargo run --release --example https_client
