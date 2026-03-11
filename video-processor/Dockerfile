FROM python:3.11-slim

# Install system dependencies including Tesseract
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Verify tesseract installation
RUN tesseract --version

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY processor.py .
COPY firebase_client.py .

# Test that tesseract works
RUN python -c "import pytesseract; print('✅ Tesseract path:', pytesseract.get_tesseract_version())"

CMD uvicorn processor:app --host 0.0.0.0 --port ${PORT:-8080}
