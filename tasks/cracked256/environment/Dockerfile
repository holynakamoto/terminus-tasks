FROM python:3.11.11-slim

# Build optimization: Pre-built images cached in GHCR for faster CI runs
# Last updated: 2026-01-21


WORKDIR /app

# Copy data generation script and run at build time to bake data into image
# Script is removed after generation to prevent agents from reading plaintext passwords
COPY generate_data.py /app/generate_data.py
RUN python3 /app/generate_data.py && rm /app/generate_data.py

# Keep container running so agent can execute commands
CMD ["tail", "-f", "/dev/null"]