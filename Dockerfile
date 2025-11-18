# Use Python 3.11 runtime as base image
FROM python:3.11-slim

# Set working directory in container
WORKDIR /app

# Ensure stdout/stderr unbuffered for real-time logs in Cloud Run
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system dependencies (if needed)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port 8080 (Cloud Run default)
EXPOSE 8080

# Run the Flask application using gunicorn
# gunicorn is production-ready WSGI server
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app