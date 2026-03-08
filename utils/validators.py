import re
from datetime import datetime

def validate_player_id(player_id):
    """Check if player ID is 10 digits"""
    if not player_id:
        return False
    return re.match(r'^\d{10}$', player_id) is not None

def validate_date(date_str, format='%d/%m/%Y'):
    """Validate date format"""
    try:
        datetime.strptime(date_str, format)
        return True
    except:
        return False

def extract_player_id(text):
    """Extract 10-digit number from text"""
    if not text:
        return None
    match = re.search(r'\b\d{10}\b', text)
    return match.group(0) if match else None

def extract_profile_date(text):
    """Extract date in DD/MM/YYYY format"""
    if not text:
        return None
    match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', text)
    if match:
        return match.group(1).replace('-', '/')
    return None

def extract_email_date(text):
    """Extract date in Month DD, YYYY format"""
    if not text:
        return None
    match = re.search(r'([A-Z][a-z]+ \d{1,2}, \d{4})', text)
    return match.group(1) if match else None

def dates_match(profile_date, email_date):
    """Check if dates match within 1 day"""
    try:
        profile = datetime.strptime(profile_date, '%d/%m/%Y')
        email = datetime.strptime(email_date, '%B %d, %Y')
        diff = abs((profile - email).days)
        return diff <= 1
    except:
        return False
