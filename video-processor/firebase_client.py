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
        self._init_firebase()
    
    def _init_firebase(self):
        try:
            cred_json = os.getenv('FIREBASE_CREDS')
            db_url = os.getenv('FIREBASE_DATABASE_URL')
            
            if not cred_json or not db_url:
                logger.warning("Firebase credentials not found")
                return
            
            cred_dict = json.loads(cred_json)
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {'databaseURL': db_url})
            self.initialized = True
            logger.info("✅ Firebase initialized")
        except Exception as e:
            logger.error(f"Firebase init error: {e}")
    
    def get_email_template(self, date):
        if not self.initialized:
            return None
        try:
            ref = db.reference(f'email_templates/{date}')
            return ref.get()
        except Exception as e:
            logger.error(f"Error getting email template: {e}")
            return None
    
    def get_ad_template(self, date):
        if not self.initialized:
            return None
        try:
            ref = db.reference(f'ad_templates/{date}')
            return ref.get()
        except Exception as e:
            logger.error(f"Error getting ad template: {e}")
            return None
    
    def validate_player(self, player_id):
        if not self.initialized:
            return False
        try:
            ref = db.reference(f'players/{player_id}')
            return ref.get() is not None
        except Exception as e:
            logger.error(f"Error validating player: {e}")
            return False
    
    def save_verification(self, data):
        if not self.initialized:
            return
        try:
            player_id = data.get('player_id', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ref = db.reference(f'verifications/{player_id}_{timestamp}')
            ref.set(data)
        except Exception as e:
            logger.error(f"Error saving verification: {e}")
