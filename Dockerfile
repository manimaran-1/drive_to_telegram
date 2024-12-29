# Dockerfile
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create directory for temporary file storage
RUN mkdir -p /app/tmp

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY fargate.py .

# Set environment for temporary files
ENV TEMP_DIR=/app/tmp

# Command to run the service
CMD ["python", "fargate.py"]