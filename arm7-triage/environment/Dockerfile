FROM rust:1.83-slim-bookworm

# Install ARM cross-compilation toolchain, QEMU, and build tools for preloader
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    gcc-arm-linux-gnueabihf \
    binutils-arm-linux-gnueabihf \
    libc6-dev-armhf-cross \
    qemu-user \
    file \
    binutils \
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
