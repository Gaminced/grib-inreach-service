# config.py - Gmail API version

import os

VERSION = "3.7.0"
SERVICE_NAME = "GRIB inReach Service"

GARMIN_USERNAME = os.environ.get('GARMIN_USERNAME', 'garminced@gmail.com')
GARMIN_PASSWORD = os.environ.get('GARMIN_PASSWORD')

GMAIL_TOKEN_FILE = "token.pickle"
GMAIL_CREDENTIALS_FILE = "credentials.json"

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993

SAILDOCS_EMAIL = "query@saildocs.com"
SAILDOCS_RESPONSE_EMAIL = "query-reply@saildocs.com"

MAX_MESSAGE_LENGTH = 120
DELAY_BETWEEN_MESSAGES = 5

PLAYWRIGHT_BROWSER_PATH = '/opt/render/project/src/browsers/chromium-1091/chrome-linux/chrome'
PLAYWRIGHT_TIMEOUT = 30000

PORT = int(os.environ.get('PORT', 10000))

SAILDOCS_TIMEOUT = 300

def validate_config():
    errors = []
    if not GARMIN_USERNAME:
        errors.append("GARMIN_USERNAME manquant")
    if not GARMIN_PASSWORD:
        errors.append("GARMIN_PASSWORD manquant")
    return errors
