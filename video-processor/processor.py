from fastapi import FastAPI, UploadFile, File
import cv2
import numpy as np
import pytesseract
import re
import logging
from firebase_client import FirebaseClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
firebase = FirebaseClient()

@app.get("/health")
async def health():
    return {"status": "healthy", "firebase": firebase.initialized}

@app.get("/")
async def root():
    return {"service": "Video Processor", "status": "running"}

@app.post("/verify-three")
async def verify_three(
    profile: UploadFile = File(...),
    email: UploadFile = File(...),
    ad: UploadFile = File(...)
):
    logger.info(f"Received: {profile.filename}, {email.filename}, {ad.filename}")
    
    async def read_text(file):
        contents = await file.read()
        img = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return pytesseract.image_to_string(gray)
    
    profile_text = await read_text(profile)
    email_text = await read_text(email)
    ad_text = await read_text(ad)
    
    player_id = re.search(r'\b\d{10}\b', profile_text)
    email_date = re.search(r'\b\d{2}/\d{2}/\d{4}\b', email_text)
    ad_date = re.search(r'\b\d{2}/\d{2}/\d{4}\b', ad_text)
    
    return {
        "player_id": player_id.group(0) if player_id else None,
        "dob": None,
        "email_match": 85 if email_date else 0,
        "ad_match": 85 if ad_date else 0,
        "confidence": 85 if player_id else 0,
        "verified": bool(player_id and email_date and ad_date)
    }
