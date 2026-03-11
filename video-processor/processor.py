# [Filename: video-processor/processor.py] - FINAL WITH IMPROVED MATCHING
from fastapi import FastAPI, UploadFile, File
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
    request_id = datetime.now().strftime("%Y%m%d%H%M%S")
    logger.info(f"[{request_id}] Processing 3 images")
    
    try:
        # Process profile
        profile_text = await process_image(profile)
        player_id = extract_player_id(profile_text)
        dob = extract_dob(profile_text)
        logger.info(f"[{request_id}] Profile text: {profile_text[:100]}...")
        
        # Process email
        email_text = await process_image(email)
        email_date = extract_date(email_text)
        logger.info(f"[{request_id}] Email text: {email_text[:100]}...")
        
        # Process ad
        ad_text = await process_image(ad)
        ad_date = extract_date(ad_text)
        logger.info(f"[{request_id}] Ad text: {ad_text[:100]}...")
        
        # Match with Firebase
        email_match = 0
        ad_match = 0
        
        if email_date:
            template = firebase.get_email_template(email_date)
            if template:
                email_match = calculate_match(email_text, template)
                logger.info(f"[{request_id}] Email match: {email_match}%")
            else:
                logger.warning(f"[{request_id}] No email template for {email_date}")
        
        if ad_date:
            template = firebase.get_ad_template(ad_date)
            if template:
                ad_match = calculate_match(ad_text, template)
                logger.info(f"[{request_id}] Ad match: {ad_match}%")
            else:
                logger.warning(f"[{request_id}] No ad template for {ad_date}")
        
        # Validate player
        player_valid = False
        if player_id:
            player_valid = firebase.validate_player(player_id)
        
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
        
        logger.info(f"[{request_id}] Result: {result}")
        firebase.save_verification(result)
        return result
        
    except Exception as e:
        logger.error(f"[{request_id}] Error: {e}", exc_info=True)
        return {"error": str(e)}

async def process_image(file: UploadFile) -> str:
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Simple threshold for better OCR
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    return pytesseract.image_to_string(thresh)

def extract_player_id(text: str) -> str:
    if not text: return None
    match = re.search(r'\b\d{10}\b', text)
    return match.group(0) if match else None

def extract_dob(text: str) -> str:
    if not text: return None
    match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
    return match.group(1) if match else None

def extract_date(text: str) -> str:
    if not text: return None
    match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
    if match:
        return match.group(1)
    match = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4})', text)
    return match.group(1) if match else None

def calculate_match(extracted_text: str, template: dict) -> int:
    """Advanced matching with multiple fields and keyword weighting"""
    if not extracted_text or not template:
        return 0
    
    score = 0
    total_weight = 0
    
    # Combine all template fields
    template_text = ' '.join(filter(None, [
        template.get('subject', ''),
        template.get('sender', ''),
        template.get('content', ''),
        template.get('headline', ''),
        template.get('description', ''),
        template.get('full_text', '')
    ])).lower()
    
    extracted_lower = extracted_text.lower()
    
    # Important keywords with weights
    keywords = {
        'gold': 10, 'investment': 8, 'bank': 8, 'target': 8,
        'record': 6, 'high': 5, 'price': 5, 'market': 5,
        'stock': 5, 'trade': 5, 'club': 5, 'newsletter': 8,
        'reader': 3, 'dear': 3, 'cramer': 10, 'stansberry': 10,
        'elite': 8, 'pre-market': 8, 'closing bell': 8,
        'subscribe': 5, 'free': 5, 'email': 3
    }
    
    # Check for keywords
    for word, weight in keywords.items():
        if word in extracted_lower and word in template_text:
            score += weight
            total_weight += weight
    
    # Word overlap percentage
    words_extracted = set(extracted_lower.split())
    words_template = set(template_text.split())
    if words_template:
        overlap = len(words_extracted.intersection(words_template))
        overlap_score = (overlap / len(words_template)) * 30  # max 30%
        score += overlap_score
        total_weight += 30
    
    # Normalize
    if total_weight > 0:
        final_score = min(int((score / total_weight) * 100), 100)
    else:
        final_score = 0
    
    return final_score
