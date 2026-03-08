import os
import json
import firebase_admin
from firebase_admin import credentials, db
import logging

logger = logging.getLogger(__name__)

class FirebaseClient:
    def __init__(self):
        self.initialized = False
        self.init_firebase()
    
    def init_firebase(self):
        try:
            # Get credentials from environment variable
            cred_json = os.getenv('FIREBASE_CREDS')
            db_url = os.getenv('FIREBASE_DATABASE_URL')
            
            if cred_json and db_url:
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': db_url
                })
                self.initialized = True
                logger.info("✅ Firebase connected successfully")
            else:
                logger.warning("⚠️ Firebase credentials not found in environment")
                
        except Exception as e:
            logger.error(f"❌ Firebase initialization error: {str(e)}")
    
    def get_email_template(self, date):
        """Get email template for specific date"""
        if not self.initialized:
            return None
        try:
            ref = db.reference(f'email_templates/{date}/client1')
            return ref.get()
        except Exception as e:
            logger.error(f"Firebase email template error: {str(e)}")
            return None
    
    def get_ad_template(self, date):
        """Get ad template for specific date"""
        if not self.initialized:
            return None
        try:
            ref = db.reference(f'ad_pages/client1/{date}')
            return ref.get()
        except Exception as e:
            logger.error(f"Firebase ad template error: {str(e)}")
            return None

# Global instance
firebase_client = FirebaseClient()
