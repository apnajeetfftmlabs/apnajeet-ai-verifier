# [Filename: video-processor/processor.py] - DEBUG VERSION
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
    logger.info(f"[{request_id}] ===== START PROCESSING 3 IMAGES =====")
    
    try:
        # Profile
        profile_text = await process_image(profile)
        player_id = extract_player_id(profile_text)
        dob = extract_dob(profile_text)
        logger.info(f"[{request_id}] Profile text (first 300): {profile_text[:300]}")
        logger.info(f"[{request_id}] Player ID: {player_id}, DOB: {dob}")
        
        # Email
        email_text = await process_image(email)
        email_date = extract_date(email_text)
        logger.info(f"[{request_id}] Email text (first 300): {email_text[:300]}")
        logger.info(f"[{request_id}] Extracted email_date: {email_date}")
        
        email_match = 0
        if email_date:
            # Normalize date to YYYY-MM-DD
            parts = email_date.split('/')
            if len(parts) == 3:
                date_key = f"{parts[2]}-{parts[1]}-{parts[0]}"
            else:
                date_key = email_date
            logger.info(f"[{request_id}] Looking for email template at: email_templates/{date_key}/client1")
            template = firebase.get_email_template(date_key)
            if template:
                logger.info(f"[{request_id}] Email template keys: {list(template.keys())}")
                logger.info(f"[{request_id}] Template content (first 300): {template.get('content', '')[:300]}")
                email_match = calculate_match(email_text, template)
                logger.info(f"[{request_id}] Email match: {email_match}%")
            else:
                logger.warning(f"[{request_id}] No email template found for {date_key}")
        else:
            logger.warning(f"[{request_id}] No date extracted from email image")
        
        # Ad
        ad_text = await process_image(ad)
        ad_date = extract_date(ad_text)
        logger.info(f"[{request_id}] Ad text (first 300): {ad_text[:300]}")
        logger.info(f"[{request_id}] Extracted ad_date: {ad_date}")
        
        ad_match = 0
        if ad_date:
            parts = ad_date.split('/')
            if len(parts) == 3:
                date_key = f"{parts[2]}-{parts[1]}-{parts[0]}"
            else:
                date_key = ad_date
            logger.info(f"[{request_id}] Looking for ad template at: ad_templates/client1/{date_key}")
            template = firebase.get_ad_template(date_key)  # ensure this function uses correct path
            if template:
                logger.info(f"[{request_id}] Ad template keys: {list(template.keys())}")
                logger.info(f"[{request_id}] Template full_text (first 300): {template.get('full_text', '')[:300]}")
                ad_match = calculate_match(ad_text, template)
                logger.info(f"[{request_id}] Ad match: {ad_match}%")
            else:
                logger.warning(f"[{request_id}] No ad template found for {date_key}")
        else:
            logger.warning(f"[{request_id}] No date extracted from ad image")
        
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
        logger.info(f"[{request_id}] Final result: {result}")
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
    # Try DD/MM/YYYY
    match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
    if match:
        return match.group(1)
    # Try Month DD, YYYY
    match = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4})', text)
    return match.group(1) if match else None

def calculate_match(extracted_text: str, template: dict) -> int:
    """Combine all text fields and compute similarity"""
    if not extracted_text or not template:
        return 0
    
    # Combine all relevant template fields
    template_text = ' '.join(filter(None, [
        template.get('subject', ''),
        template.get('sender', ''),
        template.get('content', ''),
        template.get('headline', ''),
        template.get('description', ''),
        template.get('full_text', ''),
        template.get('full_html', '')
    ])).lower()
    
    extracted_lower = extracted_text.lower()
    
    # Word overlap
    words_ext = set(extracted_lower.split())
    words_temp = set(template_text.split())
    if not words_temp:
        return 0
    common = words_ext.intersection(words_temp)
    overlap = len(common)
    base_score = (overlap / len(words_temp)) * 70  # 70% weight to overlap
    
    # Keyword bonus
    keywords = ['gold', 'investment', 'bank', 'target', 'record', 'high', 
                'price', 'market', 'stock', 'trade', 'club', 'newsletter',
                'reader', 'cramer', 'stansberry', 'elite', 'pre-market']
    keyword_bonus = 0
    for kw in keywords:
        if kw in extracted_lower and kw in template_text:
            keyword_bonus += 5  # 5% per keyword, max 30%
    keyword_bonus = min(keyword_bonus, 30)
    
    total = base_score + keyword_bonus
    return min(int(total), 100)
