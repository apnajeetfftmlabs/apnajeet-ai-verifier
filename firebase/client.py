import os
import json
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv

load_dotenv()

class FirebaseClient:
    def __init__(self):
        self.initialized = False
        self.init_firebase()
    
    def init_firebase(self):
        try:
            cred_json = os.getenv('FIREBASE_CREDS')
            if cred_json:
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': os.getenv('FIREBASE_DATABASE_URL')
                })
                self.initialized = True
                print("✅ Firebase connected")
        except Exception as e:
            print(f"❌ Firebase error: {e}")
    
    def get_email_template(self, date):
        if not self.initialized:
            return None
        try:
            ref = db.reference(f'email_templates/{date}/client1')
            return ref.get()
        except Exception as e:
            return None
    
    def get_ad_template(self, date):
        if not self.initialized:
            return None
        try:
            ref = db.reference(f'ad_pages/client1/{date}')
            return ref.get()
        except Exception as e:
            return None

firebase_client = FirebaseClient()