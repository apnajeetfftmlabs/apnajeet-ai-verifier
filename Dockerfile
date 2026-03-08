FROM python:3.11-slim

# System dependencies install kar
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    libleptonica-dev \
    build-essential \
    swig \
    libpcre3-dev \
    zlib1g-dev \
    libmupdf-dev \
    libfreetype6-dev \
    libopenjp2-7-dev \
    libjbig2dec0-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements copy kar aur install kar
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Baaki code copy kar
COPY . .

# Start command
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
