import cv2
import numpy as np
import json
import re
from .detector import detect_text_regions
from .ocr import extract_text_paddle
from .vision import describe_ad_page

def extract_player_id(text_lines):
    for line in text_lines:
        match = re.search(r'\b\d{10}\b', line)
        if match:
            return match.group(0)
    return None

def extract_profile_date(text_lines):
    for line in text_lines:
        match = re.search(r'\b\d{2}/\d{2}/\d{4}\b', line)
        if match:
            return match.group(0)
    return None

def extract_email_date(text_lines):
    for line in text_lines:
        match = re.search(r'[A-Z][a-z]+ \d{1,2}, \d{4}', line)
        if match:
            return match.group(0)
    return None

def process_video(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    all_texts = []
    player_id = None
    profile_date = None
    email_date = None
    ad_descriptions = []
    
    # Process every 30th frame (1 second intervals)
    for i in range(0, frame_count, int(fps)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret:
            break
        
        texts = extract_text_paddle(frame)
        all_texts.extend(texts)
        
        if not player_id:
            player_id = extract_player_id(texts)
        if not profile_date:
            profile_date = extract_profile_date(texts)
        if not email_date:
            email_date = extract_email_date(texts)
        
        ad_keywords = ['elite trade club', 'subscribe', 'pre-market']
        if any(keyword in ' '.join(texts).lower() for keyword in ad_keywords):
            ad_descriptions.append(describe_ad_page(frame))
    
    cap.release()
    
    all_texts = list(set(all_texts))
    ad_descriptions = list(set(ad_descriptions))
    
    result = {
        "player_id": player_id,
        "profile_date": profile_date,
        "email_date": email_date,
        "email_lines": all_texts[:15],
        "ad_lines": ad_descriptions[:3],
        "full_text": "\n".join(all_texts)
    }
    
    return result