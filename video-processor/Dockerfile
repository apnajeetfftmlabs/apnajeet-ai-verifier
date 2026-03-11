FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY processor.py .
COPY firebase_client.py .

# Debug: print environment and files
RUN echo "=== CONTAINER CONTENTS ===" && ls -la

# Start with debug output
CMD uvicorn processor:app --host 0.0.0.0 --port 8080 --log-level debug
