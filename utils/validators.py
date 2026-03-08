import re
from datetime import datetime

def validate_player_id(player_id):
    return re.match(r'^\d{10}$', player_id) is not None

def validate_date(date_str, format='%d/%m/%Y'):
    try:
        datetime.strptime(date_str, format)
        return True
    except:
        return False

def extract_player_id(text):
    match = re.search(r'\b\d{10}\b', text)
    return match.group(0) if match else None

def extract_profile_date(text):
    match = re.search(r'\b\d{2}/\d{2}/\d{4}\b', text)
    return match.group(0) if match else None

def extract_email_date(text):
    match = re.search(r'[A-Z][a-z]+ \d{1,2}, \d{4}', text)
    return match.group(0) if match else None