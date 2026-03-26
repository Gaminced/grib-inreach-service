# grib_handler.py - v3.6.1-integrated
# Fusion de la v3.6.0 (Gmail) et de la logique v3.5.7 (Workflow complet)

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

def send_to_saildocs(grib_request):
    """Envoie la requête GRIB via Gmail API (Remplace MailerSend)"""
    print(f"\n{'='*70}", flush=True)
    print(f"📤 ÉTAPE 1/3: ENVOI À SAILDOCS (Gmail API)", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Requête: {grib_request}", flush=True)
    
    body = f"send {grib_request}"
    return send_email_gmail(
        subject="GRIB request",
        body=body,
        to_email=SAILDOCS_EMAIL
    )

def wait_for_saildocs_response(timeout=SAILDOCS_TIMEOUT):
    """Attend la réponse de Saildocs sur la boîte IMAP (Logique v3.5.7)"""
    print(f"\n{'='*70}", flush=True)
    print(f"⏳ ÉTAPE 2/3: ATTENTE RÉPONSE SAILDOCS", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Email attendu: {SAILDOCS_RESPONSE_EMAIL}", flush=True)
    print(f"Timeout: {timeout}s", flush=True)
    
    start_time = time.time()
    check_count = 0
    
    while time.time() - start_time < timeout:
        check_count += 1
        elapsed = int(time.time() - start_time)
        print(f"🔍 Vérification #{check_count} - {elapsed}s", flush=True)
        
        try:
            # Connexion IMAP pour surveiller l'arrivée du fichier
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
            mail.select('inbox')
            
            # Recherche d'emails non lus provenant de Saildocs
            status, messages = mail.search(None, f'(UNSEEN FROM "{SAILDOCS_RESPONSE_EMAIL}")')
            
            if status == 'OK' and messages[0]:
                email_ids = messages[0].split()
                for email_id in email_ids:
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    # Extraction de la pièce jointe GRIB
                    for part in msg.walk():
                        if part.get_content_type() == 'application/octet-stream':
                            grib_data = part.get_payload(decode=True)
                            if grib_data:
                                print(f"✅ GRIB REÇU! ({len(grib_data)} octets)", flush=True)
                                mail.store(email_id, '+FLAGS', '\\Seen')
                                mail.logout()
                                return grib_data
            mail.logout()
        except Exception as e:
            print(f"   ❌ Erreur IMAP: {e}", flush=True)
        
        time.sleep(10) # Pause avant la prochaine vérification
    
    print(f"\n❌ TIMEOUT : Saildocs n'a pas répondu à temps", flush=True)
    return None

def process_grib_request(raw_email_body, inreach_url, mail=None):
    """
    Fonction principale (v3.5.7 améliorée) :
    1. Extrait la requête du corps du message InReach
    2. Envoie la demande à Saildocs via Gmail API
    3. Attend et récupère le fichier GRIB par IMAP
    4. Segmente et renvoie le fichier vers l'unité InReach
    """
    print(f"\n{'='*70}", flush=True)
    print(f"🌊 WORKFLOW GRIB v3.6.1 (Gmail + InReach)", flush=True)
    print(f"{'='*70}", flush=True)
    
    # Nettoyage et extraction de la commande (ex: GFS:14N,20N...)
    grib_request = extract_grib_request(raw_email_body)
    if not grib_request:
        print(f"❌ Erreur : Impossible de lire la requête GRIB dans l'email", flush=True)
        return False
    
    try:
        # Étape 1 : Envoi Gmail
        if not send_to_saildocs(grib_request):
            return False
        
        # Étape 2 : Attente du retour Saildocs
        grib_data = wait_for_saildocs_response()
        if not grib_data:
            return False
        
        # Étape 3 : Encodage (Base64/Segmentation) et envoi InReach
        print(f"\n🔧 ÉTAPE 3/3: ENCODAGE ET ENVOI VERS INREACH", flush=True)
        messages = encode_and_split_grib(grib_data)
        success = send_to_inreach(inreach_url, messages)
        
        if success:
            print(f"✅✅✅ SUCCÈS : GRIB transmis à l'InReach ({len(messages)} segments)", flush=True)
            return True
        else:
            print(f"❌ Échec de l'envoi vers l'URL InReach", flush=True)
            return False
            
    except Exception as e:
        print(f"❌ ERREUR CRITIQUE DANS LE PROCESSUS : {e}", flush=True)
        return False
