# [Filename: telegram-bot/Dockerfile]
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY bot.py .

# ✅ FIX: Use gunicorn instead of python bot.py
CMD gunicorn bot:app --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 120 --log-level debug
