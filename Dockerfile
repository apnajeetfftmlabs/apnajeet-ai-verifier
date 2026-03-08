# [Filename: Dockerfile]
# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Tesseract OCR and OpenCV libraries
RUN apt-get update && apt-get install -y \
    # Tesseract OCR
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    libleptonica-dev \
    # OpenCV dependencies
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # Utils
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create upload directory with proper permissions
RUN mkdir -p data/uploads && chmod 777 data/uploads

# Create non-root user for security
RUN useradd -m -u 1000 apnajeet && \
    chown -R apnajeet:apnajeet /app

# Switch to non-root user
USER apnajeet

# Expose port 8080
EXPOSE 8080

# 🔥 CRITICAL: Hardcoded port 8080 - NO ENVIRONMENT VARIABLES
# Using exec form to avoid shell interpolation issues
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"]
