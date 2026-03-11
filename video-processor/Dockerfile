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

# Copy requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code
COPY processor.py .
COPY firebase_client.py .

# Debug: Check imports
RUN python -c "import cv2, numpy, pytesseract, firebase_admin; print('✅ All imports OK')"
RUN python -c "from firebase_client import FirebaseClient; print('✅ FirebaseClient import OK')"

# Test Firebase init (will fail if env vars missing, but we catch it)
RUN python -c "import os; print(f'FIREBASE_DATABASE_URL: {os.getenv(\"FIREBASE_DATABASE_URL\", \"NOT SET\")}')"

# Start with maximum logging
CMD uvicorn processor:app --host 0.0.0.0 --port 8080 --log-level debug
