# [Filename: Dockerfile] - PRODUCTION READY
FROM python:3.11-slim

WORKDIR /app

# Minimal system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Core requirements only
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/uploads

# Skip non-root user for speed (add later)
# USER 1000

# Hardcoded port
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
