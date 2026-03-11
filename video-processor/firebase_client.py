import os, json, firebase_admin
from firebase_admin import credentials, db
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
            if cred_json and db_url and not firebase_admin._apps:
                cred = credentials.Certificate(json.loads(cred_json))
                firebase_admin.initialize_app(cred, {'databaseURL': db_url})
                self.initialized = True
                logger.info("✅ Firebase connected")
        except Exception as e:
            logger.error(f"Firebase error: {e}")
    
    @property
    def initialized(self):
        return self._initialized
