# grib_handler.py - v3.6.2-notif
# Intègre notifications InReach et correction du blocage Gmail

import time
import imaplib
import email
import sys
from gmail_sender import send_email_gmail
from config import (GARMIN_USERNAME, GARMIN_PASSWORD, SAILDOCS_EMAIL, 
                    SAILDOCS_RESPONSE_EMAIL, IMAP_HOST, IMAP_PORT, SAILDOCS_TIMEOUT)
from utils import encode_and_split_grib
from inreach_sender import send_to_inreach
from inreach_cleaner_final import extract_grib_request

sys.stdout.flush()

def notify_status(inreach_url, message):
    """Envoie un message de statut rapide à l'InReach pour suivi à distance"""
    print(f"📡 Notification InReach: {message}", flush=True)
    return send_to_inreach(inreach_url, [message])

def send_to_saildocs(grib_request):
    """Envoie la requête GRIB via Gmail API"""
    print(f"\n{'='*70}", flush=True)
    print(f"📤 ÉTAPE 1/3: ENVOI À SAILDOCS (Gmail API)", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Requête: {grib_request}", flush=True)
    
    body = f"send {grib_request}"
    try:
        success = send_email_gmail(
            subject="GRIB request",
            body=body,
            to_email=SAILDOCS_EMAIL
        )
        if success:
            print("✅ Email envoyé avec succès via Gmail", flush=True)
        return success
    except Exception as e:
        print(f"❌ Erreur critique Gmail: {e}", flush=True)
        return False

def wait_for_saildocs_response(inreach_url, timeout=SAILDOCS_TIMEOUT):
    """Attend la réponse Saildocs via IMAP"""
    print(f"\n{'='*70}", flush=True)
    print(f"⏳ ÉTAPE 2/3: ATTENTE RÉPONSE SAILDOCS", flush=True)
    print(f"{'='*70}", flush=True)
    
    start_time = time.time()
    check_count = 0
    
    while time.time() - start_time < timeout:
        check_count += 1
        elapsed = int(time.time() - start_time)
        print(f"🔍 Vérification #{check_count} - {elapsed}s", flush=True)
        
        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
            mail.select('inbox')
            
            status, messages = mail.search(None, f'(UNSEEN FROM "{SAILDOCS_RESPONSE_EMAIL}")')
            
            if status == 'OK' and messages[0]:
                email_ids = messages[0].split()
                for email_id in email_ids:
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    msg = email.message_from_bytes(msg_data[0][1])
                    
                    for part in msg.walk():
                        if part.get_content_type() == 'application/octet-stream':
                            grib_data = part.get_payload(decode=True)
                            if grib_data:
                                print(f"✅ GRIB REÇU!", flush=True)
                                mail.store(email_id, '+FLAGS', '\\Seen')
                                mail.logout()
                                return grib_data
            mail.logout()
        except Exception as e:
            print(f"   ❌ Erreur IMAP: {e}", flush=True)
        
        time.sleep(20)
    
    notify_status(inreach_url, "❌ Erreur: Saildocs n'a pas repondu (Timeout).")
    return None

def process_grib_request(raw_email_body, inreach_url, mail=None):
    """Workflow complet avec notifications InReach à chaque étape"""
    print(f"\n🌊 DEMARRAGE WORKFLOW GRIB v3.6.2", flush=True)
    
    # 1. Notification de début
    notify_status(inreach_url, "📥 Recu. Analyse de la requete...")
    
    grib_request = extract_grib_request(raw_email_body)
    if not grib_request:
        notify_status(inreach_url, "❌ Erreur: Requete GRIB illisible.")
        return False
    
    # 2. Envoi Saildocs & Notification
    if send_to_saildocs(grib_request):
        notify_status(inreach_url, f"📤 Requete envoyee a Saildocs. Attente du fichier...")
    else:
        notify_status(inreach_url, "❌ Erreur: Echec de l'envoi Gmail.")
        return False
    
    # 3. Attente du fichier
    grib_data = wait_for_saildocs_response(inreach_url)
    if not grib_data:
        return False
    
    # 4. Encodage et Envoi final
    notify_status(inreach_url, "⚙️ GRIB recu. Envoi des segments...")
    try:
        messages = encode_and_split_grib(grib_data)
        success = send_to_inreach(inreach_url, messages)
        
        if success:
            print(f"✅✅✅ SUCCÈS", flush=True)
            return True
        else:
            notify_status(inreach_url, "❌ Erreur: Echec envoi InReach final.")
            return False
    except Exception as e:
        print(f"❌ Erreur technique: {e}", flush=True)
        return False
