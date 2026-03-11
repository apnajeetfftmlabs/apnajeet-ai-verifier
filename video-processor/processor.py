# [Filename: video-processor/processor.py] - Fixed & Improved
from fastapi import FastAPI, UploadFile, File, HTTPException
import cv2
import numpy as np
import pytesseract
import re
from datetime import datetime
import logging
from firebase_client import FirebaseClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="ApnaJeet Video Processor")
firebase = FirebaseClient()

@app.get("/")
async def root():
    return {
        "service": "ApnaJeet Video Processor",
        "status": "running",
        "endpoints": {
            "/health": "GET",
            "/verify-three": "POST (3 images)"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "firebase": "connected" if firebase.initialized else "disconnected",
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
    logger.info(f"[{request_id}] Received 3 images: {profile.filename}, {email.filename}, {ad.filename}")

    # Validate file types
    for file in [profile, email, ad]:
        if not file.content_type.startswith('image/'):
            logger.error(f"Invalid file type: {file.content_type}")
            raise HTTPException(400, f"File {file.filename} is not an image")

    try:
        # Process profile image
        profile_text = await process_image(profile)
        player_id = extract_player_id(profile_text)
        dob = extract_dob(profile_text)
        logger.info(f"Profile: player_id={player_id}, dob={dob}")

        # Process email image
        email_text = await process_image(email)
        email_date = extract_date(email_text)
        logger.info(f"Email: date={email_date}")

        # Process ad image
        ad_text = await process_image(ad)
        ad_date = extract_date(ad_text)
        logger.info(f"Ad: date={ad_date}")

        # Match with Firebase
        email_match = 0
        ad_match = 0

        if email_date:
            template = firebase.get_email_template(email_date)
            if template:
                email_match = calculate_match(email_text, template.get('content', ''))
                logger.info(f"Email match: {email_match}%")

        if ad_date:
            template = firebase.get_ad_template(ad_date)
            if template:
                ad_match = calculate_match(ad_text, template.get('content', ''))
                logger.info(f"Ad match: {ad_match}%")

        # Validate player ID
        player_valid = False
        if player_id:
            player_valid = firebase.validate_player(player_id)
            logger.info(f"Player valid: {player_valid}")

        # Calculate overall confidence
        confidence = (email_match + ad_match) / 2
        verified = confidence > 70 and player_valid

        result = {
            "player_id": player_id,
            "dob": dob,
            "email_match": email_match,
            "ad_match": ad_match,
            "confidence": confidence,
            "verified": verified,
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id
        }

        # Save to Firebase
        firebase.save_verification(result)
        logger.info(f"Result: {result}")

        return result

    except Exception as e:
        logger.error(f"Error processing request {request_id}: {e}", exc_info=True)
        return {"error": str(e), "request_id": request_id}

async def process_image(file: UploadFile) -> str:
    """Process single image and return text"""
    try:
        contents = await file.read()
        logger.info(f"Image {file.filename} size: {len(contents)} bytes")
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Optional: improve OCR with threshold
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        text = pytesseract.image_to_string(thresh)
        logger.info(f"Extracted text length: {len(text)}")
        return text
    except Exception as e:
        logger.error(f"Error processing image {file.filename}: {e}")
        raise

def extract_player_id(text: str) -> str:
    match = re.search(r'\b\d{10}\b', text)
    return match.group(0) if match else None

def extract_dob(text: str) -> str:
    match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
    return match.group(1) if match else None

def extract_date(text: str) -> str:
    # Try DD/MM/YYYY
    match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
    if match:
        return match.group(1)
    # Try Month DD, YYYY
    match = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4})', text)
    return match.group(1) if match else None

def calculate_match(text1: str, text2: str) -> int:
    """Simple match percentage"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    common = words1.intersection(words2)
    if len(words2) == 0:
        return 0
    return int((len(common) / len(words2)) * 100)
