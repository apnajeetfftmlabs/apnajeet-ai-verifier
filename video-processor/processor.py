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

# Initialize Firebase safely
try:
    firebase = FirebaseClient()
except Exception as e:
    logger.error(f"Firebase init failed: {e}")
    firebase = None

@app.get("/health")
async def health():
    if firebase:
        return {"status": "healthy", "firebase": firebase.initialized}
    else:
        return {"status": "healthy", "firebase": False}

@app.post("/verify-three")
async def verify_three(
    profile: UploadFile = File(...),
    email: UploadFile = File(...),
    ad: UploadFile = File(...)
):
    request_id = datetime.now().strftime("%Y%m%d%H%M%S")
    logger.info(f"[{request_id}] Processing 3 images")
    
    # Process images
    profile_text = await process_image(profile)
    email_text = await process_image(email)
    ad_text = await process_image(ad)
    
    # Extract data
    player_id = extract_player_id(profile_text)
    dob = extract_dob(profile_text)
    email_date = extract_date(email_text)
    ad_date = extract_date(ad_text)
    
    logger.info(f"[{request_id}] Player ID: {player_id}, DOB: {dob}")
    logger.info(f"[{request_id}] Email date: {email_date}, Ad date: {ad_date}")
    
    # Match with Firebase
    email_match = 0
    ad_match = 0
    
    if email_date and firebase:
        # Convert DD/MM/YYYY to YYYY-MM-DD for Firebase
        date_key = email_date
        if '/' in email_date:
            parts = email_date.split('/')
            if len(parts) == 3:
                date_key = f"{parts[2]}-{parts[1]}-{parts[0]}"
        
        template = firebase.get_email_template(date_key)
        if template:
            logger.info(f"[{request_id}] Email template found")
            email_match = calculate_match(email_text, template)
    
    if ad_date and firebase:
        date_key = ad_date
        if '/' in ad_date:
            parts = ad_date.split('/')
            if len(parts) == 3:
                date_key = f"{parts[2]}-{parts[1]}-{parts[0]}"
        
        template = firebase.get_ad_template(date_key)
        if template:
            logger.info(f"[{request_id}] Ad template found")
            ad_match = calculate_match(ad_text, template)
    
    # Validate player
    player_valid = False
    if player_id and firebase:
        player_valid = firebase.validate_player(player_id)
    
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
    
    logger.info(f"[{request_id}] Result: {result}")
    if firebase:
        firebase.save_verification(result)
    return result

async def process_image(file: UploadFile) -> str:
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    return pytesseract.image_to_string(thresh)

def extract_player_id(text: str) -> str:
    match = re.search(r'\b\d{10}\b', text)
    return match.group(0) if match else None

def extract_dob(text: str) -> str:
    match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
    return match.group(1) if match else None

def extract_date(text: str) -> str:
    if not text:
        return None
    
    # DD/MM/YYYY
    match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
    if match:
        return match.group(1)
    
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

def calculate_match(extracted_text: str, template: dict) -> int:
    if not extracted_text or not template:
        return 0
    
    # Combine all template fields
    template_text = ' '.join(filter(None, [
        template.get('subject', ''),
        template.get('content', ''),
        template.get('full_html', ''),
        template.get('sender', '')
    ])).lower()
    
    extracted_lower = extracted_text.lower()
    
    words_ext = set(extracted_lower.split())
    words_temp = set(template_text.split())
    
    if not words_temp:
        return 0
    
    common = words_ext.intersection(words_temp)
    return min(int((len(common) / len(words_temp)) * 100), 100)
