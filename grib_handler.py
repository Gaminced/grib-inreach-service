# grib_handler.py - v3.6.4
# - Intègre la limite stricte de 25 messages InReach
# - Notifications de suivi incluses

import time
import imaplib
import email
import sys
from gmail_sender import send_email_gmail
from config import (GARMIN_USERNAME, GARMIN_PASSWORD, SAILDOCS_EMAIL, 
                    SAILDOCS_RESPONSE_EMAIL, IMAP_HOST, IMAP_PORT, SAILDOCS_TIMEOUT)
from utils import encode_and_split_grib
from inreach_sender import send_to_inreach

sys.stdout.flush()

def notify_status(inreach_url, message):
    """Notification rapide pour suivi à distance"""
    print(f"📡 Suivi: {message}", flush=True)
    return send_to_inreach(inreach_url, [message])

def wait_for_saildocs_response(inreach_url, timeout=SAILDOCS_TIMEOUT):
    """Attend le retour de Saildocs par IMAP"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
            mail.select('inbox')
            status, messages = mail.search(None, f'(UNSEEN FROM "{SAILDOCS_RESPONSE_EMAIL}")')
            
            if status == 'OK' and messages[0]:
                for email_id in messages[0].split():
                    _, msg_data = mail.fetch(email_id, '(RFC822)')
                    msg = email.message_from_bytes(msg_data[0][1])
                    for part in msg.walk():
                        if part.get_content_type() == 'application/octet-stream':
                            grib_data = part.get_payload(decode=True)
                            if grib_data:
                                mail.store(email_id, '+FLAGS', '\\Seen')
                                mail.logout()
                                return grib_data
            mail.logout()
        except Exception as e:
            print(f"⚠️ Erreur IMAP: {e}")
        time.sleep(20)
    return None

def process_grib_request(grib_request, inreach_url, mail=None):
    """Workflow complet GRIB avec limite de 25 messages"""
    print(f"\n🌊 TRAITEMENT GRIB: {grib_request}", flush=True)
    
    # 1. Notification initiale
    notify_status(inreach_url, f"📥 Recu. Requete {grib_request.split(':')[0].upper()} en cours...")

    # 2. Envoi Saildocs
    body = f"send {grib_request}"
    success = send_email_gmail(subject="GRIB request", body=body, to_email=SAILDOCS_EMAIL)
    
    if success:
        notify_status(inreach_url, "📤 Requete envoyee a Saildocs. Attente...")
    else:
        notify_status(inreach_url, "❌ Erreur: Echec envoi Gmail (Token?)")
        return False
    
    # 3. Attente du fichier GRIB
    grib_data = wait_for_saildocs_response(inreach_url)
    if not grib_data:
        notify_status(inreach_url, "❌ Timeout: Saildocs ne repond pas.")
        return False

    # 4. Encodage et vérification de la taille
    notify_status(inreach_url, "⚙️ GRIB recu. Analyse de la taille...")
    messages = encode_and_split_grib(grib_data)
    num_msg = len(messages)
    
    # --- LIMITE DE SÉCURITÉ ---
    if num_msg > 25:
        error_msg = f"⚠️ ALERTE: GRIB trop volumineux ({num_msg} msg). Limite: 25. Reduisez la zone ou le nombre de jours."
        print(f"❌ {error_msg}", flush=True)
        notify_status(inreach_url, error_msg)
        return False
    # --------------------------

    # 5. Envoi final si la limite est respectée
    if send_to_inreach(inreach_url, messages):
        print(f"✅ Workflow terminé: {num_msg} messages envoyés.", flush=True)
        return True
    
    return False
