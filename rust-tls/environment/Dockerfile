FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install all build dependencies in one layer to speed up builds
# Install Rust, pkg-config, libssl-dev, and libclang-dev
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    pkg-config \
    libssl-dev \
    libclang-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (make toolchain available in subsequent RUNs and in interactive shells)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal

ENV CARGO_HOME=/root/.cargo
ENV RUSTUP_HOME=/root/.rustup
ENV PATH="/root/.cargo/bin:${PATH}"

# Pre-flight: ensure cargo/rustc are usable (helps fail fast if rustup didn't install correctly)
RUN cargo --version && rustc --version

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

# Copy the Rust project as a directory.
# This avoids brittle builds when task packagers/build contexts drop "loose" files
# (e.g., wrapper.h) and keeps the image layout identical to the repo.
COPY project/ /app/

# Ensure wrapper.h exists during the image build.
# Prefer the repo-provided file if present, but fall back to a minimal header.
RUN if [ -f /app/wrapper.h ]; then \
    echo "wrapper.h already present in image layer"; \
    else \
    printf '%s\n' '#include <unistd.h>' > /app/wrapper.h; \
    fi
