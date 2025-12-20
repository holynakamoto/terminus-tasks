FROM rust:1.83-slim

# Install ARM cross-compilation toolchain and QEMU
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc-arm-linux-gnueabihf \
    binutils-arm-linux-gnueabihf \
    libc6-dev-armhf-cross \
    qemu-user-static \
    qemu-user \
    && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the source files (these are in the environment/ directory)
COPY Cargo.toml Cargo.lock* ./
COPY src ./src/

# Create the broken .cargo/config.toml
# This will be present in the image but can be overwritten by the agent
RUN mkdir -p .cargo && \
    printf '# Broken configuration - wrong target triple and missing linker config\n[target.armv7-unknown-linux-musleabihf]\nlinker = "arm-linux-gnueabihf-gcc"\n' > .cargo/config.toml

# Note: We intentionally do NOT copy solution/ or tests/ into the image
# The .cargo/config.toml should be broken/misconfigured initially
