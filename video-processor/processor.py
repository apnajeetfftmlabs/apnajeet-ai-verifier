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

@app.get("/health")
async def health():
    return {"status": "healthy", "firebase": firebase.initialized}

@app.post("/verify-three")
async def verify_three(
    profile: UploadFile = File(...),
    email: UploadFile = File(...),
    ad: UploadFile = File(...)
):
    request_id = datetime.now().strftime("%Y%m%d%H%M%S")
    logger.info(f"[{request_id}] ===== START PROCESSING 3 IMAGES =====")
    
    # Process profile
    profile_text = await process_image(profile, "profile")
    player_id = extract_player_id(profile_text)
    dob = extract_dob(profile_text)
    
    # Process email
    email_text = await process_image(email, "email")
    email_date = extract_date(email_text)
    
    # Process ad
    ad_text = await process_image(ad, "ad")
    ad_date = extract_date(ad_text)
    
    logger.info(f"[{request_id}] Player ID: {player_id}, DOB: {dob}")
    logger.info(f"[{request_id}] Email date: {email_date}, Ad date: {ad_date}")
    
    # Match with Firebase
    email_match = 0
    ad_match = 0
    
    if email_date:
        # Normalize date for Firebase
        date_key = email_date.replace('/', '-')
        logger.info(f"[{request_id}] Looking for email template: email_templates/{date_key}")
        template = firebase.get_email_template(date_key)
        if template:
            logger.info(f"[{request_id}] ✅ Email template found")
            email_match = calculate_match(email_text, template, "email")
        else:
            logger.warning(f"[{request_id}] ❌ No email template for {date_key}")
    
    if ad_date:
        date_key = ad_date.replace('/', '-')
        logger.info(f"[{request_id}] Looking for ad template: ad_templates/{date_key}")
        template = firebase.get_ad_template(date_key)
        if template:
            logger.info(f"[{request_id}] ✅ Ad template found")
            ad_match = calculate_match(ad_text, template, "ad")
        else:
            logger.warning(f"[{request_id}] ❌ No ad template for {date_key}")
    
    # Validate player
    player_valid = False
    if player_id:
        player_valid = firebase.validate_player(player_id)
        logger.info(f"[{request_id}] Player valid: {player_valid}")
    
    confidence = (email_match + ad_match) / 2 if (email_match + ad_match) > 0 else 85 if player_id else 0
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

async def process_image(file: UploadFile, img_type: str) -> str:
    contents = await file.read()
    logger.info(f"[{img_type}] Size: {len(contents)} bytes")
    
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Preprocessing for better OCR
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    
    # Try different preprocessing if text is short
    text = pytesseract.image_to_string(thresh)
    if len(text) < 50:
        # Try with sharpening
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharp = cv2.filter2D(gray, -1, kernel)
        _, thresh2 = cv2.threshold(sharp, 150, 255, cv2.THRESH_BINARY)
        text2 = pytesseract.image_to_string(thresh2)
        if len(text2) > len(text):
            text = text2
    
    logger.info(f"[{img_type}] OCR extracted {len(text)} chars")
    return text

def extract_player_id(text: str) -> str:
    match = re.search(r'\b\d{10}\b', text)
    return match.group(0) if match else None

def extract_dob(text: str) -> str:
    match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
    if match:
        return match.group(1).replace('-', '/')
    return None

def extract_date(text: str) -> str:
    if not text:
        return None
    
    # DD/MM/YYYY
    match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
    if match:
        return match.group(1).replace('-', '/')
    
    # Month DD, YYYY
    match = re.search(r'\b([A-Z][a-z]+ \d{1,2}, \d{4})\b', text)
    if match:
        date_str = match.group(1)
        try:
            date_obj = datetime.strptime(date_str, "%b %d, %Y")
            return date_obj.strftime("%d/%m/%Y")
        except:
            try:
                date_obj = datetime.strptime(date_str, "%B %d, %Y")
                return date_obj.strftime("%d/%m/%Y")
            except:
                return date_str
    return None

def calculate_match(extracted_text: str, template: dict, template_type: str) -> int:
    """Calculate match percentage with detailed logging"""
    
    # Combine template fields
    fields_to_check = []
    if template_type == "email":
        fields_to_check = [
            template.get('subject', ''),
            template.get('content', ''),
            template.get('full_html', ''),
            template.get('sender', '')
        ]
    else:  # ad template
        fields_to_check = [
            template.get('headline', ''),
            template.get('description', ''),
            template.get('full_text', ''),
            template.get('cta', '')
        ]
    
    template_text = ' '.join(filter(None, fields_to_check)).lower()
    extracted_lower = extracted_text.lower()
    
    # Clean text (remove extra spaces, normalize)
    template_text = ' '.join(template_text.split())
    extracted_lower = ' '.join(extracted_lower.split())
    
    words_ext = set(extracted_lower.split())
    words_temp = set(template_text.split())
    
    logger.info(f"[{template_type}] Extracted words: {len(words_ext)}")
    logger.info(f"[{template_type}] Template words: {len(words_temp)}")
    
    if not words_temp:
        return 0
    
    common = words_ext.intersection(words_temp)
    logger.info(f"[{template_type}] Common words: {len(common)}")
    
    if len(common) == 0:
        # Log samples for debugging
        logger.warning(f"[{template_type}] NO COMMON WORDS FOUND!")
        logger.info(f"[{template_type}] Extracted sample: {extracted_lower[:200]}...")
        logger.info(f"[{template_type}] Template sample: {template_text[:200]}...")
        return 0
    
    match_percent = (len(common) / len(words_temp)) * 100
    final_score = min(int(match_percent), 100)
    logger.info(f"[{template_type}] Match score: {final_score}%")
    
    return final_score
