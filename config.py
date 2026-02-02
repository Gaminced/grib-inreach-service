# config.py - v3.5.0
"""Configuration centralisée - Mailersend (remplace Resend)"""

import os

# ==========================================
# VERSION
# ==========================================
VERSION = "3.5.0"
VERSION_DATE = "2026-02-02"
SERVICE_NAME = "GRIB inReach Service"

# ==========================================
# CREDENTIALS GARMIN
# ==========================================
GARMIN_USERNAME = os.environ.get('GARMIN_USERNAME', 'garminced@gmail.com')
GARMIN_PASSWORD = os.environ.get('GARMIN_PASSWORD')

# ==========================================
# API KEYS
# ==========================================
# MAILERSEND(remplace Resend)
MAILERSEND_API_KEY = os.environ.get('MAILERSEND_API_KEY')  # Format: key-xxxxx
#MAILGUN_DOMAIN = os.environ.get('MAILGUN_DOMAIN')    # Format: sandboxXXX.mailgun.org

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')

# ==========================================
# EMAIL CONFIGURATION
# ==========================================
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

SAILDOCS_EMAIL = "query@saildocs.com"
SAILDOCS_RESPONSE_EMAIL = "query-reply@saildocs.com"

# ==========================================
# INREACH CONFIGURATION
# ==========================================
MAX_MESSAGE_LENGTH = 120
DELAY_BETWEEN_MESSAGES = 5

INREACH_HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# ==========================================
# PLAYWRIGHT CONFIGURATION
# ==========================================
PLAYWRIGHT_BROWSER_PATH = '/opt/render/project/src/browsers/chromium-1091/chrome-linux/chrome'
PLAYWRIGHT_TIMEOUT = 30000

# ==========================================
# FLASK CONFIGURATION
# ==========================================
PORT = int(os.environ.get('PORT', 10000))
FLASK_DEBUG = False

# ==========================================
# SCHEDULER CONFIGURATION
# ==========================================
CHECK_INTERVAL_MINUTES = 5

# ==========================================
# SAILDOCS CONFIGURATION
# ==========================================
SAILDOCS_TIMEOUT = 300

# ==========================================
# VALIDATION
# ==========================================
def validate_config():
    """Vérifie configuration"""
    errors = []
    
    if not GARMIN_USERNAME:
        errors.append("GARMIN_USERNAME manquant")
    if not GARMIN_PASSWORD:
        errors.append("GARMIN_PASSWORD manquant")
    if not MAILERSEND_API_KEY:
        errors.append("MAILERSEND_API_KEY manquant")
    
    return errors

def get_config_status():
    """Statut configuration"""
    return {
        "version": VERSION,
        "version_date": VERSION_DATE,
        "garmin_username": GARMIN_USERNAME if GARMIN_USERNAME else "Non configuré",
        "mailersend_configured": "✅ Oui" if MAILERSEND_API_KEY else "❌ Non",
        "anthropic_configured": "✅ Oui" if ANTHROPIC_API_KEY else "❌ Non",
        "mistral_configured": "✅ Oui" if MISTRAL_API_KEY else "❌ Non",
        "check_interval": f"{CHECK_INTERVAL_MINUTES} minutes"
    }
