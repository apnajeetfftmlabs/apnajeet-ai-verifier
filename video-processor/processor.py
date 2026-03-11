# [Filename: video-processor/processor.py] - FIXED VERSION
from fastapi import FastAPI, UploadFile, File, HTTPException
import cv2
import numpy as np
import pytesseract
import re
from datetime import datetime
import logging
import os
from firebase_client import FirebaseClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Check if tesseract is installed
try:
    tesseract_version = pytesseract.get_tesseract_version()
    logger.info(f"✅ Tesseract version: {tesseract_version}")
except Exception as e:
    logger.error(f"❌ Tesseract not found! Error: {e}")
    logger.error("Make sure tesseract-ocr is installed in the container")

app = FastAPI(title="ApnaJeet Video Processor")
firebase = FirebaseClient()

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "tesseract": str(pytesseract.get_tesseract_version()) if pytesseract else "missing",
        "firebase": firebase.initialized,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/verify-three")
async def verify_three(
    profile: UploadFile = File(...),
    email: UploadFile = File(...),
    ad: UploadFile = File(...)
):
    """Verify using three images: profile, email, ad"""
    request_id = datetime.now().strftime("%Y%m%d%H%M%S")
    logger.info(f"[{request_id}] Processing 3 images")
    
    try:
        # Process profile image
        logger.info(f"[{request_id}] Processing profile image: {profile.filename}")
        profile_text = await process_image(profile, "profile")
        player_id = extract_player_id(profile_text)
        dob = extract_dob(profile_text)
        logger.info(f"[{request_id}] Profile text length: {len(profile_text)}")
        
        # Process email image
        logger.info(f"[{request_id}] Processing email image: {email.filename}")
        email_text = await process_image(email, "email")
        email_date = extract_date(email_text)
        logger.info(f"[{request_id}] Email text length: {len(email_text)}")
        
        # Process ad image
        logger.info(f"[{request_id}] Processing ad image: {ad.filename}")
        ad_text = await process_image(ad, "ad")
        ad_date = extract_date(ad_text)
        logger.info(f"[{request_id}] Ad text length: {len(ad_text)}")
        
        # Log extracted data
        logger.info(f"[{request_id}] Extracted - Player ID: {player_id}, DOB: {dob}, Email Date: {email_date}, Ad Date: {ad_date}")
        
        # Match with Firebase
        email_match = 0
        ad_match = 0
        
        if email_date:
            template = firebase.get_email_template(email_date)
            if template:
                email_match = calculate_match(email_text, template.get('content', ''))
                logger.info(f"[{request_id}] Email match: {email_match}%")
        
        if ad_date:
            template = firebase.get_ad_template(ad_date)
            if template:
                ad_match = calculate_match(ad_text, template.get('content', ''))
                logger.info(f"[{request_id}] Ad match: {ad_match}%")
        
        # Validate player ID
        player_valid = False
        if player_id:
            player_valid = firebase.validate_player(player_id)
            logger.info(f"[{request_id}] Player valid: {player_valid}")
        
        # Calculate overall confidence
        confidence = (email_match + ad_match) / 2 if (email_match + ad_match) > 0 else 0
        verified = confidence > 70 and player_valid
        
        result = {
            "player_id": player_id,
            "dob": dob,
            "email_match": email_match,
            "ad_match": ad_match,
            "confidence": confidence,
            "verified": verified,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"[{request_id}] Result: {result}")
        
        # Save to Firebase
        firebase.save_verification(result)
        
        return result
        
    except Exception as e:
        logger.error(f"[{request_id}] Error: {e}", exc_info=True)
        return {"error": str(e)}

async def process_image(file: UploadFile, image_type: str) -> str:
    """Process single image and return text"""
    try:
        # Read file contents
        contents = await file.read()
        logger.info(f"{image_type} image size: {len(contents)} bytes")
        
        if len(contents) == 0:
            logger.error(f"{image_type} image is empty")
            return ""
        
        # Convert to numpy array
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            logger.error(f"{image_type} image could not be decoded")
            return ""
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold to improve OCR
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        # Run OCR
        try:
            text = pytesseract.image_to_string(thresh)
            logger.info(f"{image_type} OCR successful, extracted {len(text)} characters")
            return text
        except Exception as e:
            logger.error(f"{image_type} OCR failed: {e}")
            return ""
            
    except Exception as e:
        logger.error(f"Error processing {image_type} image: {e}")
        return ""

def extract_player_id(text: str) -> str:
    if not text:
        return None
    match = re.search(r'\b\d{10}\b', text)
    return match.group(0) if match else None

def extract_dob(text: str) -> str:
    if not text:
        return None
    match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
    return match.group(1) if match else None

def extract_date(text: str) -> str:
    if not text:
        return None
    # Try DD/MM/YYYY
    match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
    if match:
        return match.group(1)
    # Try Month DD, YYYY
    match = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4})', text)
    return match.group(1) if match else None

def calculate_match(text1: str, text2: str) -> int:
    """Simple match percentage"""
    if not text1 or not text2:
        return 0
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if len(words2) == 0:
        return 0
    common = words1.intersection(words2)
    return int((len(common) / len(words2)) * 100)
