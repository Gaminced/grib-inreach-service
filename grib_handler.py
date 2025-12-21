# grib_handler.py - v3.0.2
"""Module de traitement des requêtes GRIB - Email Saildocs CORRIGÉ"""

import time
import imaplib
import email
import sys
from config import (GARMIN_USERNAME, GARMIN_PASSWORD, SENDGRID_API_KEY,
                    SAILDOCS_EMAIL, SAILDOCS_RESPONSE_EMAIL, IMAP_HOST, IMAP_PORT, SAILDOCS_TIMEOUT)
from utils import encode_and_split_grib
from inreach_sender import send_to_inreach

# Forcer stdout non-bufferisé
sys.stdout.flush()


def send_to_saildocs(grib_request):
    """Envoie requête GRIB à Saildocs par email"""
    print(f"\n{'='*70}", flush=True)
    print(f"📤 ÉTAPE 1/3: ENVOI À SAILDOCS", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Requête: {grib_request}", flush=True)
    
    if not SENDGRID_API_KEY:
        print("❌ SendGrid requis pour Saildocs", flush=True)
        return False
    
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        email_body = f"send {grib_request}"
        
        print(f"📧 Création email SendGrid...", flush=True)
        print(f"   De: {GARMIN_USERNAME}", flush=True)
        print(f"   À: {SAILDOCS_EMAIL}", flush=True)
        print(f"   Corps: {email_body}", flush=True)
        
        message = Mail(
            from_email=GARMIN_USERNAME,
            to_emails=SAILDOCS_EMAIL,
            subject='send',
            plain_text_content=email_body
        )
        
        print(f"📤 Envoi email...", flush=True)
        response = sg.send(message)
        
        print(f"📬 SendGrid Status: {response.status_code}", flush=True)
        
        if response.status_code in [200, 201, 202]:
            print(f"✅ Demande envoyée avec succès", flush=True)
            print(f"✅ Réponse attendue de: {SAILDOCS_RESPONSE_EMAIL}", flush=True)
            return True
        else:
            print(f"❌ Erreur: Status {response.status_code}", flush=True)
            return False
        
    except Exception as e:
        print(f"❌ Erreur: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False


def wait_for_saildocs_response(timeout=SAILDOCS_TIMEOUT):
    """Attend réponse de Saildocs - CHERCHE query-reply@saildocs.com"""
    print(f"\n{'='*70}", flush=True)
    print(f"⏳ ÉTAPE 2/3: ATTENTE RÉPONSE SAILDOCS", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Email attendu: {SAILDOCS_RESPONSE_EMAIL}", flush=True)
    print(f"Timeout: {timeout}s ({timeout//60} min)", flush=True)
    print(f"{'='*70}\n", flush=True)
    
    start_time = time.time()
    check_count = 0
    
    while time.time() - start_time < timeout:
        check_count += 1
        elapsed = int(time.time() - start_time)
        
        print(f"🔍 Vérification #{check_count} - {elapsed}s", flush=True)
        
        try:
            print(f"   📧 Connexion IMAP...", flush=True)
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
            mail.select('inbox')
            print(f"   ✅ IMAP OK", flush=True)
            
            # CRITIQUE: Chercher query-REPLY@saildocs.com
            print(f"   🔎 Recherche: {SAILDOCS_RESPONSE_EMAIL}...", flush=True)
            status, messages = mail.search(None, f'(UNSEEN FROM "{SAILDOCS_RESPONSE_EMAIL}")')
            
            if status == 'OK':
                if messages[0]:
                    email_ids = messages[0].split()
                    print(f"   ✅ {len(email_ids)} email(s) trouvé(s)!", flush=True)
                    
                    for email_id in email_ids:
                        print(f"\n   📩 Email ID: {email_id.decode()}", flush=True)
                        
                        status, msg_data = mail.fetch(email_id, '(RFC822)')
                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)
                        
                        subject = msg.get('Subject', 'No subject')
                        print(f"      Sujet: {subject}", flush=True)
                        print(f"      📎 Pièces jointes...", flush=True)
                        
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            filename = part.get_filename()
                            
                            if filename:
                                print(f"         📄 {filename} ({content_type})", flush=True)
                            
                            if content_type == 'application/octet-stream':
                                grib_data = part.get_payload(decode=True)
                                
                                if grib_data and len(grib_data) > 0:
                                    print(f"\n{'='*70}", flush=True)
                                    print(f"✅ GRIB REÇU!", flush=True)
                                    print(f"{'='*70}", flush=True)
                                    print(f"Taille: {len(grib_data)} octets", flush=True)
                                    print(f"Attente: {elapsed}s", flush=True)
                                    print(f"{'='*70}\n", flush=True)
                                    
                                    mail.store(email_id, '+FLAGS', '\\Seen')
                                    mail.logout()
                                    return grib_data
                else:
                    print(f"   📭 Aucun email pour l'instant", flush=True)
            
            mail.logout()
            print(f"   🔌 Déconnexion\n", flush=True)
            
        except Exception as e:
            print(f"   ❌ Erreur: {e}", flush=True)
        
        if elapsed < timeout - 10:
            print(f"   ⏸️  Attente 10s...\n", flush=True)
            time.sleep(10)
        else:
            break
    
    print(f"\n❌ TIMEOUT après {timeout}s\n", flush=True)
    return None


def process_grib_request(grib_request, inreach_url, reply_email=None):
    """Traite requête GRIB complète"""
    print(f"\n{'='*70}", flush=True)
    print(f"🌊 TRAITEMENT GRIB", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Requête: {grib_request}", flush=True)
    print(f"URL: {inreach_url}", flush=True)
    print(f"{'='*70}\n", flush=True)
    
    try:
        if not send_to_saildocs(grib_request):
            return False
        
        grib_data = wait_for_saildocs_response()
        if not grib_data:
            return False
        
        print(f"\n{'='*70}", flush=True)
        print(f"🔧 ÉTAPE 3/3: ENCODAGE ET ENVOI", flush=True)
        print(f"{'='*70}\n", flush=True)
        
        messages = encode_and_split_grib(grib_data)
        success = send_to_inreach(inreach_url, messages, reply_email)
        
        if success:
            print(f"\n✅✅✅ SUCCÈS ({len(messages)} msg) ✅✅✅\n", flush=True)
            return True
        else:
            print(f"\n❌ Échec envoi inReach\n", flush=True)
            return False
            
    except Exception as e:
        print(f"❌ ERREUR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False
