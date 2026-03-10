# [Filename: video_processor/firebase_client.py]
import os
import json
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FirebaseClient:
    def __init__(self):
        self.initialized = False
        self.init_firebase()
    
    def init_firebase(self):
        try:
            cred_json = os.getenv('FIREBASE_CREDS')
            db_url = os.getenv('FIREBASE_DATABASE_URL')
            
            if cred_json and db_url:
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': db_url
                })
                self.initialized = True
                logger.info("✅ Firebase connected")
        except Exception as e:
            logger.error(f"Firebase error: {e}")
    
    def validate_player(self, player_id):
        if not self.initialized:
            return False
        try:
            ref = db.reference(f'players/{player_id}')
            return ref.get() is not None
        except:
            return False
    
    def get_email_template(self, date):
        if not self.initialized:
            return None
        try:
            ref = db.reference(f'email_templates/{date}')
            return ref.get()
        except:
            return None
    
    def get_ad_template(self, date):
        if not self.initialized:
            return None
        try:
            ref = db.reference(f'ad_templates/{date}')
            return ref.get()
        except:
            return None
    
    def save_verification(self, data):
        if not self.initialized:
            return
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            player_id = data.get('player_id', 'unknown')
            ref = db.reference(f'verifications/{player_id}_{timestamp}')
            ref.set(data)
        except:
            pass
