import easyocr
import cv2
import numpy as np
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Initialize EasyOCR
try:
    reader = easyocr.Reader(['en'], gpu=False)
    logger.info("EasyOCR initialized successfully")
except Exception as e:
    logger.error(f"EasyOCR initialization failed: {str(e)}")
    reader = None

def extract_text_from_image(image):
    """Extract all text from image using EasyOCR"""
    if reader is None:
        return []
    
    try:
        results = reader.readtext(image)
        texts = [result[1] for result in results if result[2] > 0.5]  # confidence > 0.5
        return texts
    except Exception as e:
        logger.error(f"OCR error: {str(e)}")
        return []

def extract_player_id(texts):
    """Find 10-digit Player ID in text"""
    for text in texts:
        match = re.search(r'\b\d{10}\b', text)
        if match:
            return match.group(0)
    return None

def extract_profile_date(texts):
    """Find date in DD/MM/YYYY format"""
    for text in texts:
        match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
        if match:
            # Convert to standard format
            date_str = match.group(1).replace('-', '/')
            return date_str
    return None

def extract_email_date(texts):
    """Find email date like 'March 7, 2026' or '07/03/2026'"""
    for text in texts:
        # Try Month DD, YYYY format
        match = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4})', text)
        if match:
            return match.group(1)
        
        # Try DD/MM/YYYY format
        match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', text)
        if match:
            return match.group(1)
    return None

def extract_email_content(texts):
    """Extract meaningful email lines"""
    email_lines = []
    keywords = ['dear', 'reader', 'gold', 'stansberry', 'cramer', 'investment', 
                'stock', 'market', 'price', 'fund', 'dollars', 'billion']
    
    for text in texts:
        if len(text) > 20:  # Only meaningful lines
            text_lower = text.lower()
            if any(keyword in text_lower for keyword in keywords):
                email_lines.append(text)
    
    return email_lines[:10]  # Max 10 lines

def extract_ad_content(texts):
    """Extract ad page content"""
    ad_lines = []
    keywords = ['elite trade club', 'subscribe', 'newsletter', 'click', 'sign up',
                'register', 'free', 'join', 'start your day', 'pre-market']
    
    for text in texts:
        if len(text) > 15:
            text_lower = text.lower()
            if any(keyword in text_lower for keyword in keywords):
                ad_lines.append(text)
    
    return ad_lines[:5]  # Max 5 lines
