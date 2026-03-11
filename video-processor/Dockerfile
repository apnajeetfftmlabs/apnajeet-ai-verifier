FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Test imports at build time
RUN python -c "import cv2, numpy, pytesseract, fastapi, firebase_admin"

COPY processor.py .
COPY firebase_client.py .

EXPOSE 8080

# Start uvicorn with debug logs
CMD ["uvicorn", "processor:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"]
