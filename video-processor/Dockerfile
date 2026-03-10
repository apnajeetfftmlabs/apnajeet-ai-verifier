# [Filename: video-processor/Dockerfile]
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY processor.py .
COPY firebase_client.py .

# Create directory for uploads
RUN mkdir -p /tmp/uploads

# Expose port
EXPOSE 8080

# Start the application
CMD uvicorn processor:app --host 0.0.0.0 --port ${PORT:-8080}
