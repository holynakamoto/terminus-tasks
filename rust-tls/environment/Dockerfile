FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install all build dependencies and LLVM versions in one layer to speed up builds
# Install Rust, multiple LLVM versions (13, 15 but NOT 14), and OpenSSL
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    pkg-config \
    libssl-dev \
    llvm-13-dev \
    llvm-15-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"

# Move OpenSSL to non-standard location to simulate a custom installation
# pkg-config won't find it there without proper configuration
RUN mkdir -p /opt/openssl/lib /opt/openssl/include \
    && ARCH=$(dpkg --print-architecture) \
    && LIB_DIR="/usr/lib/$(uname -m)-linux-gnu" \
    && if [ ! -d "$LIB_DIR" ]; then LIB_DIR="/usr/lib"; fi \
    && cp -r $LIB_DIR/libssl.so* /opt/openssl/lib/ 2>/dev/null || true \
    && cp -r $LIB_DIR/libcrypto.so* /opt/openssl/lib/ 2>/dev/null || true \
    && cp -r /usr/include/openssl /opt/openssl/include/ 2>/dev/null || true \
    && rm -f $LIB_DIR/libssl.so* \
    && rm -f $LIB_DIR/libcrypto.so* \
    && rm -rf /usr/include/openssl

WORKDIR /app

# Copy the broken Rust project
COPY project/ /app/

# The issues that need to be resolved:
# 1. LLVM-14 is NOT installed (only 13 and 15 are), but bindgen needs 14
# 2. OpenSSL libraries are in /opt/openssl but pkg-config can't find them
# 3. libclang.so is missing because LLVM-14-dev isn't installed
# 4. Need to set PKG_CONFIG_PATH and OPENSSL_DIR environment variables
# 5. Need to find correct libclang.so path after installing LLVM-14
