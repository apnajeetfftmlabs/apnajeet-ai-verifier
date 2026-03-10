# [Filename: video-processor/processor.py] - 3-Image Version
from fastapi import FastAPI, UploadFile, File, Form
import cv2
import numpy as np
import pytesseract
import re
from datetime import datetime
import logging
from firebase_client import FirebaseClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
firebase = FirebaseClient()

@app.post("/verify-three")
async def verify_three(
    profile: UploadFile = File(...),
    email: UploadFile = File(...),
    ad: UploadFile = File(...)
):
    """Verify using three images: profile, email, ad"""
    
    try:
        # Process profile image
        profile_text = await process_image(profile)
        player_id = extract_player_id(profile_text)
        dob = extract_dob(profile_text)
        
        # Process email image
        email_text = await process_image(email)
        email_date = extract_date(email_text)
        
        # Process ad image
        ad_text = await process_image(ad)
        ad_date = extract_date(ad_text)
        
        # Match with Firebase
        email_match = 0
        ad_match = 0
        
        if email_date:
            template = firebase.get_email_template(email_date)
            if template:
                email_match = calculate_match(email_text, template.get('content', ''))
        
        if ad_date:
            template = firebase.get_ad_template(ad_date)
            if template:
                ad_match = calculate_match(ad_text, template.get('content', ''))
        
        # Validate player ID
        player_valid = False
        if player_id:
            player_valid = firebase.validate_player(player_id)
        
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
            "timestamp": datetime.now().isoformat()
        }
        
        # Save to Firebase
        firebase.save_verification(result)
        
        return result
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"error": str(e)}

async def process_image(file: UploadFile) -> str:
    """Process single image and return text"""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return pytesseract.image_to_string(gray)

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
