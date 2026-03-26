import base64
import pickle
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from config import GMAIL_TOKEN_FILE, GARMIN_USERNAME

def send_email_gmail(subject, body, to_email):
    try:
        with open(GMAIL_TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

        service = build('gmail', 'v1', credentials=creds)

        message = MIMEText(body)
        message['to'] = to_email
        message['from'] = GARMIN_USERNAME
        message['subject'] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        service.users().messages().send(
            userId="me",
            body={'raw': raw}
        ).execute()

        print("✅ Gmail envoyé")
        return True

    except Exception as e:
        print(f"❌ Gmail erreur: {e}")
        return False
