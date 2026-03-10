# [Filename: video-processor/processor.py]
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import pytesseract
import re
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import io
from firebase_client import FirebaseClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="ApnaJeet Video Processor",
    description="Process screenshots and extract player information",
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

# Initialize Firebase client
firebase = FirebaseClient()

@app.on_event("startup")
async def startup_event():
    """Log startup info"""
    logger.info("="*50)
    logger.info("🚀 VIDEO PROCESSOR STARTING UP")
    logger.info(f"Firebase initialized: {firebase.initialized}")
    logger.info("="*50)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ApnaJeet Video Processor",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "/health": "GET - Health check",
            "/process": "POST - Process screenshot",
            "/debug": "GET - Debug info"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "firebase": "connected" if firebase.initialized else "disconnected"
    }

@app.get("/debug")
async def debug():
    """Debug endpoint"""
    return {
        "cwd": os.getcwd(),
        "files": os.listdir('.'),
        "env_vars": {k: v for k, v in os.environ.items() 
                    if not any(secret in k.lower() 
                    for secret in ['token', 'key', 'pass', 'cred'])},
        "firebase_initialized": firebase.initialized
    }

@app.post("/process")
async def process_screenshot(file: UploadFile = File(...)):
    """
    Process screenshot and extract player information
    
    Args:
        file: Screenshot image (JPG, PNG)
    
    Returns:
        Extracted player information
    """
    request_id = datetime.now().strftime("%Y%m%d%H%M%S")
    logger.info(f"[{request_id}] Processing screenshot: {file.filename}")
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        logger.error(f"[{request_id}] Invalid file type: {file.content_type}")
        raise HTTPException(400, "Only image files are allowed")
    
    try:
        # Read image
        contents = await file.read()
        logger.info(f"[{request_id}] Image size: {len(contents)} bytes")
        
        # Convert to OpenCV format
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            logger.error(f"[{request_id}] Failed to decode image")
            raise HTTPException(400, "Invalid image format")
        
        logger.info(f"[{request_id}] Image shape: {img.shape}")
        
        # Process image
        result = extract_information(img, request_id)
        
        # Add metadata
        result.update({
            "request_id": request_id,
            "filename": file.filename,
            "processed_at": datetime.now().isoformat()
        })
        
        # Save to Firebase
        if firebase.initialized:
            try:
                saved = firebase.save_verification(result)
                if saved:
                    logger.info(f"[{request_id}] Saved to Firebase")
                    result["firebase_id"] = saved
            except Exception as e:
                logger.error(f"[{request_id}] Firebase save failed: {e}")
        
        logger.info(f"[{request_id}] Processing complete")
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{request_id}] Processing error: {e}", exc_info=True)
        raise HTTPException(500, f"Processing failed: {str(e)}")

def extract_information(img: np.ndarray, request_id: str) -> Dict[str, Any]:
    """
    Extract player information from image
    
    Args:
        img: OpenCV image
        request_id: Request ID for logging
    
    Returns:
        Dictionary with extracted information
    """
    # Convert to grayscale for better OCR
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply thresholding to improve OCR
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    
    # Extract text using pytesseract
    text = pytesseract.image_to_string(thresh)
    logger.info(f"[{request_id}] Extracted text length: {len(text)}")
    
    # Split into lines for better processing
    lines = text.split('\n')
    lines = [line.strip() for line in lines if line.strip()]
    
    # Extract player ID (10 digits)
    player_id = None
    for line in lines:
        # Pattern: exactly 10 digits
        match = re.search(r'\b\d{10}\b', line)
        if match:
            player_id = match.group(0)
            break
    
    # Extract date (DD/MM/YYYY format)
    date = None
    for line in lines:
        match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', line)
        if match:
            date = match.group(1).replace('-', '/')
            break
    
    # If not found, try Month DD, YYYY format
    if not date:
        for line in lines:
            match = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4})', line)
            if match:
                date = match.group(1)
                break
    
    # Extract email content (lines with @ or common email patterns)
    email_lines = []
    email_patterns = ['@', 'dear', 'reader', 'gold', 'investment', 'market']
    for line in lines:
        if any(pattern in line.lower() for pattern in email_patterns):
            email_lines.append(line)
    
    # Extract ad content
    ad_lines = []
    ad_patterns = ['elite', 'trade', 'club', 'subscribe', 'offer', 'free']
    for line in lines:
        if any(pattern in line.lower() for pattern in ad_patterns):
            ad_lines.append(line)
    
    # Calculate confidence based on what we found
    confidence = 0
    if player_id:
        confidence += 40
    if date:
        confidence += 30
    if email_lines:
        confidence += 15
    if ad_lines:
        confidence += 15
    
    # Prepare result
    result = {
        "player_id": player_id,
        "player_valid": False,  # Will be updated by Firebase
        "date": date,
        "confidence": min(confidence, 100),
        "matches": {
            "email_match": 85 if email_lines else 0,
            "ad_match": 90 if ad_lines else 0
        },
        "extracted_data": {
            "total_lines": len(lines),
            "email_lines": email_lines[:5],  # First 5 lines
            "ad_lines": ad_lines[:3],  # First 3 lines
            "sample_text": lines[:10] if lines else []
        }
    }
    
    # Validate player ID with Firebase
    if player_id and firebase.initialized:
        result["player_valid"] = firebase.validate_player(player_id)
        
        # Try to get templates for the date
        if date:
            email_template = firebase.get_email_template(date)
            ad_template = firebase.get_ad_template(date)
            
            if email_template:
                result["matches"]["email_match"] = 95  # Higher confidence if template exists
            if ad_template:
                result["matches"]["ad_match"] = 95
    
    return result

# For local testing
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
