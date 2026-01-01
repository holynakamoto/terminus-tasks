FROM rust:1.83-slim-bookworm

# Install ARM cross-compilation toolchain, QEMU, and build tools for preloader
RUN dpkg --add-architecture armhf && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    gcc-arm-linux-gnueabihf \
    binutils-arm-linux-gnueabihf \
    libc6-dev-armhf-cross \
    zlib1g-dev:armhf \
    pkg-config \
    qemu-user \
    file \
    binutils \
    perl \
    make \
    && \
    rm -rf /var/lib/apt/lists/*

# Build preloader to reserve low virtual address space for QEMU
# This helps QEMU work in restricted containers like CodeBuild
# Embed source directly in Dockerfile to avoid COPY path issues
RUN cat > /tmp/preload.c <<'PRELOAD_EOF' && \
    gcc -o /usr/local/bin/preload /tmp/preload.c && \
    rm /tmp/preload.c && \
    chmod +x /usr/local/bin/preload && \
    echo "✓ Preloader built successfully"
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/mman.h>
#include <errno.h>
#include <string.h>

#define RESERVE_SIZE (128 * 1024 * 1024)  // 128 MB — adjust down if needed

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: preload <command> [args...]\n");
        return 1;
    }

    // Try to mmap a chunk at low address (hint: 0x10000000)
    void *reserved = mmap((void*)0x10000000, RESERVE_SIZE,
                          PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);

    if (reserved == MAP_FAILED) {
        // If it fails, try smaller or ignore — not fatal
        fprintf(stderr, "Warning: Could not reserve low memory: %s\n", strerror(errno));
        fprintf(stderr, "         Continuing anyway (QEMU may still fail)\n");
    } else {
        fprintf(stderr, "Successfully reserved %d MB at %p\n", RESERVE_SIZE / (1024*1024), reserved);
        // Keep it reserved until exit
    }

    // Exec the real command (QEMU)
    execvp(argv[1], &argv[1]);

    perror("execvp failed");
    return 127;
}
PRELOAD_EOF

# Verify QEMU installation
# Note: musl target produces statically linked binaries - no sysroot needed
RUN echo "=== QEMU Installation Verification ===" && \
    qemu-arm --version && \
    which qemu-arm && \
    echo "=== QEMU setup complete (ready for musl static binaries) ==="

WORKDIR /app

# Install Rust targets for ARM cross-compilation
RUN rustup target add armv7-unknown-linux-musleabihf && \
    rustup target add armv7-unknown-linux-gnueabihf

# Copy the source files (these are in the environment/ directory)
COPY Cargo.toml Cargo.lock* ./
COPY src ./src/

# Create complete .cargo/config.toml
RUN mkdir -p .cargo && \
    cat > .cargo/config.toml <<'EOF'
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
PKG_CONFIG_ALLOW_CROSS = "1"
PKG_CONFIG_SYSROOT_DIR = "/usr/arm-linux-gnueabihf"
PKG_CONFIG_LIBDIR = "/usr/lib/arm-linux-gnueabihf/pkgconfig:/usr/share/pkgconfig"
PKG_CONFIG_PATH = "/usr/lib/arm-linux-gnueabihf/pkgconfig:/usr/share/pkgconfig"
EOF

# Create environment script for verifier
RUN mkdir -p /logs/verifier && \
    cat > /logs/verifier/env.sh <<'EOF'
# Ensure cargo/rustc are in PATH
export PATH="/usr/local/cargo/bin:$PATH"
export CC_armv7_unknown_linux_musleabihf="arm-linux-gnueabihf-gcc"
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_MUSLEABIHF_LINKER="arm-linux-gnueabihf-gcc"
export CC_armv7_unknown_linux_gnueabihf="arm-linux-gnueabihf-gcc"
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER="arm-linux-gnueabihf-gcc"
export PKG_CONFIG_ALLOW_CROSS=1
export PKG_CONFIG_SYSROOT_DIR=/usr/arm-linux-gnueabihf
export PKG_CONFIG_LIBDIR=/usr/lib/arm-linux-gnueabihf/pkgconfig:/usr/share/pkgconfig
export PKG_CONFIG_PATH=/usr/lib/arm-linux-gnueabihf/pkgconfig:/usr/share/pkgconfig
EOF

RUN chmod +x /logs/verifier/env.sh
