from fastapi import FastAPI
import logging
import sys
import os

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
async def startup():
    logger.info("=" * 50)
    logger.info("🚀 APP STARTING...")
    logger.info(f"PORT: {os.getenv('PORT', '8000')}")
    logger.info("=" * 50)

@app.get("/")
async def root():
    return {"status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/test")
async def test():
    return {"message": "working"}
