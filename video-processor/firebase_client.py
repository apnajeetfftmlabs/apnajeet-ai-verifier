# [Filename: video-processor/firebase_client.py]
import os
import json
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FirebaseClient:
    """Firebase client for template storage and player validation"""
    
    def __init__(self):
        self.initialized = False
        self.init_firebase()
    
    def init_firebase(self):
        """Initialize Firebase with credentials from environment"""
        try:
            # Get credentials from environment
            cred_json = os.getenv('FIREBASE_CREDS')
            db_url = os.getenv('FIREBASE_DATABASE_URL')
            
            if not cred_json or not db_url:
                logger.warning("Firebase credentials not found in environment")
                return
            
            # Parse JSON credentials
            try:
                cred_dict = json.loads(cred_json)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid Firebase credentials JSON: {e}")
                return
            
            # Initialize Firebase
            if not firebase_admin._apps:
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': db_url
                })
            
            self.initialized = True
            logger.info("✅ Firebase initialized successfully")
            
        except Exception as e:
            logger.error(f"Firebase initialization error: {e}")
    
    def validate_player(self, player_id: str) -> bool:
        """
        Check if player ID exists in database
        
        Args:
            player_id: 10-digit player ID
        
        Returns:
            True if player exists
        """
        if not self.initialized:
            return False
        
        try:
            ref = db.reference(f'players/{player_id}')
            player_data = ref.get()
            
            if player_data:
                logger.info(f"✅ Valid player ID: {player_id}")
                return True
            else:
                logger.info(f"❌ Invalid player ID: {player_id}")
                return False
                
        except Exception as e:
            logger.error(f"Player validation error: {e}")
            return False
    
    def get_email_template(self, date: str) -> dict:
        """
        Get email template for specific date
        
        Args:
            date: Date string (DD/MM/YYYY or YYYY-MM-DD)
        
        Returns:
            Template data or None
        """
        if not self.initialized:
            return None
        
        # Normalize date to YYYY-MM-DD for Firebase
        if '/' in date:
            parts = date.split('/')
            if len(parts) == 3:
                date_key = f"{parts[2]}-{parts[1]}-{parts[0]}"
            else:
                date_key = date
        else:
            date_key = date
        
        try:
            ref = db.reference(f'email_templates/{date_key}')
            template = ref.get()
            
            if template:
                logger.info(f"✅ Email template found for {date_key}")
                return template
            else:
                logger.info(f"ℹ️ No email template for {date_key}")
                return None
                
        except Exception as e:
            logger.error(f"Get email template error: {e}")
            return None
    
    def get_ad_template(self, date: str) -> dict:
        """
        Get ad template for specific date
        
        Args:
            date: Date string (DD/MM/YYYY or YYYY-MM-DD)
        
        Returns:
            Template data or None
        """
        if not self.initialized:
            return None
        
        # Normalize date
        if '/' in date:
            parts = date.split('/')
            if len(parts) == 3:
                date_key = f"{parts[2]}-{parts[1]}-{parts[0]}"
            else:
                date_key = date
        else:
            date_key = date
        
        try:
            ref = db.reference(f'ad_templates/{date_key}')
            template = ref.get()
            
            if template:
                logger.info(f"✅ Ad template found for {date_key}")
                return template
            else:
                logger.info(f"ℹ️ No ad template for {date_key}")
                return None
                
        except Exception as e:
            logger.error(f"Get ad template error: {e}")
            return None
    
    def save_verification(self, data: dict) -> str:
        """
        Save verification result to Firebase
        
        Args:
            data: Verification data
        
        Returns:
            Reference ID
        """
        if not self.initialized:
            return None
        
        try:
            # Generate ID
            player_id = data.get('player_id', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ref_id = f"{player_id}_{timestamp}"
            
            # Save to Firebase
            ref = db.reference(f'verifications/{ref_id}')
            ref.set(data)
            
            logger.info(f"✅ Verification saved: {ref_id}")
            return ref_id
            
        except Exception as e:
            logger.error(f"Save verification error: {e}")
            return None
    
    def save_template(self, date: str, template_type: str, content: dict, image_bytes: bytes = None):
        """
        Save template to Firebase
        
        Args:
            date: Date string (DD/MM/YYYY)
            template_type: 'email' or 'ad'
            content: Template content
            image_bytes: Optional image bytes
        """
        if not self.initialized:
            return False
        
        # Normalize date
        if '/' in date:
            parts = date.split('/')
            date_key = f"{parts[2]}-{parts[1]}-{parts[0]}"
        else:
            date_key = date
        
        try:
            # Save to Realtime DB
            if template_type == 'email':
                ref = db.reference(f'email_templates/{date_key}')
            else:
                ref = db.reference(f'ad_templates/{date_key}')
            
            ref.set(content)
            logger.info(f"✅ {template_type} template saved for {date_key}")
            return True
            
        except Exception as e:
            logger.error(f"Save template error: {e}")
            return False
