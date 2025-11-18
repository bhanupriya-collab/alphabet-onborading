# Cloud Run Dockerfile for email scheduler (polling Google Sheets)
# Base lightweight Python image
FROM python:3.11-slim

# Ensure stdout/stderr unbuffered for real-time logs
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Set working directory
WORKDIR /app

# Install system deps (optional: add lib dependencies if needed later)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY root_agent/ root_agent/

# Default command (can be overridden in Cloud Run revision settings)
CMD ["python", "root_agent/tools/utils/email_scheduler.py"]
