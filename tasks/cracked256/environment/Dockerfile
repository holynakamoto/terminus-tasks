FROM python:3.11.11-slim

# No additional dependencies needed - Python's hashlib is built-in

WORKDIR /app

# Copy data generation script and run at build time to bake data into image
# Note: Script kept in image (~4KB) for debugging/reference - can add cleanup if size matters
COPY generate_data.py /app/generate_data.py
RUN python3 /app/generate_data.py

# Keep container running so agent can execute commands
CMD ["tail", "-f", "/dev/null"]