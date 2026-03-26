from gmail_sender import send_email_gmail
from config import SAILDOCS_EMAIL

def send_to_saildocs(grib_request):
    print("📤 Envoi Gmail API")

    body = f"send {grib_request}"

    return send_email_gmail(
        subject="GRIB request",
        body=body,
        to_email=SAILDOCS_EMAIL
    )
