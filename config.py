# config.py - v3.7.2-gmail
import os

VERSION = "3.7.2"
VERSION_DATE = "2026-03-26"
SERVICE_NAME = "GRIB inReach Service"

GARMIN_USERNAME = os.environ.get('GARMIN_USERNAME', 'garminced@gmail.com')
GARMIN_PASSWORD = os.environ.get('GARMIN_PASSWORD')

GMAIL_TOKEN_FILE = "token.pickle"
GMAIL_CREDENTIALS_FILE = "credentials.json"

MAILERSEND_API_KEY = os.environ.get('MAILERSEND_API_KEY')

ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

SAILDOCS_EMAIL = "query@saildocs.com"
SAILDOCS_RESPONSE_EMAIL = "query-reply@saildocs.com"

MAX_MESSAGE_LENGTH = 120
DELAY_BETWEEN_MESSAGES = 5

INREACH_HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'User-Agent': 'Mozilla/5.0'
}

PLAYWRIGHT_BROWSER_PATH = '/opt/render/project/src/browsers/chromium-1091/chrome-linux/chrome'
PLAYWRIGHT_TIMEOUT = 30000

PORT = int(os.environ.get('PORT', 10000))
FLASK_DEBUG = False

CHECK_INTERVAL_MINUTES = 5
SAILDOCS_TIMEOUT = 300

def validate_config():
    errors = []
    if not GARMIN_USERNAME:
        errors.append("GARMIN_USERNAME manquant")
    if not GARMIN_PASSWORD:
        errors.append("GARMIN_PASSWORD manquant")
    if not os.path.exists(GMAIL_TOKEN_FILE):
        errors.append("token.pickle manquant")
    if not os.path.exists(GMAIL_CREDENTIALS_FILE):
        errors.append("credentials.json manquant")
    return errors

def get_config_status():
    """Statut configuration"""
    return {
        "version": VERSION,
        "version_date": VERSION_DATE,
        "garmin_username": GARMIN_USERNAME if GARMIN_USERNAME else "Non configuré",
        "anthropic_configured": "✅ Oui" if ANTHROPIC_API_KEY else "❌ Non",
        "mistral_configured": "✅ Oui" if MISTRAL_API_KEY else "❌ Non",
        "check_interval": f"{CHECK_INTERVAL_MINUTES} minutes"
    }

