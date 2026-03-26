# grib_handler.py - v3.6.0-gmail
from gmail_sender import send_email_gmail
from config import SAILDOCS_EMAIL

def send_to_saildocs(grib_request):
    body = f"send {grib_request}"
    return send_email_gmail(
        subject="GRIB request",
        body=body,
        to_email=SAILDOCS_EMAIL
    )
