from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import uuid
from datetime import datetime
import logging
from typing import Optional

# Import AI pipeline
from ai.pipeline import process_video

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

@app.get("/")
async def root():
    return {
        "service": "ApnaJeet AI Video Verifier",
        "version": "1.0",
        "status": "running"
    }

@app.post("/verify")
async def verify_video(file: UploadFile = File(...)):
    """
    Upload video and extract player info
    """
    # Validate file
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.3gp')):
        raise HTTPException(400, "Invalid video format. Please upload MP4, AVI, MOV, MKV, or 3GP")
    
    # Check file size (max 50MB)
    file_size = 0
    content = await file.read()
    file_size = len(content)
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(400, "File too large. Maximum size is 50MB")
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        logger.info(f"File saved: {file_path} ({file_size/1024/1024:.2f}MB)")
        
        # Process video with AI
        result = process_video(file_path)
        
        # Add metadata
        result["filename"] = file.filename
        result["processed_at"] = datetime.now().isoformat()
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        raise HTTPException(500, f"Verification failed: {str(e)}")
    finally:
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
