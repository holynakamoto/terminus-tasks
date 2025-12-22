FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install all build dependencies in one layer to speed up builds
# Install Python, Rust, pkg-config, libssl-dev, and libclang-dev
RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    python3-pip \
    build-essential \
    pkg-config \
    libssl-dev \
    libclang-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv using pip (more reliable than curl in restricted environments)
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install uv

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal

ENV PATH="/root/.cargo/bin:${PATH}"

# Move OpenSSL to non-standard location to simulate a custom installation
# pkg-config won't find it there without proper configuration
RUN mkdir -p /opt/openssl/lib /opt/openssl/include \
    && ARCH=$(dpkg --print-architecture) \
    && LIB_DIR="/usr/lib/$(uname -m)-linux-gnu" \
    && if [ ! -d "$LIB_DIR" ]; then LIB_DIR="/usr/lib/${ARCH}-linux-gnu"; fi \
    && if [ ! -d "$LIB_DIR" ]; then LIB_DIR="/usr/lib"; fi \
    && find $LIB_DIR -name "libssl.so*" -exec cp -a {} /opt/openssl/lib/ \; \
    && find $LIB_DIR -name "libcrypto.so*" -exec cp -a {} /opt/openssl/lib/ \; \
    && cp -r /usr/include/openssl /opt/openssl/include/ \
    && ls -la /opt/openssl/include/openssl/ \
    && rm -f $LIB_DIR/libssl.so* \
    && rm -f $LIB_DIR/libcrypto.so* \
    && rm -rf /usr/include/openssl

WORKDIR /app

# Copy the broken Rust project
COPY project/ /app/
