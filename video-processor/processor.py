# [Filename: video_processor/processor.py]
from fastapi import FastAPI, UploadFile, File
import cv2
import numpy as np
import pytesseract
import re
import os
import logging
from firebase_client import FirebaseClient
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Video Processor")
firebase = FirebaseClient()

@app.get("/")
async def root():
    return {"service": "Video Processor", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/process")
async def process_image(file: UploadFile = File(...)):
    """Process screenshot and extract information"""
    try:
        # Read image
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Extract text
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray)
        
        # Find player ID (10 digits)
        player_id = None
        match = re.search(r'\b\d{10}\b', text)
        if match:
            player_id = match.group(0)
        
        # Find date
        date = None
        match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
        if match:
            date = match.group(1)
        
        # Check in Firebase
        player_valid = False
        email_match = 0
        ad_match = 0
        
        if player_id:
            player_valid = firebase.validate_player(player_id)
        
        if date:
            # Normalize date
            if '/' in date:
                parts = date.split('/')
                date_key = f"{parts[2]}-{parts[1]}-{parts[0]}"
            else:
                date_key = date
            
            # Get templates
            email_template = firebase.get_email_template(date_key)
            ad_template = firebase.get_ad_template(date_key)
            
            # Simple matching
            if email_template:
                email_match = 85  # Mock score
            
            if ad_template:
                ad_match = 90  # Mock score
        
        result = {
            "player_id": player_id,
            "player_valid": player_valid,
            "date": date,
            "matches": {
                "email_match": email_match,
                "ad_match": ad_match
            },
            "confidence": (email_match + ad_match) / 2 if (email_match + ad_match) > 0 else 0,
            "text_preview": text[:200]
        }
        
        # Save to Firebase
        firebase.save_verification(result)
        
        return result
        
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return {"error": str(e)}
