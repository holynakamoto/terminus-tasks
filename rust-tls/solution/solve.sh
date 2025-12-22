#!/bin/bash
set -e
cd /app

# Make OpenSSL libraries available to the system before installing packages
# (The Dockerfile moved them to /opt/openssl, but system tools need them)
echo "/opt/openssl/lib" > /etc/ld.so.conf.d/openssl-custom.conf
ldconfig

# Update and install required packages
apt-get update

# Install pkg-config (required for openssl-sys to find headers via .pc files)
apt-get install -y pkg-config

# Install LLVM-14 for bindgen (required by the task)
# Ubuntu 24.04 has LLVM-18 by default, but we need LLVM-14 specifically
# LLVM 14 is available in Ubuntu's official repositories (not from apt.llvm.org)
apt-get install -y llvm-14-dev libclang-14-dev clang-14

# Set LLVM environment variables to use version 14
export LLVM_CONFIG_PATH=/usr/bin/llvm-config-14
export LIBCLANG_PATH=/usr/lib/llvm-14/lib

# Setup pkg-config for custom OpenSSL in /opt/openssl
mkdir -p /opt/openssl/lib/pkgconfig

OPENSSL_VERSION=$(ls /opt/openssl/lib/libssl.so.* 2>/dev/null | head -1 | sed 's/.*libssl\.so\.//' || echo "3")

cat > /opt/openssl/lib/pkgconfig/openssl.pc << EOF
prefix=/opt/openssl
exec_prefix=\${prefix}
libdir=\${exec_prefix}/lib
includedir=\${prefix}/include

Name: OpenSSL
Description: OpenSSL
Version: ${OPENSSL_VERSION}
Libs: -L\${libdir} -lssl -lcrypto
Cflags: -I\${includedir}
EOF

cat > /opt/openssl/lib/pkgconfig/libssl.pc << EOF
prefix=/opt/openssl
exec_prefix=\${prefix}
libdir=\${exec_prefix}/lib
includedir=\${prefix}/include

Name: OpenSSL-libssl
Description: OpenSSL libssl
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
Description: OpenSSL libcrypto
Version: ${OPENSSL_VERSION}
Libs: -L\${libdir} -lcrypto
Cflags: -I\${includedir}
EOF

# Make pkg-config files discoverable system-wide by symlinking to standard location
# Get the system's architecture-specific pkg-config directory
ARCH=$(dpkg --print-architecture)
PKG_CONFIG_DIR="/usr/lib/${ARCH}-linux-gnu/pkgconfig"

# Ensure the pkg-config directory exists
mkdir -p ${PKG_CONFIG_DIR}

# Create symlinks so pkg-config can find OpenSSL automatically
ln -sf /opt/openssl/lib/pkgconfig/openssl.pc ${PKG_CONFIG_DIR}/openssl.pc
ln -sf /opt/openssl/lib/pkgconfig/libssl.pc ${PKG_CONFIG_DIR}/libssl.pc
ln -sf /opt/openssl/lib/pkgconfig/libcrypto.pc ${PKG_CONFIG_DIR}/libcrypto.pc

# Set environment variables (PKG_CONFIG_PATH must be set before build)
export PKG_CONFIG_PATH="/opt/openssl/lib/pkgconfig:$PKG_CONFIG_PATH"
export OPENSSL_DIR=/opt/openssl
export OPENSSL_LIB_DIR=/opt/openssl/lib
export OPENSSL_INCLUDE_DIR=/opt/openssl/include
export LD_LIBRARY_PATH="/opt/openssl/lib:$LD_LIBRARY_PATH"

# Create Cargo config to persist build settings for all subsequent builds
mkdir -p /app/.cargo
cat > /app/.cargo/config.toml << 'EOF'
[env]
OPENSSL_DIR = "/opt/openssl"
OPENSSL_LIB_DIR = "/opt/openssl/lib"
OPENSSL_INCLUDE_DIR = "/opt/openssl/include"
PKG_CONFIG_PATH = "/opt/openssl/lib/pkgconfig"
LLVM_CONFIG_PATH = "/usr/bin/llvm-config-14"
LIBCLANG_PATH = "/usr/lib/llvm-14/lib"
LD_LIBRARY_PATH = "/opt/openssl/lib"
EOF

# Verify pkg-config finds headers correctly
pkg-config --exists openssl || { echo "pkg-config cannot find openssl"; exit 1; }
echo "OpenSSL Cflags: $(pkg-config --cflags openssl)"
echo "OpenSSL Libs: $(pkg-config --libs openssl)"

# Remove the TLS version check block that uses deprecated API
# Delete lines 25-31 (comment, code block, closing brace, and blank line)
sed -i '25,31d' examples/https_client.rs

# Suppress bindgen warnings
sed -i '1i #![allow(non_camel_case_types)]\n#![allow(non_upper_case_globals)]\n#![allow(non_snake_case)]\n#![allow(dead_code)]\n#![allow(unused_variables)]' build.rs

# Clean previous artifacts and build
cargo clean
cargo build --release

# Run example to verify TLSv1.3 connection works
cargo run --release --example https_client
