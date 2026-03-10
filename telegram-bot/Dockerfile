FROM python:3.11-slim

WORKDIR /app

COPY requirements-aiohttp.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY bot_aiohttp.py bot.py

CMD python bot.py
