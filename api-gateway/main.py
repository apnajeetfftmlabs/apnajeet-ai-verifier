# [Filename: api_gateway/main.py]
from fastapi import FastAPI, Request
import httpx
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ApnaJeet API Gateway")

# Other server URLs (set in Railway env)
BOT_URL = os.getenv("BOT_URL", "http://telegram-bot:8081")
PROCESSOR_URL = os.getenv("PROCESSOR_URL", "http://video-processor:8082")

@app.get("/")
async def root():
    return {
        "service": "API Gateway",
        "status": "running",
        "endpoints": {
            "/health": "GET - Health check",
            "/bot/*": "Forward to Telegram Bot",
            "/process/*": "Forward to Video Processor"
        }
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gateway"}

# Forward to Bot Server
@app.api_route("/bot/{path:path}", methods=["GET", "POST"])
async def proxy_to_bot(path: str, request: Request):
    async with httpx.AsyncClient() as client:
        url = f"{BOT_URL}/{path}"
        logger.info(f"Forwarding to bot: {url}")
        
        if request.method == "GET":
            resp = await client.get(url)
        else:
            body = await request.body()
            resp = await client.post(url, content=body)
        
        return resp.json()

# Forward to Processor Server
@app.api_route("/process/{path:path}", methods=["GET", "POST"])
async def proxy_to_processor(path: str, request: Request):
    async with httpx.AsyncClient() as client:
        url = f"{PROCESSOR_URL}/{path}"
        logger.info(f"Forwarding to processor: {url}")
        
        if request.method == "GET":
            resp = await client.get(url)
        else:
            body = await request.body()
            resp = await client.post(url, content=body)
        
        return resp.json()
