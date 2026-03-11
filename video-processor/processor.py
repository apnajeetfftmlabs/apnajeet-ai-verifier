# [Filename: video-processor/processor.py] - FINAL WORKING VERSION
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI(title="ApnaJeet Video Processor")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Firebase
firebase = FirebaseClient()

# Check Tesseract
try:
    tesseract_version = pytesseract.get_tesseract_version()
    logger.info(f"✅ Tesseract version: {tesseract_version}")
except Exception as e:
    logger.error(f"❌ Tesseract not found: {e}")
    logger.error("Install tesseract-ocr in Dockerfile")

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
        logger.info(f"[{request_id}] Processing profile: {profile.filename}")
        profile_text = await process_image_advanced(profile, "profile")
        player_id = extract_player_id(profile_text)
        dob = extract_dob(profile_text)
        logger.info(f"[{request_id}] Profile text: {profile_text[:200]}...")
        
        # Process email image
        logger.info(f"[{request_id}] Processing email: {email.filename}")
        email_text = await process_image_advanced(email, "email")
        email_date = extract_date(email_text)
        logger.info(f"[{request_id}] Email text: {email_text[:200]}...")
        
        # Process ad image
        logger.info(f"[{request_id}] Processing ad: {ad.filename}")
        ad_text = await process_image_advanced(ad, "ad")
        ad_date = extract_date(ad_text)
        logger.info(f"[{request_id}] Ad text: {ad_text[:200]}...")
        
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

async def process_image_advanced(file: UploadFile, image_type: str) -> str:
    """Advanced image processing with multiple OCR attempts"""
    try:
        # Read file
        contents = await file.read()
        logger.info(f"{image_type} image size: {len(contents)} bytes")
        
        if len(contents) < 100:  # Too small
            logger.error(f"{image_type} image too small")
            return ""
        
        # Convert to image
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            logger.error(f"{image_type} image decode failed")
            return ""
        
        # Try multiple preprocessing techniques
        texts = []
        
        # Method 1: Original grayscale
        gray1 = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        text1 = pytesseract.image_to_string(gray1)
        texts.append(text1)
        
        # Method 2: Threshold
        _, thresh = cv2.threshold(gray1, 150, 255, cv2.THRESH_BINARY)
        text2 = pytesseract.image_to_string(thresh)
        texts.append(text2)
        
        # Method 3: Resize for better OCR (2x)
        height, width = gray1.shape
        resized = cv2.resize(gray1, (width*2, height*2), interpolation=cv2.INTER_CUBIC)
        text3 = pytesseract.image_to_string(resized)
        texts.append(text3)
        
        # Method 4: Denoise
        denoised = cv2.fastNlMeansDenoising(gray1, h=30)
        text4 = pytesseract.image_to_string(denoised)
        texts.append(text4)
        
        # Choose the longest text (usually best)
        best_text = max(texts, key=len)
        logger.info(f"{image_type} OCR best length: {len(best_text)}")
        
        return best_text
        
    except Exception as e:
        logger.error(f"{image_type} OCR error: {e}")
        return ""

def extract_player_id(text: str) -> str:
    if not text:
        return None
    # Try multiple patterns
    patterns = [
        r'\b\d{10}\b',  # Exactly 10 digits
        r'ID[:\s]*(\d{10})',  # ID: 1234567890
        r'Player[:\s]*(\d{10})',  # Player: 1234567890
        r'Phone[:\s]*(\d{10})',  # Phone: 1234567890
        r'Mobile[:\s]*(\d{10})',  # Mobile: 1234567890
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1) if match.groups() else match.group(0)
    return None

def extract_dob(text: str) -> str:
    if not text:
        return None
    # Try DD/MM/YYYY
    match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
    if match:
        return match.group(1)
    # Try Date: DD/MM/YYYY
    match = re.search(r'Date[:\s]*(\d{2}[/-]\d{2}[/-]\d{4})', text, re.IGNORECASE)
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
    """Advanced matching with keyword weighting"""
    if not text1 or not text2:
        return 0
    
    # Convert to lowercase
    text1_lower = text1.lower()
    text2_lower = text2.lower()
    
    # Extract key phrases (important words)
    important_words = ['gold', 'investment', 'bank', 'target', 'record', 'high', 
                      'price', 'market', 'stock', 'trade', 'club', 'newsletter',
                      'reader', 'dear', 'cramer', 'stansberry']
    
    # Calculate word overlap
    words1 = set(text1_lower.split())
    words2 = set(text2_lower.split())
    
    common_words = words1.intersection(words2)
    common_count = len(common_words)
    
    # Give extra weight to important words
    important_common = [w for w in common_words if w in important_words]
    important_score = len(important_common) * 10  # Each important word = 10%
    
    # Base score from word overlap
    if len(words2) > 0:
        base_score = (common_count / len(words2)) * 100
    else:
        base_score = 0
    
    # Final score (capped at 100)
    final_score = min(base_score + important_score, 100)
    
    return int(final_score)
