FROM python:3.11.11-slim

# No additional dependencies needed - Python's hashlib is built-in

WORKDIR /app

# Keep container running so agent can execute commands
CMD ["tail", "-f", "/dev/null"]