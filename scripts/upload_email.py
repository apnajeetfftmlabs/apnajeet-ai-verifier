import firebase_admin
from firebase_admin import db, credentials
from datetime import datetime
import json
import sys

def upload_email_template(email_text, client="client1"):
    """Upload email template to Firebase"""
    
    # Split into lines
    lines = [line.strip() for line in email_text.split('\n') if line.strip()]
    
    # Get today's date
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Upload
    ref = db.reference(f'email_templates/{today}/{client}')
    ref.set({
        'lines': lines,
        'line_count': len(lines),
        'uploaded_at': datetime.now().timestamp()
    })
    
    print(f"✅ Uploaded {len(lines)} lines for {today}")

if __name__ == "__main__":
    # Read from command line or file
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            email_text = f.read()
    else:
        email_text = sys.stdin.read()
    
    upload_email_template(email_text)