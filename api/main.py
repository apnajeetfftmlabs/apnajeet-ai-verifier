import os
import uuid
import shutil
import logging
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="ApnaJeet AI Video Verifier")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Upload directory
UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ============================================
# BASIC ENDPOINTS (Already Working)
# ============================================

@app.get("/")
async def root():
    return {
        "status": "ok",
        "port": os.getenv("PORT", "8080"),
        "service": "ApnaJeet AI Video Verifier",
        "version": "1.0"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/test")
async def test():
    return {"message": "working"}

# ============================================
# VERIFY ENDPOINT (POST)
# ============================================

@app.post("/verify")
async def verify_video(file: UploadFile = File(...)):
    """
    Upload video and extract player info
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] New verification request: {file.filename}")
    
    # Validate file
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.3gp')):
        raise HTTPException(400, "Invalid video format")
    
    # Read file
    try:
        content = await file.read()
        file_size = len(content)
        logger.info(f"[{request_id}] File size: {file_size/1024/1024:.2f}MB")
        
        if file_size > 50 * 1024 * 1024:
            raise HTTPException(400, "File too large. Max 50MB")
    except Exception as e:
        logger.error(f"[{request_id}] Error reading file: {e}")
        raise HTTPException(500, f"Error reading file")
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        logger.info(f"[{request_id}] File saved")
        
        # 🔥 MOCK RESULT - Replace with actual AI processing
        result = {
            "player_id": "1234567890",
            "profile_date": "07/03/2026",
            "email_date": "March 7, 2026",
            "email_lines": [
                "A $10,000 Gold Target Is Now Being Discussed",
                "Dear Reader, Gold continues to hit new record high...",
                "investment banks just raised their targets to $10,000/oz"
            ],
            "ad_lines": [
                "Elite Trade Club - Start your day with the trends",
                "Pre-market Report: RECORD CHIPS, SMARTER FLEETS"
            ],
            "filename": file.filename,
            "request_id": request_id,
            "processed_at": datetime.now().isoformat()
        }
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"[{request_id}] Error: {e}")
        raise HTTPException(500, f"Verification failed")
    finally:
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)

# ============================================
# DEBUG ENDPOINTS
# ============================================

@app.get("/debug")
async def debug_info():
    return {
        "cwd": os.getcwd(),
        "files": os.listdir('.'),
        "env": {k: v for k, v in os.environ.items() if 'TOKEN' not in k and 'CREDS' not in k}
    }

@app.post("/echo")
async def echo_file(file: UploadFile = File(...)):
    """Echo file info (for testing)"""
    content = await file.read()
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(content)
    }
