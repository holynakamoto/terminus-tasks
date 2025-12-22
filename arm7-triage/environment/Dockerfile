FROM rust:1.83-slim-bookworm

# Install ARM cross-compilation toolchain and QEMU
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc-arm-linux-gnueabihf \
    binutils-arm-linux-gnueabihf \
    libc6-dev-armhf-cross \
    qemu-user \
    file \
    binutils \
    && \
    rm -rf /var/lib/apt/lists/*

# Verify QEMU installation
# Note: musl target produces statically linked binaries - no sysroot needed
RUN echo "=== QEMU Installation Verification ===" && \
    qemu-arm --version && \
    which qemu-arm && \
    echo "=== QEMU setup complete (ready for musl static binaries) ==="

WORKDIR /app

# Copy the source files (these are in the environment/ directory)
COPY Cargo.toml Cargo.lock* ./
COPY src ./src/

# Create an incomplete .cargo/config.toml
# This will be present in the image but will be properly configured by solve.sh
# The config is "broken" because it's missing rustflags for static linking
RUN mkdir -p .cargo && \
    printf '# Incomplete configuration - missing rustflags for static linking\n# solve.sh will replace this with a complete musl configuration\n[target.armv7-unknown-linux-musleabihf]\nlinker = "arm-linux-gnueabihf-gcc"\n' > .cargo/config.toml

# Note: We intentionally do NOT copy solution/ or tests/ into the image
# The .cargo/config.toml is intentionally incomplete - the agent must fix it
