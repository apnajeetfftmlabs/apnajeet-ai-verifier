from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import uuid
from datetime import datetime
import logging
import sys
import traceback
from typing import Optional

# ============================================
# 🔥 DETAILED LOGGING
# ============================================
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

# ============================================
# 🔥 TRY IMPORT AI PIPELINE
# ============================================
try:
    logger.info("Attempting to import AI pipeline...")
    from ai.pipeline import process_video
    logger.info("✅ AI pipeline imported successfully")
    AI_AVAILABLE = True
except Exception as e:
    logger.error(f"❌ Failed to import AI pipeline: {e}")
    logger.error(traceback.format_exc())
    AI_AVAILABLE = False
    process_video = None

# ============================================
# 🔥 INITIALIZE FASTAPI
# ============================================
app = FastAPI(
    title="ApnaJeet AI Video Verifier",
    description="Verify player ID, date, email, and ad from video",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# 🔥 STARTUP EVENT
# ============================================
@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("🚀 APNAJEET AI VIDEO VERIFIER STARTING UP")
    logger.info("=" * 60)
    
    # System info
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info(f"Files in current dir: {os.listdir('.')}")
    
    # Check directories
    dirs_to_check = ['ai', 'api', 'bot', 'utils', 'data']
    for d in dirs_to_check:
        if os.path.exists(d):
            logger.info(f"✅ Directory '{d}' exists")
            if d == 'ai':
                logger.info(f"   AI files: {os.listdir(d)}")
        else:
            logger.warning(f"⚠️ Directory '{d}' missing")
    
    # Upload directory
    global UPLOAD_DIR
    UPLOAD_DIR = "data/uploads"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.info(f"✅ Upload directory: {UPLOAD_DIR}")
    
    # AI status
    if AI_AVAILABLE:
        logger.info("✅ AI pipeline: READY")
    else:
        logger.warning("⚠️ AI pipeline: NOT AVAILABLE (will use mock data)")
    
    logger.info("=" * 60)
    logger.info("✅ Application startup complete")
    logger.info("=" * 60)

# ============================================
# 🔥 HEALTH CHECK
# ============================================
@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {
        "status": "healthy",
        "ai_available": AI_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ApnaJeet AI Video Verifier",
        "version": "1.0.0",
        "status": "running",
        "ai_available": AI_AVAILABLE,
        "endpoints": {
            "health": "/health",
            "verify": "/verify (POST)",
            "docs": "/docs"
        }
    }

@app.get("/debug")
async def debug_info():
    """Debug endpoint to check system"""
    return {
        "cwd": os.getcwd(),
        "files": os.listdir('.'),
        "ai_available": AI_AVAILABLE,
        "env_vars": {k: v for k, v in os.environ.items() if 'TOKEN' not in k and 'CREDS' not in k}
    }

# ============================================
# 🔥 VERIFY ENDPOINT
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
        logger.warning(f"[{request_id}] Invalid file format: {file.filename}")
        raise HTTPException(400, "Invalid video format. Please upload MP4, AVI, MOV, MKV, or 3GP")
    
    # Check file size
    try:
        content = await file.read()
        file_size = len(content)
        logger.info(f"[{request_id}] File size: {file_size/1024/1024:.2f}MB")
        
        if file_size > 50 * 1024 * 1024:
            logger.warning(f"[{request_id}] File too large: {file_size/1024/1024:.2f}MB")
            raise HTTPException(400, "File too large. Maximum size is 50MB")
    except Exception as e:
        logger.error(f"[{request_id}] Error reading file: {e}")
        raise HTTPException(500, f"Error reading file: {str(e)}")
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    try:
        # Save uploaded file
        logger.info(f"[{request_id}] Saving to: {file_path}")
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        logger.info(f"[{request_id}] File saved successfully")
        
        # Process video with AI
        if AI_AVAILABLE and process_video:
            logger.info(f"[{request_id}] Starting AI processing...")
            try:
                result = process_video(file_path)
                logger.info(f"[{request_id}] AI processing complete")
            except Exception as e:
                logger.error(f"[{request_id}] AI processing error: {e}")
                logger.error(traceback.format_exc())
                result = {
                    "error": f"AI processing failed: {str(e)}",
                    "player_id": None,
                    "profile_date": None,
                    "email_date": None,
                    "email_lines": [],
                    "ad_lines": []
                }
        else:
            logger.warning(f"[{request_id}] AI not available, returning mock data")
            result = {
                "player_id": "1234567890",
                "profile_date": "01/01/2026",
                "email_date": "January 1, 2026",
                "email_lines": ["Test email line 1", "Test email line 2"],
                "ad_lines": ["Test ad line 1"],
                "note": "AI pipeline not available - using mock data"
            }
        
        # Add metadata
        result["filename"] = file.filename
        result["processed_at"] = datetime.now().isoformat()
        result["request_id"] = request_id
        
        logger.info(f"[{request_id}] Returning result: player_id={result.get('player_id')}")
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(500, f"Verification failed: {str(e)}")
    finally:
        # Cleanup
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"[{request_id}] Cleaned up temp file")
            except:
                pass

# ============================================
# 🔥 ADDITIONAL ENDPOINTS
# ============================================
@app.get("/test")
async def test_endpoint():
    """Simple test endpoint"""
    return {"message": "API is working!", "timestamp": datetime.now().isoformat()}

@app.post("/echo")
async def echo_file(file: UploadFile = File(...)):
    """Echo file info (for testing)"""
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(await file.read())
    }
