FROM ubuntu:24.04

# Cache buster - forces rebuild when instruction.md changes
ARG CACHE_BUST=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y -qq \
    tshark \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Note: Using --break-system-packages is safe in Docker containers
RUN pip3 install --no-cache-dir --break-system-packages scapy==2.5.0

WORKDIR /app