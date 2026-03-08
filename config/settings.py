import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
    FIREBASE_DATABASE_URL = os.getenv('FIREBASE_DATABASE_URL')
    HF_SPACE_URL = os.getenv('HF_SPACE_URL', 'https://dailyupdate8399-apnajeet-video-verifier.hf.space')
    
    # Thresholds
    MIN_MATCHING_LINES = 10
    MIN_MATCH_SCORE = 20
    AD_MATCH_THRESHOLD = 0.6

settings = Settings()