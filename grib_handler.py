# grib_handler.py - v3.0.0
"""Module de traitement des requêtes GRIB"""

import time
import imaplib
import email
from config import (GARMIN_USERNAME, GARMIN_PASSWORD, SENDGRID_API_KEY,
                    SAILDOCS_EMAIL, IMAP_HOST, IMAP_PORT, SAILDOCS_TIMEOUT)
from utils import encode_and_split_grib
from inreach_sender import send_to_inreach


def send_to_saildocs(grib_request):
    """
    Envoie requête GRIB à Saildocs par email
    IMPORTANT: Envoie SEULEMENT la requête pure, sans signature ni URL
    
    Args:
        grib_request: Requête GRIB pure (ex: Gfs:8N,9N,80W,79W|1,1|0,3|WIND)
        
    Returns:
        bool: True si succès
    """
    print(f"📤 Envoi à Saildocs...")
    print(f"   Requête: {grib_request}")
    
    if not SENDGRID_API_KEY:
        print("❌ SendGrid requis pour Saildocs")
        return False
    
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        
        # CRITIQUE: Envoyer SEULEMENT "send <requête>"
        # PAS de signature, PAS d'URL, PAS d'autre texte
        email_body = f"send {grib_request}"
        
        message = Mail(
            from_email=GARMIN_USERNAME,
            to_emails=SAILDOCS_EMAIL,
            subject='send',
            plain_text_content=email_body
        )
        
        response = sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            print(f"✅ Demande GRIB envoyée à Saildocs")
            print(f"   Corps email: {email_body}")
            return True
        else:
            print(f"❌ Erreur SendGrid: {response.status_code}")
            return False
        
    except Exception as e:
        print(f"❌ Erreur envoi Saildocs: {e}")
        return False


def wait_for_saildocs_response(timeout=SAILDOCS_TIMEOUT):
    """
    Attend réponse de Saildocs avec fichier GRIB
    
    Args:
        timeout: Temps max d'attente en secondes
        
    Returns:
        bytes: Données GRIB ou None
    """
    print(f"⏳ Attente réponse Saildocs (max {timeout}s)...")
    
    start_time = time.time()
    check_count = 0
    
    while time.time() - start_time < timeout:
        check_count += 1
        elapsed = int(time.time() - start_time)
        print(f"   ⏱️  {elapsed}s écoulées... (vérification #{check_count})")
        
        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            mail.login(GARMIN_USERNAME, GARMIN_PASSWORD)
            mail.select('inbox')
            
            # Chercher emails non lus de Saildocs
            status, messages = mail.search(None, '(UNSEEN FROM "query@saildocs.com")')
            
            if status == 'OK' and messages[0]:
                email_ids = messages[0].split()
                print(f"   📧 {len(email_ids)} email(s) de Saildocs trouvé(s)")
                
                for email_id in email_ids:
                    status, msg_data = mail.fetch(email_id, '(RFC822)')
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    print(f"   📎 Analyse des pièces jointes...")
                    
                    # Chercher pièce jointe GRIB
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        filename = part.get_filename()
                        
                        if filename:
                            print(f"      Fichier trouvé: {filename}")
                        
                        # GRIB = application/octet-stream
                        if content_type == 'application/octet-stream':
                            grib_data = part.get_payload(decode=True)
                            
                            if grib_data:
                                print(f"   ✅ GRIB reçu: {len(grib_data)} octets")
                                
                                # Marquer comme lu
                                mail.store(email_id, '+FLAGS', '\\Seen')
                                mail.logout()
                                
                                return grib_data
            
            mail.logout()
            
        except Exception as e:
            print(f"   ⚠️  Erreur vérification: {e}")
        
        # Attendre 10s avant prochaine vérification
        time.sleep(10)
    
    print(f"❌ Timeout attente Saildocs ({timeout}s)")
    return None


def process_grib_request(grib_request, inreach_url, reply_email=None):
    """
    Traite une requête GRIB complète de bout en bout
    
    Args:
        grib_request: Requête GRIB pure
        inreach_url: URL inReach pour réponse
        reply_email: Email de secours
        
    Returns:
        bool: True si succès
    """
    print(f"\n{'='*70}")
    print(f"🌊 TRAITEMENT GRIB COMPLET")
    print(f"{'='*70}")
    print(f"Requête: {grib_request}")
    print(f"URL: {inreach_url}")
    print(f"{'='*70}\n")
    
    try:
        # Étape 1: Envoyer à Saildocs
        print("📤 Étape 1/3: Envoi à Saildocs...")
        if not send_to_saildocs(grib_request):
            print("❌ Échec envoi Saildocs")
            return False
        
        # Étape 2: Attendre réponse
        print("\n⏳ Étape 2/3: Attente réponse Saildocs...")
        grib_data = wait_for_saildocs_response()
        
        if not grib_data:
            print("❌ Aucune réponse Saildocs")
            return False
        
        # Étape 3: Encoder et envoyer
        print("\n🔧 Étape 3/3: Encodage et envoi...")
        messages = encode_and_split_grib(grib_data)
        
        # Envoyer vers inReach
        success = send_to_inreach(inreach_url, messages, reply_email)
        
        if success:
            print(f"\n✅✅✅ GRIB ENVOYÉ ({len(messages)} messages) ✅✅✅\n")
            return True
        else:
            print("\n❌ Échec envoi inReach\n")
            return False
            
    except Exception as e:
        print(f"❌ Erreur process_grib: {e}")
        import traceback
        traceback.print_exc()
        return False
