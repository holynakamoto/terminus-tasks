FROM rust:1.83-slim-bookworm

# Install basic build tools, Python, and uv for testing
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    curl \
    ca-certificates \
    && \
    rm -rf /var/lib/apt/lists/*

# Install uv (required by Harbor for test runner)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx

WORKDIR /app

# Install Rust (already included in rust:1.83 image)
# Set up the broken project

# Copy the broken source files
COPY Cargo.toml Cargo.lock ./
COPY src ./src/

# Verify the broken code doesn't compile (expected to fail)
RUN echo "=== Attempting to compile broken code (expected to fail) ===" && \
    (cargo build --release 2>&1 | head -20 || true) && \
    echo "=== As expected, compilation failed ===" && \
    echo "Agent must fix these errors to complete the task"

# The agent will need to:
# 1. Fix lifetime errors
# 2. Implement required traits
# 3. Add proper error handling
# 4. Build successfully with: cargo build --release
