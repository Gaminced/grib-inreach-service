# grib_handler.py - v3.5.6
"""Module GRIB - FIX: Préserve les points décimaux (0.5) dans requêtes"""

import time
import imaplib
import email
import sys
import requests
from config import (GARMIN_USERNAME, GARMIN_PASSWORD, MAILERSEND_API_KEY,
                    SAILDOCS_EMAIL, SAILDOCS_RESPONSE_EMAIL, IMAP_HOST, IMAP_PORT, SAILDOCS_TIMEOUT)
from utils import encode_and_split_grib
from inreach_sender import send_to_inreach
from inreach_cleaner_final import extract_grib_request

sys.stdout.flush()


def send_to_saildocs(grib_request):
    """
    Envoie requête GRIB via MailerSend avec format COMPLET Saildocs
    
    FORMAT SAILDOCS REQUIS:
    - Reply-To: garminced@gmail.com (CRITIQUE pour recevoir réponse)
    - CC: garminced@gmail.com (traçabilité)
    - Subject: vide
    - Body: send + requête
    """
    print(f"\n{'='*70}", flush=True)
    print(f"📤 ÉTAPE 1/3: ENVOI À SAILDOCS (MailerSend)", flush=True)
    print(f"{'='*70}", flush=True)
    print(f"Requête: {grib_request}", flush=True)
    
    if not MAILERSEND_API_KEY:
        print("❌ MAILERSEND_API_KEY manquant", flush=True)
        return False
    
    try:
        email_body = f"send {grib_request}"
        
        print(f"📧 Création email MailerSend...", flush=True)
        print(f"   De: inreach@test-69oxl5eoonxl785k.mlsender.net", flush=True)
        print(f"   Reply-To: {GARMIN_USERNAME}", flush=True)
        print(f"   À: {SAILDOCS_EMAIL}", flush=True)
        print(f"   CC: {GARMIN_USERNAME}", flush=True)
        print(f"   Subject: (vide)", flush=True)
        print(f"   Corps: {email_body}", flush=True)
        
        # API MailerSend
        url = "https://api.mailersend.com/v1/email"
        
        headers = {
            "Authorization": f"Bearer {MAILERSEND_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "from": {
                "email": "inreach@test-69oxl5eoonxl785k.mlsender.net",
                "name": "Garmin inReach"
            },
            "to": [
                {
                    "email": SAILDOCS_EMAIL
                }
            ],
            "cc": [
                {
                    "email": GARMIN_USERNAME,
                    "name": "Archive"
                }
            ],
            "reply_to": {
                "email": GARMIN_USERNAME,
                "name": "Garmin inReach"
            },
            "subject": "",
            "text": email_body
        }
        
        print(f"📤 Envoi email...", flush=True)
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        print(f"📬 MailerSend Status: {response.status_code}", flush=True)
        
        if response.status_code == 202:
            print(f"✅ Demande envoyée avec succès", flush=True)
            print(f"✅ Reply-To configuré: {GARMIN_USERNAME}", flush=True)
            print(f"✅ Copie envoyée à: {GARMIN_USERNAME}", flush=True)
            print(f"✅ Réponse attendue de: {SAILDOCS_RESPONSE_EMAIL}", flush=True)
            return True
        else:
            print(f"❌ Erreur HTTP {response.status_code}", flush=True)
            print(f"Response: {response.text[:500]}", flush=True)
            return False
        
    except Exception as e:
        print(f"❌ Erreur MailerSend: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return False


def wait_for_saildocs_response(timeout=SAILDOCS_TIMEOUT):
    """Attend réponse Saildocs"""
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
                        print(f"      📎 Recherche pièces jointes...", flush=True)
                        
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
            print(f"   ❌ Erreur IMAP: {e}", flush=True)
        
        if elapsed < timeout - 10:
            print(f"   ⏸️  Attente 10s...\n", flush=True)
            time.sleep(10)
        else:
            break
    
    print(f"\n❌ TIMEOUT après {timeout}s", flush=True)
    return None


def process_grib_request(raw_email_body, inreach_url, mail=None):
    """Traite requête GRIB complète"""
    print(f"\n{'='*70}", flush=True)
    print(f"🌊 TRAITEMENT GRIB v3.5.6 (MailerSend)", flush=True)
    print(f"{'='*70}", flush=True)
    
    # NOUVEAU v3.5.6: Logger l'email BRUT pour debug
    print(f"📧 Email brut (100 premiers chars): {raw_email_body[:100]}...", flush=True)
    
    print(f"🧹 Nettoyage email InReach...", flush=True)
    grib_request = extract_grib_request(raw_email_body)
    
    if not grib_request:
        print(f"❌ Impossible d'extraire la requête GRIB", flush=True)
        print(f"💡 Email brut: {raw_email_body[:200]}", flush=True)
        return False
    
    # NOUVEAU v3.5.6: Logger AVANT/APRÈS nettoyage
    print(f"✅ Requête extraite: {grib_request}", flush=True)
    print(f"📊 Longueur: {len(grib_request)} caractères", flush=True)
    print(f"🔍 Contient des points: {'OUI' if '.' in grib_request else 'NON ⚠️'}", flush=True)
    print(f"📍 URL inReach: {inreach_url}", flush=True)
    print(f"{'='*70}\n", flush=True)
    
    try:
        if not send_to_saildocs(grib_request):
            print(f"❌ Échec envoi Saildocs", flush=True)
            return False
        
        grib_data = wait_for_saildocs_response()
        if not grib_data:
            print(f"❌ Pas de réponse Saildocs", flush=True)
            return False
        
        print(f"\n{'='*70}", flush=True)
        print(f"🔧 ÉTAPE 3/3: ENCODAGE ET ENVOI", flush=True)
        print(f"{'='*70}\n", flush=True)
        
        messages = encode_and_split_grib(grib_data)
        print(f"📤 Envoi {len(messages)} messages à inReach...", flush=True)
        
        success = send_to_inreach(inreach_url, messages)
        
        if success:
            print(f"\n{'='*70}", flush=True)
            print(f"✅✅✅ SUCCÈS COMPLET ✅✅✅", flush=True)
            print(f"{'='*70}", flush=True)
            print(f"Messages envoyés: {len(messages)}", flush=True)
            print(f"Taille GRIB: {len(grib_data)} octets", flush=True)
            print(f"{'='*70}\n", flush=True)
            return True
        else:
            print(f"\n❌ Échec envoi inReach", flush=True)
            return False
            
    except Exception as e:
        print(f"\n{'='*70}", flush=True)
        print(f"❌ ERREUR CRITIQUE", flush=True)
        print(f"{'='*70}", flush=True)
        print(f"Exception: {e}", flush=True)
        import traceback
        traceback.print_exc()
        print(f"{'='*70}\n", flush=True)
        return False
