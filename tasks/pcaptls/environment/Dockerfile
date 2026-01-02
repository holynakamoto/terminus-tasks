FROM ubuntu:24.04

# Self-busting cache: COPY this file to invalidate cache when cache_bust.txt changes
# To force a rebuild, increment the number in cache_bust.txt and commit
COPY cache_bust.txt /tmp/cache_bust.txt

# Canary hook retained for external systems to rewrite if needed
# CANARY_STRING_PLACEHOLDER

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