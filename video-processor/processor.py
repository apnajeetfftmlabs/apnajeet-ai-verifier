# [Filename: video-processor/processor.py]
from fastapi import FastAPI, UploadFile, File
import cv2
import numpy as np
import pytesseract
import re
from datetime import datetime
import logging
import unicodedata
from firebase_client import FirebaseClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    return {"status": "healthy", "firebase": firebase.initialized if firebase else False}

@app.post("/verify-three")
async def verify_three(
    profile: UploadFile = File(...),
    email: UploadFile = File(...),
    ad: UploadFile = File(...)
):
    request_id = datetime.now().strftime("%Y%m%d%H%M%S")
    logger.info(f"[{request_id}] ===== START PROCESSING 3 IMAGES =====")
    
    # Process images with advanced OCR
    profile_text = await process_image_advanced(profile, "profile")
    email_text = await process_image_advanced(email, "email")
    ad_text = await process_image_advanced(ad, "ad")
    
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
    email_template = None
    ad_template = None
    
    if email_date and firebase:
        # Convert date to Firebase key format (YYYY-MM-DD)
        date_key = email_date
        if '/' in email_date:
            parts = email_date.split('/')
            if len(parts) == 3:
                date_key = f"{parts[2]}-{parts[1]}-{parts[0]}"
        
        template = firebase.get_email_template(date_key)
        if template:
            logger.info(f"[{request_id}] Email template found for {date_key}")
            email_template = template
            email_match = calculate_match(email_text, template)
            logger.info(f"[{request_id}] Email match: {email_match}%")
        else:
            logger.warning(f"[{request_id}] No email template for {date_key}")
    
    if ad_date and firebase:
        date_key = ad_date
        if '/' in ad_date:
            parts = ad_date.split('/')
            if len(parts) == 3:
                date_key = f"{parts[2]}-{parts[1]}-{parts[0]}"
        
        template = firebase.get_ad_template(date_key)
        if template:
            logger.info(f"[{request_id}] Ad template found for {date_key}")
            ad_template = template
            ad_match = calculate_match(ad_text, template)
            logger.info(f"[{request_id}] Ad match: {ad_match}%")
        else:
            logger.warning(f"[{request_id}] No ad template for {date_key}")
    
    # Validate player
    player_valid = False
    if player_id and firebase:
        player_valid = firebase.validate_player(player_id)
        logger.info(f"[{request_id}] Player valid: {player_valid}")
    
    # Calculate confidence (base from player ID if nothing else)
    if email_match > 0 or ad_match > 0:
        confidence = (email_match + ad_match) / 2
    elif player_id:
        confidence = 85  # Player ID mila to base confidence
    else:
        confidence = 0
    
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
    if firebase:
        firebase.save_verification(result)
    return result

async def process_image_advanced(file: UploadFile, image_type: str) -> str:
    """Advanced image preprocessing for better OCR"""
    try:
        contents = await file.read()
        logger.info(f"[{image_type}] Size: {len(contents)} bytes")
        
        if len(contents) == 0:
            return ""
        
        # Decode image
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            logger.error(f"[{image_type}] Failed to decode image")
            return ""
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Try multiple preprocessing methods and combine results
        texts = []
        
        # Method 1: Simple threshold
        _, thresh1 = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        texts.append(pytesseract.image_to_string(thresh1))
        
        # Method 2: Adaptive threshold
        thresh2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        texts.append(pytesseract.image_to_string(thresh2))
        
        # Method 3: Resize (2x) for better detail
        resized = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        texts.append(pytesseract.image_to_string(resized))
        
        # Method 4: Denoise
        denoised = cv2.fastNlMeansDenoising(gray, h=30)
        texts.append(pytesseract.image_to_string(denoised))
        
        # Choose the longest text (usually best)
        best_text = max(texts, key=len)
        logger.info(f"[{image_type}] OCR extracted {len(best_text)} chars")
        logger.debug(f"[{image_type}] Text sample: {best_text[:200]}...")
        
        return best_text
        
    except Exception as e:
        logger.error(f"[{image_type}] OCR error: {e}")
        return ""

def extract_player_id(text: str) -> str:
    if not text:
        return None
    # Try multiple patterns
    patterns = [
        r'\b\d{10}\b',
        r'ID[:\s]*(\d{10})',
        r'Player[:\s]*(\d{10})',
        r'Phone[:\s]*(\d{10})',
        r'Mobile[:\s]*(\d{10})'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1) if match.groups() else match.group(0)
    return None

def extract_dob(text: str) -> str:
    if not text:
        return None
    match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
    return match.group(1) if match else None

def extract_date(text: str) -> str:
    if not text:
        return None
    
    # Pattern 1: DD/MM/YYYY
    match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
    if match:
        return match.group(1).replace('-', '/')
    
    # Pattern 2: Month DD, YYYY
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
    """Calculate match percentage between extracted text and template"""
    if not extracted_text or not template:
        logger.warning("calculate_match: missing input")
        return 0
    
    # Combine all relevant template fields
    template_text = ' '.join(filter(None, [
        template.get('subject', ''),
        template.get('content', ''),
        template.get('full_html', ''),
        template.get('sender', ''),
        template.get('headline', ''),
        template.get('description', ''),
        template.get('full_text', '')
    ]))
    
    # Normalize text: lowercase, remove punctuation, normalize unicode
    def normalize(text):
        # Convert to lowercase
        text = text.lower()
        # Remove punctuation (keep letters, numbers, spaces)
        text = re.sub(r'[^\w\s]', ' ', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    extracted_norm = normalize(extracted_text)
    template_norm = normalize(template_text)
    
    words_ext = set(extracted_norm.split())
    words_temp = set(template_norm.split())
    
    logger.debug(f"Extracted words count: {len(words_ext)}")
    logger.debug(f"Template words count: {len(words_temp)}")
    
    if not words_temp:
        return 0
    
    common = words_ext.intersection(words_temp)
    common_count = len(common)
    
    logger.debug(f"Common words count: {common_count}")
    
    if common_count == 0:
        # Log samples for debugging
        logger.debug(f"Extracted sample: {extracted_norm[:200]}")
        logger.debug(f"Template sample: {template_norm[:200]}")
        return 0
    
    match_percent = (common_count / len(words_temp)) * 100
    return min(int(match_percent), 100)
