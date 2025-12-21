# config.py - v3.0.1
"""Configuration centralisée pour GRIB inReach Service"""

import os

# ==========================================
# INFORMATIONS VERSION
# ==========================================
VERSION = "3.0.1"
VERSION_DATE = "2025-12-21"
SERVICE_NAME = "GRIB inReach Service"

# ==========================================
# CREDENTIALS GARMIN
# ==========================================
GARMIN_USERNAME = os.environ.get('GARMIN_USERNAME', 'garminced@gmail.com')
GARMIN_PASSWORD = os.environ.get('GARMIN_PASSWORD')

# ==========================================
# API KEYS
# ==========================================
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')

# ==========================================
# EMAIL CONFIGURATION
# ==========================================
IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

SAILDOCS_EMAIL = "query@saildocs.com"
SAILDOCS_RESPONSE_EMAIL = "query-reply@saildocs.com"  # CRITIQUE: Réponses viennent de query-REPLY

# ==========================================
# INREACH CONFIGURATION
# ==========================================
MAX_MESSAGE_LENGTH = 120
DELAY_BETWEEN_MESSAGES = 5

# Headers HTTP pour requêtes Garmin
INREACH_HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# ==========================================
# PLAYWRIGHT CONFIGURATION
# ==========================================
PLAYWRIGHT_BROWSER_PATH = '/opt/render/project/src/browsers/chromium-1091/chrome-linux/chrome'
PLAYWRIGHT_TIMEOUT = 30000  # 30 secondes

# ==========================================
# FLASK CONFIGURATION
# ==========================================
PORT = int(os.environ.get('PORT', 10000))
FLASK_DEBUG = False

# ==========================================
# SCHEDULER CONFIGURATION
# ==========================================
CHECK_INTERVAL_MINUTES = 5  # Vérification toutes les 5 minutes

# ==========================================
# SAILDOCS CONFIGURATION
# ==========================================
SAILDOCS_TIMEOUT = 300  # 5 minutes max d'attente pour réponse

# ==========================================
# VALIDATION
# ==========================================
def validate_config():
    """Vérifie que la configuration est complète"""
    errors = []
    
    if not GARMIN_USERNAME:
        errors.append("GARMIN_USERNAME manquant")
    
    if not GARMIN_PASSWORD:
        errors.append("GARMIN_PASSWORD manquant")
    
    if not SENDGRID_API_KEY:
        errors.append("SENDGRID_API_KEY manquant (requis pour Saildocs)")
    
    return errors

def get_config_status():
    """Retourne le statut de configuration pour /status"""
    return {
        "version": VERSION,
        "version_date": VERSION_DATE,
        "garmin_username": GARMIN_USERNAME if GARMIN_USERNAME else "Non configuré",
        "sendgrid_configured": "✅ Oui" if SENDGRID_API_KEY else "❌ Non",
        "anthropic_configured": "✅ Oui" if ANTHROPIC_API_KEY else "❌ Non",
        "mistral_configured": "✅ Oui" if MISTRAL_API_KEY else "❌ Non",
        "check_interval": f"{CHECK_INTERVAL_MINUTES} minutes"
    }
