#!/bin/bash
# Startup script for cracked256 task
# Generates data at container startup (not build time) for reproducibility

set -e

echo "🔐 Generating password hashes..."

# Generate data files (hashes.txt and dictionary.txt)
python3 /app/generate_data.py

# Remove the generation script to prevent agents from reading it
rm -f /app/generate_data.py

echo "✅ Environment ready"

# Keep container alive for harness
exec tail -f /dev/null
