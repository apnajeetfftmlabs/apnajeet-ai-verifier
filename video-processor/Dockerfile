FROM python:3.11-slim

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

# Debug: Print env and start app with full logging
CMD ["sh", "-c", "\
    echo '=== STARTING UP ==='; \
    echo 'PORT: ' $PORT; \
    echo 'FIREBASE_DATABASE_URL: ' $FIREBASE_DATABASE_URL; \
    echo 'Starting uvicorn...'; \
    uvicorn processor:app --host 0.0.0.0 --port ${PORT:-8080} --log-level debug \
"]
