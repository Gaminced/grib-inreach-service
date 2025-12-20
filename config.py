# config.py
"""Configuration centralisée du service GRIB inReach Multi-AI"""

import os

# ==========================================
# VARIABLES D'ENVIRONNEMENT
# ==========================================

GARMIN_USERNAME = os.environ.get('GARMIN_USERNAME', 'garminced@gmail.com')
GARMIN_PASSWORD = os.environ.get('GARMIN_PASSWORD')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')

# ==========================================
# CONFIGURATION EMAIL
# ==========================================

GMAIL_HOST = "smtp.gmail.com"
GMAIL_PORT = 465  # SSL direct
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

# ==========================================
# ADRESSES
# ==========================================

SAILDOCS_EMAIL = "query@saildocs.com"
SAILDOCS_RESPONSE_EMAIL = "query-reply@saildocs.com"

# ==========================================
# CONFIGURATION INREACH
# ==========================================

MAX_MESSAGE_LENGTH = 120
DELAY_BETWEEN_MESSAGES = 5

INREACH_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Origin': 'https://explore.garmin.com',
    'Referer': 'https://explore.garmin.com/'
}

INREACH_COOKIES = {}

# ==========================================
# CONFIGURATION SERVEUR
# ==========================================

PORT = int(os.environ.get('PORT', 10000))

# ==========================================
# VÉRIFICATION CREDENTIALS
# ==========================================

def check_credentials():
    """Vérifie que les identifiants essentiels sont configurés"""
    if not GARMIN_USERNAME or not GARMIN_PASSWORD:
        print("❌ ERREUR: GARMIN_USERNAME et GARMIN_PASSWORD requis")
        return False
    print(f"✅ Identifiants Garmin: {GARMIN_USERNAME}")
    return True
