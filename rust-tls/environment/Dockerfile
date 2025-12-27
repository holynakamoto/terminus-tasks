FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install ALL necessary build dependencies (including python3 for completeness)
# CRITICAL: Must install LLVM 14 specifically for bindgen
RUN apt-get update && apt-get install -y \
    curl \
    python3 \
    python3-pip \
    build-essential \
    pkg-config \
    libssl-dev \
    llvm-14-dev \
    libclang-14-dev \
    clang-14 \
    strace \
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

# Critical fallback: create minimal wrapper.h if the task package doesn't provide it
RUN if [ ! -f /app/wrapper.h ]; then \
        printf '%s\n' \
            '#ifndef WRAPPER_H' \
            '#define WRAPPER_H' \
            '#include <unistd.h>' \
            '#include <stdint.h>' \
            '#include <stddef.h>' \
            '#endif' > /app/wrapper.h && \
        echo "Created fallback wrapper.h"; \
    else \
        echo "wrapper.h already exists"; \
    fi
