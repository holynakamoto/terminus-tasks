FROM python:3.11.11-slim

# No additional dependencies needed - Python's hashlib is built-in

WORKDIR /app

# Copy data generation script
COPY generate_data.py /app/generate_data.py
RUN chmod +x /app/generate_data.py

# Generate test data on container startup
RUN python3 /app/generate_data.py

# Keep container running so agent can execute commands
CMD ["tail", "-f", "/dev/null"]